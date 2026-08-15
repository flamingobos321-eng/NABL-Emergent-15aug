"""Iteration 5 bug fix tests: document create validation + Obsolete transition."""
import os
import pytest
import requests
from pathlib import Path

def _load_url():
    if os.environ.get("REACT_APP_BACKEND_URL"):
        return os.environ["REACT_APP_BACKEND_URL"]
    for line in Path("/app/frontend/.env").read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("REACT_APP_BACKEND_URL not found")

BASE = _load_url().rstrip("/")
API = f"{BASE}/api"

QUALITY = {"email": "quality@yog.local", "password": "Quality@2026"}


@pytest.fixture(scope="module")
def qsess():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=QUALITY, timeout=30)
    assert r.status_code == 200, r.text
    return s


def _count(sess):
    r = sess.get(f"{API}/documents", timeout=30)
    assert r.status_code == 200
    return len(r.json()), r.json()


# ---------- Backend validation ----------
def test_create_empty_doc_number_rejected(qsess):
    before, _ = _count(qsess)
    r = qsess.post(f"{API}/documents", json={
        "doc_number": "", "title": "Some title", "category": "manual", "revision": "01",
        "file_url": "", "effective_date": "", "review_date": "",
        "prepared_by": "", "reviewed_by": "", "approved_by": "", "change_note": ""
    })
    assert r.status_code == 400
    assert "required" in r.text.lower()
    after, _ = _count(qsess)
    assert after == before, "No record should be created on invalid payload"


def test_create_empty_title_rejected(qsess):
    before, _ = _count(qsess)
    r = qsess.post(f"{API}/documents", json={
        "doc_number": "TEST-X1", "title": "   ", "category": "manual", "revision": "01",
        "file_url": "", "effective_date": "", "review_date": "",
        "prepared_by": "", "reviewed_by": "", "approved_by": "", "change_note": ""
    })
    assert r.status_code == 400
    after, _ = _count(qsess)
    assert after == before


def test_create_both_empty_rejected(qsess):
    before, _ = _count(qsess)
    r = qsess.post(f"{API}/documents", json={
        "doc_number": "  ", "title": "", "category": "manual", "revision": "01",
        "file_url": "", "effective_date": "", "review_date": "",
        "prepared_by": "", "reviewed_by": "", "approved_by": "", "change_note": ""
    })
    assert r.status_code == 400
    after, _ = _count(qsess)
    assert after == before


# ---------- Valid create + obsolete lifecycle ----------
@pytest.fixture(scope="module")
def created_doc(qsess):
    import uuid
    dn = f"TEST-BUG5-{uuid.uuid4().hex[:6].upper()}"
    r = qsess.post(f"{API}/documents", json={
        "doc_number": dn, "title": "Iter5 bug test doc", "category": "manual", "revision": "01",
        "file_url": "", "effective_date": "", "review_date": "",
        "prepared_by": "Quality", "reviewed_by": "", "approved_by": "", "change_note": "init"
    })
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "draft"
    return d


def test_created_doc_is_draft(created_doc):
    assert created_doc["doc_number"].startswith("TEST-BUG5-")
    assert created_doc["status"] == "draft"


def test_full_lifecycle_and_manual_obsolete(qsess, created_doc):
    did = created_doc["id"]
    # draft -> under_review
    r = qsess.post(f"{API}/documents/{did}/status", json={"status": "under_review", "note": "review"})
    assert r.status_code == 200 and r.json()["status"] == "under_review"
    # -> approved
    r = qsess.post(f"{API}/documents/{did}/status", json={"status": "approved", "note": "ok"})
    assert r.status_code == 200 and r.json()["status"] == "approved"
    # -> effective
    r = qsess.post(f"{API}/documents/{did}/status", json={"status": "effective", "note": "go"})
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "effective"
    assert j["is_current"] is True
    # -> obsolete (manual)
    r = qsess.post(f"{API}/documents/{did}/status", json={"status": "obsolete", "note": "retire"})
    assert r.status_code == 200
    j = r.json()
    assert j["status"] == "obsolete"
    assert j["is_current"] is False


def test_revise_effective_supersedes_previous(qsess):
    """Regression: revise + effective should auto-obsolete the prior effective revision."""
    import uuid
    dn = f"TEST-BUG5R-{uuid.uuid4().hex[:6].upper()}"
    # create + push to effective
    r = qsess.post(f"{API}/documents", json={
        "doc_number": dn, "title": "Revise test", "category": "manual", "revision": "01",
        "file_url": "", "effective_date": "", "review_date": "",
        "prepared_by": "Q", "reviewed_by": "", "approved_by": "", "change_note": ""
    })
    assert r.status_code == 200
    did = r.json()["id"]
    for s in ("under_review", "approved", "effective"):
        r = qsess.post(f"{API}/documents/{did}/status", json={"status": s, "note": ""})
        assert r.status_code == 200
    # revise
    r = qsess.post(f"{API}/documents/{did}/revise", json={"status": "draft", "note": "rev2"})
    assert r.status_code == 200
    new_id = r.json()["id"]
    assert r.json()["revision"] == "02"
    # promote new rev to effective
    for s in ("under_review", "approved", "effective"):
        r = qsess.post(f"{API}/documents/{new_id}/status", json={"status": s, "note": ""})
        assert r.status_code == 200
    # old should be obsolete now
    r = qsess.get(f"{API}/documents", timeout=30)
    docs = [d for d in r.json() if d["doc_number"] == dn]
    old = next(d for d in docs if d["revision"] == "01")
    assert old["status"] == "obsolete"
    assert old["is_current"] is False
