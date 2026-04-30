from pydantic import BaseModel


class ATSError(Exception):
    """Base exception for ATS operations."""


class ATSDetectionError(ATSError):
    """Raised when ATS platform detection fails."""


class ATSFormError(ATSError):
    """Raised when form filling encounters an error."""


class ATSSubmitError(ATSError):
    """Raised when form submission fails."""


class ATSTimeoutError(ATSError):
    """Raised when an ATS operation times out."""


class ATSCAPTCHAError(ATSError):
    """Raised when a CAPTCHA is detected on the page."""


class ApplyResult(BaseModel):
    """Result of an ATS application submission."""
    success: bool
    platform: str
    message: str = ""
    screenshot_path: str | None = None
    submitted_at: str | None = None
