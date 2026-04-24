"""Seed script for JobedIn V3 — inserts test data into Docker Postgres."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, datetime

from sqlmodel import select

from app.database import async_session_factory
from app.models import (
    Application,
    ApplicationStatus,
    CandidateProfile,
    Education,
    Experience,
    ExperienceLevel,
    Job,
    JobSource,
    Skill,
    TargetRole,
)

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"

TRUNCATE_ORDER = [
    "interview_sessions",
    "interview_preps",
    "cover_letters",
    "resumes",
    "applications",
    "certifications",
    "languages",
    "target_roles",
    "skills",
    "projects",
    "experiences",
    "educations",
    "jobs",
    "candidate_profiles",
]


async def truncate_all(session) -> None:
    from sqlalchemy import text

    for table in TRUNCATE_ORDER:
        await session.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))


async def seed() -> None:
    async with async_session_factory() as session:
        await truncate_all(session)
        await session.commit()

        candidate = CandidateProfile(
            user_id=TEST_USER_ID,
            first_name="John",
            last_name="Doe",
            headline="Full-Stack Software Engineer",
            summary="Experienced software engineer with 5+ years building scalable web applications.",
            location="San Francisco, CA",
            phone="+1-555-0123",
            linkedin_url="https://linkedin.com/in/johndoe",
            github_url="https://github.com/johndoe",
            experience_level=ExperienceLevel.mid,
        )
        session.add(candidate)
        await session.flush()

        educations = [
            Education(
                candidate_id=candidate.id,
                institution="University of California, Berkeley",
                degree="Bachelor of Science",
                field_of_study="Computer Science",
                start_date=date(2016, 9, 1),
                end_date=date(2020, 5, 15),
                grade="3.8 GPA",
            ),
            Education(
                candidate_id=candidate.id,
                institution="Stanford University",
                degree="Master of Science",
                field_of_study="Artificial Intelligence",
                start_date=date(2020, 9, 1),
                end_date=date(2022, 6, 15),
            ),
        ]
        session.add_all(educations)
        await session.flush()

        experiences = [
            Experience(
                candidate_id=candidate.id,
                company="TechCorp Inc.",
                title="Senior Software Engineer",
                location="San Francisco, CA",
                start_date=date(2022, 7, 1),
                description="Led backend team building microservices for financial platform.",
                is_current=True,
            ),
            Experience(
                candidate_id=candidate.id,
                company="StartupXYZ",
                title="Software Engineer",
                location="Remote",
                start_date=date(2020, 6, 1),
                end_date=date(2022, 6, 30),
                description="Full-stack development on React/Python stack.",
                is_current=False,
            ),
        ]
        session.add_all(experiences)
        await session.flush()

        skills = [
            Skill(candidate_id=candidate.id, name="Python", category="Programming", proficiency="Expert"),
            Skill(candidate_id=candidate.id, name="TypeScript", category="Programming", proficiency="Advanced"),
            Skill(candidate_id=candidate.id, name="React", category="Framework", proficiency="Advanced"),
            Skill(candidate_id=candidate.id, name="PostgreSQL", category="Database", proficiency="Advanced"),
            Skill(candidate_id=candidate.id, name="Docker", category="Tool", proficiency="Intermediate"),
        ]
        session.add_all(skills)
        await session.flush()

        target_roles = [
            TargetRole(candidate_id=candidate.id, title="Senior Software Engineer", priority=0, keywords="backend, python, fastapi"),
            TargetRole(candidate_id=candidate.id, title="Staff Engineer", priority=1, keywords="architecture, leadership"),
        ]
        session.add_all(target_roles)
        await session.flush()

        jobs = [
            Job(
                source=JobSource.linkedin,
                source_url="https://linkedin.com/jobs/view/123456",
                external_id="li-123456",
                title="Senior Software Engineer",
                company="Acme Corp",
                description="We are looking for a senior engineer to join our platform team.",
                salary_min=150000,
                salary_max=200000,
                salary_currency="USD",
                location="San Francisco, CA",
                experience_level=ExperienceLevel.senior,
                job_type="full-time",
                remote_policy="hybrid",
                ats_platform="greenhouse",
                apply_url="https://boards.greenhouse.io/acme/jobs/123",
                scraped_at=datetime.now(),
            ),
            Job(
                source=JobSource.adzuna,
                source_url="https://adzuna.com/jobs/789",
                external_id="adz-789",
                title="Python Developer",
                company="DataFlow Inc.",
                description="Python developer for data pipeline team.",
                salary_min=130000,
                salary_max=170000,
                salary_currency="USD",
                location="Remote",
                experience_level=ExperienceLevel.mid,
                job_type="full-time",
                remote_policy="remote",
                scraped_at=datetime.now(),
            ),
            Job(
                source=JobSource.jsearch,
                source_url="https://jsearch.com/listing/456",
                external_id="js-456",
                title="Backend Engineer",
                company="CloudNine Systems",
                description="Build cloud-native APIs with FastAPI and PostgreSQL.",
                salary_min=140000,
                salary_max=180000,
                salary_currency="USD",
                location="New York, NY",
                experience_level=ExperienceLevel.mid,
                job_type="full-time",
                remote_policy="onsite",
                scraped_at=datetime.now(),
            ),
        ]
        session.add_all(jobs)
        await session.flush()

        applications = [
            Application(
                user_id=TEST_USER_ID,
                job_id=jobs[0].id,
                status=ApplicationStatus.saved,
            ),
            Application(
                user_id=TEST_USER_ID,
                job_id=jobs[1].id,
                status=ApplicationStatus.applied,
                applied_at=datetime.now(),
                notes="Applied via greenhouse. Strong match for Python skills.",
            ),
        ]
        session.add_all(applications)
        await session.commit()

        print("Seed data inserted successfully!")
        print(f"  CandidateProfiles: 1")
        print(f"  Educations: {len(educations)}")
        print(f"  Experiences: {len(experiences)}")
        print(f"  Skills: {len(skills)}")
        print(f"  TargetRoles: {len(target_roles)}")
        print(f"  Jobs: {len(jobs)}")
        print(f"  Applications: {len(applications)}")


if __name__ == "__main__":
    asyncio.run(seed())
