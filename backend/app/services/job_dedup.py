import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

TITLE_SIMILARITY_THRESHOLD = 0.85
COMPANY_SIMILARITY_THRESHOLD = 0.80


def _normalize_text(text: str | None) -> str:
    if not text:
        return ""
    return " ".join(text.lower().split())


def _are_similar(title_a: str, company_a: str, title_b: str, company_b: str) -> bool:
    if title_a == title_b and company_a == company_b:
        return True

    title_ratio = SequenceMatcher(None, title_a, title_b).ratio()
    company_ratio = SequenceMatcher(None, company_a, company_b).ratio()

    return title_ratio >= TITLE_SIMILARITY_THRESHOLD and company_ratio >= COMPANY_SIMILARITY_THRESHOLD


def deduplicate_jobs(jobs: list[dict]) -> list[dict]:
    """Deduplicate jobs within a single discovery batch.

    Keeps the first occurrence and adds an ``alternate_sources`` list
    to the kept job containing the source info of removed duplicates.

    Strategy:
    1. Exact match on (title, company) — case-insensitive
    2. Fuzzy match using SequenceMatcher on (title, company)
    """
    if not jobs:
        return []

    kept: list[dict] = []
    seen: list[tuple[str, str, dict]] = []

    for job in jobs:
        title_norm = _normalize_text(job.get("title"))
        company_norm = _normalize_text(job.get("company"))

        duplicate_of_idx: int | None = None

        for idx, (seen_title, seen_company, _seen_job) in enumerate(seen):
            if _are_similar(title_norm, company_norm, seen_title, seen_company):
                duplicate_of_idx = idx
                break

        if duplicate_of_idx is not None:
            _, _, original = seen[duplicate_of_idx]
            alt_sources = original.setdefault("alternate_sources", [])
            alt_sources.append({
                "source": job.get("source"),
                "external_id": job.get("external_id"),
                "source_url": job.get("source_url"),
            })
            logger.debug(
                f"Dedup: '{job.get('title')}' from {job.get('source')} "
                f"is duplicate of '{original.get('title')}' from {original.get('source')}"
            )
        else:
            seen.append((title_norm, company_norm, job))
            kept.append(job)

    return kept
