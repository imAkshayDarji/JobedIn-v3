import asyncio
import logging
from abc import ABC, abstractmethod

import httpx

from app.services.job_sources.exceptions import (
    JobSourceAuthError,
    JobSourceRateLimitError,
    JobSourceResponseError,
    JobSourceTimeoutError,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 2
RETRY_DELAYS = [1, 2]
REQUEST_TIMEOUT = 15.0


class JobSourceAdapter(ABC):
    """Base class for API-based job source adapters.

    Subclasses must implement:
        - ``build_url``: construct the request URL given query params.
        - ``build_params``: build query-string params (dict or None).
        - ``build_headers``: build request headers (dict or None).
        - ``_map_response``: transform the raw JSON response into a list
          of job dicts with keys matching what ``normalize_job`` expects.
          Do NOT include ``source`` in the returned dicts.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        ...

    @abstractmethod
    def build_url(self, keywords: str, location: str | None) -> str:
        ...

    @abstractmethod
    def build_params(self, keywords: str, location: str | None) -> dict | None:
        ...

    @abstractmethod
    def build_headers(self) -> dict | None:
        ...

    @abstractmethod
    def _map_response(self, data: dict) -> list[dict]:
        ...

    async def fetch_jobs(
        self,
        client: httpx.AsyncClient,
        keywords: str,
        location: str | None = None,
    ) -> list[dict]:
        url = self.build_url(keywords, location)
        params = self.build_params(keywords, location)
        headers = self.build_headers()

        data = await self._make_request(client, url, params=params, headers=headers)
        return self._map_response(data)

    async def fetch_detail(
        self,
        client: httpx.AsyncClient,
        external_id: str,
    ) -> dict | None:
        """Fetch full details for a single job by its external ID.

        Returns a normalized job dict (same shape as _map_response items)
        or None if the detail endpoint is not available / the job was not found.
        Subclasses should override this if the source has a detail endpoint.
        """
        return None

    async def _make_request(
        self,
        client: httpx.AsyncClient,
        url: str,
        *,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> dict:
        last_exc: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await client.get(url, params=params, headers=headers)

                if response.status_code == 401:
                    raise JobSourceAuthError(self.source_name)

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise JobSourceRateLimitError(
                        self.source_name,
                        retry_after=int(retry_after) if retry_after else None,
                    )

                if response.status_code >= 500:
                    raise JobSourceResponseError(
                        self.source_name,
                        status_code=response.status_code,
                    )

                response.raise_for_status()
                return response.json()

            except JobSourceAuthError:
                raise

            except JobSourceRateLimitError:
                raise

            except httpx.TimeoutException as exc:
                last_exc = exc
                if attempt < MAX_RETRIES:
                    logger.warning(
                        f"Timeout from {self.source_name} (attempt {attempt + 1}/{MAX_RETRIES + 1}): {exc}"
                    )
                    await asyncio.sleep(RETRY_DELAYS[attempt])

            except JobSourceResponseError as exc:
                last_exc = exc
                if attempt < MAX_RETRIES:
                    logger.warning(
                        f"Server error from {self.source_name} (attempt {attempt + 1}/{MAX_RETRIES + 1}): {exc}"
                    )
                    await asyncio.sleep(RETRY_DELAYS[attempt])

            except Exception as exc:
                last_exc = exc
                if attempt < MAX_RETRIES:
                    logger.warning(
                        f"Request to {self.source_name} failed (attempt {attempt + 1}/{MAX_RETRIES + 1}): {exc}"
                    )
                    await asyncio.sleep(RETRY_DELAYS[attempt])

        if isinstance(last_exc, httpx.TimeoutException):
            raise JobSourceTimeoutError(self.source_name, url) from last_exc

        if isinstance(last_exc, JobSourceResponseError):
            raise last_exc

        raise JobSourceResponseError(
            self.source_name,
            detail=str(last_exc),
        ) from last_exc
