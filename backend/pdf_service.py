from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import httpx
import tempfile
import os
import asyncio
from datetime import datetime

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
    farmer_name = "master 1"
    c.drawRightString(width - 40, height - 160, farmer_name)
    c.drawRightString(width - 40, height - 175, "G99H+F9W")
    c.drawRightString(width - 40, height - 190, "Meerut Division")
    
    # 4. Table Header
    table_y = height - 250
    c.setStrokeColor(colors.black)
    c.line(40, table_y, width - 40, table_y)
    
    c.setFont("Helvetica-Bold", 11)
    c.drawString(45, table_y - 15, "Item")
    c.drawString(200, table_y - 15, "Subsidy Item")
    c.drawString(400, table_y - 15, "Quantity")
    
    # Table Row Background
    c.setFillColor(colors.HexColor("#f0f5fa"))
    c.rect(40, table_y - 45, width - 80, 25, fill=1, stroke=0)
    
    # Table Row Text
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawString(45, table_y - 38, "1")
    c.drawString(200, table_y - 38, "Cattle Feed")
    c.drawString(400, table_y - 38, "25.0 kg")
    
    # Table Bottom Line
    c.setStrokeColor(colors.black)
    c.line(40, table_y - 45, width - 40, table_y - 45)
    
    # 5. Proof of Delivery Video
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, table_y - 80, "Proof of Delivery Video:")
    
    video_url = delivery_data.get("video_proof_url", "No video provided")
    c.setFont("Helvetica", 10)
    c.setFillColor(colors.blue)
    c.drawString(40, table_y - 100, "Tap here to view the Delivery Proof Video")
    
    # Make video link clickable
    c.linkURL(video_url, (40, table_y - 105, 250, table_y - 90), relative=0)
    
    c.setFillColor(colors.HexColor("#333333"))
    c.setFont("Helvetica", 8)
    c.drawString(40, table_y - 115, f"URL: {video_url}")
    
    # 6. Attached Images
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, table_y - 150, "Attached Images:")
    
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
    
    images = await asyncio.gather(
        download_image(partner_url),
        download_image(receiver_url),
        download_image(items_url)
    )
    
    img_y = table_y - 280
    x_positions = [40, 220, 400]
    labels = ["Partner Photo", "Receiver Photo", "Items Photo"]
    
    for i, img_path in enumerate(images):
        if img_path:
            try:
                c.drawImage(img_path, x_positions[i], img_y, width=150, height=100, preserveAspectRatio=True)
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
