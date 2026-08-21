import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import deliveries_collection, beneficiaries_collection, supervisors_collection
from cloudinary_service import upload_media
from models import DeliveryCreate, BeneficiaryCreate, PartnerLogin, SupervisorCreate
from bson import ObjectId
import asyncio
from pydantic import BaseModel
import pandas as pd
import io
import hashlib

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

@app.on_event("startup")
async def seed_supervisors():
    count = await supervisors_collection.count_documents({})
    if count == 0:
        for district, name in SUPERVISORS_MAPPING.items():
            await supervisors_collection.insert_one({
                "name": name,
                "districts": [district],
                "villages": []
            })
        print("Seeded initial supervisors.")

@app.get("/api/districts")
async def get_districts():
    supervisors = await supervisors_collection.find({}).to_list(length=1000)
    districts = set()
    for s in supervisors:
        districts.update([str(d).strip().title() for d in s.get("districts", [])])
        
    b_districts = await beneficiaries_collection.distinct("district")
    if b_districts:
        districts.update([str(d).strip().title() for d in b_districts if d and str(d).lower() != 'nan'])
        
    valid_districts = sorted(list(districts))
    return valid_districts

@app.get("/api/districts/{district}/villages")
async def get_villages(district: str):
    import re
    villages = set()
    
    district_clean = district.strip()
    escaped = re.escape(district_clean)
    regex = f"^\\s*{escaped}\\s*$"
    
    # 1. Get from beneficiaries collection
    b_villages = await beneficiaries_collection.distinct("village", {"district": {"$regex": regex, "$options": "i"}})
    if b_villages:
        villages.update([str(v).strip().title() for v in b_villages if v and str(v).lower() != 'nan'])
        
    # 2. Get from supervisors assigned to this district
    supervisors = await supervisors_collection.find({
        "districts": {"$regex": regex, "$options": "i"}
    }).to_list(length=1000)
    
    for s in supervisors:
        villages.update([str(v).strip().title() for v in s.get("villages", [])])
        
    valid_villages = sorted(list(villages))
    return valid_villages

@app.post("/api/partner/login")
async def partner_login(payload: PartnerLogin):
    # Find supervisor by name and check if they have the requested district
    # Using case-insensitive regex for name search
    supervisor = await supervisors_collection.find_one({
        "name": {"$regex": f"^{payload.supervisor_name}$", "$options": "i"}
    })
    
    if not supervisor:
        raise HTTPException(status_code=403, detail="Invalid supervisor name.")
        
    # Check if the district is in their allocated districts (case-insensitive check)
    assigned_districts = [d.lower() for d in supervisor.get("districts", [])]
    if payload.district.lower() not in assigned_districts:
        raise HTTPException(status_code=403, detail="Access Denied: Supervisor not assigned to this district.")
        
    return {"success": True, "partner_name": payload.partner_name, "district": payload.district, "village": payload.village}

@app.get("/api/supervisors")
async def get_supervisors():
    cursor = supervisors_collection.find({})
    supervisors = await cursor.to_list(length=1000)
    for s in supervisors:
        s['_id'] = str(s['_id'])
    return supervisors

@app.post("/api/supervisors")
async def create_supervisor(supervisor: SupervisorCreate):
    supervisor_dict = supervisor.dict()
    result = await supervisors_collection.insert_one(supervisor_dict)
    supervisor_dict["_id"] = str(result.inserted_id)
    return supervisor_dict

@app.put("/api/supervisors/{supervisor_id}")
async def update_supervisor(supervisor_id: str, supervisor: SupervisorCreate):
    if not ObjectId.is_valid(supervisor_id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    
    result = await supervisors_collection.update_one(
        {"_id": ObjectId(supervisor_id)},
        {"$set": supervisor.dict()}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    return {"message": "Updated successfully"}

@app.delete("/api/supervisors/{supervisor_id}")
async def delete_supervisor(supervisor_id: str):
    if not ObjectId.is_valid(supervisor_id):
        raise HTTPException(status_code=400, detail="Invalid ID")
        
    result = await supervisors_collection.delete_one({"_id": ObjectId(supervisor_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    return {"message": "Deleted successfully"}


@app.post("/api/admin/login")
async def admin_login(creds: AdminLogin):
    # Hardcoded for now per plan
    if creds.username == "admin" and creds.password == "password123":
        return {"message": "Login successful", "token": "admin-fake-token"}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/api/beneficiaries")
async def get_beneficiaries():
    cursor = beneficiaries_collection.find({})
    beneficiaries = await cursor.to_list(length=10000)
    for b in beneficiaries:
        b['_id'] = str(b['_id'])
    return beneficiaries

@app.get("/api/beneficiaries/qrs/download")
async def download_all_qrs():
    cursor = beneficiaries_collection.find({})
    beneficiaries = await cursor.to_list(length=10000)
    
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
        
        # Read ALL sheets
        sheet_dict = pd.read_excel(io.BytesIO(contents), sheet_name=None, header=None)
        
        total_rows = 0
        successfully_imported = 0
        beneficiaries_created = 0
        beneficiaries_reused = 0
        distributions_created = 0
        skipped_rows = 0
        invalid_rows = []
        duplicate_conflicting_rows = []
        validation_errors = []
        
        for sheet_name, raw_df in sheet_dict.items():
            header_idx = -1
            for i, row in raw_df.iterrows():
                row_str = ' '.join(str(val).lower() for val in row.values)
                if 'tag no.' in row_str or 'tag no' in row_str or 'beneficiary name' in row_str or 'farmer name' in row_str:
                    header_idx = i
                    break
                    
            if header_idx == -1:
                print(f"Skipping sheet {sheet_name} as no valid header was found.")
                continue
                
            # Read this specific sheet with the correct header
            df = pd.read_excel(io.BytesIO(contents), sheet_name=sheet_name, header=header_idx)
            df.columns = [str(c).strip().lower() for c in df.columns]
            
            # Rename alternative columns to match the expected map
            rename_map = {}
            for col in df.columns:
                if col == 'farmer name':
                    rename_map[col] = 'beneficiary name'
                elif 'father/husband' in col or 'father / husband' in col or 'father /husband' in col:
                    rename_map[col] = "husband's name"
                elif col == 'tag no':
                    rename_map[col] = 'tag no.'
                elif 'cattle feed' in col:
                    rename_map[col] = 'cattle feed (kg)'
                elif 'silage' in col:
                    rename_map[col] = 'silage (kg)'
                    
            df.rename(columns=rename_map, inplace=True)
            
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
                print(f"Skipping sheet {sheet_name} due to missing columns: {missing_cols}")
                continue
                
            for row_idx, row in df.iterrows():
                total_rows += 1
                try:
                    tag_no = str(row.get('tag no.', '')).strip()
                    if not tag_no or tag_no == 'nan':
                        invalid_rows.append({"sheet": sheet_name, "row": row_idx + 2, "tag_no": tag_no, "reason": "Missing tag_no"})
                        skipped_rows += 1
                        continue
                    
                    # Parse quantities safely
                    def parse_qty(val):
                        if pd.isna(val) or val == '' or str(val).strip() == '-':
                            return 0
                        try:
                            return int(float(val))
                        except ValueError:
                            raise ValueError(f"Invalid numeric value: {val}")
                            
                    try:
                        cattle_feed = parse_qty(row.get('cattle feed (kg)'))
                        silage = parse_qty(row.get('silage (kg)'))
                    except ValueError as e:
                        invalid_rows.append({"sheet": sheet_name, "row": row_idx + 2, "tag_no": tag_no, "reason": str(e)})
                        skipped_rows += 1
                        continue

                    # Identity info
                    farmer_name = str(row.get('beneficiary name', '')).strip()
                    if farmer_name == 'nan': farmer_name = ''
                    father_name = str(row.get("husband's name", '')).strip()
                    if father_name == 'nan': father_name = ''
                    village = str(row.get('village', '')).strip()
                    if village == 'nan': village = ''
                    district = str(row.get('district', '')).strip()
                    if district == 'nan': district = ''

                    if not farmer_name:
                        invalid_rows.append({"sheet": sheet_name, "row": row_idx + 2, "tag_no": tag_no, "reason": "Missing beneficiary name"})
                        skipped_rows += 1
                        continue

                    # Idempotency hash (use raw row values + tag_no)
                    raw_row_str = "".join([str(v) for v in row.values])
                    import_hash = hashlib.sha256(f"{tag_no}_{raw_row_str}".encode()).hexdigest()

                    existing = await beneficiaries_collection.find_one({"tag_no": tag_no})
                    
                    if existing:
                        # Identity mismatch check (allow minor case differences)
                        ex_name = str(existing.get('farmer_name', '')).strip().lower()
                        ex_village = str(existing.get('village', '')).strip().lower()
                        
                        if ex_name and farmer_name.lower() != ex_name:
                            duplicate_conflicting_rows.append({
                                "sheet": sheet_name, "row": row_idx + 2, "tag_no": tag_no, 
                                "reason": f"Identity mismatch. Excel: {farmer_name} | DB: {existing.get('farmer_name')}"
                            })
                            skipped_rows += 1
                            continue

                        # Check if distribution already imported
                        existing_dists = existing.get('distributions', [])
                        if any(d.get('import_hash') == import_hash for d in existing_dists):
                            # Idempotent duplicate
                            skipped_rows += 1
                            continue
                            
                        # Add new distribution and increment totals
                        new_dist = {
                            "cattle_feed_kg": cattle_feed,
                            "silage_kg": silage,
                            "import_hash": import_hash
                        }
                        
                        await beneficiaries_collection.update_one(
                            {"tag_no": tag_no},
                            {
                                "$push": {"distributions": new_dist},
                                "$inc": {
                                    "cattle_feed_kg": cattle_feed,
                                    "silage_kg": silage
                                }
                            }
                        )
                        beneficiaries_reused += 1
                        distributions_created += 1
                        successfully_imported += 1
                        
                    else:
                        # Create new beneficiary
                        beneficiary_data = {
                            "tag_no": tag_no,
                            "farmer_name": farmer_name,
                            "father_husband_name": father_name,
                            "village": village,
                            "district": district,
                            "cattle_feed_kg": cattle_feed,
                            "silage_kg": silage,
                            "distributions": [{
                                "cattle_feed_kg": cattle_feed,
                                "silage_kg": silage,
                                "import_hash": import_hash
                            }]
                        }
                        
                        await beneficiaries_collection.insert_one(beneficiary_data)
                        beneficiaries_created += 1
                        distributions_created += 1
                        successfully_imported += 1
                        
                except Exception as e:
                    validation_errors.append({"sheet": sheet_name, "row": row_idx + 2, "tag_no": tag_no, "reason": str(e)})
                    skipped_rows += 1
                    
        return {
            "message": "Upload complete",
            "summary": {
                "Total rows": total_rows,
                "Successfully imported": successfully_imported,
                "Beneficiaries created": beneficiaries_created,
                "Existing beneficiaries reused": beneficiaries_reused,
                "Distribution records created": distributions_created,
                "Skipped rows": skipped_rows,
            },
            "Invalid rows": invalid_rows,
            "Duplicate/conflicting rows": duplicate_conflicting_rows,
            "Validation errors": validation_errors
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.delete("/api/beneficiaries/{tag_no}")
async def delete_beneficiary(tag_no: str):
    result = await beneficiaries_collection.delete_one({"tag_no": tag_no})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Beneficiary not found")
    return {"message": "Deleted successfully"}

@app.get("/api/qr/{qr_code_id}")
async def get_qr_data(qr_code_id: str, supervisor_district: str = None):
    # qr_code_id format is typically "TAG_NO-MX"
    parts = qr_code_id.split("-M")
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid QR code format")
    
    tag_no = parts[0]
    month = parts[1]
    
    beneficiary = await beneficiaries_collection.find_one({"tag_no": tag_no})
    if not beneficiary:
        raise HTTPException(status_code=404, detail="Beneficiary not found")
        
    if supervisor_district:
        b_district = str(beneficiary.get('district', '')).strip().lower()
        s_district = supervisor_district.strip().lower()
        if b_district != s_district:
            raise HTTPException(
                status_code=403, 
                detail=f"INVALID QR: This QR belongs to {beneficiary.get('district')}, but you are logged in for {supervisor_district}."
            )
        
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
    video_proof: UploadFile = File(...),
    supervisor_district: str = Form(None)
):
    try:
        # Check authorization if supervisor_district is provided
        if supervisor_district:
            parts = tag_no.split("-M")
            b_tag_no = parts[0] if len(parts) > 0 else tag_no
            beneficiary = await beneficiaries_collection.find_one({"tag_no": b_tag_no})
            if beneficiary:
                b_district = str(beneficiary.get('district', '')).strip().lower()
                s_district = supervisor_district.strip().lower()
                if b_district != s_district:
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Unauthorized: Cannot complete delivery for {beneficiary.get('district')} while logged in for {supervisor_district}"
                    )

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
