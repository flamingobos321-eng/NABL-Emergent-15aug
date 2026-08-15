"""Work Order → SRF → Calibration Job workflow tests (iteration 2)."""
import os
import uuid
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE:
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
    em, pw = CREDS[role]
    r = s.post(f"{API}/auth/login", json={"email": em, "password": pw}, timeout=30)
    assert r.status_code == 200, f"login {role} {r.status_code} {r.text}"
    tok = r.json().get("access_token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def admin():
    return _login("admin")


@pytest.fixture(scope="module")
def tech():
    return _login("technician")


@pytest.fixture(scope="module")
def reviewer():
    return _login("reviewer")


@pytest.fixture(scope="module")
def signatory():
    return _login("signatory")


@pytest.fixture(scope="module")
def viewer():
    return _login("viewer")


@pytest.fixture(scope="module")
def customer_id(admin):
    r = admin.get(f"{API}/customers")
    assert r.status_code == 200
    cs = r.json()
    assert cs, "No seeded customer available"
    return cs[0]["id"]


# ---------- Seeded WO / Dashboard ----------
class TestSeededWO:
    def test_dashboard_has_wo_pipeline(self, admin):
        r = admin.get(f"{API}/dashboard")
        assert r.status_code == 200
        d = r.json()
        assert "wo_pipeline" in d, d
        for k in ("new", "srf_pending", "approval_pending", "ready", "in_progress", "correction"):
            assert k in d["wo_pipeline"], f"missing {k}"
        assert "recent_work_orders" in d

    def test_seeded_wo_exists(self, admin):
        r = admin.get(f"{API}/work-orders")
        assert r.status_code == 200
        wos = r.json()
        target = next((w for w in wos if w.get("wo_number") == "WO/2026/001"), None)
        assert target, "Seeded WO/2026/001 not found"
        # fetch details
        r = admin.get(f"{API}/work-orders/{target['id']}")
        assert r.status_code == 200
        w = r.json()
        assert len(w["items"]) == 2
        # verify items match spec
        items = {i["serial_number"]: i for i in w["items"]}
        assert "TC001" in items and "TC002" in items
        assert items["TC001"]["certificate_type"] == "NABL"
        assert items["TC001"]["template_code"] == "K-IND"
        assert items["TC001"]["calibration_points"] == [100.0, 400.0]
        assert items["TC002"]["certificate_type"] == "Traceable"
        assert items["TC002"]["template_code"] == "RTD-IND"
        assert items["TC002"]["calibration_points"] == [100.0, 200.0]


# ---------- RBAC ----------
class TestWORBAC:
    def test_viewer_cannot_create_wo(self, viewer, customer_id):
        r = viewer.post(f"{API}/work-orders", json={
            "wo_number": f"TEST_WO_{uuid.uuid4().hex[:6]}",
            "customer_id": customer_id, "items": [],
        })
        assert r.status_code == 403

    def test_public_srf_no_auth(self):
        # Random token should 404 without any auth
        r = requests.get(f"{API}/srf/nonexistent_token_xyz")
        assert r.status_code == 404


# ---------- Full new-WO workflow (destructive on newly created WO) ----------
@pytest.fixture(scope="module")
def new_wo(admin, customer_id):
    """Create a fresh WO with NABL + Traceable items."""
    wo_number = f"TEST_WO/{uuid.uuid4().hex[:8]}"
    payload = {
        "wo_number": wo_number,
        "customer_id": customer_id,
        "customer_po": "TEST-PO-1",
        "required_completion_date": "2026-08-01",
        "special_instructions": "test flow",
        "items": [
            {"product_name": "TestThermocouple", "description": "type K",
             "quantity": 1, "serial_number": f"TS-{uuid.uuid4().hex[:4]}",
             "range": "0-800 C", "calibration_points": [100.0, 400.0],
             "certificate_type": "NABL", "template_code": "K-IND"},
            {"product_name": "TestRTD", "description": "PT100",
             "quantity": 1, "serial_number": f"TS-{uuid.uuid4().hex[:4]}",
             "range": "0-300 C", "calibration_points": [100.0, 200.0],
             "certificate_type": "Traceable", "template_code": "RTD-IND"},
        ],
    }
    r = admin.post(f"{API}/work-orders", json=payload)
    assert r.status_code == 200, r.text
    w = r.json()
    assert w["status"] == "work_order_received"
    assert w["wo_number"] == wo_number
    return w


class TestWOFullFlow:
    def test_01_start_calibration_blocked_before_srf_approval(self, admin, new_wo):
        r = admin.post(f"{API}/work-orders/{new_wo['id']}/start-calibration")
        assert r.status_code == 400, f"Expected 400 but got {r.status_code} {r.text}"

    def test_02_review(self, admin, new_wo):
        r = admin.post(f"{API}/work-orders/{new_wo['id']}/review")
        assert r.status_code == 200
        w = admin.get(f"{API}/work-orders/{new_wo['id']}").json()
        assert w["status"] == "lab_review"

    def test_03_prepare_srf_prefill(self, admin, new_wo, customer_id):
        r = admin.post(f"{API}/work-orders/{new_wo['id']}/prepare-srf")
        assert r.status_code == 200, r.text
        srf = r.json()["srf"]
        # prefilled customer details
        cust = admin.get(f"{API}/customers").json()
        c = next(x for x in cust if x["id"] == customer_id)
        assert srf["customer_name"] == c["name"]
        # items prefilled with points + cert type
        assert len(srf["items"]) == 2
        types = sorted([i["certificate_type"] for i in srf["items"]])
        assert types == ["NABL", "Traceable"]
        for it in srf["items"]:
            assert len(it["calibration_points"]) > 0

        w = admin.get(f"{API}/work-orders/{new_wo['id']}").json()
        assert w["status"] == "srf_prepared"

    def test_04_send_srf_returns_token(self, admin, new_wo):
        r = admin.post(f"{API}/work-orders/{new_wo['id']}/send-srf")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["token"] and "srf_link" in body
        new_wo["_srf_token"] = body["token"]

    def test_05_public_srf_no_auth(self, new_wo):
        tok = new_wo["_srf_token"]
        r = requests.get(f"{API}/srf/{tok}")  # no session/cookies
        assert r.status_code == 200
        d = r.json()
        assert d["wo_number"] == new_wo["wo_number"]
        assert d["status"] == "srf_sent"
        assert d["srf"] and len(d["srf"]["items"]) == 2

    def test_06_start_calibration_blocked_before_customer_approval(self, admin, new_wo):
        r = admin.post(f"{API}/work-orders/{new_wo['id']}/start-calibration")
        assert r.status_code == 400

    def test_07_public_approve_srf(self, new_wo):
        tok = new_wo["_srf_token"]
        r = requests.post(f"{API}/srf/{tok}/action",
                          json={"action": "approve", "customer_name": "Cust Rep",
                                "comments": "ok"})
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "srf_approved"

    def test_08_start_calibration_creates_jobs(self, admin, new_wo):
        r = admin.post(f"{API}/work-orders/{new_wo['id']}/start-calibration")
        assert r.status_code == 200, r.text
        job_ids = r.json()["job_ids"]
        assert len(job_ids) == 2
        new_wo["_job_ids"] = job_ids
        # verify each job carries the right certificate_type + points
        types = []
        for jid in job_ids:
            j = admin.get(f"{API}/jobs/{jid}").json()
            types.append(j["certificate_type"])
            assert j["work_order_id"] == new_wo["id"]
            assert len(j["points"]) == 2
        assert sorted(types) == ["NABL", "Traceable"]
        # WO status
        w = admin.get(f"{API}/work-orders/{new_wo['id']}").json()
        assert w["status"] == "calibration_in_progress"

    def test_09_start_calibration_idempotent_blocked(self, admin, new_wo):
        r = admin.post(f"{API}/work-orders/{new_wo['id']}/start-calibration")
        assert r.status_code == 400  # already has jobs / wrong status

    def test_10_certificate_pdf_headers_differ(self, admin, tech, reviewer, signatory, new_wo):
        """Approve BOTH jobs then verify PDF NABL vs Traceable header text."""
        pdfs = {}
        for jid in new_wo["_job_ids"]:
            j = admin.get(f"{API}/jobs/{jid}").json()
            ctype = j["certificate_type"]
            # Give them minimal readings; existing status is 'draft' with zero readings
            # submit workflow
            r = tech.post(f"{API}/jobs/{jid}/submit-review")
            assert r.status_code == 200
            r = reviewer.post(f"{API}/jobs/{jid}/review", json={"comments": "ok"})
            assert r.status_code == 200
            r = signatory.post(f"{API}/jobs/{jid}/approve")
            assert r.status_code == 200, r.text
            r = admin.get(f"{API}/jobs/{jid}/certificate/pdf")
            assert r.status_code == 200
            assert r.content[:4] == b"%PDF"
            pdfs[ctype] = r.content

        # Extract text via pypdf (ReportLab compresses streams).
        import io
        from pypdf import PdfReader
        def _text(b):
            r = PdfReader(io.BytesIO(b))
            return "\n".join((p.extract_text() or "") for p in r.pages)
        nabl_txt = _text(pdfs["NABL"])
        trace_txt = _text(pdfs["Traceable"])
        assert "NABL Accredited" in nabl_txt, f"NABL header missing. Text sample: {nabl_txt[:400]}"
        assert "ULR" in nabl_txt, "ULR field missing in NABL PDF"
        assert "Traceable Calibration" in trace_txt, f"Traceable header missing. Text sample: {trace_txt[:400]}"
        assert "ULR No." not in trace_txt, "Traceable PDF should not show ULR No."

    def test_11_wo_completes_when_all_jobs_certified(self, admin, new_wo):
        w = admin.get(f"{API}/work-orders/{new_wo['id']}").json()
        assert w["status"] == "completed", f"Expected completed got {w['status']}"

    def test_12_public_verify_returns_cert_type(self, admin, new_wo):
        # verify NABL job specifically returns certificate_type
        for jid in new_wo["_job_ids"]:
            j = admin.get(f"{API}/jobs/{jid}").json()
            vid = j["certificate"]["verification_id"]
            r = requests.get(f"{API}/verify/{vid}")
            assert r.status_code == 200
            d = r.json()
            assert d["certificate_type"] == j["certificate_type"]


# ---------- Correction / Reject paths (separate fresh WOs) ----------
def _create_and_send_srf(admin, customer_id):
    payload = {
        "wo_number": f"TEST_WO/{uuid.uuid4().hex[:8]}",
        "customer_id": customer_id, "items": [
            {"product_name": "X", "quantity": 1, "serial_number": f"SN{uuid.uuid4().hex[:4]}",
             "calibration_points": [100.0], "certificate_type": "NABL", "template_code": "K-IND"}
        ],
    }
    w = admin.post(f"{API}/work-orders", json=payload).json()
    admin.post(f"{API}/work-orders/{w['id']}/review")
    admin.post(f"{API}/work-orders/{w['id']}/prepare-srf")
    tok = admin.post(f"{API}/work-orders/{w['id']}/send-srf").json()["token"]
    return w, tok


class TestSRFOtherActions:
    def test_request_correction(self, admin, customer_id):
        w, tok = _create_and_send_srf(admin, customer_id)
        r = requests.post(f"{API}/srf/{tok}/action",
                          json={"action": "request_correction",
                                "customer_name": "Cust", "comments": "please fix"})
        assert r.status_code == 200
        wo = admin.get(f"{API}/work-orders/{w['id']}").json()
        assert wo["status"] == "srf_correction_requested"
        # Lab can re-send since public_srf_action allows srf_correction_requested state
        r = admin.post(f"{API}/work-orders/{w['id']}/send-srf")
        assert r.status_code == 200
        wo = admin.get(f"{API}/work-orders/{w['id']}").json()
        assert wo["status"] == "srf_sent"

    def test_reject(self, admin, customer_id):
        w, tok = _create_and_send_srf(admin, customer_id)
        r = requests.post(f"{API}/srf/{tok}/action",
                          json={"action": "reject", "customer_name": "Cust", "comments": "nope"})
        assert r.status_code == 200
        wo = admin.get(f"{API}/work-orders/{w['id']}").json()
        assert wo["status"] == "srf_rejected"


# ---------- Regression: seeded jobs validation still 0-FAIL ----------
class TestCalcEngineUnchanged:
    @pytest.mark.parametrize("job_no", ["CY/219.03", "CY/212.01"])
    def test_validation_zero_fail(self, admin, job_no):
        jobs = admin.get(f"{API}/jobs").json()
        j = next((x for x in jobs if x.get("job_no") == job_no), None)
        if not j:
            pytest.skip(f"{job_no} not found (may have been consumed in prior iteration)")
        r = admin.get(f"{API}/jobs/{j['id']}/validation")
        assert r.status_code == 200
        d = r.json()
        if not d["has_reference"]:
            pytest.skip(f"{job_no} lost its excel_reference (prior test iteration side-effect)")
        fails = [row for row in d["rows"] if row["status"] == "FAIL"]
        assert fails == [], f"Unexpected FAIL rows: {fails}"
