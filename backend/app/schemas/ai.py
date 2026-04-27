from pydantic import BaseModel, Field


class SkillRequirement(BaseModel):
    name: str
    importance: str = Field(default="required", pattern="^(required|preferred|nice_to_have)$")


class JobAnalysis(BaseModel):
    required_skills: list[SkillRequirement]
    responsibilities: list[str]
    keywords: list[str]
    tone: str = Field(default="professional")
    company_values: list[str] = Field(default_factory=list)
    experience_level_required: str | None = Field(default=None)


class SkillMatch(BaseModel):
    skill: str
    candidate_has: bool
    match_quality: str = Field(default="exact", pattern="^(exact|partial|missing)$")


class GapAnalysis(BaseModel):
    matches: list[SkillMatch]
    strengths: list[str]
    gaps: list[str]
    match_score: float = Field(ge=0, le=100)
    relevant_experience_years: float | None = Field(default=None)
    summary: str


class ResumeBulletPoint(BaseModel):
    text: str
    keywords_included: list[str] = Field(default_factory=list)


class ResumeSection(BaseModel):
    title: str
    order: int = Field(ge=0)
    bullet_points: list[ResumeBulletPoint] = Field(default_factory=list)
    content: str | None = Field(default=None)


class ResumeContent(BaseModel):
    sections: list[ResumeSection]
    target_keywords_covered: list[str]
    overall_keyword_coverage: float = Field(ge=0, le=100)


class ATSKeywordCheck(BaseModel):
    keyword: str
    found: bool
    count: int = Field(default=0)


class ATSSectionCheck(BaseModel):
    section: str
    present: bool
    score: float = Field(default=0)


class ATSResult(BaseModel):
    overall_score: float = Field(ge=0, le=100)
    keyword_score: float = Field(ge=0, le=100)
    section_score: float = Field(ge=0, le=100)
    keyword_checks: list[ATSKeywordCheck] = Field(default_factory=list)
    section_checks: list[ATSSectionCheck] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class CoverLetterParagraph(BaseModel):
    heading: str | None = None
    body: str


class CoverLetterContent(BaseModel):
    paragraphs: list[CoverLetterParagraph]
    tone_used: str
    keywords_addressed: list[str] = Field(default_factory=list)
    full_text: str
