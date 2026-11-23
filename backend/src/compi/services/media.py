"""Images on disk, content-addressed: an IMAGE value is just the file name."""

import base64
import hashlib
from io import BytesIO

from PIL import Image

from compi.services.settings import DATA

MEDIA = DATA / "media"


def save(data: bytes, ext: str = "png") -> str:
    MEDIA.mkdir(parents=True, exist_ok=True)
    name = f"{hashlib.sha256(data).hexdigest()[:24]}.{ext.lstrip('.').lower()}"
    (MEDIA / name).write_bytes(data)
    return name


def open_image(name: str) -> Image.Image:
    return Image.open(MEDIA / name)


def save_image(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return save(buf.getvalue(), "png")


def is_image(value: object) -> bool:
    return (
        isinstance(value, str)
        and value.endswith((".png", ".jpg", ".jpeg", ".webp"))
        and (MEDIA / value).is_file()
    )


def media_type(name: str) -> str:
    ext = name.rsplit(".", 1)[-1]
    return "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"


def b64(name: str) -> str:
    return base64.standard_b64encode((MEDIA / name).read_bytes()).decode()


def data_url(name: str) -> str:
    return f"data:{media_type(name)};base64,{b64(name)}"
