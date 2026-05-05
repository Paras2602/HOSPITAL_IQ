# Graph Report - .  (2026-05-05)

## Corpus Check
- 121 files · ~141,050 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 417 nodes · 636 edges · 69 communities (54 shown, 15 thin omitted)
- Extraction: 69% EXTRACTED · 31% INFERRED · 0% AMBIGUOUS · INFERRED: 196 edges (avg confidence: 0.56)
- Token cost: 3,000 input · 1,500 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Backend Domain Models|Backend Domain Models]]
- [[_COMMUNITY_Diagnostic ML Services|Diagnostic ML Services]]
- [[_COMMUNITY_QR & Notification Logic|QR & Notification Logic]]
- [[_COMMUNITY_Auth & Security|Auth & Security]]
- [[_COMMUNITY_QR Generation Utils|QR Generation Utils]]
- [[_COMMUNITY_Email Communication|Email Communication]]
- [[_COMMUNITY_Lab Reporting|Lab Reporting]]
- [[_COMMUNITY_Doctor Clinical Workflow|Doctor Clinical Workflow]]
- [[_COMMUNITY_Frontend Auth & UI Shell|Frontend Auth & UI Shell]]
- [[_COMMUNITY_Patient Symptom Analysis|Patient Symptom Analysis]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 68|Community 68]]

## God Nodes (most connected - your core abstractions)
1. `User` - 32 edges
2. `UserRole` - 28 edges
3. `Base` - 24 edges
4. `PatientProfile` - 21 edges
5. `DoctorProfile` - 17 edges
6. `LabReport` - 15 edges
7. `Appointment` - 14 edges
8. `PredictionRecord` - 13 edges
9. `UpdateSlotsRequest` - 13 edges
10. `ConfirmApptRequest` - 13 edges

## Surprising Connections (you probably didn't know these)
- `book_appointment()` --calls--> `Appointment`  [INFERRED]
  backend/routers/patient.py → backend/models/appointment.py
- `add_clinical_note()` --calls--> `ClinicalNote`  [INFERRED]
  backend/routers/doctor.py → backend/models/appointment.py
- `create_lab_request()` --calls--> `LabRequest`  [INFERRED]
  backend/routers/doctor.py → backend/models/lab.py
- `upload_manual_values()` --calls--> `LabReport`  [INFERRED]
  backend/routers/lab.py → backend/models/lab.py
- `COVID-19 Prediction Audio Transcript` --conceptually_related_to--> `Project README`  [INFERRED]
  graphify-out/transcripts/prediction_covid_19_4ed6d7.txt → frontend/README.md

## Communities (69 total, 15 thin omitted)

### Community 0 - "Backend Domain Models"
Cohesion: 0.14
Nodes (45): BaseModel, Appointment, AppointmentStatus, ClinicalNote, gen_uuid(), gen_uuid(), LabReport, LabRequest (+37 more)

### Community 1 - "Diagnostic ML Services"
Cohesion: 0.14
Nodes (14): Base, Base, seed_data(), DeclarativeBase, SymptomDiseasePredictor, DiagnosisAuditLog, DiagnosisSession, Disease (+6 more)

### Community 2 - "QR & Notification Logic"
Cohesion: 0.09
Nodes (17): QRCodeService, ============================================ HospitalIQ — Notification Utility S, Google Text-to-Speech service for converting text to audio., Convert text to an MP3 audio file.          Args:             text: The text to, Generate a spoken summary of a prediction result., Generate audio narration of a health report., Multi-language translation service powered by Google Translate (via deep-transla, Translate text to the target language.          Args:             text: Source t (+9 more)

### Community 3 - "Auth & Security"
Cohesion: 0.12
Nodes (14): create_doctor(), create_lab(), activate_account(), get_me(), login(), Health check endpoint, register_patient(), TokenResponse (+6 more)

### Community 4 - "QR Generation Utils"
Cohesion: 0.13
Nodes (15): check_rate_limit(), generate_appointment_qr(), generate_patient_qr(), generate_qr(), generate_report_qr(), Convert text to speech and return audio file metadata., Translate text to target language., Generate a custom QR code. (+7 more)

### Community 5 - "Email Communication"
Cohesion: 0.18
Nodes (8): EmailService, Send a welcome email after patient registration., Send appointment confirmation email., Notify patient that lab report is ready., Send high-risk alert notification., Send an OTP / access code email., SMTP-based email notification service for HospitalIQ., Send an email via SMTP.          Args:             to_email: Recipient email add

### Community 6 - "Lab Reporting"
Cohesion: 0.19
Nodes (8): extract_text_from_image(), extract_text_from_pdf(), parse_lab_text(), Extract common lab values from raw text using regex patterns., Extract text from a PDF using PyMuPDF (fitz)., Extract text from an image using pytesseract OCR., upload_lab_result(), upload_manual_values()

### Community 8 - "Frontend Auth & UI Shell"
Cohesion: 0.24
Nodes (7): handleLogout(), clearAuth(), getAuth(), saveAuth(), handleActivate(), handleLogin(), handleSubmit()

### Community 9 - "Patient Symptom Analysis"
Cohesion: 0.27
Nodes (6): analyzeSymptoms(), fetchSymptoms(), listenToSummary(), toggleCategory(), toggleSymptom(), translateResult()

### Community 12 - "Community 12"
Cohesion: 0.25
Nodes (3): init_db(), lifespan(), _seed_admin()

### Community 14 - "Community 14"
Cohesion: 0.5
Nodes (7): divider(), ============================================ HospitalIQ — Notification Services, result(), test_email(), test_qr(), test_translation(), test_tts()

### Community 15 - "Community 15"
Cohesion: 0.29
Nodes (6): get_disease_features(), Return required features for a disease model., What-if simulation — no DB save, just prediction., run_prediction(), _update_health_score(), whatif_simulation()

### Community 16 - "Community 16"
Cohesion: 0.29
Nodes (4): download_pdf_report(), _calc_bmi(), generate_pdf_report(), PDF report generation with ReportLab + QR code.

### Community 17 - "Community 17"
Cohesion: 0.48
Nodes (6): _load_model(), _plot_to_base64(), predict(), Prediction engine with SHAP + LIME explainability., _recommendations(), _risk_label()

### Community 18 - "Community 18"
Cohesion: 0.48
Nodes (6): ML Training Script — generates synthetic data and trains 4 XGBoost classifiers., _save(), train_ckd(), train_diabetes(), train_heart(), train_liver()

### Community 20 - "Community 20"
Cohesion: 0.29
Nodes (7): Admin Router, Auth Router, Database Session Provider, Doctor Profile Model, Patient Profile Model, Security Utilities, User Model

### Community 30 - "Community 30"
Cohesion: 0.83
Nodes (3): fetchAll(), handleUpload(), publishReport()

### Community 33 - "Community 33"
Cohesion: 0.5
Nodes (4): Frontend API Library, Dashboard Layout, Risk Timeline Component, Patient Dashboard Page

## Knowledge Gaps
- **51 isolated node(s):** `============================================ HospitalIQ — Notification Services`, `Prediction engine with SHAP + LIME explainability.`, `ML Training Script — generates synthetic data and trains 4 XGBoost classifiers.`, `Health check endpoint`, `Extract common lab values from raw text using regex patterns.` (+46 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `User` connect `Backend Domain Models` to `Diagnostic ML Services`, `Auth & Security`, `Community 12`?**
  _High betweenness centrality (0.053) - this node is a cross-community bridge._
- **Why does `Base` connect `Diagnostic ML Services` to `Backend Domain Models`, `Community 12`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Why does `UserRole` connect `Backend Domain Models` to `Diagnostic ML Services`, `Auth & Security`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 30 inferred relationships involving `User` (e.g. with `Base` and `PatientProfile`) actually correct?**
  _`User` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `UserRole` (e.g. with `Base` and `PatientProfile`) actually correct?**
  _`UserRole` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `Base` (e.g. with `AppointmentStatus` and `Appointment`) actually correct?**
  _`Base` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `PatientProfile` (e.g. with `Base` and `UserRole`) actually correct?**
  _`PatientProfile` has 19 INFERRED edges - model-reasoned connections that need verification._