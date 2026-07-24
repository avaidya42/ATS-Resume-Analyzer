"""
backend/app/services/resume_extractor.py

LLM-based resume parsing using Gemini via the official google-genai SDK
(same SDK/client pattern as llm_optimizer.py — the old google.generativeai
package is not used here).

The response is constrained directly to the ParsedResume schema via
response_schema, so the model's JSON is guaranteed well-formed — no manual
quote/newline escaping or markdown-fence stripping needed.

Dependencies: google-genai, python-dotenv
    pip install google-genai python-dotenv

Environment:
    GEMINI_API_KEY (or GOOGLE_API_KEY)   required
    GEMINI_EXTRACTOR_MODEL               optional, defaults to "gemini-3.5-flash-lite"
                                          (check ai.google.dev/gemini-api/docs/models
                                          before relying on this default — Google
                                          retires model IDs frequently)
"""

import json
import logging
import os
import time
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

from app.models.schemas import ParsedResume

load_dotenv()

logger = logging.getLogger(__name__)

# NOTE: Google has been retiring Gemini model IDs faster than their
# published deprecation dates suggest (gemini-2.5-flash was pulled well
# ahead of its announced Oct 2026 shutdown). Do not assume this default
# stays valid — check https://ai.google.dev/gemini-api/docs/models and
# https://ai.google.dev/gemini-api/docs/deprecations, and override via
# GEMINI_EXTRACTOR_MODEL the moment a model gets pulled.
MODEL_NAME = os.environ.get("GEMINI_EXTRACTOR_MODEL", "gemini-3.5-flash-lite")

# Retry behavior for genuinely transient failures only (malformed JSON,
# brief 503 overload). Daily quota exhaustion (429 RESOURCE_EXHAUSTED with
# a per-day quotaId) and a retired model ID (404) are NOT retried — neither
# is fixed by trying again immediately, and doing so just burns time and
# error-log noise.
_MAX_TRANSIENT_RETRIES = 2
_BASE_BACKOFF_SECONDS = 2.0

_client: Optional[genai.Client] = None


class GeminiQuotaExceededError(RuntimeError):
    """
    Raised when Gemini returns 429 RESOURCE_EXHAUSTED for a per-day quota.
    Distinct from transient rate limiting — retrying will not help until
    the quota resets or billing is enabled.
    """


class GeminiModelUnavailableError(RuntimeError):
    """
    Raised when Gemini returns 404 for the configured model — meaning the
    model ID has been retired/removed. Not worth retrying; the model needs
    to be swapped via GEMINI_EXTRACTOR_MODEL.
    """


def _get_client() -> genai.Client:
    """Lazily initialize and cache the genai Client."""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY (or GOOGLE_API_KEY) environment variable is not set"
            )
        _client = genai.Client(api_key=api_key)
    return _client


EXTRACTION_PROMPT = """You are an expert resume parsing system. Analyze the
raw resume text below and extract every detail into the structured schema
provided. Be exhaustive — do not skip entries. If a field isn't present in
the resume, use an empty string or empty list as appropriate; never
fabricate information that isn't in the source text.

Raw resume text:
---
{raw_text}
---
"""


def _is_daily_quota_error(exc: genai_errors.ClientError) -> bool:
    """
    Distinguish a per-day RESOURCE_EXHAUSTED quota failure (not worth
    retrying) from a transient per-minute rate limit (worth retrying).
    """
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if status != 429:
        return False
    message = str(exc)
    # The API's quota violations include a quotaId like
    # "GenerateRequestsPerDayPerProjectPerModel-FreeTier" for daily caps.
    return "PerDay" in message or "RESOURCE_EXHAUSTED" in message


def _request_once(client: genai.Client, prompt: str) -> ParsedResume:
    """Single Gemini call + parse attempt. Raises ValueError on failure."""
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ParsedResume,
                max_output_tokens=8192,
                # NOTE: `temperature` intentionally omitted. Gemini 3.x
                # ignores it already and Google has said future model
                # generations will hard-error on it. If you're on an older
                # model that still honors it, add it back explicitly.
            ),
        )
    except genai_errors.ClientError as exc:
        status = getattr(exc, "status_code", None) or getattr(exc, "code", None)

        if status == 404:
            raise GeminiModelUnavailableError(
                f"Gemini model '{MODEL_NAME}' is no longer available (it "
                "may have been retired ahead of its announced shutdown "
                "date). Set GEMINI_EXTRACTOR_MODEL to a current model — "
                "check https://ai.google.dev/gemini-api/docs/models"
            ) from exc

        if _is_daily_quota_error(exc):
            raise GeminiQuotaExceededError(
                f"Gemini daily quota exhausted for model '{MODEL_NAME}'. "
                "Wait for the daily reset, enable billing on your Google "
                "Cloud project, or switch GEMINI_EXTRACTOR_MODEL to a model "
                "with more free-tier headroom."
            ) from exc
        raise

    # When response_schema is a Pydantic model, the SDK auto-parses and
    # validates the output for you — this is the common/expected path.
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, ParsedResume):
        return parsed

    # Fallback: manually parse response.text, in case .parsed wasn't
    # populated (e.g. schema too complex for constrained decoding).
    raw = (response.text or "").strip()
    if not raw:
        raise ValueError("Gemini returned an empty response for resume extraction")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Gemini JSON output: %s", raw[:500])
        raise ValueError(f"Model did not return valid JSON: {exc}") from exc

    try:
        return ParsedResume(**data)
    except Exception as exc:
        logger.error("ParsedResume validation failed for: %s", data)
        raise ValueError(f"Extracted data did not match ParsedResume schema: {exc}") from exc


def parse_resume(raw_text: str, max_retries: int = _MAX_TRANSIENT_RETRIES) -> ParsedResume:
    """
    Extract a structured ParsedResume from raw resume text using Gemini.

    Retries a limited number of times on transient failures (malformed
    JSON, brief overload) with backoff. Does NOT retry on daily quota
    exhaustion — that fails fast with a clear GeminiQuotaExceededError
    instead, since retrying can't fix a cap that only resets once a day.

    Raises:
        RuntimeError: if no API key is configured.
        GeminiQuotaExceededError: if the daily free-tier quota is exhausted.
        ValueError: if extraction still fails after all transient retries.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("raw_text must not be empty")

    client = _get_client()
    prompt = EXTRACTION_PROMPT.format(raw_text=raw_text)

    last_error: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            return _request_once(client, prompt)
        except (GeminiQuotaExceededError, GeminiModelUnavailableError):
            # Fail fast — neither is fixed by retrying immediately.
            raise
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Resume extraction attempt %d/%d failed: %s",
                attempt + 1,
                max_retries + 1,
                exc,
            )
            if attempt < max_retries:
                wait = _BASE_BACKOFF_SECONDS * (2 ** attempt)
                time.sleep(wait)

    raise ValueError(f"Resume extraction failed after retries: {last_error}") from last_error