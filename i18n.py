"""
Lightweight internationalization framework. (#9)

Dict-based catalogs (no gettext/compilation step) keyed by a short message id.
`t(key, lang)` returns the string for the requested language, falling back to
Hinglish ("hi_en", the product's native voice) and then to the key itself.

Supported languages are declared in SUPPORTED. Regional catalogs start as stubs
that inherit from Hinglish until translated, so nothing breaks as they are filled in.

Usage:
    from i18n import t, normalize_lang
    t("report.title", "hi")        -> Hindi string
    t("cta.unlock", "en")          -> English string
    normalize_lang("HI-in")        -> "hi"
"""

DEFAULT_LANG = "hi_en"  # Hinglish — the site's native voice

# Order matters for the language picker.
SUPPORTED = ["hi_en", "hi", "en", "mr", "ta", "te", "bn", "gu", "kn"]

LANG_NAMES = {
    "hi_en": "Hinglish", "hi": "हिन्दी", "en": "English", "mr": "मराठी",
    "ta": "தமிழ்", "te": "తెలుగు", "bn": "বাংলা", "gu": "ગુજરાતી", "kn": "ಕನ್ನಡ",
}

# ---- catalogs -------------------------------------------------------------
# Only the fully-authored languages carry values; the rest inherit at lookup time.
CATALOG = {
    "hi_en": {
        "report.title": "Marriage Timing Report",
        "report.subtitle": "Jyotish, calculated — no opinion, only calculation",
        "cta.unlock": "Poori report unlock kijiye — ₹499",
        "cta.whatsapp": "WhatsApp par report paayein",
        "teaser.heading": "Aapka free preview taiyaar hai",
        "pay.secure": "100% secure payment",
        "field.name": "Aapka naam",
        "field.dob": "Janm tithi",
        "field.tob": "Janm samay",
        "field.place": "Janm sthan",
        "milan.title": "Kundli Milan — 36 Guna",
        "blueprint.title": "Life Blueprint",
        "footer.disclaimer": "Indications, not fate — chart direction batata hai, choice aapki hai.",
    },
    "hi": {
        "report.title": "विवाह समय रिपोर्ट",
        "report.subtitle": "ज्योतिष, गणना द्वारा — कोई राय नहीं, केवल गणना",
        "cta.unlock": "पूरी रिपोर्ट अनलॉक करें — ₹499",
        "cta.whatsapp": "व्हाट्सएप पर रिपोर्ट पाएँ",
        "teaser.heading": "आपका नि:शुल्क पूर्वावलोकन तैयार है",
        "pay.secure": "100% सुरक्षित भुगतान",
        "field.name": "आपका नाम",
        "field.dob": "जन्म तिथि",
        "field.tob": "जन्म समय",
        "field.place": "जन्म स्थान",
        "milan.title": "कुंडली मिलान — 36 गुण",
        "blueprint.title": "जीवन ब्लूप्रिंट",
        "footer.disclaimer": "संकेत, भाग्य नहीं — कुंडली दिशा बताती है, चुनाव आपका है।",
    },
    "en": {
        "report.title": "Marriage Timing Report",
        "report.subtitle": "Astrology, calculated — no opinion, only calculation",
        "cta.unlock": "Unlock the full report — ₹499",
        "cta.whatsapp": "Get your report on WhatsApp",
        "teaser.heading": "Your free preview is ready",
        "pay.secure": "100% secure payment",
        "field.name": "Your name",
        "field.dob": "Date of birth",
        "field.tob": "Time of birth",
        "field.place": "Place of birth",
        "milan.title": "Kundli Milan — 36 Guna",
        "blueprint.title": "Life Blueprint",
        "footer.disclaimer": "Indications, not fate — the chart shows direction; the choice is yours.",
    },
}
# Regional languages inherit Hinglish until authored.
for _lang in ("mr", "ta", "te", "bn", "gu", "kn"):
    CATALOG.setdefault(_lang, {})


def normalize_lang(lang: str) -> str:
    """Map a raw request/header value to a supported code, else DEFAULT_LANG."""
    if not lang:
        return DEFAULT_LANG
    code = lang.replace("-", "_").lower().strip()
    if code in SUPPORTED:
        return code
    base = code.split("_")[0]
    if base in SUPPORTED:
        return base
    return DEFAULT_LANG


def t(key: str, lang: str = DEFAULT_LANG) -> str:
    """Translate `key`; fall back lang -> Hinglish -> key."""
    lang = normalize_lang(lang)
    if key in CATALOG.get(lang, {}):
        return CATALOG[lang][key]
    if key in CATALOG.get(DEFAULT_LANG, {}):
        return CATALOG[DEFAULT_LANG][key]
    return key


def coverage(lang: str) -> float:
    """Fraction of DEFAULT_LANG keys authored for `lang` (for a translation dashboard)."""
    base = CATALOG.get(DEFAULT_LANG, {})
    if not base:
        return 1.0
    have = CATALOG.get(normalize_lang(lang), {})
    return sum(1 for k in base if k in have) / len(base)
