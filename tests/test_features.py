"""Tests for the supporting feature modules: i18n, geocoding, ratelimit, payments."""
import os
import sqlite3
import tempfile

import i18n
import geocoding
import ratelimit
import payments


# ---- i18n -----------------------------------------------------------------
def test_i18n_translation_and_fallback():
    assert i18n.t("field.name", "en") == "Your name"
    assert i18n.t("field.name", "hi")  # Hindi authored
    # Unknown key falls back to the key itself
    assert i18n.t("no.such.key", "en") == "no.such.key"
    # Regional language inherits Hinglish until authored
    assert i18n.t("field.name", "ta") == i18n.t("field.name", "hi_en")


def test_i18n_normalize_lang():
    assert i18n.normalize_lang("HI-in") == "hi"
    assert i18n.normalize_lang("") == i18n.DEFAULT_LANG
    assert i18n.normalize_lang("xx") == i18n.DEFAULT_LANG


# ---- geocoding ------------------------------------------------------------
def test_geocode_known_city_no_network():
    lat, lon, tz = geocoding.resolve("Mumbai")
    assert round(lat) == 19 and tz == 5.5


def test_geocode_unknown_falls_back_to_delhi(monkeypatch):
    monkeypatch.setenv("GEOCODER", "off")           # disable external lookups
    assert geocoding.resolve("Nowhere-xyz-123") == geocoding.DELHI


# ---- ratelimit ------------------------------------------------------------
def test_rate_limiter_blocks_after_burst():
    ip = "203.0.113.9"
    allowed = sum(1 for _ in range(50) if ratelimit.allow(ip, "/api/kundli"))
    # policy capacity for /api/kundli is 10 -> only ~10 allowed in a burst
    assert allowed <= 12
    assert allowed >= 8


def test_captcha_disabled_returns_true(monkeypatch):
    monkeypatch.delenv("CAPTCHA_PROVIDER", raising=False)
    monkeypatch.delenv("CAPTCHA_SECRET", raising=False)
    assert ratelimit.captcha_ok("") is True


# ---- payments -------------------------------------------------------------
def _tmp_db():
    path = os.path.join(tempfile.mkdtemp(), "p.db")

    def db():
        return sqlite3.connect(path)
    return db


def test_webhook_idempotency():
    db = _tmp_db()
    payments.ensure_tables(db)
    evt = {"payload": {"payment": {"entity": {"id": "pay_ABC123"}}}}
    eid = payments.event_id_of(evt)
    assert eid == "pay_ABC123"
    assert payments.already_processed(db, eid) is False
    payments.mark_processed(db, eid, "payment.captured", "rid1")
    assert payments.already_processed(db, eid) is True


def test_reconcile_noop_without_razorpay(monkeypatch):
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)
    db = _tmp_db()
    payments.ensure_tables(db)
    res = payments.reconcile(db)
    assert res["recovered"] == 0
