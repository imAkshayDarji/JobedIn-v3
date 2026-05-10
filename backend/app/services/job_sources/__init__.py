from app.config import settings
from app.services.job_sources.adzuna import AdzunaAdapter
from app.services.job_sources.base import JobSourceAdapter
from app.services.job_sources.exceptions import (
    JobSourceAuthError,
    JobSourceError,
    JobSourceRateLimitError,
    JobSourceResponseError,
    JobSourceTimeoutError,
    LinkedInAuthError,
    LinkedInCAPTCHAError,
    LinkedInDiscoveryError,
    LinkedInScrapeError,
    LinkedInSessionCooldownError,
    LinkedInTimeoutError,
)
from app.services.job_sources.jsearch import JSearchAdapter
from app.services.job_sources.linkedin import LinkedInDiscovery
from app.services.job_sources.reed import ReedAdapter
from app.services.job_sources.remotive import RemotiveAdapter

ADAPTER_REGISTRY: dict[str, type[JobSourceAdapter]] = {
    "jsearch": JSearchAdapter,
    "adzuna": AdzunaAdapter,
    "remotive": RemotiveAdapter,
    "reed": ReedAdapter,
}

API_SOURCE_NAMES = set(ADAPTER_REGISTRY.keys())


def disabled_api_sources() -> frozenset[str]:
    return frozenset(
        name.strip().lower()
        for name in settings.DISABLED_API_SOURCES.split(",")
        if name.strip()
    )


def active_api_sources() -> list[str]:
    blocked = disabled_api_sources()
    return [name for name in ADAPTER_REGISTRY if name not in blocked]

__all__ = [
    "ADAPTER_REGISTRY",
    "API_SOURCE_NAMES",
    "active_api_sources",
    "AdzunaAdapter",
    "disabled_api_sources",
    "JSearchAdapter",
    "JobSourceAdapter",
    "JobSourceAuthError",
    "JobSourceError",
    "JobSourceRateLimitError",
    "JobSourceResponseError",
    "JobSourceTimeoutError",
    "LinkedInAuthError",
    "LinkedInCAPTCHAError",
    "LinkedInDiscovery",
    "LinkedInDiscoveryError",
    "LinkedInScrapeError",
    "LinkedInSessionCooldownError",
    "LinkedInTimeoutError",
    "ReedAdapter",
    "RemotiveAdapter",
]
