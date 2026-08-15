"""End-to-end backend tests for YOG Calibration Lab."""
import os
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE:
    # fallback: read frontend .env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE = line.split("=", 1)[1].strip().rstrip("/")

API = f"{BASE}/api"

CREDS = {
    "admin":      ("mbhashik@gmail.com", "Yog@Admin2026"),
    "technician": ("technician@yog.local", "Tech@2026"),
    "reviewer":   ("reviewer@yog.local", "Review@2026"),
    "signatory":  ("signatory@yog.local", "Sign@2026"),
    "viewer":     ("viewer@yog.local", "View@2026"),
}


def _login(role):
    s = requests.Session()
    email, pw = CREDS[role]
    r = s.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=30)
    assert r.status_code == 200, f"login {role} failed: {r.status_code} {r.text}"
    tok = r.json().get("access_token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s, r.json()


@pytest.fixture(scope="session")
def admin():
    return _login("admin")


@pytest.fixture(scope="session")
def tech():
    return _login("technician")


@pytest.fixture(scope="session")
def reviewer():
    return _login("reviewer")


@pytest.fixture(scope="session")
def signatory():
    return _login("signatory")


@pytest.fixture(scope="session")
def viewer():
    return _login("viewer")


# ---------- Auth ----------
class TestAuth:
    @pytest.mark.parametrize("role", list(CREDS.keys()))
    def test_login_each_role(self, role):
        s, body = _login(role)
        assert body["user"]["role"] == role or (role == "admin" and body["user"]["role"] == "admin")
        assert body["user"]["email"] == CREDS[role][0].lower()

    def test_me(self, admin):
        s, _ = admin
        r = s.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 200
        assert r.json()["role"] == "admin"

    def test_bad_login(self):
        r = requests.post(f"{API}/auth/login", json={"email": "x@y.z", "password": "bad"})
        assert r.status_code == 401


# ---------- Dashboard ----------
class TestDashboard:
    def test_dashboard(self, admin):
        s, _ = admin
        r = s.get(f"{API}/dashboard")
        assert r.status_code == 200
        d = r.json()
        assert "counts" in d and "recent_jobs" in d
        assert "expiring_masters" in d and "expired_masters" in d


# ---------- Jobs / Validation ----------
@pytest.fixture(scope="session")
def seeded_jobs(admin):
    s, _ = admin
    r = s.get(f"{API}/jobs")
    assert r.status_code == 200
    jobs = r.json()
    return jobs


class TestSeededJobs:
    def test_two_seeded(self, seeded_jobs):
        job_nos = {j.get("job_no") for j in seeded_jobs}
        assert "CY/219.03" in job_nos
        assert "CY/212.01" in job_nos
        for j in seeded_jobs:
            if j.get("job_no") in ("CY/219.03", "CY/212.01"):
                assert j["status"] in ("readings_entered", "calculated")

    @pytest.mark.parametrize("job_no", ["CY/219.03", "CY/212.01"])
    def test_validation_all_pass(self, admin, seeded_jobs, job_no):
        s, _ = admin
        j = next(x for x in seeded_jobs if x.get("job_no") == job_no)
        r = s.get(f"{API}/jobs/{j['id']}/validation")
        assert r.status_code == 200
        data = r.json()
        assert data["has_reference"] is True
        fails = [row for row in data["rows"] if row["status"] == "FAIL"]
        assert fails == [], f"FAIL rows for {job_no}: {fails}"

    def test_calculate(self, admin, seeded_jobs):
        s, _ = admin
        j = seeded_jobs[0]
        r = s.post(f"{API}/jobs/{j['id']}/calculate")
        assert r.status_code == 200
        results = r.json()["results"]
        assert len(results) > 0
        for pt in results:
            res = pt["results"]
            for key in ("combined_unc", "veff", "k", "expanded_unc", "reported_uncertainty"):
                assert key in res


# ---------- RBAC ----------
class TestRBAC:
    def test_viewer_cannot_create_customer(self, viewer):
        s, _ = viewer
        r = s.post(f"{API}/customers", json={"name": "TEST_x"})
        assert r.status_code == 403

    def test_viewer_cannot_create_master(self, viewer):
        s, _ = viewer
        r = s.post(f"{API}/masters", json={"master_id": "TEST_M1", "name": "x"})
        assert r.status_code == 403

    def test_reviewer_cannot_approve(self, reviewer, admin):
        s, _ = admin
        jobs = s.get(f"{API}/jobs").json()
        j = jobs[0]
        rs, _ = reviewer
        r = rs.post(f"{API}/jobs/{j['id']}/approve")
        assert r.status_code == 403

    def test_technician_can_create_customer(self, tech):
        s, _ = tech
        r = s.post(f"{API}/customers", json={"name": "TEST_TechCust"})
        assert r.status_code == 200


# ---------- Full workflow ----------
class TestWorkflow:
    def test_submit_review_approve_and_pdf(self, tech, reviewer, signatory, admin):
        s_admin, _ = admin
        jobs = s_admin.get(f"{API}/jobs").json()
        # pick a job in readings_entered not yet certified
        target = None
        for j in jobs:
            if j.get("status") == "readings_entered" and not j.get("certificate"):
                target = j
                break
        assert target, "No candidate job for workflow"
        jid = target["id"]

        s_tech, _ = tech
        r = s_tech.post(f"{API}/jobs/{jid}/submit-review")
        assert r.status_code == 200

        s_rev, _ = reviewer
        r = s_rev.post(f"{API}/jobs/{jid}/review", json={"comments": "ok"})
        assert r.status_code == 200

        s_sig, _ = signatory
        r = s_sig.post(f"{API}/jobs/{jid}/approve")
        assert r.status_code == 200, r.text
        cert = r.json()["certificate"]
        assert "verification_id" in cert
        vid = cert["verification_id"]

        # PDF
        r = s_admin.get(f"{API}/jobs/{jid}/certificate/pdf")
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

        # Public verify
        r = requests.get(f"{API}/verify/{vid}")
        assert r.status_code == 200
        v = r.json()
        assert v["status"] == "issued"
        # confidential customer data should not be present
        assert "customer" not in v
        assert "customer_name" not in v


# ---------- Audit ----------
class TestAudit:
    def test_audit_records_reading_change(self, tech, admin):
        s_admin, _ = admin
        jobs = s_admin.get(f"{API}/jobs").json()
        # find a not-certified job
        target = None
        for j in jobs:
            if j.get("status") not in ("certified", "approved") and not j.get("certificate"):
                target = j
                break
        if not target:
            pytest.skip("No non-certified job to edit")
        # fetch full job
        jid = target["id"]
        full = s_admin.get(f"{API}/jobs/{jid}").json()
        points = full.get("points", [])
        if not points:
            pytest.skip("No points")
        # mutate first reading
        pts = []
        for p in points:
            pts.append({
                "point_label": p["point_label"],
                "nominal": p.get("nominal", 0),
                "master_readings": p["master_readings"],
                "uut_readings": p["uut_readings"],
                "point_deviation": p.get("point_deviation", 0.0),
                "components": p["components"],
                "cmc_floor": p.get("cmc_floor"),
            })
        original = list(pts[0]["uut_readings"])
        pts[0]["uut_readings"] = [x + 0.001 for x in original]
        s_tech, _ = tech
        r = s_tech.put(f"{API}/jobs/{jid}/readings", json={"points": pts})
        assert r.status_code == 200

        r = s_admin.get(f"{API}/audit", params={"entity_id": jid})
        assert r.status_code == 200
        logs = r.json()
        assert any(l.get("action") == "reading_change" for l in logs)

        # restore
        pts[0]["uut_readings"] = original
        s_tech.put(f"{API}/jobs/{jid}/readings", json={"points": pts})


# ---------- Masters ----------
class TestMasters:
    def test_masters_have_validity(self, admin):
        s, _ = admin
        r = s.get(f"{API}/masters")
        assert r.status_code == 200
        ms = r.json()
        assert len(ms) > 0
        for m in ms:
            assert m.get("validity_status") in ("valid", "expiring", "expired", "unknown")
