"""Helpers — admin role checks, email token utils, PDF receipts, in-memory mailbox."""
import os
import logging
import secrets
from datetime import datetime, timezone, timedelta
from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

logger = logging.getLogger(__name__)

# Local mailbox keeps the latest dev emails so the UI can show admin a "what we sent" view.
EMAIL_LOG: list[dict] = []


def admin_email() -> str:
    return os.environ.get("ADMIN_EMAIL", "admin@expiremate.com").lower()


def admin_password() -> str:
    return os.environ.get("ADMIN_PASSWORD", "ExpireMate2026!")


def is_admin(user: dict) -> bool:
    return bool(user) and (user.get("role") == "admin" or user.get("email") == admin_email())


def make_token(prefix: str = "tk") -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def now_utc():
    return datetime.now(timezone.utc)


def send_dev_email(to: str, subject: str, body: str, link: str | None = None) -> dict:
    """Mock email — log the message and stash it in memory for the admin UI."""
    entry = {
        "to": to,
        "subject": subject,
        "body": body,
        "link": link,
        "sent_at": now_utc().isoformat(),
    }
    EMAIL_LOG.insert(0, entry)
    del EMAIL_LOG[200:]  # keep last 200
    logger.info(f"[DEV EMAIL] -> {to}  subj={subject}  link={link}")
    return entry


def build_receipt_pdf(*, donor_name: str, donor_email: str, amount: float,
                      currency: str, session_id: str, paid_at: str) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    w, h = letter

    c.setFillColorRGB(0.18, 0.37, 0.30)  # forest green
    c.rect(0, h - 1.2 * inch, w, 1.2 * inch, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(0.75 * inch, h - 0.7 * inch, "ExpireMate")
    c.setFont("Helvetica", 11)
    c.drawString(0.75 * inch, h - 0.95 * inch, "Donation receipt — thank you for keeping a student in school")

    c.setFillColorRGB(0.11, 0.10, 0.09)
    y = h - 1.8 * inch
    c.setFont("Helvetica-Bold", 14)
    c.drawString(0.75 * inch, y, "Receipt details")
    y -= 0.35 * inch
    c.setFont("Helvetica", 11)

    rows = [
        ("Donor", donor_name or "Anonymous"),
        ("Email", donor_email or "—"),
        ("Amount", f"${amount:,.2f} {currency.upper()}"),
        ("Payment ref", session_id),
        ("Date", paid_at),
    ]
    for label, value in rows:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(0.75 * inch, y, f"{label}:")
        c.setFont("Helvetica", 11)
        c.drawString(2.1 * inch, y, str(value))
        y -= 0.27 * inch

    y -= 0.4 * inch
    c.setFont("Helvetica-Oblique", 10)
    c.setFillColorRGB(0.34, 0.32, 0.30)
    for line in [
        "ExpireMate is a student-run platform. 100% of donations go directly to the founder's",
        "college fund (tuition, books, room & board). No goods or services were provided in exchange",
        "for this donation. Save this receipt for your records — consult a tax advisor regarding",
        "deductibility in your jurisdiction.",
    ]:
        c.drawString(0.75 * inch, y, line)
        y -= 0.2 * inch

    c.setFillColorRGB(0.88, 0.35, 0.28)
    c.rect(0, 0, w, 0.4 * inch, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.75 * inch, 0.16 * inch, "ExpireMate · expiremate.com · safety@expiremate.com")

    c.showPage()
    c.save()
    return buf.getvalue()
