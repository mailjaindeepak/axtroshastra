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


# ----------------------------------------------------- name_hi display polish

# Curated Devanagari DISPLAY name for the dropdown on *.hi.html pages.
# `label` must stay ASCII English — it is what the input is filled with and
# what the form submits/geocodes.

_MAJOR = [("दिल्ली", "Delhi", "दिल्ली"),
          ("मुंबई", "Mumbai", "मुंबई"),
          ("कोलकाता", "Kolkata", "कोलकाता"),
          ("बेंगलुरु", "Bengaluru", "बेंगलुरु"),
          ("जयपुर", "Jaipur", "जयपुर"),
          ("वाराणसी", "Varanasi", "वाराणसी"),
          ("लखनऊ", "Lucknow", "लखनऊ"),
          ("इंदौर", "Indore", "इंदौर"),
          ("पुणे", "Pune", "पुणे"),
          ("चेन्नई", "Chennai", "चेन्नई")]


def test_name_hi_present_for_major_cities():
    for q, name_en, name_hi in _MAJOR:
        res = gazetteer.suggest(q, 8)
        assert res and res[0]["name"] == name_en, f"{q} -> {[r['name'] for r in res[:3]]}"
        assert res[0].get("name_hi") == name_hi
        # label stays ASCII English regardless of name_hi
        assert res[0]["label"].isascii()
        assert res[0]["label"].startswith(name_en)


def test_name_hi_prefers_modern_common_form():
    # display table overrides archaic alias/geonames first forms
    assert gazetteer.suggest("मुंबई", 1)[0]["name_hi"] == "मुंबई"          # not ग्रेटर मुम्बई
    assert gazetteer.suggest("कोलकाता", 1)[0]["name_hi"] == "कोलकाता"     # not कलकत्ता
    assert gazetteer.suggest("वाराणसी", 1)[0]["name_hi"] == "वाराणसी"     # not काशी
    assert gazetteer.suggest("मंगलुरु", 1)[0]["name_hi"] == "मंगलुरु"       # not मंगलौर


def test_name_hi_omitted_for_uncurated_small_towns():
    # No curated name -> key omitted entirely (frontend falls back to English)
    for q in ["hodal", "bhabhua", "aonla"]:
        res = gazetteer.suggest(q, 8)
        assert res, q
        assert res[0].get("name_hi") is None
        assert "name_hi" not in res[0]


def test_name_hi_is_devanagari_label_is_latin_everywhere():
    # label stays Latin-script for every city (geonames names may carry
    # macrons, e.g. "Thāne" — Latin, but not strict ASCII); name_hi, when
    # present, is real Devanagari.
    gazetteer._load()
    for r in gazetteer._CITIES:
        p = gazetteer._public(r)
        assert not any("ऀ" <= ch <= "ॿ" for ch in p["label"]), p["label"]
        if "name_hi" in p:
            assert p["name_hi"] and any("ऀ" <= ch <= "ॿ" for ch in p["name_hi"])


# ------------------------------------------------- hi-page dropdown wiring

def _page(name):
    import pathlib
    return (pathlib.Path(__file__).resolve().parent.parent / "pages" / name).read_text(encoding="utf-8")


def test_hi_pages_render_name_hi_but_submit_english_label():
    """Static markers for the *.hi.html autosuggest: the dropdown row shows
    name_hi (fallback English name), but pick() still fills the input with the
    English c.label, so the submit guard (inp.value === picked.label) and the
    server-side re-geocode are untouched."""
    for name, guard in [("milan.hi.html", "inp.value.trim()!==sel.label"),
                        ("shaadi.hi.html", "inp.value.trim()!==selected.label")]:
        html = _page(name)
        assert "c.name_hi||c.name" in html, name          # row shows Hindi first
        assert "inp.value=c.label" in html, name          # pick fills English label
        assert guard in html, name                        # submit guard compares label


def test_english_pages_untouched_by_name_hi():
    for name in ["milan.html", "shaadi.html", "jeevan.html", "career.html", "career.hinglish.html"]:
        assert "name_hi" not in _page(name), name


# ------------------------------------------------- end-to-end submit safety

def test_api_city_suggest_devanagari(client):
    r = client.get("/api/city-suggest", params={"q": "जयपुर"})
    assert r.status_code == 200
    results = r.json()["results"]
    assert results and results[0]["name"] == "Jaipur"
    assert results[0]["label"].isascii()
    # response schema unchanged (plus curated name_hi for display)
    assert {"id", "name", "label", "lat", "lon", "tz"} <= set(results[0])
    assert results[0]["name_hi"] == "जयपुर"


def test_api_city_suggest_delhi_name_hi(client):
    r = client.get("/api/city-suggest", params={"q": "दिल्ली"})
    assert r.status_code == 200
    top = r.json()["results"][0]
    assert top["name"] == "Delhi"
    assert top["name_hi"] == "दिल्ली"
    assert top["label"] == "Delhi, India" and top["label"].isascii()


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
