"""Tests for Document Control file attachment feature (iteration 4)."""
import os
import io
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or "http://localhost:8001"
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("mbhashik@gmail.com", "Yog@Admin2026")
QUALITY = ("quality@yog.local", "Quality@2026")
VIEWER = ("viewer@yog.local", "View@2026")


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=20)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    body = r.json()
    token = body.get("access_token")
    return s, token, body.get("user")


@pytest.fixture(scope="module")
def admin_session():
    s, t, u = _login(*ADMIN)
    return s, t, u


@pytest.fixture(scope="module")
def quality_session():
    s, t, u = _login(*QUALITY)
    return s, t, u


@pytest.fixture(scope="module")
def viewer_session():
    s, t, u = _login(*VIEWER)
    return s, t, u


@pytest.fixture(scope="module")
def test_document(admin_session):
    """Create a fresh document for attachment tests."""
    s, _, _ = admin_session
    payload = {
        "doc_number": "TEST-ATTACH-001",
        "title": "TEST attachment doc",
        "type": "SOP",
        "category": "quality",
        "revision": "0",
    }
    r = s.post(f"{API}/documents", json=payload, timeout=15)
    assert r.status_code in (200, 201), r.text
    did = r.json().get("id") or r.json().get("_id")
    assert did
    yield did
    # cleanup: try delete
    try:
        s.delete(f"{API}/documents/{did}", timeout=10)
    except Exception:
        pass


def _pdf_bytes(size=1024):
    header = b"%PDF-1.4\n%TEST\n"
    return header + b"0" * (size - len(header))


class TestDocAttachment:
    def test_upload_as_quality_manager(self, quality_session, test_document):
        s, _, _ = quality_session
        did = test_document
        files = {"file": ("test_upload.pdf", _pdf_bytes(2048), "application/pdf")}
        r = s.post(f"{API}/documents/{did}/attachment", files=files, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("ok") is True
        att = body.get("attachment")
        assert att and att["file_name"] == "test_upload.pdf"
        assert att["content_type"] == "application/pdf"
        assert att["size"] > 0
        assert att["file_path"]

    def test_get_documents_lists_attachment(self, admin_session, test_document):
        s, _, _ = admin_session
        r = s.get(f"{API}/documents", timeout=15)
        assert r.status_code == 200
        docs = r.json()
        found = [d for d in docs if (d.get("id") or d.get("_id")) == test_document]
        assert found, "document missing from list"
        assert found[0].get("attachment"), "attachment field missing"
        assert found[0]["attachment"]["file_name"] == "test_upload.pdf"

    def test_download_with_cookie(self, quality_session, test_document):
        s, _, _ = quality_session
        r = s.get(f"{API}/documents/{test_document}/attachment", timeout=30)
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content.startswith(b"%PDF")

    def test_download_with_bearer(self, quality_session, test_document):
        s, token, _ = quality_session
        # fresh session without cookies
        r = requests.get(
            f"{API}/documents/{test_document}/attachment",
            headers={"Authorization": f"Bearer {token}"}, timeout=30)
        assert r.status_code == 200
        assert r.content.startswith(b"%PDF")

    def test_download_without_auth_returns_401(self, test_document):
        r = requests.get(f"{API}/documents/{test_document}/attachment", timeout=15)
        assert r.status_code == 401

    def test_viewer_forbidden_from_upload(self, viewer_session, test_document):
        s, _, _ = viewer_session
        files = {"file": ("hack.pdf", _pdf_bytes(512), "application/pdf")}
        r = s.post(f"{API}/documents/{test_document}/attachment", files=files, timeout=15)
        assert r.status_code == 403, f"expected 403 got {r.status_code} {r.text}"

    def test_oversize_file_rejected(self, quality_session, test_document):
        s, _, _ = quality_session
        big = b"A" * (20 * 1024 * 1024 + 100)  # >20MB
        files = {"file": ("big.pdf", big, "application/pdf")}
        r = s.post(f"{API}/documents/{test_document}/attachment", files=files, timeout=60)
        assert r.status_code == 400, f"expected 400 got {r.status_code}"

    def test_reupload_replaces_attachment(self, quality_session, admin_session, test_document):
        s, _, _ = quality_session
        files = {"file": ("second.pdf", _pdf_bytes(4096), "application/pdf")}
        r = s.post(f"{API}/documents/{test_document}/attachment", files=files, timeout=30)
        assert r.status_code == 200
        # verify via GET docs list -> single attachment object, latest name
        sa, _, _ = admin_session
        docs = sa.get(f"{API}/documents", timeout=15).json()
        d = next(x for x in docs if (x.get("id") or x.get("_id")) == test_document)
        assert isinstance(d.get("attachment"), dict)
        assert d["attachment"]["file_name"] == "second.pdf"

    def test_history_contains_file_attached(self, admin_session, test_document):
        s, _, _ = admin_session
        r = s.get(f"{API}/documents/{test_document}/history", timeout=15)
        assert r.status_code == 200
        h = r.json()
        # find our document revision
        revs = h.get("revisions", [])
        assert revs
        # collect all history items across revisions
        items = []
        for rev in revs:
            items.extend(rev.get("history", []))
        actions = [it.get("action") for it in items]
        assert any("file attached" in (a or "") for a in actions), actions

    def test_audit_log_attach_file(self, admin_session, test_document):
        s, _, _ = admin_session
        r = s.get(f"{API}/audit", params={"entity_id": test_document}, timeout=15)
        assert r.status_code == 200
        logs = r.json()
        actions = [l.get("action") for l in logs]
        assert "attach_file" in actions, actions
