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
    
    # Auto-fit product name on stub
    stub_prod_title = prod_name.upper()
    stub_font_size = 10.5
    while stub_font_size > 7.0 and c.stringWidth(stub_prod_title, "Helvetica-Bold", stub_font_size) > (stub_w - 24):
        stub_font_size -= 0.5
    c.setFont("Helvetica-Bold", stub_font_size)
    c.setFillColor(theme_color)
    c.drawString(x + 12, y + h - 56, stub_prod_title)
    
    c.setFont("Helvetica-Bold", 11)
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
    
    # Top Header: "360 PARENTING POD • SUBSIDY COUPON" & Month Validity Pill
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
    
    # Product Title on Left
    main_prod_title = prod_name.upper()
    main_font_size = 14.0
    while main_font_size > 9.0 and c.stringWidth(main_prod_title, "Helvetica-Bold", main_font_size) > 230:
        main_font_size -= 0.5
    c.setFillColor(theme_color)
    c.setFont("Helvetica-Bold", main_font_size)
    c.drawString(main_x, y + h - 54, main_prod_title)
    
    # Quantity Pill Badge (Right-aligned, preventing any overlap with product name)
    qty_text = f"QTY: {prod_qty}"
    c.setFont("Helvetica-Bold", 10.5)
    qty_str_w = c.stringWidth(qty_text, "Helvetica-Bold", 10.5)
    qty_badge_w = qty_str_w + 16
    qty_badge_h = 18
    qty_badge_x = x + w - qty_badge_w - 14
    qty_badge_y = y + h - 58
    
    c.setFillColor(colors.HexColor(product_info['light_bg']))
    c.setStrokeColor(theme_color)
    c.setLineWidth(1)
    c.roundRect(qty_badge_x, qty_badge_y, qty_badge_w, qty_badge_h, 4, fill=1, stroke=1)
    
    c.setFillColor(theme_color)
    c.drawCentredString(qty_badge_x + (qty_badge_w / 2), qty_badge_y + 5, qty_text)
    
    # Left Info Box for Beneficiary Details
    info_y = y + h - 68
    box_w = 235
    c.setFillColor(colors.HexColor("#f1f5f9"))
    c.roundRect(main_x, y + 14, box_w, info_y - (y + 14), 6, fill=1, stroke=0)
    
    def fit_text(txt: str, font: str, sz: float, max_w: float) -> str:
        if c.stringWidth(txt, font, sz) <= max_w:
            return txt
        while len(txt) > 3 and c.stringWidth(txt + "..", font, sz) > max_w:
            txt = txt[:-1]
        return txt + ".."
    
    val_max_w = box_w - 95 - 8
    
    # Details rows
    row_y = info_y - 14
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(sub_text)
    c.drawString(main_x + 10, row_y, "Beneficiary Name:")
    c.setFont("Helvetica-Bold", 9.5)
    c.setFillColor(dark_text)
    c.drawString(main_x + 95, row_y, fit_text(farmer_name, "Helvetica-Bold", 9.5, val_max_w))
    
    row_y -= 16
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(sub_text)
    c.drawString(main_x + 10, row_y, "Father/Husband:")
    c.setFont("Helvetica", 9)
    c.setFillColor(dark_text)
    c.drawString(main_x + 95, row_y, fit_text(father_husband, "Helvetica", 9, val_max_w))
    
    row_y -= 16
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(sub_text)
    c.drawString(main_x + 10, row_y, "Village & District:")
    c.setFont("Helvetica", 9)
    c.setFillColor(dark_text)
    c.drawString(main_x + 95, row_y, fit_text(f"{village}, {district}", "Helvetica", 9, val_max_w))
    
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
    c.drawString(main_x + 10, row_y, "Note: Present coupon to supervisor upon monthly delivery.")
    
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

# Try registering Nirmala fonts for Hindi script support if available
FONT_HINDI_BOLD = "Helvetica-Bold"
FONT_HINDI_REG = "Helvetica"
try:
    nirmala_path = r"C:\Windows\Fonts\Nirmala.ttc"
    if os.path.exists(nirmala_path):
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        pdfmetrics.registerFont(TTFont('Nirmala', nirmala_path, subfontIndex=0))
        pdfmetrics.registerFont(TTFont('Nirmala-Bold', nirmala_path, subfontIndex=1))
        FONT_HINDI_BOLD = 'Nirmala-Bold'
        FONT_HINDI_REG = 'Nirmala'
except Exception:
    pass

def _draw_cover_page(c: canvas.Canvas, beneficiary: dict):
    """
    Renders Page 1: Premium Booklet Cover matching the user design:
    - Top Maroon Header Bar: 'सब्सिडी वितरण / Subsidy Distribution'
    - Left Maroon Spine with stitch/dashed line
    - Large Title: 'सब्सिडी वितरण'
    - Subtitle: '12 MONTHS • 3 PRODUCTS/MONTH • 36 TEARABLE COUPONS'
    - Central Illustration: Rural farming & dairy cattle illustration
    - Bottom Left: 'My Animal' branding & 'Leading the Animal Tech Revolution'
    - Right: Master Booklet QR Code with beneficiary verification details
    """
    page_w, page_h = letter # 612 x 792 pt
    tag_no = str(beneficiary.get('tag_no', 'UNKNOWN'))
    farmer_name = str(beneficiary.get('farmer_name', 'Beneficiary Name'))
    village = str(beneficiary.get('village', '-'))
    district = str(beneficiary.get('district', '-'))
    
    maroon_color = colors.HexColor("#5c1421")
    dark_slate = colors.HexColor("#0f172a")
    sub_slate = colors.HexColor("#475569")
    
    # 1. Background base
    c.setFillColor(colors.HexColor("#FDFBF7"))
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)
    
    # 2. Top Maroon Header Bar
    c.setFillColor(maroon_color)
    c.rect(0, page_h - 44, page_w, 44, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont(FONT_HINDI_BOLD, 15)
    c.drawCentredString(page_w / 2, page_h - 28, "सब्सिडी वितरण / Subsidy Distribution")
    
    # 3. Left Spine Binding Accent
    spine_w = 26
    c.setFillColor(maroon_color)
    c.rect(0, 0, spine_w, page_h - 44, fill=1, stroke=0)
    
    # Perforated/stitch dashed line along spine
    c.saveState()
    c.setStrokeColor(colors.HexColor("#94a3b8"))
    c.setLineWidth(1)
    c.setDash([3, 3])
    c.line(spine_w + 6, 28, spine_w + 6, page_h - 52)
    c.restoreState()
    
    # 4. Main Cover Content Area
    content_x = spine_w + 16
    
    # Main Hindi Title
    c.setFillColor(maroon_color)
    c.setFont(FONT_HINDI_BOLD, 32)
    c.drawString(content_x, page_h - 96, "सब्सिडी वितरण")
    
    # Sub-headline
    c.setFillColor(dark_slate)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(content_x, page_h - 120, "12 MONTHS • 3 PRODUCTS/MONTH • 36 TEARABLE COUPONS")
    
    # Subtle separator line below header
    c.setStrokeColor(colors.HexColor("#e2e8f0"))
    c.setLineWidth(1)
    c.line(content_x, page_h - 132, page_w - 20, page_h - 132)
    
    # 5. Middle Layout: Illustration (Left/Center) & Master QR (Right)
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    cover_img_path = os.path.join(assets_dir, "cover_illustration.jpg")
    
    img_x = content_x
    img_y = 230
    img_w = 345
    img_h = 390
    
    # Draw container box for illustration
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor("#e2e8f0"))
    c.setLineWidth(1)
    c.roundRect(img_x, img_y, img_w, img_h, 8, fill=1, stroke=1)
    
    if os.path.exists(cover_img_path):
        try:
            # Draw illustration neatly clipped inside rounded card
            c.saveState()
            c.drawImage(cover_img_path, img_x + 4, img_y + 4, width=img_w - 8, height=img_h - 8, preserveAspectRatio=True)
            c.restoreState()
        except Exception as e:
            print(f"Failed to render cover illustration: {e}")
            
    # 6. Right Side Master QR Code Container
    qr_card_x = img_x + img_w + 12
    qr_card_y = 230
    qr_card_w = page_w - qr_card_x - 20 # ~175 pt
    qr_card_h = 390
    
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setLineWidth(1)
    c.roundRect(qr_card_x, qr_card_y, qr_card_w, qr_card_h, 8, fill=1, stroke=1)
    
    # Master QR Banner Header
    c.setFillColor(maroon_color)
    c.roundRect(qr_card_x + 8, qr_card_y + qr_card_h - 28, qr_card_w - 16, 20, 4, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(qr_card_x + (qr_card_w / 2), qr_card_y + qr_card_h - 22, "BOOKLET MASTER QR")
    
    # Generate Master QR code buffer
    master_qr_data = f"360POD-BOOKLET-TAG{tag_no}"
    master_qr_buf = _make_qr_buffer(master_qr_data)
    master_qr_img = ImageReader(master_qr_buf)
    
    qr_size = 135
    qr_pos_x = qr_card_x + (qr_card_w - qr_size) / 2
    qr_pos_y = qr_card_y + 200
    
    # White background container with outline for QR
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.HexColor("#e2e8f0"))
    c.setLineWidth(0.8)
    c.roundRect(qr_pos_x - 4, qr_pos_y - 4, qr_size + 8, qr_size + 8, 4, fill=1, stroke=1)
    c.drawImage(master_qr_img, qr_pos_x, qr_pos_y, width=qr_size, height=qr_size)
    
    # Scan verification label
    c.setFont("Helvetica-Bold", 7.5)
    c.setFillColor(maroon_color)
    c.drawCentredString(qr_card_x + (qr_card_w / 2), qr_pos_y - 14, "SCAN TO VERIFY BOOKLET")
    
    c.setFont("Helvetica", 6.5)
    c.setFillColor(sub_slate)
    c.drawCentredString(qr_card_x + (qr_card_w / 2), qr_pos_y - 24, master_qr_data)
    
    # Beneficiary Summary Badge inside right card
    info_box_y = qr_card_y + 12
    info_box_h = 135
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.setStrokeColor(colors.HexColor("#E2E8F0"))
    c.setLineWidth(0.8)
    c.roundRect(qr_card_x + 8, info_box_y, qr_card_w - 16, info_box_h, 6, fill=1, stroke=1)
    
    # Beneficiary quick metadata
    c.setFillColor(maroon_color)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(qr_card_x + 14, info_box_y + info_box_h - 16, "BENEFICIARY:")
    
    c.setFillColor(dark_slate)
    c.setFont("Helvetica-Bold", 9)
    farmer_disp = (farmer_name[:18] + '..') if len(farmer_name) > 18 else farmer_name
    c.drawString(qr_card_x + 14, info_box_y + info_box_h - 30, farmer_disp)
    
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(sub_slate)
    c.drawString(qr_card_x + 14, info_box_y + info_box_h - 46, "TAG NUMBER:")
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(colors.HexColor("#0369a1"))
    c.drawString(qr_card_x + 14, info_box_y + info_box_h - 58, f"#{tag_no}")
    
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(sub_slate)
    c.drawString(qr_card_x + 14, info_box_y + info_box_h - 74, "LOCATION:")
    c.setFont("Helvetica", 8)
    c.setFillColor(dark_slate)
    loc_str = f"{village}, {district}"
    loc_disp = (loc_str[:18] + '..') if len(loc_str) > 18 else loc_str
    c.drawString(qr_card_x + 14, info_box_y + info_box_h - 86, loc_disp)
    
    # Green enrollment status pill
    status_pill_w = qr_card_w - 32
    c.setFillColor(colors.HexColor("#DCFCE7"))
    c.roundRect(qr_card_x + 16, info_box_y + 10, status_pill_w, 18, 4, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#15803D"))
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(qr_card_x + 16 + (status_pill_w / 2), info_box_y + 15, "ACTIVE ENROLLMENT")
    
    # 7. Bottom Branding & Footer Section
    # "My Animal" Logo
    my_animal_y = 135
    c.setFont("Helvetica-Bold", 26)
    c.setFillColor(colors.HexColor("#0284C7")) # Blue
    c.drawString(content_x, my_animal_y, "My ")
    
    c.setFillColor(colors.HexColor("#16A34A")) # Green
    c.drawString(content_x + 44, my_animal_y, "Animal")
    
    # Subtitle
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(colors.HexColor("#475569"))
    c.drawString(content_x, my_animal_y - 15, "Leading the Animal Tech Revolution")
    
    # Project subtitle badge
    c.setFillColor(colors.HexColor("#F1F5F9"))
    c.roundRect(content_x, my_animal_y - 42, 345, 20, 4, fill=1, stroke=0)
    c.setFillColor(maroon_color)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(content_x + 8, my_animal_y - 35, "360 PARENTING POD • CATTLE WELFARE & SUBSIDY PROGRAM")
    
    # Right-side Official Stamp Box on Cover
    stamp_x = qr_card_x
    stamp_y = 75
    stamp_w = qr_card_w
    stamp_h = 130
    c.setFillColor(colors.HexColor("#FAFAFA"))
    c.setStrokeColor(colors.HexColor("#E2E8F0"))
    c.setLineWidth(1)
    c.roundRect(stamp_x, stamp_y, stamp_w, stamp_h, 6, fill=1, stroke=1)
    
    c.setFillColor(dark_slate)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(stamp_x + (stamp_w / 2), stamp_y + stamp_h - 16, "AUTHORIZATION")
    
    c.setFont("Helvetica", 7.5)
    c.setFillColor(sub_slate)
    c.drawCentredString(stamp_x + (stamp_w / 2), stamp_y + stamp_h - 32, "Verified & Issued by")
    c.drawCentredString(stamp_x + (stamp_w / 2), stamp_y + stamp_h - 44, "360 Parenting POD Gateway")
    
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(0.8)
    c.setDash([2, 2])
    c.line(stamp_x + 12, stamp_y + 35, stamp_x + stamp_w - 12, stamp_y + 35)
    c.setDash([])
    
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(sub_slate)
    c.drawCentredString(stamp_x + (stamp_w / 2), stamp_y + 20, "OFFICIAL STAMP / SIGN")
    
    # Bottom Maroon Footer Bar
    c.setFillColor(maroon_color)
    c.rect(0, 0, page_w, 28, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 8)
    c.drawCentredString(page_w / 2, 10, "An Initiative by My Animal & 360 Parenting POD • Valid for 12 Consecutive Delivery Cycles")
    
    c.showPage()

def _draw_beneficiary_details_page(c: canvas.Canvas, beneficiary_data: dict):
    """
    Renders Page 2: Dedicated Beneficiary Enrollment Certificate & Subsidy Entitlement Breakdown.
    - Header: '360 PARENTING POD • BENEFICIARY ENROLLMENT CERTIFICATE'
    - Card 1: Beneficiary Profile & Livestock Information
    - Card 2: 12-Month Subsidy Allocation Breakdown Table (Silage, Cattle Feed, Mineral Mixture)
    - Card 3: Instructions & Coupon Redemption Rules
    - Card 4: Official Signatures & Verification Stamp
    """
    page_w, page_h = letter # 612 x 792 pt
    tag_no = str(beneficiary_data.get('tag_no', 'UNKNOWN'))
    farmer_name = str(beneficiary_data.get('farmer_name', 'Beneficiary Name'))
    father_husband = str(beneficiary_data.get('father_husband_name', '-'))
    village = str(beneficiary_data.get('village', '-'))
    district = str(beneficiary_data.get('district', '-'))
    state = str(beneficiary_data.get('state', 'Chhattisgarh'))
    
    silage_kg = beneficiary_data.get('silage_kg') or 50
    cattle_kg = beneficiary_data.get('cattle_feed_kg') or 25
    mineral_kg = beneficiary_data.get('mineral_mixture_kg') or 5
    
    total_monthly_kg = silage_kg + cattle_kg + mineral_kg
    total_annual_kg = total_monthly_kg * 12
    
    dark_navy = colors.HexColor("#0F172A")
    sub_slate = colors.HexColor("#475569")
    text_dark = colors.HexColor("#1E293B")
    border_slate = colors.HexColor("#E2E8F0")
    
    # 1. Top Header Banner
    c.setFillColor(dark_navy)
    c.rect(0, page_h - 52, page_w, 52, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(28, page_h - 26, "360 PARENTING POD • BENEFICIARY ENROLLMENT CERTIFICATE")
    
    c.setFont("Helvetica", 8.5)
    c.setFillColor(colors.HexColor("#94A3B8"))
    c.drawString(28, page_h - 42, "Official record of farmer enrollment, cattle subsidy quotas, and monthly redemption guidelines")
    
    # Active Status Pill
    status_w = 120
    status_h = 22
    status_x = page_w - status_w - 28
    status_y = page_h - 38
    c.setFillColor(colors.HexColor("#15803D"))
    c.roundRect(status_x, status_y, status_w, status_h, 5, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(status_x + (status_w / 2), status_y + 7, "VERIFIED & ACTIVE")
    
    margin_x = 28
    card_w = page_w - (margin_x * 2) # 556 pt
    
    # ==================== CARD 1: BENEFICIARY PROFILE ====================
    card1_y = page_h - 195
    card1_h = 130
    
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.setStrokeColor(border_slate)
    c.setLineWidth(1)
    c.roundRect(margin_x, card1_y, card_w, card1_h, 8, fill=1, stroke=1)
    
    # Card 1 Header Strip
    c.setFillColor(colors.HexColor("#1E293B"))
    c.roundRect(margin_x, card1_y + card1_h - 24, card_w, 24, 6, fill=1, stroke=0)
    c.rect(margin_x, card1_y + card1_h - 24, card_w, 8, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(margin_x + 14, card1_y + card1_h - 16, "1. BENEFICIARY & LIVESTOCK PROFILE")
    
    # Column 1 (Left)
    col1_x = margin_x + 16
    row1_y = card1_y + card1_h - 45
    
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(sub_slate)
    c.drawString(col1_x, row1_y, "Beneficiary Name:")
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(text_dark)
    c.drawString(col1_x + 115, row1_y, farmer_name)
    
    row1_y -= 22
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(sub_slate)
    c.drawString(col1_x, row1_y, "Father / Husband:")
    c.setFont("Helvetica", 10)
    c.setFillColor(text_dark)
    c.drawString(col1_x + 115, row1_y, father_husband)
    
    row1_y -= 22
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(sub_slate)
    c.drawString(col1_x, row1_y, "Village & District:")
    c.setFont("Helvetica", 10)
    c.setFillColor(text_dark)
    c.drawString(col1_x + 115, row1_y, f"{village}, {district} ({state})")
    
    # Column 2 (Right)
    col2_x = margin_x + 290
    row2_y = card1_y + card1_h - 45
    
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(sub_slate)
    c.drawString(col2_x, row2_y, "Cattle Ear Tag No:")
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#0369A1"))
    c.drawString(col2_x + 115, row2_y, f"#{tag_no}")
    
    row2_y -= 22
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(sub_slate)
    c.drawString(col2_x, row2_y, "Enrollment Period:")
    c.setFont("Helvetica-Bold", 9.5)
    c.setFillColor(text_dark)
    c.drawString(col2_x + 115, row2_y, "12 Months (36 Total Vouchers)")
    
    row2_y -= 22
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(sub_slate)
    c.drawString(col2_x, row2_y, "Program Gateway:")
    c.setFont("Helvetica", 9.5)
    c.setFillColor(text_dark)
    c.drawString(col2_x + 115, row2_y, "360 Parenting POD System")
    
    # ==================== CARD 2: SUBSIDY ENTITLEMENT TABLE ====================
    card2_y = card1_y - 175
    card2_h = 162
    
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.setStrokeColor(border_slate)
    c.setLineWidth(1)
    c.roundRect(margin_x, card2_y, card_w, card2_h, 8, fill=1, stroke=1)
    
    # Card 2 Header Strip
    c.setFillColor(colors.HexColor("#1E293B"))
    c.roundRect(margin_x, card2_y + card2_h - 24, card_w, 24, 6, fill=1, stroke=0)
    c.rect(margin_x, card2_y + card2_h - 24, card_w, 8, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(margin_x + 14, card2_y + card2_h - 16, "2. SUBSIDY ENTITLEMENT & ANNUAL QUOTA BREAKDOWN")
    
    # Table Column Headers
    tbl_hdr_y = card2_y + card2_h - 44
    c.setFillColor(colors.HexColor("#E2E8F0"))
    c.rect(margin_x + 10, tbl_hdr_y, card_w - 20, 18, fill=1, stroke=0)
    
    c.setFillColor(dark_navy)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(margin_x + 16, tbl_hdr_y + 5, "SUBSIDY PRODUCT")
    c.drawString(margin_x + 160, tbl_hdr_y + 5, "MONTHLY QUOTA")
    c.drawString(margin_x + 280, tbl_hdr_y + 5, "ANNUAL TOTAL (12 MOS)")
    c.drawString(margin_x + 420, tbl_hdr_y + 5, "CATEGORY / BENEFIT")
    
    # Rows Data
    rows = [
        ("Silage Subsidy", f"{silage_kg} KG / Month", f"{silage_kg * 12} KG Total", "Green Roughage & Milk Yield", "#15803D", "#DCFCE7"),
        ("Cattle Feed Subsidy", f"{cattle_kg} KG / Month", f"{cattle_kg * 12} KG Total", "Balanced Protein Feed", "#B45309", "#FEF3C7"),
        ("Mineral Mixture Subsidy", f"{mineral_kg} KG / Month", f"{mineral_kg * 12} KG Total", "Micronutrients & Immunity", "#0369A1", "#E0F2FE")
    ]
    
    cur_tbl_y = tbl_hdr_y - 24
    for prod_name, mo_quota, yr_quota, purpose, p_color, bg_pill in rows:
        c.setFillColor(colors.HexColor(p_color))
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin_x + 16, cur_tbl_y + 3, prod_name)
        
        # Monthly Quota Pill
        c.setFillColor(colors.HexColor(bg_pill))
        c.roundRect(margin_x + 158, cur_tbl_y, 90, 16, 3, fill=1, stroke=0)
        c.setFillColor(colors.HexColor(p_color))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawCentredString(margin_x + 203, cur_tbl_y + 4, mo_quota)
        
        c.setFillColor(text_dark)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin_x + 280, cur_tbl_y + 3, yr_quota)
        
        c.setFont("Helvetica", 8.5)
        c.setFillColor(sub_slate)
        c.drawString(margin_x + 420, cur_tbl_y + 3, purpose)
        
        # Row divider
        c.setStrokeColor(border_slate)
        c.setLineWidth(0.6)
        c.line(margin_x + 10, cur_tbl_y - 4, margin_x + card_w - 10, cur_tbl_y - 4)
        cur_tbl_y -= 23
        
    # Total Summary Bar
    summary_y = card2_y + 8
    c.setFillColor(colors.HexColor("#0F172A"))
    c.roundRect(margin_x + 10, summary_y, card_w - 20, 20, 4, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(margin_x + 20, summary_y + 6, f"TOTAL ALLOCATION:  {total_monthly_kg} KG per Month")
    c.drawRightString(margin_x + card_w - 20, summary_y + 6, f"GRAND TOTAL:  {total_annual_kg} KG across 36 Coupons")
    
    # ==================== CARD 3: GUIDELINES & REDEMPTION PROCESS ====================
    card3_y = card2_y - 145
    card3_h = 132
    
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.setStrokeColor(border_slate)
    c.setLineWidth(1)
    c.roundRect(margin_x, card3_y, card_w, card3_h, 8, fill=1, stroke=1)
    
    # Card 3 Header Strip
    c.setFillColor(colors.HexColor("#1E293B"))
    c.roundRect(margin_x, card3_y + card3_h - 24, card_w, 24, 6, fill=1, stroke=0)
    c.rect(margin_x, card3_y + card3_h - 24, card_w, 8, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(margin_x + 14, card3_y + card3_h - 16, "3. IMPORTANT GUIDELINES & COUPON REDEMPTION INSTRUCTIONS")
    
    instructions = [
        "1. Monthly Handover: Present the designated month's coupon to the authorized supervisor upon monthly supply delivery.",
        "2. Perforated Stub: The supervisor will retain the left vendor copy and leave the verified right voucher with the farmer.",
        "3. QR Verification: Ensure the supervisor scans the unique coupon QR code to record geo-tagged proof of delivery.",
        "4. Non-Transferable: Coupons are valid strictly for cattle tag #" + tag_no + " and cannot be exchanged or transferred."
    ]
    
    inst_y = card3_y + card3_h - 42
    for inst in instructions:
        c.setFillColor(dark_navy)
        c.setFont("Helvetica", 8.5)
        c.drawString(margin_x + 16, inst_y, inst)
        inst_y -= 19
        
    # ==================== CARD 4: SIGNATURES & VERIFICATION ====================
    card4_y = card3_y - 110
    card4_h = 98
    
    c.setFillColor(colors.HexColor("#FFFFFF"))
    c.setStrokeColor(border_slate)
    c.setLineWidth(1)
    c.roundRect(margin_x, card4_y, card_w, card4_h, 8, fill=1, stroke=1)
    
    col_w = (card_w - 40) / 3 # ~172 pt
    
    # Box 1: Beneficiary Sign
    box1_x = margin_x + 10
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setDash([2, 2])
    c.line(box1_x + 10, card4_y + 35, box1_x + col_w - 10, card4_y + 35)
    c.setDash([])
    c.setFillColor(text_dark)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(box1_x + (col_w / 2), card4_y + 20, "Beneficiary Signature / Thumbprint")
    c.setFont("Helvetica", 7)
    c.setFillColor(sub_slate)
    c.drawCentredString(box1_x + (col_w / 2), card4_y + 10, f"Farmer: {farmer_name}")
    
    # Box 2: Supervisor Sign
    box2_x = box1_x + col_w + 10
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setDash([2, 2])
    c.line(box2_x + 10, card4_y + 35, box2_x + col_w - 10, card4_y + 35)
    c.setDash([])
    c.setFillColor(text_dark)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(box2_x + (col_w / 2), card4_y + 20, "Authorized Supervisor Signature")
    c.setFont("Helvetica", 7)
    c.setFillColor(sub_slate)
    c.drawCentredString(box2_x + (col_w / 2), card4_y + 10, "360 Parenting POD Field Partner")
    
    # Box 3: Official Stamp
    box3_x = box2_x + col_w + 10
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setDash([2, 2])
    c.line(box3_x + 10, card4_y + 35, box3_x + col_w - 10, card4_y + 35)
    c.setDash([])
    c.setFillColor(text_dark)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(box3_x + (col_w / 2), card4_y + 20, "Official POD Seal & Stamp")
    c.setFont("Helvetica", 7)
    c.setFillColor(sub_slate)
    c.drawCentredString(box3_x + (col_w / 2), card4_y + 10, "Registration Gateway Verification")
    
    # Bottom Footer
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#64748B"))
    c.drawCentredString(page_w / 2, 14, "Page 2 of 14 • Beneficiary Enrollment & Subsidy Record • 360 Parenting POD Gateway")
    
    c.showPage()

def _render_beneficiary_coupon_pages(c: canvas.Canvas, beneficiary_data: dict):
    """
    Renders the complete 14-page beneficiary subsidy booklet:
    - Page 1: Premium Booklet Cover Page
    - Page 2: Dedicated Beneficiary Details & Subsidy Certificate Page
    - Pages 3 to 14: 12 Monthly Coupon Pages (3 coupons per page = 36 total coupons)
    """
    # 1. Render Cover Page (Page 1)
    _draw_cover_page(c, beneficiary_data)
    
    # 2. Render Dedicated Beneficiary Details Page (Page 2)
    _draw_beneficiary_details_page(c, beneficiary_data)
    
    # 3. Render 12 Monthly Coupon Pages (Pages 3 to 14)
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
                "name": "Silage",
                "code": "SILAGE",
                "qty": f"{silage_kg} KG",
                "color": "#15803D",     # Forest Green
                "light_bg": "#DCFCE7",  # Light Mint Green
            },
            {
                "name": "Cattle Feed",
                "code": "CATTLEFEED",
                "qty": f"{cattle_kg} KG",
                "color": "#B45309",     # Amber / Gold
                "light_bg": "#FEF3C7",  # Light Amber
            },
            {
                "name": "Mineral Mixture",
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
        c.drawCentredString(page_w / 2, 12, f"Coupon Book Month {month} of 12 • Page {month + 2} of 14 • 36 Total Coupons • 360 Parenting POD Gateway")
        
        c.showPage()

async def generate_qr_pdf(beneficiary_data: dict) -> str:
    """Generates a complete 14-page booklet PDF (Cover + Beneficiary Details + 12 Monthly Pages) for a beneficiary."""
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_pdf_path = temp_pdf.name
    temp_pdf.close()
    
    c = canvas.Canvas(temp_pdf_path, pagesize=letter)
    _render_beneficiary_coupon_pages(c, beneficiary_data)
    c.save()
    return temp_pdf_path

async def generate_all_qrs_pdf(beneficiaries: list) -> str:
    """Generates a multi-booklet PDF containing all pages for each beneficiary in the list."""
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_pdf_path = temp_pdf.name
    temp_pdf.close()
    
    c = canvas.Canvas(temp_pdf_path, pagesize=letter)
    for beneficiary_data in beneficiaries:
        _render_beneficiary_coupon_pages(c, beneficiary_data)
    c.save()
    return temp_pdf_path
