# PRD — YOG Electro Process Calibration Lab System

## Original Problem Statement
Digitize the NABL-accredited in-house calibration laboratory's existing Excel workflow (temperature calibration of Type-K thermocouples & RTD/PT-100 sensors) into a secure, traceable web application that **reproduces the exact approved Excel calculation logic** and generates the same certificate. Preserve calculations; do not invent NABL methods.

## Excel Analysis (done first — see EXCEL_LOGIC_ANALYSIS.md)
- Certificate template: FTECH04R5 (K + RTD). Only live formula: Deviation = Measured − Standard.
- Uncertainty budget: FTECH22R0 (one sheet per calibration point). GUM method.
- Key preserved rules (verified to match Excel EXACTLY for all 8 seeded points, diff <1e-6):
  - Xbar (mean UUC) rounded to 2 decimals BEFORE computing std dev.
  - Std unc divisors: Normal(k=2)→/2, Rectangular→/√3, Type A→s(x)/√n.
  - Combined Uc = √Σ Ui²; Welch–Satterthwaite Veff; k=2 if Veff>30; U=k·Uc.
  - Corrected STD = mean(master) − point deviation.
- FLAGGED (in analysis doc, awaiting lab confirmation): reported certificate uncertainty ≠ calc k·Uc → appears to be MAX(rounded calc, CMC/accreditation-scope floor). Implemented as configurable `cmc_floor` per point; both calc & reported shown.

## Architecture
- Backend: FastAPI (/api), MongoDB (motor), JWT cookie+bearer auth (bcrypt). Modules: server.py, calc.py (calculation engine), auth.py, pdf_gen.py (reportlab certificate + QR). Seed from seed_data.json.
- Frontend: React + Tailwind + shadcn/ui + sonner. Swiss/high-contrast clinical design (Work Sans / IBM Plex Sans / JetBrains Mono).

## User Roles
Admin (full), Technician (jobs + readings), Reviewer (review), Authorized Signatory (approve/issue cert), Viewer (read-only). RBAC enforced backend.

## Implemented (2026-06-15)
- Auth (5 seeded users), dashboard (today/pending/issued/expiring/expired/recent).
- Customers + Products, Master instrument DB with validity badges + expiry checks (approval blocked if master expired).
- Calibration Job wizard: customer→product→template→masters→multi-point readings.
- Calculation engine reproducing Excel exactly; per-point uncertainty budget table.
- Excel-vs-App validation screen (0 FAIL for both seeded example jobs).
- Workflow: draft→readings→calculate→submit-review→review→approve→certified.
- PDF certificate (FTECH04R5 layout) + QR code; public verification page (no confidential data).
- Audit trail (reading changes record old/new/user/time).

## Backlog / Not Yet Done (P1/P2)
- P1: Confirm CMC floor / reported-uncertainty rule with lab; make CMC scope table configurable in UI.
- P1: Excel historical import (openpyxl) preserving original values.
- P2: Editable certificate template config; more calibration methods beyond K/RTD.
- P2: Stability/uniformity report ingestion to auto-populate bath uncertainty components.

## Test Status
Backend: 19/19 pytest pass. Frontend core flows verified. Both seeded jobs validation = 0 FAIL.
