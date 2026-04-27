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
