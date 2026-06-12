"""Real email sender via Resend, with dev-log fallback when key absent."""
import os
import logging
import requests

logger = logging.getLogger(__name__)

EMAIL_LOG: list[dict] = []  # in-memory mailbox for admin Outbox view


def _from() -> str:
    return os.environ.get("RESEND_FROM", "ExpireMate <onboarding@resend.dev>")


def send_email(*, to: str, subject: str, html: str, link: str | None = None) -> dict:
    """Send via Resend if key present; always log to in-memory mailbox."""
    key = os.environ.get("RESEND_API_KEY")
    body_preview = html.replace("<br/>", "\n")[:240]
    entry = {
        "to": to, "subject": subject, "body": body_preview, "link": link,
        "sent_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "delivered": False, "provider": "mock",
    }
    if key:
        try:
            resp = requests.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"from": _from(), "to": [to], "subject": subject, "html": html},
                timeout=15,
            )
            entry["provider"] = "resend"
            if resp.status_code in (200, 202):
                entry["delivered"] = True
                entry["resend_id"] = resp.json().get("id")
            else:
                entry["error"] = f"{resp.status_code}: {resp.text[:200]}"
                logger.error(f"[resend] failed {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            entry["error"] = str(e)
            logger.error(f"[resend] exception: {e}")
    else:
        logger.info(f"[DEV EMAIL → {to}] {subject} link={link}")
    EMAIL_LOG.insert(0, entry)
    del EMAIL_LOG[200:]
    return entry


def render_action_email(*, heading: str, body: str, cta_text: str, cta_url: str) -> str:
    return f"""
<div style="font-family:-apple-system,Segoe UI,sans-serif;max-width:520px;margin:0 auto;padding:24px;background:#FAF9F6;color:#1C1917;">
  <div style="background:#E05A47;color:white;padding:18px 24px;border-radius:14px 14px 0 0;font-weight:700;font-size:20px;">ExpireMate</div>
  <div style="background:white;padding:24px;border-radius:0 0 14px 14px;border:1px solid #E5E0D8;border-top:none;">
    <h1 style="margin:0 0 12px;font-size:22px;">{heading}</h1>
    <p style="line-height:1.55;color:#57534E;margin:0 0 20px;">{body}</p>
    <a href="{cta_url}" style="display:inline-block;background:#E05A47;color:white;text-decoration:none;padding:12px 22px;border-radius:999px;font-weight:600;">{cta_text}</a>
    <p style="margin-top:24px;font-size:12px;color:#A8A29E;">Or paste this link in your browser:<br/><span style="word-break:break-all;">{cta_url}</span></p>
  </div>
  <p style="text-align:center;font-size:11px;color:#A8A29E;margin-top:14px;">© ExpireMate · Built by a high school student</p>
</div>"""


def render_zip_alert(*, item_title: str, item_url: str, category: str, days_left: int, zip_code: str) -> str:
    days = f"in {days_left} day{'s' if days_left != 1 else ''}" if days_left > 0 else "today"
    return render_action_email(
        heading=f"A new item just dropped in {zip_code}",
        body=f"<strong>{item_title}</strong> ({category}) expires {days}. First verified neighbor to claim, wins.",
        cta_text="Claim it →",
        cta_url=item_url,
    )
