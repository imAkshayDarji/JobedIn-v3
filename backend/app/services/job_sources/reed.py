import base64
import logging

import httpx

from app.config import settings
from app.services.job_sources.base import JobSourceAdapter
from app.services.job_sources.exceptions import JobSourceAuthError

logger = logging.getLogger(__name__)

BASE_URL = "https://www.reed.co.uk/api/1.0/search"


def _reed_plain_api_key() -> str:
    direct = (settings.REED_API_KEY or "").strip()
    if direct:
        return direct
    rapid = (settings.RAPIDAPI_KEY or "").strip()
    if rapid:
        return rapid
    return (settings.JSEARCH_API_KEY or "").strip()


def _reed_auth_header() -> str | None:
    """Return full Authorization header value ('Basic …') if credentials are configured."""
    legacy = (settings.REED_BASIC_TOKEN or "").strip()
    if legacy:
        decoded = legacy.lstrip()
        if decoded.lower().startswith("basic "):
            return decoded.strip()
        return f"Basic {decoded.strip()}"

    plain = _reed_plain_api_key().strip()
    if not plain:
        return None
    token = base64.b64encode(f"{plain}:".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


class ReedAdapter(JobSourceAdapter):
    @property
    def source_name(self) -> str:
        return "reed"

    def build_url(self, keywords: str, location: str | None) -> str:
        return BASE_URL

    def build_params(self, keywords: str, location: str | None) -> dict | None:
        if not _reed_auth_header():
            raise JobSourceAuthError(self.source_name)
        params: dict[str, str] = {
            "keywords": keywords,
            "resultsToTake": "20",
        }
        if location:
            params["locationName"] = location
        return params

    def build_headers(self) -> dict | None:
        header = _reed_auth_header()
        if not header:
            raise JobSourceAuthError(self.source_name)
        return {"Authorization": header}

    async def fetch_detail(
        self,
        client: httpx.AsyncClient,
        external_id: str,
    ) -> dict | None:
        detail_url = f"https://www.reed.co.uk/api/1.0/jobs/{external_id}"
        headers = self.build_headers()
        data = await self._make_request(client, detail_url, headers=headers)

        title = (data.get("jobTitle") or "").strip()
        company = (data.get("employerName") or "").strip()
        if not title or not company:
            return None

        description = data.get("jobDescription") or None
        location = (data.get("locationName") or "").strip()
        source_url = data.get("jobUrl") or ""
        salary_min = data.get("minimumSalary")
        salary_max = data.get("maximumSalary")
        remote_policy = None
        if data.get("remoteWorking"):
            remote_policy = "remote"

        return {
            "external_id": str(external_id),
            "title": title,
            "company": company,
            "location": location or None,
            "source_url": source_url,
            "description": description,
            "salary_min": int(salary_min) if salary_min else None,
            "salary_max": int(salary_max) if salary_max else None,
            "salary_currency": "GBP",
            "job_type": None,
            "remote_policy": remote_policy,
        }

    def _map_response(self, data: dict) -> list[dict]:
        raw_jobs = data.get("results") or []
        jobs: list[dict] = []

        for raw in raw_jobs:
            if not isinstance(raw, dict):
                continue

            title = (raw.get("jobTitle") or "").strip()
            company = (raw.get("employerName") or "").strip()
            if not title or not company:
                continue

            external_id = raw.get("jobId")
            if external_id is None:
                continue

            description = raw.get("jobDescription") or None
            location = (raw.get("locationName") or "").strip()
            source_url = raw.get("jobUrl") or ""

            salary_min = raw.get("minimumSalary")
            salary_max = raw.get("maximumSalary")

            remote_policy = None
            if raw.get("remoteWorking"):
                remote_policy = "remote"

            jobs.append({
                "external_id": str(external_id),
                "title": title,
                "company": company,
                "location": location or None,
                "source_url": source_url,
                "description": description,
                "salary_min": int(salary_min) if salary_min else None,
                "salary_max": int(salary_max) if salary_max else None,
                "salary_currency": "GBP",
                "job_type": None,
                "remote_policy": remote_policy,
            })

        return jobs
