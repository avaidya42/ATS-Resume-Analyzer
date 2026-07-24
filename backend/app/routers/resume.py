"""
backend/app/routers/resume.py
Phase 1 (Upload/Parse) & Phase 2 (JD Matcher & Bullet Optimizer)
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

# Correct imports matching your actual services and functions
from app.services.pdf_parser import extract_text_from_pdf
from app.services.resume_extractor import (
    parse_resume,
    GeminiQuotaExceededError,
    GeminiModelUnavailableError as ExtractorModelUnavailableError,
)
from app.services.ats_scorer import calculate_ats_score
from app.services.jd_matcher import (
    match_resume_to_jd,
    JDMatchResult,
    GeminiRateLimitError,
    GeminiModelUnavailableError as MatcherModelUnavailableError,
)
from app.services.llm_optimizer import rewrite_bullet_point

router = APIRouter(prefix="/api/resume", tags=["resume"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class AnalyzeJDRequest(BaseModel):
    resume_text: str
    jd_text: str


class OptimizeBulletRequest(BaseModel):
    bullet_point: str
    target_jd: str = ""


class OptimizeBulletResponse(BaseModel):
    original_bullet: str
    optimized_bullet: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        # 1. Read file as bytes
        file_bytes = await file.read()

        # 2. Extract raw text from PDF using PyMuPDF
        raw_text = extract_text_from_pdf(file_bytes)

        # 3. Parse raw text into structured JSON schema using Gemini.
        #    parse_resume calls the Gemini SDK synchronously, so run it off
        #    the event loop to avoid blocking other requests.
        parsed_data = await run_in_threadpool(parse_resume, raw_text)

        # 4. Score the parsed resume for ATS compatibility. This is a pure
        #    rule-based/regex scorer (no Gemini call), so no need to run it
        #    in a threadpool — it's fast and non-blocking either way.
        ats_result = calculate_ats_score(parsed_data)

        # Wrapped so the frontend gets both `parsed` (ResumeDetails) and
        # `ats` (ATSScore) instead of just the raw parsed resume. Previously
        # this endpoint returned parsed_data directly, so result.ats was
        # always undefined and ATSScore.jsx silently rendered a 0.
        return {"parsed": parsed_data, "ats": ats_result}

    except HTTPException as http_exc:
        raise http_exc
    except GeminiQuotaExceededError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ExtractorModelUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-jd", response_model=JDMatchResult)
async def analyze_jd(payload: AnalyzeJDRequest):
    if not payload.resume_text.strip() or not payload.jd_text.strip():
        raise HTTPException(
            status_code=400, detail="resume_text and jd_text must not be empty"
        )

    try:
        # match_resume_to_jd calls the Gemini SDK synchronously, so run it
        # off the event loop to avoid blocking other requests.
        return await run_in_threadpool(
            match_resume_to_jd, payload.resume_text, payload.jd_text
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except GeminiRateLimitError as e:
        # Distinct from generic failures so the frontend can show
        # "please wait and try again" instead of a hard error.
        raise HTTPException(status_code=429, detail=str(e))
    except MatcherModelUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        # Missing API key / Gemini call failure / bad model response.
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/optimize-bullet", response_model=OptimizeBulletResponse)
async def optimize_bullet(payload: OptimizeBulletRequest):
    if not payload.bullet_point.strip():
        raise HTTPException(status_code=400, detail="bullet_point must not be empty")

    optimized = rewrite_bullet_point(
        bullet_point=payload.bullet_point,
        target_jd=payload.target_jd,
    )

    return OptimizeBulletResponse(
        original_bullet=payload.bullet_point,
        optimized_bullet=optimized,
    )