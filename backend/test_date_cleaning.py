from app.services.resume_extractor import parse_resume

# Test case 1: Project with date in name
raw_text1 = """
Projects
Smart Cache August 2022 - Present: A caching layer
- Implemented eviction policies
"""
parsed1 = parse_resume(raw_text1)
print("Test 1 - Project name with date:")
print(f"  Project name: '{parsed1.projects[0].name}'")
print(f"  Project date: '{parsed1.projects[0].date}'")
print(f"  No date in name: {('august' not in parsed1.projects[0].name.lower() and '2022' not in parsed1.projects[0].name)}")
print()

# Test case 2: Education with date duplication
raw_text2 = """
Education
University
B.S. Computer Science August 2020 - Present
"""
parsed2 = parse_resume(raw_text2)
print("Test 2 - Education date deduplication:")
print(f"  Institution: '{parsed2.education[0].institution}'")
print(f"  Degree: '{parsed2.education[0].degree}'")
print(f"  Year: '{parsed2.education[0].year}'")
degree_clean = not ('august' in parsed2.education[0].degree.lower() or '2020' in parsed2.education[0].degree) if parsed2.education[0].degree else True
print(f"  Degree has no date: {degree_clean}")
