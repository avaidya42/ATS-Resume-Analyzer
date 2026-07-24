from fastapi import HTTPException, UploadFile
from app.config import settings

ALLOWED_CONTENT_TYPES = {"application/pdf"}


def validate_pdf_upload(file: UploadFile, size_bytes: int) -> None:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds max size of {settings.max_upload_mb}MB.",
        )

    if size_bytes == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
