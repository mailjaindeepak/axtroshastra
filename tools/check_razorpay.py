"""Preflight for the Numerology payment set-up. Run it with the Razorpay environment variables set (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET,
RAZORPAY_WEBHOOK_SECRET, PUBLIC_BASE_URL); it reads them from the environment or .env and never prints a secret.

    python tools/check_razorpay.py

It checks that the keys exist and which mode they are in, creates and reads back one real Razorpay TEST-mode order for Rs 299 (it refuses to
create anything with live keys), and exercises our own signature checks. It does not take a payment. Exit code 0 only if every check passes."""
import hashlib
import hmac
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "db"))                # db_v2 lives here, as in api.py

try:                                    # python-dotenv is optional: without it only real environment variables are read
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass

import mulank_payment as mp  # noqa: E402
import mulank_pricing  # noqa: E402

results = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append(ok)
    print(("PASS  " if ok else "FAIL  ") + name + (f"  ({detail})" if detail else ""))
    return ok


def main() -> int:
    key = os.getenv("RAZORPAY_KEY_ID", "")
    secret = os.getenv("RAZORPAY_KEY_SECRET", "")
    wh = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    base = os.getenv("PUBLIC_BASE_URL", "")
    mode = "test" if key.startswith("rzp_test_") else ("live" if key.startswith("rzp_live_") else "unknown")

    check("RAZORPAY_KEY_ID is set", bool(key) and mode != "unknown", f"mode: {mode}")
    check("RAZORPAY_KEY_SECRET is set", len(secret) >= 16)
    check("RAZORPAY_WEBHOOK_SECRET is set", len(wh) >= 8, "must match the secret entered on the Razorpay webhook")
    check("PUBLIC_BASE_URL is https", base.startswith("https://"), base or "not set")
    check("price is Rs 299 (29900 paise, INR)", mulank_pricing.MULANK_PRICE_PAISE == 29900)

    # our own verification code, using the real secrets but a locally computed signature
    if secret:
        oid, pid = "order_preflight", "pay_preflight"
        good = hmac.new(secret.encode(), f"{oid}|{pid}".encode(), hashlib.sha256).hexdigest()
        check("checkout signature check accepts a valid and rejects a bad signature",
              mp.signature_ok(secret, oid, pid, good) and not mp.signature_ok(secret, oid, pid, "0" * 64))
    if wh:
        body = b'{"event":"payment.captured"}'
        good = hmac.new(wh.encode(), body, hashlib.sha256).hexdigest()
        check("webhook signature check accepts a valid and rejects a bad signature",
              mp.webhook_signature_ok(wh, body, good) and not mp.webhook_signature_ok(wh, body, "0" * 64))

    if mode == "live":
        print("SKIP  creating a Razorpay order: live keys are present, so this tool will not create anything. Run it with rzp_test_ keys.")
    elif mode == "test" and secret:
        try:
            import razorpay
            client = razorpay.Client(auth=(key, secret))
            order = client.order.create({"amount": mulank_pricing.MULANK_PRICE_PAISE, "currency": "INR",
                                         "receipt": f"mk_preflight_{int(time.time())}", "payment_capture": 1})
            back = client.order.fetch(order["id"])
            check("Razorpay accepts the keys and creates a Rs 299 test order",
                  back.get("amount") == 29900 and back.get("currency") == "INR" and back.get("status") == "created", order["id"])
        except Exception as e:                       # the message can echo request data, so only the class and Razorpay's own error text are shown
            check("Razorpay accepts the keys and creates a Rs 299 test order", False, f"{e.__class__.__name__}: {str(e)[:120]}")
    print()
    print("RESULT: " + ("PASS" if all(results) else "FAIL") + f"  ({sum(results)}/{len(results)} checks)")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
