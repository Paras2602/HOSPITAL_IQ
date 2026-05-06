# HospitalIQ — AI-Powered Clinical Decision Support (Multi-Disease Risk Prediction)

HospitalIQ is a hospital-focused, role-based clinical decision support web application that predicts risk for **Diabetes, Heart Disease, Chronic Kidney Disease (CKD), and Liver Disease** using Machine Learning. It includes **Explainable AI (SHAP + LIME)** to make predictions transparent and clinically interpretable.

> **Note/Disclaimer:** HospitalIQ is a clinical decision *support* tool and must not be used as a standalone diagnostic system. Final decisions must be made by licensed clinicians.

---

## Table of Contents
- [Project Overview](#project-overview)
- [Key Problems Solved](#key-problems-solved)
- [Core Objectives](#core-objectives)
- [User Roles & Access Model](#user-roles--access-model)
- [System Workflow (End-to-End)](#system-workflow-end-to-end)
- [Features by Role](#features-by-role)
- [ML + Explainability (SHAP/LIME)](#ml--explainability-shaplime)
- [Lab Report Upload + OCR Extraction](#lab-report-upload--ocr-extraction)
- [Reports, Voice, and Multi-language](#reports-voice-and-multi-language)
- [Suggested Data Model (High Level)](#suggested-data-model-high-level)
- [Recommended Tech Stack](#recommended-tech-stack)
- [Security, Privacy, and Compliance Notes](#security-privacy-and-compliance-notes)
- [Deployment Model](#deployment-model)
- [MVP Scope Recommendation](#mvp-scope-recommendation)
- [Future Enhancements](#future-enhancements)

---

## Project Overview

**Title:** HospitalIQ — AI-Powered Clinical Decision Support for Multi-Disease Risk Prediction

HospitalIQ provides:
- **Multi-disease risk prediction**: High-fidelity models for Diabetes, Heart Disease, CKD, and Liver Disease.
- **Explainable AI (XAI)**: Integrated SHAP and LIME visualizations for clinical transparency.
- **Role-Based Access Control (RBAC)**: Secure workflows for Admins, Doctors, and Patients.
- **Clinical Safety Framework**: Per-patient rate limiting, secure sanitization, and 30-day session management.
- **Verified Audit Trails**: Comprehensive logging of all clinical actions for compliance.
- **Dynamic Dashboards**: Premium glassmorphic interfaces for real-time health monitoring.
- **Medical Utilities**: PDF prescription generation, OCR-ready lab integration, and longitudinal health scoring.

---

## Key Problems Solved

Many hospital ML systems are:
- **Black boxes** (no explanation → low clinical trust)
- Single-disease and not workflow-driven
- Poorly integrated with real lab report pipelines
- Not patient-friendly (complex outputs, poor accessibility)

HospitalIQ addresses these gaps by:
- Providing **transparent predictions** (SHAP/LIME)
- Supporting **multi-disease** risk prediction
- Enabling **role-based workflows** (hospital operations aligned)
- Making outputs **clinically actionable** and **patient-friendly**

---

- Build a hospital-grade multi-disease prediction system (Diabetes/Heart/CKD/Liver)
- Integrate SHAP and LIME explainability with visual dashboards
- Implement strict role-based access (Admin/Doctor/Lab/Patient)
- Admin panel for user management, analytics, and verified clinical audit logs
- Secure clinical diagnosis workflow with automated high-risk alerts
- Dynamic health score tracking and longitudinal risk timeline
- Generate secure, QR-coded PDF reports and automated prescriptions
- Ensure production safety via per-patient rate limiting and session security
- Maintain 99.9% audit-readiness for all medical data access

---

## User Roles & Access Model

### Roles
- **Admin (Hospital Administrator)**
- **Doctor**
- **Lab Technician / Lab Department User**
- **Patient**

### Access Rules (High Level)
- **Admin**: full access to hospital-level data and user management
- **Doctor**: access to assigned/consulting patients, appointments, clinical notes, predictions
- **Lab**: access to lab requests, upload results, view patient identifiers only as needed
- **Patient**: access to own profile, reports, predictions, history, appointments

---

## System Workflow (End-to-End)

### 1) Hospital/Admin Onboarding
1. Admin registers hospital with:
   - Hospital Name, Email, Contact, Address
2. Admin profile is displayed as **“Administrator”** (no personal name required)
3. All users can view limited admin/hospital contact info for support/reporting issues

### 2) Admin Creates Doctor & Lab Accounts
**Doctor creation fields (recommended):**
- Full Name
- Specialization
- Qualification/Degrees (examples: MBBS, MD, MS, DM, MCh, DNB, MRCP, FRCS, PhD)
- Years of Experience
- Success Rate (%) *(optional — should be validated/defined clearly)*
- Profile Photo

**Lab creation fields (recommended):**
- Lab Department Name (e.g., Biochemistry, Pathology)
- Services/Tests Offered
- Contact & timing info
- Profile Photo/Logo *(optional)*

**Access Code Flow:**
- System generates a **unique access code** for each Doctor and Lab user
- Admin shares the code privately
- Doctor/Lab uses the code to activate/login and set password (or code-based login as per design)

### 3) Patient Registration + Profile Completion
**Patient registers** with:
- Name, Phone, Email, Password

After registration, patient completes a detailed profile form:
- Full name, age, sex
- Height, weight, blood group
- Father’s name + contact
- Mother’s name + contact
- Address, emergency contact, allergies, chronic conditions *(recommended)*
- Passport photo (JPG)

System generates a **unique Patient ID**.
- Admin/Doctor/Lab can access patient details using this Patient ID (permission-controlled)
- If a patient registers but does not complete the form, Admin is notified for follow-up

### 4) Appointment Booking (Queue + Time Slots)
- Patient searches doctor list and views profiles
- Patient books appointment:
  - Based on doctor availability (time slots)
  - Queue system supported
- Doctor confirms appointment and assigns a time slot

### 5) Doctor Visit → Clinical Updates
- Doctor views patient profile
- Doctor adds/updates:
  - symptoms, diagnosis notes, vitals, history updates
  - recommended lab tests / scans
- Doctor can create **lab request** referencing Patient ID

### 6) Lab Workflow
- Lab receives test request
- Lab uploads results (PDF/Image/CSV/XLSX)
- OCR/parser extracts values where applicable
- Results become available to:
  - Doctor (review & clinical action)
  - Patient (view report depending on hospital policy)

### 7) ML Predictions + Explainability
- Doctor/Lab/Patient can run prediction (as allowed)
- System outputs:
  - disease risk probabilities / classification
  - SHAP explanation plots
  - LIME explanation plots
  - key features contributing to prediction
- Risk timeline and health score updated per visit

### 8) Report Generation
- Generate PDF report with:
  - Patient summary
  - Prediction results
  - SHAP/LIME explanations (visuals)
  - Recommendations and normal-range indicators
  - QR code linking to online report page

### 9) Patient-Friendly Output
- Plain-language explanations
- Voice output for key summary
- Multi-language translation support

---

## Features by Role

### Admin Dashboard (Implemented)
- **Hospital Analytics**: Real-time breakdown of user counts, prediction trends, and disease prevalence.
- **User Management**: Secure creation of Doctor/Lab accounts with automated access code generation.
- **Clinical Audit Logs**: Searchable, verified history of all system actions (logins, predictions, deactivations).
- **Safety Controls**: Global monitoring of high-risk alerts and low-confidence predictions.

### Doctor Dashboard (Implemented)
- **Clinical Inbox**: View patient symptoms and automated risk assessments.
- **Diagnostic Suite**: Run multi-disease predictions with local SHAP/LIME explanations.
- **Prescription Generator**: AI-assisted prescription synthesis with automated PDF generation.
- **Appointment Manager**: Queue-based system for patient consultation and slot assignment.
- **Patient History**: Access to longitudinal health scores and prior diagnostic reports.

### Patient Dashboard (Implemented)
- **Health Portal**: Unique Patient ID with secure access to personal risk records.
- **Risk Timeline**: Visual tracking of health scores over multiple clinical visits.
- **Diagnostic Archive**: Downloadable PDF reports for all prior screenings.
- **Appointment Booking**: Direct scheduling with hospital doctors based on availability.

---

## ML + Explainability (SHAP/LIME)

### Disease Models
- Diabetes Risk
- Heart Disease Risk
- CKD Risk
- Liver Disease Risk

### Explainability Output
- **SHAP**: global and local feature contribution plots (waterfall, bar)
- **LIME**: local explanation for individual predictions

### Model Governance (recommended)
- Store model version, training date, dataset metadata
- Track prediction request logs (who/when/inputs)
- Monitor drift and performance over time

---

## Lab Report Upload + OCR Extraction

### Supported Formats
- PDF
- JPG/PNG (scanned images)
- CSV
- XLSX

### Pipeline
1. Upload → file stored securely
2. OCR/Parser extracts key lab values (HbA1c, Creatinine, etc.)
3. Validation:
   - unit normalization (mg/dL, mmol/L)
   - normal range checks
   - missing value handling
4. User confirms extracted values before running predictions

---

## Reports, Voice, and Multi-language

- Downloadable PDF reports
- QR codes to verify/view report online
- Voice summary (TTS) for patient
- Translation support for UI labels and key explanations

---

## Suggested Data Model (High Level)

Entities (minimum):
- Hospital
- User (RBAC)
- DoctorProfile
- LabProfile
- PatientProfile
- Appointment
- Visit/Encounter
- LabRequest
- LabReport
- PredictionRecord (inputs + outputs + model version)
- ExplainabilityArtifacts (SHAP/LIME plots/values)
- HealthScoreRecord
- Notification/AuditLog

---

## Recommended Tech Stack

**Frontend**
- React / Next.js
- TailwindCSS or hospital-grade design system
- Plotly for charts/gauges/trends

**Backend**
- Python FastAPI or Django
- JWT authentication + RBAC
- REST API (or GraphQL optionally)

**Database**
- PostgreSQL
- Redis (queues/caching/background jobs)

**ML/AI**
- scikit-learn / XGBoost
- SHAP, LIME
- pandas, numpy

**OCR & Parsing**
- Tesseract OCR (open-source) or Google Vision API (higher accuracy)
- PyMuPDF for PDF extraction
- openpyxl for Excel

**Reports**
- WeasyPrint / ReportLab for PDFs
- qrcode library for QR generation

**Voice & Translation**
- gTTS for voice output
- Translation API (Google/DeepL) or offline alternatives

**Deployment**
- Docker
- Nginx + Gunicorn/Uvicorn
- AWS/Azure/GCP or on-prem hospital server

---

## Security, Privacy, and Clinical Safety

HospitalIQ is built with a **Security-First** clinical architecture:

- **Per-Patient Rate Limiting**: Implemented via `SlowAPI` to prevent DoS and brute-force access to sensitive records.
- **30-Day Session Security**: Robust JWT management with strict 30-day expiration for clinical environments.
- **Input Sanitization**: Multi-layer regex-based sanitization of all clinical inputs to prevent injection attacks.
- **Verified Audit Trails**: Every clinical action (prediction, report view, login) is cryptographically linked to a user and IP.
- **HTTP Security Headers**: Mandatory implementation of HSTS, CSP, and X-Frame-Options.
- **Data Privacy**: Role-based scoping ensures doctors only see assigned patients and patients only see their own data.
- **Model Validation**: Automated registry checks to ensure only authorized ML versions are used for diagnosis.

---

## Deployment Model

### Intended Commercial Flow
- Build and sell/deploy to hospitals
- Admin controls onboarding of doctors and labs
- Patients register to the hospital’s instance of HospitalIQ
- Supports longitudinal patient tracking and hospital workflow integration

---

## MVP Scope Recommendation

To ship faster:
1. RBAC + Auth + Admin create Doctor/Lab via access codes
2. Patient registration + profile + Patient ID
3. Appointment booking + doctor confirmation
4. Lab request + report upload (CSV first; OCR later)
5. One disease model first (e.g., Diabetes) + SHAP explanation
6. PDF report generation (basic)
7. Then expand to all diseases + OCR + LIME + voice + multilingual

---

## Future Enhancements

- Billing & invoices
- SMS/WhatsApp notifications
- EHR integration (HL7/FHIR)
- Advanced model monitoring/drift detection
- Pharmacy & prescription module
- Consent management & patient data sharing controls
- Multi-hospital SaaS tenancy support

---

## Contact / Support

Hospital contact details are visible to users with limited info:
- Hospital Name
- Address
- Support Email
- Support Contact

Admin profile appears as **“Administrator”**.