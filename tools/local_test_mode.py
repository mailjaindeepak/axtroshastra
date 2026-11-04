"""Run the real app on localhost so a genuine Razorpay TEST-mode payment can be made through the real checkout popup.

    python tools/local_test_mode.py            # then open http://127.0.0.1:8000/en/numerology

TEST ONLY. Because nothing is owner-approved yet, no customer can be offered the report. For this one local process only, every drafted content key is
treated as approved IN MEMORY so the unlock button appears; nothing is written to mulank_registry.json and nothing else changes. The payment path is the
real one: real Razorpay order, real checkout popup, real signature and amount verification, real webhook route. There is no stand-in gateway.

It refuses to start unless RAZORPAY_KEY_ID is a rzp_test_ key, and it only listens on 127.0.0.1. Never run it on a server."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

try:                                    # python-dotenv is optional: without it only real environment variables are read
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass


def main() -> int:
    key, secret = os.getenv("RAZORPAY_KEY_ID", ""), os.getenv("RAZORPAY_KEY_SECRET", "")
    if not key.startswith("rzp_test_") or not secret:
        print("Refusing to start: set RAZORPAY_KEY_ID (a rzp_test_ key) and RAZORPAY_KEY_SECRET in the environment or .env.\n"
              "Live keys are never accepted here. See docs/numerology-razorpay-test-mode.md.")
        return 2
    import uvicorn

    import api
    import mulank_content as mc

    mc.REGISTRY = {k: mc.Entry(mc.OWNER_APPROVED, editor="LOCAL TEST", approved_by="LOCAL TEST", approved_on="2026-01-01") for k in mc.load_ledger()}
    print("=" * 78)
    print("LOCAL TEST MODE. Razorpay TEST keys, real checkout. All content treated as approved in memory ONLY.")
    print("Open http://127.0.0.1:8000/en/numerology   (Ctrl+C to stop)")
    print("=" * 78)
    uvicorn.run(api.app, host="127.0.0.1", port=int(os.getenv("PORT", "8000")), log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
