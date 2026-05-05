import asyncio
from backend.database import AsyncSessionLocal
from backend.models.user import User
from backend.models.patient import PatientProfile
from backend.models.appointment import Appointment
from backend.models.lab import LabReport, LabRequest
from backend.models.prediction import PredictionRecord, HealthScore
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(PatientProfile))
        profiles = res.scalars().all()
        for p in profiles:
            print(f"Profile {p.patient_id}:")
            print(f"  Name: {p.full_name}")
            print(f"  Age: {p.age}")
            print(f"  Sex: {p.sex}")
            print(f"  Height/Weight: {p.height_cm}/{p.weight_kg}")
            print(f"  Complete: {p.profile_complete}")
            print(f"  Updated at: {p.created_at}")

if __name__ == "__main__":
    asyncio.run(check())
