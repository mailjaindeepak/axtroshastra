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

# Suggest at city/district level, not sub-locality. MIN_POP drops tiny places;
# _LOCALITY_RE drops cantonment/sub-locality entries that survive on population
# alone (e.g. "Delhi Cantonment" ~1.1 lakh). Tune MIN_POP to trade clutter vs
# coverage of smaller birth-towns.
import re
MIN_POP = 50000
_LOCALITY_RE = re.compile(r"\b(cantonment|cantt)\b", re.I)


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
        if pop < MIN_POP:         # keep city/district level — drop tiny localities
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
        rows.append({
            "id": c["geonameid"], "name": name, "name_l": _ascii(name),
            "alts": alts, "alts_hi": alts_hi, "cc": cc, "country": _COUNTRY.get(cc, cc),
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
    return {"id": r["id"], "name": r["name"], "label": f"{r['name']}, {region}",
            "region": region,
            "country": r["country"], "cc": r["cc"], "lat": r["lat"], "lon": r["lon"],
            "tz": r["tz"], "pop": r["pop"]}


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
            if r["name_l"].startswith(qq):
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
