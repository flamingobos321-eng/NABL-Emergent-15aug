from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import os
import json
import re
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any

from fastapi import FastAPI, APIRouter, Request, Response, HTTPException, Depends, UploadFile, File, Form, Query, Header
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr
from bson import ObjectId
from pymongo import ReturnDocument

import auth as authmod
import calc as calcmod
import storage as storagemod
from pdf_gen import build_certificate_pdf

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="YOG Calibration Lab")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("yog")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def clean(doc):
    if not doc:
        return doc
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    doc.pop("password_hash", None)
    return doc


# ---------------- Auth dependency / RBAC ----------------
async def current_user(request: Request):
    return await authmod.resolve_user(request, db)


def require(*roles):
    async def dep(user=Depends(current_user)):
        if roles and user["role"] not in roles and user["role"] != "admin":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return dep


async def audit(entity_type, entity_id, action, user, field=None, old=None, new=None, reason=None):
    await db.audit_logs.insert_one({
        "entity_type": entity_type, "entity_id": str(entity_id), "action": action,
        "field": field, "old_value": old, "new_value": new, "reason": reason,
        "user_id": user.get("id"), "user_name": user.get("name"), "user_role": user.get("role"),
        "timestamp": now_iso(),
    })


# ---------------- Models ----------------
class LoginIn(BaseModel):
    email: str
    password: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "viewer"


class CustomerIn(BaseModel):
    name: str
    address: str = ""
    contact: str = ""
    email: str = ""
    phone: str = ""


class ProductIn(BaseModel):
    customer_id: str
    name: str
    type: str = ""
    make: str = ""
    range: str = ""
    description: str = ""
    serial_number: str = ""
    tag_number: str = ""
    reference_no: str = ""
    specification: str = ""


class MasterIn(BaseModel):
    master_id: str
    name: str
    manufacturer: str = ""
    model: str = ""
    serial_number: str = ""
    range: str = ""
    accuracy: str = ""
    resolution: str = ""
    cert_no: str = ""
    cal_date: str = ""
    cal_due_date: str = ""
    traceability: str = ""
    uncertainty: float = 0.0
    status: str = "active"
    location: str = ""
    remarks: str = ""


class DeleteIn(BaseModel):
    reason: str = ""


class ComponentIn(BaseModel):
    label: str
    source: str = ""
    distribution: str  # normal_k2 | rect_root3 | typeA
    estimate: float = 0.0
    ci: float = 1.0


class PointIn(BaseModel):
    point_label: str
    nominal: float = 0.0
    master_readings: List[float] = []
    uut_readings: List[float] = []
    point_deviation: float = 0.0
    components: List[ComponentIn] = []
    cmc_floor: Optional[float] = None
    excel_reference: Optional[dict] = None


DEFAULT_ENV = {"humidity": "55 \u00b115 % RH", "ambient_temp": "25 \u00b14 \u00b0C"}


class JobItemIn(BaseModel):
    """One product within a calibration job — a full independent calibration record."""
    item_id: Optional[str] = None
    product_id: str
    serial_number: str = ""
    tag_number: str = ""
    sr_number: str = ""
    part_number: str = ""
    url_number: str = ""
    certificate_type: str = "NABL"
    method: str = "WI \u2013 TECH/11"
    reference_standard: str = ""
    cal_date: str = ""
    issue_date: str = ""
    item_received_date: str = ""
    environmental: dict = Field(default_factory=lambda: dict(DEFAULT_ENV))
    master_ids: List[str] = []
    template_code: str = ""
    points: List[PointIn] = []


class JobCreate(BaseModel):
    job_no: str = ""
    work_order_ref: str = ""
    work_order_date: str = ""
    work_order_notes: str = ""
    customer_id: str
    items: List[JobItemIn] = []


class ReadingsUpdate(BaseModel):
    points: List[PointIn]


class ReviewIn(BaseModel):
    comments: str = ""


class RejectIn(BaseModel):
    reason: str = ""


class SRFUpdate(BaseModel):
    srf: dict


class SRFAction(BaseModel):
    action: str  # approve | request_correction | reject
    customer_name: str = ""
    comments: str = ""


class DocumentIn(BaseModel):
    doc_number: str
    title: str
    category: str
    revision: str = "01"
    effective_date: str = ""
    review_date: str = ""
    prepared_by: str = ""
    reviewed_by: str = ""
    approved_by: str = ""
    file_url: str = ""
    change_note: str = ""


class DocStatusIn(BaseModel):
    status: str = ""
    note: str = ""


# ---------------- Auth routes ----------------
def set_cookies(resp, uid, email, role):
    at = authmod.create_access_token(uid, email, role)
    rt = authmod.create_refresh_token(uid)
    resp.set_cookie("access_token", at, httponly=True, secure=True, samesite="none", max_age=43200, path="/")
    resp.set_cookie("refresh_token", rt, httponly=True, secure=True, samesite="none", max_age=604800, path="/")
    return at


@api.post("/auth/login")
async def login(body: LoginIn, response: Response):
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not authmod.verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = set_cookies(response, str(user["_id"]), email, user["role"])
    u = clean(user)
    return {"user": u, "access_token": token}


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}


@api.get("/auth/me")
async def me(user=Depends(current_user)):
    return user


# ---------------- Users ----------------
@api.get("/users")
async def list_users(user=Depends(require("admin"))):
    return [clean(u) for u in await db.users.find().to_list(500)]


@api.post("/users")
async def create_user(body: UserCreate, user=Depends(require("admin"))):
    if body.role not in authmod.ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    if await db.users.find_one({"email": body.email.lower()}):
        raise HTTPException(status_code=400, detail="Email already exists")
    doc = {"email": body.email.lower(), "password_hash": authmod.hash_password(body.password),
           "name": body.name, "role": body.role, "created_at": now_iso()}
    res = await db.users.insert_one(doc)
    await audit("user", res.inserted_id, "create", user, new=body.email)
    return clean(await db.users.find_one({"_id": res.inserted_id}))


@api.delete("/users/{uid}")
async def delete_user(uid: str, user=Depends(require("admin"))):
    await db.users.delete_one({"_id": ObjectId(uid)})
    await audit("user", uid, "delete", user)
    return {"ok": True}


# ---------------- Customers & Products ----------------
@api.get("/customers")
async def list_customers(user=Depends(current_user)):
    return [clean(c) for c in await db.customers.find().sort("name", 1).to_list(1000)]


@api.post("/customers")
async def create_customer(body: CustomerIn, user=Depends(require("admin", "technician"))):
    doc = {**body.model_dump(), "created_at": now_iso()}
    res = await db.customers.insert_one(doc)
    await audit("customer", res.inserted_id, "create", user, new=body.name)
    return clean(await db.customers.find_one({"_id": res.inserted_id}))


@api.put("/customers/{cid}")
async def update_customer(cid: str, body: CustomerIn, user=Depends(require("admin", "technician"))):
    await db.customers.update_one({"_id": ObjectId(cid)}, {"$set": body.model_dump()})
    await audit("customer", cid, "update", user)
    return clean(await db.customers.find_one({"_id": ObjectId(cid)}))


@api.get("/products")
async def list_products(customer_id: Optional[str] = None, include_archived: bool = False, user=Depends(current_user)):
    q = {"customer_id": customer_id} if customer_id else {}
    if not include_archived:
        q["status"] = {"$ne": "archived"}
    return [clean(p) for p in await db.products.find(q).to_list(1000)]


@api.post("/products")
async def create_product(body: ProductIn, user=Depends(require("admin", "technician"))):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Product name is required")
    if not body.customer_id.strip():
        raise HTTPException(status_code=400, detail="Customer is required")
    doc = {**body.model_dump(), "status": "active", "created_at": now_iso()}
    res = await db.products.insert_one(doc)
    await audit("product", res.inserted_id, "create", user, new=body.name)
    return clean(await db.products.find_one({"_id": res.inserted_id}))


@api.put("/products/{pid}")
async def update_product(pid: str, body: ProductIn, user=Depends(require("admin", "technician"))):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Product name is required")
    old = await db.products.find_one({"_id": ObjectId(pid)})
    await db.products.update_one({"_id": ObjectId(pid)}, {"$set": body.model_dump()})
    await audit("product", pid, "update", user, old=(old or {}).get("name"), new=body.name)
    return clean(await db.products.find_one({"_id": ObjectId(pid)}))


@api.delete("/products/{pid}")
async def delete_product(pid: str, user=Depends(require("admin", "technician"))):
    used = await db.jobs.count_documents({"items.product_id": pid})
    if used > 0:
        await db.products.update_one({"_id": ObjectId(pid)}, {"$set": {"status": "archived"}})
        await audit("product", pid, "archive", user, reason=f"Used in {used} job(s) — archived, not deleted")
        return {"archived": True, "message": "Product is used in calibration records; it was archived (not deleted) to preserve history."}
    await db.products.delete_one({"_id": ObjectId(pid)})
    await audit("product", pid, "delete", user, reason="Unused product deleted")
    return {"archived": False, "message": "Product deleted."}


# ---------------- Masters ----------------
def master_status(m):
    if m.get("status") in ("retired", "inactive", "out_of_service"):
        return m.get("status")
    due = m.get("cal_due_date")
    if not due:
        return "unknown"
    try:
        d = datetime.fromisoformat(due[:10]).date()
    except Exception:
        return "unknown"
    today = datetime.now(timezone.utc).date()
    if d < today:
        return "expired"
    if (d - today).days <= 30:
        return "expiring"
    return "valid"


@api.get("/masters")
async def list_masters(user=Depends(current_user)):
    out = []
    for m in await db.masters.find().sort("master_id", 1).to_list(1000):
        c = clean(m)
        c["validity_status"] = master_status(m)
        out.append(c)
    return out


@api.post("/masters")
async def create_master(body: MasterIn, user=Depends(require("admin", "technician"))):
    if not body.master_id.strip() or not body.name.strip():
        raise HTTPException(status_code=400, detail="Master ID and Instrument name are required")
    doc = {**body.model_dump(), "created_at": now_iso()}
    res = await db.masters.insert_one(doc)
    await audit("master", res.inserted_id, "create", user, new=body.master_id)
    return clean(await db.masters.find_one({"_id": res.inserted_id}))


@api.put("/masters/{mid}")
async def update_master(mid: str, body: MasterIn, user=Depends(require("admin", "technician"))):
    old = await db.masters.find_one({"_id": ObjectId(mid)})
    await db.masters.update_one({"_id": ObjectId(mid)}, {"$set": body.model_dump()})
    await audit("master", mid, "update", user, old=(old or {}).get("cal_due_date"), new=body.cal_due_date)
    return clean(await db.masters.find_one({"_id": ObjectId(mid)}))


@api.delete("/masters/{mid}")
async def delete_master(mid: str, user=Depends(require("admin", "technician"))):
    m = await db.masters.find_one({"_id": ObjectId(mid)})
    if not m:
        raise HTTPException(status_code=404, detail="Master not found")
    used = await db.jobs.count_documents({"items.master_ids": m.get("master_id")})
    if used > 0:
        await db.masters.update_one({"_id": ObjectId(mid)}, {"$set": {"status": "retired"}})
        await audit("master", mid, "retire", user, old=m.get("status"), new="retired",
                    reason=f"Used in {used} calibration(s) — retired, not deleted")
        return {"archived": True, "message": "Master is used in calibration records; it was marked Retired (not deleted) to preserve history."}
    await db.masters.delete_one({"_id": ObjectId(mid)})
    await audit("master", mid, "delete", user, reason="Unused master deleted")
    return {"archived": False, "message": "Master deleted."}


# ----- Master external calibration certificate attachment -----
@api.post("/masters/{mid}/attachment")
async def upload_master_cert(mid: str, file: UploadFile = File(...),
                             cert_no: str = Form(""), cal_agency: str = Form(""),
                             cal_date: str = Form(""), cal_due_date: str = Form(""),
                             notes: str = Form(""),
                             user=Depends(require("admin", "technician", "quality"))):
    m = await db.masters.find_one({"_id": ObjectId(mid)})
    if not m:
        raise HTTPException(status_code=404, detail="Master not found")
    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 20 MB limit")
    ext = (file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "bin")
    ctype = file.content_type or storagemod.MIME_TYPES.get(ext, "application/octet-stream")
    path = f"{storagemod.APP_NAME}/masters/{mid}/{uuid.uuid4()}.{ext}"
    try:
        result = storagemod.put_object(path, data, ctype)
    except Exception as e:
        logger.error(f"Storage upload failed: {e}")
        raise HTTPException(status_code=502, detail="File storage upload failed")
    prev = m.get("attachment")
    version = (m.get("attachment_version") or 0) + 1
    att = {
        "file_path": result["path"], "file_name": file.filename,
        "content_type": ctype, "size": result.get("size", len(data)),
        "version": version,
        "cert_no": cert_no or m.get("cert_no", ""),
        "cal_agency": cal_agency or m.get("traceability", ""),
        "cal_date": cal_date or m.get("cal_date", ""),
        "cal_due_date": cal_due_date or m.get("cal_due_date", ""),
        "notes": notes,
        "uploaded_by": user["name"], "uploaded_at": now_iso(),
    }
    updates = {"attachment": att, "attachment_version": version}
    # keep the master's structured cal fields in sync (kept separate from the file)
    if cert_no:
        updates["cert_no"] = cert_no
    if cal_agency:
        updates["traceability"] = cal_agency
    if cal_date:
        updates["cal_date"] = cal_date
    if cal_due_date:
        updates["cal_due_date"] = cal_due_date
    push = {"$push": {"attachment_history": prev}} if prev else {}
    await db.masters.update_one({"_id": ObjectId(mid)}, {"$set": updates, **push})
    was = master_status(m)
    note = (f"Replaced cal cert (v{prev.get('version')} '{prev.get('cert_no','')}' -> v{version} '{att['cert_no']}')"
            if prev else f"Attached cal cert v{version} '{att['cert_no']}'")
    if was in ("expired", "retired", "inactive", "out_of_service"):
        note += f" — NOTE: master was '{was}' at time of change"
    await audit("master", mid, "cal_cert_replace" if prev else "cal_cert_attach", user,
                old=(prev or {}).get("cert_no"), new=att["cert_no"], reason=note)
    return {"ok": True, "attachment": att}


@api.get("/masters/{mid}/attachment")
async def download_master_cert(mid: str, request: Request, version: Optional[int] = None,
                               authorization: str = Header(None)):
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        authmod.decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    m = await db.masters.find_one({"_id": ObjectId(mid)})
    if not m:
        raise HTTPException(status_code=404, detail="Master not found")
    att = m.get("attachment")
    if version is not None and (not att or att.get("version") != version):
        att = next((h for h in m.get("attachment_history", []) if h and h.get("version") == version), None)
    if not att:
        raise HTTPException(status_code=404, detail="No calibration certificate attached")
    try:
        content, ctype = storagemod.get_object(att["file_path"])
    except Exception as e:
        logger.error(f"Storage download failed: {e}")
        raise HTTPException(status_code=502, detail="File storage download failed")
    return Response(content=content, media_type=att.get("content_type", ctype),
                    headers={"Content-Disposition": f'inline; filename="{att.get("file_name", "master_cert")}"'})


# ---------------- Templates ----------------
@api.get("/templates")
async def list_templates(user=Depends(current_user)):
    return [clean(t) for t in await db.templates.find().to_list(100)]


# ================= Jobs (container) + Items (per-product calibration records) =================
async def next_seq(name):
    doc = await db.counters.find_one_and_update(
        {"_id": name}, {"$inc": {"seq": 1}}, upsert=True, return_document=ReturnDocument.AFTER)
    return doc["seq"]


async def hydrate_standards(master_ids):
    stds = []
    for mid in master_ids:
        m = await db.masters.find_one({"master_id": mid})
        if m:
            att = m.get("attachment") or {}
            stds.append({
                "name": m["name"], "uncertainty": m.get("uncertainty", 0),
                "id_no": m.get("master_id", ""), "certified_by": m.get("traceability", ""),
                "report_no": m.get("cert_no", ""), "validity": m.get("cal_due_date", ""),
                "master_oid": str(m["_id"]),
                "cal_date": m.get("cal_date", ""),
                "attachment_version": att.get("version"),
                "attachment_file_name": att.get("file_name"),
                "has_attachment": bool(att),
            })
    return stds


def next_cal_date(cal_date):
    try:
        d = datetime.fromisoformat(cal_date[:10])
        return (d + timedelta(days=364)).date().isoformat()
    except Exception:
        return ""


async def gen_cert_no(item):
    """Certificate number is assigned at issuance (never at job/product creation)."""
    tag = "NABL" if str(item.get("certificate_type", "NABL")).upper() == "NABL" else "TRC"
    year = datetime.now(timezone.utc).year
    return f"YEP/{tag}/{year}/{await next_seq('cert'):05d}"


STATUS_ORDER = ["draft", "readings_entered", "calculated", "in_review", "reviewed", "certified"]


def job_rollup_status(job):
    items = job.get("items", [])
    if not items:
        return "draft"
    sts = [it.get("status", "draft") for it in items]
    if all(s == "certified" for s in sts):
        return "certified"
    if any(s == "rejected" for s in sts):
        return "rejected"
    return min(sts, key=lambda s: STATUS_ORDER.index(s) if s in STATUS_ORDER else 0)


async def build_item(data: dict):
    """Prepare a fresh per-product calibration item document from an incoming payload."""
    points = data.get("points", [])
    points = [p if isinstance(p, dict) else p.model_dump() for p in points]
    return {
        "item_id": data.get("item_id") or uuid.uuid4().hex,
        "product_id": data.get("product_id", ""),
        "serial_number": data.get("serial_number", ""),
        "tag_number": data.get("tag_number", ""),
        "sr_number": data.get("sr_number", ""),
        "part_number": data.get("part_number", ""),
        "url_number": data.get("url_number", ""),
        "cert_no": "",
        "certificate_type": data.get("certificate_type", "NABL"),
        "method": data.get("method", "WI \u2013 TECH/11"),
        "reference_standard": data.get("reference_standard", ""),
        "cal_date": data.get("cal_date", ""),
        "issue_date": data.get("issue_date", ""),
        "item_received_date": data.get("item_received_date", ""),
        "environmental": data.get("environmental") or dict(DEFAULT_ENV),
        "master_ids": data.get("master_ids", []),
        "template_code": data.get("template_code", ""),
        "standards_used": await hydrate_standards(data.get("master_ids", [])),
        "recommended_next_date": next_cal_date(data.get("cal_date", "")),
        "points": points,
        "computed": [],
        "status": "draft",
        "review": None,
        "approval": None,
        "certificate": None,
    }


def find_item(job, item_id):
    for it in job.get("items", []):
        if it.get("item_id") == item_id:
            return it
    return None


async def replace_item(jid, items, item):
    for i, it in enumerate(items):
        if it["item_id"] == item["item_id"]:
            items[i] = item
            break
    await db.jobs.update_one({"_id": ObjectId(jid)}, {"$set": {"items": items}})


async def _get_job_item(jid, item_id):
    j = await db.jobs.find_one({"_id": ObjectId(jid)})
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    it = find_item(j, item_id)
    if not it:
        raise HTTPException(status_code=404, detail="Product not found in this job")
    return j, it


async def hydrate_item(it):
    prod = await db.products.find_one({"_id": ObjectId(it["product_id"])}) if it.get("product_id") else None
    out = dict(it)
    out["product"] = clean(prod) if prod else None
    out["product_name"] = prod["name"] if prod else ""
    return out


def compute_points(points):
    results = []
    for p in points:
        r = calcmod.compute_point(
            p["master_readings"], p["uut_readings"], p.get("point_deviation", 0.0),
            p["components"], p.get("cmc_floor"),
        )
        results.append({
            "point_label": p.get("point_label"), "nominal": p.get("nominal"),
            "master_readings": p["master_readings"], "uut_readings": p["uut_readings"],
            "point_deviation": p.get("point_deviation", 0.0),
            "cmc_floor": p.get("cmc_floor"), "components": p["components"],
            "results": r,
        })
    return results


@api.get("/jobs")
async def list_jobs(user=Depends(current_user)):
    out = []
    for j in await db.jobs.find().sort("created_at", -1).to_list(1000):
        c = clean(j)
        cust = await db.customers.find_one({"_id": ObjectId(c["customer_id"])}) if c.get("customer_id") else None
        items = c.get("items", [])
        names = []
        for it in items:
            prod = await db.products.find_one({"_id": ObjectId(it["product_id"])}) if it.get("product_id") else None
            names.append(prod["name"] if prod else "")
        c["customer_name"] = cust["name"] if cust else ""
        c["product_count"] = len(items)
        c["certified_count"] = sum(1 for it in items if it.get("status") == "certified")
        c["product_names"] = names
        c["cal_date"] = items[0].get("cal_date") if items else ""
        c["status"] = job_rollup_status(c)
        out.append(c)
    return out


@api.get("/jobs/{jid}")
async def get_job(jid: str, user=Depends(current_user)):
    j = await db.jobs.find_one({"_id": ObjectId(jid)})
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    c = clean(j)
    cust = await db.customers.find_one({"_id": ObjectId(c["customer_id"])}) if c.get("customer_id") else None
    c["customer"] = clean(cust) if cust else None
    c["items"] = [await hydrate_item(it) for it in c.get("items", [])]
    c["status"] = job_rollup_status(c)
    return c


@api.post("/jobs")
async def create_job(body: JobCreate, user=Depends(require("admin", "technician"))):
    if not body.work_order_ref.strip():
        raise HTTPException(status_code=400, detail="Work Order Number is required")
    if not body.items:
        raise HTTPException(status_code=400, detail="Add at least one product to the job")
    items = [await build_item(it.model_dump()) for it in body.items]
    doc = {
        "job_no": body.job_no or f"CAL-{datetime.now(timezone.utc).year}-{await next_seq('job'):05d}",
        "work_order_ref": body.work_order_ref, "work_order_date": body.work_order_date,
        "work_order_notes": body.work_order_notes, "work_order_source": "Billing/ERP",
        "customer_id": body.customer_id,
        "items": items,
        "srf": None, "srf_no": None, "srf_token": None, "srf_status": "none", "srf_approval": None,
        "technician_id": user["id"], "technician_name": user["name"],
        "created_by": user["id"], "created_at": now_iso(),
    }
    res = await db.jobs.insert_one(doc)
    await audit("job", res.inserted_id, "create", user, field="work_order_ref",
                new=f"{doc['job_no']} (WO {body.work_order_ref}) · {len(items)} product(s)")
    return clean(await db.jobs.find_one({"_id": res.inserted_id}))


@api.post("/jobs/{jid}/items")
async def add_item(jid: str, body: JobItemIn, user=Depends(require("admin", "technician"))):
    j = await db.jobs.find_one({"_id": ObjectId(jid)})
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    item = await build_item(body.model_dump())
    items = j.get("items", []) + [item]
    await db.jobs.update_one({"_id": ObjectId(jid)}, {"$set": {"items": items}})
    await audit("job", jid, "add_product", user, new=item["item_id"])
    return {"ok": True, "item_id": item["item_id"]}


@api.delete("/jobs/{jid}/items/{item_id}")
async def delete_item(jid: str, item_id: str, user=Depends(require("admin", "technician"))):
    j, it = await _get_job_item(jid, item_id)
    if it.get("status") == "certified":
        raise HTTPException(status_code=400, detail="Cannot remove a certified product")
    items = [x for x in j.get("items", []) if x["item_id"] != item_id]
    await db.jobs.update_one({"_id": ObjectId(jid)}, {"$set": {"items": items}})
    await audit("job", jid, "remove_product", user, old=item_id)
    return {"ok": True}


@api.put("/jobs/{jid}/items/{item_id}/readings")
async def update_readings(jid: str, item_id: str, body: ReadingsUpdate, user=Depends(require("admin", "technician"))):
    j, it = await _get_job_item(jid, item_id)
    if it.get("status") in ("approved", "certified"):
        raise HTTPException(status_code=400, detail="Product is locked after approval")
    old_points = it.get("points", [])
    new_points = [p.model_dump() for p in body.points]
    for i, np in enumerate(new_points):
        op = old_points[i] if i < len(old_points) else {}
        if op.get("master_readings") != np.get("master_readings"):
            await audit("job", jid, "reading_change", user, field=f"item[{item_id}].point[{i}].master_readings",
                        old=op.get("master_readings"), new=np.get("master_readings"))
        if op.get("uut_readings") != np.get("uut_readings"):
            await audit("job", jid, "reading_change", user, field=f"item[{item_id}].point[{i}].uut_readings",
                        old=op.get("uut_readings"), new=np.get("uut_readings"))
    it["points"] = new_points
    it["status"] = "readings_entered"
    await replace_item(jid, j["items"], it)
    return {"ok": True}


@api.post("/jobs/{jid}/items/{item_id}/calculate")
async def calculate_item(jid: str, item_id: str, user=Depends(current_user)):
    j, it = await _get_job_item(jid, item_id)
    results = compute_points(it.get("points", []))
    it["computed"] = results
    if it.get("status") in ("draft", "readings_entered"):
        it["status"] = "calculated"
    await replace_item(jid, j["items"], it)
    return {"results": results}


@api.post("/jobs/{jid}/items/{item_id}/submit-review")
async def submit_review(jid: str, item_id: str, user=Depends(require("admin", "technician"))):
    j, it = await _get_job_item(jid, item_id)
    it["status"] = "in_review"
    await replace_item(jid, j["items"], it)
    await audit("job", jid, "submit_review", user, field=item_id)
    return {"ok": True}


@api.post("/jobs/{jid}/items/{item_id}/review")
async def review_item(jid: str, item_id: str, body: ReviewIn, user=Depends(require("admin", "reviewer"))):
    j, it = await _get_job_item(jid, item_id)
    it["status"] = "reviewed"
    it["review"] = {"reviewer_id": user["id"], "reviewer_name": user["name"], "date": now_iso(), "comments": body.comments}
    await replace_item(jid, j["items"], it)
    await audit("job", jid, "review", user, field=item_id, reason=body.comments)
    return {"ok": True}


@api.post("/jobs/{jid}/items/{item_id}/reject")
async def reject_item(jid: str, item_id: str, body: RejectIn, user=Depends(require("admin", "reviewer", "signatory"))):
    j, it = await _get_job_item(jid, item_id)
    it["status"] = "rejected"
    it["reject_reason"] = body.reason
    await replace_item(jid, j["items"], it)
    await audit("job", jid, "reject", user, field=item_id, reason=body.reason)
    return {"ok": True}


@api.post("/jobs/{jid}/items/{item_id}/approve")
async def approve_item(jid: str, item_id: str, user=Depends(require("admin", "signatory"))):
    j, it = await _get_job_item(jid, item_id)
    for mid in it.get("master_ids", []):
        m = await db.masters.find_one({"master_id": mid})
        if m and master_status(m) == "expired":
            raise HTTPException(status_code=400, detail=f"Master {mid} calibration expired; cannot approve")
    verify_id = uuid.uuid4().hex[:12]
    cert_no = it.get("cert_no") or await gen_cert_no(it)
    it["cert_no"] = cert_no
    cert = {"cert_no": cert_no, "ulr_no": it.get("url_number"),
            "verification_id": verify_id, "issued_date": now_iso(),
            "issued_by": user["name"], "status": "issued"}
    it["status"] = "certified"
    it["approval"] = {"signatory_id": user["id"], "signatory_name": user["name"], "date": now_iso()}
    it["certificate"] = cert
    await replace_item(jid, j["items"], it)
    await audit("job", jid, "approve_certify", user, field=item_id, new=verify_id)
    return {"ok": True, "certificate": cert}


@api.post("/jobs/{jid}/items/{item_id}/cancel-certificate")
async def cancel_cert(jid: str, item_id: str, body: RejectIn, user=Depends(require("admin", "signatory"))):
    j, it = await _get_job_item(jid, item_id)
    if it.get("certificate"):
        it["certificate"]["status"] = "cancelled"
        it["certificate"]["cancel_reason"] = body.reason
    await replace_item(jid, j["items"], it)
    await audit("job", jid, "cancel_certificate", user, field=item_id, reason=body.reason)
    return {"ok": True}


@api.get("/jobs/{jid}/items/{item_id}/certificate/pdf")
async def cert_pdf(jid: str, item_id: str, user=Depends(current_user)):
    j, it = await _get_job_item(jid, item_id)
    if not it.get("certificate"):
        raise HTTPException(status_code=404, detail="Certificate not issued")
    cust = await db.customers.find_one({"_id": ObjectId(j["customer_id"])})
    prod = await db.products.find_one({"_id": ObjectId(it["product_id"])}) if it.get("product_id") else None
    results = compute_points(it.get("points", []))
    pdf_job = {**it, "job_no": j.get("job_no"), "work_order_ref": j.get("work_order_ref"),
               "cert_no": it.get("cert_no"), "ulr_no": it.get("url_number")}
    verify_url = f"{os.environ.get('FRONTEND_URL','')}/verify/{it['certificate']['verification_id']}"
    pdf = build_certificate_pdf(pdf_job, clean(cust) if cust else {}, clean(prod) if prod else {}, results,
                                verify_url, cert_type=it.get("certificate_type", "NABL"))
    return StreamingResponse(pdf, media_type="application/pdf", headers={
        "Content-Disposition": f'inline; filename="certificate_{(it.get("cert_no") or "cert").replace("/","_")}.pdf"'})


@api.get("/jobs/{jid}/items/{item_id}/validation")
async def validation(jid: str, item_id: str, user=Depends(current_user)):
    j, it = await _get_job_item(jid, item_id)
    rows = []
    has_ref = False
    for p in it.get("points", []):
        ref = p.get("excel_reference")
        r = calcmod.compute_point(p["master_readings"], p["uut_readings"], p.get("point_deviation", 0.0),
                                  p["components"], p.get("cmc_floor"))
        params = [
            ("Corrected STD (°C)", "corrected_std", r["corrected_std"]),
            ("Measured (Xbar) (°C)", "uut_mean", r["uut_mean"]),
            ("Deviation (°C)", None, r["deviation"]),
            ("Std Dev s(x)", "s_x", r["s_x"]),
            ("Combined Unc Uc", "combined_unc", r["combined_unc"]),
            ("Veff", "veff", r["veff"]),
            ("Expanded Unc U", "expanded_unc", r["expanded_unc"]),
        ]
        for label, key, appval in params:
            excelval = ref.get(key) if (ref and key) else None
            if excelval is not None:
                has_ref = True
                diff = abs(appval - excelval)
                tol = 1e-6 * max(1, abs(excelval))
                status = "PASS" if diff <= tol else "FAIL"
            else:
                diff = None
                status = "N/A"
            rows.append({"point": p.get("point_label"), "parameter": label,
                         "excel": excelval, "application": appval,
                         "difference": diff, "status": status})
    return {"has_reference": has_ref, "rows": rows}


@api.get("/jobs/{jid}/items/{item_id}/pre-release-check")
async def pre_release_check(jid: str, item_id: str, user=Depends(current_user)):
    j, it = await _get_job_item(jid, item_id)
    checks = []
    def add(label, ok):
        checks.append({"item": label, "ok": bool(ok)})
    pts = it.get("points", [])
    mv = True
    for mid in it.get("master_ids", []):
        m = await db.masters.find_one({"master_id": mid})
        if m and master_status(m) == "expired":
            mv = False
    add("Product selected", it.get("product_id"))
    add("Serial / Tag number present", it.get("serial_number") or it.get("tag_number"))
    add("Work Order reference present", j.get("work_order_ref"))
    add("Calibration points present", len(pts) > 0)
    add("Master / reference selected", len(it.get("master_ids", [])) > 0)
    add("All masters within validity", mv)
    add("Readings complete (non-zero)", bool(pts) and all(any(r for r in p.get("uut_readings", [])) for p in pts))
    add("Technical review completed", it.get("review") is not None)
    add("SRF customer-approved", j.get("srf_status") == "approved")
    return {"ready": all(c["ok"] for c in checks), "checks": checks}


# ---------------- SRF (attached to the Calibration Job / Work Order) ----------------
@api.post("/jobs/{jid}/prepare-srf")
async def prepare_job_srf(jid: str, user=Depends(require("admin", "technician"))):
    j = await db.jobs.find_one({"_id": ObjectId(jid)})
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    cust = await db.customers.find_one({"_id": ObjectId(j["customer_id"])}) if j.get("customer_id") else {}
    cust = cust or {}
    products = []
    for it in j.get("items", []):
        prod = await db.products.find_one({"_id": ObjectId(it["product_id"])}) if it.get("product_id") else {}
        prod = prod or {}
        products.append({
            "product_name": prod.get("name", ""),
            "serial_number": it.get("serial_number", ""),
            "tag_number": it.get("tag_number", ""),
            "range": prod.get("range", ""),
            "certificate_type": it.get("certificate_type", "NABL"),
            "calibration_points": [p.get("nominal") for p in it.get("points", [])],
        })
    srf_no = j.get("srf_no") or f"SRF-{datetime.now(timezone.utc).year}-{await next_seq('srf'):05d}"
    srf = {
        "srf_no": srf_no,
        "customer_name": cust.get("name", ""), "address": cust.get("address", ""),
        "contact": cust.get("contact", ""), "email": cust.get("email", ""), "phone": cust.get("phone", ""),
        "work_order_ref": j.get("work_order_ref", ""),
        "products": products,
        "calibration_requirement": "As per customer specification",
        "lab_notes": (j.get("srf") or {}).get("lab_notes", ""),
        "prepared_by": user["name"], "prepared_at": now_iso(),
    }
    await db.jobs.update_one({"_id": ObjectId(jid)}, {"$set": {"srf": srf, "srf_no": srf_no, "srf_status": "prepared"}})
    await audit("job", jid, "prepare_srf", user, new=srf_no)
    return {"ok": True, "srf": srf}


@api.put("/jobs/{jid}/srf")
async def update_job_srf(jid: str, body: SRFUpdate, user=Depends(require("admin", "technician"))):
    await db.jobs.update_one({"_id": ObjectId(jid)}, {"$set": {"srf": body.srf}})
    await audit("job", jid, "update_srf", user)
    return {"ok": True}


@api.post("/jobs/{jid}/send-srf")
async def send_job_srf(jid: str, user=Depends(require("admin", "technician"))):
    j = await db.jobs.find_one({"_id": ObjectId(jid)})
    if not j or not j.get("srf"):
        raise HTTPException(status_code=400, detail="Prepare the SRF before sending")
    token = j.get("srf_token") or uuid.uuid4().hex
    link = f"{os.environ.get('FRONTEND_URL','')}/srf/{token}"
    await db.jobs.update_one({"_id": ObjectId(jid)}, {"$set": {"srf_token": token, "srf_status": "sent", "srf_sent_at": now_iso()}})
    await audit("job", jid, "send_srf", user, new=token)
    return {"ok": True, "srf_link": link, "token": token}


# ----- Public SRF (customer) -----
@api.get("/srf/{token}")
async def public_srf(token: str):
    j = await db.jobs.find_one({"srf_token": token})
    if not j:
        raise HTTPException(status_code=404, detail="SRF not found")
    return {
        "job_no": j.get("job_no"), "work_order_ref": j.get("work_order_ref"),
        "srf_status": j.get("srf_status"), "srf": j.get("srf"), "srf_approval": j.get("srf_approval"),
    }


@api.post("/srf/{token}/action")
async def public_srf_action(token: str, body: SRFAction):
    j = await db.jobs.find_one({"srf_token": token})
    if not j:
        raise HTTPException(status_code=404, detail="SRF not found")
    if j.get("srf_status") not in ("sent", "correction_requested"):
        raise HTTPException(status_code=400, detail="SRF is not awaiting customer action")
    mapping = {"approve": "approved", "request_correction": "correction_requested", "reject": "rejected"}
    if body.action not in mapping:
        raise HTTPException(status_code=400, detail="Invalid action")
    approval = {"action": body.action, "customer_name": body.customer_name,
                "comments": body.comments, "date": now_iso(), "token_ref": token}
    await db.jobs.update_one({"_id": j["_id"]}, {"$set": {"srf_status": mapping[body.action], "srf_approval": approval}})
    await db.audit_logs.insert_one({
        "entity_type": "job", "entity_id": str(j["_id"]), "action": f"customer_srf_{body.action}",
        "field": "srf_status", "old_value": "sent", "new_value": mapping[body.action], "reason": body.comments,
        "user_id": None, "user_name": body.customer_name or "Customer", "user_role": "customer",
        "timestamp": now_iso()})
    return {"ok": True, "srf_status": mapping[body.action]}


# ---------------- Global Search ----------------
@api.get("/search")
async def search(q: str = "", user=Depends(current_user)):
    q = (q or "").strip()
    if not q:
        return {"jobs": []}
    rx = {"$regex": re.escape(q), "$options": "i"}
    cust_ids = [str(c["_id"]) for c in await db.customers.find({"name": rx}).to_list(200)]
    query = {"$or": [
        {"job_no": rx}, {"work_order_ref": rx}, {"srf_no": rx},
        {"items.serial_number": rx}, {"items.tag_number": rx}, {"items.sr_number": rx},
        {"items.cert_no": rx}, {"items.certificate.cert_no": rx}, {"items.certificate.verification_id": rx},
    ]}
    if cust_ids:
        query["$or"].append({"customer_id": {"$in": cust_ids}})
    out = []
    for j in await db.jobs.find(query).sort("created_at", -1).to_list(100):
        cust = await db.customers.find_one({"_id": ObjectId(j["customer_id"])}) if j.get("customer_id") else None
        items = j.get("items", [])
        out.append({"id": str(j["_id"]), "job_no": j.get("job_no"), "work_order_ref": j.get("work_order_ref"),
                    "srf_no": j.get("srf_no"),
                    "cert_no": ", ".join([it.get("cert_no", "") for it in items if it.get("cert_no")]),
                    "customer_name": cust["name"] if cust else "",
                    "serial_number": ", ".join([it.get("serial_number", "") for it in items if it.get("serial_number")]),
                    "product_count": len(items),
                    "status": job_rollup_status(j)})
    return {"jobs": out}


# ---------------- Dashboard ----------------
@api.get("/dashboard")
async def dashboard(user=Depends(current_user)):
    jobs = await db.jobs.find().to_list(2000)
    masters = await db.masters.find().to_list(1000)
    today = datetime.now(timezone.utc).date().isoformat()
    counts = {"pending_readings": 0, "pending_review": 0, "pending_approval": 0,
              "certificates_issued": 0, "today_jobs": 0}
    srf_pipeline = {"no_srf": 0, "prepared": 0, "awaiting_customer": 0, "approved": 0, "correction": 0}
    for j in jobs:
        # per-product (item) counts
        for it in j.get("items", []):
            s = it.get("status")
            if s in ("draft", "readings_entered"):
                counts["pending_readings"] += 1
            if s == "in_review":
                counts["pending_review"] += 1
            if s in ("reviewed", "calculated"):
                counts["pending_approval"] += 1
            if s == "certified":
                counts["certificates_issued"] += 1
            if (it.get("cal_date") or "")[:10] == today:
                counts["today_jobs"] += 1
        ss = j.get("srf_status") or "none"
        if ss == "none":
            srf_pipeline["no_srf"] += 1
        elif ss == "prepared":
            srf_pipeline["prepared"] += 1
        elif ss == "sent":
            srf_pipeline["awaiting_customer"] += 1
        elif ss == "approved":
            srf_pipeline["approved"] += 1
        elif ss in ("correction_requested", "rejected"):
            srf_pipeline["correction"] += 1
    expiring, expired = [], []
    for m in masters:
        st = master_status(m)
        if st == "expiring":
            expiring.append(clean(m))
        elif st == "expired":
            expired.append(clean(m))
    recent = []
    for j in sorted(jobs, key=lambda x: x.get("created_at", ""), reverse=True)[:8]:
        c = clean(j)
        cust = await db.customers.find_one({"_id": ObjectId(c["customer_id"])}) if c.get("customer_id") else None
        items = c.get("items", [])
        recent.append({"id": c["id"], "job_no": c.get("job_no"), "work_order_ref": c.get("work_order_ref"),
                       "customer_name": cust["name"] if cust else "", "status": job_rollup_status(c),
                       "product_count": len(items),
                       "cal_date": items[0].get("cal_date") if items else ""})
    counts["masters_expiring"] = len(expiring)
    counts["masters_expired"] = len(expired)
    return {"counts": counts, "srf_pipeline": srf_pipeline, "expiring_masters": expiring,
            "expired_masters": expired, "recent_jobs": recent}


# ---------------- Audit ----------------
@api.get("/audit")
async def get_audit(entity_id: Optional[str] = None, user=Depends(current_user)):
    q = {"entity_id": entity_id} if entity_id else {}
    logs = await db.audit_logs.find(q).sort("timestamp", -1).to_list(500)
    return [clean(l) for l in logs]


@api.get("/jobs/{jid}/traceability")
async def traceability(jid: str, user=Depends(current_user)):
    j = await db.jobs.find_one({"_id": ObjectId(jid)})
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    cust = await db.customers.find_one({"_id": ObjectId(j["customer_id"])}) if j.get("customer_id") else None
    logs = [clean(l) for l in await db.audit_logs.find({"entity_id": jid}).sort("timestamp", 1).to_list(1000)]
    items_out = []
    for it in j.get("items", []):
        prod = await db.products.find_one({"_id": ObjectId(it["product_id"])}) if it.get("product_id") else None
        masters = []
        for mid in it.get("master_ids", []):
            m = await db.masters.find_one({"master_id": mid})
            if m:
                mc = clean(m)
                mc["validity_status"] = master_status(m)
                masters.append(mc)
        items_out.append({
            "item_id": it.get("item_id"),
            "product": clean(prod) if prod else None,
            "certificate": it.get("certificate"), "certificate_type": it.get("certificate_type"),
            "approval": it.get("approval"), "review": it.get("review"),
            "cal_date": it.get("cal_date"), "method": it.get("method"),
            "standards_used": it.get("standards_used", []),
            "calibration_points": [{"label": p.get("point_label"), "nominal": p.get("nominal")} for p in it.get("points", [])],
            "masters": masters,
            "readings": [{"point": p.get("point_label"), "master_readings": p.get("master_readings"),
                          "uut_readings": p.get("uut_readings")} for p in it.get("points", [])],
        })
    return {
        "job": {"id": jid, "job_no": j.get("job_no"), "status": job_rollup_status(j)},
        "work_order_ref": j.get("work_order_ref"), "work_order_source": j.get("work_order_source"),
        "srf": {"srf_no": j.get("srf_no"), "status": j.get("srf_status"), "approval": j.get("srf_approval")},
        "customer": clean(cust) if cust else None,
        "items": items_out,
        "audit_trail": logs,
    }


# ---------------- Document Control ----------------
DOC_CATEGORIES = [
    "Quality Manual", "SOP", "Calibration Procedure", "Work Instruction", "Form",
    "Calculation Method", "Uncertainty Procedure", "Equipment Procedure",
    "Environmental Procedure", "Certificate Template", "Policy",
]
DOC_STATUS_FLOW = {"draft": "under_review", "under_review": "approved", "approved": "effective"}


@api.get("/documents")
async def list_documents(category: Optional[str] = None, status: Optional[str] = None, user=Depends(current_user)):
    q = {}
    if category:
        q["category"] = category
    if status:
        q["status"] = status
    docs = await db.documents.find(q).sort([("category", 1), ("doc_number", 1), ("revision", -1)]).to_list(2000)
    return [clean(d) for d in docs]


@api.post("/documents")
async def create_document(body: DocumentIn, user=Depends(require("admin", "quality"))):
    if not body.doc_number.strip() or not body.title.strip():
        raise HTTPException(status_code=400, detail="Document Number and Title are required")
    if await db.documents.find_one({"doc_number": body.doc_number, "revision": body.revision}):
        raise HTTPException(status_code=400, detail="This document number + revision already exists")
    doc = {**body.model_dump(), "status": "draft", "is_current": False, "superseded_by": None,
           "created_by": user["id"], "created_by_name": user["name"],
           "created_at": now_iso(), "updated_at": now_iso(),
           "history": [{"action": "created", "by": user["name"], "at": now_iso(), "note": body.change_note}]}
    res = await db.documents.insert_one(doc)
    await audit("document", res.inserted_id, "create", user, new=f"{body.doc_number} rev {body.revision}")
    return clean(await db.documents.find_one({"_id": res.inserted_id}))


@api.put("/documents/{did}")
async def update_document(did: str, body: DocumentIn, user=Depends(require("admin", "quality"))):
    d = await db.documents.find_one({"_id": ObjectId(did)})
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    if d["status"] in ("effective", "obsolete"):
        raise HTTPException(status_code=400, detail="Effective/obsolete documents cannot be edited — create a new revision")
    await db.documents.update_one({"_id": ObjectId(did)}, {"$set": {**body.model_dump(), "updated_at": now_iso()}})
    await audit("document", did, "update", user)
    return clean(await db.documents.find_one({"_id": ObjectId(did)}))


@api.post("/documents/{did}/status")
async def transition_document(did: str, body: DocStatusIn, user=Depends(require("admin", "quality"))):
    d = await db.documents.find_one({"_id": ObjectId(did)})
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    target = body.status
    if target not in ("under_review", "approved", "effective", "obsolete"):
        raise HTTPException(status_code=400, detail="Invalid target status")
    updates = {"status": target, "updated_at": now_iso()}
    if target == "effective":
        updates["is_current"] = True
        if not d.get("effective_date"):
            updates["effective_date"] = now_iso()[:10]
        await db.documents.update_many(
            {"doc_number": d["doc_number"], "status": "effective", "_id": {"$ne": ObjectId(did)}},
            {"$set": {"status": "obsolete", "is_current": False, "superseded_by": d.get("revision")}})
    elif target == "obsolete":
        updates["is_current"] = False
    await db.documents.update_one({"_id": ObjectId(did)}, {
        "$set": updates,
        "$push": {"history": {"action": f"status → {target}", "by": user["name"], "at": now_iso(), "note": body.note}}})
    await audit("document", did, "status_change", user, old=d.get("status"), new=target, reason=body.note)
    return clean(await db.documents.find_one({"_id": ObjectId(did)}))


@api.post("/documents/{did}/revise")
async def revise_document(did: str, body: DocStatusIn, user=Depends(require("admin", "quality"))):
    d = await db.documents.find_one({"_id": ObjectId(did)})
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    try:
        nextrev = f"{int(d.get('revision', '01')) + 1:02d}"
    except ValueError:
        nextrev = f"{d.get('revision', '01')}-R"
    if await db.documents.find_one({"doc_number": d["doc_number"], "revision": nextrev}):
        raise HTTPException(status_code=400, detail="Next revision already exists")
    newdoc = {"doc_number": d["doc_number"], "title": d.get("title", ""), "category": d.get("category", ""),
              "file_url": d.get("file_url", ""), "revision": nextrev, "status": "draft",
              "is_current": False, "superseded_by": None, "effective_date": "", "review_date": "",
              "prepared_by": user["name"], "reviewed_by": "", "approved_by": "", "change_note": body.note or "",
              "created_by": user["id"], "created_by_name": user["name"],
              "created_at": now_iso(), "updated_at": now_iso(),
              "history": [{"action": f"new revision from rev {d.get('revision')}", "by": user["name"], "at": now_iso(), "note": body.note}]}
    res = await db.documents.insert_one(newdoc)
    await audit("document", res.inserted_id, "revise", user, old=d.get("revision"), new=nextrev)
    return clean(await db.documents.find_one({"_id": res.inserted_id}))


@api.get("/documents/{did}/history")
async def document_history(did: str, user=Depends(current_user)):
    d = await db.documents.find_one({"_id": ObjectId(did)})
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    revs = await db.documents.find({"doc_number": d["doc_number"]}).sort("revision", 1).to_list(200)
    return {"doc_number": d["doc_number"], "revisions": [clean(x) for x in revs]}


@api.post("/documents/{did}/attachment")
async def upload_document_file(did: str, file: UploadFile = File(...), user=Depends(require("admin", "quality"))):
    d = await db.documents.find_one({"_id": ObjectId(did)})
    if not d:
        raise HTTPException(status_code=404, detail="Document not found")
    data = await file.read()
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 20 MB limit")
    ext = (file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "bin")
    ctype = file.content_type or storagemod.MIME_TYPES.get(ext, "application/octet-stream")
    path = f"{storagemod.APP_NAME}/documents/{did}/{uuid.uuid4()}.{ext}"
    try:
        result = storagemod.put_object(path, data, ctype)
    except Exception as e:
        logger.error(f"Storage upload failed: {e}")
        raise HTTPException(status_code=502, detail="File storage upload failed")
    att = {"file_path": result["path"], "file_name": file.filename,
           "content_type": ctype, "size": result.get("size", len(data)),
           "uploaded_by": user["name"], "uploaded_at": now_iso()}
    await db.documents.update_one({"_id": ObjectId(did)}, {
        "$set": {"attachment": att, "updated_at": now_iso()},
        "$push": {"history": {"action": "file attached", "by": user["name"], "at": now_iso(), "note": file.filename}}})
    await audit("document", did, "attach_file", user, new=file.filename)
    return {"ok": True, "attachment": att}


@api.get("/documents/{did}/attachment")
async def download_document_file(did: str, request: Request, authorization: str = Header(None)):
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        authmod.decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    d = await db.documents.find_one({"_id": ObjectId(did)})
    if not d or not d.get("attachment"):
        raise HTTPException(status_code=404, detail="No attachment for this document")
    att = d["attachment"]
    try:
        content, ctype = storagemod.get_object(att["file_path"])
    except Exception as e:
        logger.error(f"Storage download failed: {e}")
        raise HTTPException(status_code=502, detail="File storage download failed")
    return Response(content=content, media_type=att.get("content_type", ctype),
                    headers={"Content-Disposition": f'inline; filename="{att.get("file_name", "document")}"'})


# ---------------- Public verification ----------------
@api.get("/verify/{verification_id}")
async def verify(verification_id: str):
    j = await db.jobs.find_one({"items.certificate.verification_id": verification_id})
    if not j:
        raise HTTPException(status_code=404, detail="Certificate not found")
    it = None
    for x in j.get("items", []):
        if (x.get("certificate") or {}).get("verification_id") == verification_id:
            it = x
            break
    if not it:
        raise HTTPException(status_code=404, detail="Certificate not found")
    cert = it.get("certificate", {})
    prod = await db.products.find_one({"_id": ObjectId(it["product_id"])}) if it.get("product_id") else None
    return {
        "found": True,
        "job_no": j.get("job_no"),
        "work_order_ref": j.get("work_order_ref"),
        "certificate_no": cert.get("cert_no"),
        "ulr_no": cert.get("ulr_no"),
        "certificate_type": it.get("certificate_type", "NABL"),
        "status": cert.get("status"),
        "issued_date": cert.get("issued_date"),
        "cal_date": it.get("cal_date"),
        "recommended_next_date": it.get("recommended_next_date"),
        "item": prod["name"] if prod else "",
        "item_type": prod.get("type") if prod else "",
        "serial_number": it.get("serial_number"),
        "points": len(it.get("points", [])),
    }


@api.get("/")
async def root():
    return {"service": "YOG Calibration Lab API", "status": "ok"}


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- Migration: single-product jobs -> multi-product items[] ----------------
async def migrate_jobs_to_items():
    legacy_fields = ["product_id", "serial_number", "tag_number", "sr_number", "part_number",
                     "url_number", "cert_no", "ulr_no", "certificate_type", "template_code",
                     "reference_standard", "method", "cal_date", "issue_date", "item_received_date",
                     "recommended_next_date", "environmental", "master_ids", "standards_used",
                     "points", "computed", "review", "approval", "certificate", "reject_reason"]
    migrated = 0
    async for j in db.jobs.find({"items": {"$exists": False}}):
        item = {
            "item_id": uuid.uuid4().hex,
            "product_id": j.get("product_id", ""),
            "serial_number": j.get("serial_number", ""),
            "tag_number": j.get("tag_number", ""),
            "sr_number": j.get("sr_number", ""),
            "part_number": j.get("part_number", ""),
            "url_number": j.get("url_number") or j.get("ulr_no", ""),
            "cert_no": j.get("cert_no", ""),
            "certificate_type": j.get("certificate_type", "NABL"),
            "method": j.get("method", "WI \u2013 TECH/11"),
            "reference_standard": j.get("reference_standard", ""),
            "cal_date": j.get("cal_date", ""),
            "issue_date": j.get("issue_date", ""),
            "item_received_date": j.get("item_received_date", ""),
            "environmental": j.get("environmental") or dict(DEFAULT_ENV),
            "master_ids": j.get("master_ids", []),
            "template_code": j.get("template_code", ""),
            "standards_used": j.get("standards_used", []),
            "recommended_next_date": j.get("recommended_next_date", ""),
            "points": j.get("points", []),
            "computed": j.get("computed", []),
            "status": j.get("status", "draft"),
            "review": j.get("review"),
            "approval": j.get("approval"),
            "certificate": j.get("certificate"),
        }
        await db.jobs.update_one({"_id": j["_id"]}, {
            "$set": {"items": [item]},
            "$unset": {f: "" for f in legacy_fields + ["status"]},
        })
        migrated += 1
    if migrated:
        logger.info(f"Migrated {migrated} legacy job(s) into multi-product structure")


async def consolidate_url_field():
    """Merge legacy per-item `ulr_no` into the single `url_number` field and drop `ulr_no`."""
    fixed = 0
    async for j in db.jobs.find({}):
        items = j.get("items", [])
        changed = False
        for it in items:
            if not it.get("url_number") and it.get("ulr_no"):
                it["url_number"] = it.get("ulr_no")
                changed = True
            if "ulr_no" in it:
                it.pop("ulr_no", None)
                changed = True
        if changed:
            await db.jobs.update_one({"_id": j["_id"]}, {"$set": {"items": items}})
            fixed += 1
    if fixed:
        logger.info(f"Consolidated ulr_no -> url_number on {fixed} job(s)")


# ---------------- Seeding ----------------
async def seed():
    await db.users.create_index("email", unique=True)
    await db.masters.create_index("master_id")
    admin_email = os.environ["ADMIN_EMAIL"].lower()
    admin_pw = os.environ["ADMIN_PASSWORD"]
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({"email": admin_email, "password_hash": authmod.hash_password(admin_pw),
                                   "name": "Lab Administrator", "role": "admin", "created_at": now_iso()})
    elif not authmod.verify_password(admin_pw, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": authmod.hash_password(admin_pw)}})

    demo = [("technician@yog.local", "Tech@2026", "Nilesh Bodakhe", "technician"),
            ("reviewer@yog.local", "Review@2026", "Quality Reviewer", "reviewer"),
            ("signatory@yog.local", "Sign@2026", "A. A. Kothe", "signatory"),
            ("quality@yog.local", "Quality@2026", "Quality Manager", "quality"),
            ("viewer@yog.local", "View@2026", "Read Only", "viewer")]
    for em, pw, nm, role in demo:
        if not await db.users.find_one({"email": em}):
            await db.users.insert_one({"email": em, "password_hash": authmod.hash_password(pw),
                                       "name": nm, "role": role, "created_at": now_iso()})

    if await db.documents.count_documents({}) == 0:
        samples = [
            {"doc_number": "QM-01", "title": "Quality Manual", "category": "Quality Manual", "revision": "03", "status": "effective", "effective_date": "2026-01-01", "review_date": "2027-01-01", "prepared_by": "Quality Manager", "reviewed_by": "Technical Manager", "approved_by": "Lab Director"},
            {"doc_number": "WI-TECH/11", "title": "Temperature Calibration Work Instruction", "category": "Work Instruction", "revision": "05", "status": "effective", "effective_date": "2026-02-01", "review_date": "2027-02-01", "prepared_by": "N. H. Bodakhe", "reviewed_by": "A. A. Kothe", "approved_by": "A. A. Kothe"},
            {"doc_number": "FTECH04", "title": "Calibration Certificate Template", "category": "Certificate Template", "revision": "05", "status": "effective", "effective_date": "2026-02-01", "review_date": "2027-02-01", "prepared_by": "Quality Manager", "reviewed_by": "", "approved_by": "A. A. Kothe"},
            {"doc_number": "FTECH22", "title": "Uncertainty Calculation Procedure", "category": "Uncertainty Procedure", "revision": "00", "status": "under_review", "effective_date": "", "review_date": "", "prepared_by": "N. H. Bodakhe", "reviewed_by": "", "approved_by": ""},
        ]
        for s in samples:
            await db.documents.insert_one({**s, "file_url": "", "change_note": "",
                "is_current": s["status"] == "effective", "superseded_by": None, "created_by_name": "System",
                "created_at": now_iso(), "updated_at": now_iso(),
                "history": [{"action": "seeded", "by": "System", "at": now_iso(), "note": ""}]})

    if await db.jobs.count_documents({}) > 0:
        await migrate_jobs_to_items()
        await consolidate_url_field()
        return

    with open(ROOT_DIR / "seed_data.json") as f:
        data = json.load(f)

    for m in data["masters"]:
        if not await db.masters.find_one({"master_id": m["master_id"]}):
            await db.masters.insert_one({**m, "created_at": now_iso()})

    cust_map = {}
    for c in data["customers"]:
        key = c.pop("key")
        res = await db.customers.insert_one({**c, "created_at": now_iso()})
        cust_map[key] = str(res.inserted_id)

    prod_map = {}
    for p in data["products"]:
        key = p.pop("key")
        ckey = p.pop("customer_key")
        p["customer_id"] = cust_map[ckey]
        res = await db.products.insert_one({**p, "status": "active", "created_at": now_iso()})
        prod_map[key] = str(res.inserted_id)

    for t in data["templates"]:
        if not await db.templates.find_one({"code": t["code"]}):
            await db.templates.insert_one({**t, "created_at": now_iso()})

    for j in data["jobs"]:
        ckey = j.pop("customer_key")
        pkey = j.pop("product_key")
        item = {
            "item_id": uuid.uuid4().hex,
            "product_id": prod_map[pkey],
            "serial_number": j.get("serial_number", ""),
            "tag_number": j.get("tag_number", ""),
            "sr_number": j.get("sr_number", ""),
            "part_number": j.get("part_number", ""),
            "url_number": j.get("url_number") or j.get("ulr_no", ""),
            "cert_no": j.get("cert_no", ""),
            "certificate_type": j.get("certificate_type", "NABL"),
            "method": j.get("method", "WI \u2013 TECH/11"),
            "reference_standard": j.get("reference_standard", ""),
            "cal_date": j.get("cal_date", ""),
            "issue_date": j.get("issue_date", ""),
            "item_received_date": j.get("item_received_date", ""),
            "environmental": j.get("environmental") or dict(DEFAULT_ENV),
            "master_ids": j.get("master_ids", []),
            "template_code": j.get("template_code", ""),
            "standards_used": await hydrate_standards(j.get("master_ids", [])),
            "recommended_next_date": next_cal_date(j.get("cal_date", "")),
            "points": j.get("points", []),
            "computed": [],
            "status": "readings_entered",
            "review": None,
            "approval": None,
            "certificate": None,
        }
        doc = {
            "job_no": j.get("job_no"),
            "work_order_ref": j.get("work_order_ref") or "WO-2026-00458",
            "work_order_date": "", "work_order_notes": "", "work_order_source": "Billing/ERP",
            "customer_id": cust_map[ckey],
            "items": [item],
            "srf": None, "srf_no": None, "srf_token": None, "srf_status": "none", "srf_approval": None,
            "technician_name": "Nilesh Bodakhe",
            "created_at": now_iso(),
        }
        await db.jobs.insert_one(doc)

    logger.info("Seed complete")


@app.on_event("startup")
async def startup():
    try:
        storagemod.init_storage()
        logger.info("Object storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
    await seed()


@app.on_event("shutdown")
async def shutdown():
    client.close()
