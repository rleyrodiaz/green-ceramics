from datetime import datetime, timedelta
from jose import JWTError, jwt
from config.settings import SECRET_KEY

ALGORITHM   = "HS256"
EXPIRE_DAYS = 7


def crear_token(user_id: int, rol: str) -> str:
    payload = {
        "sub":  str(user_id),
        "rol":  rol,
        "exp":  datetime.utcnow() + timedelta(days=EXPIRE_DAYS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verificar_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def es_admin_token(token: str) -> bool:
    payload = verificar_token(token)
    if not payload:
        return False
    rol = payload.get("rol")
    return rol in ("admin", "owner")