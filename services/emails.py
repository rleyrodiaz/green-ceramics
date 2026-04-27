import resend
from config.settings import RESEND_API_KEY, EMAIL_FROM

resend.api_key = RESEND_API_KEY


def _precio(n) -> str:
    return f"${float(n):,.0f}".replace(",", ".")


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
    """
    Envía email de confirmación al cliente.
    Retorna True si se envió correctamente.
    """
    resend.api_key = RESEND_API_KEY  # ← agregá esta línea
    items_html = "".join([
        f"""
        <tr>
            <td style="padding:0.75rem 0;border-bottom:1px solid #f0ebe3;
                       font-family:'Georgia',serif;color:#3d2b1f">
                {item['nombre']}
            </td>
            <td style="padding:0.75rem 0;border-bottom:1px solid #f0ebe3;
                       text-align:center;color:#7a6a5a">
                ×{item['cantidad']}
            </td>
            <td style="padding:0.75rem 0;border-bottom:1px solid #f0ebe3;
                       text-align:right;color:#3d2b1f">
                {_precio(item['subtotal'])}
            </td>
        </tr>
        """
        for item in items
    ])

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0;padding:0;background:#f5f0e8;font-family:'Jost',sans-serif;
                 font-weight:300;color:#2c1f14">

        <!-- Header -->
        <div style="background:#3d2b1f;padding:2rem 3rem;text-align:center">
            <p style="font-family:'Georgia',serif;font-size:2rem;font-weight:300;
                      letter-spacing:0.2em;color:#f5f0e8;margin:0">
                Green<span style="color:#c4875a">.</span>
            </p>
            <p style="font-size:0.75rem;letter-spacing:0.3em;text-transform:uppercase;
                      color:rgba(245,240,232,0.5);margin:0.5rem 0 0">
                Cerámica en Gres
            </p>
        </div>

        <!-- Body -->
        <div style="max-width:560px;margin:0 auto;padding:3rem 2rem">

            <p style="font-size:0.75rem;letter-spacing:0.3em;text-transform:uppercase;
                      color:#c4875a;margin-bottom:0.5rem">
                Pedido confirmado
            </p>
            <h1 style="font-family:'Georgia',serif;font-size:2rem;font-weight:300;
                       color:#3d2b1f;margin:0 0 1rem;line-height:1.2">
                ¡Gracias, {to_name}!
            </h1>
            <p style="color:#7a6a5a;line-height:1.8;margin-bottom:2rem">
                Recibimos tu pedido <strong style="color:#3d2b1f">#{order_id}</strong>.
                Nos ponemos en contacto para coordinar el envío.
            </p>

            <!-- Items -->
            <div style="background:#fff;padding:1.5rem 2rem;margin-bottom:1.5rem">
                <p style="font-size:0.7rem;letter-spacing:0.25em;text-transform:uppercase;
                           color:#c4875a;margin-bottom:1rem">
                    Tu pedido
                </p>
                <table style="width:100%;border-collapse:collapse">
                    <tbody>
                        {items_html}
                    </tbody>
                    <tfoot>
                        <tr>
                            <td colspan="2" style="padding:0.75rem 0;color:#7a6a5a;
                                                   font-size:0.85rem">Subtotal</td>
                            <td style="padding:0.75rem 0;text-align:right;
                                       color:#7a6a5a;font-size:0.85rem">
                                {_precio(subtotal)}
                            </td>
                        </tr>
                        <tr>
                            <td colspan="2" style="padding:0.75rem 0;color:#7a6a5a;
                                                   font-size:0.85rem">Envío</td>
                            <td style="padding:0.75rem 0;text-align:right;
                                       color:#7a6a5a;font-size:0.85rem">
                                {"Gratis" if shipping == 0 else _precio(shipping)}
                            </td>
                        </tr>
                        <tr style="border-top:1px solid #e8ddd0">
                            <td colspan="2" style="padding:1rem 0 0;
                                                   font-family:'Georgia',serif;
                                                   font-size:1.1rem;color:#3d2b1f">
                                Total
                            </td>
                            <td style="padding:1rem 0 0;text-align:right;
                                       font-family:'Georgia',serif;
                                       font-size:1.1rem;color:#3d2b1f">
                                {_precio(total)}
                            </td>
                        </tr>
                    </tfoot>
                </table>
            </div>

            <!-- Envío -->
            <div style="background:#fff;padding:1.5rem 2rem;margin-bottom:2rem">
                <p style="font-size:0.7rem;letter-spacing:0.25em;text-transform:uppercase;
                           color:#c4875a;margin-bottom:0.75rem">
                    Datos de envío
                </p>
                <p style="color:#3d2b1f;margin:0">{direccion}</p>
                <p style="color:#7a6a5a;font-size:0.9rem;margin:0.2rem 0 0">
                    {ciudad}, {provincia}
                </p>
            </div>

            <p style="color:#7a6a5a;font-size:0.85rem;line-height:1.8">
                ✦ Embalaje especial para cerámica<br>
                ✦ Te avisamos cuando tu pedido esté en camino<br>
                ✦ Ante cualquier consulta respondemos en 24-48hs
            </p>
        </div>

        <!-- Footer -->
        <div style="text-align:center;padding:2rem;border-top:1px solid #e8ddd0;
                    color:#7a6a5a;font-size:0.8rem;line-height:2">
            <p style="margin:0">Green. Cerámica en Gres</p>
            <p style="margin:0">hola@greenceramica.com · @green.ceramica</p>
            <p style="margin:0">Cada pieza es única e irrepetible</p>
        </div>

    </body>
    </html>
    """

    try:
        resend.Emails.send({
            "from":    EMAIL_FROM,
            "to":      to_email,
            "subject": f"Green. — Pedido #{order_id} confirmado",
            "html":    html,
        })
        return True
    except Exception as e:
        print(f"⚠️ Error enviando email: {e}")
        return False