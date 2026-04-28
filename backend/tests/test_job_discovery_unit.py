from app.models.base import JobSource
from app.services.job_discovery import IngestResult, JobDiscoveryService


class TestNormalizeJob:
    def test_basic_normalization(self) -> None:
        raw = {
            "title": "  senior python developer  ",
            "company": "acme corp",
            "location": "London, UK",
            "source_url": "https://linkedin.com/jobs/view/1234567890",
            "external_id": "1234567890",
            "source": "linkedin",
        }
        result = JobDiscoveryService.normalize_job(raw, JobSource.linkedin)
        assert result is not None
        assert result["title"] == "Senior Python Developer"
        assert result["company"] == "acme corp"
        assert result["location"] == "London, UK"
        assert result["external_id"] == "1234567890"
        assert result["source"] == JobSource.linkedin

    def test_missing_title_returns_none(self) -> None:
        raw = {"title": "", "company": "acme", "source_url": "https://example.com"}
        assert JobDiscoveryService.normalize_job(raw, JobSource.linkedin) is None

    def test_missing_company_returns_none(self) -> None:
        raw = {"title": "dev", "company": "", "source_url": "https://example.com"}
        assert JobDiscoveryService.normalize_job(raw, JobSource.linkedin) is None

    def test_whitespace_only_title_returns_none(self) -> None:
        raw = {"title": "   ", "company": "acme", "source_url": "https://example.com"}
        assert JobDiscoveryService.normalize_job(raw, JobSource.linkedin) is None

    def test_missing_location_becomes_none(self) -> None:
        raw = {
            "title": "dev",
            "company": "acme",
            "source_url": "https://linkedin.com/jobs/view/123",
            "external_id": "123",
        }
        result = JobDiscoveryService.normalize_job(raw, JobSource.linkedin)
        assert result is not None
        assert result["location"] is None

    def test_uses_external_id_from_raw(self) -> None:
        raw = {
            "title": "dev",
            "company": "acme",
            "source_url": "https://linkedin.com/jobs/view/999",
            "external_id": "999",
        }
        result = JobDiscoveryService.normalize_job(raw, JobSource.linkedin)
        assert result is not None
        assert result["external_id"] == "999"

    def test_generates_hash_id_when_no_external_id(self) -> None:
        raw = {
            "title": "dev",
            "company": "acme",
            "source_url": "https://example.com/job/xyz",
        }
        result = JobDiscoveryService.normalize_job(raw, JobSource.adzuna)
        assert result is not None
        assert result["external_id"] is not None
        assert len(result["external_id"]) == 32

    def test_extracts_linkedin_id_from_url(self) -> None:
        raw = {
            "title": "dev",
            "company": "acme",
            "source_url": "https://linkedin.com/jobs/view/555555",
        }
        result = JobDiscoveryService.normalize_job(raw, JobSource.linkedin)
        assert result is not None
        assert result["external_id"] == "555555"

    def test_scraped_at_is_set(self) -> None:
        raw = {
            "title": "dev",
            "company": "acme",
            "source_url": "https://example.com",
            "external_id": "abc",
        }
        result = JobDiscoveryService.normalize_job(raw, JobSource.linkedin)
        assert result is not None
        assert result["scraped_at"] is not None

    def test_passes_through_description(self) -> None:
        raw = {
            "title": "dev",
            "company": "acme",
            "source_url": "https://example.com",
            "external_id": "abc",
            "description": "A great job",
        }
        result = JobDiscoveryService.normalize_job(raw, JobSource.adzuna)
        assert result is not None
        assert result["description"] == "A great job"

    def test_passes_through_salary(self) -> None:
        raw = {
            "title": "dev",
            "company": "acme",
            "source_url": "https://example.com",
            "external_id": "abc",
            "salary_min": 50000,
            "salary_max": 80000,
            "salary_currency": "GBP",
        }
        result = JobDiscoveryService.normalize_job(raw, JobSource.reed)
        assert result is not None
        assert result["salary_min"] == 50000
        assert result["salary_max"] == 80000
        assert result["salary_currency"] == "GBP"

    def test_passes_through_job_type_and_remote_policy(self) -> None:
        raw = {
            "title": "dev",
            "company": "acme",
            "source_url": "https://example.com",
            "external_id": "abc",
            "job_type": "full_time",
            "remote_policy": "remote",
        }
        result = JobDiscoveryService.normalize_job(raw, JobSource.remotive)
        assert result is not None
        assert result["job_type"] == "full_time"
        assert result["remote_policy"] == "remote"

    def test_passes_through_alternate_sources(self) -> None:
        raw = {
            "title": "dev",
            "company": "acme",
            "source_url": "https://example.com",
            "external_id": "abc",
            "alternate_sources": [{"source": "jsearch", "external_id": "xyz"}],
        }
        result = JobDiscoveryService.normalize_job(raw, JobSource.adzuna)
        assert result is not None
        assert len(result["alternate_sources"]) == 1


class TestNormalizeLinkedInUrl:
    def test_view_url(self) -> None:
        assert JobDiscoveryService.normalize_linkedin_url(
            "https://linkedin.com/jobs/view/1234567890"
        ) == "1234567890"

    def test_current_job_id(self) -> None:
        assert JobDiscoveryService.normalize_linkedin_url(
            "https://linkedin.com/jobs/search/?currentJobId=9876543210"
        ) == "9876543210"

    def test_empty_string(self) -> None:
        assert JobDiscoveryService.normalize_linkedin_url("") is None

    def test_no_match(self) -> None:
        assert JobDiscoveryService.normalize_linkedin_url(
            "https://linkedin.com/in/someone"
        ) is None

    def test_none_input(self) -> None:
        assert JobDiscoveryService.normalize_linkedin_url(None) is None


class TestIngestResult:
    def test_default_values(self) -> None:
        result = IngestResult()
        assert result.new_count == 0
        assert result.updated_count == 0
        assert result.skipped_count == 0
        assert result.total_found == 0
        assert result.errors == []

    def test_model_dump(self) -> None:
        result = IngestResult(new_count=5, total_found=10, errors=["some error"])
        data = result.model_dump()
        assert data["new_count"] == 5
        assert data["total_found"] == 10
        assert len(data["errors"]) == 1
