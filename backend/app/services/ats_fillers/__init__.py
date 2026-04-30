from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page

    from app.models.candidate import CandidateProfile
    from app.services.ats_fillers.exceptions import ApplyResult


class ATSFiller(ABC):
    """Abstract base class for ATS platform form fillers.

    Subclasses implement platform-specific form filling logic.
    Method `can_handle` (renamed from `detect` to avoid confusion with ATSDetector.detect)
    checks if the current page belongs to this ATS platform.
    """

    @abstractmethod
    async def can_handle(self, page: "Page") -> bool:
        """Return True if the page belongs to this ATS platform."""
        ...

    @abstractmethod
    async def fill(
        self,
        page: "Page",
        profile: "CandidateProfile",
        resume_path: str | None = None,
    ) -> None:
        """Fill the ATS application form with candidate profile data."""
        ...

    @abstractmethod
    async def submit(self, page: "Page") -> bool:
        """Submit the application form. Returns True if submission succeeded."""
        ...

    @abstractmethod
    async def verify(self, page: "Page") -> "ApplyResult":
        """Verify the submission result after form submission."""
        ...
