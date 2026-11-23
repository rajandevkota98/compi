"""HTTP API + the built canvas. Run: uv run uvicorn compi.api.app:app --env-file ../.env"""

import json
import shutil
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import compi.nodes  # noqa: F401  # pyright: ignore[reportUnusedImport]  (registers node types)
from compi.api import runs
from compi.domain.spec import WorkflowSpec
from compi.engine.cache import DiskCache
from compi.engine.registry import all_types, schema
from compi.engine.review import approve, node_states
from compi.engine.validate import validate
from compi.services import media
from compi.services.settings import DATA

ROOT = Path(__file__).resolve().parents[4]  # repo root: workflows/ and frontend/dist live here
WORKFLOWS = DATA / "workflows"
CACHE = DiskCache(DATA / "cache")


class Workflow(BaseModel):
    spec: WorkflowSpec
    layout: dict[str, dict[str, float]] = {}  # node id -> {x, y} on the canvas


class RunRequest(BaseModel):
    spec: WorkflowSpec
    targets: list[str] | None = None


class ReviewRequest(BaseModel):
    spec: WorkflowSpec
    node_id: str
    outputs: dict[str, Any] | None = None


def _seed_workflows() -> None:
    """Copy the ready-made workflows into the data folder the first time."""
    WORKFLOWS.mkdir(parents=True, exist_ok=True)
    for path in (ROOT / "workflows").glob("*.json"):
        if not (WORKFLOWS / path.name).exists():
            shutil.copy(path, WORKFLOWS)


_seed_workflows()
media.MEDIA.mkdir(parents=True, exist_ok=True)
app = FastAPI(title="Compi")


@app.get("/api/nodes")
def nodes() -> list[dict[str, Any]]:
    return [schema(t) for t in all_types() if not t.startswith("test.")]


def _original(workflow_id: str) -> Path:
    """The ready-made copy in the repo, if this workflow is one of them."""
    return ROOT / "workflows" / f"{Path(workflow_id).name}.json"


@app.get("/api/workflows")
def workflows() -> list[dict[str, str | bool]]:
    found = (json.loads(p.read_text()) for p in sorted(WORKFLOWS.glob("*.json")))
    return [
        {
            "id": w["spec"]["id"],
            "name": w["spec"]["name"],
            "builtin": _original(w["spec"]["id"]).exists(),
        }
        for w in found
    ]


@app.post("/api/workflows/{workflow_id}/reset")
def reset(workflow_id: str) -> Workflow:
    """Put a ready-made workflow back to how it shipped."""
    if not _original(workflow_id).exists():
        raise HTTPException(404, "only ready-made workflows can be reset")
    shutil.copy(_original(workflow_id), WORKFLOWS)
    return load(workflow_id)


@app.get("/api/workflows/{workflow_id}")
def load(workflow_id: str) -> Workflow:
    path = WORKFLOWS / f"{Path(workflow_id).name}.json"
    if not path.exists():
        raise HTTPException(404, "no such workflow")
    return Workflow.model_validate_json(path.read_text())


@app.put("/api/workflows/{workflow_id}")
def save(workflow_id: str, workflow: Workflow) -> dict[str, list[str]]:
    (WORKFLOWS / f"{Path(workflow_id).name}.json").write_text(workflow.model_dump_json(indent=2))
    return {"errors": validate(workflow.spec)}


@app.post("/api/state")
async def state(spec: WorkflowSpec) -> dict[str, dict[str, object]]:
    return await node_states(spec, CACHE)


@app.post("/api/runs")
async def start_run(req: RunRequest) -> dict[str, str]:
    if errors := validate(req.spec):
        raise HTTPException(422, errors)
    return {"run_id": runs.start(req.spec, CACHE, req.targets)}


@app.get("/api/runs/{run_id}/events")
def run_events(run_id: str) -> StreamingResponse:
    if run_id not in runs.RUNS:
        raise HTTPException(404, "no such run")
    return StreamingResponse(runs.sse(runs.RUNS[run_id]), media_type="text/event-stream")


@app.post("/api/review")
async def review(req: ReviewRequest) -> dict[str, bool]:
    try:
        await approve(req.spec, CACHE, req.node_id, req.outputs)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"ok": True}


@app.get("/api/media")
def gallery() -> list[dict[str, str | float]]:
    """Every image made or uploaded, newest first."""
    files = [p for p in media.MEDIA.iterdir() if media.is_image(p.name)]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [{"name": p.name, "time": p.stat().st_mtime} for p in files]


@app.post("/api/media")
async def upload(file: UploadFile) -> dict[str, str]:
    ext = Path(file.filename or "upload.png").suffix or ".png"
    return {"asset": media.save(await file.read(), ext)}


app.mount("/media", StaticFiles(directory=media.MEDIA), name="media")
if (ROOT / "frontend" / "dist").is_dir():
    app.mount("/", StaticFiles(directory=ROOT / "frontend" / "dist", html=True), name="canvas")
