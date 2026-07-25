"""LLM narrative layer. All network is monkeypatched, so these run offline and
deterministically. We verify: off-by-default, provider switch, JSON parsing,
the facts-frozen guardrail (a section that alters a score is dropped), HTML
escaping, PII scrubbing, and that any failure falls back to {} (banks)."""
import json
import os

import narrative
import pytest


MILAN_PAYLOAD = {
    "product": "milan",
    "meta": {"p1": "Priya Sharma", "p2": "Arjun Verma",
             "_email": "priya@example.com", "phone": "+919812345678"},
    "total": 28, "max_total": 36, "verdict": "Shubh",
    "element": {"p1": "water", "p2": "earth", "text": "bank element text"},
    "kootas": [{"name": "Nadi", "score": 8, "max": 8, "text": "bank nadi"}],
}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("NARRATIVE_ENABLED", "NARRATIVE_PROVIDER", "NARRATIVE_MODEL",
              "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "NARRATIVE_LANG"):
        monkeypatch.delenv(k, raising=False)
    yield


def _fake_http(monkeypatch, captured, payload_obj):
    """Patch the single HTTP chokepoint to return a chosen provider response
    shaped like Anthropic or OpenAI, and record what would have been sent."""
    def fake(url, headers, body):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = body
        text = json.dumps(payload_obj)
        if "anthropic" in url:
            # our anthropic path prefills "{", so return the object WITHOUT it
            return {"content": [{"type": "text", "text": text[1:]}]}
        return {"choices": [{"message": {"content": text}}]}
    monkeypatch.setattr(narrative, "_http_post_json", fake)


def test_disabled_by_default_returns_empty(monkeypatch):
    _fake_http(monkeypatch, {}, {"combined_energy": "should not be used"})
    assert narrative.generate_narrative(MILAN_PAYLOAD) == {}


def test_claude_provider_generates_and_escapes(monkeypatch):
    monkeypatch.setenv("NARRATIVE_ENABLED", "1")
    monkeypatch.setenv("NARRATIVE_PROVIDER", "claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    cap = {}
    _fake_http(monkeypatch, cap, {
        "headline": "A warm & lucky match",
        "combined_energy": "Water <3 earth — naturally nourishing.",
    })
    out = narrative.generate_narrative(MILAN_PAYLOAD)
    assert out["headline"] == "A warm &amp; lucky match"        # escaped
    assert "&lt;3" in out["combined_energy"]                     # escaped
    assert "anthropic" in cap["url"]
    assert cap["headers"]["x-api-key"] == "sk-ant-test"


def test_openai_provider_switch(monkeypatch):
    monkeypatch.setenv("NARRATIVE_ENABLED", "1")
    monkeypatch.setenv("NARRATIVE_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-oai-test")
    cap = {}
    _fake_http(monkeypatch, cap, {"summary": "Lovely couple."})
    out = narrative.generate_narrative(MILAN_PAYLOAD)
    assert out["summary"] == "Lovely couple."
    assert "openai" in cap["url"]
    assert cap["headers"]["Authorization"] == "Bearer sk-oai-test"
    assert cap["body"]["response_format"] == {"type": "json_object"}


def test_pii_is_scrubbed_from_prompt(monkeypatch):
    monkeypatch.setenv("NARRATIVE_ENABLED", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    cap = {}
    _fake_http(monkeypatch, cap, {"headline": "hi"})
    narrative.generate_narrative(MILAN_PAYLOAD)
    sent = json.dumps(cap["body"])
    assert "priya@example.com" not in sent      # email dropped
    assert "+919812345678" not in sent          # phone dropped
    assert "Priya" in sent and "Sharma" not in sent   # first name only


def test_altered_score_section_is_dropped(monkeypatch):
    """The engine says Nadi 8/8. If the model writes '7/8' in a section, that
    section must be discarded (facts frozen), while clean sections survive."""
    monkeypatch.setenv("NARRATIVE_ENABLED", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    _fake_http(monkeypatch, {}, {
        "summary": "Your Nadi is a perfect 7/8, wonderful.",   # WRONG number -> dropped
        "headline": "A beautiful match",                        # clean -> kept
    })
    out = narrative.generate_narrative(MILAN_PAYLOAD)
    assert "summary" not in out
    assert out["headline"] == "A beautiful match"


def test_correct_score_in_prose_is_allowed(monkeypatch):
    monkeypatch.setenv("NARRATIVE_ENABLED", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    _fake_http(monkeypatch, {}, {"summary": "You scored 28/36 — Nadi 8/8, strong."})
    out = narrative.generate_narrative(MILAN_PAYLOAD)
    assert out["summary"] == "You scored 28/36 — Nadi 8/8, strong."


def test_missing_api_key_falls_back(monkeypatch):
    monkeypatch.setenv("NARRATIVE_ENABLED", "1")     # enabled but no key set
    out = narrative.generate_narrative(MILAN_PAYLOAD)
    assert out == {}


def test_bad_json_falls_back(monkeypatch):
    monkeypatch.setenv("NARRATIVE_ENABLED", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(narrative, "_http_post_json",
                        lambda u, h, b: {"content": [{"type": "text", "text": "not json"}]})
    assert narrative.generate_narrative(MILAN_PAYLOAD) == {}


def test_unknown_product_returns_empty(monkeypatch):
    monkeypatch.setenv("NARRATIVE_ENABLED", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    assert narrative.generate_narrative({"product": "mystery", "meta": {}}) == {}


def test_narr_accessor():
    assert narrative.narr({"narrative": {"x": "y"}}, "x") == "y"
    assert narrative.narr({}, "x") is None


def test_parse_json_strips_code_fences():
    assert narrative._parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert narrative._parse_json('prose {"a": 2} trailing') == {"a": 2}
