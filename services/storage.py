import os
import uuid
from pathlib import Path
from config.settings import STORAGE_BACKEND  # "cloudinary" o "local"


# ── Interface común ────────────────────────────────────────────────

def upload_image(file_bytes: bytes, product_slug: str, position: int = 0) -> dict:
    """
    Sube una imagen al backend configurado.
    Retorna dict con 'url' y 'public_id'.
    """
    if STORAGE_BACKEND == "cloudinary":
        return _upload_cloudinary(file_bytes, product_slug, position)
    return _upload_local(file_bytes, product_slug, position)


def delete_image(public_id: str) -> None:
    """Elimina una imagen del backend configurado."""
    if STORAGE_BACKEND == "cloudinary":
        _delete_cloudinary(public_id)
    else:
        _delete_local(public_id)


# ── Cloudinary ─────────────────────────────────────────────────────

def _upload_cloudinary(file_bytes: bytes, product_slug: str, position: int) -> dict:
    import cloudinary
    import cloudinary.uploader
    from config.settings import CLOUDINARY_CONFIG

    cloudinary.config(
        cloud_name=CLOUDINARY_CONFIG["cloud_name"],
        api_key=CLOUDINARY_CONFIG["api_key"],
        api_secret=CLOUDINARY_CONFIG["api_secret"],
        secure=True,
    )
    result = cloudinary.uploader.upload(
        file_bytes,
        folder="ceramics_shop/products",
        public_id=f"{product_slug}_{position}",
        overwrite=True,
        transformation=[
            {"width": 800, "height": 800, "crop": "limit"},
            {"quality": "auto:good"},
            {"fetch_format": "auto"},
        ],
    )
    return {
        "url": result["secure_url"],
        "public_id": result["public_id"],
    }


def _delete_cloudinary(public_id: str) -> None:
    import cloudinary
    import cloudinary.uploader
    from config.settings import CLOUDINARY_CONFIG

    cloudinary.config(**CLOUDINARY_CONFIG)
    cloudinary.uploader.destroy(public_id)


# ── Local ──────────────────────────────────────────────────────────

LOCAL_UPLOAD_DIR = Path("assets/uploads")


def _ensure_upload_dir() -> None:
    LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _upload_local(file_bytes: bytes, product_slug: str, position: int) -> dict:
    """
    Guarda la imagen en assets/uploads/.
    public_id = nombre del archivo (para poder borrarlo después).
    url = ruta relativa que Streamlit puede servir.
    """
    _ensure_upload_dir()

    # Nombre único para evitar colisiones
    filename = f"{product_slug}_{position}_{uuid.uuid4().hex[:8]}.jpg"
    filepath = LOCAL_UPLOAD_DIR / filename

    # Redimensionar con Pillow si supera 800px
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(file_bytes))
        img.thumbnail((800, 800))
        # Convertir a RGB si es RGBA (PNG con transparencia)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(filepath, "JPEG", quality=85, optimize=True)
    except Exception:
        # Fallback: guardar los bytes tal cual
        filepath.write_bytes(file_bytes)

    return {
        "url": f"assets/uploads/{filename}",   # ruta relativa
        "public_id": filename,                  # nombre del archivo
    }


def _delete_local(public_id: str) -> None:
    """public_id en local es el nombre del archivo."""
    filepath = LOCAL_UPLOAD_DIR / public_id
    if filepath.exists():
        filepath.unlink()





def get_image_url(url: str) -> str:
    """
    Cloudinary: URL absoluta, se retorna tal cual.
    Local: ruta relativa, verifica que el archivo exista.
    Retorna string vacío si no encuentra nada.
    """
    if not url:
        return ""
    if url.startswith("http"):
        return url
    filepath = Path(url)
    if filepath.exists() and filepath.is_file():
        return str(filepath)
    return ""    