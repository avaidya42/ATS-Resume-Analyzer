"""Extracts raw text from PDF resumes using PyMuPDF."""
import fitz  # PyMuPDF
from fastapi import HTTPException


def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read PDF file.") from exc

    if doc.page_count == 0:
        raise HTTPException(status_code=400, detail="PDF has no pages.")

    text_parts = [page.get_text("text", sort=True).replace("\x0c", "\n") for page in doc]
    doc.close()

    full_text = "\n".join(text_parts).strip()
    if not full_text:
        raise HTTPException(
            status_code=422,
            detail="No extractable text found. The PDF may be a scanned image.",
        )
    return full_text
