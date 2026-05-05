import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum
from backend.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class AppointmentStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    completed = "completed"
    cancelled = "cancelled"


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_profiles.id"))
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("doctor_profiles.id"))
    requested_date: Mapped[str] = mapped_column(String(50))
    requested_slot: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confirmed_slot: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus), default=AppointmentStatus.pending
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    symptoms: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    patient: Mapped["PatientProfile"] = relationship(  # type: ignore
        "PatientProfile", back_populates="appointments"
    )
    doctor: Mapped["DoctorProfile"] = relationship(  # type: ignore
        "DoctorProfile", back_populates="appointments"
    )
    clinical_note: Mapped["ClinicalNote | None"] = relationship(
        "ClinicalNote", back_populates="appointment", uselist=False
    )


class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    appointment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("appointments.id"), unique=True, nullable=True
    )
    patient_profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("patient_profiles.id")
    )
    doctor_profile_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("doctor_profiles.id")
    )
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    symptoms: Mapped[str | None] = mapped_column(Text, nullable=True)
    vitals: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    history_update: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_tests: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    appointment: Mapped["Appointment"] = relationship(
        "Appointment", back_populates="clinical_note"
    )
