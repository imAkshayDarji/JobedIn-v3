import io
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_async_session
from app.main import app
from tests.conftest import mint_jwt


def _make_pdf() -> bytes:
    from PyPDF2 import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.read()


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


@pytest.mark.asyncio
async def test_onboarding_status_new_user():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        sync_resp = await client.post(
            "/api/auth/sync-profile",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert sync_resp.status_code == 200

        response = await client.get(
            "/api/onboarding/status",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["onboarding_step"] == 0
    assert data["onboarding_completed"] is False
    assert data["completion_percentage"] == 0
    assert data["completed_sections"] == []
    assert data["next_step"] == 1


@pytest.mark.asyncio
async def test_onboarding_save_full():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/auth/sync-profile",
            headers={"Authorization": f"Bearer {token}"},
        )

        payload = {
            "personal_info": {
                "first_name": "John",
                "last_name": "Doe",
                "headline": "Software Engineer",
                "summary": "Experienced developer",
                "location": "San Francisco",
                "phone": "+1234567890",
                "experience_level": "senior",
            },
            "target_roles": [
                {"title": "Senior Backend Engineer", "priority": 1, "keywords": "python,fastapi"},
                {"title": "Staff Engineer", "priority": 2},
            ],
            "skills": [
                {"name": "Python", "category": "Programming", "proficiency": "expert"},
                {"name": "FastAPI", "category": "Framework", "proficiency": "advanced"},
            ],
            "education": [
                {
                    "institution": "MIT",
                    "degree": "B.S. Computer Science",
                    "field_of_study": "Computer Science",
                    "start_date": "2015-09-01",
                    "end_date": "2019-06-01",
                    "grade": "3.9",
                },
            ],
            "experience": [
                {
                    "company": "Google",
                    "title": "Senior SWE",
                    "location": "Mountain View",
                    "start_date": "2019-07-01",
                    "end_date": "2024-01-01",
                    "description": "Built scalable systems",
                    "is_current": False,
                },
            ],
        }

        response = await client.post(
            "/api/onboarding/save",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "profile_id" in data
    assert data["created_target_roles"] == 2
    assert data["created_skills"] == 2
    assert data["created_education"] == 1
    assert data["created_experience"] == 1


@pytest.mark.asyncio
async def test_onboarding_save_partial():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/auth/sync-profile",
            headers={"Authorization": f"Bearer {token}"},
        )

        payload = {
            "personal_info": {
                "first_name": "Jane",
                "last_name": "Smith",
            },
            "target_roles": [],
            "skills": [],
            "education": [],
            "experience": [],
        }

        response = await client.post(
            "/api/onboarding/save",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "profile_id" in data
    assert data["created_target_roles"] == 0


@pytest.mark.asyncio
async def test_onboarding_status_after_save():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/auth/sync-profile",
            headers={"Authorization": f"Bearer {token}"},
        )

        payload = {
            "personal_info": {
                "first_name": "Alice",
                "last_name": "Wonder",
                "headline": "PM",
            },
            "target_roles": [{"title": "Product Manager"}],
            "skills": [],
            "education": [],
            "experience": [],
        }
        await client.post(
            "/api/onboarding/save",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )

        response = await client.get(
            "/api/onboarding/status",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["onboarding_completed"] is True
    assert data["onboarding_step"] == 5
    assert "personal_info" in data["completed_sections"]
    assert "target_roles" in data["completed_sections"]
    assert data["personal_info"]["first_name"] == "Alice"
    assert len(data["target_roles"]) == 1


@pytest.mark.asyncio
async def test_upload_resume_no_file():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/onboarding/upload-resume",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_resume_pdf():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        pdf_bytes = _make_pdf()
        response = await client.post(
            "/api/onboarding/upload-resume",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "extracted_text" in data
    assert "page_count" in data
    assert data["page_count"] == 1
    assert "pre_fill" in data


@pytest.mark.asyncio
async def test_onboarding_unauthorized():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/onboarding/status")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_onboarding_status_no_profile():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/onboarding/status",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404
    assert "profile not found" in response.json()["detail"].lower()
