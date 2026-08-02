"""Devanagari city autosuggest (T1).

gazetteer.suggest() must match Hindi-script queries against the Devanagari
alternate names bundled in geonamescache plus the curated _HI_ALIASES table,
while the returned `name`/`label` stay English so the submitted value keeps
geocoding exactly as before.
"""
import gazetteer
import geocoding


def _names(q, limit=8):
    return [r["name"] for r in gazetteer.suggest(q, limit)]


# ---------------------------------------------------------------- Devanagari

def test_jaipur_devanagari():
    res = gazetteer.suggest("जयपुर", 8)
    assert res and res[0]["name"] == "Jaipur"
    # label stays English/Latin — this is what the client submits
    assert res[0]["label"].isascii()
    assert res[0]["label"] == "Jaipur, Rajasthan"


def test_mumbai_both_spellings():
    # anusvara (मुंबई) and conjunct (मुम्बई) spellings both resolve
    assert _names("मुंबई")[0] == "Mumbai"
    assert _names("मुम्बई")[0] == "Mumbai"


def test_delhi():
    names = _names("दिल्ली")
    assert names[0] == "Delhi"
    assert "New Delhi" in names


def test_nukta_insensitive():
    # ग़ with nukta and ग without both match Ghāziābād (fold strips nukta)
    assert _names("गाज़ियाबाद")[0] == "Ghāziābād"
    assert _names("गाजियाबाद")[0] == "Ghāziābād"


def test_alias_table_fills_geonames_gaps():
    # These have no usable Devanagari alternatename in geonames; the curated
    # _HI_ALIASES table provides them.
    assert _names("बेंगलुरु")[0] == "Bengaluru"   # geonames only has बंगलौर
    assert _names("ठाणे")[0] == "Thāne"
    assert _names("ग्वालियर")[0] == "Gwalior"
    assert _names("सूरत")[0] == "Surat"
    assert _names("इंदौर")[0] == "Indore"
    assert _names("प्रयागराज")[0] == "Prayagraj"


def test_devanagari_prefix():
    # 2-char Devanagari prefix suggests, population-ranked
    names = _names("जय")
    assert "Jaipur" in names[:3]


def test_devanagari_common_cities_top1():
    for q, expect in [("कानपुर", "Kanpur"), ("लखनऊ", "Lucknow"),
                      ("भोपाल", "Bhopal"), ("पटना", "Patna"),
                      ("वाराणसी", "Varanasi"), ("जोधपुर", "Jodhpur"),
                      ("हावड़ा", "Howrah"), ("कोलकाता", "Kolkata")]:
        names = _names(q)
        assert names and names[0] == expect, f"{q} -> {names[:3]}"


def test_short_or_empty_query():
    assert gazetteer.suggest("ज", 8) == []
    assert gazetteer.suggest("", 8) == []


# ------------------------------------------------------------ English intact

def test_english_regression():
    assert _names("jaipur")[0] == "Jaipur"
    assert _names("mumbai")[0] == "Mumbai"
    assert _names("delh")[0] == "Delhi"


def test_non_devanagari_non_latin_scripts_do_not_match():
    # the old alt filter leaked matra-free CJK/Katakana names; now closed
    assert gazetteer.suggest("シャイプル", 8) == []
    assert gazetteer.suggest("자이푸르", 8) == []


# ------------------------------------------------- end-to-end submit safety

def test_api_city_suggest_devanagari(client):
    r = client.get("/api/city-suggest", params={"q": "जयपुर"})
    assert r.status_code == 200
    results = r.json()["results"]
    assert results and results[0]["name"] == "Jaipur"
    assert results[0]["label"].isascii()
    # response schema unchanged
    assert {"id", "name", "label", "lat", "lon", "tz"} <= set(results[0])


def test_suggested_label_geocodes_offline(client, monkeypatch):
    """The label the client fills/submits must resolve WITHOUT the external
    geocoder and WITHOUT the Delhi fallback (guards the /api/milan path,
    which re-geocodes p1_place/p2_place server-side)."""
    monkeypatch.setenv("GEOCODER", "off")
    for q in ["जयपुर", "मुंबई", "ठाणे", "गाज़ियाबाद", "ग्वालियर", "हावड़ा"]:
        label = client.get("/api/city-suggest", params={"q": q}).json()["results"][0]["label"]
        d = geocoding.resolve_detailed(label)
        assert d["resolved"], f"{q} -> {label} fell back to Delhi"
        assert d["source"] != "default_delhi"
