"""Unit tests for pdfgen's reliability guards (T2 fix):
binary probe order, negative cache, lock patience, local font substitution,
and the client snippet's retry-before-fallback."""
import os
import threading
import time

import pytest

import pdfgen


@pytest.fixture(autouse=True)
def _clean_state(tmp_path, monkeypatch):
    """Isolate the on-disk cache and the in-memory negative cache per test."""
    monkeypatch.setattr(pdfgen, "PDF_DIR", str(tmp_path / "pdfs"))
    pdfgen._failed.clear()
    yield
    pdfgen._failed.clear()


# ---- chrome_bin probe order ------------------------------------------------

def _mk_shell(root):
    d = root / "chromium_headless_shell-9999" / "chrome-headless-shell-linux"
    d.mkdir(parents=True)
    p = d / "chrome-headless-shell"
    p.write_text("#!/bin/sh\n")
    return str(p)


def test_playwright_shell_probed_before_system_chrome(tmp_path, monkeypatch):
    """The headless shell must win over desktop Chrome: --headless desktop
    Chrome has been observed hanging >90s on report HTML the shell renders
    in ~1s (T2 root cause)."""
    shell = _mk_shell(tmp_path)
    fake_desktop = tmp_path / "Google Chrome"
    fake_desktop.write_text("")
    monkeypatch.delenv("CHROME_BIN", raising=False)
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
    monkeypatch.setattr(pdfgen, "_CHROME_CANDIDATES", [str(fake_desktop)])
    assert pdfgen.chrome_bin() == shell


def test_chrome_bin_env_override_wins(tmp_path, monkeypatch):
    shell = _mk_shell(tmp_path)
    override = tmp_path / "my-chrome"
    override.write_text("")
    monkeypatch.setenv("CHROME_BIN", str(override))
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path))
    assert pdfgen.chrome_bin() == str(override)
    assert shell  # the shell exists yet the explicit override still wins


def test_system_candidates_are_last_resort(tmp_path, monkeypatch):
    fake_desktop = tmp_path / "Google Chrome"
    fake_desktop.write_text("")
    monkeypatch.delenv("CHROME_BIN", raising=False)
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "empty"))
    monkeypatch.setattr(pdfgen, "_CHROME_CANDIDATES", [str(fake_desktop)])
    # patch the home-dir playwright stores away so only the candidate exists
    monkeypatch.setattr(os.path, "expanduser", lambda p: str(tmp_path / "nohome"))
    assert pdfgen.chrome_bin() == str(fake_desktop)


def test_timeout_stays_below_alb_idle_timeout():
    # The ALB kills idle connections at 60s; Chrome must give up first so the
    # client gets a real 503 (and its retry/fallback), never a dead socket.
    assert pdfgen._TIMEOUT_S < 60


# ---- negative cache + lock patience ---------------------------------------

def test_failed_render_is_not_retried_within_cooldown(monkeypatch):
    calls = []
    monkeypatch.setattr(pdfgen, "generate", lambda html: calls.append(1) or None)
    assert pdfgen.get_or_generate("rid-bad", "<html>") is None
    assert pdfgen.get_or_generate("rid-bad", "<html>") is None
    assert len(calls) == 1                       # second hit served from cooldown
    # a different rid is unaffected
    assert pdfgen.get_or_generate("rid-other", "<html>") is None
    assert len(calls) == 2


def test_success_after_cooldown_clears_the_flag(monkeypatch):
    monkeypatch.setattr(pdfgen, "generate", lambda html: None)
    assert pdfgen.get_or_generate("rid-x", "<html>") is None
    assert "rid-x" in pdfgen._failed
    pdfgen._failed["rid-x"] -= pdfgen._FAIL_TTL_S + 1     # cooldown expired
    pdf = b"%PDF-1.4 " + b"x" * 2048             # >1024 so get_cached serves it
    monkeypatch.setattr(pdfgen, "generate", lambda html: pdf)
    assert pdfgen.get_or_generate("rid-x", "<html>") == pdf
    assert "rid-x" not in pdfgen._failed
    assert pdfgen.get_or_generate("rid-x", "<html>") == pdf   # now cached on disk


def test_busy_renderer_falls_back_without_negative_cache(monkeypatch):
    monkeypatch.setattr(pdfgen, "_LOCK_PATIENCE_S", 0.05)
    monkeypatch.setattr(pdfgen, "generate",
                        lambda html: pytest.fail("must not render while busy"))
    grabbed = threading.Event()
    release = threading.Event()

    def hog():
        pdfgen._lock.acquire()
        grabbed.set()
        release.wait(5)
        pdfgen._lock.release()

    t = threading.Thread(target=hog)
    t.start()
    assert grabbed.wait(2)
    try:
        t0 = time.time()
        assert pdfgen.get_or_generate("rid-busy", "<html>") is None
        assert time.time() - t0 < 2              # gave up promptly, no queueing
        assert "rid-busy" not in pdfgen._failed  # busy is not the content's fault
    finally:
        release.set()
        t.join(5)


# ---- local fonts for the PDF path ------------------------------------------

HI_HEAD = ('<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
           '<link href="https://fonts.googleapis.com/css2?family=Mukta:wght@400;500;600;700;800'
           '&family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap" rel="stylesheet">')


def test_localize_fonts_inlines_local_devanagari_faces():
    html = f"<html><head>{HI_HEAD}</head><body>नमस्ते</body></html>"
    out = pdfgen._localize_fonts(html)
    assert "fonts.googleapis.com" not in out
    assert "fonts.gstatic.com" not in out        # preconnect stripped too
    assert "@font-face" in out
    assert "file://" in out and "Noto Sans Devanagari" in out
    # the woff2 files the CSS points at actually ship in the repo
    for m in __import__("re").finditer(r"url\(file://([^)]+\.woff2)\)", out):
        assert os.path.exists(m.group(1)), m.group(1)


def test_localize_fonts_leaves_unknown_urls_remote():
    html = ('<head><link href="https://fonts.googleapis.com/css2?family=Nope"'
            ' rel="stylesheet"></head>')
    out = pdfgen._localize_fonts(html)
    assert 'css2?family=Nope' in out             # unknown URL untouched


def test_generate_writes_localized_html(tmp_path, monkeypatch):
    """generate() must feed Chrome the font-localized HTML, not the original."""
    seen = {}

    def fake_run(args, **kw):
        src = [a for a in args if a.startswith("file://")][0][len("file://"):]
        seen["html"] = open(src, encoding="utf-8").read()
        pdf_out = [a for a in args if a.startswith("--print-to-pdf=")][0].split("=", 1)[1]
        with open(pdf_out, "wb") as f:
            f.write(b"%PDF-1.4 fake")
        class R:
            returncode = 0
            stderr = b""
        return R()

    monkeypatch.setattr(pdfgen, "chrome_bin", lambda: "/bin/echo")
    monkeypatch.setattr(pdfgen.subprocess, "run", fake_run)
    out = pdfgen.generate(f"<html><head>{HI_HEAD}</head><body>x</body></html>")
    assert out == b"%PDF-1.4 fake"
    assert "fonts.googleapis.com" not in seen["html"]
    assert "@font-face" in seen["html"]


# ---- client snippet retry ---------------------------------------------------

def test_download_snippet_retries_before_print_fallback():
    import api
    snip = api._AXDL_SNIPPET
    assert "attempt(1)" in snip                  # exactly one retry
    assert "retriesLeft" in snip
    assert "attempt(retriesLeft-1)" in snip
    assert "window.print()" in snip              # fallback preserved as last resort
    assert snip.index("retriesLeft>0") < snip.index("window.print()")
