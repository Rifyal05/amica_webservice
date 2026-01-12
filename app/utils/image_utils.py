import os
from PIL import Image, ImageOps
from flask import current_app

def generate_thumbnail(filename_only, size=(256, 256)):
    if not filename_only:
        return None
    
    static_folder = current_app.static_folder
    original_full_path = os.path.join(static_folder, 'uploads', filename_only) # type: ignore
    
    thumb_folder = os.path.join(static_folder, 'thumbnails') # type: ignore
    thumb_filename = f"thumb_{size[0]}x{size[1]}_{filename_only}"
    thumb_full_path = os.path.join(thumb_folder, thumb_filename)

    if os.path.exists(thumb_full_path):
        return f"thumbnails/{thumb_filename}"

    if not os.path.exists(original_full_path):
        return None

    try:
        if not os.path.exists(thumb_folder):
            os.makedirs(thumb_folder)

        with Image.open(original_full_path) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            thumb_img = ImageOps.fit(img, size, Image.Resampling.LANCZOS)
            thumb_img.save(thumb_full_path, quality=85, optimize=True)
            
        return f"thumbnails/{thumb_filename}"
        
    except Exception:
        return None