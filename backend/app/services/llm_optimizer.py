"""
backend/app/services/llm_optimizer.py

LLM-powered resume bullet point rewriting using Google's official
google-genai SDK.

Dependencies:
    pip install google-genai

Environment:
    GEMINI_API_KEY   required for live rewrites; falls back gracefully if absent.
"""

import os
import re
from typing import Optional
from dotenv import load_dotenv
from google import genai

load_dotenv()  # Load environment variables from .env file if present

MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

_client: Optional["genai.Client"] = None
_client_init_attempted = False


def _get_client() -> Optional["genai.Client"]:
    """
    Lazily initialize and cache the genai Client. Returns None (instead of
    raising) if no API key is present or initialization fails, so callers
    can fall back gracefully.
    """
    global _client, _client_init_attempted

    if _client is not None:
        return _client

    if _client_init_attempted:
        return None

    _client_init_attempted = True

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        _client = genai.Client(api_key=api_key)
        return _client
    except Exception:
        return None


def _build_prompt(bullet_point: str, target_jd: str = "") -> str:
    prompt = (
        "Rewrite the following resume bullet point so it is action-oriented, "
        "metric-driven, and starts with a strong past-tense action verb. "
        "Keep it to a single line, under 30 words. Do not invent specific "
        "numbers that aren't implied by the original — instead phrase the "
        "impact in a way that highlights measurable outcomes.\n\n"
        f"Original bullet point:\n{bullet_point}\n"
    )

    if target_jd.strip():
        prompt += (
            "\nTailor the wording to naturally reflect relevant keywords and "
            "priorities from this target job description, without "
            "keyword-stuffing:\n"
            f"{target_jd.strip()[:3000]}\n"
        )

    prompt += (
        "\nReturn ONLY the rewritten bullet point as plain text — no quotes, "
        "no markdown, no bullet symbols, no intro text, no explanation."
    )
    return prompt


def _clean_response_text(text: str) -> str:
    """Strip quotes, markdown bullets/fences, and surrounding whitespace."""
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?|```$", "", text).strip()
    text = re.sub(r"^[\-\*\u2022]\s*", "", text)
    text = text.strip("\"'")
    return text.strip()


def _local_fallback_rewrite(bullet_point: str, target_jd: str = "") -> str:
    """
    Locally formatted fallback used when the Gemini client is unavailable
    or the API call fails, so the backend never crashes.
    """
    bullet = bullet_point.strip().rstrip(".")

    action_verbs = (
        "led", "built", "developed", "designed", "implemented", "created",
        "managed", "drove", "delivered", "launched", "owned",
    )
    starts_with_verb = bullet.lower().startswith(action_verbs)

    prefix = "" if starts_with_verb else "Drove "
    rewritten = f"{prefix}{bullet} to strengthen measurable impact and results."

    if target_jd.strip():
        rewritten += " Aligned with target role requirements."

    return rewritten


def rewrite_bullet_point(bullet_point: str, target_jd: str = "") -> str:
    """
    Rewrite a resume bullet point into an action-oriented, metric-driven
    statement, optionally tailored to a target job description.

    Always returns a plain string — falls back to a locally formatted
    rewrite if the API key is missing or the call fails for any reason.
    """
    if not bullet_point or not bullet_point.strip():
        return bullet_point

    client = _get_client()
    if client is None:
        return _local_fallback_rewrite(bullet_point, target_jd)

    try:
        prompt = _build_prompt(bullet_point, target_jd)
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )

        text = getattr(response, "text", None)
        if not text:
            return _local_fallback_rewrite(bullet_point, target_jd)

        cleaned = _clean_response_text(text)
        return cleaned if cleaned else _local_fallback_rewrite(bullet_point, target_jd)

    except Exception:
        return _local_fallback_rewrite(bullet_point, target_jd)
