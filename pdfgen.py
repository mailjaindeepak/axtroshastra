"""
pdfgen.py — beautiful (browser-quality) PDF generation via headless Chrome.

Why Chrome: the report pages are styled with modern CSS (custom properties,
flex/grid) that lightweight HTML→PDF libraries cannot reproduce. Headless
Chrome's --print-to-pdf uses the same engine as the browser print dialog, so
the output is identical to what a user gets from "Save as PDF" — which is the
quality bar the owner approved.

Design:
  * generate(html) -> bytes|None      render HTML to PDF (never raises)
  * cache_path(rid) / get_cached(rid) / save(rid, data)   disk cache under
    PDF_DIR (default ./data/pdfs). PDFs are pre-generated once per report by a
    background task right after payment; the download endpoint serves the file
    instantly. Cache is best-effort: if the file is missing (fresh deploy,
    disk wipe) the endpoint regenerates on demand.
  * A process-wide lock serializes Chrome runs — the production box has 1 GB
    RAM; one renderer at a time is the safe pattern.

Env:
  CHROME_BIN  path to the Chrome/Chromium binary. If unset, common locations
              are probed. When no binary is found generate() returns None and
              the client falls back to the print dialog (owner-approved UX).
  PDF_DIR     cache directory (default ./data/pdfs)
"""
import logging
import os
import subprocess
import tempfile
import threading

logger = logging.getLogger("axtroshastra.pdfgen")

BASE = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.getenv("PDF_DIR", os.path.join(BASE, "data", "pdfs"))

_CHROME_CANDIDATES = [
    os.getenv("CHROME_BIN", ""),
    "/usr/bin/chromium-browser", "/usr/bin/chromium", "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable", "/snap/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]
_TIMEOUT_S = 90
_lock = threading.Lock()          # one Chrome at a time (1 GB RAM box)


def chrome_bin() -> str:
    """First existing Chrome binary, or '' when none is installed."""
    for c in _CHROME_CANDIDATES:
        if c and os.path.exists(c):
            return c
    return ""


def generate(html: str) -> bytes | None:
    """Render HTML to a PDF with headless Chrome. Returns None on ANY failure
    (missing binary, crash, timeout) — callers treat None as 'fall back'."""
    chrome = chrome_bin()
    if not chrome:
        logger.warning("[pdf] no Chrome binary found (set CHROME_BIN)")
        return None
    tmp_html = tmp_pdf = None
    try:
        with _lock:
            fd, tmp_html = tempfile.mkstemp(suffix=".html")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(html)
            fd, tmp_pdf = tempfile.mkstemp(suffix=".pdf")
            os.close(fd)
            args = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
                    "--disable-dev-shm-usage", "--no-pdf-header-footer",
                    "--virtual-time-budget=10000",
                    f"--print-to-pdf={tmp_pdf}", f"file://{tmp_html}"]
            r = subprocess.run(args, capture_output=True, timeout=_TIMEOUT_S)
            if r.returncode != 0:                 # older Chrome: no --headless=new
                args[1] = "--headless"
                r = subprocess.run(args, capture_output=True, timeout=_TIMEOUT_S)
            if r.returncode != 0:
                logger.error("[pdf] chrome exit %s: %s", r.returncode,
                             r.stderr.decode(errors="replace")[-400:])
                return None
            with open(tmp_pdf, "rb") as f:
                data = f.read()
            if not data.startswith(b"%PDF"):
                logger.error("[pdf] chrome produced non-PDF output (%d bytes)", len(data))
                return None
            return data
    except Exception as e:                        # never raise into callers
        logger.error("[pdf] generation failed: %s", e)
        return None
    finally:
        for p in (tmp_html, tmp_pdf):
            if p:
                try:
                    os.unlink(p)
                except OSError:
                    pass


def cache_path(rid: str) -> str:
    safe = "".join(ch for ch in rid if ch.isalnum() or ch in "-_")
    return os.path.join(PDF_DIR, f"{safe}.pdf")


def get_cached(rid: str) -> bytes | None:
    try:
        p = cache_path(rid)
        if os.path.exists(p) and os.path.getsize(p) > 1024:
            with open(p, "rb") as f:
                return f.read()
    except OSError:
        pass
    return None


def save(rid: str, data: bytes) -> None:
    try:
        os.makedirs(PDF_DIR, exist_ok=True)
        tmp = cache_path(rid) + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, cache_path(rid))          # atomic — no half-written reads
    except OSError as e:
        logger.error("[pdf] cache save failed for %s: %s", rid, e)


def get_or_generate(rid: str, html: str) -> bytes | None:
    """Serve from cache, else render + cache. None => caller falls back."""
    data = get_cached(rid)
    if data:
        return data
    data = generate(html)
    if data:
        save(rid, data)
    return data
