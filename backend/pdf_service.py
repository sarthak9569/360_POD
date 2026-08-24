from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import httpx
import tempfile
import os
import asyncio
from datetime import datetime
import qrcode
from io import BytesIO
from reportlab.lib.utils import ImageReader

async def generate_invoice_pdf(delivery_data: dict) -> str:
    """Generates a PDF invoice matched to the provided design."""
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_pdf_path = temp_pdf.name
    temp_pdf.close()
    
    c = canvas.Canvas(temp_pdf_path, pagesize=letter)
    width, height = letter # 612 x 792 points
    
    # 1. Top Blue Header
    c.setFillColor(colors.HexColor("#104e76"))
    c.rect(0, height - 110, width, 110, fill=1, stroke=0)
    
    # INVOICE text
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 36)
    c.drawString(40, height - 70, "INVOICE")
    
    # Company details right-aligned
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(width - 40, height - 30, "My Animal")
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 40, height - 45, "Sector 132, Noida (default)")
    c.drawRightString(width - 40, height - 60, "Uttar Pradesh, 201304")
    c.drawRightString(width - 40, height - 75, "+91 1800-123-456")
    c.drawRightString(width - 40, height - 90, "support@myanimal.com")
    
    # 2. Invoice Details (Left)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, height - 150, "Invoice No.")
    c.drawString(40, height - 170, "Date of Issue")
    
    c.setFont("Helvetica", 10)
    tag_no = delivery_data.get('tag_no', '62313')
    date_str = datetime.now().strftime("%B %d, %Y")
    
    c.drawString(120, height - 150, tag_no)
    c.drawString(120, height - 170, date_str)
    
    # Draw grey lines under values
    c.setStrokeColor(colors.HexColor("#e0e0e0"))
    c.line(115, height - 152, 250, height - 152)
    c.line(115, height - 172, 250, height - 172)
    
    # 3. Bill To (Right)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width - 40, height - 140, "Bill To")
    
    c.setFont("Helvetica", 10)
    beneficiary = delivery_data.get('beneficiary', {})
    farmer_name = beneficiary.get('farmer_name', 'Unknown')
    village = beneficiary.get('village', 'Unknown')
    district = beneficiary.get('district', 'Unknown')
    
    c.drawRightString(width - 40, height - 160, farmer_name)
    c.drawRightString(width - 40, height - 175, f"Village: {village}")
    c.drawRightString(width - 40, height - 190, f"District: {district}")
    
    # 4. Table Header
    table_y = height - 250
    c.setStrokeColor(colors.black)
    c.line(40, table_y, width - 40, table_y)
    
    c.setFont("Helvetica-Bold", 11)
    c.drawString(45, table_y - 15, "Item")
    c.drawString(200, table_y - 15, "Subsidy Item")
    c.drawString(400, table_y - 15, "Quantity")
    
    items = []
    cattle = beneficiary.get('cattle_feed_kg', 0)
    silage = beneficiary.get('silage_kg', 0)
    mineral = beneficiary.get('mineral_mixture_kg', 0)
    
    if cattle > 0:
        items.append(("Cattle Feed", f"{cattle} kg"))
    if silage > 0:
        items.append(("Silage", f"{silage} kg"))
    if mineral > 0:
        items.append(("Mineral Mixture", f"{mineral} kg"))
        
    if not items:
        items.append(("Cattle Feed", "25.0 kg"))
        
    y_offset = 45
    for idx, (item_name, item_qty) in enumerate(items, start=1):
        if idx % 2 == 1:
            c.setFillColor(colors.HexColor("#f0f5fa"))
            c.rect(40, table_y - y_offset, width - 80, 25, fill=1, stroke=0)
            
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)
        c.drawString(45, table_y - y_offset + 7, str(idx))
        c.drawString(200, table_y - y_offset + 7, item_name)
        c.drawString(400, table_y - y_offset + 7, item_qty)
        y_offset += 25
    
    # Table Bottom Line
    c.setStrokeColor(colors.black)
    c.line(40, table_y - y_offset + 25, width - 40, table_y - y_offset + 25)
    
    current_y = table_y - y_offset
    
    # Check if we need a new page for the video and images
    if current_y < 380:
        c.showPage()
        current_y = height - 100
        
    # 5. Proof of Delivery Video & 6. Attached Images
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, current_y - 35, "Proof of Delivery Video:")
    
    video_url = delivery_data.get("video_proof_url", "No video provided")
    c.setFillColor(colors.HexColor("#333333"))
    c.setFont("Helvetica", 8)
    c.drawString(40, current_y - 50, f"URL: {video_url}")
    
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, current_y - 185, "Attached Images:")
    
    async def download_image(url):
        if not url: return None
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    tf = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                    tf.write(resp.content)
                    tf.close()
                    return tf.name
        except Exception as e:
            print(f"Error downloading image for PDF: {e}")
        return None
        
    partner_url = delivery_data.get("partner_photo_url")
    receiver_url = delivery_data.get("receiver_photo_url")
    items_url = delivery_data.get("items_photo_url")
    video_thumb_url = video_url.replace('.mp4', '.jpg') if video_url and '.mp4' in video_url else None
    
    images = await asyncio.gather(
        download_image(video_thumb_url),
        download_image(partner_url),
        download_image(receiver_url),
        download_image(items_url)
    )
    
    # Draw Video Thumbnail
    if images[0]:
        try:
            c.drawImage(images[0], 40, current_y - 155, width=150, height=100, preserveAspectRatio=True)
            # Make video thumbnail clickable to the original video URL
            if video_url and video_url != "No video provided":
                c.linkURL(video_url, (40, current_y - 155, 190, current_y - 55), relative=0)
            
            # Overlay a play button or text (simulated)
            c.setFillColor(colors.white)
            c.rect(100, current_y - 115, 30, 20, fill=1, stroke=0)
            c.setFillColor(colors.red)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(102, current_y - 110, "PLAY")
            
            os.remove(images[0])
        except Exception as e:
            print(f"Failed to draw video thumbnail: {e}")

    # Draw Other Images
    img_y = current_y - 315
    x_positions = [40, 220, 400]
    labels = ["Partner Photo", "Receiver Photo", "Items Photo"]
    
    for i, img_path in enumerate(images[1:]):
        if img_path:
            try:
                c.drawImage(img_path, x_positions[i], img_y, width=150, height=100, preserveAspectRatio=True)
                c.setFillColor(colors.black)
                c.setFont("Helvetica", 10)
                c.drawString(x_positions[i], img_y - 15, labels[i])
                os.remove(img_path)
            except Exception as e:
                print(f"Failed to draw image: {e}")
                
    # 7. Bottom Blue Footer
    c.setFillColor(colors.HexColor("#104e76"))
    c.rect(0, 0, width, 40, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(width / 2.0, 15, "Thank you for your business!")
    
    c.save()
    return temp_pdf_path

async def generate_qr_pdf(beneficiary_data: dict) -> str:
    """Generates a PDF containing 12 monthly QR codes for a beneficiary."""
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_pdf_path = temp_pdf.name
    temp_pdf.close()
    
    c = canvas.Canvas(temp_pdf_path, pagesize=letter)
    width, height = letter
    
    tag_no = beneficiary_data.get('tag_no', 'UNKNOWN')
    name = beneficiary_data.get('farmer_name', 'Unknown')
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, height - 40, f"Monthly QR Codes for: {name} (Tag: {tag_no})")
    
    # Grid layout for 12 QRs (3 columns, 4 rows)
    cols = 3
    rows = 4
    qr_size = 120
    x_spacing = 180
    y_spacing = 160
    
    start_x = 40
    start_y = height - 200
    
    for i in range(12):
        month = i + 1
        qr_data_string = f"{tag_no}-M{month}"
        
        # Generate QR code in memory
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data_string)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to BytesIO
        img_buffer = BytesIO()
        img.save(img_buffer)
        img_buffer.seek(0)
        
        col = i % cols
        row = i // cols
        
        x = start_x + (col * x_spacing)
        y = start_y - (row * y_spacing)
        
        # Draw QR Image
        qr_image = ImageReader(img_buffer)
        c.drawImage(qr_image, x, y, width=qr_size, height=qr_size)
        
        # Label below QR
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(x + (qr_size/2), y - 15, f"Month {month}")
        c.setFont("Helvetica", 10)
        c.drawCentredString(x + (qr_size/2), y - 30, qr_data_string)
        
    c.save()
    return temp_pdf_path

async def generate_all_qrs_pdf(beneficiaries: list) -> str:
    """Generates a multi-page PDF containing 12 monthly QR codes for each beneficiary."""
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_pdf_path = temp_pdf.name
    temp_pdf.close()
    
    c = canvas.Canvas(temp_pdf_path, pagesize=letter)
    width, height = letter
    
    for beneficiary_data in beneficiaries:
        tag_no = beneficiary_data.get('tag_no', 'UNKNOWN')
        name = beneficiary_data.get('farmer_name', 'Unknown')
        
        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, height - 40, f"Monthly QR Codes for: {name} (Tag: {tag_no})")
        
        # Grid layout for 12 QRs (3 columns, 4 rows)
        cols = 3
        rows = 4
        qr_size = 120
        x_spacing = 180
        y_spacing = 160
        
        start_x = 40
        start_y = height - 200
        
        for i in range(12):
            month = i + 1
            qr_data_string = f"{tag_no}-M{month}"
            
            # Generate QR code in memory
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data_string)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save to BytesIO
            img_buffer = BytesIO()
            img.save(img_buffer)
            img_buffer.seek(0)
            
            col = i % cols
            row = i // cols
            
            x = start_x + (col * x_spacing)
            y = start_y - (row * y_spacing)
            
            # Draw QR Image
            qr_image = ImageReader(img_buffer)
            c.drawImage(qr_image, x, y, width=qr_size, height=qr_size)
            
            # Label below QR
            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(x + (qr_size/2), y - 15, f"Month {month}")
            c.setFont("Helvetica", 10)
            c.drawCentredString(x + (qr_size/2), y - 30, qr_data_string)
            
        c.showPage() # Move to next page for the next beneficiary
        
    c.save()
    return temp_pdf_path
