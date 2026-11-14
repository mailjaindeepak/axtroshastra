"""The Numerology page opens only the real Razorpay checkout, secrets never reach the browser, and the set-up tools behave safely.
(The tools' logic is tested here with a stand-in Razorpay client; the genuine Test Mode payment itself needs the owner's keys: see docs/numerology-razorpay-test-mode.md.)"""
import importlib.util
import os
import re
import sys
import types

import pytest

import api

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PAGE = open(os.path.join(_ROOT, "pages", "numerology.html"), encoding="utf-8").read()


def _tool(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_the_page_loads_razorpays_own_checkout_script_like_every_other_report_page():
    assert '<script src="https://checkout.razorpay.com/v1/checkout.js" defer></script>' in _PAGE
    assert "new Razorpay({key:d.key_id,amount:d.amount,currency:d.currency,order_id:d.razorpay_order_id" in _PAGE      # all values come from our server's order
    assert "prefill:(PHONE?{contact:PHONE}:{})" in _PAGE and "theme:{color:'#C93B2E'}" in _PAGE


def test_no_demo_checkout_and_no_key_in_the_page_or_the_repo_code():
    low = _PAGE.lower()
    assert "__demo" not in low and "simulate" not in low and "window.confirm" not in low and "confirm('" not in low
    for f in ("pages/numerology.html", "numerology_viewer.py", "mulank_routes.py", "mulank_payment.py"):
        src = open(os.path.join(_ROOT, f), encoding="utf-8").read()
        assert not re.search(r"rzp_(test|live)_[A-Za-z0-9]{6,}", src), f
        assert not re.search(r"RAZORPAY_KEY_SECRET\s*=\s*['\"][^'\"]+['\"]", src), f


def test_the_order_response_carries_the_public_key_and_server_amount_never_a_secret(client, monkeypatch):
    import mulank_content as mc
    import numerology
    from datetime import date
    pin = date(2026, 11, 3)
    monkeypatch.setattr(mc, "_today", lambda: pin)
    E = numerology.compute_mulank(29, 7, 1990, today=pin)
    monkeypatch.setattr(mc, "REGISTRY", {k: mc.Entry(mc.OWNER_APPROVED, editor="E", approved_by="O", approved_on="2026-11-03") for k in mc.required_keys(E)})

    class _Rz:
        class order:
            @staticmethod
            def create(d):
                return {"id": "order_" + d["receipt"][-30:], "amount": d["amount"], "currency": d["currency"]}
    monkeypatch.setattr(api, "RZP_KEY", "rzp_test_publicid123456")
    monkeypatch.setattr(api, "RZP_SECRET", "super_secret_value_that_must_not_leak")
    monkeypatch.setattr(api, "rzp_client", lambda: _Rz())
    rid = client.post("/api/mulank", json={"name": "Priya Sharma", "dob": "1990-07-29", "country_code": "+91", "phone": "9433300001", "consent_terms": True}).json()["report_id"]
    r = client.post("/api/mulank/order", json={"report_id": rid, "amount": 1})
    assert r.status_code == 200 and r.json()["amount"] == 29900 and r.json()["currency"] == "INR" and r.json()["key_id"] == "rzp_test_publicid123456"
    assert "super_secret_value_that_must_not_leak" not in r.text


def test_the_page_says_so_when_checkout_is_not_configured_instead_of_faking_it(client, monkeypatch):
    import mulank_content as mc
    import numerology
    from datetime import date
    pin = date(2026, 11, 3)
    monkeypatch.setattr(mc, "_today", lambda: pin)
    E = numerology.compute_mulank(29, 7, 1990, today=pin)
    monkeypatch.setattr(mc, "REGISTRY", {k: mc.Entry(mc.OWNER_APPROVED, editor="E", approved_by="O", approved_on="2026-11-03") for k in mc.required_keys(E)})
    monkeypatch.setattr(api, "RZP_KEY", "")
    monkeypatch.setattr(api, "RZP_SECRET", "")
    rid = client.post("/api/mulank", json={"name": "Priya Sharma", "dob": "1990-07-29", "country_code": "+91", "phone": "9433300002", "consent_terms": True}).json()["report_id"]
    r = client.post("/api/mulank/order", json={"report_id": rid})
    assert r.status_code == 503 and "razorpay_order_id" not in r.text                  # no order, no popup, no pretend success
    assert "Checkout is not available right now" in _PAGE


# ------------------------------------------------------------------ set-up tools
def test_preflight_fails_without_keys_and_never_prints_a_secret(monkeypatch, capsys):
    for k in ("RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET", "PUBLIC_BASE_URL"):
        monkeypatch.delenv(k, raising=False)
    tool = _tool("check_razorpay")
    assert tool.main() == 1 and "RESULT: FAIL" in capsys.readouterr().out


def test_preflight_passes_in_test_mode_creating_one_299_order_and_prints_no_secret(monkeypatch, capsys):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_abcdef123456")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "s3cretvaluethatmustnotbeprinted")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "whsecretmustnotbeprinted")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://www.axtroshastra.com")
    made = []

    class Client:
        def __init__(self, auth):
            assert auth[0].startswith("rzp_test_")
            self.order = self

        def create(self, d):
            made.append(d)
            return {"id": "order_X1"}

        def fetch(self, oid):
            return {"id": oid, "amount": made[-1]["amount"], "currency": "INR", "status": "created"}
    monkeypatch.setitem(sys.modules, "razorpay", types.SimpleNamespace(Client=Client))
    tool = _tool("check_razorpay")
    assert tool.main() == 0
    out = capsys.readouterr().out
    assert "RESULT: PASS" in out and made and made[0]["amount"] == 29900 and made[0]["currency"] == "INR"
    assert "s3cretvaluethatmustnotbeprinted" not in out and "whsecretmustnotbeprinted" not in out


def test_preflight_never_creates_an_order_with_live_keys(monkeypatch, capsys):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_live_abcdef123456")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "s3cretvaluethatmustnotbeprinted")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "whsecretmustnotbeprinted")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://www.axtroshastra.com")
    monkeypatch.setitem(sys.modules, "razorpay", types.SimpleNamespace(Client=lambda auth: pytest.fail("a live key must never reach Razorpay from this tool")))
    tool = _tool("check_razorpay")
    tool.main()
    assert "SKIP  creating a Razorpay order" in capsys.readouterr().out


@pytest.mark.parametrize("key", ["", "rzp_live_abcdef123456", "notakey"])
def test_local_test_mode_refuses_anything_but_a_test_key(monkeypatch, capsys, key):
    monkeypatch.setenv("RAZORPAY_KEY_ID", key)
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "x" * 20)
    monkeypatch.setitem(sys.modules, "uvicorn", types.SimpleNamespace(run=lambda *a, **k: pytest.fail("must not start")))
    tool = _tool("local_test_mode")
    assert tool.main() == 2 and "Refusing to start" in capsys.readouterr().out
