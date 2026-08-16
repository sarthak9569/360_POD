import os
import cloudinary
import cloudinary.uploader

# Cloudinary automatically picks up the CLOUDINARY_URL from the environment
cloudinary.config()

def upload_media(file_path: str, is_video: bool = False) -> str:
    """
    Uploads an image or video to Cloudinary in a separate folder for this project.
    """
    try:
        # We specify the "folder" parameter here to keep files separate
        options = {
            "folder": "pod2_assets", # ALL files for this project go here!
            "resource_type": "video" if is_video else "image"
        }
        
        response = cloudinary.uploader.upload(file_path, **options)
        
        # Return the secure URL to store in your MongoDB database
        return response.get("secure_url")
        
    except Exception as e:
        print(f"Error uploading to Cloudinary: {e}")
        return None
