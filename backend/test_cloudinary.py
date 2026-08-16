from cloudinary_service import upload_media
import os

with open("test_image.jpg", "wb") as f:
    f.write(b"test image content")

print("Testing upload...")
url = upload_media("test_image.jpg")
print(f"Result URL: {url}")

os.remove("test_image.jpg")
