"""ops.config — env-var parsing must handle empty strings gracefully.

GitHub secrets that are SET but EMPTY (e.g. SMTP_PORT exists but has value "")
used to crash with ValueError on int(""). These tests guard the fix."""
import importlib
import os


def test_smtp_port_empty_string_uses_default(monkeypatch):
    monkeypatch.setenv("SMTP_PORT", "")
    import ops.config as cfg
    importlib.reload(cfg)
    assert cfg.SMTP_PORT == 587


def test_smtp_port_unset_uses_default(monkeypatch):
    monkeypatch.delenv("SMTP_PORT", raising=False)
    import ops.config as cfg
    importlib.reload(cfg)
    assert cfg.SMTP_PORT == 587


def test_smtp_port_explicit_value(monkeypatch):
    monkeypatch.setenv("SMTP_PORT", "465")
    import ops.config as cfg
    importlib.reload(cfg)
    assert cfg.SMTP_PORT == 465


def test_http_timeout_empty_string_uses_default(monkeypatch):
    monkeypatch.setenv("OPS_HTTP_TIMEOUT", "")
    import ops.config as cfg
    importlib.reload(cfg)
    assert cfg.HTTP_TIMEOUT == 25


def test_http_timeout_unset_uses_default(monkeypatch):
    monkeypatch.delenv("OPS_HTTP_TIMEOUT", raising=False)
    import ops.config as cfg
    importlib.reload(cfg)
    assert cfg.HTTP_TIMEOUT == 25


def test_http_timeout_explicit_value(monkeypatch):
    monkeypatch.setenv("OPS_HTTP_TIMEOUT", "10")
    import ops.config as cfg
    importlib.reload(cfg)
    assert cfg.HTTP_TIMEOUT == 10
