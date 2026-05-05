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
- Multi-disease risk prediction from patient demographics, vitals, history, and lab values
- Explainable results using SHAP and LIME
- Role-based workflows for **Admin, Doctor, Lab Technician, and Patient**
- Lab report uploads (PDF/Image/CSV/XLSX) with OCR-based extraction
- Appointment booking + queue management
- Health score tracking, risk timeline, alerts, and what-if simulator
- PDF report generation with QR code, voice output, and multi-language support

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

## Core Objectives

- Build a hospital-grade multi-disease prediction system (Diabetes/Heart/CKD/Liver)
- Integrate SHAP and LIME explainability with visual dashboards
- Implement strict role-based access (Admin/Doctor/Lab/Patient)
- Admin panel for user management, analytics, audit/activity monitoring
- Lab report upload & parsing (PDF/JPG/PNG/CSV/XLSX) + OCR extraction
- What-if simulator, risk timeline, health score tracking, alerts
- Generate downloadable PDF reports with QR codes and recommendations
- Voice output and multi-language support for patient understanding
- Track patient longitudinal history across visits
- Maintain accuracy + transparency + auditability

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

### Admin Dashboard
- Hospital profile & settings
- Create/Manage Doctors & Labs (generate access codes)
- View all users and activity logs (audit trail)
- System analytics (usage, prediction counts, common diseases)
- Manage staging rules/thresholds (if applicable)
- Support tickets/contact visibility (optional)

### Doctor Dashboard
- Profile + availability/time slots
- Appointment requests + confirmations
- Patient search by Patient ID
- Clinical notes & history update form
- Lab test request workflow
- View lab results + trends
- Run predictions + SHAP/LIME explainability
- What-if simulator (e.g., effect of HbA1c change)
- PDF report generation

### Lab Dashboard
- Lab profile + services
- Incoming test requests
- Upload reports (PDF/JPG/PNG/CSV/XLSX)
- OCR extraction review + manual correction
- Publish finalized results to doctor/patient (policy-based)

### Patient Dashboard
- Profile + Patient ID
- Search doctors/labs & view profiles/services
- Book appointments (queue/time slot)
- View predictions (if enabled) and simplified explanation
- Risk timeline + health score
- Download PDF reports
- Voice output and language switch

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

## Security, Privacy, and Compliance Notes

- Encrypt sensitive data at rest and in transit (TLS)
- Strong password policy + MFA (recommended for Admin/Doctor)
- Audit logs for all critical actions (view/update/predict/download)
- Access control by role + patient consent policy
- Data retention policy and secure backups
- Consider compliance requirements (HIPAA / local regulations) depending on region
- Clearly display disclaimers: decision support only, not diagnosis

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