"""ElectronicHub email service.
Sends transactional emails via Resend when RESEND_API_KEY is present,
otherwise falls back to console-only mode (logs email body to backend logs).
"""
import os, asyncio, logging
from typing import Optional

logger = logging.getLogger("emails")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "").strip()
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
BRAND_NAME = "ElectronicHub"

_resend = None
if RESEND_API_KEY:
    try:
        import resend as _resend_mod
        _resend_mod.api_key = RESEND_API_KEY
        _resend = _resend_mod
        logger.info("Resend email provider active")
    except Exception as e:
        logger.warning(f"Resend init failed, falling back to console: {e}")


async def send_email(to: str, subject: str, html: str) -> dict:
    """Send an email. Returns {'status', 'provider', 'id'?}."""
    if not to:
        return {"status": "skipped", "reason": "no recipient"}
    if not _resend:
        logger.info(f"[EMAIL:CONSOLE] to={to} subject={subject!r}")
        logger.info(f"[EMAIL:CONSOLE] body:\n{html[:2000]}")
        return {"status": "console", "provider": "console"}
    try:
        params = {"from": f"{BRAND_NAME} <{SENDER_EMAIL}>", "to": [to],
                  "subject": subject, "html": html}
        result = await asyncio.to_thread(_resend.Emails.send, params)
        logger.info(f"[EMAIL:RESEND] sent id={result.get('id')} to={to}")
        return {"status": "sent", "provider": "resend", "id": result.get("id")}
    except Exception as e:
        logger.error(f"[EMAIL:RESEND] failed to send to {to}: {e}")
        return {"status": "error", "provider": "resend", "error": str(e)}


def _wrap(inner_html: str) -> str:
    return f"""<!doctype html>
<html><body style="margin:0;padding:0;background:#050A0F;font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#F8FAFC;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#050A0F;padding:32px 0;">
  <tr><td align="center">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#0A1017;border:1px solid rgba(255,255,255,0.1);">
      <tr><td style="padding:24px 32px;border-bottom:1px solid rgba(255,255,255,0.1);">
        <div style="font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:0.25em;color:#00FF66;text-transform:uppercase;">ElectronicHub</div>
      </td></tr>
      <tr><td style="padding:32px;color:#F8FAFC;line-height:1.6;font-size:14px;">
        {inner_html}
      </td></tr>
      <tr><td style="padding:20px 32px;border-top:1px solid rgba(255,255,255,0.1);font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:0.2em;color:#64748B;text-transform:uppercase;text-align:center;">
        © 2026 ElectronicHub · Built for makers
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""


def _line_items_html(items: list) -> str:
    rows = ""
    for it in items:
        rows += f"""<tr>
          <td style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);color:#F8FAFC;font-size:13px;">
            <div>{it['name']}</div>
            <div style="color:#64748B;font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:0.1em;">{it['sku']} × {it['quantity']}</div>
          </td>
          <td align="right" style="padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);color:#00FF66;font-family:'JetBrains Mono',monospace;font-size:13px;">₹{it['line_total']:.0f}</td>
        </tr>"""
    return f"<table width='100%' cellpadding='0' cellspacing='0'>{rows}</table>"


async def send_order_confirmation(order: dict, recipient: str):
    short_id = order["id"][:8].upper()
    inner = f"""
      <h1 style="font-family:'Cabinet Grotesk','Inter',sans-serif;font-size:28px;font-weight:900;margin:0 0 8px;letter-spacing:-0.02em;">
        Order confirmed <span style="color:#00FF66;">✓</span>
      </h1>
      <p style="color:#94A3B8;margin:0 0 24px;">Thanks for shopping with ElectronicHub. We've received your order <b style="color:#F8FAFC;font-family:'JetBrains Mono',monospace;">#{short_id}</b> and it's being prepped for dispatch.</p>
      <div style="border:1px solid rgba(0,255,102,0.3);padding:16px;margin-bottom:24px;">
        <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:0.25em;color:#00FF66;text-transform:uppercase;margin-bottom:12px;">Order Summary</div>
        {_line_items_html(order['items'])}
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:12px;font-family:'JetBrains Mono',monospace;font-size:12px;color:#94A3B8;">
          <tr><td>Subtotal</td><td align="right">₹{order['subtotal']:.0f}</td></tr>
          {"<tr><td>Discount</td><td align='right' style='color:#00FF66;'>-₹" + f"{order['discount']:.0f}" + "</td></tr>" if order.get('discount') else ""}
          <tr><td>Shipping</td><td align="right">{'FREE' if order['shipping']==0 else '₹' + str(order['shipping'])}</td></tr>
          <tr><td>Tax (18% GST)</td><td align="right">₹{order['tax']:.0f}</td></tr>
          <tr><td style="padding-top:8px;border-top:1px solid rgba(255,255,255,0.1);color:#F8FAFC;font-size:14px;">Total</td>
              <td align="right" style="padding-top:8px;border-top:1px solid rgba(255,255,255,0.1);color:#00FF66;font-size:16px;">₹{order['total']:.0f}</td></tr>
        </table>
      </div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:0.25em;color:#00FF66;text-transform:uppercase;margin-bottom:8px;">Shipping To</div>
      <p style="color:#94A3B8;margin:0 0 24px;font-size:13px;">
        {order['address']['full_name']}<br>
        {order['address']['line1']}{', ' + order['address']['line2'] if order['address'].get('line2') else ''}<br>
        {order['address']['city']}, {order['address']['state']} {order['address']['pincode']}<br>
        {order['address']['country']} · {order['address']['phone']}
      </p>
      <p style="color:#94A3B8;font-size:13px;">You'll get another email as soon as your package ships. Questions? Just reply to this email.</p>
    """
    return await send_email(recipient, f"Order confirmed · #{short_id}", _wrap(inner))


async def send_shipping_notification(order: dict, recipient: str):
    short_id = order["id"][:8].upper()
    tracking = order.get("tracking_number") or "—"
    inner = f"""
      <h1 style="font-family:'Cabinet Grotesk','Inter',sans-serif;font-size:28px;font-weight:900;margin:0 0 8px;letter-spacing:-0.02em;">
        Your parts are on the way <span style="color:#00FF66;">→</span>
      </h1>
      <p style="color:#94A3B8;margin:0 0 24px;">Order <b style="color:#F8FAFC;font-family:'JetBrains Mono',monospace;">#{short_id}</b> just left our warehouse. Track it below.</p>
      <div style="border:1px solid rgba(0,255,102,0.3);padding:20px;margin-bottom:24px;text-align:center;">
        <div style="font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:0.25em;color:#00FF66;text-transform:uppercase;margin-bottom:8px;">Tracking Number</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:20px;color:#F8FAFC;letter-spacing:0.1em;">{tracking}</div>
      </div>
      <p style="color:#94A3B8;font-size:13px;">Typical delivery time: 3–5 business days. We'll email you once it's delivered.</p>
    """
    return await send_email(recipient, f"Shipped · #{short_id}", _wrap(inner))


async def send_delivered_notification(order: dict, recipient: str):
    short_id = order["id"][:8].upper()
    inner = f"""
      <h1 style="font-family:'Cabinet Grotesk','Inter',sans-serif;font-size:28px;font-weight:900;margin:0 0 8px;letter-spacing:-0.02em;">
        Delivered <span style="color:#00FF66;">✓</span>
      </h1>
      <p style="color:#94A3B8;margin:0 0 24px;">Order <b style="color:#F8FAFC;font-family:'JetBrains Mono',monospace;">#{short_id}</b> was delivered. Happy building!</p>
      <p style="color:#94A3B8;font-size:13px;">If anything is wrong with your order, reply to this email and we'll make it right.</p>
    """
    return await send_email(recipient, f"Delivered · #{short_id}", _wrap(inner))
