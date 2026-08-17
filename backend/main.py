import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import deliveries_collection, beneficiaries_collection
from cloudinary_service import upload_media
from models import DeliveryCreate, BeneficiaryCreate, PartnerLogin
import asyncio
from pydantic import BaseModel
import pandas as pd
import io

app = FastAPI(title="Proof of Delivery Backend")

# Allow CORS for all networks (0.0.0.0)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
class AdminLogin(BaseModel):
    username: str
    password: str

SUPERVISORS_MAPPING = {
    "Mahasamund": "Ankit",
    "Kanker": "Sreekant Mandal",
    "Kondagaon": "Kishor",
    "Sharangarh": "Patel Thandaram",
    "Balrampur": "Millan Haldhar"
}

@app.get("/api/districts")
async def get_districts():
    # Return all static districts defined in SUPERVISORS_MAPPING
    return list(SUPERVISORS_MAPPING.keys())

@app.get("/api/districts/{district}/villages")
async def get_villages(district: str):
    villages = await beneficiaries_collection.distinct("village", {"district": district})
    valid_villages = sorted([v for v in villages if v and str(v).lower() != 'nan'])
    return valid_villages

@app.post("/api/partner/login")
async def partner_login(payload: PartnerLogin):
    # Verify if supervisor matches the district (case-insensitive)
    expected_supervisor = SUPERVISORS_MAPPING.get(payload.district)
    if not expected_supervisor:
        raise HTTPException(status_code=403, detail="Invalid district or no supervisor mapped.")
    
    if expected_supervisor.lower() != payload.supervisor_name.lower():
        raise HTTPException(status_code=403, detail="Access Denied: Incorrect supervisor name for this district.")
        
    return {"success": True, "partner_name": payload.partner_name, "district": payload.district, "village": payload.village}


@app.post("/api/admin/login")
async def admin_login(creds: AdminLogin):
    # Hardcoded for now per plan
    if creds.username == "admin" and creds.password == "password123":
        return {"message": "Login successful", "token": "admin-fake-token"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/api/beneficiaries")
async def get_beneficiaries():
    cursor = beneficiaries_collection.find({})
    beneficiaries = await cursor.to_list(length=100)
    for b in beneficiaries:
        b['_id'] = str(b['_id'])
    return beneficiaries

@app.get("/api/beneficiaries/qrs/download")
async def download_all_qrs():
    cursor = beneficiaries_collection.find({})
    beneficiaries = await cursor.to_list(length=1000)
    
    if not beneficiaries:
        raise HTTPException(status_code=404, detail="No active beneficiaries found")
        
    pdf_path = await generate_all_qrs_pdf(beneficiaries)
    
    return FileResponse(
        path=pdf_path, 
        filename="All_Active_QRs.pdf", 
        media_type="application/pdf",
        background=BackgroundTask(lambda: os.remove(pdf_path) if os.path.exists(pdf_path) else None)
    )

from pdf_service import generate_qr_pdf, generate_all_qrs_pdf
from starlette.background import BackgroundTask
from fastapi.responses import FileResponse

@app.post("/api/beneficiaries")
async def create_beneficiary(beneficiary: BeneficiaryCreate):
    # Check if exists
    existing = await beneficiaries_collection.find_one({"tag_no": beneficiary.tag_no})
    if existing:
        raise HTTPException(status_code=400, detail="Beneficiary with this tag_no already exists")
    
    # Insert to DB
    beneficiary_dict = beneficiary.dict()
    result = await beneficiaries_collection.insert_one(beneficiary_dict)
    
    # Generate QR PDF
    pdf_path = await generate_qr_pdf(beneficiary_dict)
    
    return FileResponse(
        path=pdf_path, 
        filename=f"QRs_{beneficiary.tag_no}.pdf", 
        media_type="application/pdf",
        background=BackgroundTask(lambda: os.remove(pdf_path) if os.path.exists(pdf_path) else None)
    )

@app.get("/api/beneficiaries/{tag_no}/qrs/download")
async def download_single_qrs(tag_no: str):
    beneficiary = await beneficiaries_collection.find_one({"tag_no": tag_no})
    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiary not found")
    
    pdf_path = await generate_qr_pdf(beneficiary)
    
    return FileResponse(
        path=pdf_path, 
        filename=f"QRs_{tag_no}.pdf", 
        media_type="application/pdf",
        background=BackgroundTask(lambda: os.remove(pdf_path) if os.path.exists(pdf_path) else None)
    )

@app.post("/api/beneficiaries/upload")
async def upload_beneficiaries(file: UploadFile = File(...)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")
    
    try:
        contents = await file.read()
        
        # Read without headers first to find the correct row
        raw_df = pd.read_excel(io.BytesIO(contents), header=None)
        
        header_idx = 0
        for i, row in raw_df.iterrows():
            row_str = ' '.join(str(val).lower() for val in row.values)
            if 'tag no.' in row_str or 'beneficiary name' in row_str:
                header_idx = i
                break
                
        df = pd.read_excel(io.BytesIO(contents), header=header_idx)
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # Map file columns to expected keys
        col_map = {
            'tag no.': 'tag_no',
            'beneficiary name': 'farmer_name',
            "husband's name": 'father_husband_name',
            'village': 'village',
            'district': 'district',
            'cattle feed (kg)': 'cattle_feed_kg',
            'silage (kg)': 'silage_kg'
        }
        
        missing_cols = set(col_map.keys()) - set(df.columns)
        if missing_cols:
            raise HTTPException(status_code=400, detail=f"Missing required columns: {missing_cols}")
            
        inserted_count = 0
        skipped_count = 0
        
        for _, row in df.iterrows():
            try:
                tag_no = str(row.get('tag no.', '')).strip()
                if not tag_no or tag_no == 'nan':
                    continue
                    
                existing = await beneficiaries_collection.find_one({"tag_no": tag_no})
                if existing:
                    skipped_count += 1
                    continue
                    
                beneficiary_data = {
                    "tag_no": tag_no,
                    "farmer_name": str(row.get('beneficiary name', '')),
                    "father_husband_name": str(row.get("husband's name", '')),
                    "village": str(row.get('village', '')),
                    "district": str(row.get('district', '')),
                    "cattle_feed_kg": int(row.get('cattle feed (kg)', 0) if pd.notna(row.get('cattle feed (kg)')) else 0),
                    "silage_kg": int(row.get('silage (kg)', 0) if pd.notna(row.get('silage (kg)')) else 0),
                }
                
                beneficiary = BeneficiaryCreate(**beneficiary_data)
                
                await beneficiaries_collection.insert_one(beneficiary.dict())
                inserted_count += 1
            except Exception as e:
                print(f"Error processing row {row.get('tag_no')}: {e}")
                skipped_count += 1
                
        return {"message": "Upload complete", "inserted": inserted_count, "skipped": skipped_count}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.delete("/api/beneficiaries/{tag_no}")
async def delete_beneficiary(tag_no: str):
    result = await beneficiaries_collection.delete_one({"tag_no": tag_no})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Beneficiary not found")
    return {"message": "Deleted successfully"}

@app.get("/api/qr/{qr_code_id}")
async def get_qr_data(qr_code_id: str):
    # qr_code_id format is typically "TAG_NO-MX"
    parts = qr_code_id.split("-M")
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid QR code format")
    
    tag_no = parts[0]
    month = parts[1]
    
    beneficiary = await beneficiaries_collection.find_one({"tag_no": tag_no})
    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiary not found")
        
    # Check if this specific month's QR code has already been used
    existing_delivery = await deliveries_collection.find_one({"tag_no": qr_code_id})
    is_completed = existing_delivery is not None
        
    beneficiary['_id'] = str(beneficiary['_id'])
    
    # Return both the beneficiary and the month context
    return {
        "beneficiary": beneficiary,
        "month": int(month),
        "is_completed": is_completed
    }

@app.post("/api/deliveries/{tag_no}")
async def complete_delivery(
    tag_no: str,
    partner_photo: UploadFile = File(...),
    receiver_photo: UploadFile = File(...),
    items_photo: UploadFile = File(...),
    video_proof: UploadFile = File(...)
):
    try:
        # Read files into memory for uploading
        partner_bytes = await partner_photo.read()
        receiver_bytes = await receiver_photo.read()
        items_bytes = await items_photo.read()
        video_bytes = await video_proof.read()

        # Temporary files are needed for cloudinary SDK upload
        import tempfile
        import os

        def temp_upload(file_bytes, is_video=False):
            suffix = ".mp4" if is_video else ".jpg"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                f.write(file_bytes)
                temp_path = f.name
            
            try:
                url = upload_media(temp_path, is_video=is_video)
                return url
            finally:
                os.remove(temp_path)

        # Upload files concurrently to cloudinary to speed up response
        loop = asyncio.get_event_loop()
        partner_url, receiver_url, items_url, video_url = await asyncio.gather(
            loop.run_in_executor(None, temp_upload, partner_bytes, False),
            loop.run_in_executor(None, temp_upload, receiver_bytes, False),
            loop.run_in_executor(None, temp_upload, items_bytes, False),
            loop.run_in_executor(None, temp_upload, video_bytes, True)
        )

        if not all([partner_url, receiver_url, items_url, video_url]):
            raise HTTPException(status_code=500, detail="Failed to upload one or more media files to Cloudinary")

        # Create delivery record
        delivery_data = {
            "tag_no": tag_no,
            "partner_name": "Test Partner", # Ideally passed from app, but matching models.py for now
            "partner_photo_url": partner_url,
            "receiver_photo_url": receiver_url,
            "items_photo_url": items_url,
            "video_proof_url": video_url,
            "status": "delivered"
        }

        # Insert into MongoDB
        result = await deliveries_collection.insert_one(delivery_data)
        
        return {"message": "Delivery completed successfully", "id": str(result.inserted_id)}

    except Exception as e:
        print(f"Error processing delivery: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from pdf_service import generate_invoice_pdf

@app.get("/api/deliveries/{tag_no}")
async def get_delivery(tag_no: str):
    delivery = await deliveries_collection.find_one({"tag_no": tag_no})
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    delivery['_id'] = str(delivery['_id'])
    
    parts = tag_no.split("-M")
    if len(parts) > 0:
        ben_tag = parts[0]
        beneficiary = await beneficiaries_collection.find_one({"tag_no": ben_tag})
        if beneficiary:
            beneficiary['_id'] = str(beneficiary['_id'])
            delivery['beneficiary'] = beneficiary

    return delivery

@app.get("/api/deliveries/{tag_no}/invoice.pdf")
async def get_invoice_pdf(tag_no: str):
    delivery = await deliveries_collection.find_one({"tag_no": tag_no})
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    pdf_path = await generate_invoice_pdf(delivery)
    return FileResponse(
        path=pdf_path, 
        filename=f"invoice_{tag_no}.pdf", 
        media_type="application/pdf",
        background=BackgroundTask(lambda: os.remove(pdf_path) if os.path.exists(pdf_path) else None)
    )

if __name__ == "__main__":
    import uvicorn
    # Host on 0.0.0.0 to allow physical devices on same network to connect
    uvicorn.run(app, host="0.0.0.0", port=8000)
