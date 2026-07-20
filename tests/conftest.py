"""Shared pytest fixtures. Env is set BEFORE importing the app, because api.py
reads configuration at import time."""
import os
import tempfile

os.environ.setdefault("DEMO_MODE", "1")  # enables /api/_demo_pay for the escape test
# The whole suite shares one TestClient (=> one client IP), so the per-IP token
# bucket would throttle /api/kundli across unrelated tests. Disable the MIDDLEWARE
# here; the limiter algorithm itself is still unit-tested directly in test_features.
os.environ.setdefault("RATE_LIMIT_ENABLED", "0")
os.environ.setdefault("DB_PATH", os.path.join(tempfile.mkdtemp(), "reports.db"))
os.environ.setdefault("RAZORPAY_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("STATS_KEY", "test-stats-key")

import pytest
from fastapi.testclient import TestClient

import api


@pytest.fixture(scope="session")
def client():
    return TestClient(api.app)
