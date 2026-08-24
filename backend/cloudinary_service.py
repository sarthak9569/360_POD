import os
import cloudinary
import cloudinary.uploader

# Cloudinary automatically picks up the CLOUDINARY_URL from the environment
cloudinary.config()

def upload_media(file_path: str, is_video: bool = False, subfolder: str = "") -> str:
    """
    Uploads an image or video to Cloudinary in a separate folder for this project.
    """
    try:
        # We specify the "folder" parameter here to keep files separate
        folder_path = "pod2_assets"
        if subfolder:
            folder_path = f"pod2_assets/{subfolder}"
            
        res_type = "image"
        if is_video:
            res_type = "video"
        elif file_path.lower().endswith(".pdf"):
            res_type = "raw"
            
        options = {
            "folder": folder_path,
            "resource_type": res_type
        }
        
        response = cloudinary.uploader.upload(file_path, **options)
        
        # Return the secure URL to store in your MongoDB database
        return response.get("secure_url")
        
    except Exception as e:
        print(f"Error uploading to Cloudinary: {e}")
        return None
