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
import json
import logging
import os
import re
import subprocess
import tempfile
import threading
import time

logger = logging.getLogger("axtroshastra.pdfgen")

BASE = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.getenv("PDF_DIR", os.path.join(BASE, "data", "pdfs"))
FONTS_DIR = os.path.join(BASE, "static", "fonts")

_CHROME_CANDIDATES = [
    "/usr/bin/chromium-browser", "/usr/bin/chromium", "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable", "/snap/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]
_TIMEOUT_S = 45                   # < the ALB's 60s idle timeout: the client must
                                  # see a real 503, never a dead socket
_LOCK_PATIENCE_S = 5              # max wait for the render lock before giving up
_FAIL_TTL_S = 600                 # negative cache: don't re-render a failing rid
_lock = threading.RLock()         # one Chrome at a time (1 GB RAM box)
_failed: dict[str, float] = {}    # rid -> time.time() of last failed render


def chrome_bin() -> str:
    """First existing Chrome binary, or '' when none is installed.

    Probe order: explicit CHROME_BIN, then Playwright's browser store
    (PLAYWRIGHT_BROWSERS_PATH, default /opt/pw-browsers — the production
    Graviton/aarch64 box has no system chromium package, so .ebextensions
    installs Playwright's prebuilt chrome-headless-shell there), then system
    locations. The headless shell is probed BEFORE full desktop Chrome on
    purpose: desktop Chrome's --headless mode has been observed hanging >90s
    on report pages that the shell renders in ~1s."""
    import glob as _glob
    env_bin = os.getenv("CHROME_BIN", "")
    if env_bin and os.path.exists(env_bin):
        return env_bin
    roots = [os.getenv("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"),
             os.path.expanduser("~/.cache/ms-playwright"),
             os.path.expanduser("~/Library/Caches/ms-playwright")]
    for root in roots:
        for pat in ("chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell",
                    "chromium_headless_shell-*/chrome-headless-shell-mac*/chrome-headless-shell",
                    "chromium_headless_shell-*/chrome-linux/headless_shell",
                    "chromium-*/chrome-linux/chrome"):
            hits = sorted(_glob.glob(os.path.join(root, pat)))
            if hits:
                return hits[-1]                  # newest build wins
    for c in _CHROME_CANDIDATES:
        if c and os.path.exists(c):
            return c
    return ""


_FONT_LINK_RE = re.compile(
    r'<link\b[^>]*href="(https://fonts\.googleapis\.com/css2[^"]*)"[^>]*>')
_PRECONNECT_RE = re.compile(
    r'<link\b(?=[^>]*rel="preconnect")[^>]*href="https://fonts\.[^"]*"[^>]*>')


def _localize_fonts(html: str) -> str:
    """Replace remote Google Fonts <link>s with inline @font-face CSS pointing
    at the repo-bundled woff2 files in static/fonts (file:// URLs), so PDF
    rendering never depends on the network. Only the PDF path calls this —
    on-screen pages keep their webfont links. Unknown css2 URLs are left
    remote (graceful); never raises."""
    try:
        man_p = os.path.join(FONTS_DIR, "manifest.json")
        if not os.path.exists(man_p):
            return html
        with open(man_p, encoding="utf-8") as f:
            manifest = json.load(f)
        fonts_url = "file://" + FONTS_DIR.replace(os.sep, "/")

        def _repl(m):
            css_name = manifest.get(m.group(1))
            if not css_name:
                logger.warning("[pdf] no local fonts for %s — link left remote",
                               m.group(1))
                return m.group(0)
            try:
                with open(os.path.join(FONTS_DIR, css_name), encoding="utf-8") as f:
                    css = f.read()
            except OSError:
                return m.group(0)
            return "<style>" + css.replace("__FONTS__", fonts_url) + "</style>"

        out = _FONT_LINK_RE.sub(_repl, html)
        return _PRECONNECT_RE.sub("", out)
    except Exception as e:
        logger.error("[pdf] font localization failed: %s", e)
        return html


def generate(html: str) -> bytes | None:
    """Render HTML to a PDF with headless Chrome. Returns None on ANY failure
    (missing binary, busy renderer, crash, timeout) — callers treat None as
    'fall back'. Waits at most _LOCK_PATIENCE_S for the render lock: queueing
    behind a slow render past that only produces gateway timeouts."""
    chrome = chrome_bin()
    if not chrome:
        logger.warning("[pdf] no Chrome binary found (set CHROME_BIN)")
        return None
    html = _localize_fonts(html)
    if not _lock.acquire(timeout=_LOCK_PATIENCE_S):
        logger.warning("[pdf] renderer busy — skipping generation")
        return None
    tmp_html = tmp_pdf = None
    try:
        fd, tmp_html = tempfile.mkstemp(suffix=".html")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(html)
        fd, tmp_pdf = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        common = ["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage",
                  "--no-pdf-header-footer", "--virtual-time-budget=10000",
                  # _localize_fonts rewrites webfonts to file:// @font-face; the
                  # headless shell loads those as-is, but full desktop Chrome
                  # blocks file->file subresources without this flag.
                  "--allow-file-access-from-files",
                  f"--print-to-pdf={tmp_pdf}", f"file://{tmp_html}"]
        if "headless" in os.path.basename(chrome).replace("-", "_"):
            # chrome-headless-shell is headless by construction — no flag
            r = subprocess.run([chrome] + common, capture_output=True,
                               timeout=_TIMEOUT_S)
        else:
            args = [chrome, "--headless=new"] + common
            r = subprocess.run(args, capture_output=True, timeout=_TIMEOUT_S)
            if r.returncode != 0:             # older Chrome: no --headless=new
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
        _lock.release()
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
    """Serve from cache, else render + cache. None => caller falls back.

    Two guards keep one bad report from degrading everyone's downloads:
      * negative cache — a rid whose render just failed is not retried for
        _FAIL_TTL_S; each retry used to cost a full Chrome run under the
        global lock, stalling every other download behind it.
      * lock patience — if another render holds the lock for more than
        _LOCK_PATIENCE_S we return None (fall back) instead of queueing into
        a gateway timeout. A busy renderer does NOT negative-cache the rid:
        the content isn't at fault."""
    data = get_cached(rid)
    if data:
        return data
    now = time.time()
    ts = _failed.get(rid)
    if ts and now - ts < _FAIL_TTL_S:
        logger.info("[pdf] %s in failure cooldown (%.0fs left) — skipping",
                    rid, _FAIL_TTL_S - (now - ts))
        return None
    for k, t in list(_failed.items()):            # keep the dict from growing
        if now - t >= _FAIL_TTL_S:
            _failed.pop(k, None)
    if not _lock.acquire(timeout=_LOCK_PATIENCE_S):
        logger.warning("[pdf] renderer busy — %s falls back this time", rid)
        return None
    try:
        data = get_cached(rid)                    # rendered while we waited?
        if data:
            return data
        data = generate(html)                     # RLock: re-acquire is instant
    finally:
        _lock.release()
    if data:
        save(rid, data)
        _failed.pop(rid, None)
    else:
        _failed[rid] = time.time()
    return data
