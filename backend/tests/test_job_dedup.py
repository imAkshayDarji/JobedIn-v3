"""Tests for within-batch fuzzy job deduplication."""

from app.services.job_dedup import deduplicate_jobs


class TestNoDuplicates:
    def test_no_duplicates(self):
        jobs = [
            {"title": "Software Engineer", "company": "Acme", "source": "jsearch", "external_id": "1"},
            {"title": "Data Scientist", "company": "Beta", "source": "adzuna", "external_id": "2"},
            {"title": "Product Manager", "company": "Gamma", "source": "remotive", "external_id": "3"},
        ]
        result = deduplicate_jobs(jobs)
        assert len(result) == 3
        for job in result:
            assert "alternate_sources" not in job


class TestExactDuplicate:
    def test_exact_duplicate(self):
        jobs = [
            {"title": "Software Engineer", "company": "Acme", "source": "jsearch", "external_id": "1"},
            {"title": "Software Engineer", "company": "Acme", "source": "adzuna", "external_id": "2"},
        ]
        result = deduplicate_jobs(jobs)
        assert len(result) == 1
        assert result[0]["source"] == "jsearch"
        assert result[0]["alternate_sources"] == [
            {"source": "adzuna", "external_id": "2", "source_url": None}
        ]


class TestFuzzyDuplicate:
    def test_fuzzy_duplicate_similar_title(self):
        jobs = [
            {"title": "Senior Software Engineer", "company": "Acme Inc", "source": "jsearch", "external_id": "1"},
            {"title": "Sr. Software Engineer", "company": "Acme Inc", "source": "adzuna", "external_id": "2"},
        ]
        result = deduplicate_jobs(jobs)
        assert len(result) == 1
        assert len(result[0].get("alternate_sources", [])) == 1


class TestEmptyInput:
    def test_empty_input(self):
        result = deduplicate_jobs([])
        assert result == []


class TestSingleSource:
    def test_single_source_no_cross_dedup(self):
        jobs = [
            {"title": "Engineer", "company": "Acme", "source": "jsearch", "external_id": "1"},
            {"title": "Designer", "company": "Beta", "source": "jsearch", "external_id": "2"},
            {"title": "Engineer", "company": "Acme", "source": "jsearch", "external_id": "3"},
        ]
        result = deduplicate_jobs(jobs)
        assert len(result) == 2
        duped = [j for j in result if "alternate_sources" in j]
        assert len(duped) == 1
        assert duped[0]["alternate_sources"][0]["external_id"] == "3"
