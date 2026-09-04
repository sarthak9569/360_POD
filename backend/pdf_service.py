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
    c.drawString(40, height - 190, "Delivered By")
    
    c.setFont("Helvetica", 10)
    tag_no = delivery_data.get('tag_no', '62313')
    date_str = datetime.now().strftime("%B %d, %Y")
    delivered_by = delivery_data.get('supervisor_name') or delivery_data.get('partner_name') or 'Supervisor'
    
    c.drawString(120, height - 150, tag_no)
    c.drawString(120, height - 170, date_str)
    c.drawString(120, height - 190, str(delivered_by))
    
    # Draw grey lines under values
    c.setStrokeColor(colors.HexColor("#e0e0e0"))
    c.line(115, height - 152, 250, height - 152)
    c.line(115, height - 172, 250, height - 172)
    c.line(115, height - 192, 250, height - 192)
    
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

def _make_qr_buffer(data_str: str) -> BytesIO:
    """Generates an in-memory QR code PNG image."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=2,
    )
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

def _draw_coupon_ticket(c: canvas.Canvas, x: float, y: float, w: float, h: float,
                        beneficiary: dict, product_info: dict, month: int):
    """
    Renders a single perforated voucher coupon with:
    - Left Stub (Vendor Copy) with QR code, product name, quantity, and month
    - Semicircular cutout notches & dashed tear line
    - Right Voucher (Beneficiary Copy) with Header, Product Title, Quantity,
      Month Validity Badge ('VALID FOR MONTH X ONLY'), Farmer info, and identical Right QR code.
    """
    tag_no = str(beneficiary.get('tag_no', 'UNKNOWN'))
    farmer_name = str(beneficiary.get('farmer_name', 'Beneficiary Name'))
    father_husband = str(beneficiary.get('father_husband_name', '-'))
    village = str(beneficiary.get('village', '-'))
    district = str(beneficiary.get('district', '-'))
    
    prod_name = product_info['name']
    prod_code = product_info['code']
    prod_qty = product_info['qty']
    theme_color = colors.HexColor(product_info['color'])
    dark_text = colors.HexColor("#0f172a")
    sub_text = colors.HexColor("#475569")
    
    qr_data = f"{tag_no}-M{month}-{prod_code}"
    qr_buf = _make_qr_buffer(qr_data)
    qr_img = ImageReader(qr_buf)
    
    # 1. Outer container background (rounded card with border)
    c.saveState()
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.setStrokeColor(theme_color)
    c.setLineWidth(1.5)
    c.roundRect(x, y, w, h, 10, fill=1, stroke=1)
    
    # Left stub width
    stub_w = 165
    divider_x = x + stub_w
    
    # Left Stub Background Accent
    c.setFillColor(colors.HexColor(product_info['light_bg']))
    c.rect(x + 1, y + 1, stub_w - 1, h - 2, fill=1, stroke=0)
    c.restoreState()
    
    # Re-stroke border neatly
    c.saveState()
    c.setStrokeColor(theme_color)
    c.setLineWidth(1.5)
    c.roundRect(x, y, w, h, 10, fill=0, stroke=1)
    c.restoreState()
    
    # 2. Perforated divider & circular notches
    c.saveState()
    c.setStrokeColor(colors.HexColor("#94a3b8"))
    c.setLineWidth(1)
    c.setDash([3, 3])
    c.line(divider_x, y + 12, divider_x, y + h - 12)
    c.setDash([])
    
    # Top and Bottom Notches (White semicircles with subtle border)
    notch_radius = 8
    c.setFillColor(colors.white)
    c.setStrokeColor(theme_color)
    c.setLineWidth(1.2)
    c.circle(divider_x, y + h, notch_radius, fill=1, stroke=1)
    c.circle(divider_x, y, notch_radius, fill=1, stroke=1)
    c.restoreState()
    
    # ==================== LEFT STUB (VENDOR / OFFICE COPY) ====================
    # Header Banner for Stub
    c.setFillColor(theme_color)
    c.roundRect(x + 10, y + h - 26, stub_w - 20, 18, 4, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(x + (stub_w / 2), y + h - 22, "VENDOR COPY")
    
    # Stub Month & Product Details
    c.setFillColor(dark_text)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x + 12, y + h - 42, f"MONTH {month} ONLY")
    
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(theme_color)
    c.drawString(x + 12, y + h - 56, prod_name.upper())
    
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(dark_text)
    c.drawString(x + 12, y + h - 70, f"QTY: {prod_qty}")
    
    # Beneficiary tag on stub
    c.setFont("Helvetica", 8)
    c.setFillColor(sub_text)
    farmer_disp = (farmer_name[:16] + '..') if len(farmer_name) > 16 else farmer_name
    c.drawString(x + 12, y + h - 83, f"Farmer: {farmer_disp}")
    c.drawString(x + 12, y + h - 94, f"Tag #{tag_no}")
    
    # Left Stub QR Code
    stub_qr_size = 72
    stub_qr_x = x + (stub_w - stub_qr_size) / 2
    stub_qr_y = y + 18
    
    # QR white box background
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setLineWidth(0.8)
    c.roundRect(stub_qr_x - 4, stub_qr_y - 4, stub_qr_size + 8, stub_qr_size + 8, 4, fill=1, stroke=1)
    c.drawImage(qr_img, stub_qr_x, stub_qr_y, width=stub_qr_size, height=stub_qr_size)
    
    # Stub Token Text
    c.setFont("Helvetica", 6.5)
    c.setFillColor(sub_text)
    c.drawCentredString(x + (stub_w / 2), y + 6, qr_data)
    
    # ==================== RIGHT VOUCHER (BENEFICIARY COPY) ====================
    main_x = divider_x + 15
    
    # Top Header: "360 PARENTING POD" & Month Validity Pill
    c.setFillColor(theme_color)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(main_x, y + h - 24, "360 PARENTING POD • SUBSIDY COUPON")
    
    # Month Validity Pill Badge (Top Right)
    badge_w = 128
    badge_h = 20
    badge_x = x + w - badge_w - 12
    badge_y = y + h - 28
    c.setFillColor(theme_color)
    c.roundRect(badge_x, badge_y, badge_w, badge_h, 5, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(badge_x + (badge_w / 2), badge_y + 6, f"VALID FOR MONTH {month} ONLY")
    
    # Sub-header separator line
    c.setStrokeColor(colors.HexColor("#e2e8f0"))
    c.setLineWidth(1)
    c.line(main_x, y + h - 34, x + w - 12, y + h - 34)
    
    # Product Big Title & Quantity
    c.setFillColor(theme_color)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(main_x, y + h - 56, prod_name.upper())
    
    c.setFillColor(dark_text)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(main_x + 180, y + h - 56, f"{prod_qty}")
    
    # Left Info Box for Beneficiary Details
    info_y = y + h - 74
    c.setFillColor(colors.HexColor("#f1f5f9"))
    c.roundRect(main_x, y + 14, 235, info_y - (y + 14), 6, fill=1, stroke=0)
    
    # Details rows
    row_y = info_y - 15
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(sub_text)
    c.drawString(main_x + 10, row_y, "Beneficiary Name:")
    c.setFont("Helvetica-Bold", 9.5)
    c.setFillColor(dark_text)
    c.drawString(main_x + 95, row_y, farmer_name)
    
    row_y -= 16
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(sub_text)
    c.drawString(main_x + 10, row_y, "Father/Husband:")
    c.setFont("Helvetica", 9)
    c.setFillColor(dark_text)
    c.drawString(main_x + 95, row_y, father_husband)
    
    row_y -= 16
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(sub_text)
    c.drawString(main_x + 10, row_y, "Village & District:")
    c.setFont("Helvetica", 9)
    c.setFillColor(dark_text)
    c.drawString(main_x + 95, row_y, f"{village}, {district}")
    
    row_y -= 16
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(sub_text)
    c.drawString(main_x + 10, row_y, "Tag Number:")
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(theme_color)
    c.drawString(main_x + 95, row_y, f"#{tag_no}")
    
    row_y -= 16
    c.setFont("Helvetica", 7.5)
    c.setFillColor(sub_text)
    c.drawString(main_x + 10, row_y, "Note: Present this coupon to supervisor upon monthly delivery.")
    
    # Right QR Code in Main Voucher
    main_qr_size = 90
    main_qr_x = x + w - main_qr_size - 18
    main_qr_y = y + 26
    
    # QR white container with drop outline
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setLineWidth(0.8)
    c.roundRect(main_qr_x - 5, main_qr_y - 5, main_qr_size + 10, main_qr_size + 10, 6, fill=1, stroke=1)
    c.drawImage(qr_img, main_qr_x, main_qr_y, width=main_qr_size, height=main_qr_size)
    
    # Scan verification instruction & serial number below QR
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(theme_color)
    c.drawCentredString(main_qr_x + (main_qr_size / 2), y + 14, "SCAN TO VERIFY")
    
    c.setFont("Helvetica", 6.5)
    c.setFillColor(sub_text)
    c.drawCentredString(main_qr_x + (main_qr_size / 2), y + 4, qr_data)

def _render_beneficiary_coupon_pages(c: canvas.Canvas, beneficiary_data: dict):
    """Renders 12 monthly pages (3 coupons per page = 36 coupons total) for a single beneficiary."""
    page_w, page_h = letter # 612 x 792
    
    silage_kg = beneficiary_data.get('silage_kg') or 50
    cattle_kg = beneficiary_data.get('cattle_feed_kg') or 25
    mineral_kg = beneficiary_data.get('mineral_mixture_kg') or 5
    
    for month in range(1, 13):
        # Top Page Header
        c.setFillColor(colors.HexColor("#0F172A"))
        c.rect(0, page_h - 45, page_w, 45, fill=1, stroke=0)
        
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(24, page_h - 26, f"360 PARENTING COUPON BOOK • MONTH {month} OF 12")
        
        farmer_name = beneficiary_data.get('farmer_name', 'Unknown')
        tag_no = beneficiary_data.get('tag_no', 'UNKNOWN')
        c.setFont("Helvetica", 9)
        c.drawRightString(page_w - 24, page_h - 26, f"Beneficiary: {farmer_name} (Tag: #{tag_no})")
        
        # 3 products for this month
        products = [
            {
                "name": "Silage Subsidy",
                "code": "SILAGE",
                "qty": f"{silage_kg} KG",
                "color": "#15803D",     # Forest Green
                "light_bg": "#DCFCE7",  # Light Mint Green
            },
            {
                "name": "Cattle Feed Subsidy",
                "code": "CATTLEFEED",
                "qty": f"{cattle_kg} KG",
                "color": "#B45309",     # Amber / Gold
                "light_bg": "#FEF3C7",  # Light Amber
            },
            {
                "name": "Mineral Mixture Subsidy",
                "code": "MINERALS",
                "qty": f"{mineral_kg} KG",
                "color": "#0369A1",     # Deep Ocean Blue
                "light_bg": "#E0F2FE",  # Light Sky Blue
            }
        ]
        
        coupon_w = page_w - 48 # 564 pt
        coupon_h = 224 # 224 pt
        start_y = page_h - 58 - coupon_h
        y_gap = 14
        
        for p_idx, prod in enumerate(products):
            cur_y = start_y - (p_idx * (coupon_h + y_gap))
            _draw_coupon_ticket(c, 24, cur_y, coupon_w, coupon_h, beneficiary_data, prod, month)
            
        # Footer
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.HexColor("#64748B"))
        c.drawCentredString(page_w / 2, 12, f"Coupon Book Page {month} of 12 • 36 Total Monthly Product Coupons • 360 Parenting POD Gateway")
        
        c.showPage()

async def generate_qr_pdf(beneficiary_data: dict) -> str:
    """Generates a complete 36-coupon booklet PDF (12 months x 3 products) for a single beneficiary."""
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_pdf_path = temp_pdf.name
    temp_pdf.close()
    
    c = canvas.Canvas(temp_pdf_path, pagesize=letter)
    _render_beneficiary_coupon_pages(c, beneficiary_data)
    c.save()
    return temp_pdf_path

async def generate_all_qrs_pdf(beneficiaries: list) -> str:
    """Generates a multi-page PDF containing 36 coupons for each beneficiary in the list."""
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_pdf_path = temp_pdf.name
    temp_pdf.close()
    
    c = canvas.Canvas(temp_pdf_path, pagesize=letter)
    for beneficiary_data in beneficiaries:
        _render_beneficiary_coupon_pages(c, beneficiary_data)
    c.save()
    return temp_pdf_path
