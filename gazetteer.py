"""
Offline city gazetteer for Axtroshastra — autosuggest + exact resolution.

Backed by the bundled `geonamescache` dataset (~32k cities, population > 15k, worldwide),
so there is NO external API, no key, no network at deploy. Each city carries real
lat/lon and an IANA timezone. Replaces open-text geocoding + the Delhi fallback.

Public API:
  suggest(q, limit=8)      -> ranked list of dicts (autosuggest)
  resolve(geonameid)       -> single city dict or None
  tz_offset_hours(iana, local_dt) -> float UTC offset AT that date (handles DST/historical)

Each city dict: {id, name, label, country, cc, lat, lon, tz, pop}
`label` is display-ready, e.g. "Hyderabad, India" (disambiguates cross-border duplicates).
"""
from datetime import datetime
import unicodedata

_STATE = {"01": "Andaman & Nicobar", "02": "Andhra Pradesh", "03": "Assam", "05": "Chandigarh", "07": "Delhi", "09": "Gujarat", "10": "Haryana", "11": "Himachal Pradesh", "12": "Jammu & Kashmir", "13": "Kerala", "16": "Maharashtra", "17": "Manipur", "18": "Meghalaya", "19": "Karnataka", "20": "Nagaland", "21": "Odisha", "22": "Puducherry", "23": "Punjab", "24": "Rajasthan", "25": "Tamil Nadu", "26": "Tripura", "28": "West Bengal", "29": "Sikkim", "30": "Arunachal Pradesh", "31": "Mizoram", "33": "Goa", "34": "Bihar", "35": "Madhya Pradesh", "36": "Uttar Pradesh", "37": "Chhattisgarh", "38": "Jharkhand", "39": "Uttarakhand", "40": "Telangana", "41": "Ladakh", "52": "Dadra & Nagar Haveli and Daman & Diu"}

_CITIES = None          # loaded once
_BY_ID = None
_COUNTRY = None
_NAME_IDX = None        # ascii-folded name/alias -> best (highest-pop) row

# Suggest at city/district level, not sub-locality. MIN_POP drops tiny places;
# _LOCALITY_RE drops cantonment/sub-locality entries that survive on population
# alone (e.g. "Delhi Cantonment" ~1.1 lakh). Tune MIN_POP to trade clutter vs
# coverage of smaller birth-towns.
import re
MIN_POP = 15000
_LOCALITY_RE = re.compile(r"\b(cantonment|cantt)\b", re.I)

# Geonameids kept even below MIN_POP because they are the representative/known
# city for an area users search by a broader name (e.g. Mapusa is a well-known
# Goa town below the population floor but reachable via मापुसा / "Goa").
_KEEP_IDS = {
    1263580,   # Mapusa (Goa), pop ~40k < MIN_POP
}


def _ascii(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c)).lower().strip()


def _has_devanagari(s: str) -> bool:
    return any("ऀ" <= ch <= "ॿ" for ch in s)


# Hand-curated Devanagari aliases, keyed by geonameid (stable across dataset
# updates). Fills the gaps where the geonames alternatenames carry no Devanagari
# spelling (70 of the top-200 Indian cities by population), plus common modern
# spellings geonames lacks (e.g. बेंगलुरु — geonames only has बंगलौर).
# Values are RAW Devanagari (nukta/halant included); they are folded through
# _ascii() at load so matching tolerates nukta and conjunct variants.
# Source: Hindi Wikipedia article titles for each city.
_HI_ALIASES = {
    # ---- top-200 cities with no Devanagari alternatename in geonames ----
    1254661: ["ठाणे", "थाने"],                    # Thāne
    1258393: ["रासापूडिपालेम"],                    # Rasapūdipalem (Vizag metro)
    12165956: ["कल्लाकुरिची"],                     # Kallakurichi
    1258847: ["राजकोट"],                          # Rājkot
    1270926: ["गोरखपुर"],                         # Gorakhpur
    1268295: ["कल्याण"],                          # Kalyān
    1253133: ["विरार"],                           # Virār
    1261162: ["नबरंगपुर", "नवरंगपुर"],              # Nowrangapur
    1271308: ["गाज़ियाबाद", "गाजियाबाद"],           # Ghāziābād
    1270583: ["ग्वालियर"],                         # Gwalior
    1254745: ["तेनी", "थेनी"],                     # Teni / Theni
    1270396: ["हावड़ा", "हौरा"],                    # Howrah
    6943660: ["शिवाजी नगर"],                      # Shivaji Nagar (Pune)
    1269920: ["हुबली", "हुब्बल्ली"],                # Hubballi / Hubli
    12069922: ["रोहिणी"],                         # Rohini (Delhi)
    12501153: ["कनयन्नूर"],                        # Kanayannur
    1261809: ["नरेला"],                           # Narela (Delhi)
    1262801: ["मुरादाबाद"],                        # Morādābād
    1257416: ["सांगली", "सांगली-मिरज"],             # Sāngli
    1275362: ["बोकारो"],                          # Bokāro
    1266285: ["कोल्हापुर"],                        # Kolhāpur
    1275610: ["बिलिमोरा"],                        # Bilimora
    1267696: ["करोल बाग", "करोल बाग़"],            # Karol Bāgh
    1257806: ["सहारनपुर"],                        # Sahāranpur
    1276058: ["भाटपाड़ा"],                        # Bhātpāra
    1264115: ["मालेगांव", "मालेगाँव"],              # Malegaon
    1271439: ["गया"],                             # Gaya
    1278840: ["अंबत्तूर"],                         # Ambattur
    1258662: ["रामगुंडम"],                        # Rāmgundam
    1348843: ["महेशतला"],                         # Maheshtala
    1260107: ["पटियाला"],                         # Patiāla
    1256409: ["श्यामनगर"],                        # Shyamnagar
    1273368: ["दावणगेरे", "दावनगेरे"],              # Davangere
    1255783: ["राजपुर सोनारपुर"],                  # Rajpur Sonarpur
    1269006: ["झांसी", "झाँसी"],                   # Jhānsi
    1276300: ["भागलपुर"],                         # Bhāgalpur
    1268561: ["काकीनाडा"],                        # Kākināda
    1260482: ["पानीहाटी"],                        # Pānihāti
    1258932: ["राजमहेंद्रवरम", "राजमुंदरी"],         # Rajamahendravaram
    1275637: ["बिलासपुर"],                        # Bilāspur
    1275960: ["भीलवाड़ा"],                        # Bhilwara
    1259239: ["पुनासा"],                          # Punāsa
    1278130: ["अवडी", "आवडी"],                    # Avadi
    1273800: ["कडपा", "कड़पा"],                    # Kadapa
    1268257: ["कामारहाटी"],                       # Kāmārhāti
    1256728: ["शाहजहांपुर", "शाहजहाँपुर"],          # Shāhjānpur
    1268773: ["जूनागढ़"],                          # Jūnāgadh
    1254187: ["त्रिशूर", "त्रिस्सूर"],               # Thrissur
    1261258: ["निजामाबाद", "निज़ामाबाद"],           # Nizāmābād
    1254089: ["तुमकुर", "तुमकूर", "तुमकुरु"],        # Tumkūr
    1271885: ["फिरोजाबाद", "फ़िरोज़ाबाद"],          # Fīrozābād
    1265711: ["कुल्टी"],                           # Kulti
    1267708: ["करनाल"],                           # Karnāl
    1277029: ["बर्धमान", "वर्धमान"],                # Barddhamān
    11679708: ["गुंडुपालयम"],                      # Gundupālaiyam
    1277065: ["बारासात", "बारासत"],                # Bārāsat
    12165955: ["मुलुगु"],                          # Mulugu
    1275716: ["बिहार शरीफ", "बिहारशरीफ"],          # Bihār Sharīf
    1277539: ["बाली"],                            # Bāli (WB)
    1258599: ["रामपुर"],                          # Rāmpur
    1260476: ["पानीपत"],                          # Panipat
    1267755: ["करीमनगर"],                         # Karīmnagar
    1255744: ["सोनीपत"],                          # Sonīpat
    1269395: ["जालना"],                           # Jālna
    10263153: ["किराड़ी सुलेमान नगर", "किराड़ी"],    # Kirāri Sulemānnagar
    1257022: ["सतना"],                            # Satna
    12032137: ["कुशीनगर"],                        # Kushinagar
    1258342: ["रतलाम"],                           # Ratlām
    1258451: ["रानीपेट"],                          # Rānipet
    7302826: ["लाल बहादुर नगर"],                   # Lal Bahadur Nagar
    # ---- common modern spellings missing from geonames Devanagari alts ----
    1255364: ["सूरत"],                            # Surat (geonames: सुरत only)
    1269743: ["इंदौर"],                           # Indore (geonames: इन्दौर/इंदूर)
    1278994: ["प्रयागराज", "प्रयाग"],               # Prayagraj (geonames: इलाहाबाद)
    1277333: ["बेंगलुरु", "बेंगलूरु", "बैंगलोर"],     # Bengaluru (geonames: बंगलौर)
    1257629: ["सलेम"],                            # Salem (geonames: सेलम)
    1263780: ["मंगलौर", "मंगलुरु"],                # Mangaluru (geonames: मंगळूर)
    1265873: ["कोझिकोड", "कालीकट"],               # Kozhikode (geonames: कोळिकोड)
    1276533: ["बेलगाम"],                          # Belagavi (geonames: बेलगांव)
    1271715: ["गांधीनगर"],                        # Gandhinagar (geonames: गान्धीनगरम्)
    1276070: ["भटिंडा"],                          # Bathinda (geonames: बठिंडा)
    1256436: ["सोलापुर", "शोलापुर"],               # Sholapur (geonames: सोलापूर)
    1256320: ["सीकर"],                            # Sīkar
    1271942: ["फर्रुखाबाद"],                       # Farrukhābād
    1271987: ["इटावा"],                           # Etāwah
    1278860: ["अंबाला", "अम्बाला"],                 # Ambāla
    # ---- Goa: "Goa" is a STATE, not a city; the real cities sit under other
    # names with no Devanagari alt. Map गोवा/गोआ to the capital Panaji (Panjim),
    # and give each main Goa city a typeable Devanagari spelling. ----
    1260607: ["गोवा", "गोआ", "पणजी"],              # Panjim (Panaji) — Goa capital
    1264588: ["मडगांव", "मारगांव"],                 # Madgaon (Margao)
    1253367: ["वास्को द गामा", "वास्को"],            # Vasco da Gama
    1263494: ["मुरगांव"],                          # Mormugao
    1263580: ["मापुसा"],                          # Mapusa
}


# Curated Latin-script aliases treated at NAME priority (so they outrank a
# same-or-lower-population city whose real name merely shares the prefix).
# "Goa" is a state with no city of that name, so 'goa' should surface the Goa
# capital (Panjim) — not Goālpāra in Assam, which merely starts with "goa".
_EN_ALIASES = {
    1260607: ["goa"],                            # Panjim (Panaji) — Goa capital
}


# Curated Hindi DISPLAY names, keyed by geonameid — the `name_hi` shown in the
# dropdown on the Hindi (*.hi.html) pages. Display-only: `name`/`label` stay
# English so the submitted value keeps geocoding exactly as before.
# Prefer the modern common name (मुंबई not ग्रेटर मुम्बई, कोलकाता not कलकत्ता,
# वाराणसी not काशी). Cities NOT here fall back to the first _HI_ALIASES entry
# (curated from Hindi Wikipedia titles, so its first form is display-ready);
# entries below also OVERRIDE aliases whose first form is archaic (मंगलौर,
# बेलगाम). No curated name at all -> name_hi omitted, frontend shows English.
_HI_DISPLAY = {
    1275339: "मुंबई",             # Mumbai
    1273294: "दिल्ली",             # Delhi
    1261481: "नई दिल्ली",          # New Delhi
    1269843: "हैदराबाद",           # Hyderabad
    1279233: "अहमदाबाद",          # Ahmedabad
    1264527: "चेन्नई",             # Chennai
    1275004: "कोलकाता",           # Kolkata (not कलकत्ता)
    1259229: "पुणे",               # Pune
    1269515: "जयपुर",             # Jaipur
    1267995: "कानपुर",            # Kanpur
    6619347: "नवी मुंबई",          # Navi Mumbai
    1264733: "लखनऊ",             # Lucknow
    1262180: "नागपुर",             # Nagpur
    1273865: "कोयंबटूर",           # Coimbatore
    1253573: "वडोदरा",            # Vadodara
    1275841: "भोपाल",             # Bhopal
    7626690: "पिंपरी-चिंचवड",       # Pimpri-Chinchwad
    1259652: "पिंपरी",             # Pimpri
    1260086: "पटना",              # Patna
    1264728: "लुधियाना",           # Ludhiana
    1261731: "नासिक",             # Nashik
    1264521: "मदुरै",              # Madurai
    1254361: "तिरुनेलवेली",         # Tirunelveli
    1279259: "आगरा",              # Agra
    1271951: "फरीदाबाद",          # Faridabad
    1262111: "नजफगढ़",            # Najafgarh
    1269300: "जमशेदपुर",          # Jamshedpur
    1272423: "डोंबिवली",           # Dombivali
    1263214: "मेरठ",              # Meerut
    1255634: "श्रीनगर",            # Srinagar
    1272979: "धनबाद",             # Dhanbad
    1278149: "औरंगाबाद",          # Aurangabad
    1253405: "वाराणसी",           # Varanasi (not काशी/बनारस)
    1278710: "अमृतसर",            # Amritsar
    1253184: "विजयवाड़ा",          # Vijayawada
    1258526: "रांची",              # Ranchi
    1269633: "जबलपुर",            # Jabalpur
    1253102: "विशाखापत्तनम",       # Visakhapatnam
    1268865: "जोधपुर",            # Jodhpur
    1258980: "रायपुर",             # Raipur
    1254388: "तिरुचिरापल्ली",       # Tiruchirappalli
    1266049: "कोटा",              # Kota
    1274746: "चंडीगढ़",            # Chandigarh
    1254348: "तिरुपुर",            # Tiruppur
    1271476: "गुवाहाटी",           # Guwahati
    1262321: "मैसूर",              # Mysuru
    1270642: "गुरुग्राम",           # Gurugram
    1275817: "भुवनेश्वर",           # Bhubaneswar
    1275901: "भिवंडी",             # Bhiwandi
    1268782: "जालंधर",            # Jalandhar
    1276014: "भायंदर",            # Bhayandar
    1254163: "तिरुवनंतपुरम",        # Thiruvananthapuram
    1279017: "अलीगढ़",            # Aligarh
    1277013: "बरेली",              # Bareilly
    1252948: "वारंगल",            # Warangal
    1270927: "गोरखपुर",           # Gorakhpur (second geonames entry)
    1270668: "गुंटूर",              # Guntur
    1259425: "पुडुचेरी",            # Puducherry
    1278718: "अमरावती",           # Amravati
    1275665: "बीकानेर",            # Bikaner
    1273874: "कोच्चि",             # Kochi
    1275971: "भिलाई",             # Bhilai
    1273780: "कटक",               # Cuttack
    1275248: "बोरीवली",            # Borivli
    1276032: "भावनगर",            # Bhavnagar
    1269317: "जामनगर",            # Jamnagar
    1269321: "जम्मू",              # Jammu
    1261977: "नांदेड़",             # Nanded
    1261529: "नेल्लोर",             # Nellore
    1270752: "कलबुर्गी",            # Kalaburagi
    1279159: "अजमेर",             # Ajmer
    1273313: "देहरादून",            # Dehra Dun
    1272013: "इरोड",              # Erode
    1272175: "दुर्गापुर",            # Durgapur
    1253894: "उल्हासनगर",          # Ulhasnagar
    1256525: "सिलीगुड़ी",           # Siliguri
    1253914: "उज्जैन",             # Ujjain
    1278314: "आसनसोल",           # Asansol
    1253286: "वेल्लोर",             # Vellore
    1269407: "जलगांव",            # Jalgaon
    1265491: "कुरनूल",             # Kurnool
    1253986: "उदयपुर",            # Udaipur
    1279105: "अकोला",             # Akola
    1266122: "कोरबा",             # Korba
    8629640: "थूथुकुडी",            # Thoothukudi
    1276509: "बल्लारी",            # Ballari
    1279290: "अगरतला",            # Agartala
    1258076: "रोहतक",             # Rohtak
    1262330: "मुजफ्फरपुर",          # Muzaffarpur
    1263364: "मथुरा",             # Mathura
    1278946: "अलवर",              # Alwar
    1273491: "दरभंगा",             # Darbhanga
    1254360: "तिरुपति",            # Tirupati
    7279746: "नोएडा",             # Noida
    1273066: "देवास",              # Dewas
    1269771: "इंफाल",             # Imphal
    1256237: "शिमला",             # Shimla
    # ---- overrides: alias list starts with an archaic form ----
    1263780: "मंगलुरु",            # Mangaluru (alias first entry: मंगलौर)
    1276533: "बेलगावी",            # Belagavi  (alias first entry: बेलगाम)
    # ---- Goa cities (name stays English; Devanagari shown on *.hi.html) ----
    1260607: "पणजी",              # Panjim (Panaji) — Goa capital
    1264588: "मडगांव",             # Madgaon (Margao)
    1253367: "वास्को द गामा",       # Vasco da Gama
    1263494: "मुरगांव",            # Mormugao
    1263580: "मापुसा",             # Mapusa
}


def _load():
    global _CITIES, _BY_ID, _COUNTRY
    if _CITIES is not None:
        return
    from geonamescache import GeonamesCache
    gc = GeonamesCache()
    _COUNTRY = {c["iso"]: c["name"] for c in gc.get_countries().values()}
    rows = []
    for c in gc.get_cities().values():
        name = c["name"]
        cc = c.get("countrycode", "")
        if cc != "IN":            # India-only for now: hide foreign cities (avoids confusion)
            continue
        pop = int(c.get("population", 0) or 0)
        if pop < MIN_POP and c["geonameid"] not in _KEEP_IDS:   # keep city/district level — drop tiny localities
            continue
        if _LOCALITY_RE.search(name):   # drop cantonment / sub-locality entries
            continue
        # Latin alternate names for Roman-script queries; Devanagari alternate
        # names (folded through _ascii: nukta/halant stripped, matras kept) for
        # Devanagari queries. Other scripts (CJK etc.) are dropped.
        alts, alts_hi = set(), set()
        for a in c.get("alternatenames", []) or []:
            if _has_devanagari(a):
                fa = _ascii(a)
                if fa:
                    alts_hi.add(fa)
                continue
            aa = _ascii(a)
            if aa and aa.isascii() and all(ch.isalpha() or ch in " .-" for ch in aa):
                alts.add(aa)
        for a in _HI_ALIASES.get(c["geonameid"], []):
            alts_hi.add(_ascii(a))
        # Curated Latin-script aliases matched at name priority (see _EN_ALIASES).
        alts_en = {fa for a in _EN_ALIASES.get(c["geonameid"], []) if (fa := _ascii(a))}
        # Curated Hindi display name: explicit table wins; else first alias
        # entry (display-ready, from Hindi Wikipedia titles); else None (the
        # frontend falls back to the English name). Also indexed for matching
        # so every displayed name is findable by typing it.
        name_hi = _HI_DISPLAY.get(c["geonameid"]) or \
            next(iter(_HI_ALIASES.get(c["geonameid"], [])), None)
        if name_hi:
            alts_hi.add(_ascii(name_hi))
        rows.append({
            "id": c["geonameid"], "name": name, "name_l": _ascii(name), "name_hi": name_hi,
            "alts": alts, "alts_hi": alts_hi, "alts_en": alts_en, "cc": cc, "country": _COUNTRY.get(cc, cc),
            "lat": round(float(c["latitude"]), 4), "lon": round(float(c["longitude"]), 4),
            "tz": c.get("timezone", ""), "pop": int(c.get("population", 0) or 0),
            "admin1": c.get("admin1code", ""),
        })
    rows.sort(key=lambda r: -r["pop"])          # population-ranked for suggest priority
    _CITIES = rows
    _BY_ID = {r["id"]: r for r in rows}


def _public(r: dict) -> dict:
    st = _STATE.get(r.get("admin1", ""), "")
    region = st if (st and st != r["name"]) else "India"
    out = {"id": r["id"], "name": r["name"], "label": f"{r['name']}, {region}",
           "region": region,
           "country": r["country"], "cc": r["cc"], "lat": r["lat"], "lon": r["lon"],
           "tz": r["tz"], "pop": r["pop"]}
    # Curated Hindi display name (dropdown text on *.hi.html pages ONLY).
    # `label` stays English ALWAYS — it is what the form submits and geocodes.
    # Omitted when we have no curated name; frontend then shows the English name.
    if r.get("name_hi"):
        out["name_hi"] = r["name_hi"]
    return out


def _build_name_index():
    """Build (once) an ascii-folded name/alias -> (lat, lon) map over EVERY Indian
    city GeoNames knows (~3.6k, population > 15k), independent of the autosuggest
    display floor (MIN_POP=50k). The resolver should place any city a user types
    — e.g. Leh (37k) — not just the ones shown in the dropdown. Highest-population
    first + first-write-wins, so an ambiguous name resolves to its biggest city,
    and old aliases (Bangalore->Bengaluru, Gurgaon->Gurugram) resolve correctly."""
    global _NAME_IDX
    if _NAME_IDX is not None:
        return
    from geonamescache import GeonamesCache
    rows = []
    for c in GeonamesCache().get_cities().values():
        if c.get("countrycode") != "IN":
            continue
        rows.append((int(c.get("population", 0) or 0),
                     round(float(c["latitude"]), 4), round(float(c["longitude"]), 4),
                     c["name"], c.get("alternatenames") or []))
    rows.sort(key=lambda t: -t[0])                 # most-populous first
    idx = {}
    for pop, lat, lon, name, alts in rows:
        keys = {_ascii(name)}
        for a in alts:
            fa = _ascii(a)
            if not fa:
                continue
            if _has_devanagari(a) or (fa.isascii() and all(ch.isalpha() or ch in " .-" for ch in fa)):
                keys.add(fa)
        for k in keys:
            if k and k not in idx:
                idx[k] = (lat, lon)
    _NAME_IDX = idx


def coords_for_name(place: str):
    """Authoritative offline coordinates for an Indian place NAME, from the full
    GeoNames India set (~3.6k cities, pop > 15k). Returns (lat, lon,
    tz_offset_hours) for the best/highest-population match, or None. India is a
    single timezone, so tz is +5.5 everywhere. This lets a city the user typed
    resolve to its real coordinates instead of the server silently defaulting to
    Delhi. Never raises."""
    try:
        _build_name_index()
        r = _NAME_IDX.get(_ascii((place or "").split(",")[0]))
        return (r[0], r[1], 5.5) if r else None
    except Exception:
        return None


def suggest(q: str, limit: int = 8) -> list:
    """Ranked autosuggest. Prefix-on-name > prefix-on-altname > substring, then by population.

    Accepts Latin or Devanagari queries. Devanagari queries match the folded
    Devanagari alternate names (alts_hi); results are the same city dicts —
    `name`/`label` stay English so downstream submit/geocode is unchanged.
    """
    _load()
    qq = _ascii(q or "")
    if len(qq) < 2:
        return []
    pre_name, pre_alt, sub = [], [], []
    if _has_devanagari(qq):
        # No canonical-vs-alt distinction in Devanagari: prefix > substring.
        for r in _CITIES:                        # already population-sorted
            if any(a.startswith(qq) for a in r["alts_hi"]):
                pre_name.append(r)
            elif any(qq in a for a in r["alts_hi"]):
                sub.append(r)
            if len(pre_name) >= limit:
                break
    else:
        for r in _CITIES:                        # already population-sorted
            if r["name_l"].startswith(qq) or any(a.startswith(qq) for a in r["alts_en"]):
                pre_name.append(r)
            elif any(a.startswith(qq) for a in r["alts"]):
                pre_alt.append(r)
            elif qq in r["name_l"]:
                sub.append(r)
            if len(pre_name) >= limit and len(pre_alt) >= limit:
                break
    out, seen = [], set()
    for bucket in (pre_name, pre_alt, sub):
        for r in bucket:
            if r["id"] in seen:
                continue
            seen.add(r["id"]); out.append(_public(r))
            if len(out) >= limit:
                return out
    return out


def resolve(geonameid) -> dict | None:
    _load()
    r = _BY_ID.get(int(geonameid)) if geonameid is not None else None
    return _public(r) if r else None


def tz_offset_hours(iana: str, local_dt: datetime) -> float | None:
    """UTC offset (hours) for an IANA zone at a given LOCAL date — DST/historical aware."""
    if not iana:
        return None
    try:
        from zoneinfo import ZoneInfo
        off = local_dt.replace(tzinfo=ZoneInfo(iana)).utcoffset()
        return round(off.total_seconds() / 3600, 2) if off is not None else None
    except Exception:
        return None
