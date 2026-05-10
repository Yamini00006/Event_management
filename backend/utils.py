import os
import re
import uuid
import qrcode
from io import BytesIO
from PIL import Image
from pathlib import Path
from datetime import datetime
from fastapi import UploadFile, HTTPException
import base64

from backend.config import settings

UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(exist_ok=True)
(UPLOAD_DIR / "avatars").mkdir(exist_ok=True)
(UPLOAD_DIR / "events").mkdir(exist_ok=True)
(UPLOAD_DIR / "qrcodes").mkdir(exist_ok=True)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    text = re.sub(r'^-+|-+$', '', text)
    return text


def generate_unique_slug(title: str, db, EventModel) -> str:
    base_slug = slugify(title)
    slug = base_slug
    counter = 1
    while db.query(EventModel).filter(EventModel.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def generate_ticket_number() -> str:
    return f"TKT-{uuid.uuid4().hex[:8].upper()}"


def generate_qr_code(data: str, filename: str) -> str:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    filepath = UPLOAD_DIR / "qrcodes" / f"{filename}.png"
    img.save(str(filepath))
    
    return f"/uploads/qrcodes/{filename}.png"


async def save_upload(file: UploadFile, folder: str) -> str:
    if file.size and file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")
    
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only image files allowed")
    
    ext = file.filename.split(".")[-1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = UPLOAD_DIR / folder / filename
    
    content = await file.read()
    
    # Resize if needed
    img = Image.open(BytesIO(content))
    if folder == "avatars":
        img.thumbnail((400, 400))
    elif folder == "events":
        img.thumbnail((1200, 630))
    
    img.save(str(filepath), optimize=True, quality=85)
    
    return f"/uploads/{folder}/{filename}"


def format_datetime(dt: datetime) -> str:
    return dt.strftime("%B %d, %Y at %I:%M %p")
