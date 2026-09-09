import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import qrcode
from io import BytesIO

def make_qr_buffer(data_str: str) -> BytesIO:
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

def test_render():
    beneficiary = {
        "tag_no": "62313",
        "farmer_name": "Rameshwar Patel",
        "father_husband_name": "Shyamlal Patel",
        "village": "Mahasamund",
        "district": "Mahasamund",
        "cattle_feed_kg": 25,
        "silage_kg": 50,
        "mineral_mixture_kg": 5,
    }
    
    pdf_path = os.path.join(os.path.dirname(__file__), "test_overlap_fix.pdf")
    c = canvas.Canvas(pdf_path, pagesize=letter)
    page_w, page_h = letter
    
    # Test products
    products = [
        {"name": "Silage", "code": "SILAGE", "qty": "50 KG", "color": "#15803D", "light_bg": "#DCFCE7"},
        {"name": "Cattle Feed", "code": "CATTLEFEED", "qty": "25 KG", "color": "#B45309", "light_bg": "#FEF3C7"},
        {"name": "Mineral Mixture", "code": "MINERALS", "qty": "5 KG", "color": "#0369A1", "light_bg": "#E0F2FE"},
    ]
    
    for month in range(1, 2):
        c.setFillColor(colors.HexColor("#0F172A"))
        c.rect(0, page_h - 45, page_w, 45, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 13)
        c.drawString(24, page_h - 26, f"360 PARENTING COUPON BOOK • MONTH {month} OF 12")
        
        coupon_w = page_w - 48
        coupon_h = 224
        start_y = page_h - 58 - coupon_h
        y_gap = 14
        
        for p_idx, prod in enumerate(products):
            cur_y = start_y - (p_idx * (coupon_h + y_gap))
            
            x = 24
            y = cur_y
            w = coupon_w
            h = coupon_h
            
            tag_no = str(beneficiary.get('tag_no', 'UNKNOWN'))
            farmer_name = str(beneficiary.get('farmer_name', 'Beneficiary Name'))
            father_husband = str(beneficiary.get('father_husband_name', '-'))
            village = str(beneficiary.get('village', '-'))
            district = str(beneficiary.get('district', '-'))
            
            prod_name = prod['name']
            prod_code = prod['code']
            prod_qty = prod['qty']
            theme_color = colors.HexColor(prod['color'])
            dark_text = colors.HexColor("#0f172a")
            sub_text = colors.HexColor("#475569")
            
            qr_data = f"{tag_no}-M{month}-{prod_code}"
            qr_buf = make_qr_buffer(qr_data)
            qr_img = ImageReader(qr_buf)
            
            # Outer card
            c.saveState()
            c.setFillColor(colors.HexColor("#F8FAFC"))
            c.setStrokeColor(theme_color)
            c.setLineWidth(1.5)
            c.roundRect(x, y, w, h, 10, fill=1, stroke=1)
            
            stub_w = 165
            divider_x = x + stub_w
            
            c.setFillColor(colors.HexColor(prod['light_bg']))
            c.rect(x + 1, y + 1, stub_w - 1, h - 2, fill=1, stroke=0)
            c.restoreState()
            
            c.saveState()
            c.setStrokeColor(theme_color)
            c.setLineWidth(1.5)
            c.roundRect(x, y, w, h, 10, fill=0, stroke=1)
            c.restoreState()
            
            # Divider
            c.saveState()
            c.setStrokeColor(colors.HexColor("#94a3b8"))
            c.setLineWidth(1)
            c.setDash([3, 3])
            c.line(divider_x, y + 12, divider_x, y + h - 12)
            c.setDash([])
            
            notch_radius = 8
            c.setFillColor(colors.white)
            c.setStrokeColor(theme_color)
            c.setLineWidth(1.2)
            c.circle(divider_x, y + h, notch_radius, fill=1, stroke=1)
            c.circle(divider_x, y, notch_radius, fill=1, stroke=1)
            c.restoreState()
            
            # Left stub
            c.setFillColor(theme_color)
            c.roundRect(x + 10, y + h - 26, stub_w - 20, 18, 4, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(x + (stub_w / 2), y + h - 22, "VENDOR COPY")
            
            c.setFillColor(dark_text)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x + 12, y + h - 42, f"MONTH {month} ONLY")
            
            c.setFont("Helvetica-Bold", 10.5)
            c.setFillColor(theme_color)
            c.drawString(x + 12, y + h - 56, prod_name.upper())
            
            c.setFont("Helvetica-Bold", 11)
            c.setFillColor(dark_text)
            c.drawString(x + 12, y + h - 70, f"QTY: {prod_qty}")
            
            c.setFont("Helvetica", 8)
            c.setFillColor(sub_text)
            farmer_disp = (farmer_name[:16] + '..') if len(farmer_name) > 16 else farmer_name
            c.drawString(x + 12, y + h - 83, f"Farmer: {farmer_disp}")
            c.drawString(x + 12, y + h - 94, f"Tag #{tag_no}")
            
            stub_qr_size = 72
            stub_qr_x = x + (stub_w - stub_qr_size) / 2
            stub_qr_y = y + 18
            
            c.setFillColor(colors.white)
            c.setStrokeColor(colors.HexColor("#cbd5e1"))
            c.setLineWidth(0.8)
            c.roundRect(stub_qr_x - 4, stub_qr_y - 4, stub_qr_size + 8, stub_qr_size + 8, 4, fill=1, stroke=1)
            c.drawImage(qr_img, stub_qr_x, stub_qr_y, width=stub_qr_size, height=stub_qr_size)
            
            c.setFont("Helvetica", 6.5)
            c.setFillColor(sub_text)
            c.drawCentredString(x + (stub_w / 2), y + 6, qr_data)
            
            # Right voucher
            main_x = divider_x + 15
            
            c.setFillColor(theme_color)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(main_x, y + h - 24, "360 PARENTING POD • SUBSIDY COUPON")
            
            badge_w = 128
            badge_h = 20
            badge_x = x + w - badge_w - 12
            badge_y = y + h - 28
            c.setFillColor(theme_color)
            c.roundRect(badge_x, badge_y, badge_w, badge_h, 5, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont("Helvetica-Bold", 8.5)
            c.drawCentredString(badge_x + (badge_w / 2), badge_y + 6, f"VALID FOR MONTH {month} ONLY")
            
            c.setStrokeColor(colors.HexColor("#e2e8f0"))
            c.setLineWidth(1)
            c.line(main_x, y + h - 34, x + w - 12, y + h - 34)
            
            # Dynamic text width check to ensure NO overlap
            main_qr_size = 90
            main_qr_x = x + w - main_qr_size - 18
            main_qr_y = y + 26
            
            # Product Title on Left
            c.setFillColor(theme_color)
            c.setFont("Helvetica-Bold", 14)
            c.drawString(main_x, y + h - 54, prod_name.upper())
            
            # Quantity Callout Badge / Right Aligned before QR
            qty_text = f"QTY: {prod_qty}"
            c.setFont("Helvetica-Bold", 13)
            qty_w = c.stringWidth(qty_text, "Helvetica-Bold", 13)
            qty_badge_x = main_qr_x - qty_w - 18
            
            c.setFillColor(dark_text)
            c.drawString(qty_badge_x, y + h - 54, qty_text)
            
            # Left Info Box for Beneficiary Details
            info_y = y + h - 68
            c.setFillColor(colors.HexColor("#f1f5f9"))
            c.roundRect(main_x, y + 14, 235, info_y - (y + 14), 6, fill=1, stroke=0)
            
            row_y = info_y - 14
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
            c.drawString(main_x + 10, row_y, "Note: Present coupon to supervisor upon monthly delivery.")
            
            # Right QR
            c.setFillColor(colors.white)
            c.setStrokeColor(colors.HexColor("#cbd5e1"))
            c.setLineWidth(0.8)
            c.roundRect(main_qr_x - 5, main_qr_y - 5, main_qr_size + 10, main_qr_size + 10, 6, fill=1, stroke=1)
            c.drawImage(qr_img, main_qr_x, main_qr_y, width=main_qr_size, height=main_qr_size)
            
            c.setFont("Helvetica-Bold", 7)
            c.setFillColor(theme_color)
            c.drawCentredString(main_qr_x + (main_qr_size / 2), y + 14, "SCAN TO VERIFY")
            
            c.setFont("Helvetica", 6.5)
            c.setFillColor(sub_text)
            c.drawCentredString(main_qr_x + (main_qr_size / 2), y + 4, qr_data)
            
    c.save()
    print("Overlap fix test rendered successfully at:", pdf_path)

if __name__ == "__main__":
    test_render()
