"""Backend tests for the multi-product job refactor."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://precision-cal-app-1.preview.emergentagent.com").rstrip("/")

ADMIN = ("mbhashik@gmail.com", "Yog@Admin2026")
TECH = ("technician@yog.local", "Tech@2026")
REV = ("reviewer@yog.local", "Review@2026")
SIG = ("signatory@yog.local", "Sign@2026")


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login {email} failed: {r.status_code} {r.text}"
    tok = r.json().get("access_token")
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def admin_s():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def tech_s():
    return _login(*TECH)


@pytest.fixture(scope="module")
def rev_s():
    return _login(*REV)


@pytest.fixture(scope="module")
def sig_s():
    return _login(*SIG)


# ---------------- Auth ----------------
def test_admin_login():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]}, timeout=30)
    assert r.status_code == 200
    assert "access_token" in r.json()


# ---------------- List Jobs / Rollup ----------------
def test_list_jobs_has_rollup_fields(admin_s):
    r = admin_s.get(f"{BASE_URL}/api/jobs")
    assert r.status_code == 200
    jobs = r.json()
    assert isinstance(jobs, list) and len(jobs) >= 2
    for j in jobs:
        assert "product_count" in j
        assert "certified_count" in j
        assert "product_names" in j
        assert "status" in j


# ---------------- Migration integrity: seeded CY jobs ----------------
@pytest.fixture(scope="module")
def seeded_jobs(admin_s):
    r = admin_s.get(f"{BASE_URL}/api/jobs")
    jobs = r.json()
    cy = [j for j in jobs if (j.get("job_no") or "").startswith("CY/")]
    assert len(cy) >= 2, f"Expected 2 seeded CY jobs, got {len(cy)}"
    return cy


def test_seeded_jobs_have_items_and_points(admin_s, seeded_jobs):
    for j in seeded_jobs:
        r = admin_s.get(f"{BASE_URL}/api/jobs/{j['id']}")
        assert r.status_code == 200
        d = r.json()
        assert d.get("items") and len(d["items"]) >= 1
        it = d["items"][0]
        assert it.get("product_name")
        assert it.get("points") and len(it["points"]) > 0
        # excel_reference should be preserved on at least the first point
        assert any("excel_reference" in p for p in it["points"]), "excel_reference missing"
        assert "standards_used" in it


def test_excel_validation_seeded_all_pass(admin_s, seeded_jobs):
    """Calc engine must still match Excel exactly (0 FAIL)."""
    for j in seeded_jobs:
        detail = admin_s.get(f"{BASE_URL}/api/jobs/{j['id']}").json()
        for it in detail["items"]:
            r = admin_s.get(f"{BASE_URL}/api/jobs/{j['id']}/items/{it['item_id']}/validation")
            assert r.status_code == 200
            v = r.json()
            assert v["has_reference"] is True, f"has_reference False for {j['job_no']}"
            fails = [row for row in v["rows"] if row["status"] == "FAIL"]
            assert len(fails) == 0, f"Excel-vs-App FAILs for {j['job_no']}: {fails}"


# ---------------- Create multi-product job ----------------
@pytest.fixture(scope="module")
def multi_job(admin_s, seeded_jobs):
    # reuse seeded product/customer/master from CY/212.01
    src = admin_s.get(f"{BASE_URL}/api/jobs/{seeded_jobs[0]['id']}").json()
    cid = src["customer_id"]
    src_item = src["items"][0]
    pid = src_item["product_id"]
    mids = src_item.get("master_ids") or []
    tpl = src_item.get("template_code", "")

    point = {
        "point_label": "P1", "nominal": 100.0,
        "master_readings": [100.0, 100.1, 100.0, 100.0, 100.0],
        "uut_readings": [100.2, 100.3, 100.2, 100.2, 100.2],
        "point_deviation": 0.0,
        "components": [
            {"label": "master_unc", "source": "master", "distribution": "normal_k2", "estimate": 0.05, "ci": 1.0},
            {"label": "resolution", "source": "uut", "distribution": "rect_root3", "estimate": 0.1, "ci": 1.0},
        ],
    }
    body = {
        "work_order_ref": f"WO-TEST-{uuid.uuid4().hex[:6]}",
        "customer_id": cid,
        "items": [
            {"product_id": pid, "serial_number": "SN-A", "sr_number": "SR-A", "part_number": "PN-A",
             "url_number": "URL-A", "certificate_type": "NABL", "cal_date": "2026-01-15",
             "template_code": tpl, "master_ids": mids, "points": [point]},
            {"product_id": pid, "serial_number": "SN-B", "sr_number": "SR-B", "part_number": "PN-B",
             "url_number": "URL-B", "certificate_type": "Traceable", "cal_date": "2026-01-15",
             "template_code": tpl, "master_ids": mids, "points": [point]},
        ],
    }
    r = admin_s.post(f"{BASE_URL}/api/jobs", json=body)
    assert r.status_code == 200, r.text
    j = r.json()
    assert len(j["items"]) == 2
    ids = {it["item_id"] for it in j["items"]}
    assert len(ids) == 2, "item_ids must be unique"
    return j


def test_create_multi_product_job(multi_job):
    assert multi_job["job_no"]
    assert len(multi_job["items"]) == 2
    serials = sorted(it["serial_number"] for it in multi_job["items"])
    assert serials == ["SN-A", "SN-B"]


# ---------------- Per-product workflow independence ----------------
def test_per_product_workflow_independence(admin_s, rev_s, sig_s, multi_job):
    jid = multi_job["id"]
    item_a = multi_job["items"][0]
    item_b = multi_job["items"][1]
    aid = item_a["item_id"]
    bid = item_b["item_id"]

    # readings already set. Run pipeline on A only
    r = admin_s.put(f"{BASE_URL}/api/jobs/{jid}/items/{aid}/readings",
                    json={"points": item_a["points"]})
    assert r.status_code == 200
    r = admin_s.post(f"{BASE_URL}/api/jobs/{jid}/items/{aid}/calculate")
    assert r.status_code == 200
    r = admin_s.post(f"{BASE_URL}/api/jobs/{jid}/items/{aid}/submit-review")
    assert r.status_code == 200
    r = rev_s.post(f"{BASE_URL}/api/jobs/{jid}/items/{aid}/review", json={"comments": "ok"})
    assert r.status_code == 200, r.text
    r = sig_s.post(f"{BASE_URL}/api/jobs/{jid}/items/{aid}/approve")
    assert r.status_code == 200, r.text
    cert_a = r.json()["certificate"]
    assert cert_a.get("verification_id")

    # Verify job state — A certified, B not
    j = admin_s.get(f"{BASE_URL}/api/jobs/{jid}").json()
    a = next(x for x in j["items"] if x["item_id"] == aid)
    b = next(x for x in j["items"] if x["item_id"] == bid)
    assert a["status"] == "certified"
    assert b["status"] != "certified"
    assert a["certificate"]["verification_id"] == cert_a["verification_id"]
    assert b.get("certificate") in (None, {}, )

    # Now certify B and confirm distinct verification_id
    admin_s.post(f"{BASE_URL}/api/jobs/{jid}/items/{bid}/calculate")
    admin_s.post(f"{BASE_URL}/api/jobs/{jid}/items/{bid}/submit-review")
    rev_s.post(f"{BASE_URL}/api/jobs/{jid}/items/{bid}/review", json={"comments": "ok"})
    rb = sig_s.post(f"{BASE_URL}/api/jobs/{jid}/items/{bid}/approve")
    assert rb.status_code == 200, rb.text
    cert_b = rb.json()["certificate"]
    assert cert_b["verification_id"] != cert_a["verification_id"], "verification_ids must be unique per item"

    # store for later tests
    pytest.CERT_A = cert_a
    pytest.CERT_B = cert_b
    pytest.MULTI_JID = jid
    pytest.MULTI_AID = aid
    pytest.MULTI_BID = bid


def test_certificate_pdf(admin_s):
    r = admin_s.get(f"{BASE_URL}/api/jobs/{pytest.MULTI_JID}/items/{pytest.MULTI_AID}/certificate/pdf")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"


def test_public_verify_resolves_correct_item():
    vid_a = pytest.CERT_A["verification_id"]
    r = requests.get(f"{BASE_URL}/api/verify/{vid_a}", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["serial_number"] == "SN-A"
    assert d["certificate_type"] == "NABL"
    assert d["points"] >= 1

    vid_b = pytest.CERT_B["verification_id"]
    r = requests.get(f"{BASE_URL}/api/verify/{vid_b}", timeout=30)
    assert r.status_code == 200
    d = r.json()
    assert d["serial_number"] == "SN-B"
    assert d["certificate_type"] == "Traceable"


def test_pre_release_check_per_item(admin_s):
    r = admin_s.get(f"{BASE_URL}/api/jobs/{pytest.MULTI_JID}/items/{pytest.MULTI_AID}/pre-release-check")
    assert r.status_code == 200
    d = r.json()
    assert "checks" in d and "ready" in d
    assert any(c["item"] == "Product selected" for c in d["checks"])


# ---------------- SRF at job level ----------------
def test_srf_multiproduct(admin_s):
    jid = pytest.MULTI_JID
    r = admin_s.post(f"{BASE_URL}/api/jobs/{jid}/prepare-srf")
    assert r.status_code == 200, r.text
    srf = r.json()["srf"]
    assert len(srf["products"]) == 2
    r = admin_s.post(f"{BASE_URL}/api/jobs/{jid}/send-srf")
    assert r.status_code == 200
    token = r.json()["token"]

    r = requests.get(f"{BASE_URL}/api/srf/{token}", timeout=30)
    assert r.status_code == 200
    pub = r.json()
    assert len(pub["srf"]["products"]) == 2

    r = requests.post(f"{BASE_URL}/api/srf/{token}/action",
                      json={"action": "approve", "customer_name": "Cust"}, timeout=30)
    assert r.status_code == 200
    assert r.json()["srf_status"] == "approved"


# ---------------- Add / remove product endpoints ----------------
def test_add_and_delete_item(admin_s):
    jid = pytest.MULTI_JID
    # get product/masters/template
    src = admin_s.get(f"{BASE_URL}/api/jobs/{jid}").json()
    it = src["items"][0]
    new_item = {"product_id": it["product_id"], "serial_number": "SN-C", "sr_number": "SR-C",
                "part_number": "PN-C", "url_number": "URL-C", "certificate_type": "NABL",
                "cal_date": "2026-01-16", "template_code": it.get("template_code", ""),
                "master_ids": it.get("master_ids", []), "points": []}
    r = admin_s.post(f"{BASE_URL}/api/jobs/{jid}/items", json=new_item)
    assert r.status_code == 200, r.text
    new_id = r.json()["item_id"]

    # delete non-certified new item
    r = admin_s.delete(f"{BASE_URL}/api/jobs/{jid}/items/{new_id}")
    assert r.status_code == 200

    # delete on certified should be blocked
    r = admin_s.delete(f"{BASE_URL}/api/jobs/{jid}/items/{pytest.MULTI_AID}")
    assert r.status_code == 400


def test_jobs_list_reflects_counts(admin_s):
    r = admin_s.get(f"{BASE_URL}/api/jobs")
    row = next((j for j in r.json() if j["id"] == pytest.MULTI_JID), None)
    assert row is not None
    assert row["product_count"] == 2
    assert row["certified_count"] == 2
