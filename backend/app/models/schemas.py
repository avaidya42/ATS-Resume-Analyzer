from pydantic import BaseModel
from typing import List, Optional


class Education(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    year: Optional[str] = None
    gpa: Optional[str] = None


class Experience(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    duration: Optional[str] = None
    bullets: List[str] = []


class Project(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None
    bullet_points: List[str] = []
    tech_stack: List[str] = []


class ContactInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None


class ParsedResume(BaseModel):
    contact: ContactInfo
    education: List[Education] = []
    experience: List[Experience] = []
    projects: List[Project] = []
    skills: List[str] = []
    certifications: List[str] = []
    achievements: List[str] = []
    languages: List[str] = []
    raw_text: str = ""


class ScoreBreakdown(BaseModel):
    structure: float
    formatting: float
    section_completeness: float
    keyword_density: float
    technical_skills: float
    action_verbs: float
    quantified_achievements: float
    readability: float


class ATSResult(BaseModel):
    overall_score: float
    breakdown: ScoreBreakdown
    notes: List[str] = []


class ResumeAnalysisResponse(BaseModel):
    resume_id: str
    parsed: ParsedResume
    ats: ATSResult


class JobMatchRequest(BaseModel):
    resume_id: str
    job_description: str


class JobMatchResult(BaseModel):
    match_percentage: float
    missing_skills: List[str] = []
    missing_keywords: List[str] = []
    matching_strengths: List[str] = []
    recommendations: List[str] = []

class JDMatchRequest(BaseModel):
    resume_id: str
    job_description: str

class JDMatchResponse(BaseModel):
    match_percentage: float
    total_jd_keywords: int
    matching_keywords_count: int
    matching_keywords: List[str]
    missing_keywords: List[str]
    missing_skills: List[str]
    strengths: List[str]

class BulletOptimizeRequest(BaseModel):
    bullet: str

class BulletOptimizeResponse(BaseModel):
    original: str
    optimized: str
    