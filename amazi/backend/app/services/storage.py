import os
import uuid
from pathlib import Path
from fastapi import UploadFile
from app.core.config import get_settings


settings = get_settings()


def save_upload_locally(file: UploadFile) -> str:
    ext = Path(file.filename or "upload").suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest = Path(settings.storage_dir) / unique_name
    with open(dest, "wb") as f:
        f.write(file.file.read())
    return str(dest)

