"""Schema validation edge-case tests for all request schemas."""

import uuid

import pytest
from pydantic import ValidationError

from app.schemas.apply import (
    ApplyBulkRequest,
    ApplySingleRequest,
    ATSDetectRequest,
)
from app.schemas.cover_letter import (
    CoverLetterGenerateManualRequest,
    CoverLetterGenerateRequest,
)
from app.schemas.onboarding import (
    OnboardingPersonalInfo,
    OnboardingSaveRequest,
    OnboardingSkill,
    OnboardingTargetRole,
)
from app.schemas.resume import (
    ResumeGenerateManualRequest,
    ResumeGenerateRequest,
)


# --- Apply schemas ---


class TestApplySingleRequest:
    def test_accepts_valid_uuid(self):
        req = ApplySingleRequest(application_id=uuid.uuid4())
        assert req.application_id is not None

    def test_rejects_missing_application_id(self):
        with pytest.raises(ValidationError):
            ApplySingleRequest()  # type: ignore[call-arg]


class TestApplyBulkRequest:
    def test_accepts_up_to_10_ids(self):
        ids = [uuid.uuid4() for _ in range(10)]
        req = ApplyBulkRequest(application_ids=ids)
        assert len(req.application_ids) == 10

    def test_rejects_more_than_10_ids(self):
        ids = [uuid.uuid4() for _ in range(11)]
        with pytest.raises(ValidationError):
            ApplyBulkRequest(application_ids=ids)

    def test_accepts_empty_list_as_valid(self):
        """Empty list passes Pydantic validation (no min_length constraint)."""
        req = ApplyBulkRequest(application_ids=[])
        assert len(req.application_ids) == 0

    def test_accepts_single_id(self):
        req = ApplyBulkRequest(application_ids=[uuid.uuid4()])
        assert len(req.application_ids) == 1


class TestATSDetectRequest:
    def test_accepts_job_id_only(self):
        req = ATSDetectRequest(job_id=uuid.uuid4())
        assert req.apply_url is None

    def test_accepts_job_id_and_url(self):
        req = ATSDetectRequest(job_id=uuid.uuid4(), apply_url="https://example.com")
        assert req.apply_url == "https://example.com"


# --- Resume schemas ---


class TestResumeGenerateRequest:
    def test_accepts_job_id(self):
        req = ResumeGenerateRequest(job_id=uuid.uuid4())
        assert req.job_id is not None

    def test_accepts_job_description(self):
        req = ResumeGenerateRequest(job_description="Senior Python Developer role...")
        assert req.job_description is not None

    def test_rejects_neither_job_id_nor_description(self):
        with pytest.raises(ValidationError, match="At least one"):
            ResumeGenerateRequest()

    def test_accepts_both_fields(self):
        req = ResumeGenerateRequest(
            job_id=uuid.uuid4(),
            job_description="A great job",
        )
        assert req.job_id is not None
        assert req.job_description == "A great job"

    def test_rejects_oversized_job_description(self):
        with pytest.raises(ValidationError):
            ResumeGenerateRequest(job_description="x" * 10001)


class TestResumeGenerateManualRequest:
    def test_accepts_valid_description(self):
        req = ResumeGenerateManualRequest(job_description="x" * 50)
        assert len(req.job_description) == 50

    def test_rejects_short_description(self):
        with pytest.raises(ValidationError):
            ResumeGenerateManualRequest(job_description="x" * 49)

    def test_rejects_missing_description(self):
        with pytest.raises(ValidationError):
            ResumeGenerateManualRequest()  # type: ignore[call-arg]

    def test_optional_fields_default_to_none(self):
        req = ResumeGenerateManualRequest(job_description="x" * 50)
        assert req.company_name is None
        assert req.job_title is None

    def test_company_name_max_length(self):
        with pytest.raises(ValidationError):
            ResumeGenerateManualRequest(
                job_description="x" * 50,
                company_name="x" * 201,
            )


# --- Cover Letter schemas ---


class TestCoverLetterGenerateRequest:
    def test_accepts_job_id(self):
        req = CoverLetterGenerateRequest(job_id=uuid.uuid4())
        assert req.tone == "professional"

    def test_accepts_valid_tones(self):
        for tone in ("professional", "casual", "enthusiastic"):
            req = CoverLetterGenerateRequest(
                job_id=uuid.uuid4(),
                tone=tone,
            )
            assert req.tone == tone

    def test_rejects_invalid_tone(self):
        with pytest.raises(ValidationError):
            CoverLetterGenerateRequest(
                job_id=uuid.uuid4(),
                tone="aggressive",
            )

    def test_rejects_neither_source(self):
        with pytest.raises(ValidationError, match="At least one"):
            CoverLetterGenerateRequest()


class TestCoverLetterGenerateManualRequest:
    def test_accepts_valid_input(self):
        req = CoverLetterGenerateManualRequest(job_description="x" * 50)
        assert req.tone == "professional"

    def test_rejects_short_description(self):
        with pytest.raises(ValidationError):
            CoverLetterGenerateManualRequest(job_description="short")

    def test_rejects_invalid_tone(self):
        with pytest.raises(ValidationError):
            CoverLetterGenerateManualRequest(
                job_description="x" * 50,
                tone="invalid",
            )


# --- Onboarding schemas ---


class TestOnboardingPersonalInfo:
    def test_accepts_valid_minimal(self):
        req = OnboardingPersonalInfo(
            first_name="John",
            last_name="Doe",
        )
        assert req.first_name == "John"

    def test_rejects_empty_first_name(self):
        with pytest.raises(ValidationError):
            OnboardingPersonalInfo(first_name="", last_name="Doe")

    def test_rejects_oversized_first_name(self):
        with pytest.raises(ValidationError):
            OnboardingPersonalInfo(first_name="x" * 101, last_name="Doe")

    def test_accepts_unicode_names(self):
        req = OnboardingPersonalInfo(
            first_name="José",
            last_name="García",
        )
        assert req.first_name == "José"

    def test_all_optional_fields_default(self):
        req = OnboardingPersonalInfo(first_name="Jane", last_name="Smith")
        assert req.headline is None
        assert req.summary is None
        assert req.location is None
        assert req.phone is None


class TestOnboardingSaveRequest:
    def test_accepts_valid_request(self):
        req = OnboardingSaveRequest(
            personal_info=OnboardingPersonalInfo(
                first_name="Test",
                last_name="User",
            ),
        )
        assert req.personal_info.first_name == "Test"

    def test_default_empty_arrays(self):
        req = OnboardingSaveRequest(
            personal_info=OnboardingPersonalInfo(
                first_name="Test",
                last_name="User",
            ),
        )
        assert req.target_roles == []
        assert req.skills == []
        assert req.education == []
        assert req.experience == []

    def test_with_all_sections(self):
        req = OnboardingSaveRequest(
            personal_info=OnboardingPersonalInfo(
                first_name="Test",
                last_name="User",
            ),
            target_roles=[
                OnboardingTargetRole(title="Software Engineer", keywords="python, react"),
            ],
            skills=[
                OnboardingSkill(name="Python", category="Programming"),
            ],
        )
        assert len(req.target_roles) == 1
        assert len(req.skills) == 1


class TestOnboardingTargetRole:
    def test_rejects_empty_title(self):
        with pytest.raises(ValidationError):
            OnboardingTargetRole(title="")

    def test_rejects_oversized_title(self):
        with pytest.raises(ValidationError):
            OnboardingTargetRole(title="x" * 201)

    def test_priority_bounds(self):
        with pytest.raises(ValidationError):
            OnboardingTargetRole(title="Dev", priority=-1)
        with pytest.raises(ValidationError):
            OnboardingTargetRole(title="Dev", priority=11)

    def test_valid_priority(self):
        req = OnboardingTargetRole(title="Dev", priority=5)
        assert req.priority == 5


class TestOnboardingSkill:
    def test_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            OnboardingSkill(name="")

    def test_rejects_oversized_name(self):
        with pytest.raises(ValidationError):
            OnboardingSkill(name="x" * 101)

    def test_accepts_minimal(self):
        req = OnboardingSkill(name="TypeScript")
        assert req.category is None
        assert req.proficiency is None
