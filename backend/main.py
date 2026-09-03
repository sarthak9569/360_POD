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

WEBSITE_API_URL = os.getenv("WEBSITE_API_URL", "https://360parenting.com/api")
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

BENEFICIARIES_STORE = [
    {
        "_id": "b1",
        "tag_no": "62313",
        "farmer_name": "Rameshwar Patel",
        "father_husband_name": "Shyamlal Patel",
        "village": "Mahasamund",
        "district": "Mahasamund",
        "cattle_feed_kg": 25,
        "silage_kg": 50,
        "mineral_mixture_kg": 5,
    },
    {
        "_id": "b2",
        "tag_no": "78201",
        "farmer_name": "Santosh Kumar",
        "father_husband_name": "Dinesh Kumar",
        "village": "Kanker",
        "district": "Kanker",
        "cattle_feed_kg": 30,
        "silage_kg": 60,
        "mineral_mixture_kg": 10,
    },
    {
        "_id": "b3",
        "tag_no": "91044",
        "farmer_name": "Gita Bai Sahu",
        "father_husband_name": "Maniram Sahu",
        "village": "Kondagaon",
        "district": "Kondagaon",
        "cattle_feed_kg": 20,
        "silage_kg": 40,
        "mineral_mixture_kg": 5,
    },
    {
        "_id": "b4",
        "tag_no": "44912",
        "farmer_name": "Dhaniram Netam",
        "father_husband_name": "Kripal Netam",
        "village": "Sarangarh",
        "district": "Sharangarh",
        "cattle_feed_kg": 35,
        "silage_kg": 70,
        "mineral_mixture_kg": 10,
    },
    {
        "_id": "b5",
        "tag_no": "31908",
        "farmer_name": "Sunil Yadav",
        "father_husband_name": "Brijesh Yadav",
        "village": "Balrampur",
        "district": "Balrampur",
        "cattle_feed_kg": 25,
        "silage_kg": 50,
        "mineral_mixture_kg": 5,
    },
]

DELIVERIES_STORE = {}

@app.get("/api/districts")
async def get_districts():
    # Attempt to fetch from 360 Parenting website API if available
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{WEBSITE_API_URL}/districts")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    
    # Fallback to mapped districts
    districts = set()
    for s in SUPERVISORS_DATA:
        districts.update(s.get("districts", []))
    for b in BENEFICIARIES_STORE:
        districts.add(b.get("district", ""))
    return sorted(list(filter(None, districts)))

@app.get("/api/districts/{district}/villages")
async def get_villages(district: str):
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{WEBSITE_API_URL}/districts/{district}/villages")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass

    villages = set()
    d_clean = district.strip().lower()
    for s in SUPERVISORS_DATA:
        if any(d.strip().lower() == d_clean for d in s.get("districts", [])):
            villages.update(s.get("villages", []))
    for b in BENEFICIARIES_STORE:
        if b.get("district", "").strip().lower() == d_clean:
            villages.add(b.get("village", ""))
    return sorted(list(filter(None, villages)))

@app.post("/api/partner/login")
async def partner_login(payload: PartnerLogin):
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(f"{WEBSITE_API_URL}/partner/login", json=payload.dict())
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass

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
async def get_beneficiaries():
    """Fetch all beneficiaries added on the 360 Parenting website."""
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(f"{WEBSITE_API_URL}/beneficiaries")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return BENEFICIARIES_STORE

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
        tag_no = str(item.get("tag_no", item.get("tagNo", ""))).strip()
        if not tag_no:
            continue
            
        # Check if already exists in memory, update or insert
        existing_idx = next((i for i, b in enumerate(BENEFICIARIES_STORE) if str(b.get("tag_no")) == tag_no), None)
        beneficiary_obj = {
            "_id": item.get("_id", f"b_{tag_no}"),
            "tag_no": tag_no,
            "farmer_name": item.get("farmer_name", item.get("farmerName", item.get("name", "Unknown"))),
            "father_husband_name": item.get("father_husband_name", item.get("fatherHusbandName", item.get("husband_name", "-"))),
            "village": item.get("village", ""),
            "district": item.get("district", ""),
            "cattle_feed_kg": int(item.get("cattle_feed_kg", item.get("cattleFeedKg", item.get("cattle_feed", 0)))),
            "silage_kg": int(item.get("silage_kg", item.get("silageKg", item.get("silage", 0)))),
            "mineral_mixture_kg": int(item.get("mineral_mixture_kg", item.get("mineralMixtureKg", item.get("mineral_mixture", 0)))),
        }
        
        if existing_idx is not None:
            BENEFICIARIES_STORE[existing_idx] = beneficiary_obj
        else:
            BENEFICIARIES_STORE.append(beneficiary_obj)
            
        received_count += 1
        
    return {
        "success": True,
        "message": f"Successfully received and synced {received_count} beneficiary record(s).",
        "total_beneficiaries_in_app": len(BENEFICIARIES_STORE)
    }

@app.get("/api/beneficiaries/{tag_no}/qrs/download")
async def download_single_qrs(tag_no: str):
    """Generate and download a 12-month QR sheet PDF for a beneficiary."""
    beneficiary = next((b for b in BENEFICIARIES_STORE if str(b.get("tag_no")) == str(tag_no)), None)
    if not beneficiary:
        beneficiary = {
            "tag_no": tag_no,
            "farmer_name": f"Beneficiary {tag_no}",
            "father_husband_name": "-",
            "village": "Default Village",
            "district": "Default District",
        }
        
    pdf_path = await generate_qr_pdf(beneficiary)
    return FileResponse(
        path=pdf_path,
        filename=f"QRs_{tag_no}.pdf",
        media_type="application/pdf",
        background=BackgroundTask(lambda: os.remove(pdf_path) if os.path.exists(pdf_path) else None)
    )

@app.get("/api/beneficiaries/qrs/download")
async def download_all_qrs():
    """Download all active beneficiaries' QR code sheets."""
    pdf_path = await generate_all_qrs_pdf(BENEFICIARIES_STORE)
    return FileResponse(
        path=pdf_path,
        filename="All_360_Parenting_QRs.pdf",
        media_type="application/pdf",
        background=BackgroundTask(lambda: os.remove(pdf_path) if os.path.exists(pdf_path) else None)
    )

@app.get("/api/qr/{qr_code_id}")
async def get_qr_data(qr_code_id: str, supervisor_district: str = None):
    parts = qr_code_id.split("-M")
    tag_no = parts[0]
    month = int(parts[1]) if len(parts) > 1 else 1

    beneficiary = next((b for b in BENEFICIARIES_STORE if str(b.get("tag_no")) == str(tag_no)), None)
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

    is_completed = qr_code_id in DELIVERIES_STORE

    return {
        "beneficiary": beneficiary,
        "month": month,
        "is_completed": is_completed
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
    beneficiary = next((b for b in BENEFICIARIES_STORE if str(b.get("tag_no")) == str(b_tag_no)), None)

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
        beneficiary = next((b for b in BENEFICIARIES_STORE if str(b.get("tag_no")) == str(b_tag)), None)
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
        beneficiary = next((b for b in BENEFICIARIES_STORE if str(b.get("tag_no")) == str(b_tag)), None)
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
