import logging

from app.config import settings
from app.services.job_sources.base import JobSourceAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://remotive.com/api/remote-jobs/search"


class RemotiveAdapter(JobSourceAdapter):
    @property
    def source_name(self) -> str:
        return "remotive"

    def build_url(self, keywords: str, location: str | None) -> str:
        return BASE_URL

    def build_params(self, keywords: str, location: str | None) -> dict | None:
        params: dict[str, str] = {
            "search": keywords,
            "limit": "20",
        }
        if settings.REMOTIVE_API_KEY:
            params["api_key"] = settings.REMOTIVE_API_KEY
        return params

    def build_headers(self) -> dict | None:
        return {"Accept": "application/json"}

    def _map_response(self, data: dict) -> list[dict]:
        raw_jobs = data.get("jobs") or []
        jobs: list[dict] = []

        for raw in raw_jobs:
            if not isinstance(raw, dict):
                continue

            title = (raw.get("title") or "").strip()
            company = (raw.get("company_name") or "").strip()
            if not title or not company:
                continue

            external_id = raw.get("id")
            if external_id is None:
                continue

            description = raw.get("description") or None
            location = (raw.get("candidate_required_location") or "").strip()
            job_type = raw.get("job_type") or None
            source_url = raw.get("url") or ""

            salary_raw = raw.get("salary") or ""
            salary_min = None
            salary_max = None
            if salary_raw:
                try:
                    salary_min = int(float(salary_raw.replace(",", "").split("-")[0].strip()))
                except (ValueError, IndexError):
                    pass
                try:
                    max_part = salary_raw.replace(",", "").split("-")[1].strip()
                    salary_max = int(float(max_part))
                except (ValueError, IndexError):
                    pass

            tags = raw.get("tags") or []

            jobs.append({
                "external_id": str(external_id),
                "title": title,
                "company": company,
                "location": location or None,
                "source_url": source_url,
                "description": description,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "salary_currency": "USD",
                "job_type": job_type,
                "remote_policy": "remote",
            })

        return jobs
