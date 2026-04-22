"""
Testea upload y delete en ambos backends.
Correr con: poetry run python test_storage.py
"""
import os
from pathlib import Path

# ── Test LOCAL ─────────────────────────────────────────────────────

print("=" * 50)
print("TEST STORAGE LOCAL")
print("=" * 50)

os.environ["STORAGE_BACKEND"] = "local"

# Forzar recarga de settings con el nuevo valor
import importlib
import config.settings as settings_module
importlib.reload(settings_module)

from services.storage import upload_image, delete_image, get_image_url

# Crear una imagen de prueba (cuadrado rojo 100x100) sin necesitar archivo real
from PIL import Image
import io

img = Image.new("RGB", (100, 100), color=(180, 80, 60))
buf = io.BytesIO()
img.save(buf, format="JPEG")
image_bytes = buf.getvalue()

# Upload
result = upload_image(image_bytes, "test-producto", position=0)
print(f"✅ Upload local OK")
print(f"   url       : {result['url']}")
print(f"   public_id : {result['public_id']}")

# Verificar que el archivo existe
filepath = Path(result["url"])
assert filepath.exists(), "❌ El archivo no se creó en disco"
print(f"   archivo   : existe en disco ✅")

# get_image_url
resolved = get_image_url(result["url"])
print(f"   get_image_url: {resolved}")

# Delete
delete_image(result["public_id"])
assert not filepath.exists(), "❌ El archivo no se eliminó"
print(f"✅ Delete local OK\n")


# ── Test CLOUDINARY ────────────────────────────────────────────────

print("=" * 50)
print("TEST STORAGE CLOUDINARY")
print("=" * 50)

from dotenv import load_dotenv
load_dotenv()

cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
api_key    = os.getenv("CLOUDINARY_API_KEY")
api_secret = os.getenv("CLOUDINARY_API_SECRET")

if not all([cloud_name, api_key, api_secret]):
    print("⚠️  Credenciales de Cloudinary no configuradas en .env — saltando test")
else:
    os.environ["STORAGE_BACKEND"] = "cloudinary"
    importlib.reload(settings_module)

    # Reimportar storage con el nuevo backend
    import services.storage as storage_module
    importlib.reload(storage_module)
    from services.storage import upload_image as upload_cl, delete_image as delete_cl

    result_cl = upload_cl(image_bytes, "test-producto-cl", position=0)
    print(f"✅ Upload Cloudinary OK")
    print(f"   url       : {result_cl['url']}")
    print(f"   public_id : {result_cl['public_id']}")

    delete_cl(result_cl["public_id"])
    print(f"✅ Delete Cloudinary OK\n")

print("=" * 50)
print("TODOS LOS TESTS PASARON ✅")
print("=" * 50)