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

## Architecture Corrections (2026-06-15, later iterations)
1. SRF-before-calibration workflow, then corrected again: **Work Orders are NOT managed here** — they live in the billing/ERP. The Calibration Job is the primary record and stores a Work Order **reference** only (work_order_ref, work_order_date, work_order_source="Billing/ERP", notes), designed for future API lookup. Job number auto-generated (CAL-YYYY-NNNNN via counters). SRF now attaches to the Job (srf_no SRF-YYYY-NNNNN, srf_status, srf_token, srf_approval); prepared from job → sent (secure /srf/{token}) → customer approve/correct/reject. Global search across WO ref / job / SRF / cert / customer / serial / tag. Certificate type (NABL vs Traceable) flows per job into PDF (title + ULR shown only for NABL).
2. Removed Work Order module + screens (per lab's system-separation requirement).

## Audit-Readiness (see AUDIT_GAP_ANALYSIS.md — full gap table + phased plan)
Implemented Phase-A start: `/api/jobs/{id}/pre-release-check` (completeness checklist surfaced on Certificate tab before release) and `/api/jobs/{id}/traceability` (full backward chain: cert→approval→review→job→readings→points→masters→WO ref→SRF→customer approval→customer/product + audit trail). Remaining Phase A–D quality-system modules are documented and pending prioritisation.

## Test Status
Core flows re-verified via API after each correction (login, jobs, SRF prepare/send/approve, search, validation 0 FAIL, pre-release, traceability). Calc engine unchanged and still matches Excel exactly.
