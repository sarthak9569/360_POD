import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import deliveries_collection
from cloudinary_service import upload_media
from models import DeliveryCreate
import asyncio

app = FastAPI(title="Proof of Delivery Backend")

# Allow CORS for all networks (0.0.0.0)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
