"""Rule-based ATS compatibility scorer.

Each sub-score is 0-100; the overall score is a weighted average.
Weights are chosen to reflect what real ATS/recruiter screens emphasize.

STABILITY NOTE: `action_verbs` and `quantified_achievements` used to read
from ParsedResume's `bullets` / `bullet_points` fields, which are populated
by Gemini (resume_extractor.py) — an LLM call with no determinism
guarantee. In practice, Gemini would sometimes paraphrase or embellish
bullet wording between identical uploads of the same PDF (e.g. prepending
an extra verb, or appending an invented "impact" sentence not present in
the source). Since these two scorers key off exact first-word matches and
literal digit/percent patterns, even small wording drift flipped bullets
in or out of scoring — producing a materially different overall ATS score
for the exact same resume file from one upload to the next.

Fix: these two scorers now read bullet lines directly out of
`resume.raw_text` (extracted by PyMuPDF at upload time — a fixed,
non-LLM, byte-for-byte deterministic transform of the PDF) via
`_raw_bullet_lines()`, instead of trusting Gemini's rewritten copies. Given
the same PDF, this always yields the same bullet list, so these two scores
can no longer vary between identical uploads. The rest of the breakdown
(structure, section_completeness, technical_skills) still reasonably
depends on Gemini's *structural* parsing (which sections/skills exist),
since that's a lower-variance judgment than verbatim wording and there's
no raw-text equivalent for "did it find an education section."
"""
import re
from app.models.schemas import ATSResult, ParsedResume, ScoreBreakdown

ACTION_VERBS = {
    "led", "built", "developed", "designed", "implemented", "created", "optimized",
    "improved", "reduced", "increased", "launched", "architected", "automated",
    "managed", "engineered", "deployed", "delivered", "streamlined", "spearheaded",
    "collaborated", "analyzed", "integrated", "refactored", "migrated", "scaled",
    "constructed", "set",
}

WEIGHTS = {
    "structure": 0.10,
    "formatting": 0.10,
    "section_completeness": 0.15,
    "keyword_density": 0.10,
    "technical_skills": 0.15,
    "action_verbs": 0.15,
    "quantified_achievements": 0.15,
    "readability": 0.10,
}

# Matches a line that starts (after optional leading whitespace) with a
# common bullet-marker character, capturing the text after the marker.
# This is what makes bullet extraction independent of Gemini's parsing —
# it runs directly against the deterministic raw_text from PyMuPDF.
_BULLET_LINE_RE = re.compile(r"^\s*[•\-\*\u2022\u25CF\u25AA\u25CB\u25E6]\s*(.+)$")

# Detects "Label: item, item, item" category-list lines (e.g. "Languages:
# Python, Java, C", "Tools: Docker, Git, AWS"). These commonly appear
# bullet-marked under a Skills-type section, but were never written as
# accomplishment sentences — they shouldn't be scored for action
# verbs/quantified impact.
#
# This matches on the SHAPE of the line (short label + colon + 2+
# comma-separated items), not on specific section header text. That's
# deliberate: resumes name this section differently ("Skills",
# "Technical Skills & Tools", "Core Competencies", "Programming
# Languages", etc.), and matching against a fixed list of header strings
# would silently fail to help on any resume that phrases it differently.
# Judging each line by its own structure works regardless of what the
# surrounding section is called, or even whether it has a recognizable
# header at all.
_LABEL_LIST_LINE_RE = re.compile(
    r"^[A-Za-z][A-Za-z /&\-]{1,30}:\s*"            # short label + colon
    r"[A-Za-z0-9][\w.+#/\-]*(?: [\w.+#/\-]+)*"       # first item
    r"(,\s*[A-Za-z0-9][\w.+#/\-]*(?: [\w.+#/\-]+)*){1,}\s*$"  # 2+ more items
)


def _raw_bullet_lines(raw_text: str) -> list[str]:
    """
    Extract bullet-marked lines from the raw resume text, verbatim, but
    skip category-label lines (e.g. "Languages: Python, Java, C") — those
    are lists, not accomplishment statements, and scoring them for action
    verbs/quantified impact unfairly drags the score down regardless of
    what the resume calls that section.
    Deterministic for a given PDF — no LLM involved.
    """
    lines = []
    for line in raw_text.splitlines():
        match = _BULLET_LINE_RE.match(line)
        if not match:
            continue
        content = match.group(1).strip()
        if _LABEL_LIST_LINE_RE.match(content):
            continue
        lines.append(content)
    return lines


def _score_structure(resume: ParsedResume) -> float:
    present = sum([
        bool(resume.contact.email),
        bool(resume.contact.phone),
        bool(resume.education),
        bool(resume.experience or resume.projects),
        bool(resume.skills),
    ])
    return round((present / 5) * 100, 1)


def _score_formatting(raw_text: str) -> float:
    score = 100.0
    lines = [ln for ln in raw_text.splitlines() if ln.strip()]
    if len(lines) < 10:
        score -= 25
    long_lines = [ln for ln in lines if len(ln) > 220]
    score -= min(len(long_lines) * 5, 25)
    if re.search(r"\t{2,}", raw_text):
        score -= 10
    return round(max(score, 0), 1)


def _score_section_completeness(resume: ParsedResume) -> float:
    sections = [
        resume.education, resume.experience, resume.projects, resume.skills,
        resume.certifications, resume.achievements,
    ]
    filled = sum(1 for s in sections if s)
    return round((filled / len(sections)) * 100, 1)


def _score_keyword_density(resume: ParsedResume) -> float:
    word_count = max(len(resume.raw_text.split()), 1)
    keyword_count = len(resume.skills) + len(_raw_bullet_lines(resume.raw_text))
    density = keyword_count / word_count
    # ideal density band ~2%-8% of words tied to skills/impact bullets
    score = min(density / 0.05, 1.0) * 100
    return round(min(score, 100), 1)


def _score_technical_skills(resume: ParsedResume) -> float:
    count = len(resume.skills)
    if count == 0:
        return 0.0
    return round(min(count / 12, 1.0) * 100, 1)


FIRST_WORD_RE = re.compile(r"^[\s\-\*•\u2022\u25CF▪●○\"'“”.,:;]*([A-Za-z]+)")


def _first_word(text: str) -> str | None:
    match = FIRST_WORD_RE.match(text)
    return match.group(1).lower() if match else None


def _score_action_verbs(resume: ParsedResume) -> float:
    bullets = _raw_bullet_lines(resume.raw_text)
    if not bullets:
        return 0.0
    strong = sum(1 for b in bullets if _first_word(b) in ACTION_VERBS)
    return round((strong / len(bullets)) * 100, 1)


def _score_quantified_achievements(resume: ParsedResume) -> float:
    bullets = _raw_bullet_lines(resume.raw_text)
    if not bullets:
        return 0.0
    number_re = re.compile(r"\d+%?|\$\d+|\d+x\b")
    quantified = sum(1 for b in bullets if number_re.search(b))
    return round((quantified / len(bullets)) * 100, 1)


def _score_readability(raw_text: str) -> float:
    sentences = re.split(r"[.!?\n]", raw_text)
    sentences = [s for s in sentences if s.strip()]
    if not sentences:
        return 0.0
    avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
    # ideal bullet/sentence length ~8-20 words
    if 8 <= avg_len <= 20:
        return 100.0
    penalty = min(abs(avg_len - 14) * 4, 100)
    return round(max(100 - penalty, 0), 1)


def calculate_ats_score(resume: ParsedResume) -> ATSResult:
    breakdown = ScoreBreakdown(
        structure=_score_structure(resume),
        formatting=_score_formatting(resume.raw_text),
        section_completeness=_score_section_completeness(resume),
        keyword_density=_score_keyword_density(resume),
        technical_skills=_score_technical_skills(resume),
        action_verbs=_score_action_verbs(resume),
        quantified_achievements=_score_quantified_achievements(resume),
        readability=_score_readability(resume.raw_text),
    )

    overall = sum(getattr(breakdown, k) * w for k, w in WEIGHTS.items())

    notes = []
    if breakdown.quantified_achievements < 40:
        notes.append("Add measurable results (%, numbers, time saved) to your bullet points.")
    if breakdown.action_verbs < 50:
        notes.append("Start bullet points with strong action verbs (Built, Led, Optimized).")
    if breakdown.technical_skills < 50:
        notes.append("List more relevant technical skills to improve keyword matching.")
    if breakdown.section_completeness < 70:
        notes.append("Some standard resume sections appear to be missing.")
    if not notes:
        notes.append("Resume is well-structured with strong ATS compatibility.")

    return ATSResult(overall_score=round(overall, 1), breakdown=breakdown, notes=notes)