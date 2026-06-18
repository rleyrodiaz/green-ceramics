from db.connection import get_db
from db.models import AppSetting

# Valores por defecto si la clave no existe en la DB
DEFAULTS: dict[str, str] = {
    "shipping.domicilio":           "5000",
    "shipping.sucursal":            "3500",
    "shipping.free_threshold":      "50000",
    "reminders.mp_hours":           "24",
    "reminders.transfer_hours":     "48",
    "bank.cbu":                     "",
    "bank.alias":                   "",
    "bank.holder":                  "",
    "notifications.visit_email":    "false",
    "notifications.visit_email_to": "",
}

LABELS: dict[str, str] = {
    "shipping.domicilio":           "Costo envío a domicilio ($)",
    "shipping.sucursal":            "Costo retiro en sucursal ($)",
    "shipping.free_threshold":      "Mínimo para envío gratis ($)",
    "reminders.mp_hours":           "Recordatorio MP — horas de espera",
    "reminders.transfer_hours":     "Recordatorio transferencia — horas de espera",
    "bank.cbu":                     "CBU",
    "bank.alias":                   "Alias",
    "bank.holder":                  "Titular",
    "notifications.visit_email":    "Notificar visitas por email (true/false)",
    "notifications.visit_email_to": "Email de notificaciones",
}


def get_setting(key: str, default: str = "") -> str:
    try:
        with get_db() as db:
            s = db.query(AppSetting).filter(AppSetting.key == key).first()
            return s.value if s else DEFAULTS.get(key, default)
    except Exception:
        return DEFAULTS.get(key, default)


def get_int(key: str) -> int:
    return int(float(get_setting(key, DEFAULTS.get(key, "0"))))


def get_float(key: str) -> float:
    return float(get_setting(key, DEFAULTS.get(key, "0")))


def get_bool(key: str) -> bool:
    return get_setting(key, DEFAULTS.get(key, "false")).strip().lower() == "true"


def set_setting(key: str, value: str) -> None:
    with get_db() as db:
        s = db.query(AppSetting).filter(AppSetting.key == key).first()
        if s:
            s.value = str(value)
        else:
            db.add(AppSetting(key=key, value=str(value), label=LABELS.get(key, key)))


def get_all_settings() -> list[dict]:
    try:
        with get_db() as db:
            rows = db.query(AppSetting).order_by(AppSetting.key).all()
            existing = {r.key: r.value for r in rows}
        result = []
        for key, default in DEFAULTS.items():
            result.append({
                "key":   key,
                "value": existing.get(key, default),
                "label": LABELS.get(key, key),
            })
        return result
    except Exception:
        return []


def seed_defaults(initial_values: dict[str, str]) -> None:
    """Inserta solo las claves que no existen todavía."""
    try:
        with get_db() as db:
            for key, value in initial_values.items():
                existing = db.query(AppSetting).filter(AppSetting.key == key).first()
                if not existing:
                    db.add(AppSetting(key=key, value=value, label=LABELS.get(key, key)))
    except Exception as e:
        print(f"[WARN] Error seeding settings: {e}")
