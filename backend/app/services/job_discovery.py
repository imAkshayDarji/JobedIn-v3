import hashlib
import logging
import uuid
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.base import JobSource
from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.services.credential_crypto import decrypt_value
from app.services.job_sources.exceptions import LinkedInSessionCooldownError
from app.services.job_sources.linkedin import LinkedInDiscovery

logger = logging.getLogger(__name__)


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class IngestResult(BaseModel):
    new_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    total_found: int = 0
    errors: list[str] = []


class JobDiscoveryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def ingest_jobs(
        self,
        raw_jobs: list[dict],
        source: JobSource,
    ) -> IngestResult:
        result = IngestResult(total_found=len(raw_jobs))

        for raw in raw_jobs:
            normalized = self.normalize_job(raw, source)
            if normalized is None:
                result.skipped_count += 1
                continue

            external_id = normalized.get("external_id")
            if not external_id:
                logger.warning(f"Skipping job without external_id: {normalized.get('title')}")
                result.skipped_count += 1
                continue

            try:
                now_ts = _utc_naive_now()
                row = {
                    **normalized,
                    "id": uuid.uuid4(),
                    "created_at": now_ts,
                    "updated_at": now_ts,
                }
                insert_stmt = insert(Job).values(**row)
                upsert_stmt = insert_stmt.on_conflict_do_update(
                    constraint="uq_jobs_source_external_id",
                    set_={
                        "title": insert_stmt.excluded.title,
                        "company": insert_stmt.excluded.company,
                        "location": insert_stmt.excluded.location,
                        "source_url": insert_stmt.excluded.source_url,
                        "scraped_at": insert_stmt.excluded.scraped_at,
                        "updated_at": now_ts,
                    },
                )
                existing = await self.session.execute(
                    select(Job.id).where(
                        Job.source == source,
                        Job.external_id == external_id,
                    )
                )
                was_update = existing.scalar_one_or_none() is not None
                await self.session.execute(upsert_stmt)
                if was_update:
                    result.updated_count += 1
                else:
                    result.new_count += 1
            except Exception as exc:
                logger.warning(f"Failed to upsert job {external_id}: {exc}")
                result.errors.append(f"Upsert failed for {external_id}: {exc}")
                result.skipped_count += 1

        await self.session.commit()
        return result

    async def run_linkedin_discovery(
        self,
        user_id: uuid.UUID,
        keywords: list[str],
        location: str | None = None,
    ) -> IngestResult:
        result = await self.session.execute(
            select(CandidateProfile).where(CandidateProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            raise ValueError(f"CandidateProfile not found for user {user_id}")

        if not profile.linkedin_email or not profile.linkedin_password_encrypted:
            raise ValueError("LinkedIn credentials not configured")

        now = datetime.now(timezone.utc)
        if profile.linkedin_last_scraped_at:
            elapsed = now - profile.linkedin_last_scraped_at
            cooldown = timedelta(hours=settings.LINKEDIN_SESSION_COOLDOWN_HOURS)
            if elapsed < cooldown:
                remaining = cooldown - elapsed
                remaining_hours = remaining.total_seconds() / 3600
                raise LinkedInSessionCooldownError(remaining_hours=remaining_hours)

        password = decrypt_value(profile.linkedin_password_encrypted)
        if password is None:
            raise ValueError("Failed to decrypt LinkedIn password")

        all_raw_jobs: list[dict] = []
        search_errors: list[str] = []

        async with LinkedInDiscovery(headless=True) as scraper:
            await scraper.login(profile.linkedin_email, password)

            for keyword in keywords:
                try:
                    jobs = await scraper.search_jobs(
                        keywords=keyword,
                        location=location,
                        max_results=settings.LINKEDIN_SEARCH_MAX_RESULTS,
                    )
                    all_raw_jobs.extend(jobs)
                except Exception as exc:
                    logger.error(f"LinkedIn search failed for '{keyword}': {exc}")
                    search_errors.append(f"Search failed for '{keyword}': {exc}")

        ingest = await self.ingest_jobs(all_raw_jobs, JobSource.linkedin)
        ingest.errors.extend(search_errors)

        profile.linkedin_last_scraped_at = now
        self.session.add(profile)
        await self.session.commit()

        return ingest

    @staticmethod
    def normalize_job(raw: dict, source: JobSource) -> dict | None:
        title = (raw.get("title") or "").strip()
        company = (raw.get("company") or "").strip()

        if not title or not company:
            return None

        source_url = raw.get("source_url", "")
        external_id = raw.get("external_id")

        if not external_id and source == JobSource.linkedin:
            external_id = JobDiscoveryService.normalize_linkedin_url(source_url)

        if not external_id:
            source_identifier = f"{source.value}:{source_url}"
            external_id = hashlib.sha256(source_identifier.encode()).hexdigest()[:32]

        location = (raw.get("location") or "").strip() or None

        return {
            "source": source,
            "source_url": source_url or None,
            "external_id": external_id,
            "title": title.title(),
            "company": company,
            "location": location,
            "scraped_at": _utc_naive_now(),
        }

    @staticmethod
    def normalize_linkedin_url(url: str | None) -> str | None:
        import re

        if not url:
            return None

        view_match = re.search(r"/jobs/view/(\d+)", url)
        if view_match:
            return view_match.group(1)

        current_match = re.search(r"currentJobId=(\d+)", url)
        if current_match:
            return current_match.group(1)

        return None
