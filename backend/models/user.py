import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Enum, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base

if TYPE_CHECKING:
    from backend.models.patient import PatientProfile
    from backend.models.prediction import AuditLog
    from backend.models.appointment import Appointment
    from backend.models.lab import LabRequest, LabReport


class UserRole(str, enum.Enum):
    admin = "admin"
    doctor = "doctor"
    lab = "lab"
    patient = "patient"


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    access_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    doctor_profile: Mapped["DoctorProfile | None"] = relationship(
        "DoctorProfile", back_populates="user", uselist=False
    )
    lab_profile: Mapped["LabProfile | None"] = relationship(
        "LabProfile", back_populates="user", uselist=False
    )
    patient_profile: Mapped["PatientProfile | None"] = relationship(
        "PatientProfile", back_populates="user", uselist=False
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user")


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    full_name: Mapped[str] = mapped_column(String(255))
    specialization: Mapped[str] = mapped_column(String(255))
    registration_number: Mapped[str] = mapped_column(String(50), default="REG-772810")
    qualification: Mapped[str] = mapped_column(String(500))
    years_experience: Mapped[int | None] = mapped_column(nullable=True)
    success_rate: Mapped[float | None] = mapped_column(nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    available_slots: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="doctor_profile")
    appointments: Mapped[list["Appointment"]] = relationship(
        "Appointment", back_populates="doctor"
    )
    lab_requests: Mapped[list["LabRequest"]] = relationship(
        "LabRequest", back_populates="doctor"
    )


class LabProfile(Base):
    __tablename__ = "lab_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    department_name: Mapped[str] = mapped_column(String(255))
    services: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timing: Mapped[str | None] = mapped_column(String(255), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="lab_profile")
    lab_reports: Mapped[list["LabReport"]] = relationship(
        "LabReport", back_populates="lab"
    )
