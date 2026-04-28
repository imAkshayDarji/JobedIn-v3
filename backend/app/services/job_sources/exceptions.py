# --- Adapter-generic exceptions (used by API source adapters) ---

class JobSourceError(Exception):
    """Base exception for all job source failures."""


class JobSourceRateLimitError(JobSourceError):
    """API rate limit exceeded (HTTP 429 or source-specific signal)."""

    def __init__(self, source: str, retry_after: int | None = None) -> None:
        self.source = source
        self.retry_after = retry_after
        msg = f"Rate limited by {source}"
        if retry_after:
            msg += f" (retry after {retry_after}s)"
        super().__init__(msg)


class JobSourceAuthError(JobSourceError):
    """Authentication failed (invalid API key / credentials)."""

    def __init__(self, source: str, detail: str = "") -> None:
        self.source = source
        msg = f"Auth failed for {source}"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


class JobSourceTimeoutError(JobSourceError):
    """Request to job source timed out."""

    def __init__(self, source: str, url: str = "") -> None:
        self.source = source
        self.url = url
        msg = f"Request to {source} timed out"
        if url:
            msg += f" ({url})"
        super().__init__(msg)


class JobSourceResponseError(JobSourceError):
    """Unexpected response (HTTP 5xx, malformed JSON, empty body)."""

    def __init__(self, source: str, status_code: int | None = None, detail: str = "") -> None:
        self.source = source
        self.status_code = status_code
        msg = f"Bad response from {source}"
        if status_code:
            msg += f" (HTTP {status_code})"
        if detail:
            msg += f": {detail}"
        super().__init__(msg)


# --- LinkedIn-specific exceptions (used by Playwright scraper) ---

class LinkedInDiscoveryError(Exception):
    """Base exception for LinkedIn scraping failures."""


class LinkedInAuthError(LinkedInDiscoveryError):
    """Login failed (wrong credentials, account locked)."""


class LinkedInCAPTCHAError(LinkedInDiscoveryError):
    """CAPTCHA detected during scraping."""


class LinkedInScrapeError(LinkedInDiscoveryError):
    """Page structure changed, extraction failed."""


class LinkedInTimeoutError(LinkedInDiscoveryError):
    """Page load or action timed out."""


class LinkedInSessionCooldownError(LinkedInDiscoveryError):
    """Session cooldown has not expired yet."""

    def __init__(self, remaining_hours: float) -> None:
        self.remaining_hours = remaining_hours
        super().__init__(
            f"LinkedIn session cooldown active. Try again in {remaining_hours:.1f} hours."
        )
