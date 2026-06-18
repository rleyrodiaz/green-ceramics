import requests as http_requests
from db.connection import get_db
from db.models import ActivityLog


def _lookup_name(user_id: int) -> str:
    try:
        with get_db() as db:
            from db.models import User
            u = db.query(User).filter(User.id == user_id).first()
            return u.name if u else f"user_{user_id}"
    except Exception:
        return f"user_{user_id}"


def parse_device(user_agent_str: str) -> dict:
    try:
        import user_agents
        ua = user_agents.parse(user_agent_str or "")
        if ua.is_mobile:
            device = "mobile"
        elif ua.is_tablet:
            device = "tablet"
        else:
            device = "desktop"
        return {
            "device_type": device,
            "browser":     ua.browser.family,
            "os":          ua.os.family,
        }
    except Exception:
        return {}


def get_geo(ip: str) -> dict:
    if not ip or ip in ("127.0.0.1", "::1", "testclient"):
        return {}
    try:
        res = http_requests.get(
            f"http://ip-api.com/json/{ip}?fields=country,city,status",
            timeout=2
        )
        data = res.json()
        if data.get("status") == "success":
            return {"country": data.get("country"), "city": data.get("city")}
    except Exception:
        pass
    return {}


def get_client_ip(request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


def log(
    action:      str,
    entity_type: str  = None,
    entity_id:   int  = None,
    entity_desc: str  = None,
    detail:      str  = None,
    user_id:     int  = None,
    user_name:   str  = None,
    session_id:  str  = None,
    request=None,
) -> None:
    try:
        name    = user_name or (_lookup_name(user_id) if user_id else "anónimo")
        geo     = {}
        device  = {}
        referrer = None

        if request:
            ip       = get_client_ip(request)
            geo      = get_geo(ip)
            device   = parse_device(request.headers.get("User-Agent", ""))
            referrer = request.headers.get("Referer", None)
            if not session_id:
                session_id = request.headers.get("X-Session-ID")

        with get_db() as db:
            db.add(ActivityLog(
                session_id  = session_id,
                user_id     = user_id,
                user_name   = name,
                action      = action,
                entity_type = entity_type,
                entity_id   = entity_id,
                entity_desc = entity_desc,
                detail      = detail,
                country     = geo.get("country"),
                city        = geo.get("city"),
                device_type = device.get("device_type"),
                browser     = device.get("browser"),
                os          = device.get("os"),
                referrer    = referrer,
            ))
    except Exception as e:
        import traceback
        print(f"[WARN] Error activity log [{action}]: {e}")
        traceback.print_exc()
