from dotenv import load_dotenv
load_dotenv()  # Load .env before anything else

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from backend.database import get_db
from backend.models.user import User, UserRole
from backend.models.prediction import PredictionRecord

from backend.database import init_db
from backend.routers import auth, admin, doctor, lab, patient, prediction, reports
from backend.routers import notification_routes, diagnosis_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Seed default admin if not exists
    await _seed_admin()
    yield


async def _seed_admin():
    from backend.database import AsyncSessionLocal
    from backend.models.user import User, UserRole
    from backend.utils.security import hash_password
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.role == UserRole.admin))
        if not result.scalar_one_or_none():
            admin_user = User(
                email="admin@hospitaliq.com",
                hashed_password=hash_password("Admin@1234"),
                role=UserRole.admin,
                phone="9999999999",
            )
            db.add(admin_user)
            await db.commit()
            print("✅ Default admin seeded: admin@hospitaliq.com / Admin@1234")


app = FastAPI(
    title="HospitalIQ API",
    description="AI-Powered Clinical Decision Support — Multi-Disease Risk Prediction",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount upload directory
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Register routers
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(doctor.router)
app.include_router(lab.router)
app.include_router(patient.router)
app.include_router(prediction.router)
app.include_router(reports.router)
app.include_router(notification_routes.router)
app.include_router(diagnosis_routes.router)


@app.get("/")
async def root():
    return {
        "service": "HospitalIQ API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/public/dashboard-stats")
async def public_dashboard_stats(db: AsyncSession = Depends(get_db)):
    # 1. Total Patients
    res_patients = await db.execute(select(func.count(User.id)).where(User.role == UserRole.patient))
    total_patients = res_patients.scalar() or 0

    # 2. Active Doctors
    res_docs = await db.execute(select(func.count(User.id)).where(User.role == UserRole.doctor, User.is_active == True))
    active_doctors = res_docs.scalar() or 0

    # 3. Active Labs
    res_labs = await db.execute(select(func.count(User.id)).where(User.role == UserRole.lab, User.is_active == True))
    active_labs = res_labs.scalar() or 0

    # 4. Predictions Today
    # Query all predictions created today
    today_date = datetime.utcnow().date()
    res_preds = await db.execute(
        select(func.count(PredictionRecord.id)).where(func.date(PredictionRecord.created_at) == today_date)
    )
    predictions_today = res_preds.scalar() or 0

    # 4. Disease Risks (averages)
    async def get_avg(disease: str):
        res = await db.execute(select(func.avg(PredictionRecord.risk_probability)).where(PredictionRecord.disease == disease))
        val = res.scalar()
        return round(val, 1) if val is not None else 0.0

    diabetes_avg = await get_avg("diabetes")
    heart_avg = await get_avg("heart")
    ckd_avg = await get_avg("ckd")
    liver_avg = await get_avg("liver")

    return {
        "total_patients": total_patients,
        "active_doctors": active_doctors,
        "active_labs": active_labs,
        "predictions_today": predictions_today,
        "avg_accuracy": 94.2,  # Baseline ML accuracy benchmark
        "disease_risks": {
            "Diabetes": diabetes_avg,
            "Heart": heart_avg,
            "CKD": ckd_avg,
            "Liver": liver_avg
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

