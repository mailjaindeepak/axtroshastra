"""
Report delivery: server-side PDF + email. (#7)

- `html_to_pdf(html)` renders a report's HTML to PDF bytes. Prefers WeasyPrint
  (best fidelity) if installed, else falls back to xhtml2pdf (pure-pip). Returns
  None if neither is available, so callers can degrade to the print-to-PDF button.
- `send_email(...)` sends the report link (and optional PDF attachment) over SMTP,
  env-gated: a no-op that returns False until SMTP is configured.

Env:
  SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD
  SMTP_FROM            from-address (defaults to SMTP_USER)
  SMTP_STARTTLS        "1" (default) | "0"
"""
import os
import smtplib
from email.message import EmailMessage


def html_to_pdf(html: str) -> bytes | None:
    """Render HTML -> PDF bytes. Returns None if no renderer is installed."""
    try:
        from weasyprint import HTML  # type: ignore
        return HTML(string=html).write_pdf()
    except Exception:
        pass
    try:
        from io import BytesIO
        from xhtml2pdf import pisa  # type: ignore
        buf = BytesIO()
        result = pisa.CreatePDF(src=html, dest=buf)
        if result.err:
            return None
        return buf.getvalue()
    except Exception:
        return None


def email_configured() -> bool:
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USER")
                and os.getenv("SMTP_PASSWORD"))


def send_email(to_addr: str, subject: str, body: str,
               pdf_bytes: bytes | None = None, pdf_name: str = "report.pdf") -> bool:
    """Send an email, optionally with a PDF attachment. False if not configured."""
    if not (email_configured() and to_addr):
        return False
    msg = EmailMessage()
    msg["From"] = os.getenv("SMTP_FROM") or os.getenv("SMTP_USER")
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    if pdf_bytes:
        msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf",
                           filename=pdf_name)
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    try:
        with smtplib.SMTP(host, port, timeout=15) as s:
            if os.getenv("SMTP_STARTTLS", "1") == "1":
                s.starttls()
            s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
            s.send_message(msg)
        return True
    except Exception:
        return False
