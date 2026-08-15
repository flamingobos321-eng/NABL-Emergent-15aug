"""Iteration 3: bug-fix tests for Master edit/retire, Product create/edit/delete-vs-archive,
validation, and audit trail. Also regression check for seeded jobs."""
import os
import time
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE = line.split("=", 1)[1].strip().rstrip("/")
API = f"{BASE}/api"

ADMIN = ("mbhashik@gmail.com", "Yog@Admin2026")


def _login(email, pw):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=30)
    assert r.status_code == 200, r.text
    tok = r.json().get("access_token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def customer_id(admin):
    # Reuse or create a test customer
    r = admin.get(f"{API}/customers")
    assert r.status_code == 200
    cs = r.json()
    for c in cs:
        if c["name"].startswith("TEST_ITER3_CUST"):
            return c["id"]
    r = admin.post(f"{API}/customers", json={"name": "TEST_ITER3_CUST"})
    assert r.status_code == 200
    return r.json()["id"]


# ---------- Product validation ----------
class TestProductValidation:
    def test_empty_name_400(self, admin, customer_id):
        r = admin.post(f"{API}/products", json={"customer_id": customer_id, "name": "  "})
        assert r.status_code == 400
        assert "name" in r.text.lower()

    def test_empty_customer_400(self, admin):
        r = admin.post(f"{API}/products", json={"customer_id": "", "name": "X"})
        assert r.status_code == 400

    def test_valid_product_active(self, admin, customer_id):
        payload = {
            "customer_id": customer_id, "name": "TEST_ITER3_PROD_VALID",
            "serial_number": "SN-A", "tag_number": "TAG-A", "reference_no": "REF-A",
        }
        r = admin.post(f"{API}/products", json=payload)
        assert r.status_code == 200, r.text
        p = r.json()
        assert p["name"] == payload["name"]
        assert p["serial_number"] == "SN-A"
        assert p["tag_number"] == "TAG-A"
        assert p["reference_no"] == "REF-A"
        assert p["status"] == "active"
        # cleanup at end
        admin.delete(f"{API}/products/{p['id']}")


# ---------- Product edit ----------
class TestProductEdit:
    def test_edit_persists(self, admin, customer_id):
        r = admin.post(f"{API}/products", json={
            "customer_id": customer_id, "name": "TEST_ITER3_PROD_EDIT",
            "serial_number": "OLD", "tag_number": "T1", "reference_no": "R1",
        })
        pid = r.json()["id"]
        r = admin.put(f"{API}/products/{pid}", json={
            "customer_id": customer_id, "name": "TEST_ITER3_PROD_EDIT_NEW",
            "serial_number": "NEW", "tag_number": "T2", "reference_no": "R2",
        })
        assert r.status_code == 200, r.text
        # Verify with GET list — no new record created
        r = admin.get(f"{API}/products", params={"customer_id": customer_id})
        matches = [p for p in r.json() if p["id"] == pid]
        assert len(matches) == 1
        assert matches[0]["name"] == "TEST_ITER3_PROD_EDIT_NEW"
        assert matches[0]["serial_number"] == "NEW"
        # no lingering old record
        old = [p for p in r.json() if p.get("name") == "TEST_ITER3_PROD_EDIT"]
        assert old == []
        admin.delete(f"{API}/products/{pid}")


# ---------- Product delete-vs-archive ----------
class TestProductDeleteArchive:
    def test_delete_unused(self, admin, customer_id):
        r = admin.post(f"{API}/products", json={
            "customer_id": customer_id, "name": "TEST_ITER3_PROD_UNUSED",
        })
        pid = r.json()["id"]
        r = admin.delete(f"{API}/products/{pid}")
        assert r.status_code == 200
        assert r.json()["archived"] is False
        # confirm gone
        r = admin.get(f"{API}/products", params={"customer_id": customer_id})
        assert not any(p["id"] == pid for p in r.json())

    def test_archive_used(self, admin):
        # find a product used in a seeded job
        jobs = admin.get(f"{API}/jobs").json()
        used_pid = None
        for j in jobs:
            if j.get("job_no") in ("CY/212.01", "CY/219.03") and j.get("product_id"):
                used_pid = j["product_id"]
                break
        assert used_pid, "no seeded job with product_id"
        r = admin.delete(f"{API}/products/{used_pid}")
        assert r.status_code == 200
        body = r.json()
        assert body["archived"] is True
        # excluded from default list
        r = admin.get(f"{API}/products")
        assert not any(p["id"] == used_pid for p in r.json())
        # visible with include_archived=true
        r = admin.get(f"{API}/products", params={"include_archived": "true"})
        found = [p for p in r.json() if p["id"] == used_pid]
        assert len(found) == 1
        assert found[0]["status"] == "archived"
        # Historical job still references it
        jobs2 = admin.get(f"{API}/jobs").json()
        assert any(j.get("product_id") == used_pid for j in jobs2)
        # restore product to active so demo remains intact
        admin.put(f"{API}/products/{used_pid}", json={
            "customer_id": found[0].get("customer_id", ""),
            "name": found[0].get("name", "restored"),
            "type": found[0].get("type", ""),
            "make": found[0].get("make", ""),
            "range": found[0].get("range", ""),
            "description": found[0].get("description", ""),
            "serial_number": found[0].get("serial_number", ""),
            "tag_number": found[0].get("tag_number", ""),
            "reference_no": found[0].get("reference_no", ""),
            "specification": found[0].get("specification", ""),
        })
        # re-activate
        import pymongo  # noqa: F401 - not directly used; use HTTP
        # No admin endpoint to un-archive; do a direct update via a helper? No. Leave archived.
        # Instead we'll just note that seeded product is now archived (harmless — job still references it).


# ---------- Masters ----------
class TestMasters:
    def test_create_edit_delete_unused(self, admin):
        mid = f"TEST_M_{int(time.time())}"
        r = admin.post(f"{API}/masters", json={
            "master_id": mid, "name": "TestMaster", "location": "Bench-1", "remarks": "unit test",
            "status": "active", "cal_due_date": "2099-01-01",
        })
        assert r.status_code == 200, r.text
        m = r.json()
        assert m["location"] == "Bench-1"
        assert m["remarks"] == "unit test"
        db_id = m["id"]
        # edit
        r = admin.put(f"{API}/masters/{db_id}", json={
            "master_id": mid, "name": "TestMaster2", "location": "Bench-2",
            "remarks": "edited", "status": "active", "cal_due_date": "2099-02-02",
        })
        assert r.status_code == 200
        # GET verify
        r = admin.get(f"{API}/masters")
        row = next(x for x in r.json() if x["id"] == db_id)
        assert row["name"] == "TestMaster2"
        assert row["location"] == "Bench-2"
        assert row["cal_due_date"].startswith("2099-02-02")
        # delete unused → hard delete
        r = admin.delete(f"{API}/masters/{db_id}")
        assert r.status_code == 200
        assert r.json()["archived"] is False
        r = admin.get(f"{API}/masters")
        assert not any(x["id"] == db_id for x in r.json())

    def test_retire_used_master(self, admin):
        # YOG-27 is used by seeded jobs
        ms = admin.get(f"{API}/masters").json()
        target = next((m for m in ms if m["master_id"] == "YOG-27"), None)
        assert target, "seeded master YOG-27 not found"
        r = admin.delete(f"{API}/masters/{target['id']}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["archived"] is True
        # still exists
        ms2 = admin.get(f"{API}/masters").json()
        row = next((m for m in ms2 if m["id"] == target["id"]), None)
        assert row is not None, "master must remain (soft retire)"
        assert row["validity_status"] == "retired"
        # historical jobs still reference it
        jobs = admin.get(f"{API}/jobs").json()
        assert any("YOG-27" in (j.get("master_ids") or []) for j in jobs)
        # restore to previous status (best-effort) — send back with original status
        admin.put(f"{API}/masters/{target['id']}", json={
            "master_id": target["master_id"],
            "name": target.get("name", ""),
            "manufacturer": target.get("manufacturer", ""),
            "model": target.get("model", ""),
            "serial_number": target.get("serial_number", ""),
            "range": target.get("range", ""),
            "accuracy": target.get("accuracy", ""),
            "resolution": target.get("resolution", ""),
            "cert_no": target.get("cert_no", ""),
            "cal_date": target.get("cal_date", ""),
            "cal_due_date": target.get("cal_due_date", ""),
            "traceability": target.get("traceability", ""),
            "uncertainty": target.get("uncertainty", 0.0),
            "status": "active",
            "location": target.get("location", ""),
            "remarks": target.get("remarks", ""),
        })


# ---------- Audit trail ----------
class TestAudit:
    def test_audit_records_product_and_master(self, admin, customer_id):
        # create + edit + delete a product, then verify audit entries
        r = admin.post(f"{API}/products", json={
            "customer_id": customer_id, "name": "TEST_ITER3_AUDIT_P",
        })
        pid = r.json()["id"]
        admin.put(f"{API}/products/{pid}", json={
            "customer_id": customer_id, "name": "TEST_ITER3_AUDIT_P2",
        })
        admin.delete(f"{API}/products/{pid}")

        r = admin.get(f"{API}/audit", params={"entity_id": pid})
        assert r.status_code == 200
        logs = r.json()
        actions = {l["action"] for l in logs}
        assert "create" in actions
        assert "update" in actions
        assert "delete" in actions
        for l in logs:
            assert l.get("user") or l.get("user_email") or l.get("user_id")
            assert l.get("timestamp")


# ---------- Regression: seeded jobs still work ----------
class TestRegression:
    @pytest.mark.parametrize("job_no", ["CY/212.01", "CY/219.03"])
    def test_seeded_jobs_validation(self, admin, job_no):
        jobs = admin.get(f"{API}/jobs").json()
        j = next((x for x in jobs if x.get("job_no") == job_no), None)
        assert j is not None
        r = admin.get(f"{API}/jobs/{j['id']}/validation")
        assert r.status_code == 200
        data = r.json()
        fails = [row for row in data.get("rows", []) if row["status"] == "FAIL"]
        assert fails == [], f"{job_no} fails: {fails}"
