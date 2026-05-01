from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.ats_fillers.greenhouse import GreenhouseFiller
from app.services.ats_fillers.lever import LeverFiller
from app.services.ats_fillers.workday import WorkdayFiller

if TYPE_CHECKING:
    from app.services.ats_fillers import ATSFiller
    from app.services.browser_service import BrowserService


class ATSFillerRegistry:
    """Registry mapping platform names to concrete ATSFiller instances."""

    def __init__(self, browser_service: "BrowserService") -> None:
        self._fillers: dict[str, ATSFiller] = {
            "greenhouse": GreenhouseFiller(browser_service),
            "lever": LeverFiller(browser_service),
            "workday": WorkdayFiller(browser_service),
        }

    def get_filler(self, platform: str) -> "ATSFiller | None":
        return self._fillers.get(platform)

    def supported_platforms(self) -> list[str]:
        return list(self._fillers.keys())
