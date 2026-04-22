from db.models import ProductImage
from db.connection import get_db
from services.storage import upload_image, delete_image


def add_image_to_product(
    product_id: int,
    url: str,
    public_id: str,
    position: int = 0,
    alt_text: str = "",
) -> ProductImage:
    with get_db() as db:
        img = ProductImage(
            product_id=product_id,
            url=url,
            public_id=public_id,
            alt_text=alt_text,
            position=position,
            is_primary=(position == 0),
        )
        db.add(img)
        db.flush()
        db.expunge(img)
        from sqlalchemy.orm import make_transient
        make_transient(img)
        return img


def delete_product_images(product_id: int) -> None:
    """Elimina todas las imágenes de un producto (DB + storage)."""
    with get_db() as db:
        images = db.query(ProductImage).filter(
            ProductImage.product_id == product_id
        ).all()
        for img in images:
            if img.public_id:
                delete_image(img.public_id)
            db.delete(img)


# import cloudinary
# import cloudinary.uploader
# from config.settings import CLOUDINARY_CONFIG
# from db.models import ProductImage
# from db.connection import get_db

# # Configurar Cloudinary una sola vez al importar
# cloudinary.config(
#     cloud_name=CLOUDINARY_CONFIG["cloud_name"],
#     api_key=CLOUDINARY_CONFIG["api_key"],
#     api_secret=CLOUDINARY_CONFIG["api_secret"],
#     secure=True,
# )

# UPLOAD_FOLDER = "ceramics_shop/products"  # carpeta dentro de Cloudinary


# def upload_image(file_bytes: bytes, product_slug: str, position: int = 0) -> dict:
#     """
#     Sube una imagen a Cloudinary.
#     Retorna dict con 'url' y 'public_id'.
#     """
#     result = cloudinary.uploader.upload(
#         file_bytes,
#         folder=UPLOAD_FOLDER,
#         public_id=f"{product_slug}_{position}",
#         overwrite=True,
#         transformation=[
#             {"width": 800, "height": 800, "crop": "limit"},  # máximo 800×800
#             {"quality": "auto:good"},
#             {"fetch_format": "auto"},  # webp en browsers modernos
#         ],
#     )
#     return {
#         "url": result["secure_url"],
#         "public_id": result["public_id"],
#     }


# def delete_image(public_id: str) -> None:
#     """Elimina una imagen de Cloudinary por su public_id."""
#     cloudinary.uploader.destroy(public_id)


# def add_image_to_product(
#     product_id: int,
#     url: str,
#     public_id: str,
#     position: int = 0,
#     alt_text: str = "",
# ) -> ProductImage:
#     with get_db() as db:
#         # Si position == 0, es la imagen principal
#         img = ProductImage(
#             product_id=product_id,
#             url=url,
#             public_id=public_id,
#             alt_text=alt_text,
#             position=position,
#             is_primary=(position == 0),
#         )
#         db.add(img)
#         db.flush()
#         db.refresh(img)
#         return img


# def delete_product_images(product_id: int) -> None:
#     """Elimina todas las imágenes de un producto (DB + Cloudinary)."""
#     with get_db() as db:
#         images = db.query(ProductImage).filter(
#             ProductImage.product_id == product_id
#         ).all()
#         for img in images:
#             if img.public_id:
#                 delete_image(img.public_id)
#             db.delete(img)