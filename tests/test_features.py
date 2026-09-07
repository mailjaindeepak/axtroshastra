"""Tests for the supporting feature modules: i18n, geocoding, ratelimit, payments."""
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
def test_event_id_of_extracts_payment_entity_id():
    """event_id_of (still used by the v2 webhook for idempotency) reads the payment
    entity id, else falls back to the top-level event id. The v1 primitives
    (webhook_events dedupe / reconcile) were retired with the cutover — their behaviour
    is now covered on real MySQL by db/test_payments_v2 + db/test_payment_recovery."""
    assert payments.event_id_of(
        {"payload": {"payment": {"entity": {"id": "pay_ABC123"}}}}) == "pay_ABC123"
    assert payments.event_id_of({"id": "evt_1"}) == "evt_1"
    assert payments.event_id_of({}) == ""
