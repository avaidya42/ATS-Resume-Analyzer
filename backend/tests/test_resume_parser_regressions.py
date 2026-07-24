from app.models.schemas import ContactInfo, Education, Experience, ParsedResume, Project
from app.services.ats_scorer import calculate_ats_score
from app.services.resume_extractor import parse_resume


def test_projects_are_parsed_as_separate_entries_with_bullets():
    raw_text = """
    Name
    Email
    Experience
    Google
    Software Engineer
    August 2022 - Present
    - Built a dashboard
    - Developed a search pipeline
    Projects
    Smart Cache: A caching layer with low latency
    - Constructed a distributed cache
    - Implemented eviction policies
    Job Board: Built for recruiting teams
    - Designed a matching workflow
    Education
    University of Example
    B.S. Computer Science
    August 2022 - Present
    """

    parsed = parse_resume(raw_text)

    assert len(parsed.projects) == 2
    assert parsed.projects[0].name == "Smart Cache"
    assert parsed.projects[0].description == "A caching layer with low latency"
    assert parsed.projects[0].bullet_points == ["Constructed a distributed cache", "Implemented eviction policies"]
    assert parsed.projects[1].name == "Job Board"
    assert parsed.projects[1].description == "Built for recruiting teams"
    assert parsed.projects[1].bullet_points == ["Designed a matching workflow"]


def test_action_verbs_are_scored_from_experience_and_project_bullets():
    parsed = ParsedResume(
        contact=ContactInfo(),
        experience=[Experience(company="Example", role="Engineer", duration=None, bullets=["Built a dashboard"])],
        projects=[Project(name="Search", description=None, date=None, bullet_points=["Implemented a search pipeline"], tech_stack=[])],
        raw_text="",
    )

    result = calculate_ats_score(parsed)
    assert result.breakdown.action_verbs == 100.0


def test_date_ranges_are_not_duplicated():
    raw_text = """
    Education
    University of Example
    B.S. Computer Science
    August 2022 - Present
    Experience
    Google
    Software Engineer
    June 2024 - July 2024
    """

    parsed = parse_resume(raw_text)

    assert parsed.education[0].year == "August 2022 - Present"
    assert parsed.experience[0].duration == "June 2024 - July 2024"


def test_bullet_continuations_are_appended_to_the_previous_bullet():
    raw_text = """
    Experience
    Example Corp
    - to assist developers with secure code
    generation and task completion.
    """

    parsed = parse_resume(raw_text)

    assert parsed.experience[0].bullets == ["to assist developers with secure code generation and task completion."]


def test_project_titles_split_into_multiple_entries():
    raw_text = """
    Projects
    AI-Enhanced Phishing Detection Tool
    Built a phishing detection pipeline using NLP.
    CoachConnect App
    Built a coaching platform for mentors and students.
    Resume Intelligence Platform
    Built an ATS scoring dashboard.
    """

    parsed = parse_resume(raw_text)

    assert [p.name for p in parsed.projects] == [
        "AI-Enhanced Phishing Detection Tool",
        "CoachConnect App",
        "Resume Intelligence Platform",
    ]


def test_date_formatter_deduplicates_repeated_ranges():
    raw_text = """
    Education
    University of Example
    August 2022 - Present · August 2022 - Present
    """

    parsed = parse_resume(raw_text)

    assert parsed.education[0].year == "August 2022 - Present"
