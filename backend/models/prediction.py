import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class PredictionRecord(Base):
    __tablename__ = "prediction_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_profiles.id"))
    requested_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    disease: Mapped[str] = mapped_column(String(50))  # diabetes|heart|ckd|liver
    input_features: Mapped[str] = mapped_column(Text)  # JSON
    risk_probability: Mapped[float] = mapped_column(Float)
    risk_label: Mapped[str] = mapped_column(String(20))  # low|moderate|high
    shap_values: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    lime_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_version: Mapped[str] = mapped_column(String(50), default="v1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient: Mapped["PatientProfile"] = relationship(  # type: ignore
        "PatientProfile", back_populates="predictions"
    )


class HealthScore(Base):
    __tablename__ = "health_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_profiles.id"))
    score: Mapped[float] = mapped_column(Float)
    diabetes_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    heart_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    ckd_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    liver_risk: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient: Mapped["PatientProfile"] = relationship(  # type: ignore
        "PatientProfile", back_populates="health_scores"
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100))
    resource: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="audit_logs")  # type: ignore


class HealthTimeline(Base):
    __tablename__ = "health_timelines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patient_profiles.id"))
    event_type: Mapped[str] = mapped_column(String(50))  # diagnosis|lab|appointment
    title: Mapped[str] = mapped_column(String(255))
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient: Mapped["PatientProfile"] = relationship(  # type: ignore
        "PatientProfile", back_populates="timeline"
    )
