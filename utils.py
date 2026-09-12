import os
from pathlib import Path
from typing import Optional

from PIL import Image, ImageOps
from werkzeug.datastructures import FileStorage


ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def ensure_upload_dir(base_dir: str, folder_name: str = "uploads") -> str:
    target_dir = Path(base_dir) / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)
    return str(target_dir)


def valid_image(file: Optional[FileStorage]) -> bool:
    if not file or not hasattr(file, "filename"):
        return False
    return Path(file.filename).suffix.lower().lstrip(".") in ALLOWED_EXTENSIONS


def save_upload_image(file: Optional[FileStorage], folder: str = "uploads", max_size: tuple[int, int] = (1200, 1200)) -> str:
    if not file or not valid_image(file):
        raise ValueError("Archivo no válido o formato no permitido.")

    upload_dir = ensure_upload_dir(os.path.join(os.getcwd(), "static"), folder)
    filename = Path(file.filename).name
    stem = Path(filename).stem
    ext = Path(filename).suffix.lower()
    unique_name = f"{stem}_{os.urandom(4).hex()}{ext}"
    target_path = Path(upload_dir) / unique_name

    image = Image.open(file)
    image = ImageOps.exif_transpose(image)
    image.thumbnail(max_size, Image.Resampling.LANCZOS)

    if image.mode in ("RGBA", "LA"):
        background = Image.new("RGBA", image.size, (255, 255, 255, 255))
        background.paste(image, mask=image.getchannel("A"))
        image = background.convert("RGB")

    image.save(target_path, quality=85, optimize=True)
    return str(Path(folder) / unique_name).replace("\\", "/")
