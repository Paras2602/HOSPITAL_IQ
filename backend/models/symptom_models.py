import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base

def gen_uuid():
    return str(uuid.uuid4())

class Symptom(Base):
    __tablename__ = "symptoms"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity_weight: Mapped[float] = mapped_column(Float, default=1.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Disease(Base):
    __tablename__ = "diseases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class DiseaseSymptomMapping(Base):
    __tablename__ = "disease_symptom_mapping"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    disease_id: Mapped[int] = mapped_column(Integer, ForeignKey("diseases.id"))
    symptom_id: Mapped[int] = mapped_column(Integer, ForeignKey("symptoms.id"))
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

class Medicine(Base):
    __tablename__ = "medicines"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    generic_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    medicine_type: Mapped[str] = mapped_column(String(50), nullable=False)
    default_dosage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    common_side_effects: Mapped[str | None] = mapped_column(Text, nullable=True)
    contraindications: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class DiseaseMedicineMapping(Base):
    __tablename__ = "disease_medicine_mapping"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    disease_id: Mapped[int] = mapped_column(Integer, ForeignKey("diseases.id"))
    medicine_id: Mapped[int] = mapped_column(Integer, ForeignKey("medicines.id"))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    priority_order: Mapped[int] = mapped_column(Integer, default=1)

class DiagnosisSession(Base):
    __tablename__ = "diagnosis_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    patient_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    doctor_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    initiated_by: Mapped[str] = mapped_column(String(50), nullable=False)
    symptoms_input: Mapped[list] = mapped_column(JSON, nullable=False)
    predicted_diseases: Mapped[list] = mapped_column(JSON, nullable=False)
    top_prediction: Mapped[str] = mapped_column(String(100), nullable=False)
    top_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    ml_model_used: Mapped[str] = mapped_column(String(50), default="random_forest")
    status: Mapped[str] = mapped_column(String(50), default="pending")
    doctor_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_appointment_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("appointments.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    follow_up_appointment = relationship("Appointment")

class Prescription(Base):
    __tablename__ = "prescriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prescription_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    diagnosis_session_id: Mapped[int] = mapped_column(Integer, ForeignKey("diagnosis_sessions.id"))
    patient_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    disease_diagnosed: Mapped[str] = mapped_column(String(100), nullable=False)
    medicines_prescribed: Mapped[list] = mapped_column(JSON, nullable=False)
    precautions: Mapped[str | None] = mapped_column(Text, nullable=True)
    dietary_advice: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    llm_generated_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    doctor_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    doctor_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class DiagnosisAuditLog(Base):
    __tablename__ = "diagnosis_audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    diagnosis_session_id: Mapped[int] = mapped_column(Integer, ForeignKey("diagnosis_sessions.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    performed_by_role: Mapped[str] = mapped_column(String(50), nullable=False)
    performed_by_id: Mapped[str] = mapped_column(String(36), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
