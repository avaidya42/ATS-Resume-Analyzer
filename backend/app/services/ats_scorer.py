"""Rule-based ATS compatibility scorer.

Each sub-score is 0-100; the overall score is a weighted average.
Weights are chosen to reflect what real ATS/recruiter screens emphasize.
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


def _project_content(project) -> list[str]:
    """
    Returns the lines of substantive content for a project, counted once.

    resume_extractor.py (Gemini) frequently populates both `description`
    and `bullet_points` with the *same* sentence for a one-line project —
    there's nothing in the schema/prompt that says these should be
    mutually exclusive. Scoring functions that previously did
    `bullets += [description] + bullet_points` were silently double-
    counting every such project. Here we prefer bullet_points when
    present (it's the more granular/structured field) and only fall back
    to description when bullet_points is empty, so each project's content
    is counted exactly once regardless of which field(s) it landed in.
    """
    if project.bullet_points:
        return list(project.bullet_points)
    if project.description:
        return [project.description]
    return []


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
    keyword_count = len(resume.skills) + sum(len(e.bullets) for e in resume.experience)
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
    bullets = [b for e in resume.experience for b in e.bullets]
    bullets += [line for p in resume.projects for line in _project_content(p)]
    if not bullets:
        return 0.0
    strong = sum(1 for b in bullets if _first_word(b) in ACTION_VERBS)
    return round((strong / len(bullets)) * 100, 1)


def _score_quantified_achievements(resume: ParsedResume) -> float:
    bullets = [b for e in resume.experience for b in e.bullets]
    bullets += [line for p in resume.projects for line in _project_content(p)]
    bullets += resume.achievements
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