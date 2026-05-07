import logging

import httpx

from app.config import settings
from app.services.job_sources.base import JobSourceAdapter

logger = logging.getLogger(__name__)

BASE_URL = "https://api.adzuna.com/v1/api/jobs/gb/search/1"


class AdzunaAdapter(JobSourceAdapter):
    @property
    def source_name(self) -> str:
        return "adzuna"

    def build_url(self, keywords: str, location: str | None) -> str:
        return BASE_URL

    def build_params(self, keywords: str, location: str | None) -> dict | None:
        params: dict[str, str] = {
            "app_id": settings.ADZUNA_APP_ID,
            "app_key": settings.ADZUNA_APP_KEY,
            "what": keywords,
            "results_per_page": "20",
            "content-type": "application/json",
        }
        if location:
            params["where"] = location
        return params

    def build_headers(self) -> dict | None:
        return None

    async def fetch_detail(
        self,
        client: httpx.AsyncClient,
        external_id: str,
    ) -> dict | None:
        detail_url = f"https://api.adzuna.com/v1/api/jobs/gb/{external_id}"
        params: dict[str, str] = {
            "app_id": settings.ADZUNA_APP_ID,
            "app_key": settings.ADZUNA_APP_KEY,
            "content-type": "application/json",
        }
        data = await self._make_request(client, detail_url, params=params)

        title = (data.get("title") or "").strip()
        company_data = data.get("company", {})
        company = (company_data.get("display_name", "") if isinstance(company_data, dict) else str(company_data)).strip()
        if not title or not company:
            return None

        description = data.get("description") or None
        location_data = data.get("location", {})
        location = (location_data.get("display_name", "") if isinstance(location_data, dict) else "").strip()
        salary_min = data.get("salary_min")
        salary_max = data.get("salary_max")
        salary_currency = "GBP"
        source_url = data.get("redirect_url") or ""

        return {
            "external_id": str(external_id),
            "title": title,
            "company": company,
            "location": location or None,
            "source_url": source_url,
            "description": description,
            "salary_min": int(salary_min) if salary_min else None,
            "salary_max": int(salary_max) if salary_max else None,
            "salary_currency": salary_currency,
            "job_type": None,
            "remote_policy": None,
        }

    def _map_response(self, data: dict) -> list[dict]:
        raw_jobs = data.get("results") or []
        jobs: list[dict] = []

        for raw in raw_jobs:
            if not isinstance(raw, dict):
                continue

            title = (raw.get("title") or "").strip()
            company_data = raw.get("company", {})
            company = (company_data.get("display_name", "") if isinstance(company_data, dict) else str(company_data)).strip()
            if not title or not company:
                continue

            external_id = raw.get("id")
            if external_id is None:
                continue

            description = raw.get("description") or None
            location_data = raw.get("location", {})
            location = (location_data.get("display_name", "") if isinstance(location_data, dict) else "").strip()

            salary_min = raw.get("salary_min")
            salary_max = raw.get("salary_max")
            salary_currency = raw.get("salary_is_daily") and "GBP" or "GBP"

            remote_policy = None
            latitude = raw.get("latitude")
            longitude = raw.get("longitude")

            source_url = raw.get("redirect_url") or ""

            jobs.append({
                "external_id": str(external_id),
                "title": title,
                "company": company,
                "location": location or None,
                "source_url": source_url,
                "description": description,
                "salary_min": int(salary_min) if salary_min else None,
                "salary_max": int(salary_max) if salary_max else None,
                "salary_currency": salary_currency,
                "job_type": None,
                "remote_policy": remote_policy,
            })

        return jobs
