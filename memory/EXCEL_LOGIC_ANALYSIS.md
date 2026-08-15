# YOG Electro Process — Calibration Lab: Excel Logic Analysis (Phase 1 & 2)

Lab: Yog Electro Process Pvt. Ltd. (NABL in-house calibration laboratory)
Scope analysed so far: Temperature calibration — Thermocouple type **K with Indicator** and **RTD (PT-100) with Indicator**.

## 1. Workbooks Uploaded

| File | Type | Purpose |
|---|---|---|
| FTECH04R5 (Calibration Certificate)-K with Indicator.xlsx | xlsx | Final **Calibration Certificate** template (Type K thermocouple) |
| FTECH04R5 (Calibration Certificate)-RTD with Indicator.xlsx | xlsx | Final **Calibration Certificate** template (RTD/PT-100) |
| FTECH22R0 (Uncertainty Calculation sheet)-K with Indicator.xls | xls | **Uncertainty budget** workbook (K) — one sheet per calibration point |
| FTECH22R0 (Uncertainty Calculation sheet)-RTD with Indicator.xls | xls | **Uncertainty budget** workbook (RTD) — one sheet per calibration point |
| Stability & Uniformity *.xlsx (4 files) | xlsx | Bath stability/uniformity records feeding uncertainty components |
| Master equipment reports (3 PDFs) | pdf | External calibration certificates of the master/reference instruments (YOG-27, YOG-35, YOG-04, YOG-36) |
| FCOMM01R6 (SRF).docx | docx | Service Request Form (customer/item intake) |
| FCOMM02R0 (JR) Job Register.doc | doc | Job register |
| FTECH05R1 Master List of Calibration Equipments.doc | doc | Master instrument register |
| FTECH06/07/12/16, FCOMM11/12/17, FQUAL01/32 | doc/pdf/xlsx | Supporting QMS forms (history card, schedule, traceability, checklist, vendors, records list) |

## 2. Certificate sheet (FTECH04R5) — Structure & Formulas

Single sheet `Calibration Certificate`. No named ranges, no hidden rows/cols, no macros.

**Header / metadata (manual inputs):**
- Certificate No. `D2 + E2` (e.g. `CY/2607/` + `219.03`), ULR No. `D3`
- Calibration Date `M2`, Issue Date `M3`, Item Received Date `M5`, Job No. `M4 & N4` (`N4 = E2`)
- **Recommended next calibration** `M7 = DATE(YEAR(M2),MONTH(M2),DAY(M2)+364)` → cal date + 364 days
- Customer name & address (B5:B7), UUC name/type/serial/make/range (C11..K13)
- Calibration Standards Used table (rows 16-18): Name, Unc of Std (±°C), ID/Sr No, Certified By, Report No, Validity — one row per master used
- Method: `WI – TECH/11`; Ref standard: K→`EURAMET cg-8`, RTD→`DKD-R5-1`
- Environmental: Humidity `55 ±15 %RH`, Ambient `25 ±4 °C`

**Calibration Results table (the only live formula block):**
Columns: Sr No | Standard Value (°C) `B` | Measured Value on UUC (°C) `E` | Deviation (°C) `I` | Expanded Uncertainty (±°C) `L`
- **`Deviation (I) = Measured (E) − Standard (B)`**  — e.g. `I24 = E24 - B24`  ← ONLY calculated cell in the certificate.
- Standard Value `B`, Measured Value `E`, Expanded Uncertainty `L` are **entered/transcribed from the Uncertainty workbook** (see §3 + FLAGS).

Signatories: Calibrated By `Mr. N. H. Bodakhe (Calibration Engineer)`, Approved By `Mr. A. A. Kothe (Technical Manager)`.
Remarks: 8 fixed statements (coverage k=2 @ 95.45%, traceability, points per customer spec, etc.).

## 3. Uncertainty workbook (FTECH22R0) — Structure & Formulas

One **sheet per calibration point** (K: `100,400,700`; RTD: `00,50,100,200,300`). Each sheet = one full GUM uncertainty budget. No macros.

### 3a. Observations block (5 repeat readings x1..x5)
- Col C = STD (master) reading; Col F = UUC reading.
- `C12 = AVERAGE(C7:C11)` (mean STD)
- `D12 = Corrected STD = C12 − (master deviation at this point)`  [note in sheet: "Corrected STD = STD − Dev in STD"]
- `G12 = Xbar = AVERAGE(F7:F11)` (mean UUC reading)
- `H(7..11) = ABS(Fi − Xbar)`; `I = H^2`; `I12 = SUM(I7:I11)`
- `J12 = s(x) = SQRT(I12/(n−1))` (sample std dev, n=5)
- `K12 = s(x̄) = J12 / SQRT(n)` (std dev of mean)

### 3b. Uncertainty budget rows (u1..u10 + uA repeatability)
Per row: D=Estimate Xi (full limit), E=±Xi (=D/2 display), F=distribution, G=Std Unc U(Xi), H=Ci (=1), I=Ui(y)=G·Ci, J=Vi (dof), K=Ui(y)²
- **Std Unc divisor by distribution:** Normal `BN/2` → `G = D/2`; Rectangular `BR/√3` → `G = D/√3`; Type A `A/√n` → `G = s(x)/√5` (= K12).
- `I = G × Ci` (Ci=1 everywhere); `K = I²`
- Degrees of freedom Vi: Type B = ∞ ("¥"); Type A = n−1 = 4.

Components observed (vary by K vs RTD):
- Common: u1 Unc in CC of Reference master, u2 Unc in CC of Read-Out (Digital Thermometer), u3 Resolution of Reference, u4 Resolution of UUC/DUC, Drift of reference, uA Repeatability (Type A).
- RTD-specific: Uniformity of bath, Stability of bath, Self heating, Immersion depth.
- K-specific: Uniformity, Stability, CJC, Variation in CJC, In-homogeneity, Drift.

### 3c. Combination (Welch–Satterthwaite)
- `ΣUi² = SUM(K16:K25)`
- **`Uc (combined std unc) = SQRT(ΣUi²)`**
- **`Veff = (Uc^4 × 4) / (U_typeA_contribution^4)`** (only Type A has finite dof=4) — i.e. Welch–Satterthwaite.
- `k`: if `Veff > 30` → `k = 2`, else use NABL-141 chart.
- **`Expanded Uncertainty U = k × Uc`**

## 4. Excel → Application field mapping (core)

| Excel | Meaning | App field | App calc |
|---|---|---|---|
| C7:C11 | Master (STD) repeat readings | `master_readings[]` | input |
| F7:F11 | UUC repeat readings | `uut_readings[]` | input |
| C12 | mean STD | `std_mean` | `mean(master_readings)` |
| D12 | Corrected STD | `corrected_std` | `std_mean − master_point_deviation` |
| G12 | Xbar mean UUC | `uut_mean` | `mean(uut_readings)` |
| J12 | s(x) | `std_dev` | `sqrt(Σ(xi−x̄)²/(n−1))` |
| K12 | s(x̄) | `std_dev_mean` | `std_dev/sqrt(n)` |
| budget D | source estimate | `component.estimate` | input/config |
| budget G | std unc | `component.std_unc` | `estimate/divisor` |
| budget K | Ui² | `component.ui_sq` | `std_unc²` |
| Uc | combined std unc | `combined_unc` | `sqrt(Σ Ui²)` |
| Veff | effective dof | `veff` | Welch–Satterthwaite |
| U | expanded unc (calc) | `expanded_unc_calc` | `k × Uc` |
| cert B | Standard Value | `point.standard_value` | `= corrected_std` |
| cert E | Measured Value on UUC | `point.measured_value` | `= uut_mean` (see FLAG 2) |
| cert I | Deviation | `point.deviation` | `measured_value − standard_value` |
| cert L | Reported Expanded Unc | `point.reported_uncertainty` | see FLAG 1 |

## 5. ⚠️ FLAGS — items that must be confirmed by the lab (NOT assumed)

**FLAG 1 — Reported Expanded Uncertainty ≠ calculated expanded uncertainty.**
The value printed on the certificate (col L) does NOT equal `k×Uc` from the uncertainty sheet:

| Point | Calc U (k×Uc) | Cert reported |
|---|---|---|
| RTD 0°C | 0.137 | **0.29** |
| RTD 50°C | 0.139 | **0.29** |
| RTD 100°C | 0.141 | **0.29** |
| RTD 200°C | 0.275 | **0.61** |
| RTD 300°C | 0.334 | **0.61** |
| K 100°C | 0.575 | **0.61** |
| K 400°C | 0.655 | **0.66** |
| K 700°C | 1.423 | **1.63** |

Strongly indicates the lab reports **MAX(calculated expanded uncertainty, CMC/accreditation-scope floor)**, then rounds (2 sig figs, round up). The CMC scope table is NOT in these files → **must be provided by the lab.**

**FLAG 2 — Reported "Measured Value on UUC" vs Xbar.** Minor differences (RTD 0°C: Xbar 0.13 → cert 0.12; 100°C: 100.29 → 100.27). Likely manual rounding/resolution rounding when transcribing. Confirm the exact rounding rule.

**FLAG 3 — Corrected STD deviation source.** `Corrected STD = mean STD − deviation`. The per-point master deviation appears to come from the master's own external calibration certificate. Confirm source & sign convention.

**FLAG 4 — Number of budget components & their estimate values** are lab-defined per method (K vs RTD differ). These should be **configurable per calibration method**, seeded from these sheets, not hard-coded.
