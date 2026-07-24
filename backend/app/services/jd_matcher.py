"""
backend/app/services/jd_matcher.py

Job Description (JD) target matching service.

Uses Gemini (google-genai) to perform *semantic* skill-gap analysis
between a raw resume text and a raw job description string, instead of
naive substring matching. This correctly handles:

  - OR / alternative requirements (e.g. "React or Angular" is satisfied by
    either skill being present on the resume).
  - Implied / equivalent competencies (e.g. PyTorch + TensorFlow + BERT on
    the resume implies "Machine Learning" and "NLP" even if those exact
    phrases never appear in the resume text).

SCHEMA DESIGN NOTE: earlier versions asked Gemini for two independent
lists (matched_skills / missing_skills) directly. That let the same OR-group
requirement contradict itself across the two lists — the model would satisfy
"Flask, FastAPI, or Node.js/Express" via Node.js/Express in its reasoning,
then still list Flask and FastAPI separately in missing_skills, because
nothing forced the two lists to agree with each other.

This version asks the model for ONE list of requirement objects — one entry
per distinct JD requirement, each with a single status field — and then
Python deterministically splits that into matched_skills / missing_skills /
missing_other_requirements. Because each requirement now has exactly one
status, self-contradiction across the two output lists is structurally
impossible, not just less likely. This does NOT fix judgment errors (the
model can still misjudge whether a given requirement is satisfied) — that
part is an inherent LLM-accuracy limitation, not something a schema change
can fully remove.

The service still exposes a single sync entry point, `match_resume_to_jd`,
returning the same JDMatchResult shape as before, so nothing downstream
(the router, the frontend dashboard) needs to change.
"""

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types as genai_types
from google.genai import errors as genai_errors
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini client setup
# ---------------------------------------------------------------------------
# NOTE: `google-generativeai` (the old SDK, `import google.generativeai as
# genai`) is deprecated and `gemini-1.5-flash` has been fully shut down —
# requests to it now 404. This uses the current `google-genai` SDK instead.
#
# Model choice: multi-step structured reasoning (evaluate every requirement
# line and judge each one) is exactly where the "-lite" tier tends to drop
# steps on longer instruction lists. Use the non-lite flash tier by default;
# override via GEMINI_MODEL_NAME if cost/latency matters more than
# consistency for your use case.
#
# Google has been retiring Gemini model IDs faster than their published
# deprecation dates suggest (gemini-2.5-flash and gemini-2.5-pro were both
# pulled well ahead of their announced Oct 2026 shutdown). Do NOT assume any
# hardcoded model ID here stays valid — always check
# https://ai.google.dev/gemini-api/docs/models and
# https://ai.google.dev/gemini-api/docs/deprecations before relying on this
# default, and override via GEMINI_MODEL_NAME whenever a model gets pulled.
#
# We do not set `temperature` here: Gemini 3.x models ignore it already and
# Google has said future releases will hard-error on it, so it's not worth
# carrying. If determinism matters, rely on tight prompt wording instead.
_GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-3.5")
_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

_client: Optional[genai.Client] = None
if _GEMINI_API_KEY:
    _client = genai.Client(api_key=_GEMINI_API_KEY)
else:
    # Don't crash at import time (e.g. during tests / CI without the key) —
    # fail loudly only when someone actually tries to call the model.
    logger.warning(
        "GEMINI_API_KEY is not set. jd_matcher will raise at call time "
        "until this environment variable is configured."
    )

_GENERATION_CONFIG = genai_types.GenerateContentConfig(
    response_mime_type="application/json",
    # The requirements-list schema is noticeably chattier than a flat
    # matched/missing pair (item + type + status + note per requirement),
    # and JDs with many requirements can produce a long list. Without an
    # explicit budget the response can get cut off mid-JSON, which then
    # fails to parse. 8192 gives comfortable headroom for a JD with 20-30
    # requirement entries; raise further if you routinely paste in very
    # long JDs and still see truncation.
    max_output_tokens=8192,
)

# Retry behavior for transient failures (429 per-minute rate limit, 503
# overloaded). NOT used for daily-quota exhaustion or a retired model ID —
# both fail fast instead, since retrying can't fix either.
_MAX_RETRIES = 3
_BASE_BACKOFF_SECONDS = 2.0

# Roughly bounds prompt size so we don't blow past context limits / rack up
# cost on pathologically long uploads. Adjust as needed for your use case.
_MAX_CHARS_PER_DOCUMENT = 12000

__all__ = [
    "JDMatchResult",
    "match_resume_to_jd",
    "GeminiRateLimitError",
    "GeminiModelUnavailableError",
]


# ---------------------------------------------------------------------------
# Public result schema — unchanged from before, so the router and frontend
# don't need to change.
# ---------------------------------------------------------------------------

class JDMatchResult(BaseModel):
    match_percentage: int
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    missing_other_requirements: List[str] = []
    analysis_summary: str = ""


# ---------------------------------------------------------------------------
# Internal schema — what we actually ask Gemini for. One entry per JD
# requirement, each with a single status, so matched/missing can never
# disagree about the same requirement.
# ---------------------------------------------------------------------------

class _RequirementItem(BaseModel):
    item: str
    type: str  # "skill" | "other"
    status: str  # "matched" | "missing"
    note: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _truncate(text: str, max_chars: int = _MAX_CHARS_PER_DOCUMENT) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n[...truncated...]"


def _build_prompt(resume_text: str, jd_text: str) -> str:
    return f"""You are an expert technical recruiter performing a skill-gap
analysis between a candidate's resume and a job description.

Go through the job description and build ONE list of requirement objects —
one entry per distinct requirement — covering EVERY item mentioned, in both
"Required Qualifications" and any "Nice to Have" / "Preferred" / "Bonus"
sections. Do not skip nice-to-have items just because they're optional; a
missing nice-to-have still belongs in the list with status "missing", and a
covered one still belongs with status "matched". Re-read the JD once more
before finalizing and confirm every named requirement has exactly one
entry.

For each requirement, decide ONE status — "matched" or "missing" — using
this reasoning:

1. Alternative / OR requirements: if the JD lists options joined by "or" /
   "," (e.g. "React or Angular", "Flask, FastAPI, or Node.js/Express"),
   that is ONE requirement entry (item = the full phrase as written), not
   one entry per option. If the candidate has ANY ONE option from the
   group, status = "matched" — put the specific option they have in the
   `note` field (e.g. note: "Node.js/Express"). Never create separate
   entries for the individual options within an OR-group.
2. Implied / equivalent competencies: if the JD asks for a broader
   competency (e.g. "Machine Learning", "NLP", "Cloud Experience") and the
   resume demonstrates it indirectly through specific tools or frameworks
   (e.g. PyTorch, TensorFlow, BERT implies Machine Learning and NLP; AWS
   Lambda + S3 implies Cloud Experience), status = "matched". Do NOT apply
   this in reverse: possessing a general competency (e.g. "Machine
   Learning" via scikit-learn/XGBoost) does NOT automatically satisfy a
   more specific named tool in the same family (e.g. it does not satisfy a
   requirement for "PyTorch" or "TensorFlow" specifically) — judge each
   specific named tool/framework on its own merits.
3. Only mark a requirement "missing" if it's a genuine gap not covered by
   any alternative option and not reasonably implied by other experience
   on the resume.
4. `type` is "skill" for technical skills, tools, frameworks, and
   competencies (e.g. Docker, NLP, System Design, "Flask, FastAPI, or
   Node.js/Express"). `type` is "other" for non-skill requirements:
   tenure/seniority (e.g. "4+ years of experience"), education (e.g.
   "Bachelor's degree"), certifications, work-authorization/location, and
   soft logistics (e.g. "comfortable with on-call rotation"). If
   tenure/experience isn't stated explicitly on the resume but is
   reasonably inferable from work history dates, status = "matched" rather
   than flagging it. For a required degree: check the education entry's
   dates — if it shows an ongoing or future end date (still enrolled, not
   yet graduated), status = "missing" with note "currently in progress,
   not yet completed".
5. Compute a holistic semantic match_percentage (0-100) reflecting the
   candidate's real-world fit, weighted toward "skill" requirements over
   "other" requirements, and accounting for points 1-4 above (not a raw
   ratio of matched/total entries).

Respond with ONLY a single JSON object, no markdown fences, no commentary,
matching exactly this shape:

{{
  "match_percentage": <integer 0-100>,
  "requirements": [
    {{"item": "<requirement exactly as it reads or the full OR-phrase>",
      "type": "skill" | "other",
      "status": "matched" | "missing",
      "note": "<optional short note — which option satisfied an OR-group,
        or why something is missing (e.g. degree in progress); empty
        string if nothing to add>"}}
  ],
  "analysis_summary": "<2-4 sentence plain-English summary of overall fit,
    mentioning any equivalence/implied-skill reasoning you applied>"
}}

--- RESUME ---
{_truncate(resume_text)}

--- JOB DESCRIPTION ---
{_truncate(jd_text)}
"""


def _extract_json_object(raw_text: str) -> Dict[str, Any]:
    """
    Gemini is asked for pure JSON via response_mime_type, but we defensively
    strip markdown fences / stray text in case the model doesn't comply.
    """
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Last-resort attempt: grab the first {...} block in the response.
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


class GeminiRateLimitError(RuntimeError):
    """Raised when Gemini returns 429 after all retries are exhausted."""


class GeminiModelUnavailableError(RuntimeError):
    """
    Raised when Gemini returns 404 for the configured model — meaning the
    model ID has been retired/removed. Not worth retrying; the model needs
    to be swapped via GEMINI_MODEL_NAME.
    """


def _call_gemini(prompt: str) -> Dict[str, Any]:
    if not _client:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Set it in your environment before "
            "calling match_resume_to_jd()."
        )

    last_error: Optional[Exception] = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = _client.models.generate_content(
                model=_GEMINI_MODEL_NAME,
                contents=prompt,
                config=_GENERATION_CONFIG,
            )
            if not getattr(response, "text", None):
                raise RuntimeError("Gemini returned an empty response.")

            candidates = getattr(response, "candidates", None) or []
            finish_reason = getattr(candidates[0], "finish_reason", None) if candidates else None
            if str(finish_reason) in ("MAX_TOKENS", "FinishReason.MAX_TOKENS"):
                raise RuntimeError(
                    "Gemini's response was cut off before finishing (hit the "
                    "max_output_tokens budget). Increase max_output_tokens in "
                    "_GENERATION_CONFIG, or shorten the resume/JD input."
                )

            return _extract_json_object(response.text)

        except genai_errors.ClientError as exc:
            status = getattr(exc, "status_code", None) or getattr(exc, "code", None)

            if status == 404:
                raise GeminiModelUnavailableError(
                    f"Gemini model '{_GEMINI_MODEL_NAME}' is no longer "
                    "available (it may have been retired ahead of its "
                    "announced shutdown date). Set GEMINI_MODEL_NAME to a "
                    "current model — check "
                    "https://ai.google.dev/gemini-api/docs/models"
                ) from exc

            # 429 = rate limit / quota exceeded. Retry with backoff; if the
            # project-level quota is actually exhausted (not just a burst),
            # retries won't help and this will raise GeminiRateLimitError.
            if status == 429 and attempt < _MAX_RETRIES - 1:
                wait = _BASE_BACKOFF_SECONDS * (2 ** attempt)
                logger.warning(
                    "Gemini rate-limited (attempt %d/%d), retrying in %.1fs",
                    attempt + 1, _MAX_RETRIES, wait,
                )
                time.sleep(wait)
                last_error = exc
                continue
            if status == 429:
                raise GeminiRateLimitError(
                    "Gemini API quota/rate limit exceeded. Check your quota "
                    "at https://aistudio.google.com/ or enable billing."
                ) from exc
            raise

    raise RuntimeError(f"Gemini call failed after {_MAX_RETRIES} attempts") from last_error


def _coerce_requirements(raw_items: Any) -> List[_RequirementItem]:
    """Best-effort parse of the requirements array; skips malformed entries
    individually instead of failing the whole response over one bad item."""
    if not isinstance(raw_items, list):
        return []

    items: List[_RequirementItem] = []
    for entry in raw_items:
        if not isinstance(entry, dict):
            continue
        item_text = str(entry.get("item", "")).strip()
        if not item_text:
            continue

        item_type = str(entry.get("type", "")).strip().lower()
        if item_type not in ("skill", "other"):
            item_type = "skill"  # sane default rather than dropping it

        status = str(entry.get("status", "")).strip().lower()
        if status not in ("matched", "missing"):
            # Ambiguous status — safer to surface as missing than to hide it
            status = "missing"

        note = str(entry.get("note", "")).strip()

        try:
            items.append(
                _RequirementItem(item=item_text, type=item_type, status=status, note=note)
            )
        except ValidationError:
            continue

    return items


def _coerce_result(payload: Dict[str, Any]) -> JDMatchResult:
    """
    Split the single requirements list into matched_skills / missing_skills
    / missing_other_requirements. Each requirement has exactly one status,
    so a requirement can never end up in two conflicting output lists.
    """
    pct = payload.get("match_percentage", 0)
    try:
        pct = int(round(float(pct)))
    except (TypeError, ValueError):
        pct = 0
    pct = max(0, min(100, pct))

    requirements = _coerce_requirements(payload.get("requirements"))

    matched_skills: List[str] = []
    missing_skills: List[str] = []
    missing_other_requirements: List[str] = []

    for req in requirements:
        if req.type == "skill":
            if req.status == "matched":
                matched_skills.append(req.item)
            else:
                missing_skills.append(req.item)
        else:  # type == "other"
            if req.status == "missing":
                label = f"{req.item} — {req.note}" if req.note else req.item
                missing_other_requirements.append(label)
            # matched "other" requirements (e.g. degree already completed,
            # tenure satisfied) intentionally produce no output — nothing
            # useful to show the user for a requirement that's just fine.

    return JDMatchResult(
        match_percentage=pct,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        missing_other_requirements=missing_other_requirements,
        analysis_summary=str(payload.get("analysis_summary", "")).strip(),
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def match_resume_to_jd(resume_text: str, jd_text: str) -> JDMatchResult:
    """
    Compare raw resume text against a raw job description using Gemini for
    semantic skill-gap analysis.

    Args:
        resume_text: raw parsed resume text (flattened string).
        jd_text: raw job description text.

    Returns:
        JDMatchResult with a semantic match percentage, matched/missing
        skills (accounting for OR-requirements and implied competencies),
        and a short human-readable analysis summary.

    Raises:
        RuntimeError: if GEMINI_API_KEY is missing or the model call fails.
        ValueError: if the model response can't be parsed into valid JSON.
    """
    if not resume_text.strip() or not jd_text.strip():
        raise ValueError("resume_text and jd_text must not be empty")

    prompt = _build_prompt(resume_text, jd_text)

    try:
        raw_payload = _call_gemini(prompt)
    except (GeminiRateLimitError, GeminiModelUnavailableError):
        raise
    except Exception as exc:
        logger.exception("Gemini call failed during JD matching")
        raise RuntimeError(f"JD matching failed: {exc}") from exc

    try:
        return _coerce_result(raw_payload)
    except ValidationError as exc:
        logger.exception("Gemini response failed schema validation: %s", raw_payload)
        raise ValueError(f"Invalid response shape from Gemini: {exc}") from exc


# ---------------------------------------------------------------------------
# NOTE on async usage
# ---------------------------------------------------------------------------
# `google-genai`'s `client.models.generate_content` call is
# synchronous/blocking. If your FastAPI route is `async def`, either:
#   1. Run this in a thread pool (what the router in this project does):
#        result = await run_in_threadpool(match_resume_to_jd, resume_text, jd_text)
#      (from starlette.concurrency import run_in_threadpool)
#   2. Or switch to the async client:
#        response = await _client.aio.models.generate_content(
#            model=_GEMINI_MODEL_NAME, contents=prompt, config=_GENERATION_CONFIG,
#        )
#      and make match_resume_to_jd itself `async def`.