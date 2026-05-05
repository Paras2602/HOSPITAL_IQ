# Backend Files Summary

## Core Files
- **backend/main.py**: Main FastAPI application entry point with API route registration, middleware setup, and health endpoints
- **backend/database.py**: Database connection setup with SQLAlchemy async engine and session management
- **backend/requirements.txt**: Python package dependencies including FastAPI, SQLAlchemy, Uvicorn, and ML libraries

## Models (Database Tables)
- **backend/models/user.py**: User authentication model with roles (admin, doctor, lab, patient) and profile relationships
- **backend/models/patient.py**: Patient profile model with demographic information and relationships to appointments/labs/predictions
- **backend/models/doctor.py**: Doctor profile model with specialization, experience, and relationships to users/appointments
- **backend/models/lab.py**: Laboratory profile model with department info and relationships to users/lab reports
- **backend/models/appointment.py**: Appointment scheduling model with status tracking and clinical notes
- **backend/models/prediction.py**: Disease prediction records with ML results, SHAP/LIME explanations, and health scores
- **backend/models/symptom_models.py**: Symptom-disease mapping model for ML predictions

## Routers (API Endpoints)
- **backend/routers/auth.py**: Authentication endpoints (login, register, token refresh)
- **backend/routers/admin.py**: Admin dashboard endpoints for user management and system oversight
- **backend/routers/doctor.py**: Doctor endpoints for patient management, appointments, and prescriptions
- **backend/routers/lab.py**: Laboratory endpoints for test requests and report management
- **backend/routers/patient.py**: Patient endpoints for profile management, appointment booking, and report viewing
- **backend/routers/prediction.py**: Disease prediction endpoints for diabetes, heart, CKD, and liver risks
- **backend/routers/reports.py**: PDF report generation and management endpoints
- **backend/routers/notification_routes.py**: Notification system endpoints (email, TTS, QR codes)
- **backend/routers/diagnosis_routes.py**: Symptom-based diagnosis and disease prediction endpoints

## ML Components
- **backend/ml/predict.py**: Disease prediction engine using trained ML models
- **backend/ml/symptom_disease_predictor.py**: Symptom-to-disease mapping predictor
- **backend/ml/prescription_generator.py**: AI-powered prescription recommendation system
- **backend/ml/train_models.py**: Model training scripts for disease prediction
- **backend/ml/saved_models/**: Persisted ML models for diabetes, heart, CKD, and liver prediction
- **backend/ml/ml_models/**: Symptom-disease mapping models and lookup data

## Utilities
- **backend/utils/notifications.py**: Email, SMS, TTS, and QR code generation services
- **backend/utils/pdf_generator.py**: Medical report PDF generation with templates
- **backend/utils/security.py**: Password hashing, token generation, and authentication utilities
- **backend/utils/deps.py**: Dependency injection for database sessions
- **backend/utils/migrate.py**: Database migration scripts

## Data
- **backend/data/seed_diagnosis_data.py**: Sample data seeding script for initial database population