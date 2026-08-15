# Audit-Readiness Gap Analysis — YOG Calibration LMS
(Existing Feature → Required Audit Control → Status → Proposed Change)

NOTE: Software provides CONTROLS that SUPPORT the lab's ISO 17025/NABL compliance.
It does not, by itself, make the lab compliant. All procedures, retention periods,
uncertainty methods, acceptance criteria and roles remain lab-defined and approved.

## Already COMPLETE (built in current MVP)
| Area | Control | Status |
|---|---|---|
| Calc engine | Reproduces approved Excel logic exactly; Excel-vs-App validation screen | COMPLETE |
| Readings integrity | Reading edits recorded (old→new, user, time) in audit; jobs lock after approval | PARTIAL→ (needs mandatory reason + reviewer re-approval) |
| Audit trail | audit_logs on create/update/review/approve/reading_change/SRF/customer actions; searchable by entity | PARTIAL (needs date/user/action filters + export) |
| RBAC | 5 roles enforced backend on writes/approve | PARTIAL (add Quality Manager + Sales/Admin + Auditor read-only) |
| Certificate control | Immutable after issue; unique verification id; QR + public verify; cancel workflow | PARTIAL (add revision workflow + numbering register) |
| Master control | Full records + validity (valid/expiring/expired); approval blocked if expired | PARTIAL (add out-of-service/retired/under-cal, location, history, override workflow) |
| Traceability | Job → customer/product/masters/readings/calc/review/approval/cert; WO ref + SRF on job | PARTIAL (add single "Complete Audit Trail" view + evidence package) |
| Auth security | bcrypt, JWT httpOnly cookies, session expiry | PARTIAL (add login/logout audit + session timeout UI) |

## Key GAPS to build (mapped to spec sections)
| # | Required Control | Status | Proposed Change |
|---|---|---|---|
| 2,40 | Complete Audit Trail view + Audit Evidence Package (PDF/zip) | MISSING | "Show Complete Audit Trail" button on job; generate structured evidence package |
| 3 | Work Order revision history | PARTIAL | Keep as reference field; store WO revisions (immutable) if edited |
| 4,5 | SRF revision + preserved sent version + approval evidence (IP/device) | PARTIAL | Version SRF on each send; capture IP/UA on customer action |
| 6,7 | Add roles: Quality Manager, Sales/Admin, Auditor(read-only) + separation of duties | MISSING | Extend role list + configurable workflow gates |
| 8 | Electronic sign-off records (performed/reviewed/approved by + version) | PARTIAL | Store signed record snapshots at each gate |
| 9 | Reading correction requires reason + reviewer approval | PARTIAL | Enforce mandatory reason; re-review after change |
| 10,11 | Full audit event coverage + filters + Export Audit Trail | PARTIAL | Add login/logout/download events; filter UI + CSV export |
| 12,13 | Calculation Method versioning + Validation Records; freeze method-version per job | MISSING | calc_methods collection (Rev, effective date, approver); stamp job with version |
| 14 | Pre-Release Verification checklist screen before certificate issue | MISSING | Signatory sees completeness checklist; block issue if incomplete |
| 15-17 | Master extra statuses/location/responsible + full history timeline + override workflow | PARTIAL | Extend master model + history collection |
| 18 | Calibration point change control (who/source/reason/approval) | PARTIAL | Audit point add/remove with reason |
| 20 | Structured environmental records per job | PARTIAL | Dedicated fields (temp/RH/pressure/monitoring equip) |
| 21-24 | Certificate numbering register + revision workflow + cancel shows on QR | PARTIAL | Sequence register; revision chain; verify page shows Valid/Superseded/Cancelled |
| 25,26 | Document Control module (SOPs/procedures/templates, revisions, obsolete) | MISSING | New module + statuses |
| 27 | Configurable record retention | MISSING | Retention settings (Active/Archived/expiry/controlled disposal) |
| 28,29,42 | Backup/DR + System Health dashboard | MISSING | Backup status/history, last backup, versions, error/security logs |
| 30,31,32 | System change control + prod/test separation + Software Validation area | MISSING | Version register, validation docs area |
| 33 | Risk register (configurable) | MISSING | New module |
| 34,35,36,37 | Nonconforming/CAPA, Internal Audit Center, Management Review, Training/Competency | MISSING | New quality modules |
| 38,39 | Confidentiality controls + Auditor read-only "Assessment Mode" | PARTIAL | Auditor role + restricted views |
| 45 | Dedicated Quality/Audit dashboard | MISSING | Aggregated KPIs |
| 46,47 | Requirement Mapping module + FLAG unclear items for QM | MISSING | Config table: Requirement→Feature→Evidence→Owner |

## FLAGGED for Quality Manager decision (do NOT assume)
- Retention periods, override policy for expired masters, separation-of-duties rules,
  certificate numbering format/register, which env parameters are mandatory,
  calculation-method approval authority, and the reported-uncertainty/CMC rule
  (still open from the original analysis, FLAG 1).

## Proposed Phased Implementation
- **Phase A (highest audit value, low risk):** Complete Audit Trail view + Evidence Package; expanded roles (QM/Sales/Auditor + read-only Assessment Mode); reading-correction reason enforcement; audit filters + export; Pre-Release Verification checklist.
- **Phase B (record control):** Calculation Method versioning + Validation Records (stamp per job); Certificate numbering register + revision/cancellation chain; SRF versioning + approval IP/UA; environmental fields; master statuses/history/override.
- **Phase C (quality system):** Document Control; Retention config; Risk Register; NC/CAPA; Internal Audit; Management Review; Training/Competency; Requirement Mapping.
- **Phase D (infrastructure evidence):** Backup/DR status + System Health dashboard + System Change/Version register + Quality/Audit dashboard; final simulated assessment (spec §48).
