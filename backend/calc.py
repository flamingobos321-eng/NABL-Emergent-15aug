"""
Calibration calculation engine — reproduces the exact logic of the lab's
FTECH22R0 Uncertainty Calculation workbooks and FTECH04R5 Certificate.

Verified to match Excel EXACTLY for all seeded calibration points.

Key preserved rules (do NOT change without lab approval):
  * Xbar (mean UUC reading) is ROUNDED to 2 decimals before computing std dev
    (Excel stores G12 = ROUND(AVERAGE(F7:F11),2) and uses it in (xi-xbar)).
  * Std uncertainty divisors: Normal (k=2) -> /2 ; Rectangular -> /sqrt(3) ;
    Type A repeatability -> s(x)/sqrt(n).
  * Combined Uc = sqrt(sum(Ui^2)).
  * Welch-Satterthwaite: Veff = Uc^4 / sum(Ui^4 / Vi).  Type B => Vi = inf.
  * Coverage factor k = 2 when Veff > 30 (else NABL-141 t-table).
  * Expanded uncertainty U = k * Uc.
  * Deviation = round(Xbar,2) - corrected_std.
  * Corrected STD = mean(master_readings) - point_deviation.
"""
import math

# t-table (k) for 95.45% confidence vs effective degrees of freedom (NABL-141)
_KP_TABLE = [
    (1, 13.97), (2, 4.53), (3, 3.31), (4, 2.87), (5, 2.65), (6, 2.52),
    (7, 2.43), (8, 2.37), (9, 2.32), (10, 2.28), (12, 2.23), (14, 2.20),
    (16, 2.17), (18, 2.15), (20, 2.13), (25, 2.11), (30, 2.09), (35, 2.07),
    (40, 2.06), (45, 2.06), (50, 2.05), (100, 2.025),
]


def mean(xs):
    return sum(xs) / len(xs)


def coverage_factor(veff):
    if veff is None or math.isinf(veff) or veff > 30:
        return 2.0
    for dof, k in _KP_TABLE:
        if veff <= dof:
            return k
    return 2.0


def round_sig(x, sig=2):
    """Round to `sig` significant figures (used for reported uncertainty)."""
    if x == 0:
        return 0.0
    from math import log10, floor
    return round(x, -int(floor(log10(abs(x)))) + (sig - 1))


def component_std_unc(distribution, estimate, s_mean=None):
    if distribution == "normal_k2":
        return estimate / 2.0
    if distribution == "rect_root3":
        return estimate / math.sqrt(3)
    if distribution == "typeA":
        return s_mean
    raise ValueError(f"Unknown distribution: {distribution}")


def compute_point(master_readings, uut_readings, point_deviation, components,
                  cmc_floor=None, decimals=2):
    """Compute a single calibration point. Returns a dict of all results.

    components: list of {label, source, distribution, estimate, ci}
      - For 'typeA' components, `estimate` is ignored and recomputed as s(x).
    """
    n = len(uut_readings)
    std_mean = mean(master_readings)
    corrected_std = round(std_mean - point_deviation, 6)

    # Xbar rounded to 2 decimals BEFORE deviations (Excel behaviour)
    uut_mean = round(mean(uut_readings), decimals)
    ss = sum((x - uut_mean) ** 2 for x in uut_readings)
    s_x = math.sqrt(ss / (n - 1)) if n > 1 else 0.0
    s_mean = s_x / math.sqrt(n) if n > 0 else 0.0

    budget = []
    sum_ui_sq = 0.0
    typeA_ui = None
    for c in components:
        dist = c["distribution"]
        est = s_x if dist == "typeA" else float(c["estimate"])
        ci = float(c.get("ci", 1.0) or 1.0)
        u = component_std_unc(dist, est, s_mean)
        ui = u * ci
        ui_sq = ui * ui
        sum_ui_sq += ui_sq
        dof = (n - 1) if dist == "typeA" else None  # None == infinity
        if dist == "typeA":
            typeA_ui = ui
        budget.append({
            "label": c["label"],
            "source": c.get("source", ""),
            "distribution": dist,
            "estimate": est,
            "ci": ci,
            "std_unc": u,
            "ui": ui,
            "ui_sq": ui_sq,
            "dof": dof,
        })

    combined_unc = math.sqrt(sum_ui_sq)
    if typeA_ui and typeA_ui > 0 and n > 1:
        veff = (combined_unc ** 4) / ((typeA_ui ** 4) / (n - 1))
    else:
        veff = float("inf")
    k = coverage_factor(veff)
    expanded_unc = k * combined_unc

    # Reported uncertainty on the certificate = max(rounded U, CMC floor)
    reported_calc = round_sig(expanded_unc, 2)
    if cmc_floor is not None:
        reported_uncertainty = max(reported_calc, float(cmc_floor))
    else:
        reported_uncertainty = reported_calc

    deviation = round(uut_mean - corrected_std, decimals)

    return {
        "n": n,
        "std_mean": std_mean,
        "corrected_std": corrected_std,          # -> certificate Standard Value
        "uut_mean": uut_mean,                     # -> certificate Measured Value
        "s_x": s_x,
        "s_mean": s_mean,
        "budget": budget,
        "combined_unc": combined_unc,             # Uc
        "veff": veff,
        "k": k,
        "expanded_unc": expanded_unc,             # calculated U = k*Uc
        "reported_uncertainty": reported_uncertainty,  # printed on certificate
        "cmc_floor": cmc_floor,
        "deviation": deviation,                   # -> certificate Deviation
    }


def compute_job_points(points):
    """points: list of point dicts with readings/components. Returns computed list."""
    out = []
    for p in points:
        r = compute_point(
            p["master_readings"], p["uut_readings"], p.get("point_deviation", 0.0),
            p["components"], p.get("cmc_floor"),
        )
        out.append({**p, "results": r})
    return out
