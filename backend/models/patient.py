import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


def gen_uuid():
    return str(uuid.uuid4())


def gen_patient_id():
    import random, string
    return "PIQ-" + "".join(random.choices(string.digits, k=8))


class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    patient_id: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, default=gen_patient_id
    )
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(10), nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(5), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    father_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    father_contact: Mapped[str | None] = mapped_column(String(20), nullable=True)
    mother_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mother_contact: Mapped[str | None] = mapped_column(String(20), nullable=True)
    emergency_contact: Mapped[str | None] = mapped_column(String(20), nullable=True)
    allergies: Mapped[str | None] = mapped_column(Text, nullable=True)
    chronic_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    profile_complete: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="patient_profile")  # type: ignore
    appointments: Mapped[list["Appointment"]] = relationship(  # type: ignore
        "Appointment", back_populates="patient"
    )
    lab_requests: Mapped[list["LabRequest"]] = relationship(  # type: ignore
        "LabRequest", back_populates="patient"
    )
    predictions: Mapped[list["PredictionRecord"]] = relationship(  # type: ignore
        "PredictionRecord", back_populates="patient"
    )
    health_scores: Mapped[list["HealthScore"]] = relationship(  # type: ignore
        "HealthScore", back_populates="patient"
    )
    timeline: Mapped[list["HealthTimeline"]] = relationship(  # type: ignore
        "HealthTimeline", back_populates="patient"
    )
