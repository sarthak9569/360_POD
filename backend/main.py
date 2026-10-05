import os
import io
import re
import uuid
import tempfile
import httpx
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from pydantic import BaseModel
from models import PartnerLogin
from pdf_service import generate_qr_pdf, generate_all_qrs_pdf, generate_invoice_pdf

app = FastAPI(title="360 Parenting POD Gateway API")

# Allow CORS for all networks
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MEDIA_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploaded_media")
os.makedirs(MEDIA_UPLOAD_DIR, exist_ok=True)

# Local cache / in-memory storage for offline / bridged operation
SUPERVISORS_DATA = [
    {"_id": "1", "name": "Ankit", "districts": ["Mahasamund"], "villages": ["Mahasamund", "Bagbahara", "Saraipali", "Pithora", "Basna"]},
    {"_id": "2", "name": "Sreekant Mandal", "districts": ["Kanker"], "villages": ["Kanker", "Charama", "Narharpur", "Antagarh", "Bhanupratappur"]},
    {"_id": "3", "name": "Kishor", "districts": ["Kondagaon"], "villages": ["Kondagaon", "Makdi", "Pharasgaon", "Bade Rajpur", "Keshkal"]},
    {"_id": "4", "name": "Patel Thandaram", "districts": ["Sharangarh"], "villages": ["Sarangarh", "Baramkela", "Bilaigarh", "Kosi", "Saria"]},
    {"_id": "5", "name": "Millan Haldhar", "districts": ["Balrampur"], "villages": ["Balrampur", "Ramanujganj", "Rajpur", "Samri", "Shankargarh"]},
]

BENEFICIARIES_STORE = []

DELIVERIES_STORE = {}

BENEFICIARY_API_URL = os.getenv("BENEFICIARY_API_URL", "https://purple-raven-130094.hostingersite.com/admin/beneficiary-details")

async def fetch_realtime_beneficiaries(page: int = None, limit: int = None) -> dict:
    """
    Fetches real-time beneficiary details from the web dev team's API endpoint
    (https://purple-raven-130094.hostingersite.com/admin/beneficiary-details?page=1&limit=10).
    Populates BENEFICIARIES_STORE with live records from the API and supports pagination.
    """
    if page is not None and limit is not None:
        target_url = f"{BENEFICIARY_API_URL}?page={page}&limit={limit}"
    else:
        # Default fetch all (or high limit) for full internal sync
        target_url = f"{BENEFICIARY_API_URL}?page=1&limit=1000"

    pagination_data = {}
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(target_url)
            if resp.status_code == 200:
                res_data = resp.json()
                raw_items = []
                if isinstance(res_data, dict):
                    raw_items = res_data.get("data", [])
                    pagination_data = res_data.get("pagination", {})
                elif isinstance(res_data, list):
                    raw_items = res_data

                fresh_records = []
                for item in raw_items:
                    tag_no = str(item.get("earTagId") or item.get("tag_no") or item.get("tagNo") or "").strip()
                    if not tag_no:
                        continue

                    farmer_name = item.get("beneficiaryName") or item.get("farmer_name") or item.get("farmerName") or item.get("name") or "Unknown"
                    father_husband = item.get("husbandFatherName") or item.get("father_husband_name") or item.get("fatherHusbandName") or "-"
                    village = item.get("village", "")
                    district = item.get("district", "")
                    do_number = item.get("doNumber", "")
                    handover_date = item.get("handoverDate", "")
                    handover_time = item.get("handoverTime", "")

                    beneficiary_obj = {
                        "_id": item.get("_id", f"b_{tag_no}"),
                        "tag_no": tag_no,
                        "farmer_name": farmer_name,
                        "father_husband_name": father_husband,
                        "village": village,
                        "district": district,
                        "do_number": do_number,
                        "handover_date": handover_date,
                        "handover_time": handover_time,
                        "cattle_feed_kg": int(item.get("cattle_feed_kg", item.get("cattleFeedKg", 25))),
                        "silage_kg": int(item.get("silage_kg", item.get("silageKg", 50))),
                        "mineral_mixture_kg": int(item.get("mineral_mixture_kg", item.get("mineralMixtureKg", 5))),
                    }
                    fresh_records.append(beneficiary_obj)

                # Upsert into BENEFICIARIES_STORE
                for rec in fresh_records:
                    idx = next((i for i, b in enumerate(BENEFICIARIES_STORE) if b["tag_no"] == rec["tag_no"]), None)
                    if idx is not None:
                        BENEFICIARIES_STORE[idx] = rec
                    else:
                        BENEFICIARIES_STORE.append(rec)

                if page is not None and limit is not None:
                    return {
                        "success": True,
                        "message": "Beneficiary details fetched successfully",
                        "data": fresh_records,
                        "pagination": pagination_data or {
                            "totalRecords": len(fresh_records),
                            "totalPages": 1,
                            "currentPage": page,
                            "limit": limit
                        }
                    }

    except Exception as e:
        print(f"Warning: Failed to fetch realtime beneficiaries: {e}")

    # Default fallback response
    total_recs = len(BENEFICIARIES_STORE)
    req_limit = limit or (total_recs if total_recs > 0 else 10)
    req_page = page or 1
    
    start_idx = (req_page - 1) * req_limit
    end_idx = start_idx + req_limit
    paged_items = BENEFICIARIES_STORE[start_idx:end_idx] if page is not None else BENEFICIARIES_STORE

    total_pages = (total_recs + req_limit - 1) // req_limit if req_limit > 0 else 1

    return {
        "success": True,
        "message": "Beneficiary details fetched successfully",
        "data": paged_items,
        "pagination": {
            "totalRecords": total_recs,
            "totalPages": total_pages,
            "currentPage": req_page,
            "limit": req_limit
        }
    }

async def get_beneficiary_by_tag(tag_no: str) -> dict:
    """Find a beneficiary by tag_no, querying the real-time API if not cached."""
    tag_str = str(tag_no).strip()
    beneficiary = next((b for b in BENEFICIARIES_STORE if str(b.get("tag_no")) == tag_str), None)
    if not beneficiary:
        await fetch_realtime_beneficiaries()
        beneficiary = next((b for b in BENEFICIARIES_STORE if str(b.get("tag_no")) == tag_str), None)
    return beneficiary

@app.on_event("startup")
async def startup_event():
    """Initializes live beneficiary data on backend startup."""
    print("Initializing real-time beneficiary sync from external API...")
    beneficiaries = await fetch_realtime_beneficiaries()
    print(f"Backend started: Synced {len(beneficiaries)} beneficiary records.")

@app.get("/api/districts")
async def get_districts():
    await fetch_realtime_beneficiaries()
    districts = set()
    for s in SUPERVISORS_DATA:
        districts.update(s.get("districts", []))
    for b in BENEFICIARIES_STORE:
        if b.get("district"):
            districts.add(b.get("district"))
    return sorted(list(filter(None, districts)))

@app.get("/api/districts/{district}/villages")
async def get_villages(district: str):
    await fetch_realtime_beneficiaries()
    villages = set()
    d_clean = district.strip().lower()
    for s in SUPERVISORS_DATA:
        if any(d.strip().lower() == d_clean for d in s.get("districts", [])):
            villages.update(s.get("villages", []))
    for b in BENEFICIARIES_STORE:
        if b.get("district", "").strip().lower() == d_clean and b.get("village"):
            villages.add(b.get("village"))
    return sorted(list(filter(None, villages)))

@app.post("/api/partner/login")
async def partner_login(payload: PartnerLogin):
    sup_name = payload.supervisor_name.strip().lower()
    req_district = payload.district.strip().lower()
    
    supervisor = next((s for s in SUPERVISORS_DATA if s["name"].strip().lower() == sup_name), None)
    if not supervisor:
        raise HTTPException(status_code=403, detail="Invalid supervisor name.")
        
    assigned_districts = [d.lower() for d in supervisor.get("districts", [])]
    if req_district not in assigned_districts:
        raise HTTPException(status_code=403, detail="Supervisor not assigned to this district.")
        
    return {
        "success": True,
        "partner_name": payload.partner_name,
        "district": payload.district,
        "village": payload.village
    }

@app.get("/api/beneficiaries")
async def get_beneficiaries(page: int = None, limit: int = None):
    """Fetch beneficiaries in real time from the web dev team's API with optional pagination."""
    res = await fetch_realtime_beneficiaries(page=page, limit=limit)
    return res

@app.post("/api/beneficiaries")
@app.post("/api/webhook/beneficiaries")
async def receive_beneficiaries_from_website(request: Request):
    """
    Webhook/Ingestion endpoint for 360 Parenting website.
    The website can POST a single beneficiary object or a list of beneficiaries.
    """
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON payload: {e}")
        
    items = payload if isinstance(payload, list) else [payload]
    received_count = 0
    
    for item in items:
        tag_no = str(item.get("tag_no", item.get("tagNo", item.get("earTagId", "")))).strip()
        if not tag_no:
            continue
            
        existing_idx = next((i for i, b in enumerate(BENEFICIARIES_STORE) if str(b.get("tag_no")) == tag_no), None)
        beneficiary_obj = {
            "_id": item.get("_id", f"b_{tag_no}"),
            "tag_no": tag_no,
            "farmer_name": item.get("beneficiaryName", item.get("farmer_name", item.get("farmerName", item.get("name", "Unknown")))),
            "father_husband_name": item.get("husbandFatherName", item.get("father_husband_name", item.get("fatherHusbandName", item.get("husband_name", "-")))),
            "village": item.get("village", ""),
            "district": item.get("district", ""),
            "do_number": item.get("doNumber", ""),
            "handover_date": item.get("handoverDate", ""),
            "handover_time": item.get("handoverTime", ""),
            "cattle_feed_kg": int(item.get("cattle_feed_kg", item.get("cattleFeedKg", item.get("cattle_feed", 25)))),
            "silage_kg": int(item.get("silage_kg", item.get("silageKg", item.get("silage", 50)))),
            "mineral_mixture_kg": int(item.get("mineral_mixture_kg", item.get("mineralMixtureKg", item.get("mineral_mixture", 5)))),
        }
        
        if existing_idx is not None:
            BENEFICIARIES_STORE[existing_idx].update(beneficiary_obj)
        else:
            BENEFICIARIES_STORE.append(beneficiary_obj)
            
        received_count += 1
        
    return {
        "success": True,
        "message": f"Successfully received and synced {received_count} beneficiary record(s).",
        "total_beneficiaries_in_app": len(BENEFICIARIES_STORE)
    }

@app.get("/api/beneficiaries/{tag_no}/qrs/download")
@app.get("/api/beneficiaries/{tag_no}/qr")
@app.get("/api/beneficiaries/{tag_no}/pdf")
@app.get("/api/beneficiaries/{tag_no}/qr-pdf")
async def download_single_qrs(tag_no: str):
    """Generate and download a 36-coupon booklet PDF for a beneficiary."""
    beneficiary = await get_beneficiary_by_tag(tag_no)
    if not beneficiary:
        beneficiary = {
            "tag_no": tag_no,
            "farmer_name": f"Beneficiary {tag_no}",
            "father_husband_name": "-",
            "village": "Default Village",
            "district": "Default District",
            "cattle_feed_kg": 25,
            "silage_kg": 50,
            "mineral_mixture_kg": 5,
        }
        
    pdf_path = await generate_qr_pdf(beneficiary)
    return FileResponse(
        path=pdf_path,
        filename=f"Coupon_Book_{tag_no}.pdf",
        media_type="application/pdf",
        background=BackgroundTask(lambda: os.remove(pdf_path) if os.path.exists(pdf_path) else None)
    )

@app.get("/api/beneficiaries/qrs/download")
async def download_all_qrs():
    """Download all active beneficiaries' 36-coupon booklet PDFs."""
    all_beneficiaries = await fetch_realtime_beneficiaries()
    pdf_path = await generate_all_qrs_pdf(all_beneficiaries)
    return FileResponse(
        path=pdf_path,
        filename="All_360_Parenting_Coupon_Books.pdf",
        media_type="application/pdf",
        background=BackgroundTask(lambda: os.remove(pdf_path) if os.path.exists(pdf_path) else None)
    )

@app.get("/api/qr/{qr_code_id}")
async def get_qr_data(qr_code_id: str, supervisor_district: str = None):
    # Parse formats: "62313-M1-SILAGE", "62313-M1-CATTLEFEED", "62313-M12-MINERALS", "62313-M1", "62313"
    tag_no = qr_code_id
    month = 1
    product_code = None
    product_name = None
    product_qty = None

    qr_match = re.match(r"^([^-]+)-M(\d+)(?:-(.*))?$", qr_code_id.strip(), re.IGNORECASE)
    if qr_match:
        tag_no = qr_match.group(1)
        month = int(qr_match.group(2))
        product_code = qr_match.group(3).upper() if qr_match.group(3) else None

    beneficiary = await get_beneficiary_by_tag(tag_no)
    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiary not found")

    if supervisor_district:
        b_district = str(beneficiary.get('district', '')).strip().lower()
        s_district = supervisor_district.strip().lower()
        if b_district != s_district:
            raise HTTPException(
                status_code=403,
                detail=f"INVALID QR: Belongs to {beneficiary.get('district')}, but logged in for {supervisor_district}."
            )

    # Match product metadata if product code is in the QR
    if product_code:
        if "SIL" in product_code:
            product_name = "Silage"
            product_qty = beneficiary.get("silage_kg", 50)
        elif "CATTLE" in product_code or "CF" in product_code or "FEED" in product_code:
            product_name = "Cattle Feed"
            product_qty = beneficiary.get("cattle_feed_kg", 25)
        elif "MIN" in product_code:
            product_name = "Mineral Mixture"
            product_qty = beneficiary.get("mineral_mixture_kg", 5)

    is_completed = qr_code_id in DELIVERIES_STORE

    return {
        "beneficiary": beneficiary,
        "month": month,
        "product_code": product_code,
        "product_name": product_name,
        "product_qty": product_qty,
        "is_completed": is_completed,
        "qr_code_id": qr_code_id
    }

@app.post("/api/deliveries/{tag_no}")
async def complete_delivery(
    tag_no: str,
    partner_photo: UploadFile = File(...),
    receiver_photo: UploadFile = File(...),
    items_photo: UploadFile = File(...),
    video_proof: UploadFile = File(...),
    supervisor_district: str = Form(None),
    supervisor_name: str = Form(None),
    partner_name: str = Form(None)
):
    parts = tag_no.split("-M")
    b_tag_no = parts[0] if len(parts) > 0 else tag_no
    beneficiary = await get_beneficiary_by_tag(b_tag_no)

    # Save media locally
    async def save_file(upload_file: UploadFile, suffix: str):
        filename = f"{tag_no}_{uuid.uuid4().hex[:8]}{suffix}"
        filepath = os.path.join(MEDIA_UPLOAD_DIR, filename)
        content = await upload_file.read()
        with open(filepath, "wb") as f:
            f.write(content)
        return filepath

    partner_path = await save_file(partner_photo, ".jpg")
    receiver_path = await save_file(receiver_photo, ".jpg")
    items_path = await save_file(items_photo, ".jpg")
    video_path = await save_file(video_proof, ".mp4")

    delivery_data = {
        "tag_no": tag_no,
        "partner_name": supervisor_name or partner_name or "Supervisor",
        "supervisor_name": supervisor_name or partner_name or "Supervisor",
        "partner_photo_url": partner_path,
        "receiver_photo_url": receiver_path,
        "items_photo_url": items_path,
        "video_proof_url": video_path,
        "status": "delivered",
        "beneficiary": beneficiary or {},
        "created_at": datetime.now().isoformat()
    }

    DELIVERIES_STORE[tag_no] = delivery_data

    return {"message": "Delivery completed successfully", "id": tag_no}

@app.get("/api/deliveries/{tag_no}")
async def get_delivery(tag_no: str):
    delivery = DELIVERIES_STORE.get(tag_no)
    if not delivery:
        parts = tag_no.split("-M")
        b_tag = parts[0] if len(parts) > 0 else tag_no
        beneficiary = await get_beneficiary_by_tag(b_tag)
        return {
            "tag_no": tag_no,
            "status": "delivered",
            "supervisor_name": "Supervisor",
            "partner_name": "Supervisor",
            "beneficiary": beneficiary or {"farmer_name": "Beneficiary", "village": "-", "district": "-"},
            "partner_photo_url": "",
            "receiver_photo_url": "",
            "items_photo_url": "",
            "video_proof_url": ""
        }
    return delivery

@app.get("/api/deliveries/{tag_no}/invoice.pdf")
async def get_invoice_pdf(tag_no: str):
    delivery = DELIVERIES_STORE.get(tag_no, {})
    if not delivery:
        parts = tag_no.split("-M")
        b_tag = parts[0] if len(parts) > 0 else tag_no
        beneficiary = await get_beneficiary_by_tag(b_tag)
        delivery = {
            "tag_no": tag_no,
            "supervisor_name": "Supervisor",
            "partner_name": "Supervisor",
            "beneficiary": beneficiary or {"farmer_name": "Beneficiary", "village": "-", "district": "-"}
        }

    pdf_path = await generate_invoice_pdf(delivery)
    return FileResponse(
        path=pdf_path,
        filename=f"invoice_{tag_no}.pdf",
        media_type="application/pdf",
        background=BackgroundTask(lambda: os.remove(pdf_path) if os.path.exists(pdf_path) else None)
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
