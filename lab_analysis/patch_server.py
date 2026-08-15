import re, io

p = "/app/backend/server.py"
t = open(p).read()

def cut(a, b, new):
    global t
    i = t.index(a); j = t.index(b)
    assert i < j, (a, b)
    t = t[:i] + new + t[j:]

# 1. imports
t = t.replace("from bson import ObjectId\n", "from bson import ObjectId\nfrom pymongo import ReturnDocument\n", 1)

# 2. models: drop WOItem/WorkOrderIn, keep SRFUpdate/SRFAction
cut("class WOItem(BaseModel):", "# ---------------- Auth routes ----------------",
"""class SRFUpdate(BaseModel):
    srf: dict


class SRFAction(BaseModel):
    action: str  # approve | request_correction | reject
    customer_name: str = ""
    comments: str = ""


""")

# 3. JobCreate work order reference fields
t = t.replace(
'''class JobCreate(BaseModel):
    job_no: str = ""
    customer_id: str''',
'''class JobCreate(BaseModel):
    job_no: str = ""
    work_order_ref: str = ""
    work_order_date: str = ""
    work_order_notes: str = ""
    customer_id: str''', 1)

# 4. create_job
cut('@api.post("/jobs")\nasync def create_job', '@api.put("/jobs/{jid}/readings")',
'''@api.post("/jobs")
async def create_job(body: JobCreate, user=Depends(require("admin", "technician"))):
    if not body.work_order_ref.strip():
        raise HTTPException(status_code=400, detail="Work Order Number is required")
    doc = body.model_dump()
    if not doc.get("job_no"):
        doc["job_no"] = f"CAL-{datetime.now(timezone.utc).year}-{await next_seq('job'):05d}"
    doc["work_order_source"] = "Billing/ERP"
    doc["standards_used"] = await hydrate_standards(body.master_ids)
    doc["recommended_next_date"] = next_cal_date(body.cal_date)
    doc["status"] = "draft"
    doc["srf"] = None
    doc["srf_no"] = None
    doc["srf_token"] = None
    doc["srf_status"] = "none"
    doc["srf_approval"] = None
    doc["technician_id"] = user["id"]
    doc["technician_name"] = user["name"]
    doc["created_by"] = user["id"]
    doc["created_at"] = now_iso()
    doc["review"] = None
    doc["approval"] = None
    doc["certificate"] = None
    res = await db.jobs.insert_one(doc)
    await audit("job", res.inserted_id, "create", user, field="work_order_ref",
                new=f"{doc['job_no']} (WO {body.work_order_ref})")
    return clean(await db.jobs.find_one({"_id": res.inserted_id}))


''')

# 5. approve(): remove WO completion block
t = t.replace(
'''    await audit("job", jid, "approve_certify", user, new=verify_id)
    # If job belongs to a Work Order, mark WO completed once all its jobs are certified
    wid = j.get("work_order_id")
    if wid:
        total = await db.jobs.count_documents({"work_order_id": wid})
        done = await db.jobs.count_documents({"work_order_id": wid, "status": "certified"})
        if total > 0 and done >= total:
            await db.work_orders.update_one({"_id": ObjectId(wid)}, {"$set": {"status": "completed"}})
    return {"ok": True, "certificate": cert}''',
'''    await audit("job", jid, "approve_certify", user, new=verify_id)
    return {"ok": True, "certificate": cert}''', 1)

# 6. Replace entire Work Orders section with SRF-on-job + search + next_seq
NEW_ROUTES = '''# ---------------- Sequence counters ----------------
async def next_seq(name):
    doc = await db.counters.find_one_and_update(
        {"_id": name}, {"$inc": {"seq": 1}}, upsert=True, return_document=ReturnDocument.AFTER)
    return doc["seq"]


# ---------------- SRF (attached to Calibration Job) ----------------
@api.post("/jobs/{jid}/prepare-srf")
async def prepare_job_srf(jid: str, user=Depends(require("admin", "technician"))):
    j = await db.jobs.find_one({"_id": ObjectId(jid)})
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    cust = await db.customers.find_one({"_id": ObjectId(j["customer_id"])}) if j.get("customer_id") else {}
    prod = await db.products.find_one({"_id": ObjectId(j["product_id"])}) if j.get("product_id") else {}
    cust = cust or {}; prod = prod or {}
    srf_no = j.get("srf_no") or f"SRF-{datetime.now(timezone.utc).year}-{await next_seq('srf'):05d}"
    srf = {
        "srf_no": srf_no,
        "customer_name": cust.get("name", ""), "address": cust.get("address", ""),
        "contact": cust.get("contact", ""), "email": cust.get("email", ""), "phone": cust.get("phone", ""),
        "work_order_ref": j.get("work_order_ref", ""),
        "product_name": prod.get("name", ""), "serial_number": j.get("serial_number", ""),
        "tag_number": j.get("tag_number", ""), "range": prod.get("range", ""),
        "certificate_type": j.get("certificate_type", "NABL"),
        "calibration_points": [p.get("nominal") for p in j.get("points", [])],
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
        {"job_no": rx}, {"work_order_ref": rx}, {"serial_number": rx}, {"tag_number": rx},
        {"srf_no": rx}, {"cert_no": rx}, {"certificate.cert_no": rx}, {"certificate.verification_id": rx},
    ]}
    if cust_ids:
        query["$or"].append({"customer_id": {"$in": cust_ids}})
    out = []
    for j in await db.jobs.find(query).sort("created_at", -1).to_list(100):
        cust = await db.customers.find_one({"_id": ObjectId(j["customer_id"])}) if j.get("customer_id") else None
        out.append({"id": str(j["_id"]), "job_no": j.get("job_no"), "work_order_ref": j.get("work_order_ref"),
                    "srf_no": j.get("srf_no"), "cert_no": (j.get("certificate") or {}).get("cert_no"),
                    "customer_name": cust["name"] if cust else "", "serial_number": j.get("serial_number"),
                    "certificate_type": j.get("certificate_type"), "status": j.get("status")})
    return {"jobs": out}


'''
cut("# ---------------- Work Orders (top of workflow) ----------------",
    "# ---------------- Dashboard ----------------", NEW_ROUTES)

# 7. Dashboard rewrite (job-centric SRF pipeline)
NEW_DASH = '''@api.get("/dashboard")
async def dashboard(user=Depends(current_user)):
    jobs = await db.jobs.find().to_list(2000)
    masters = await db.masters.find().to_list(1000)
    today = datetime.now(timezone.utc).date().isoformat()
    counts = {"pending_readings": 0, "pending_review": 0, "pending_approval": 0,
              "certificates_issued": 0, "today_jobs": 0}
    srf_pipeline = {"no_srf": 0, "prepared": 0, "awaiting_customer": 0, "approved": 0, "correction": 0}
    for j in jobs:
        s = j.get("status")
        if s in ("draft", "readings_entered"):
            counts["pending_readings"] += 1
        if s in ("in_review",):
            counts["pending_review"] += 1
        if s in ("reviewed", "calculated"):
            counts["pending_approval"] += 1
        if s == "certified":
            counts["certificates_issued"] += 1
        if (j.get("cal_date") or "")[:10] == today:
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
        recent.append({"id": c["id"], "job_no": c.get("job_no"), "work_order_ref": c.get("work_order_ref"),
                       "customer_name": cust["name"] if cust else "", "status": c.get("status"),
                       "certificate_type": c.get("certificate_type"), "cal_date": c.get("cal_date")})
    counts["masters_expiring"] = len(expiring)
    counts["masters_expired"] = len(expired)
    return {"counts": counts, "srf_pipeline": srf_pipeline, "expiring_masters": expiring,
            "expired_masters": expired, "recent_jobs": recent}


'''
cut('@api.get("/dashboard")', "# ---------------- Audit ----------------", NEW_DASH)

# 8. verify: add job_no + work_order_ref
t = t.replace(
'''    return {
        "found": True,
        "certificate_no": cert.get("cert_no"),''',
'''    return {
        "found": True,
        "job_no": j.get("job_no"),
        "work_order_ref": j.get("work_order_ref"),
        "certificate_no": cert.get("cert_no"),''', 1)

# 9. seed jobs: add WO ref + srf defaults
t = t.replace(
'''        j["status"] = "readings_entered"
        j["technician_name"] = "Nilesh Bodakhe"''',
'''        j["status"] = "readings_entered"
        j["work_order_ref"] = j.get("work_order_ref") or "WO-2026-00458"
        j["work_order_source"] = "Billing/ERP"
        j["srf"] = None
        j["srf_no"] = None
        j["srf_token"] = None
        j["srf_status"] = "none"
        j["srf_approval"] = None
        j["technician_name"] = "Nilesh Bodakhe"''', 1)

# 10. remove seed_work_order function + its startup call
cut("async def seed_work_order", '@app.on_event("startup")', "")
t = t.replace("    await seed()\n    await seed_work_order()", "    await seed()", 1)

open(p, "w").write(t)
print("server.py rewritten OK; length", len(t))
