import mercadopago
from config.settings import MP_ACCESS_TOKEN, MP_PUBLIC_KEY
from db.connection import get_db
from db.models import Order

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)


def crear_preferencia(order: Order, items: list) -> dict:
    """
    Crea una preferencia de pago en MercadoPago.
    Retorna dict con 'id' y 'init_point' (URL de pago).
    """
    preference_data = {
        "items": [
            {
                "id":          str(item.product_id),
                "title":       item.product_name,
                "quantity":    item.quantity,
                "unit_price":  float(item.unit_price),
                "currency_id": "ARS",
            }
            for item in items
        ],
        "back_urls": {
            "success": "http://localhost:8000/pago/exitoso",
            "failure": "http://localhost:8000/pago/fallido",
            "pending": "http://localhost:8000/pago/pendiente",
        },
        # "auto_return": "approved",
        "external_reference": str(order.id),
        "statement_descriptor": "Green Ceramica",
        "metadata": {
            "order_id": order.id,
        },
    }

    result = sdk.preference().create(preference_data)

    if result["status"] not in [200, 201]:
        raise ValueError(f"Error creando preferencia MP: {result}")

    return {
        "id":         result["response"]["id"],
        "init_point": result["response"]["init_point"],      # producción
        "sandbox_url": result["response"]["sandbox_init_point"],  # pruebas
    }


def procesar_webhook(data: dict) -> dict | None:
    """
    Procesa notificación de MercadoPago.
    Retorna dict con order_id y status si el pago fue aprobado.
    """
    if data.get("type") != "payment":
        return None

    payment_id = data.get("data", {}).get("id")
    if not payment_id:
        return None

    result = sdk.payment().get(payment_id)
    if result["status"] != 200:
        return None

    payment = result["response"]
    status  = payment.get("status")
    order_id = payment.get("external_reference")

    return {
        "payment_id": str(payment_id),
        "order_id":   int(order_id) if order_id else None,
        "status":     status,  # "approved", "pending", "rejected"
        "amount":     payment.get("transaction_amount"),
    }