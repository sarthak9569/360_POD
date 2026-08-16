import qrcode
import os

# Create directory if it doesn't exist
output_dir = "test_qr_codes"
os.makedirs(output_dir, exist_ok=True)

# Sample tag numbers from the provided list
tag_numbers = [
    "106208111223",
    "106296833111",
    "106296201654",
    "106296201046",
    "106296833268"
]

for tag in tag_numbers:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(tag)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    file_path = os.path.join(output_dir, f"{tag}.png")
    img.save(file_path)
    print(f"Generated QR Code for Tag No {tag} -> {file_path}")

print("Done! You can find the test QR codes in the 'test_qr_codes' folder.")
