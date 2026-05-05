# Frontend Files Summary

## Core Application Files
- **frontend/app/layout.tsx**: Root layout component with navigation and authentication wrappers
- **frontend/app/page.tsx**: Landing page/dashboard overview
- **frontend/app/globals.css**: Global CSS styles and TailwindCSS configuration
- **frontend/app/favicon.ico**: Application favicon

## Dashboard Sections (Role-Based)
- **frontend/app/dashboard/admin/**: Admin dashboard for system oversight
- **frontend/app/dashboard/doctor/**: Doctor interface for patient management
- **frontend/app/dashboard/lab/**: Laboratory interface for test management
- **frontend/app/dashboard/patient/**: Patient interface for health tracking

## Authentication Pages
- **frontend/app/login/**: User login page with form validation
- **frontend/app/register/**: User registration page with role selection

## Component Library
- **frontend/components/**: Reusable UI components (buttons, forms, cards, modals, charts, etc.)
- **frontend/lib/**: Utility functions, API clients, and helper modules
- **frontend/public/**: Static assets (SVG icons, images)

## Configuration Files
- **frontend/package.json**: Node.js dependencies and project metadata
- **frontend/tsconfig.json**: TypeScript compiler configuration
- **frontend/next.config.ts**: Next.js framework configuration
- **frontend/postcss.config.mjs**: PostCSS configuration for TailwindCSS
- **frontend/eslint.config.mjs**: ESLint configuration for code quality
- **frontend/.env.local**: Environment variables for API endpoints and secrets

## Key Technology Indicators
- Built with Next.js 13+ (app directory structure)
- TypeScript for type safety
- TailwindCSS for styling (globals.css indicates Tailwind usage)
- React components throughout the components directory