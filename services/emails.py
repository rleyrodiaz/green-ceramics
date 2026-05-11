import resend
from config.settings import RESEND_API_KEY, EMAIL_FROM

resend.api_key = RESEND_API_KEY

SITE_URL = "https://green-ceramics.onrender.com"


# ── Helpers ────────────────────────────────────────────────────────

def _precio(n) -> str:
    return f"${float(n):,.0f}".replace(",", ".")


def _header() -> str:
    return """
    <div style="background:#3d2b1f;padding:2rem 3rem;text-align:center">
        <p style="font-family:'Georgia',serif;font-size:2rem;font-weight:300;
                  letter-spacing:0.2em;color:#f5f0e8;margin:0">
            Green<span style="color:#c4875a">.</span>
        </p>
        <p style="font-size:0.75rem;letter-spacing:0.3em;text-transform:uppercase;
                  color:rgba(245,240,232,0.5);margin:0.5rem 0 0">
            Cerámica en Gres
        </p>
    </div>"""


def _footer() -> str:
    return """
    <div style="text-align:center;padding:2rem;border-top:1px solid #e8ddd0;
                color:#7a6a5a;font-size:0.8rem;line-height:2">
        <p style="margin:0">Green. Cerámica en Gres</p>
        <p style="margin:0">hola@greenceramica.com &nbsp;·&nbsp; @green.ceramica</p>
        <p style="margin:0">Cada pieza es única e irrepetible</p>
    </div>"""


def _btn(text: str, url: str) -> str:
    return f"""
    <a href="{url}" style="display:inline-block;background:#3d2b1f;color:#f5f0e8;
       padding:0.9rem 2rem;font-size:0.82rem;letter-spacing:0.15em;
       text-transform:uppercase;text-decoration:none;margin-top:1.5rem">
        {text}
    </a>"""


def _eyebrow(text: str) -> str:
    return f"""<p style="font-size:0.72rem;letter-spacing:0.3em;text-transform:uppercase;
                         color:#c4875a;margin-bottom:0.5rem">{text}</p>"""


def _wrap(body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#f5f0e8;font-family:'Jost',sans-serif;
             font-weight:300;color:#2c1f14">
    {_header()}
    <div style="max-width:560px;margin:0 auto;padding:3rem 2rem">
        {body}
    </div>
    {_footer()}
</body>
</html>"""


def _send(to: str, subject: str, html: str) -> bool:
    try:
        resend.api_key = RESEND_API_KEY
        resend.Emails.send({"from": EMAIL_FROM, "to": to, "subject": subject, "html": html})
        return True
    except Exception as e:
        print(f"⚠️ Error email '{subject}' → {to}: {e}")
        return False


def _items_table(items: list) -> str:
    rows = "".join([
        f"""<tr>
            <td style="padding:0.6rem 0;border-bottom:1px solid #f0ebe3;
                       font-family:'Georgia',serif;color:#3d2b1f">{i['nombre']}</td>
            <td style="padding:0.6rem 0;border-bottom:1px solid #f0ebe3;
                       text-align:center;color:#7a6a5a">×{i['cantidad']}</td>
            <td style="padding:0.6rem 0;border-bottom:1px solid #f0ebe3;
                       text-align:right;color:#3d2b1f">{_precio(i['subtotal'])}</td>
        </tr>"""
        for i in items
    ])
    return f'<table style="width:100%;border-collapse:collapse"><tbody>{rows}</tbody></table>'


# ── 1. Bienvenida ──────────────────────────────────────────────────

def enviar_bienvenida(to_email: str, nombre: str) -> bool:
    body = f"""
        {_eyebrow("Bienvenida")}
        <h1 style="font-family:'Georgia',serif;font-size:2rem;font-weight:300;
                   color:#3d2b1f;margin:0 0 1.5rem;line-height:1.2">
            Hola, {nombre}.
        </h1>
        <p style="color:#7a6a5a;line-height:1.9;margin-bottom:1rem">
            Qué bueno tenerte en Green. Hacemos cerámica en gres a mano, sin moldes
            y sin series. Cada pieza que encontrás en nuestra tienda es única e
            irrepetible — nació de las manos y el tiempo.
        </p>
        <p style="color:#7a6a5a;line-height:1.9">
            Explorá la colección y encontrá la pieza que te acompaña en el día a día.
        </p>
        {_btn("Ver colección", f"{SITE_URL}/catalogo")}
    """
    return _send(to_email, "Green. — Bienvenida", _wrap(body))


# ── 2. Pago confirmado ────────────────────────────────────────────

def enviar_pago_confirmado(
    to_email: str,
    nombre: str,
    order_id: int,
    items: list,
    subtotal: float,
    shipping: float,
    total: float,
    shipping_method: str,
    shipping_address: str = "",
    shipping_branch: str = "",
) -> bool:
    shipping_label = {
        "domicilio": "Envío a domicilio",
        "sucursal":  "Retiro en sucursal",
        "personal":  "Entrega personal",
    }.get(shipping_method, "Envío")

    shipping_detail = shipping_address or shipping_branch or "—"

    body = f"""
        {_eyebrow("Pago acreditado")}
        <h1 style="font-family:'Georgia',serif;font-size:2rem;font-weight:300;
                   color:#3d2b1f;margin:0 0 0.5rem;line-height:1.2">
            ¡Listo, {nombre}!
        </h1>
        <p style="color:#7a6a5a;margin-bottom:2rem">
            Tu pago del pedido <strong style="color:#3d2b1f">#{order_id}</strong>
            fue acreditado. Vamos a preparar todo con cuidado.
        </p>

        <div style="background:#fff;padding:1.5rem 2rem;margin-bottom:1.5rem">
            {_eyebrow("Tu pedido")}
            {_items_table(items)}
            <table style="width:100%;border-collapse:collapse;margin-top:0.75rem">
                <tr>
                    <td style="padding:0.5rem 0;color:#7a6a5a;font-size:0.85rem">Subtotal</td>
                    <td style="padding:0.5rem 0;text-align:right;color:#7a6a5a;font-size:0.85rem">{_precio(subtotal)}</td>
                </tr>
                <tr>
                    <td style="padding:0.5rem 0;color:#7a6a5a;font-size:0.85rem">Envío</td>
                    <td style="padding:0.5rem 0;text-align:right;color:#7a6a5a;font-size:0.85rem">{"Gratis" if shipping == 0 else _precio(shipping)}</td>
                </tr>
                <tr style="border-top:1px solid #e8ddd0">
                    <td style="padding:0.75rem 0 0;font-family:'Georgia',serif;font-size:1.1rem;color:#3d2b1f">Total</td>
                    <td style="padding:0.75rem 0 0;text-align:right;font-family:'Georgia',serif;font-size:1.1rem;color:#3d2b1f">{_precio(total)}</td>
                </tr>
            </table>
        </div>

        <div style="background:#fff;padding:1.5rem 2rem;margin-bottom:2rem">
            {_eyebrow("Envío")}
            <p style="color:#3d2b1f;margin:0">{shipping_label}</p>
            <p style="color:#7a6a5a;font-size:0.9rem;margin:0.3rem 0 0">{shipping_detail}</p>
        </div>

        <p style="color:#7a6a5a;font-size:0.85rem;line-height:1.9">
            ✦ Te avisamos cuando tu pedido esté en camino<br>
            ✦ Embalaje especial para cerámica<br>
            ✦ Ante cualquier consulta respondemos en 24-48 hs
        </p>
    """
    return _send(to_email, f"Green. — Pedido #{order_id} confirmado", _wrap(body))


# ── 3. Comprobante recibido ───────────────────────────────────────

def enviar_comprobante_recibido(
    to_email: str,
    nombre: str,
    order_id: int,
    total: float,
) -> bool:
    body = f"""
        {_eyebrow("Comprobante recibido")}
        <h1 style="font-family:'Georgia',serif;font-size:2rem;font-weight:300;
                   color:#3d2b1f;margin:0 0 1rem;line-height:1.2">
            Recibimos tu comprobante.
        </h1>
        <p style="color:#7a6a5a;line-height:1.9;margin-bottom:1.5rem">
            Estamos verificando la transferencia del pedido
            <strong style="color:#3d2b1f">#{order_id}</strong>
            por <strong style="color:#3d2b1f">{_precio(total)}</strong>.
            En las próximas 24 horas te confirmamos el pago y arrancamos con la preparación.
        </p>
        <p style="color:#7a6a5a;font-size:0.85rem;line-height:1.9">
            ✦ Si tenés alguna duda escribinos a hola@greenceramica.com
        </p>
    """
    return _send(to_email, f"Green. — Comprobante recibido, verificando pedido #{order_id}", _wrap(body))


# ── 4. Pago fallido ───────────────────────────────────────────────

def enviar_pago_fallido(
    to_email: str,
    nombre: str,
    order_id: int,
    total: float,
) -> bool:
    body = f"""
        {_eyebrow("Problema con el pago")}
        <h1 style="font-family:'Georgia',serif;font-size:2rem;font-weight:300;
                   color:#3d2b1f;margin:0 0 1rem;line-height:1.2">
            No pudimos procesar tu pago.
        </h1>
        <p style="color:#7a6a5a;line-height:1.9;margin-bottom:1rem">
            El pago del pedido <strong style="color:#3d2b1f">#{order_id}</strong>
            por <strong style="color:#3d2b1f">{_precio(total)}</strong>
            no pudo completarse. No se realizó ningún cobro.
        </p>
        <p style="color:#7a6a5a;line-height:1.9;margin-bottom:1.5rem">
            Puede haber ocurrido por fondos insuficientes, datos de tarjeta incorrectos
            o una restricción del banco. Tu carrito está intacto para que puedas
            intentarlo de nuevo.
        </p>
        {_btn("Volver al carrito", f"{SITE_URL}/carrito")}
    """
    return _send(to_email, f"Green. — Problema con el pago del pedido #{order_id}", _wrap(body))


# ── 5. Recordatorio MP ────────────────────────────────────────────

def enviar_recordatorio_mp(
    to_email: str,
    nombre: str,
    order_id: int,
    total: float,
) -> bool:
    body = f"""
        {_eyebrow("Tu pedido te está esperando")}
        <h1 style="font-family:'Georgia',serif;font-size:2rem;font-weight:300;
                   color:#3d2b1f;margin:0 0 1rem;line-height:1.2">
            ¿Tuviste algún problema, {nombre}?
        </h1>
        <p style="color:#7a6a5a;line-height:1.9;margin-bottom:1rem">
            Iniciaste el checkout del pedido
            <strong style="color:#3d2b1f">#{order_id}</strong>
            por <strong style="color:#3d2b1f">{_precio(total)}</strong>
            pero el pago todavía no fue completado.
        </p>
        <p style="color:#7a6a5a;line-height:1.9;margin-bottom:1.5rem">
            Si surgió algún inconveniente o querés pagar por transferencia,
            escribinos y te ayudamos.
        </p>
        {_btn("Completar el pago", f"{SITE_URL}/carrito")}
        <p style="color:#7a6a5a;font-size:0.82rem;margin-top:1.5rem">
            Si ya resolviste el pago, ignorá este mensaje.
        </p>
    """
    return _send(to_email, f"Green. — Tu pedido #{order_id} está pendiente de pago", _wrap(body))


# ── 6. Recordatorio transferencia ────────────────────────────────

def enviar_recordatorio_transfer(
    to_email: str,
    nombre: str,
    order_id: int,
    total: float,
    cbu: str,
    alias: str,
    titular: str,
) -> bool:
    body = f"""
        {_eyebrow("Comprobante pendiente")}
        <h1 style="font-family:'Georgia',serif;font-size:2rem;font-weight:300;
                   color:#3d2b1f;margin:0 0 1rem;line-height:1.2">
            Falta el comprobante, {nombre}.
        </h1>
        <p style="color:#7a6a5a;line-height:1.9;margin-bottom:1.5rem">
            Tu pedido <strong style="color:#3d2b1f">#{order_id}</strong> está listo
            pero todavía no recibimos el comprobante de la transferencia.
        </p>

        <div style="background:#fff;padding:1.5rem 2rem;margin-bottom:1.5rem">
            {_eyebrow("Datos para la transferencia")}
            <table style="width:100%;border-collapse:collapse">
                <tr>
                    <td style="padding:0.5rem 0;color:#7a6a5a;font-size:0.85rem;width:80px">CBU</td>
                    <td style="padding:0.5rem 0;color:#3d2b1f;font-family:monospace">{cbu}</td>
                </tr>
                <tr>
                    <td style="padding:0.5rem 0;color:#7a6a5a;font-size:0.85rem">Alias</td>
                    <td style="padding:0.5rem 0;color:#3d2b1f">{alias}</td>
                </tr>
                <tr>
                    <td style="padding:0.5rem 0;color:#7a6a5a;font-size:0.85rem">Titular</td>
                    <td style="padding:0.5rem 0;color:#3d2b1f">{titular}</td>
                </tr>
                <tr style="border-top:1px solid #e8ddd0">
                    <td style="padding:0.75rem 0 0;color:#7a6a5a;font-size:0.85rem">Monto</td>
                    <td style="padding:0.75rem 0 0;color:#3d2b1f;font-family:'Georgia',serif;font-size:1.1rem">{_precio(total)}</td>
                </tr>
            </table>
        </div>

        {_btn("Subir comprobante", f"{SITE_URL}/cuenta")}
    """
    return _send(to_email, f"Green. — Pedido #{order_id}: falta el comprobante", _wrap(body))


# ── 7. Pedido enviado ─────────────────────────────────────────────

def enviar_pedido_enviado(
    to_email: str,
    nombre: str,
    order_id: int,
    shipping_method: str,
    shipping_address: str = "",
    shipping_branch: str = "",
    tracking_number: str = "",
) -> bool:
    shipping_label = {
        "domicilio": "Envío a domicilio",
        "sucursal":  "Retiro en sucursal",
        "personal":  "Entrega personal",
    }.get(shipping_method, "Envío")

    shipping_detail = shipping_address or shipping_branch or ""

    tracking_html = ""
    if tracking_number:
        tracking_url = f"https://www.correoargentino.com.ar/formularios/cuentacorriente?id={tracking_number}"
        tracking_html = f"""
        <div style="background:#fff;padding:1.5rem 2rem;margin-top:1.5rem">
            {_eyebrow("Número de seguimiento")}
            <p style="font-family:monospace;font-size:1.1rem;color:#3d2b1f;margin:0">
                {tracking_number}
            </p>
            <a href="{tracking_url}" style="color:#c4875a;font-size:0.85rem;
               text-decoration:none;display:inline-block;margin-top:0.5rem">
                Rastrear en Correo Argentino →
            </a>
        </div>"""

    body = f"""
        {_eyebrow("Pedido en camino")}
        <h1 style="font-family:'Georgia',serif;font-size:2rem;font-weight:300;
                   color:#3d2b1f;margin:0 0 1rem;line-height:1.2">
            Tu pedido fue despachado.
        </h1>
        <p style="color:#7a6a5a;line-height:1.9;margin-bottom:1.5rem">
            El pedido <strong style="color:#3d2b1f">#{order_id}</strong> salió
            hacia vos. Embalamos cada pieza con cuidado para que llegue perfecta.
        </p>

        <div style="background:#fff;padding:1.5rem 2rem">
            {_eyebrow("Método de envío")}
            <p style="color:#3d2b1f;margin:0">{shipping_label}</p>
            {f'<p style="color:#7a6a5a;font-size:0.9rem;margin:0.3rem 0 0">{shipping_detail}</p>' if shipping_detail else ""}
        </div>

        {tracking_html}

        <p style="color:#7a6a5a;font-size:0.85rem;line-height:1.9;margin-top:1.5rem">
            ✦ Tiempo estimado: 3 a 10 días hábiles según destino<br>
            ✦ Ante cualquier consulta escribinos a hola@greenceramica.com
        </p>
    """
    return _send(to_email, f"Green. — Tu pedido #{order_id} está en camino", _wrap(body))


# ── 8. Pedido entregado ───────────────────────────────────────────

def enviar_pedido_entregado(
    to_email: str,
    nombre: str,
    order_id: int,
) -> bool:
    body = f"""
        {_eyebrow("Entregado")}
        <h1 style="font-family:'Georgia',serif;font-size:2rem;font-weight:300;
                   color:#3d2b1f;margin:0 0 1rem;line-height:1.2">
            ¡Tu pedido llegó, {nombre}!
        </h1>
        <p style="color:#7a6a5a;line-height:1.9;margin-bottom:1rem">
            El pedido <strong style="color:#3d2b1f">#{order_id}</strong> fue entregado.
            Esperamos que disfrutes cada pieza tanto como nosotros disfrutamos hacerla.
        </p>
        <p style="color:#7a6a5a;line-height:1.9;margin-bottom:1.5rem">
            Si algo no llegó en perfectas condiciones o tenés alguna consulta,
            escribinos a <a href="mailto:hola@greenceramica.com"
            style="color:#c4875a;text-decoration:none">hola@greenceramica.com</a>
            y lo resolvemos.
        </p>
        {_btn("Ver colección", f"{SITE_URL}/catalogo")}
    """
    return _send(to_email, f"Green. — Tu pedido #{order_id} fue entregado", _wrap(body))


# ── Original (se mantiene) ────────────────────────────────────────

def enviar_confirmacion_pedido(
    to_email:  str,
    to_name:   str,
    order_id:  int,
    items:     list,
    subtotal:  float,
    shipping:  float,
    total:     float,
    direccion: str,
    ciudad:    str,
    provincia: str,
) -> bool:
    items_html = "".join([
        f"""<tr>
            <td style="padding:0.75rem 0;border-bottom:1px solid #f0ebe3;
                       font-family:'Georgia',serif;color:#3d2b1f">{item['nombre']}</td>
            <td style="padding:0.75rem 0;border-bottom:1px solid #f0ebe3;
                       text-align:center;color:#7a6a5a">×{item['cantidad']}</td>
            <td style="padding:0.75rem 0;border-bottom:1px solid #f0ebe3;
                       text-align:right;color:#3d2b1f">{_precio(item['subtotal'])}</td>
        </tr>"""
        for item in items
    ])

    html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f5f0e8;font-family:'Jost',sans-serif;font-weight:300;color:#2c1f14">
    {_header()}
    <div style="max-width:560px;margin:0 auto;padding:3rem 2rem">
        <p style="font-size:0.75rem;letter-spacing:0.3em;text-transform:uppercase;color:#c4875a;margin-bottom:0.5rem">Pedido recibido</p>
        <h1 style="font-family:'Georgia',serif;font-size:2rem;font-weight:300;color:#3d2b1f;margin:0 0 1rem;line-height:1.2">¡Gracias, {to_name}!</h1>
        <p style="color:#7a6a5a;line-height:1.8;margin-bottom:2rem">
            Recibimos tu pedido <strong style="color:#3d2b1f">#{order_id}</strong>. Nos ponemos en contacto para coordinar el envío.
        </p>
        <div style="background:#fff;padding:1.5rem 2rem;margin-bottom:1.5rem">
            <p style="font-size:0.7rem;letter-spacing:0.25em;text-transform:uppercase;color:#c4875a;margin-bottom:1rem">Tu pedido</p>
            <table style="width:100%;border-collapse:collapse">
                <tbody>{items_html}</tbody>
                <tfoot>
                    <tr><td colspan="2" style="padding:0.75rem 0;color:#7a6a5a;font-size:0.85rem">Subtotal</td><td style="padding:0.75rem 0;text-align:right;color:#7a6a5a;font-size:0.85rem">{_precio(subtotal)}</td></tr>
                    <tr><td colspan="2" style="padding:0.75rem 0;color:#7a6a5a;font-size:0.85rem">Envío</td><td style="padding:0.75rem 0;text-align:right;color:#7a6a5a;font-size:0.85rem">{"Gratis" if shipping == 0 else _precio(shipping)}</td></tr>
                    <tr style="border-top:1px solid #e8ddd0"><td colspan="2" style="padding:1rem 0 0;font-family:'Georgia',serif;font-size:1.1rem;color:#3d2b1f">Total</td><td style="padding:1rem 0 0;text-align:right;font-family:'Georgia',serif;font-size:1.1rem;color:#3d2b1f">{_precio(total)}</td></tr>
                </tfoot>
            </table>
        </div>
        <div style="background:#fff;padding:1.5rem 2rem;margin-bottom:2rem">
            <p style="font-size:0.7rem;letter-spacing:0.25em;text-transform:uppercase;color:#c4875a;margin-bottom:0.75rem">Datos de envío</p>
            <p style="color:#3d2b1f;margin:0">{direccion}</p>
            <p style="color:#7a6a5a;font-size:0.9rem;margin:0.2rem 0 0">{ciudad}, {provincia}</p>
        </div>
        <p style="color:#7a6a5a;font-size:0.85rem;line-height:1.8">
            ✦ Embalaje especial para cerámica<br>
            ✦ Te avisamos cuando tu pedido esté en camino<br>
            ✦ Ante cualquier consulta respondemos en 24-48hs
        </p>
    </div>
    {_footer()}
</body>
</html>"""

    return _send(to_email, f"Green. — Pedido #{order_id} recibido", html)


def enviar_comprobante_al_owner(
    to_email:        str,
    order_id:        int,
    customer_name:   str,
    total:           float,
    comprobante_url: str,
) -> bool:
    import base64, requests as _req

    body = _wrap(f"""
        {_eyebrow("Comprobante recibido")}
        <h2 style="font-family:'Georgia',serif;font-size:1.4rem;font-weight:300;
                   color:#3d2b1f;margin:0 0 1.5rem">Nuevo comprobante de transferencia</h2>
        <table style="width:100%;border-collapse:collapse;font-size:0.88rem">
            <tr>
                <td style="padding:0.5rem 0;color:#7a6a5a;width:120px">Pedido</td>
                <td style="padding:0.5rem 0;color:#3d2b1f">#{order_id}</td>
            </tr>
            <tr style="border-top:1px solid #f0ebe3">
                <td style="padding:0.5rem 0;color:#7a6a5a">Cliente</td>
                <td style="padding:0.5rem 0;color:#3d2b1f">{customer_name}</td>
            </tr>
            <tr style="border-top:1px solid #f0ebe3">
                <td style="padding:0.5rem 0;color:#7a6a5a">Monto</td>
                <td style="padding:0.5rem 0;color:#3d2b1f;font-family:'Georgia',serif">{_precio(total)}</td>
            </tr>
        </table>
        <p style="color:#7a6a5a;font-size:0.85rem;margin-top:1.5rem">
            El comprobante está adjunto a este email.
        </p>
    """)

    try:
        resend.api_key = RESEND_API_KEY
        params: dict = {
            "from":    EMAIL_FROM,
            "to":      to_email,
            "subject": f"Green. — Comprobante pedido #{order_id} — {customer_name}",
            "html":    body,
        }
        # Adjuntar imagen si la URL es accesible
        try:
            resp = _req.get(comprobante_url, timeout=5)
            if resp.status_code == 200:
                ext      = comprobante_url.split(".")[-1].split("?")[0] or "jpg"
                filename = f"comprobante_orden_{order_id}.{ext}"
                params["attachments"] = [{
                    "filename": filename,
                    "content":  list(resp.content),
                }]
        except Exception as e:
            print(f"⚠️ No se pudo adjuntar comprobante: {e}")

        resend.Emails.send(params)
        return True
    except Exception as e:
        print(f"⚠️ Error email comprobante owner: {e}")
        return False


def enviar_notificacion_visita(
    to_email:   str,
    country:    str = "",
    city:       str = "",
    device:     str = "",
    browser:    str = "",
    os:         str = "",
    referrer:   str = "",
    entry_page: str = "",
    session_id: str = "",
) -> bool:
    from datetime import datetime
    hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    geo     = ", ".join(filter(None, [city, country])) or "—"
    disp    = " · ".join(filter(None, [device, browser, os])) or "—"
    ref     = referrer or "directo"

    html = _wrap(f"""
        {_eyebrow("Nueva visita")}
        <h2 style="font-family:'Georgia',serif;font-size:1.4rem;font-weight:300;
                   color:#3d2b1f;margin:0 0 1.5rem">Alguien entró al sitio</h2>
        <table style="width:100%;border-collapse:collapse;font-size:0.88rem">
            <tr>
                <td style="padding:0.5rem 0;color:#7a6a5a;width:140px">Hora</td>
                <td style="padding:0.5rem 0;color:#3d2b1f">{hora}</td>
            </tr>
            <tr style="border-top:1px solid #f0ebe3">
                <td style="padding:0.5rem 0;color:#7a6a5a">Ubicación</td>
                <td style="padding:0.5rem 0;color:#3d2b1f">{geo}</td>
            </tr>
            <tr style="border-top:1px solid #f0ebe3">
                <td style="padding:0.5rem 0;color:#7a6a5a">Dispositivo</td>
                <td style="padding:0.5rem 0;color:#3d2b1f">{disp}</td>
            </tr>
            <tr style="border-top:1px solid #f0ebe3">
                <td style="padding:0.5rem 0;color:#7a6a5a">Página entrada</td>
                <td style="padding:0.5rem 0;color:#3d2b1f">{entry_page or "/"}</td>
            </tr>
            <tr style="border-top:1px solid #f0ebe3">
                <td style="padding:0.5rem 0;color:#7a6a5a">Origen</td>
                <td style="padding:0.5rem 0;color:#3d2b1f">{ref}</td>
            </tr>
            <tr style="border-top:1px solid #f0ebe3">
                <td style="padding:0.5rem 0;color:#7a6a5a;font-size:0.78rem">Session ID</td>
                <td style="padding:0.5rem 0;color:#7a6a5a;font-family:monospace;font-size:0.78rem">{session_id or "—"}</td>
            </tr>
        </table>
    """)
    return _send(to_email, f"Green. — Nueva visita desde {geo}", html)


def enviar_email_contacto(nombre: str, email: str, mensaje: str) -> bool:
    html = f"""
    <body style="font-family:'Jost',sans-serif;background:#f5f0e8;padding:2rem">
        <div style="max-width:560px;margin:0 auto;background:#fff;padding:2rem">
            <p style="font-size:0.75rem;letter-spacing:0.3em;text-transform:uppercase;color:#c4875a">Nueva consulta — Green.</p>
            <h2 style="font-family:'Georgia',serif;color:#3d2b1f;font-weight:300">{nombre}</h2>
            <p style="color:#7a6a5a">Email: {email}</p>
            <hr style="border:none;border-top:1px solid #e8ddd0;margin:1rem 0">
            <p style="color:#2c1f14;line-height:1.8">{mensaje}</p>
        </div>
    </body>"""
    try:
        resend.api_key = RESEND_API_KEY
        resend.Emails.send({
            "from": EMAIL_FROM,
            "to": "rleyrodiaz@hotmail.com",
            "reply_to": email,
            "subject": f"Green. — Consulta de {nombre}",
            "html": html,
        })
        return True
    except Exception as e:
        print(f"⚠️ Error email contacto: {e}")
        return False
