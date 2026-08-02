# -*- coding: utf-8 -*-
"""
shaadi_hi — Hinglish→Devanagari localizer for the marriage (shaadi) funnel.

Same architecture as milan_hi: translate whole text-runs of an already-rendered
Hinglish page/report to conversational Devanagari. Only runs that fully resolve
(via the HI phrase dict, proper-noun TOK tokens, or a templated pattern) are
swapped; scripts/styles/attributes, names, numbers and anything unknown are left
untouched. Used for:
  * the /hi/marriage landing page  (localize applied to the Hinglish shaadi.html)
  * the Devanagari marriage report  (localize applied to render_report output)

Source of truth text is Hinglish; English values in the codebase's FRAG/EN dicts
were used only as reference while translating.
"""
import re
import html as _htmlmod

from shaadi_hi_data import HI_DATA

# ---------------------------------------------------------------- phrase dict
# v2 marriage report (report_view_v2) is English-base. These are the deterministic
# labels/headers/keys it emits; the LLM prose slots already arrive in Devanagari and
# pass through unchanged. Dynamic composite runs (dates, grades, planet names) are
# still handled by the TOK / GRADE / MONTH maps and the _template patterns below.
EN_HI_DATA = {
    # tier dividers
    "Tier 2": "भाग 2", "Tier 3": "भाग 3", "Tier 4": "भाग 4",
    "Summary": "सारांश", "Detailed Report": "विस्तृत रिपोर्ट", "The Astrology": "ज्योतिष विवरण",
    "The whole report, in six pages.": "पूरी रिपोर्ट, छह पन्नों में।",
    "Full depth on your timing, your partner, and your remedies.":
        "आपकी टाइमिंग, आपके जीवनसाथी और आपके उपायों का पूरा विवरण।",
    "Every classical calculation behind this report.":
        "इस रिपोर्ट के पीछे की हर शास्त्रीय गणना।",
    # section labels (plabel)
    "Your answer — at a glance": "आपका जवाब — एक नज़र में",
    "The answer": "जवाब", "Chart snapshot": "कुंडली की झलक", "Your person": "आपका जीवनसाथी",
    "Your timing story": "आपकी टाइमिंग की कहानी", "The big questions": "बड़े सवाल",
    "Your move": "आपका अगला कदम", "Window 1": "विंडो 1", "Window 2": "विंडो 2", "Window 3": "विंडो 3",
    "Action plan": "कार्य-योजना", "Quiet periods": "शांत अवधि", "Past years": "बीते वर्ष",
    "Year by year": "साल-दर-साल", "Manglik": "मांगलिक", "Sade Sati": "साढ़ेसाती",
    "Remedies": "उपाय", "Your partner": "आपका जीवनसाथी", "How you'll meet": "आप कैसे मिलेंगे",
    "Your pattern": "आपका स्वभाव", "Method": "पद्धति", "Birth chart · D1": "जन्म कुंडली · D1",
    "Lagna & Moon": "लग्न और चंद्र", "The nine planets": "नौ ग्रह",
    "Nakshatra & pada": "नक्षत्र और पद", "The 7th house": "सातवाँ भाव", "The 7th lord": "सातवें भाव का स्वामी",
    "Karakas": "कारक", "Darakaraka": "दारकारक", "The nodes": "राहु-केतु", "Dashas": "दशाएँ",
    "Gochar · transits": "गोचर", "Navamsa · D9": "नवमांश · D9", "Closing": "समापन",
    "Full chart": "पूरी कुंडली", "Under the hood": "गणना के पीछे",
    # h2 headings
    "When will you get married?": "आपकी शादी कब होगी?",
    "Your marriage windows": "आपकी विवाह विंडोज़",
    "Your Kundli at a glance": "आपकी कुंडली — एक नज़र में",
    "Your potential partner": "आपका संभावित जीवनसाथी",
    "Why not yet — and what's changing": "अब तक क्यों नहीं — और क्या बदल रहा है",
    "The three things everyone asks": "तीन सवाल जो हर कोई पूछता है",
    "What to do now": "अब क्या करें",
    "Your strongest window": "आपकी सबसे मज़बूत विंडो",
    "Your second window": "आपकी दूसरी विंडो", "Your third window": "आपकी तीसरी विंडो",
    "Strong & moderate windows — your move": "मज़बूत और मध्यम विंडोज़ — आपका कदम",
    "Weak periods — what to do": "कमज़ोर अवधि — क्या करें",
    "Why it hasn't happened yet": "अब तक क्यों नहीं हुई",
    "The next three years": "अगले तीन साल",
    "Manglik — impact, dos & don'ts": "मांगलिक — प्रभाव, क्या करें और क्या नहीं",
    "Sade Sati — the Saturn cycle": "साढ़ेसाती — शनि का चक्र",
    "Remedies for your dasha periods": "आपकी दशा अवधियों के उपाय",
    "For weak periods ahead": "आगे की कमज़ोर अवधियों के लिए",
    "Their likely personality": "उनका संभावित स्वभाव",
    "Their background & how you'll meet": "उनकी पृष्ठभूमि और आप कैसे मिलेंगे",
    "How you love": "आप प्रेम कैसे करते हैं",
    "Method & foundations": "पद्धति और आधार",
    "Your birth chart (D1)": "आपकी जन्म कुंडली (D1)",
    "Your full chart — verify it yourself": "आपकी पूरी कुंडली — खुद जाँचिए",
    "Your birth star": "आपका जन्म-नक्षत्र",
    "The 7th house — seat of marriage": "सातवाँ भाव — विवाह का स्थान",
    "The 7th lord — the marriage switch": "सातवें भाव का स्वामी — विवाह का मुख्य स्विच",
    "The marriage karakas": "विवाह के कारक",
    "Darakaraka (Jaimini)": "दारकारक (जैमिनी)",
    "Rahu / Ketu on the 7th axis": "सातवें अक्ष पर राहु / केतु",
    "The dasha system & your periods": "दशा पद्धति और आपकी अवधियाँ",
    "Jupiter & Saturn transits": "गुरु और शनि का गोचर",
    "The Navamsa (D9)": "नवमांश (D9)", "A note to you": "आपके लिए एक संदेश",
    "The Navamsa (D9) — marriage's truest mirror": "नवमांश (D9) — विवाह का सच्चा दर्पण",
    # fact keys
    "Lagna": "लग्न", "Moon · Nakshatra": "चंद्र · नक्षत्र", "7th house": "सातवाँ भाव",
    "7th lord": "सातवें भाव का स्वामी", "Marriage karaka": "विवाह कारक",
    "Navamsa promise": "नवमांश का वादा", "Ayanamsa": "अयनांश", "Houses": "भाव पद्धति",
    "System": "पद्धति", "Birth-time quality": "जन्म-समय की गुणवत्ता",
    "Moon sign · Nakshatra": "चंद्र राशि · नक्षत्र", "Dignity": "स्थिति",
    "House from Lagna": "लग्न से भाव", "Karaka(s)": "कारक",
    "Current Mahadasha": "वर्तमान महादशा", "Current Antardasha": "वर्तमान अंतर्दशा",
    "D9 Lagna": "D9 लग्न", "D9 7th house": "D9 सातवाँ भाव", "D9 7th lord": "D9 सातवें भाव का स्वामी",
    "Venus in D9": "D9 में शुक्र",
    # dos & don'ts + remedy labels
    "Do": "करें", "Don't": "न करें", "Whole sign": "पूर्ण-राशि",
    "The connection may come through": "यह रिश्ता जुड़ सकता है",
    # table headers (planet table)
    "Planet": "ग्रह", "Sign": "राशि", "Nakshatra": "नक्षत्र", "House": "भाव",
    "State": "स्थिति", "Total": "कुल",
    # cover / misc
    "Marriage Timing Report": "विवाह समय रिपोर्ट",
}

# ---- v2 report: deterministic English content -> Devanagari (authored) ----
# Static strings the report_view_v2 renderer emits verbatim. LLM prose slots come
# back in Devanagari already; these cover the scaffolding, cards, Manglik/remedies,
# and content maps so the Hindi report has no English islands.
EN_HI_V2 = {
    # ---- cover ----
    "Date of birth": "जन्म तिथि", "Time of birth": "जन्म समय", "Place of birth": "जन्म स्थान",
    "Lagna-based analysis with full house precision.":
        "लग्न-आधारित विश्लेषण, पूरी भाव-सटीकता के साथ।",
    # ---- headline chips (1-2 words) ----
    "Snapshot": "झलक", "Turning": "बदलाव", "3 checks": "3 जाँच", "Act": "कदम उठाएँ",
    "Strongest": "सबसे मज़बूत", "Second": "दूसरी", "Longer arc": "दूरगामी",
    "Lean in": "पूरा ज़ोर", "Prepare": "तैयारी", "Why not yet": "अब तक क्यों नहीं",
    "Next 3 yrs": "अगले 3 साल", "Optional": "वैकल्पिक", "Two lenses": "दो नज़रिए",
    "9 planets": "नौ ग्रह", "Birth star": "जन्म-नक्षत्र", "Marriage seat": "विवाह-स्थान",
    "The switch": "मुख्य स्विच", "Significators": "कारक", "Jaimini": "जैमिनी",
    "Karmic axis": "कर्म-अक्ष", "Your periods": "आपकी दशाएँ", "Go / slow": "आगे / धीमे",
    "Foundations": "आधार", "Your chart": "आपकी कुंडली", "For you": "आपके लिए",
    "Clear": "स्पष्ट", "Cleared": "निवारण", "Manageable": "सँभालने योग्य",
    "Active phase": "सक्रिय चरण", "Not now": "अभी नहीं",
    "1 window": "1 विंडो", "2 windows": "2 विंडोज़", "3 windows": "3 विंडोज़",
    # ---- hero ----
    "Most likely marriage window": "सबसे संभावित विवाह विंडो",
    "High confidence": "उच्च भरोसा", "Moderate confidence": "मध्यम भरोसा",
    "Emerging confidence": "उभरता भरोसा",
    "High confidence · approx. birth time": "उच्च भरोसा · अनुमानित जन्म-समय",
    "Moderate confidence · approx. birth time": "मध्यम भरोसा · अनुमानित जन्म-समय",
    "Emerging confidence · approx. birth time": "उभरता भरोसा · अनुमानित जन्म-समय",
    # ---- answer / manglik one-liners ----
    "Manglik: No — no obstacle on this front.": "मांगलिक: नहीं — इस ओर कोई रुकावट नहीं।",
    "Manglik: technically yes, but cancelled — practically No.":
        "मांगलिक: तकनीकी रूप से हाँ, पर निवारण हो गया — व्यावहारिक रूप से नहीं।",
    "Manglik: Yes — see the detail and cancellation check in the Manglik section.":
        "मांगलिक: हाँ — विवरण और निवारण-जाँच मांगलिक खंड में देखें।",
    "No": "नहीं", "Cancelled (effectively no)": "निवारण (व्यावहारिक रूप से नहीं)",
    "Yes — see the Manglik section": "हाँ — मांगलिक खंड देखें",
    "This answer comes from your full chart. The rest of the report shows every window, your Navamsa, and your past periods — so you can check it yourself.":
        "यह जवाब आपकी पूरी कुंडली से निकला है। आगे की रिपोर्ट में हर विंडो, आपका नवमांश और बीते दौर दिए हैं — ताकि आप ख़ुद मिला सकें।",
    # ---- Kundli glance (why lines) ----
    "The base of your personality and whole chart — every house is counted from here.":
        "आपके व्यक्तित्व और पूरी कुंडली का आधार — हर भाव यहीं से गिना जाता है।",
    "Your mind and emotions — and the engine of your timing, since your dasha calendar runs from your Moon.":
        "आपका मन और भावनाएँ — और आपकी टाइमिंग का इंजन, क्योंकि आपकी दशा-गणना चंद्र से चलती है।",
    "The house of marriage, partner and commitment — the main area for this report.":
        "विवाह, जीवनसाथी और प्रतिबद्धता का भाव — इस रिपोर्ट का मुख्य क्षेत्र।",
    "The main switch for marriage; its condition shapes how clear and smooth the timing is.":
        "विवाह का मुख्य स्विच; इसकी स्थिति तय करती है कि टाइमिंग कितनी साफ़ और सहज है।",
    "The natural indicator of love and marriage (Venus, plus Jupiter for a woman) — it shows the marriage promise.":
        "प्रेम और विवाह का स्वाभाविक कारक (शुक्र, और स्त्री के लिए गुरु भी) — यह विवाह का वादा दिखाता है।",
    "The Jaimini spouse-significator — a second, independent glimpse of the partner.":
        "जैमिनी का जीवनसाथी-कारक — साथी की एक दूसरी, स्वतंत्र झलक।",
    # ---- partner snapshot / love vs arranged ----
    "Your chart leans toward a love or self-chosen match.":
        "आपकी कुंडली प्रेम या स्वयं-चुने रिश्ते की ओर झुकी है।",
    "Your chart leans toward an arranged or introduction-led match.":
        "आपकी कुंडली अरेंज्ड या परिचय-आधारित रिश्ते की ओर झुकी है।",
    "There is also a signature for a partner from a different community, background, or place.":
        "एक संकेत यह भी है कि साथी किसी अलग समुदाय, पृष्ठभूमि या जगह से हो सकता है।",
    "The indications lean toward your own circle and community.":
        "संकेत आपके अपने दायरे और समुदाय की ओर झुके हैं।",
    "These are indications, not a portrait — the chart gives the direction; life fills in the detail.":
        "ये संकेत हैं, कोई पूरी तस्वीर नहीं — कुंडली दिशा देती है; ब्योरा ज़िंदगी भरती है।",
    # ---- big questions / soft notes ----
    "currently running": "अभी चल रही है", "not currently running": "अभी नहीं चल रही",
    "Each of these has its own detailed page ahead, with the reasoning and what it means for you.":
        "इनमें से हर एक का अपना विस्तृत पन्ना आगे है, कारण और आपके लिए उसके मतलब के साथ।",
    # ---- action / weak ----
    "Your chart shows the timing; the effort and the choice stay in your hands. Even in a strong window you still have to look — the conversion rate is just far better.":
        "कुंडली टाइमिंग बताती है; मेहनत और चुनाव आपके हाथ में हैं। मज़बूत विंडो में भी ढूँढना तो पड़ता है — बस सफलता की दर कहीं बेहतर होती है।",
    "A low-activation phase — matches may come but tend not to convert. Delays here are pattern, not personal failure.":
        "कम-सक्रियता का दौर — रिश्ते आ सकते हैं पर अक्सर टिकते नहीं। यहाँ देरी एक पैटर्न है, आपकी कमी नहीं।",
    # ---- remedies ----
    "For weak periods ahead": "आगे की कमज़ोर अवधियों के लिए",
    "Fast day:": "व्रत का दिन:", "Mantra:": "मंत्र:", "Gemstone:": "रत्न:",
    "not advised for this period — the mantra and fast are enough.":
        "इस अवधि के लिए सलाह नहीं — मंत्र और व्रत ही काफ़ी हैं।",
    "Remember the order: action first — actively looking during a strong window. This is support, not a substitute.":
        "क्रम याद रखें: पहले कर्म — मज़बूत विंडो में सक्रिय रूप से ढूँढना। यह सहारा है, विकल्प नहीं।",
    # ---- disclaimer / endcard / upsell ----
    "This report is computed from classical Vedic Jyotish (dasha–transit) principles — for guidance, not a guarantee. Timing windows are probabilities, not fixed dates. This is not legal, medical or financial advice. Make your own life decisions using your own judgement; Axtroshastra takes no responsibility for any outcome.":
        "यह रिपोर्ट शास्त्रीय वैदिक ज्योतिष (दशा–गोचर) सिद्धांतों पर आधारित है — मार्गदर्शन के लिए, गारंटी नहीं। समय-विंडो संभावनाएँ हैं, तय तारीख़ें नहीं। यह क़ानूनी, चिकित्सीय या वित्तीय सलाह नहीं है। अपने जीवन के फ़ैसले अपनी समझ से लें; Axtroshastra किसी परिणाम की ज़िम्मेदारी नहीं लेता।",
    "Made with Axtroshastra — get your own report:":
        "Axtroshastra से बनी — अपनी रिपोर्ट पाएँ:",
    "One more question, from the same chart: when will your career lift?":
        "एक और सवाल, इसी कुंडली से: आपका करियर कब उड़ान भरेगा?",
    "WhatsApp Support": "WhatsApp सहायता", "Download PDF": "PDF डाउनलोड करें",
    "Share on WhatsApp": "WhatsApp पर शेयर करें",
}

# ---- content maps: exact English rendered value -> Devanagari ----
_SIGN_PARTNER_HI = {
    "direct, energetic, quick to decide — someone who takes initiative":
        "सीधे, ऊर्जावान, जल्दी फ़ैसला लेने वाले — जो पहल करते हैं",
    "steady, comfort-loving, loyal — someone who values stability and family":
        "स्थिर, सुकून-पसंद, वफ़ादार — जो स्थिरता और परिवार को महत्व देते हैं",
    "communicative, witty, sociable — someone you can talk to for hours":
        "बातूनी, हाज़िरजवाब, मिलनसार — जिनसे आप घंटों बात कर सकें",
    "caring, family-oriented, emotionally deep — a nurturing presence":
        "ख़याल रखने वाले, परिवार-प्रेमी, भावनात्मक रूप से गहरे — एक सँभालने वाली मौजूदगी",
    "confident, warm, dignified — someone with presence and generosity":
        "आत्मविश्वासी, गर्मजोश, गरिमामय — रौब और दिलदारी वाले",
    "practical, detail-minded, helpful — someone organised and sincere":
        "व्यावहारिक, बारीकी पर ध्यान देने वाले, मददगार — व्यवस्थित और सच्चे",
    "balanced, charming, partnership-minded — marriage matters deeply to them":
        "संतुलित, आकर्षक, साझेदारी में यक़ीन रखने वाले — जिनके लिए विवाह गहरे मायने रखता है",
    "intense, private, deeply loyal — a bond that runs deep once formed":
        "गहरे, निजी, बेहद वफ़ादार — एक बंधन जो बनने के बाद बहुत गहरा होता है",
    "optimistic, principled, freedom-loving — someone with strong beliefs":
        "आशावादी, उसूलों वाले, आज़ादी-पसंद — मज़बूत सोच वाले",
    "responsible, ambitious, mature — often settled or career-established":
        "ज़िम्मेदार, महत्वाकांक्षी, परिपक्व — अक्सर सेटल या करियर में जमे हुए",
    "independent, idealistic, unconventional — a friend first":
        "स्वतंत्र, आदर्शवादी, अलग सोच वाले — पहले दोस्त",
    "gentle, intuitive, adaptable — emotionally giving and artistic":
        "कोमल, सहज-बोध वाले, ढल जाने वाले — भावनात्मक रूप से देने वाले और कलात्मक",
}
_DK_PARTNER_HI = {
    "a dignified, self-respecting partner, possibly from an established family":
        "गरिमामय, स्वाभिमानी साथी, शायद किसी प्रतिष्ठित परिवार से",
    "an emotionally attuned, caring partner; family approval flows easily":
        "भावनात्मक रूप से जुड़े, ख़याल रखने वाले साथी; परिवार की सहमति आसानी से मिलती है",
    "an energetic, protective partner with strong drive":
        "ऊर्जावान, रक्षक साथी, मज़बूत जोश के साथ",
    "a younger-feeling, intelligent, talkative partner":
        "उम्र में कमतर लगने वाले, बुद्धिमान, बातूनी साथी",
    "a wise, well-educated, principled partner — often traditional values":
        "समझदार, सुशिक्षित, उसूलों वाले साथी — अक्सर पारंपरिक मूल्यों वाले",
    "an attractive, artistic, pleasure-loving partner; strong mutual affection":
        "आकर्षक, कलात्मक, आनंद-प्रेमी साथी; आपसी स्नेह गहरा",
    "a mature, dutiful, patient partner — possibly older or met later":
        "परिपक्व, कर्तव्यनिष्ठ, धैर्यवान साथी — शायद उम्र में बड़े या बाद में मिलने वाले",
}
_VENUS_STYLE_HI = {
    "direct and impulsive in love — you pursue openly and lose interest in games":
        "प्रेम में सीधे और आवेगी — आप खुलकर आगे बढ़ते हैं और खेल-तमाशों में रुचि खो देते हैं",
    "sensory and loyal — love means comfort, food, touch and permanence":
        "इंद्रिय-प्रेमी और वफ़ादार — प्यार यानी सुकून, खाना, स्पर्श और स्थायित्व",
    "playful and verbal — flirting is conversation, and conversation is intimacy":
        "खिलंदड़े और बातचीत-प्रेमी — फ़्लर्ट यानी बातचीत, और बातचीत ही नज़दीकी",
    "protective and emotional — you love like family, deep and enveloping":
        "रक्षक और भावुक — आप परिवार की तरह प्यार करते हैं, गहरा और समेट लेने वाला",
    "grand and warm-hearted — romance should feel like celebration":
        "भव्य और गर्मदिल — रोमांस किसी जश्न जैसा लगना चाहिए",
    "careful and devoted — you love through acts of service and quiet standards":
        "सतर्क और समर्पित — आप सेवा और ख़ामोश मानकों से प्यार जताते हैं",
    "harmonising and partnership-built — you are at your best in a committed pair":
        "सामंजस्य बिठाने वाले और साझेदारी में ढले — आप एक प्रतिबद्ध जोड़ी में सबसे बेहतर होते हैं",
    "intense and all-or-nothing — you love deeply or not at all":
        "तीव्र और सब-या-कुछ-नहीं — आप या तो गहराई से प्यार करते हैं या बिल्कुल नहीं",
    "adventurous and idealistic — love must have meaning and room to roam":
        "साहसी और आदर्शवादी — प्यार में मायने और घूमने की जगह होनी चाहिए",
    "reserved and enduring — slow to open, near-impossible to shake once committed":
        "संकोची और टिकाऊ — धीरे खुलते हैं, पर प्रतिबद्ध होने के बाद डिगाना लगभग नामुमकिन",
    "unconventional and friendship-first — you love minds and freedom":
        "अलग सोच वाले और दोस्ती-पहले — आप दिमाग़ और आज़ादी से प्यार करते हैं",
    "romantic and self-giving — you love like poetry, and must guard against over-giving":
        "रोमांटिक और स्व-समर्पित — आप कविता की तरह प्यार करते हैं, और ज़रूरत से ज़्यादा देने से बचें",
}

# Manglik dos/don'ts + weak-period actions (mirror jyotish_maps values)
_MANGLIK_HI = {
    "Mars does not sit in a Manglik house from either your Lagna or your Moon, so the classical Mangal dosha simply does not apply to you.":
        "मंगल आपके लग्न या चंद्र, किसी से भी मांगलिक भाव में नहीं है — इसलिए शास्त्रीय मंगल दोष आप पर लागू ही नहीं होता।",
    "Answer the question confidently: on this chart, you are not Manglik.":
        "यह सवाल आत्मविश्वास से जवाब दें: इस कुंडली के हिसाब से आप मांगलिक नहीं हैं।",
    "Match on the things that actually last — values, temperament, timing.":
        "उन चीज़ों पर मिलान करें जो सचमुच टिकती हैं — मूल्य, स्वभाव, टाइमिंग।",
    "Keep the focus on your marriage windows rather than this checkbox.":
        "ध्यान इस ख़ाने पर नहीं, अपनी विवाह-विंडोज़ पर रखें।",
    "Don't let anyone invent a dosha that your chart does not show.":
        "किसी को ऐसा दोष गढ़ने न दें जो आपकी कुंडली में है ही नहीं।",
    "Don't pay for 'Manglik remedies' you do not need.":
        "जिन 'मांगलिक उपायों' की ज़रूरत नहीं, उनके लिए पैसे न दें।",
    "Mars is in a Manglik position, but a recognised classical cancellation applies — so in practice this is treated as effectively non-Manglik.":
        "मंगल मांगलिक स्थिति में है, पर एक मान्य शास्त्रीय निवारण लागू है — इसलिए व्यवहार में इसे लगभग ग़ैर-मांगलिक ही माना जाता है।",
    "Understand the cancellation so you can explain it calmly to family.":
        "निवारण को समझें ताकि आप परिवार को शांति से समझा सकें।",
    "State it plainly in a match: technically present, classically cancelled.":
        "रिश्ते में साफ़ कहें: तकनीकी रूप से मौजूद, शास्त्रीय रूप से निवारित।",
    "Weigh compatibility on the whole chart, not this single factor.":
        "अनुकूलता पूरी कुंडली पर तौलें, सिर्फ़ इस एक कारक पर नहीं।",
    "Don't accept fear-based framing — a cancelled dosha is not a warning.":
        "डर-आधारित बातों को न मानें — निवारित दोष कोई चेतावनी नहीं है।",
    "Don't over-spend on remedies for a dosha that is already neutralised.":
        "जो दोष पहले ही निष्प्रभावी है, उसके उपायों पर ज़्यादा ख़र्च न करें।",
    "Mars sits in a Manglik house. This is not a curse or a verdict on your marriage — classical texts treat it as a factor to handle thoughtfully, and it becomes neutral in a Manglik–Manglik match.":
        "मंगल एक मांगलिक भाव में है। यह कोई शाप या आपके विवाह पर फ़ैसला नहीं है — शास्त्र इसे सोच-समझकर सँभालने वाला कारक मानते हैं, और मांगलिक–मांगलिक मिलान में यह निष्प्रभावी हो जाता है।",
    "Give the relationship time to mature before big commitments — patience suits this placement.":
        "बड़े वादों से पहले रिश्ते को पकने का समय दें — इस स्थिति के लिए धीरज उपयुक्त है।",
    "Consider a partner who is also Manglik, where the factor cancels out.":
        "ऐसे साथी पर विचार करें जो स्वयं भी मांगलिक हो, जहाँ यह कारक आपस में कट जाता है।",
    "Channel the Mars energy into shared goals and honest, quick conflict-resolution.":
        "मंगल की ऊर्जा को साझा लक्ष्यों और ईमानदार, त्वरित मतभेद-समाधान में लगाएँ।",
    "Don't panic or treat this as doom — it is common and manageable.":
        "घबराएँ नहीं, इसे अनहोनी न मानें — यह आम और सँभालने योग्य है।",
    "Don't rush into expensive or fear-driven remedies; start with awareness.":
        "महँगे या डर से किए उपायों में जल्दबाज़ी न करें; शुरुआत जागरूकता से करें।",
    "Don't let this single factor override an otherwise strong match.":
        "इस एक कारक को किसी अन्यथा मज़बूत रिश्ते पर हावी न होने दें।",
}
_WEAK_HI = {
    "In a quiet phase, matches may still come but tend not to convert. This is pattern, not personal failure — and it is the best time to prepare rather than push.":
        "शांत दौर में रिश्ते आ तो सकते हैं पर अक्सर टिकते नहीं। यह एक पैटर्न है, आपकी कमी नहीं — और यही समय ज़ोर लगाने से ज़्यादा तैयारी का है।",
    "Use the time for clarity — what you actually want in a partner and a life.":
        "इस समय का उपयोग स्पष्टता के लिए करें — आप साथी और जीवन में असल में क्या चाहते हैं।",
    "Keep your profile current and doors open, without forcing outcomes.":
        "अपनी प्रोफ़ाइल अद्यतन और दरवाज़े खुले रखें, नतीजों को ज़बरदस्ती किए बिना।",
    "Invest in yourself: health, work, and the conversations with family that make later 'yes' easier.":
        "ख़ुद में निवेश करें: सेहत, काम, और परिवार से वे बातचीत जो आगे 'हाँ' को आसान बनाती हैं।",
    "Don't read a slow phase as a closed door — it is a low-activation window, not a verdict.":
        "धीमे दौर को बंद दरवाज़ा न समझें — यह कम-सक्रियता की विंडो है, कोई फ़ैसला नहीं।",
    "Don't force a decision that doesn't feel right just because time is passing.":
        "सिर्फ़ समय बीतने की वजह से कोई ग़लत लगता फ़ैसला ज़बरदस्ती न लें।",
    # dignity phrases (used in 'Planet — <phrase>')
    "in its own sign — a strong placement": "अपनी ही राशि में — मज़बूत स्थिति",
    "exalted — the best possible dignity": "उच्च — सर्वोत्तम स्थिति",
    "debilitated — timing deserves extra care": "नीच — टाइमिंग पर अतिरिक्त ध्यान",
    "neutral dignity": "सामान्य स्थिति",
    # mg heads
    "You are not Manglik ✅": "आप मांगलिक नहीं हैं ✅",
    "Manglik placement — but cancelled ✅": "मांगलिक स्थिति — पर निवारित ✅",
    "Manglik placement — let's understand it calmly": "मांगलिक स्थिति — आइए इसे शांति से समझें",
}

HI = {}
HI.update(HI_DATA)
HI.update(EN_HI_DATA)
HI.update(EN_HI_V2)
HI.update(_SIGN_PARTNER_HI)
HI.update(_DK_PARTNER_HI)
HI.update(_VENUS_STYLE_HI)
HI.update(_MANGLIK_HI)
HI.update(_WEAK_HI)
# nakshatra nature/relationship lines (English -> Devanagari, from jyotish_maps twins)
try:
    from jyotish_maps import NAK_PROFILE as _NP, NAK_PROFILE_HI as _NPH
    for _i in _NP:
        _sym, _nat, _rel = _NP[_i]
        _nat_hi, _rel_hi = _NPH[_i]
        HI[_nat] = _nat_hi
        HI[_rel] = _rel_hi
except Exception:
    pass

# remedy fast-day weekdays
HI.update({"Sunday": "रविवार", "Monday": "सोमवार", "Tuesday": "मंगलवार",
           "Wednesday": "बुधवार", "Thursday": "गुरुवार", "Friday": "शुक्रवार",
           "Saturday": "शनिवार"})
# meeting-context phrases (index-aligned with report_view_v2.MEETING_EN)
HI.update({
    "self-initiated, through your own efforts": "आपकी अपनी पहल या ख़ुद की कोशिशों से",
    "family networks or finances": "परिवार के नेटवर्क या धन-संपत्ति से",
    "siblings, neighbours, or short travels": "भाई-बहन, पड़ोसी, या छोटी यात्राओं से",
    "the home circle or mother's side": "घर के दायरे या माँ के पक्ष से",
    "social settings, children's events, or romance first": "सामाजिक मौक़ों, बच्चों के आयोजनों, या पहले रोमांस से",
    "the workplace or daily circles": "कार्यस्थल या रोज़मर्रा के दायरों से",
    "direct proposals — partnership-driven": "सीधे प्रस्तावों से — साझेदारी-प्रेरित",
    "in-law networks or transformative settings": "ससुराल के नेटवर्क या रूपांतरकारी परिस्थितियों से",
    "distant places, education circles, or a different community": "दूर के स्थानों, शिक्षा के दायरों, या किसी अलग समुदाय से",
    "career settings or father's network": "करियर की परिस्थितियों या पिता के नेटवर्क से",
    "friends' circles — a friend's introduction": "दोस्तों के दायरे से — किसी दोस्त के ज़रिए परिचय",
    "quiet or private settings, possibly at some distance": "शांत या निजी परिस्थितियों से, शायद कुछ दूरी पर",
})
# ---- static strings missed on the first pass ----
HI.update({
    "What you need to do for better results": "बेहतर नतीजों के लिए आपको क्या करना है",
    "Make your quiet phases count": "अपने शांत दौर को सार्थक बनाएँ",
    "Nature": "स्वभाव", "Love vs Arranged": "प्रेम बनाम अरेंज्ड",
    "Meeting context": "मिलने का संदर्भ", "Your Venus": "आपका शुक्र",
    "Lagna (ascendant)": "लग्न (उदयलग्न)",
    "Cancellation(s) that apply:": "लागू निवारण:", "Manglik:": "मांगलिक:",
    "Partner direction:": "जीवनसाथी की दिशा:", "Top window:": "सबसे मज़बूत विंडो:",
    "Jupiter's transit this year sits in supportive houses — it helps carry conversations forward.":
        "इस साल गुरु का गोचर सहायक भावों में है — यह बातचीत को आगे बढ़ाने में मदद करता है।",
    "Jupiter's transit this year is neutral — lean a little more on effort than on luck.":
        "इस साल गुरु का गोचर तटस्थ है — क़िस्मत से ज़्यादा मेहनत पर भरोसा रखें।",
    "Lahiri": "लाहिरी",
    "The full placement table with each planet's sign, nakshatra, house and state is on the birth-chart page above.":
        "हर ग्रह की राशि, नक्षत्र, भाव और स्थिति वाली पूरी तालिका ऊपर जन्म-कुंडली वाले पन्ने पर है।",
})
# nakshatra symbols (English -> Devanagari), used in "<Nak> (<symbol>)" titles
HI.update({
    "Horse's head": "घोड़े का सिर", "Yoni": "योनि", "Razor / flame": "उस्तरा / ज्वाला",
    "Chariot / ox-cart": "रथ / बैलगाड़ी", "Deer's head": "हिरण का सिर", "Teardrop / gem": "अश्रु / रत्न",
    "Bow and quiver": "धनुष और तरकश", "Flower / udder": "पुष्प / थन", "Coiled serpent": "कुंडली मारे साँप",
    "Throne": "सिंहासन", "Front of the bed": "पलंग का अगला भाग", "Back of the bed": "पलंग का पिछला भाग",
    "Hand": "हाथ", "Pearl / jewel": "मोती / रत्न", "Young sprout in wind": "हवा में नन्हा अंकुर",
    "Triumphal archway": "विजय-द्वार", "Lotus": "कमल", "Earring / umbrella": "कुंडल / छत्र",
    "Bundle of roots": "जड़ों का गुच्छा", "Elephant tusk / fan": "हाथी-दाँत / पंखा",
    "Elephant tusk / cot": "हाथी-दाँत / खाट", "Ear / three footprints": "कान / तीन पदचिह्न",
    "Drum": "ढोल", "Empty circle / 100 healers": "रिक्त वृत्त / सौ वैद्य",
    "Sword / two-faced man": "तलवार / दो-मुख पुरुष", "Twins / serpent of the deep": "जुड़वाँ / गहराई का सर्प",
    "Fish / drum": "मछली / ढोल",
})
# nature/venus first-word chips (dynamic single-word chips)
HI.update({
    "Direct": "सीधे", "Steady": "स्थिर", "Communicative": "बातूनी", "Caring": "ख़याल रखने वाले",
    "Confident": "आत्मविश्वासी", "Practical": "व्यावहारिक", "Balanced": "संतुलित",
    "Intense": "गहरे", "Optimistic": "आशावादी", "Responsible": "ज़िम्मेदार",
    "Independent": "स्वतंत्र", "Gentle": "कोमल", "Sensory": "इंद्रिय-प्रेमी",
    "Playful": "खिलंदड़े", "Protective": "रक्षक", "Grand": "भव्य", "Careful": "सतर्क",
    "Harmonising": "सामंजस्यपूर्ण", "Adventurous": "साहसी", "Reserved": "संकोची",
    "Unconventional": "अलग सोच", "Romantic": "रोमांटिक", "Love": "प्रेम", "Arranged": "अरेंज्ड",
})
# navamsa (D9) reasons + band notes (navamsa.py, English) -> Devanagari
HI.update({
    "Venus (the marriage karaka) is vargottama — strength in affection and staying power.":
        "शुक्र (विवाह कारक) वर्गोत्तम है — स्नेह और निभाव की मज़बूती।",
    "Venus is debilitated in D9 — a gentler, softer touch in how love is expressed.":
        "शुक्र D9 में नीच है — प्रेम जताने में नरमी की ज़रूरत।",
    "No strong plus or minus signal in D9 — a neutral promise; the timing comes from D1.":
        "D9 में कोई मज़बूत सकारात्मक या नकारात्मक संकेत नहीं — तटस्थ वादा; समय D1 से आता है।",
    "The Navamsa strongly supports the marriage promise — the union is well indicated; it is only a matter of timing (see the windows above).":
        "नवमांश विवाह के वादे का ज़ोरदार समर्थन करता है — योग पक्का है; बस समय की बात है (ऊपर विंडोज़ देखें)।",
    "The Navamsa is a little tender — this does not mean marriage won't happen; it means partner-choice and timing simply deserve more thought. This is awareness, not a warning.":
        "नवमांश थोड़ा कोमल है — इसका मतलब यह नहीं कि विवाह नहीं होगा; बल्कि साथी-चुनाव और समय पर ज़्यादा सोच-विचार ज़रूरी है। यह जागरूकता है, कोई चेतावनी नहीं।",
    "The Navamsa steadily supports the marriage promise — no major obstacle; the D1 windows are the real driver.":
        "नवमांश विवाह के वादे का स्थिर समर्थन करता है — कोई बड़ी रुकावट नहीं; असल चालक D1 विंडोज़ ही हैं।",
})

# ---------------------------------------------------------------- proper nouns
TOK = {
    # rashis (English + Sanskrit)
    "Aries": "मेष", "Taurus": "वृषभ", "Gemini": "मिथुन", "Cancer": "कर्क",
    "Leo": "सिंह", "Virgo": "कन्या", "Libra": "तुला", "Scorpio": "वृश्चिक",
    "Sagittarius": "धनु", "Capricorn": "मकर", "Aquarius": "कुंभ", "Pisces": "मीन",
    "Mesha": "मेष", "Vrishabha": "वृषभ", "Mithuna": "मिथुन", "Karka": "कर्क",
    "Simha": "सिंह", "Kanya": "कन्या", "Tula": "तुला", "Vrishchika": "वृश्चिक",
    "Dhanu": "धनु", "Makara": "मकर", "Kumbha": "कुंभ", "Meena": "मीन",
    # nakshatras
    "Ashwini": "अश्विनी", "Bharani": "भरणी", "Krittika": "कृत्तिका", "Rohini": "रोहिणी",
    "Mrigashira": "मृगशिरा", "Ardra": "आर्द्रा", "Punarvasu": "पुनर्वसु", "Pushya": "पुष्य",
    "Ashlesha": "आश्लेषा", "Magha": "मघा", "Purva Phalguni": "पूर्व फाल्गुनी",
    "Uttara Phalguni": "उत्तर फाल्गुनी", "Hasta": "हस्त", "Chitra": "चित्रा",
    "Swati": "स्वाति", "Vishakha": "विशाखा", "Anuradha": "अनुराधा", "Jyeshtha": "ज्येष्ठा",
    "Mula": "मूल", "Purva Ashadha": "पूर्व आषाढ़ा", "Uttara Ashadha": "उत्तर आषाढ़ा",
    "Shravana": "श्रवण", "Dhanishta": "धनिष्ठा", "Shatabhisha": "शतभिषा",
    "Purva Bhadrapada": "पूर्व भाद्रपद", "Uttara Bhadrapada": "उत्तर भाद्रपद", "Revati": "रेवती",
    # planets (English + Hindi source spellings used in the report)
    "Sun": "सूर्य", "Moon": "चंद्र", "Mars": "मंगल", "Mercury": "बुध", "Jupiter": "गुरु",
    "Venus": "शुक्र", "Saturn": "शनि", "Rahu": "राहु", "Ketu": "केतु",
    "Surya": "सूर्य", "Chandra": "चंद्र", "Mangal": "मंगल", "Budh": "बुध", "Guru": "गुरु",
    "Shukra": "शुक्र", "Shani": "शनि",
    # elements
    "Fire": "अग्नि", "Earth": "पृथ्वी", "Air": "वायु", "Water": "जल",
}
_TOK_SORTED = sorted(TOK, key=len, reverse=True)
_TOK_RE = re.compile(r"(?<![A-Za-z])(" + "|".join(re.escape(t) for t in _TOK_SORTED) + r")(?![A-Za-z])")
_ASCII_LETTER = re.compile(r"[A-Za-z]")


def _tok_line(key):
    """If every alphabetic word in `key` is a known proper-noun token, return the
    fully Devanagari-substituted string; else None."""
    out = _TOK_RE.sub(lambda m: TOK[m.group(1)], key)
    return out if not _ASCII_LETTER.search(out) else None


# ---------------------------------------------------------------- small maps
MONTHS = {"Jan": "जनवरी", "Feb": "फ़रवरी", "Mar": "मार्च", "Apr": "अप्रैल",
          "May": "मई", "Jun": "जून", "Jul": "जुलाई", "Aug": "अगस्त",
          "Sep": "सितंबर", "Oct": "अक्तूबर", "Nov": "नवंबर", "Dec": "दिसंबर"}
_MON_RE = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b")

# compact planet codes used inside the North-Indian chart grid
PCODE = {"Su": "सू", "Mo": "चं", "Ma": "मं", "Me": "बु", "Ju": "गु",
         "Ve": "शु", "Sa": "श", "Ra": "रा", "Ke": "के"}
_PCODE_RE = re.compile(r"\b(Su|Mo|Ma|Me|Ju|Ve|Sa|Ra|Ke)\b")

GRADE = {"STRONG": "मज़बूत", "MODERATE": "मध्यम", "BUILDING": "निर्माणाधीन",
         "QUIET": "शांत", "ACTIVE": "सक्रिय", "MILD": "हल्का", "NEUTRAL": "सामान्य",
         "Strong": "मज़बूत", "Moderate": "मध्यम", "Building": "निर्माणाधीन",
         "Quiet": "शांत", "Active": "सक्रिय", "Mild": "हल्का"}

DIGNITY = {"own": "अपना", "exalted": "उच्च", "debilitated": "नीच",
           "neutral": "सामान्य", "retro": "वक्री", "combust": "अस्त",
           "own, retro": "अपना, वक्री"}


def _months_line(s):
    """Translate a run whose only ASCII words are month abbreviations / grade words."""
    out = _MON_RE.sub(lambda m: MONTHS[m.group(1)], s)
    out = re.sub(r"\b(STRONG|MODERATE|BUILDING|QUIET|ACTIVE|MILD|NEUTRAL|Strong|Moderate|Building|Quiet|Active|Mild)\b",
                 lambda m: GRADE[m.group(1)], out)
    return out if not _ASCII_LETTER.search(out) else None


# ---------------------------------------------------------------- run matcher
_PAIRS = sorted(HI.items(), key=lambda kv: -len(kv[0]))
_SEG = re.compile(r">([^<>]+)<")
_EMO = r"\U0001F000-\U0001FAFF☀-➿←-⇿⬀-⯿️‍⭐✦✕"
_TRAIL = re.compile(rf"^(.*?)(\s*[{_EMO}]+)\s*$")
_LEAD = re.compile(rf"^([{_EMO}]+\s*)(.*)$")
_QUOTED = re.compile(r'^([“"\'])(.*)([”"\'])$', re.DOTALL)
_SKIP = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)


def _t(s):
    s = s.strip()
    if s in HI:
        return HI[s]
    return _tok_line(s)


def _tt(s):
    return _t(s) or s


# ---- the 12 "Meeting context" phrases keyed by 7th-lord house (1..12) ----
MEETING = [
    "आपकी अपनी पहल या ख़ुद की कोशिशों से",
    "परिवार के नेटवर्क या धन-संपत्ति से",
    "भाई-बहन, पड़ोसी, या छोटी यात्राओं से",
    "घर के दायरे या माँ के पक्ष से",
    "सामाजिक मौक़ों, बच्चों के आयोजनों, या पहले रोमांस से",
    "कार्यस्थल या रोज़मर्रा के दायरों से",
    "सीधे प्रस्तावों से — साझेदारी-प्रेरित",
    "ससुराल के नेटवर्क या रूपांतरकारी परिस्थितियों से",
    "दूर के स्थानों, शिक्षा के दायरों, या किसी अलग समुदाय से",
    "करियर की परिस्थितियों या पिता के नेटवर्क से",
    "दोस्तों के दायरे से — किसी दोस्त के ज़रिए परिचय",
    "शांत या निजी परिस्थितियों से, शायद कुछ दूरी पर",
]


_HINDI_PLANET = {"Surya", "Chandra", "Mangal", "Budh", "Guru", "Shukra", "Shani",
                 "Rahu", "Ketu", "Sun", "Moon", "Mars", "Mercury", "Jupiter",
                 "Venus", "Saturn"}

# venus_style suffixes (engine.py) → Devanagari, applied after the base love-style
_VENUS_SUFFIX = [
    (" — Venus combust hai, isliye expression mein hesitation aa sakti hai; feelings genuine, awaaz dheemi.",
     " — शुक्र अस्त है, इसलिए ज़ाहिर करने में झिझक आ सकती है; भावनाएँ सच्ची, आवाज़ धीमी।"),
    (" — Venus apne hi sign mein strong hai; pyaar mein aapki instinct par bharosa kiya ja sakta hai.",
     " — शुक्र अपनी ही राशि में मज़बूत है; प्रेम में आपकी सहज-प्रवृत्ति पर भरोसा किया जा सकता है।"),
]


def _dasha_side(s):
    """'Venus + Sun + Moon' -> 'शुक्र + सूर्य + चंद्र' if all planets, else None."""
    parts = [x.strip() for x in s.split("+")]
    if all(p in TOK for p in parts):
        return " + ".join(TOK[p] for p in parts)
    return None


def _template(key):
    """Interpolated / structured patterns → Devanagari, or None."""
    # cover method line
    m = re.match(r"^Generated (.+?) · NASA JPL data \(Swiss Ephemeris\) · Lahiri ayanamsa · Whole-sign houses · (.+)$", key)
    if m:
        note = HI.get(m.group(2), m.group(2))
        return (f"निर्मित {_months_line(m.group(1)) or m.group(1)} · NASA JPL डेटा (Swiss Ephemeris) · "
                f"लाहिरी अयनांश · पूर्ण-राशि भाव · {note}")
    # Sade Sati fact (fragments around the <b>date</b>)
    if key == "Sade Sati is currently running (peak phase), until":
        return "साढ़ेसाती अभी चल रही है (शिखर चरण), जब तक"
    m = re.match(r"^Sade Sati is currently running \((.+?) phase\), until$", key)
    if m:
        ph = {"rising": "आरंभिक", "peak": "शिखर", "setting": "उतरता"}.get(m.group(1), m.group(1))
        return f"साढ़ेसाती अभी चल रही है ({ph} चरण), जब तक"
    if key.startswith(". This tends to bring a maturing pressure rather than denial"):
        return ("। यह इनकार नहीं, बल्कि परिपक्व करने वाला दबाव लाती है — शनि के दौर में बने विवाह "
                "सबसे टिकाऊ माने जाते हैं।")
    # dasha-remedy reasons (engine _dasha_remedies)
    m = re.match(r"^(\w+) is debilitated in the birth chart — its periods ask for extra patience and care\.$", key)
    if m and m.group(1) in TOK:
        return f"{TOK[m.group(1)]} जन्म कुंडली में नीच है — इसकी दशाएँ अतिरिक्त धैर्य और सावधानी माँगती हैं।"
    m = re.match(r"^(\w+) is combust \(too close to the Sun\) — its influence is quieter during its periods\.$", key)
    if m and m.group(1) in TOK:
        return f"{TOK[m.group(1)]} अस्त है (सूर्य के बहुत पास) — इसकी दशाओं में इसका प्रभाव मंद रहता है।"
    m = re.match(r"^(\w+) has no direct link to the 7th house — a slower, low-activation period for marriage\.$", key)
    if m and m.group(1) in TOK:
        return f"{TOK[m.group(1)]} का 7वें भाव से सीधा संबंध नहीं — विवाह के लिए धीमा, कम-सक्रियता वाला दौर।"
    # gemstone line (base + optional trial suffix)
    m = re.match(r"^(.+?) — only if (\w+) is well-placed( — only after a trial, via a qualified jeweller/astrologer\.)?$", key)
    if m and m.group(2) in TOK:
        tail = "। केवल परीक्षण के बाद, किसी योग्य जौहरी/ज्योतिषी के ज़रिए।" if m.group(3) else ""
        return f"{m.group(1)} — केवल यदि {TOK[m.group(2)]} अच्छी स्थिति में हो{tail}"
    # navamsa (D9) reason patterns (interpolated planet/dignity)
    m = re.match(r"^Your 7th lord \((\w+)\) is vargottama \(same sign in D1 and D9\) — a strong marriage promise\.$", key)
    if m and m.group(1) in TOK:
        return f"आपके 7वें भाव का स्वामी ({TOK[m.group(1)]}) वर्गोत्तम है (D1 और D9 में एक ही राशि) — मज़बूत विवाह-वादा।"
    m = re.match(r"^In D9 the 7th lord \((\w+)\) holds good dignity \((\w+)\)\.$", key)
    if m and m.group(1) in TOK:
        return f"D9 में 7वें भाव का स्वामी ({TOK[m.group(1)]}) अच्छी स्थिति में है ({DIGNITY.get(m.group(2), m.group(2))})।"
    m = re.match(r"^Venus is strong in D9 \((\w+)\)\.$", key)
    if m:
        return f"शुक्र D9 में मज़बूत है ({DIGNITY.get(m.group(1), m.group(1))})।"
    m = re.match(r"^In D9 the 7th lord \((\w+)\) is debilitated — a little extra care around timing\.$", key)
    if m and m.group(1) in TOK:
        return f"D9 में 7वें भाव का स्वामी ({TOK[m.group(1)]}) नीच है — समय पर थोड़ा अतिरिक्त ध्यान।"
    # bare nakshatra title "<Nak> (<symbol>)" — symbol has a space/slash, which
    # distinguishes it from "<Sign> (vargottama)" handled elsewhere.
    m = re.match(r"^([A-Z][a-z]+(?: [A-Z][a-z]+)*) \((.+)\)$", key)
    if m and m.group(1) in TOK and (" " in m.group(2) or "/" in m.group(2)):
        return f"{TOK[m.group(1)]} ({HI.get(m.group(2), m.group(2))})"
    # ---- report_view_v2 (English base) interpolated patterns ----
    m = re.match(r"^Full window: (.+)$", key)
    if m and _MON_RE.search(m.group(1)):
        return f"पूरी विंडो: {_months_line(m.group(1)) or m.group(1)}"
    m = re.match(r"^After that: (.+?) \((Strong|Moderate|Building)\)$", key)
    if m:
        return f"उसके बाद: {_months_line(m.group(1)) or m.group(1)} ({GRADE[m.group(2)]})"
    m = re.match(r"^(.+?) onwards$", key)
    if m and _MON_RE.search(m.group(1)):
        return f"{_months_line(m.group(1)) or m.group(1)} से आगे"
    m = re.match(r"^Darakaraka \((\w+)\)$", key)
    if m and m.group(1) in TOK:
        return f"दारकारक ({TOK[m.group(1)]})"
    m = re.match(r"^Your nakshatra: (.+?) \((.+?)\)$", key)
    if m:
        return f"आपका नक्षत्र: {TOK.get(m.group(1), m.group(1))} ({HI.get(m.group(2), m.group(2))})"
    m = re.match(r"^Support for your 7th lord \((\w+)\)$", key)
    if m and m.group(1) in TOK:
        return f"आपके 7वें भाव के स्वामी ({TOK[m.group(1)]}) के लिए सहारा"
    m = re.match(r"^(.+) — 108 times, on (\w+)$", key)
    if m:
        return f"{m.group(1)} — 108 बार, {HI.get(m.group(2), m.group(2))} को"
    m = re.match(r"^(\w+) (Mahadasha|Antardasha) · (.+)$", key)
    if m and m.group(1) in TOK:
        role = "महादशा" if m.group(2) == "Mahadasha" else "अंतर्दशा"
        return f"{TOK[m.group(1)]} {role} · {_months_line(m.group(3)) or m.group(3)}"
    m = re.match(r"^(\w+)-type — see the partner pages$", key)
    if m and m.group(1) in TOK:
        return f"{TOK[m.group(1)]}-प्रकार — जीवनसाथी वाले पन्ने देखें"
    m = re.match(r"^The connection may come through (.+)\.$", key)
    if m and m.group(1) in HI:
        return f"यह रिश्ता जुड़ सकता है — {HI[m.group(1)]}।"
    m = re.match(r"^The detailed report breaks down your last (\d+) years period by period, and the next three years month by month\.$", key)
    if m:
        return (f"विस्तृत रिपोर्ट आपके बीते {m.group(1)} साल को दौर-दर-दौर, और अगले तीन साल को "
                f"महीने-दर-महीने खोलती है।")
    m = re.match(r"^Technical: Mars from Lagna — (clear|in a Manglik house); from Moon — (clear|in a Manglik house)\.$", key)
    if m:
        conv = {"clear": "स्पष्ट", "in a Manglik house": "मांगलिक भाव में"}
        return f"तकनीकी: लग्न से मंगल — {conv[m.group(1)]}; चंद्र से — {conv[m.group(2)]}।"
    # planet dignity fact "<Planet> — <dignity phrase already in HI>"
    m = re.match(r"^(\w+) — (.+)$", key)
    if m and m.group(1) in TOK and m.group(2) in HI:
        return f"{TOK[m.group(1)]} — {HI[m.group(2)]}"
    # bare grade badge
    if key in GRADE:
        return GRADE[key]
    # "(Grade)" alone
    m = re.match(r"^\((Strong|Moderate|Building|Quiet|Active|Mild)\)$", key)
    if m:
        return f"({GRADE[m.group(1)]})"
    # "{GRADE} WINDOW" / "NO MAJOR WINDOW"
    if key == "NO MAJOR WINDOW":
        return "कोई बड़ी विंडो नहीं"
    m = re.match(r"^(STRONG|MODERATE|BUILDING|QUIET|ACTIVE|MILD) WINDOW$", key)
    if m:
        return f"{GRADE[m.group(1)]} विंडो"
    # "N points" / "N.5 points"
    m = re.match(r"^([\d.]+) points$", key)
    if m:
        return f"{m.group(1)} अंक"
    # "{Planet} 7th house mein"
    m = re.match(r"^(\w+) 7th house mein$", key)
    if m and m.group(1) in TOK:
        return f"{TOK[m.group(1)]} 7वें भाव में"
    # "{Sign} (vargottama)"
    m = re.match(r"^(\w+) \(vargottama\)$", key)
    if m and m.group(1) in TOK:
        return f"{TOK[m.group(1)]} (वर्गोत्तम)"
    # "{Planet}-type — see page 7"
    m = re.match(r"^(\w+)-type — see page 7$", key)
    if m and m.group(1) in TOK:
        return f"{TOK[m.group(1)]}-प्रकार — पेज 7 देखें"
    # "till <Mon YYYY>"
    m = re.match(r"^till (.+)$", key)
    if m and _MON_RE.search(m.group(1)):
        return f"{_months_line(m.group(1))} तक"
    # dignity combos: "own, retro", "exalted, combust", ...
    if re.fullmatch(r"(own|exalted|debilitated|neutral|retro|combust)(, (own|exalted|debilitated|neutral|retro|combust))*", key):
        return ", ".join(DIGNITY[x.strip()] for x in key.split(","))
    # ---- date ranges & month/grade-only runs ----
    if _MON_RE.search(key):
        # "Uske baad: <dates> (Grade)"
        m = re.match(r"^Uske baad: (.+?) \((Strong|Moderate|Building|Quiet|Active|Mild)\)$", key)
        if m:
            return f"उसके बाद: {_months_line(m.group(1)) or m.group(1)} ({GRADE[m.group(2)]})"
        mm = _months_line(key)
        if mm is not None:
            return mm
    # dasha: "X MD — Y[ + Z ...] AD"  (single or multi antardasha)
    m = re.match(r"^(\w+) MD [—-] (.+) AD$", key)
    if m and m.group(1) in TOK:
        ad = _dasha_side(m.group(2))
        if ad is not None:
            return f"{TOK[m.group(1)]} महादशा — {ad} अंतर्दशा"
    m = re.match(r"^(\w+) Mahadasha [—-] (\w+) Antardasha$", key)
    if m and m.group(1) in TOK and m.group(2) in TOK:
        return f"{TOK[m.group(1)]} महादशा — {TOK[m.group(2)]} अंतर्दशा"
    # "Yeh window (<dasha>) ko humne"
    m = re.match(r"^Yeh window \((.+?)\) ko humne$", key)
    if m:
        inner = _resolve(m.group(1), 5)
        if inner is not None:
            return f"इस विंडो ({inner}) को हमने"
    # dignity phrase tail: "{Planet} — <dignity phrase in HI/DIGNITY>"
    m = re.match(r"^(\w+) — (.+)$", key)
    if m and m.group(1) in _HINDI_PLANET and m.group(1) in TOK:
        rest = _resolve(m.group(2), 5)
        if rest is not None:
            return f"{TOK[m.group(1)]} — {rest}"
    # planet dasha-combo joins: "Mercury–Rahu", "Mercury–Rahu / Mercury–Jupiter"
    if re.fullmatch(r"[A-Za-z]+(–[A-Za-z]+)?( / [A-Za-z]+(–[A-Za-z]+)?)*", key):
        parts = re.split(r"( / |–)", key)
        out = "".join(TOK.get(x, x) if x not in (" / ", "–") else x for x in parts)
        if not _ASCII_LETTER.search(out):
            return out
    # compact chart planet-codes: "Su Me Ve Ke", "Ju* Sa", "Mo Ra", "Sa↺"
    if re.fullmatch(r"(?:[A-Z][a-z][*↺]?\s*)+", key.strip()):
        out = _PCODE_RE.sub(lambda mm: PCODE[mm.group(1)], key)
        if not _ASCII_LETTER.search(out):
            return out
    # "Window N"
    m = re.match(r"^Window (\d+)$", key)
    if m:
        return f"विंडो {m.group(1)}"
    # "Window N (dates): Head"  → head is in HI
    m = re.match(r"^Window (\d+) \((.+?)\): (.+)$", key)
    if m:
        dates = _months_line(m.group(2)) or m.group(2)
        head = HI.get(m.group(3), m.group(3))
        return f"विंडो {m.group(1)} ({dates}): {head}"
    # "Core period: <dates>"
    m = re.match(r"^Core period: (.+)$", key)
    if m:
        return f"मुख्य अवधि: {_months_line(m.group(1)) or m.group(1)}"
    # "Top window: <dates> (Grade)"
    m = re.match(r"^Top window: (.+)$", key)
    if m:
        return f"सबसे मज़बूत विंडो: {_months_line(m.group(1)) or m.group(1)}"
    # "⭐ Strongest months: ..."/"⭐ Favourable months: ..."
    m = re.match(r"^⭐ Strongest months: (.+)$", key)
    if m:
        return f"⭐ सबसे मज़बूत महीने: {_months_line(m.group(1)) or m.group(1)}"
    m = re.match(r"^⭐ Favourable months: (.+)$", key)
    if m:
        return f"⭐ अनुकूल महीने: {_months_line(m.group(1)) or m.group(1)}"
    # "7th house — SIGN:"
    m = re.match(r"^7th house — (\w+):$", key)
    if m and m.group(1) in TOK:
        return f"7वाँ भाव — {TOK[m.group(1)]}:"
    # "Darakaraka PLANET:"
    m = re.match(r"^Darakaraka (\w+):$", key)
    if m and m.group(1) in TOK:
        return f"दारकारक {TOK[m.group(1)]}:"
    # "7th lord in house N suggests the connection may come through that area of life — PHRASE."
    m = re.match(r"^7th lord in house (\d+) suggests the connection may come through that area of life — (.+)\.$", key)
    if m:
        n = int(m.group(1))
        if 1 <= n <= 12:
            return (f"7वें भाव का स्वामी {n}वें भाव में होने से इशारा है कि रिश्ता ज़िंदगी "
                    f"के उस हिस्से से आ सकता है — {MEETING[n-1]}।")
    # dignity tails: "PLANET — neutral", "PLANET — neutral dignity", "PLANET — own", ...
    m = re.match(r"^(\w+) — (neutral|own|exalted|debilitated)( dignity)?$", key)
    if m and m.group(1) in TOK:
        dg = DIGNITY[m.group(2)]
        return f"{TOK[m.group(1)]} — {dg}" + (" गरिमा" if m.group(3) else "")
    # "SL — <dignity_txt>" handled in HI (dignity_txt full phrases are literals)
    # "Aapka nakshatra: NAME (SYMBOL)"
    m = re.match(r"^Aapka nakshatra: (.+?) \((.+?)\)$", key)
    if m:
        nm = TOK.get(m.group(1), m.group(1))
        sym = HI.get(m.group(2), m.group(2))
        return f"आपका नक्षत्र: {nm} ({sym})"
    # ---- Navamsa (D9) interpolated reasons ----
    m = re.match(r"^aapka 7th lord \((\w+)\) vargottama hai \(D1 aur D9 mein ek hi rashi\) — marriage promise strong$", key)
    if m and m.group(1) in TOK:
        return (f"आपका 7वें भाव का स्वामी ({TOK[m.group(1)]}) वर्गोत्तम है "
                f"(D1 और D9 में एक ही राशि) — मैरिज प्रॉमिस मज़बूत")
    m = re.match(r"^D9 mein 7th lord \((\w+)\) apni acchi dignity mein hai \((\w+)\)$", key)
    if m and m.group(1) in TOK:
        return f"D9 में 7वें भाव का स्वामी ({TOK[m.group(1)]}) अपनी अच्छी स्थिति में है ({DIGNITY.get(m.group(2), m.group(2))})"
    m = re.match(r"^Venus D9 mein strong hai \((\w+)\)$", key)
    if m:
        return f"शुक्र D9 में मज़बूत है ({DIGNITY.get(m.group(1), m.group(1))})"
    m = re.match(r"^D9 mein 7th lord \((\w+)\) debilitated hai — timing par thoda extra dhyaan$", key)
    if m and m.group(1) in TOK:
        return f"D9 में 7वें भाव का स्वामी ({TOK[m.group(1)]}) नीच है — समय पर थोड़ा अतिरिक्त ध्यान"
    # occupants: "P1, P2 — yeh partnership ke rang ko sabse seedha shape dete hain:"
    m = re.match(r"^(.+) — yeh partnership ke rang ko sabse seedha shape dete hain:$", key)
    if m:
        pls = [x.strip() for x in m.group(1).split(",")]
        if all(p in TOK for p in pls):
            return (", ".join(TOK[p] for p in pls) +
                    " — ये साझेदारी के रंग को सबसे सीधे आकार देते हैं:")
    # sade-sati next phase: "Next phase <date> se. Filhaal Shani ka is angle se koi delay-pressure nahi."
    m = re.match(r"^Next phase (.+) se\. Filhaal Shani ka is angle se koi delay-pressure nahi\.$", key)
    if m:
        d = _months_line(m.group(1)) or m.group(1)
        return f"अगला चरण {d} से। फ़िलहाल शनि का इस एंगल से कोई देरी-दबाव नहीं।"
    # venus love-style: "Your love-style is <base>[<suffix>]."
    m = re.match(r"^Your love-style is (.+)$", key)
    if m:
        inner = m.group(1).rstrip(".").strip()
        for en_suf, hi_suf in _VENUS_SUFFIX:
            en = en_suf.rstrip(".")
            if inner.endswith(en):
                base = inner[:-len(en)].strip()
                if base in HI:
                    return f"आपकी प्रेम-शैली {HI[base]}{hi_suf}"
        if inner in HI:
            return f"आपकी प्रेम-शैली {HI[inner]} है।"
    # generic "... (Moderate)" / "... (Building)" grade suffix on a date line
    m = re.match(r"^(.+) \((Strong|Moderate|Building|Quiet|Active|Mild)\)$", key)
    if m:
        inner = _resolve(m.group(1), 5)
        if inner is not None:
            return f"{inner} ({GRADE[m.group(2)]})"
    return None


def _resolve(key, depth=0):
    key = key.strip()
    if not key or depth > 5:
        return None
    if key in HI:
        return HI[key]
    # trailing sentence period: content-map cards render "<phrase>." — resolve the
    # phrase and re-add a Devanagari full stop. Guard against decimals (e.g. "8.5").
    if key.endswith(".") and not re.search(r"\d\.$", key):
        inner = _resolve(key[:-1], depth + 1)
        if inner is not None:
            return inner + ("।" if not inner.endswith(("।", ".", "!", "?")) else "")
    q = _QUOTED.match(key)
    if q and q.group(2).strip():
        inner = _resolve(q.group(2), depth + 1)
        if inner is not None:
            return q.group(1) + inner + q.group(3)
    le = _LEAD.match(key)
    if le and le.group(2).strip():
        inner = _resolve(le.group(2), depth + 1)
        if inner is not None:
            return le.group(1) + inner
    te = _TRAIL.match(key)
    if te and te.group(1).strip():
        inner = _resolve(te.group(1), depth + 1)
        if inner is not None:
            return inner + " " + te.group(2).strip()
    # " · "-separated lists (rule why-lists, legends): resolve each atom
    if " · " in key:
        parts = key.split(" · ")
        res = [_resolve(pp, depth + 1) for pp in parts]
        if all(r is not None for r in res):
            return " · ".join(res)
    # ", "-separated lists (e.g. manglik cancellation reasons) — only if every
    # part independently resolves (prose with commas won't, so it's left alone)
    if ", " in key and " · " not in key and len(key.split(", ")) <= 4:
        parts = key.split(", ")
        res = [_resolve(pp, depth + 1) for pp in parts]
        if all(r is not None for r in res):
            return ", ".join(res)
    tk = _tok_line(key)
    if tk is not None:
        return tk
    return _template(key)


def _neutralize_toggle(html):
    """On a Devanagari page/report the client Hinglish↔English swap must not run
    (it would replace Devanagari nodes like 'नहीं' via the EXACT map). Force the
    saved language to 'hi' everywhere the funnel defaults to 'en', and hide the
    in-page Hinglish/English capsule (language is fixed by URL for /hi/*)."""
    html = html.replace("var l = localStorage.getItem('axlang') || 'en';",
                        "var l = 'hi';")
    html = html.replace("var saved='en'; try{ saved=localStorage.getItem('axlang')||'en'; }catch(e){}",
                        "var saved='hi';")
    html = html.replace("var saved='en';try{saved=localStorage.getItem('axlang')||'en';}catch(e){}",
                        "var saved='hi';")
    return html


def localize(html):
    """Translate the Hinglish shell of a rendered page/report to Devanagari."""
    holds = []

    def _hold(m):
        holds.append(m.group(0))
        return f"\x00{len(holds)-1}\x00"
    tmp = _SKIP.sub(_hold, html)

    def _tr(m):
        raw = m.group(1)
        # collapse internal whitespace so multi-line source runs match the dict keys
        key = re.sub(r"\s+", " ", _htmlmod.unescape(raw.strip()))
        lead = raw[:len(raw) - len(raw.lstrip())]
        tail = raw[len(raw.rstrip()):]
        hi = _resolve(key)
        if hi is not None:
            return ">" + lead + hi + tail + "<"
        return m.group(0)
    tmp = _SEG.sub(_tr, tmp)

    tmp = re.sub(r"\x00(\d+)\x00", lambda m: holds[int(m.group(1))], tmp)

    tmp = _neutralize_toggle(tmp)
    tmp = tmp.replace('<html lang="hi-IN"', '<html lang="hi"', 1)
    tmp = tmp.replace('<html lang="en"', '<html lang="hi"', 1)
    if "</head>" in tmp:
        tmp = tmp.replace("</head>", _HEAD_HI + "</head>", 1)
    return tmp


_HEAD_HI = (
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Mukta:wght@400;500;600;700;800'
    '&family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap" rel="stylesheet">'
    "<style>:root{--display:'Mukta','Noto Sans Devanagari',system-ui,sans-serif;"
    "--body:'Noto Sans Devanagari','Mukta',system-ui,sans-serif;"
    "--disp:'Mukta','Noto Sans Devanagari',system-ui,sans-serif}"
    "#axlang{display:none!important}</style>"
)
