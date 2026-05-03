from unittest.mock import patch

import pytest

from app.services.job_sources.adzuna import AdzunaAdapter
from app.services.job_sources.jsearch import JSearchAdapter
from app.services.job_sources.reed import ReedAdapter
from app.services.job_sources.remotive import RemotiveAdapter


# ---------------------------------------------------------------------------
# Adzuna
# ---------------------------------------------------------------------------

@pytest.fixture
def adzuna():
    return AdzunaAdapter()


def test_adzuna_source_name(adzuna):
    assert adzuna.source_name == "adzuna"


def test_adzuna_build_url(adzuna):
    url = adzuna.build_url("python", "London")
    assert url == "https://api.adzuna.com/v1/api/jobs/gb/search/1"


@patch("app.services.job_sources.adzuna.settings")
def test_adzuna_build_params_with_location(mock_settings, adzuna):
    mock_settings.ADZUNA_APP_ID = "test-app-id"
    mock_settings.ADZUNA_APP_KEY = "test-app-key"

    params = adzuna.build_params("python developer", "London")

    assert params is not None
    assert params["what"] == "python developer"
    assert params["where"] == "London"
    assert params["app_id"] == "test-app-id"
    assert params["app_key"] == "test-app-key"
    assert params["results_per_page"] == "20"


@patch("app.services.job_sources.adzuna.settings")
def test_adzuna_build_params_without_location(mock_settings, adzuna):
    mock_settings.ADZUNA_APP_ID = "test-app-id"
    mock_settings.ADZUNA_APP_KEY = "test-app-key"

    params = adzuna.build_params("python developer", None)

    assert params is not None
    assert "where" not in params
    assert params["what"] == "python developer"


def test_adzuna_build_headers(adzuna):
    assert adzuna.build_headers() is None


def test_adzuna_map_response_success(adzuna):
    data = {
        "results": [
            {
                "id": 123,
                "title": "Software Engineer",
                "company": {"display_name": "TechCorp"},
                "description": "Job desc",
                "location": {"display_name": "London"},
                "salary_min": 40000,
                "salary_max": 60000,
                "redirect_url": "https://example.com/job",
            }
        ]
    }
    jobs = adzuna._map_response(data)

    assert len(jobs) == 1
    job = jobs[0]
    assert job["external_id"] == "123"
    assert job["title"] == "Software Engineer"
    assert job["company"] == "TechCorp"
    assert job["location"] == "London"
    assert job["salary_min"] == 40000
    assert job["salary_max"] == 60000
    assert job["salary_currency"] == "GBP"
    assert job["source_url"] == "https://example.com/job"


def test_adzuna_map_response_empty_results(adzuna):
    jobs = adzuna._map_response({"results": []})
    assert jobs == []


def test_adzuna_map_response_malformed(adzuna):
    data = {"results": [{}]}
    jobs = adzuna._map_response(data)
    assert jobs == []


def test_adzuna_map_response_non_dict_entry(adzuna):
    data = {"results": ["not a dict", 42, None]}
    jobs = adzuna._map_response(data)
    assert jobs == []


# ---------------------------------------------------------------------------
# JSearch
# ---------------------------------------------------------------------------

@pytest.fixture
def jsearch():
    return JSearchAdapter()


def test_jsearch_source_name(jsearch):
    assert jsearch.source_name == "jsearch"


def test_jsearch_build_url(jsearch):
    url = jsearch.build_url("python", "NYC")
    assert url == "https://jsearch.p.rapidapi.com/search"


@patch("app.services.job_sources.jsearch.settings")
def test_jsearch_build_params_with_location(mock_settings, jsearch):
    params = jsearch.build_params("python developer", "NYC")

    assert params is not None
    assert "python developer, NYC" == params["query"]
    assert params["num_pages"] == "1"


def test_jsearch_build_params_without_location(jsearch):
    params = jsearch.build_params("python developer", None)

    assert params is not None
    assert params["query"] == "python developer"


@patch("app.services.job_sources.jsearch.settings")
def test_jsearch_build_headers(mock_settings, jsearch):
    mock_settings.JSEARCH_API_KEY = "test-rapid-key"

    headers = jsearch.build_headers()

    assert headers is not None
    assert headers["X-RapidAPI-Key"] == "test-rapid-key"
    assert headers["X-RapidAPI-Host"] == "jsearch.p.rapidapi.com"


def test_jsearch_map_response_success(jsearch):
    data = {
        "data": [
            {
                "job_id": "abc123",
                "job_title": "Python Dev",
                "employer_name": "BigCo",
                "job_description": "Desc",
                "job_city": "NYC",
                "job_state": "NY",
                "job_min_salary": 80000,
                "job_max_salary": 120000,
                "job_salary_currency": "USD",
                "job_employment_type": "FULLTIME",
                "job_is_remote": True,
                "job_apply_link": "https://example.com",
            }
        ]
    }
    jobs = jsearch._map_response(data)

    assert len(jobs) == 1
    job = jobs[0]
    assert job["external_id"] == "abc123"
    assert job["title"] == "Python Dev"
    assert job["company"] == "BigCo"
    assert job["location"] == "NYC, NY"
    assert job["salary_min"] == 80000
    assert job["salary_max"] == 120000
    assert job["salary_currency"] == "USD"
    assert job["job_type"] == "FULLTIME"
    assert job["remote_policy"] == "remote"
    assert job["source_url"] == "https://example.com"


def test_jsearch_map_response_onsite(jsearch):
    data = {
        "data": [
            {
                "job_id": "xyz",
                "job_title": "Java Dev",
                "employer_name": "Corp",
                "job_is_remote": False,
            }
        ]
    }
    jobs = jsearch._map_response(data)
    assert jobs[0]["remote_policy"] == "onsite"


def test_jsearch_map_response_empty_data(jsearch):
    jobs = jsearch._map_response({"data": []})
    assert jobs == []


# ---------------------------------------------------------------------------
# Remotive
# ---------------------------------------------------------------------------

@pytest.fixture
def remotive():
    return RemotiveAdapter()


def test_remotive_source_name(remotive):
    assert remotive.source_name == "remotive"


def test_remotive_build_url(remotive):
    url = remotive.build_url("react", None)
    assert url == "https://remotive.com/api/remote-jobs/search"


@patch("app.services.job_sources.remotive.settings")
def test_remotive_build_params(mock_settings, remotive):
    mock_settings.REMOTIVE_API_KEY = ""

    params = remotive.build_params("react developer", None)

    assert params is not None
    assert params["search"] == "react developer"
    assert params["limit"] == "20"


def test_remotive_build_headers(remotive):
    headers = remotive.build_headers()
    assert headers is not None
    assert headers["Accept"] == "application/json"


def test_remotive_map_response_success(remotive):
    data = {
        "jobs": [
            {
                "id": 456,
                "title": "Frontend Dev",
                "company_name": "RemoteCo",
                "description": "Desc",
                "candidate_required_location": "Worldwide",
                "job_type": "full_time",
                "url": "https://remotive.com/job/456",
                "salary": "50000-80000",
                "tags": ["react", "typescript"],
            }
        ]
    }
    jobs = remotive._map_response(data)

    assert len(jobs) == 1
    job = jobs[0]
    assert job["external_id"] == "456"
    assert job["title"] == "Frontend Dev"
    assert job["company"] == "RemoteCo"
    assert job["location"] == "Worldwide"
    assert job["salary_min"] == 50000
    assert job["salary_max"] == 80000
    assert job["salary_currency"] == "USD"
    assert job["remote_policy"] == "remote"
    assert job["source_url"] == "https://remotive.com/job/456"


def test_remotive_map_response_no_salary(remotive):
    data = {
        "jobs": [
            {
                "id": 789,
                "title": "Backend Dev",
                "company_name": "NoSalaryCo",
                "url": "https://remotive.com/job/789",
            }
        ]
    }
    jobs = remotive._map_response(data)
    assert jobs[0]["salary_min"] is None
    assert jobs[0]["salary_max"] is None


def test_remotive_map_response_empty_jobs(remotive):
    jobs = remotive._map_response({"jobs": []})
    assert jobs == []


# ---------------------------------------------------------------------------
# Reed
# ---------------------------------------------------------------------------

@pytest.fixture
def reed():
    return ReedAdapter()


def test_reed_source_name(reed):
    assert reed.source_name == "reed"


def test_reed_build_url(reed):
    url = reed.build_url("data", "Manchester")
    assert url == "https://www.reed.co.uk/api/1.0/search"


@patch("app.services.job_sources.reed.settings")
def test_reed_build_params_with_location(mock_settings, reed):
    mock_settings.REED_API_KEY = "reed-key-123"

    params = reed.build_params("data scientist", "Manchester")

    assert params is not None
    assert params["keywords"] == "data scientist"
    assert params["locationName"] == "Manchester"
    assert params["resultsToTake"] == "20"


@patch("app.services.job_sources.reed.settings")
def test_reed_build_params_without_location(mock_settings, reed):
    mock_settings.REED_API_KEY = "reed-key-123"

    params = reed.build_params("data scientist", None)

    assert params is not None
    assert "locationName" not in params


@patch("app.services.job_sources.reed.settings")
def test_reed_build_headers(mock_settings, reed):
    mock_settings.REED_API_KEY = "reed-key-123"

    headers = reed.build_headers()

    assert headers is not None
    assert headers["Authorization"] == "Basic reed-key-123"


def test_reed_map_response_success(reed):
    data = {
        "results": [
            {
                "jobId": 789,
                "jobTitle": "Data Scientist",
                "employerName": "DataCorp",
                "jobDescription": "Desc",
                "locationName": "Manchester",
                "jobUrl": "https://reed.co.uk/job/789",
                "minimumSalary": 45000,
                "maximumSalary": 65000,
                "remoteWorking": False,
            }
        ]
    }
    jobs = reed._map_response(data)

    assert len(jobs) == 1
    job = jobs[0]
    assert job["external_id"] == "789"
    assert job["title"] == "Data Scientist"
    assert job["company"] == "DataCorp"
    assert job["location"] == "Manchester"
    assert job["salary_min"] == 45000
    assert job["salary_max"] == 65000
    assert job["salary_currency"] == "GBP"
    assert job["remote_policy"] is None
    assert job["source_url"] == "https://reed.co.uk/job/789"


def test_reed_map_response_remote_working(reed):
    data = {
        "results": [
            {
                "jobId": 999,
                "jobTitle": "Remote Dev",
                "employerName": "RemoteCorp",
                "jobUrl": "https://reed.co.uk/job/999",
                "remoteWorking": True,
            }
        ]
    }
    jobs = reed._map_response(data)

    assert jobs[0]["remote_policy"] == "remote"


def test_reed_map_response_empty_results(reed):
    jobs = reed._map_response({"results": []})
    assert jobs == []


# ---------------------------------------------------------------------------
# Adapter Registry
# ---------------------------------------------------------------------------

def test_adapter_registry_contains_all_sources():
    from app.services.job_sources import ADAPTER_REGISTRY

    assert "adzuna" in ADAPTER_REGISTRY
    assert "jsearch" in ADAPTER_REGISTRY
    assert "remotive" in ADAPTER_REGISTRY
    assert "reed" in ADAPTER_REGISTRY
    assert len(ADAPTER_REGISTRY) == 4


def test_all_adapters_instantiable_with_correct_source_names():
    from app.services.job_sources import ADAPTER_REGISTRY

    expected = {
        "adzuna": AdzunaAdapter,
        "jsearch": JSearchAdapter,
        "remotive": RemotiveAdapter,
        "reed": ReedAdapter,
    }
    for key, cls in expected.items():
        adapter = cls()
        assert adapter.source_name == key
        assert key in ADAPTER_REGISTRY
        assert ADAPTER_REGISTRY[key] is cls
