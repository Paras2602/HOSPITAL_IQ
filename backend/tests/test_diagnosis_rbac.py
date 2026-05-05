import pytest
from httpx import AsyncClient
from backend.main import app
from backend.models.user import UserRole

@pytest.mark.asyncio
async def test_admin_analytics_access():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 1. Test without token
        response = await ac.get("/api/diagnosis/admin/analytics")
        assert response.status_code in [401, 403]

@pytest.mark.asyncio
async def test_doctor_diagnosis_access():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/diagnosis/doctor/DOC-123")
        assert response.status_code in [401, 403]

@pytest.mark.asyncio
async def test_patient_history_access():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/diagnosis/history/PAT-123")
        assert response.status_code in [401, 403]
