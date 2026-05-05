import uuid, enum
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class LabRequestStatus(str, enum.Enum):
    pending = "pending"
    received = "received"
    completed = "completed"


class LabRequest(Base):
    __tablename__ = "lab_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_profiles.id"))
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("doctor_profiles.id"))
    lab_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("lab_profiles.id"), nullable=True
    )
    tests_requested: Mapped[str] = mapped_column(Text)  # JSON list
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    status: Mapped[LabRequestStatus] = mapped_column(
        Enum(LabRequestStatus), default=LabRequestStatus.pending
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient: Mapped["PatientProfile"] = relationship(  # type: ignore
        "PatientProfile", back_populates="lab_requests"
    )
    doctor: Mapped["DoctorProfile"] = relationship(  # type: ignore
        "DoctorProfile", back_populates="lab_requests"
    )
    lab_reports: Mapped[list["LabReport"]] = relationship(
        "LabReport", back_populates="lab_request"
    )


class LabReport(Base):
    __tablename__ = "lab_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    lab_request_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("lab_requests.id"), nullable=True
    )
    lab_id: Mapped[str] = mapped_column(String(36), ForeignKey("lab_profiles.id"))
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_profiles.id"))
    file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    extracted_values: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    validated_values: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    is_published: Mapped[bool] = mapped_column(default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lab_request: Mapped["LabRequest | None"] = relationship(
        "LabRequest", back_populates="lab_reports"
    )
    lab: Mapped["LabProfile"] = relationship(  # type: ignore
        "LabProfile", back_populates="lab_reports"
    )
