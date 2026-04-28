import logging

from app.config import settings
from app.services.job_sources.base import JobSourceAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://jsearch.p.rapidapi.com/search"


class JSearchAdapter(JobSourceAdapter):
    @property
    def source_name(self) -> str:
        return "jsearch"

    def build_url(self, keywords: str, location: str | None) -> str:
        return BASE_URL

    def build_params(self, keywords: str, location: str | None) -> dict | None:
        query = keywords
        if location:
            query += f", {location}"
        return {
            "query": query,
            "num_pages": "1",
        }

    def build_headers(self) -> dict | None:
        return {
            "X-RapidAPI-Key": settings.JSEARCH_API_KEY,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }

    def _map_response(self, data: dict) -> list[dict]:
        raw_jobs = data.get("data") or []
        jobs: list[dict] = []

        for raw in raw_jobs:
            if not isinstance(raw, dict):
                continue

            title = (raw.get("job_title") or "").strip()
            company = (raw.get("employer_name") or "").strip()
            if not title or not company:
                continue

            external_id = raw.get("job_id") or ""
            if not external_id:
                continue

            description = raw.get("job_description") or None
            location = raw.get("job_city") or raw.get("job_country") or ""
            if raw.get("job_state"):
                location = f"{raw.get('job_city', '')}, {raw['job_state']}".strip(", ")

            salary_min = raw.get("job_min_salary")
            salary_max = raw.get("job_max_salary")
            salary_currency = raw.get("job_salary_currency") or "USD"
            job_type = raw.get("job_employment_type") or None
            remote = raw.get("job_is_remote")

            remote_policy = None
            if remote is True:
                remote_policy = "remote"
            elif remote is False:
                remote_policy = "onsite"

            source_url = raw.get("job_apply_link") or raw.get("job_google_link") or ""

            jobs.append({
                "external_id": str(external_id),
                "title": title,
                "company": company,
                "location": location.strip() or None,
                "source_url": source_url,
                "description": description,
                "salary_min": int(salary_min) if salary_min else None,
                "salary_max": int(salary_max) if salary_max else None,
                "salary_currency": salary_currency,
                "job_type": job_type,
                "remote_policy": remote_policy,
            })

        return jobs
