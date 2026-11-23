from conftest import wire
from PIL import Image

from compi.domain.sockets import Items
from compi.domain.spec import NodeSpec, WorkflowSpec
from compi.engine.cache import DiskCache, MemoryCache
from compi.engine.run import run
from compi.services import media
from compi.services.settings import DATA


def photo(color: str = "red", size: tuple[int, int] = (400, 300)) -> str:
    return media.save_image(Image.new("RGBA", size, color))


async def test_resize_adjust_and_composite() -> None:
    spec = WorkflowSpec(
        id="m",
        name="media",
        nodes=(
            NodeSpec(id="bg", type="image.input", params={"asset": photo("blue", (800, 800))}),
            NodeSpec(id="fg", type="image.input", params={"asset": photo("red")}),
            NodeSpec(id="small", type="image.resize", params={"width": 200, "height": 100}),
            NodeSpec(id="place", type="image.composite", params={"scale": 0.5}),
            NodeSpec(id="grade", type="image.adjust", params={"brightness": 0.5}),
        ),
        edges=(
            wire("fg", "small", "image", "image"),
            wire("bg", "place", "background", "image"),
            wire("small", "place", "foreground", "image"),
            wire("place", "grade", "image", "image"),
        ),
    )
    out = (await run(spec, MemoryCache())).outputs
    assert media.open_image(out["small"]["image"]).size == (200, 100)
    graded = media.open_image(out["grade"]["image"]).convert("RGB")
    assert graded.size == (800, 800)
    assert graded.getpixel((400, 400)) == (127, 0, 0)  # red foreground at the centre, darkened
    assert graded.getpixel((10, 10)) == (0, 0, 127)  # blue background at the corner


async def test_disk_cache_keeps_items() -> None:
    cache = DiskCache(DATA / "test-cache")
    await cache.put("k:review", {"image": Items(["a.png", "b.png"]), "n": 1})
    got = await cache.get("k:review")
    assert got == {"image": ("a.png", "b.png"), "n": 1}
    assert got is not None and isinstance(got["image"], Items)
