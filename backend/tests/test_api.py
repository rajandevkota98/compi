import json
import time
from collections.abc import Iterator
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from compi.api.app import app


def png(color: str) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (4, 4), color).save(buf, format="PNG")
    return buf.getvalue()


PNG_A = png("red")
PNG_B = png("blue")


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:  # one event loop for the module, so background runs keep going
        yield c


SPEC = {
    "id": "hello",
    "name": "Hello",
    "nodes": [
        {"id": "a", "type": "text.input", "params": {"text": "hello"}},
        {"id": "b", "type": "text.input", "params": {"text": "loom"}},
        {"id": "c", "type": "prompt.concat"},
    ],
    "edges": [
        {"source": "a", "source_port": "text", "target": "c", "target_port": "part1"},
        {"source": "b", "source_port": "text", "target": "c", "target_port": "part2"},
    ],
}


def test_nodes_lists_built_in_types_only(client: TestClient) -> None:
    types = {n["type"] for n in client.get("/api/nodes").json()}
    assert {"image.generate", "llm.run", "check.vision", "list.iterate"} <= types
    assert not any(t.startswith("test.") for t in types)


def test_save_load_and_ready_made_workflows(client: TestClient) -> None:
    assert {"product-ad", "compare-models"} <= {
        w["id"] for w in client.get("/api/workflows").json()
    }
    body = {"spec": SPEC, "layout": {"a": {"x": 1, "y": 2}}}
    assert client.put("/api/workflows/hello", json=body).json() == {"errors": []}
    assert client.get("/api/workflows/hello").json()["layout"]["a"] == {"x": 1, "y": 2}


def test_run_streams_events_then_state_shows_outputs(client: TestClient) -> None:
    run_id = client.post("/api/runs", json={"spec": SPEC}).json()["run_id"]
    with client.stream("GET", f"/api/runs/{run_id}/events") as res:
        events = [json.loads(line[6:]) for line in res.iter_lines() if line.startswith("data: ")]
    assert events[-1]["kind"] == "finished"
    assert events[-1]["result"]["outputs"]["c"] == {"text": "hello loom"}
    assert client.post("/api/state", json=SPEC).json()["c"]["status"] == "done"


def test_invalid_run_is_rejected(client: TestClient) -> None:
    bad = {**SPEC, "edges": []}
    res = client.post("/api/runs", json={"spec": bad})
    assert res.status_code == 422
    assert "c: required input 'part1' is not connected" in res.json()["detail"]


def test_reset_restores_a_ready_made_workflow(client: TestClient) -> None:
    original = client.get("/api/workflows/compare-models").json()
    edited = {**original, "spec": {**original["spec"], "name": "changed"}}
    client.put("/api/workflows/compare-models", json=edited)
    assert client.post("/api/workflows/compare-models/reset").json() == original
    assert client.post("/api/workflows/hello/reset").status_code == 404


def test_gallery_lists_images_newest_first(client: TestClient) -> None:
    first = client.post("/api/media", files={"file": ("a.png", PNG_A, "image/png")}).json()
    time.sleep(0.01)
    second = client.post("/api/media", files={"file": ("b.png", PNG_B, "image/png")}).json()
    names = [m["name"] for m in client.get("/api/media").json()]
    assert names.index(second["asset"]) < names.index(first["asset"])
