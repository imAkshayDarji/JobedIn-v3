import uuid
from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_async_session
from app.main import app
from app.models.candidate import CandidateProfile
from app.models.certification import Certification
from app.models.education import Education
from app.models.experience import Experience
from app.models.language import Language
from app.models.project import Project
from app.models.skill import Skill
from app.models.target_role import TargetRole
from tests.conftest import TEST_JWT_SECRET, mint_jwt


async def _get_test_session():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture(autouse=True)
def _override_db():
    app.dependency_overrides[get_async_session] = _get_test_session
    yield
    app.dependency_overrides.clear()


async def _setup_user_with_profile(client: AsyncClient, user_id: str | None = None) -> tuple[str, str]:
    uid = user_id or str(uuid.uuid4())
    token = mint_jwt(user_id=uid)
    headers = {"Authorization": f"Bearer {token}"}

    sync_resp = await client.post("/api/auth/sync-profile", headers=headers)
    assert sync_resp.status_code == 200

    onboarding_payload = {
        "personal_info": {
            "first_name": "Test",
            "last_name": "User",
            "headline": "Software Engineer",
            "experience_level": "senior",
        },
        "target_roles": [{"title": "Backend Engineer", "priority": 1}],
        "skills": [{"name": "Python", "category": "Programming", "proficiency": "expert"}],
        "education": [],
        "experience": [],
    }
    save_resp = await client.post(
        "/api/onboarding/save", json=onboarding_payload, headers=headers
    )
    assert save_resp.status_code == 200
    profile_id = save_resp.json()["profile_id"]

    return token, profile_id


# ── Auth ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_profile_me_unauthenticated_returns_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/profile/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_profile_full_unauthenticated_returns_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/profile/full")
    assert resp.status_code == 401


# ── GET /api/profile/full ──────────────────────────────


@pytest.mark.asyncio
async def test_get_profile_full_authenticated():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/profile/full", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["first_name"] == "Test"
    assert body["last_name"] == "User"
    assert body["headline"] == "Software Engineer"
    assert body["experience_level"] == "senior"
    assert "skills" in body
    assert len(body["skills"]) == 1
    assert body["skills"][0]["name"] == "Python"
    assert "education" in body
    assert "experience" in body
    assert "projects" in body
    assert "target_roles" in body
    assert "certifications" in body
    assert "languages" in body


@pytest.mark.asyncio
async def test_get_profile_full_no_profile():
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())
    token = mint_jwt(user_id=uid)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/profile/full",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_profile_full_empty_children():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/profile/full", headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["education"] == []
    assert body["experience"] == []
    assert body["projects"] == []
    assert body["certifications"] == []
    assert body["languages"] == []


# ── PATCH /api/profile/me ──────────────────────────────


@pytest.mark.asyncio
async def test_patch_profile_me_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.patch(
            "/api/profile/me",
            json={"headline": "Senior Backend Engineer", "location": "London, UK"},
            headers=headers,
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["first_name"] == "Test"
    assert body["last_name"] == "User"


@pytest.mark.asyncio
async def test_patch_profile_me_partial_update():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.patch(
            "/api/profile/me",
            json={"phone": "+44 7911 123456"},
            headers=headers,
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["first_name"] == "Test"
    assert body["last_name"] == "User"


@pytest.mark.asyncio
async def test_patch_profile_me_empty_body_returns_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.patch(
            "/api/profile/me",
            json={},
            headers=headers,
        )

    assert resp.status_code == 422


# ── Education CRUD ──────────────────────────────────────


@pytest.mark.asyncio
async def test_create_education_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/profile/educations",
            json={
                "institution": "MIT",
                "degree": "BSc Computer Science",
                "field_of_study": "Computer Science",
                "start_date": "2018-09-01",
                "end_date": "2022-06-30",
                "grade": "First Class",
            },
            headers=headers,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["institution"] == "MIT"
    assert body["degree"] == "BSc Computer Science"
    assert "id" in body
    assert "created_at" in body


@pytest.mark.asyncio
async def test_update_education_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/profile/educations",
            json={"institution": "MIT", "degree": "BSc"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        item_id = create_resp.json()["id"]

        update_resp = await client.put(
            f"/api/profile/educations/{item_id}",
            json={"institution": "Stanford"},
            headers=headers,
        )

    assert update_resp.status_code == 200
    body = update_resp.json()
    assert body["institution"] == "Stanford"
    assert body["degree"] == "BSc"


@pytest.mark.asyncio
async def test_delete_education_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/profile/educations",
            json={"institution": "MIT", "degree": "BSc"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        item_id = create_resp.json()["id"]

        delete_resp = await client.delete(
            f"/api/profile/educations/{item_id}",
            headers=headers,
        )

    assert delete_resp.status_code == 204


@pytest.mark.asyncio
async def test_update_education_ownership_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token1, _ = await _setup_user_with_profile(client)
        headers1 = {"Authorization": f"Bearer {token1}"}

        create_resp = await client.post(
            "/api/profile/educations",
            json={"institution": "MIT", "degree": "BSc"},
            headers=headers1,
        )
        assert create_resp.status_code == 201
        item_id = create_resp.json()["id"]

        token2, _ = await _setup_user_with_profile(client)
        headers2 = {"Authorization": f"Bearer {token2}"}

        update_resp = await client.put(
            f"/api/profile/educations/{item_id}",
            json={"institution": "Harvard"},
            headers=headers2,
        )

    assert update_resp.status_code == 404


# ── Skill CRUD ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_skill_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/profile/skills",
            json={"name": "TypeScript", "category": "Programming", "proficiency": "advanced"},
            headers=headers,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "TypeScript"
    assert "id" in body


@pytest.mark.asyncio
async def test_update_skill_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/profile/skills",
            json={"name": "TypeScript"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        item_id = create_resp.json()["id"]

        update_resp = await client.put(
            f"/api/profile/skills/{item_id}",
            json={"proficiency": "expert"},
            headers=headers,
        )

    assert update_resp.status_code == 200
    assert update_resp.json()["proficiency"] == "expert"


@pytest.mark.asyncio
async def test_delete_skill_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/profile/skills",
            json={"name": "TypeScript"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        item_id = create_resp.json()["id"]

        delete_resp = await client.delete(
            f"/api/profile/skills/{item_id}",
            headers=headers,
        )

    assert delete_resp.status_code == 204


# ── Project CRUD ────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_project_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/profile/projects",
            json={
                "name": "JobedIn",
                "description": "AI job search platform",
                "technologies": "Python, FastAPI, React",
                "url": "https://jobedin.com",
            },
            headers=headers,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "JobedIn"
    assert body["technologies"] == "Python, FastAPI, React"
    assert "id" in body


@pytest.mark.asyncio
async def test_update_project_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/profile/projects",
            json={"name": "JobedIn"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        item_id = create_resp.json()["id"]

        update_resp = await client.put(
            f"/api/profile/projects/{item_id}",
            json={"description": "Updated description"},
            headers=headers,
        )

    assert update_resp.status_code == 200
    assert update_resp.json()["description"] == "Updated description"


@pytest.mark.asyncio
async def test_delete_project_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/profile/projects",
            json={"name": "JobedIn"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        item_id = create_resp.json()["id"]

        delete_resp = await client.delete(
            f"/api/profile/projects/{item_id}",
            headers=headers,
        )

    assert delete_resp.status_code == 204


@pytest.mark.asyncio
async def test_update_project_ownership_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token1, _ = await _setup_user_with_profile(client)
        headers1 = {"Authorization": f"Bearer {token1}"}

        create_resp = await client.post(
            "/api/profile/projects",
            json={"name": "JobedIn"},
            headers=headers1,
        )
        assert create_resp.status_code == 201
        item_id = create_resp.json()["id"]

        token2, _ = await _setup_user_with_profile(client)
        headers2 = {"Authorization": f"Bearer {token2}"}

        update_resp = await client.put(
            f"/api/profile/projects/{item_id}",
            json={"name": "Hacked"},
            headers=headers2,
        )

    assert update_resp.status_code == 404


# ── Experience CRUD ──────────────────────────────────────


@pytest.mark.asyncio
async def test_create_experience_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/profile/experiences",
            json={
                "company": "Google",
                "title": "Senior Engineer",
                "location": "London",
                "start_date": "2020-01-01",
                "is_current": True,
            },
            headers=headers,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["company"] == "Google"
    assert body["is_current"] is True


@pytest.mark.asyncio
async def test_update_experience_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/profile/experiences",
            json={"company": "Google", "title": "Engineer"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        item_id = create_resp.json()["id"]

        update_resp = await client.put(
            f"/api/profile/experiences/{item_id}",
            json={"title": "Senior Engineer"},
            headers=headers,
        )

    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Senior Engineer"


@pytest.mark.asyncio
async def test_delete_experience_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/profile/experiences",
            json={"company": "Google", "title": "Engineer"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        item_id = create_resp.json()["id"]

        delete_resp = await client.delete(
            f"/api/profile/experiences/{item_id}",
            headers=headers,
        )

    assert delete_resp.status_code == 204


# ── Target Role CRUD ────────────────────────────────────


@pytest.mark.asyncio
async def test_create_target_role_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/profile/target-roles",
            json={"title": "Staff Engineer", "priority": 2},
            headers=headers,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Staff Engineer"
    assert body["priority"] == 2


@pytest.mark.asyncio
async def test_update_target_role_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/profile/target-roles",
            json={"title": "Staff Engineer"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        item_id = create_resp.json()["id"]

        update_resp = await client.put(
            f"/api/profile/target-roles/{item_id}",
            json={"keywords": "python, system design"},
            headers=headers,
        )

    assert update_resp.status_code == 200
    assert update_resp.json()["keywords"] == "python, system design"


@pytest.mark.asyncio
async def test_delete_target_role_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/profile/target-roles",
            json={"title": "Staff Engineer"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        item_id = create_resp.json()["id"]

        delete_resp = await client.delete(
            f"/api/profile/target-roles/{item_id}",
            headers=headers,
        )

    assert delete_resp.status_code == 204


# ── Certification CRUD ──────────────────────────────────


@pytest.mark.asyncio
async def test_create_certification_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/profile/certifications",
            json={
                "name": "AWS Solutions Architect",
                "issuer": "Amazon",
                "issue_date": "2023-01-15",
            },
            headers=headers,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "AWS Solutions Architect"
    assert body["issuer"] == "Amazon"


@pytest.mark.asyncio
async def test_update_certification_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/profile/certifications",
            json={"name": "AWS SA"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        item_id = create_resp.json()["id"]

        update_resp = await client.put(
            f"/api/profile/certifications/{item_id}",
            json={"credential_url": "https://verify.aws/123"},
            headers=headers,
        )

    assert update_resp.status_code == 200
    assert update_resp.json()["credential_url"] == "https://verify.aws/123"


@pytest.mark.asyncio
async def test_delete_certification_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/profile/certifications",
            json={"name": "AWS SA"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        item_id = create_resp.json()["id"]

        delete_resp = await client.delete(
            f"/api/profile/certifications/{item_id}",
            headers=headers,
        )

    assert delete_resp.status_code == 204


# ── Language CRUD ────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_language_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/profile/languages",
            json={"name": "Spanish", "proficiency": "fluent"},
            headers=headers,
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Spanish"
    assert body["proficiency"] == "fluent"


@pytest.mark.asyncio
async def test_update_language_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/profile/languages",
            json={"name": "Spanish"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        item_id = create_resp.json()["id"]

        update_resp = await client.put(
            f"/api/profile/languages/{item_id}",
            json={"proficiency": "native"},
            headers=headers,
        )

    assert update_resp.status_code == 200
    assert update_resp.json()["proficiency"] == "native"


@pytest.mark.asyncio
async def test_delete_language_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post(
            "/api/profile/languages",
            json={"name": "Spanish"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        item_id = create_resp.json()["id"]

        delete_resp = await client.delete(
            f"/api/profile/languages/{item_id}",
            headers=headers,
        )

    assert delete_resp.status_code == 204


# ── Validation ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_education_validation_empty_institution():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/profile/educations",
            json={"institution": "", "degree": "BSc"},
            headers=headers,
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_skill_validation_empty_name():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/profile/skills",
            json={"name": ""},
            headers=headers,
        )

    assert resp.status_code == 422
