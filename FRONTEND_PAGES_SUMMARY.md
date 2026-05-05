# Frontend Pages/Routes Summary

## Root Level Pages
- **frontend/app/page.tsx**: Landing page/dashboard overview (public/home page)
- **frontend/app/login/page.tsx**: User authentication login page
- **frontend/app/register/page.tsx**: User registration page for new accounts

## Dashboard Routes (Role-Based)
All dashboard routes are under `/dashboard` prefix:

### Admin Dashboard
- **frontend/app/dashboard/admin/page.tsx**: Admin main dashboard overview
- **frontend/app/dashboard/admin/analytics/page.tsx**: System analytics and metrics
- **frontend/app/dashboard/admin/audit/page.tsx**: Audit logs and system activity
- **frontend/app/dashboard/admin/create-doctor/page.tsx**: Create new doctor accounts
- **frontend/app/dashboard/admin/create-lab/page.tsx**: Create new laboratory accounts
- **frontend/app/dashboard/admin/users/page.tsx**: User management interface

### Doctor Dashboard
- **frontend/app/dashboard/doctor/page.tsx**: Doctor main dashboard overview
- **frontend/app/dashboard/doctor/appointments/page.tsx**: Manage doctor appointments
- **frontend/app/dashboard/doctor/patients/page.tsx**: Patient list and management
- **frontend/app/dashboard/doctor/lab-requests/page.tsx**: View and manage lab requests
- **frontend/app/dashboard/doctor/notes/page.tsx**: Clinical notes management
- **frontend/app/dashboard/doctor/predict/page.tsx**: Disease prediction interface
- **frontend/app/dashboard/doctor/prescriptions/page.tsx**: Prescription management
- **frontend/app/dashboard/doctor/symptom-checker/page.tsx**: Symptom-based diagnosis tool
- **frontend/app/dashboard/doctor/diagnoses/page.tsx**: List of patient diagnoses
- **frontend/app/dashboard/doctor/diagnosis/[sessionId]/page.tsx**: Individual diagnosis session view

### Laboratory Dashboard
- **frontend/app/dashboard/lab/page.tsx**: Lab main dashboard overview
- *(Additional lab-specific pages would be in subdirectories)*

### Patient Dashboard
- **frontend/app/dashboard/patient/page.tsx**: Patient main dashboard overview
- **frontend/app/dashboard/patient/profile/page.tsx**: Patient profile management
- **frontend/app/dashboard/patient/appointments/page.tsx**: Patient appointment scheduling/viewing
- **frontend/app/dashboard/patient/health/page.tsx**: Health metrics and vitals tracking
- **frontend/app/dashboard/patient/predictions/page.tsx**: View past disease predictions
- **frontend/app/dashboard/patient/reports/page.tsx**: Access medical reports and lab results
- **frontend/app/dashboard/patient/prescriptions/page.tsx**: View and manage prescriptions
- **frontend/app/dashboard/patient/symptom-checker/page.tsx**: Self symptom assessment tool
- **frontend/app/dashboard/patient/diagnoses/page.tsx**: View past diagnoses

## Key Observations
1. **Role-Based Access Control**: Each user role (admin, doctor, lab, patient) has a dedicated dashboard section
2. **Comprehensive Feature Coverage**: Pages exist for all major hospital workflow components
3. **Dynamic Routing**: Uses Next.js dynamic routes for session-based views (e.g., diagnosis/[sessionId])
4. **Modular Organization**: Features are well-organized into logical subdirectories
5. **File Naming Convention**: All pages use `page.tsx` filename following Next.js 13+ app router convention

## Missing Pages (Based on Expected Functionality)
While the structure is comprehensive, some expected pages might be missing:
- Lab-specific request/report management pages under `/dashboard/lab/`
- Detailed analytics views for doctors/patients
- Notification management interfaces
- Account settings/profile editing pages for all roles