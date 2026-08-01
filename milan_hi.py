"""
milan_hi.py — server-side Devanagari (Hindi) localisation for the milan v2 report.

The v2 renderer (milan_v2.render_milan_v2) is authored in English. For a Hindi
buyer (report meta.lang == 'hi') we run the rendered HTML through a safe,
exact-text-node translation pass: only whole visible text runs are swapped, using
the HI dictionary below. Anything not in the dictionary is left untouched — so:

  * Devanagari LLM prose from narrative.py (already Hindi) passes through unchanged.
  * Names, numbers, scores, dates and emojis pass through unchanged.
  * Nothing inside <script>/<style>/tag-attributes is ever touched.

This covers the FIXED SHELL of the report (section titles, labels, the traditional
checks, timing, toolkit, proof, method glossary, certificate, CTA). Chart-VARIABLE
interpretive prose (koota texts, remedies, nakshatra lines) is best delivered by the
LLM narrative layer in Devanagari; strings not yet in HI simply remain English, so
the report degrades gracefully rather than breaking. Extend HI to raise coverage.

Wiring (api.py): after render_milan_v2(payload), if payload meta.lang == 'hi',
call localize(html).
"""
import re
import html as _htmlmod
from milan_hi_data import HI_DATA

# --------------------------------------------------------------------------- #
# Devanagari dictionary. Keys are the EXACT visible English text runs emitted by
# milan_v2 (trimmed). Western numerals and %/scores are kept as-is.
# --------------------------------------------------------------------------- #
HI = {
    # ---- hero / verdict ----
    "✦ Axtroshastra · Love Compatibility": "✦ Axtroshastra · लव कम्पैटिबिलिटी",
    "COMPATIBLE": "कम्पैटिबल",
    "Excellent Match": "बेहतरीन मैच",
    "Very Good Match": "बहुत अच्छा मैच",
    "Good Match": "अच्छा मैच",
    "Workable Match": "बन सकने वाला मैच",
    "Needs Work": "मेहनत चाहिए",

    # ---- 5-area summary (section 01) ----
    "At a glance": "एक नज़र में",
    "How you match, in 5 areas": "आप कैसे मैच करते हैं, 5 क्षेत्रों में",
    "Strongest first": "सबसे मज़बूत पहले",
    "Mind & Values": "सोच और मूल्य",
    "Health & Vitality": "सेहत और जीवनशक्ति",
    "Everyday Vibe": "रोज़मर्रा का तालमेल",
    "Chemistry & Attraction": "कैमिस्ट्री और आकर्षण",
    "Love & Long-Term": "प्यार और लंबा साथ",
    "🌱 Your growth area — the good news: it’s the most fixable one":
        "🌱 आपका ग्रोथ एरिया — अच्छी बात: यही सबसे आसानी से सुधरने वाला है",

    # ---- section eyebrows / titles / subtitles ----
    "Your green flags": "आपके ग्रीन फ्लैग",
    "Why you two work": "आप दोनों की जोड़ी क्यों बनती है",
    "The strengths worth celebrating 💚": "जश्न मनाने लायक ताक़तें 💚",
    "YOUR SUPERPOWER": "आपकी सुपरपावर",
    "Your playbook": "आपकी गाइड",
    "One thing worth working on": "एक चीज़ जिस पर काम करने लायक है",
    "Small effort, big payoff": "थोड़ी मेहनत, बड़ा फ़ायदा",
    "The honest answer": "ईमानदार जवाब",
    "Will it last?": "क्या ये टिकेगा?",
    "Yes — with intention.": "हाँ — थोड़ी सोच-समझ के साथ।",
    "The full reading": "पूरी रीडिंग",
    "Where it begins": "जहाँ से शुरू होता है",
    "The two of you": "आप दोनों",
    "You know your Sun sign. For love, we read your Moon.":
        "आप अपनी सूर्य राशि जानते हैं। प्यार के लिए हम आपकी चंद्र राशि पढ़ते हैं।",
    "Your growth area, decoded": "आपका ग्रोथ एरिया, समझाया हुआ",
    "The play": "क्या करें",
    "What it measures": "ये क्या मापता है",
    "Why you aced it": "आपने इसमें कमाल क्यों किया",
    "How to protect it": "इसे कैसे बचाए रखें",
    "Keep the good thing good": "अच्छी चीज़ को अच्छा बनाए रखें",
    "Even strengths need light care": "ताक़तों को भी थोड़ी देखभाल चाहिए",
    "The only risk with easy harmony…": "आसान तालमेल का इकलौता ख़तरा…",
    "Your strongest factor": "आपका सबसे मज़बूत फ़ैक्टर",
    "A quiet superpower": "एक ख़ामोश सुपरपावर",

    # ---- labels used across pages ----
    "🎯 Try this week": "🎯 इस हफ़्ते ये करें",
    "🎯 Try this fortnight": "🎯 इस पखवाड़े ये करें",
    "💬 Say this": "💬 ये कहें",
    "✅ Green flag you’ll notice": "✅ एक ग्रीन फ्लैग जो आप महसूस करेंगे",
    "🌿 Honour both roles": "🌿 दोनों की भूमिका का सम्मान करें",

    # ---- whole picture (section 16) ----
    "The whole picture": "पूरी तस्वीर",
    "Your relationship, in one breath": "आपका रिश्ता, एक साँस में",
    "Two people": "दो लोग",
    "deeply built to last": "गहराई से टिकने के लिए बने",
    "have": "पहले से है",
    "grow into": "बढ़कर पा लेते हैं",
    "That’s not a fragile match. It’s a strong one, with a clear path.":
        "ये कोई कमज़ोर मैच नहीं है। ये एक मज़बूत मैच है, एक साफ़ रास्ते के साथ।",

    # ---- traditional checks (section 17) ----
    "The traditional checks": "पारंपरिक जाँचें",
    "The three big ones": "तीन बड़ी जाँचें",
    "Demystified — no fear, just facts": "बिना रहस्य के — कोई डर नहीं, सिर्फ़ तथ्य",
    "Manglik (Mangal Dosha)": "मांगलिक (मंगल दोष)",
    "Nadi Dosha": "नाड़ी दोष",
    "Bhakoot Dosha": "भकूट दोष",
    "Read them as information to understand, not verdicts to fear.":
        "इन्हें समझने की जानकारी की तरह पढ़ें, डरने का फ़ैसला मानकर नहीं।",

    # ---- timing (section 18) ----
    "Auspicious timing": "शुभ समय",
    "Good moments": "अच्छे पल",
    "General guidance — not chart-specific dates": "सामान्य मार्गदर्शन — किसी ख़ास कुंडली की तारीख़ें नहीं",
    "For commitments": "प्रतिबद्धता के लिए",
    "Fridays and full-moon days are traditionally warm for love and vows.":
        "शुक्रवार और पूर्णिमा के दिन परंपरा में प्रेम और वचनों के लिए शुभ माने जाते हैं।",
    "For a new beginning": "नई शुरुआत के लिए",
    "Start something together on a rising-moon fortnight for a settled, growing start.":
        "किसी नई चीज़ की शुरुआत शुक्ल पक्ष में करें — एक टिकाऊ, बढ़ती शुरुआत के लिए।",
    "For travel together": "साथ यात्रा के लिए",
    "Shared journeys deepen your bond — try to plan one each season.":
        "साथ की यात्राएँ आपके रिश्ते को गहरा करती हैं — हर मौसम में एक की योजना बनाएँ।",

    # ---- toolkit (sections 19-20) ----
    "What to actually do": "असल में क्या करें",
    "Your toolkit — the actions": "आपका टूलकिट — काम की बातें",
    "The real levers, in one place": "असली तरीक़े, एक जगह",
    "The first remedy is always action. Do one this week.":
        "पहला उपाय हमेशा कर्म है। इस हफ़्ते एक ज़रूर करें।",
    "Optional · the traditional touch": "वैकल्पिक · पारंपरिक स्पर्श",
    "If you like the rituals": "अगर आपको रीति-रिवाज पसंद हैं",
    "A cultural add-on — never a substitute for the actions":
        "एक सांस्कृतिक जोड़ — काम की बातों का विकल्प कभी नहीं",
    "Mutual Pull": "आपसी खिंचाव",
    "Luck & Wellbeing": "सौभाग्य और कुशलता",
    "Physical Chemistry": "शारीरिक कैमिस्ट्री",

    # ---- proof (section 21) ----
    "The proof": "प्रमाण",
    "How this was calculated": "यह कैसे कैलकुलेट किया गया",
    "Not guessed. Computed.": "अंदाज़ा नहीं। गणना।",
    "Your real sky, at birth": "आपका असली आकाश, जन्म के समय",
    "The 1000-year-old method": "1000 साल पुरानी विधि",
    "No opinions, only calculation": "कोई राय नहीं, सिर्फ़ गणना",
    "Jyotish, calculated — no opinion, only calculation.":
        "ज्योतिष, कैलकुलेटेड — कोई राय नहीं, सिर्फ़ गणना।",

    # ---- what the score means (section 22) ----
    "A map, not a verdict": "एक नक्शा, फ़ैसला नहीं",
    "It’s one input, not the whole story": "ये एक इनपुट है, पूरी कहानी नहीं",
    "The pattern matters more than the number": "नंबर से ज़्यादा पैटर्न मायने रखता है",
    "Numbers don’t marry people": "नंबर लोगों से शादी नहीं करते",

    # ---- note (section 23) ----
    "A note for you": "आपके लिए एक बात",
    "From us to you": "हमारी ओर से आपके लिए",
    "A note to the couple": "जोड़े के नाम एक संदेश",
    "— Your astrologer, Axtroshastra": "— आपका ज्योतिषी, Axtroshastra",

    # ---- certificate (section 24) ----
    "Yours to keep": "यह हमेशा आपका रहेगा",
    "Compatibility Certificate": "कम्पैटिबिलिटी सर्टिफ़िकेट",
    "“According to Vedic astrology, this relationship holds warm and auspicious potential.”":
        "“वैदिक ज्योतिष के अनुसार, इस रिश्ते में गर्मजोशी और शुभ संभावनाएँ हैं।”",

    # ---- CTA (section 25) ----
    "One last thing": "आख़िरी एक बात",
    "Know a couple who’d love this?": "कोई ऐसा जोड़ा जानते हैं जिसे ये पसंद आएगा?",
    "Every reading is calculated from real charts — no two alike":
        "हर रीडिंग असली कुंडली से कैलकुलेट होती है — कोई दो एक जैसी नहीं",
    "Gift a friend their reading 💛": "किसी दोस्त को उनकी रीडिंग गिफ़्ट करें 💛",
    "Start a reading →": "एक रीडिंग शुरू करें →",

    # ---- appendix (sections 26-30) ----
    "Appendix · The receipts": "परिशिष्ट · हिसाब-किताब",
    "Nothing hidden": "कुछ नहीं छिपाया",
    "The Calculations": "गणनाएँ",
    "Every number in this report, shown its working":
        "इस रिपोर्ट का हर नंबर, उसकी पूरी गणना के साथ",
    "It starts with your exact birth details — turned into the real position of the Moon.":
        "यह आपकी सटीक जन्म जानकारी से शुरू होता है — जिसे चंद्रमा की असली स्थिति में बदला जाता है।",
    "Kundli Milan is Moon-based — these two Moon positions drive every score.":
        "कुंडली मिलान चंद्रमा-आधारित है — यही दो चंद्र स्थितियाँ हर स्कोर तय करती हैं।",
    "Appendix · The 8 scores": "परिशिष्ट · 8 स्कोर",
    "Shown, one by one": "एक-एक करके दिखाए गए",
    "How each score was made": "हर स्कोर कैसे बना",
    "Factors 1–4 · every score is a rule, not an opinion":
        "फ़ैक्टर 1–4 · हर स्कोर एक नियम है, राय नहीं",
    "…and factors 5–8": "…और फ़ैक्टर 5–8",
    "Then simply added up": "फिर बस जोड़ दिए गए",
    # koota names + meanings (appendix rows)
    "· work-ego compatibility": "· काम और अहं का तालमेल",
    "· mutual influence and pull": "· आपसी प्रभाव और खिंचाव",
    "· health and wellbeing of the bond": "· रिश्ते की सेहत और कुशलता",
    "· physical and instinctive harmony": "· शारीरिक और सहज तालमेल",
    "· mental wavelength and friendship": "· मानसिक तरंग और दोस्ती",
    "· temperament match": "· स्वभाव का मेल",
    "· emotional bond, family growth": "· भावनात्मक बंधन, परिवार की वृद्धि",
    "· health of progeny, vitality": "· संतान की सेहत, जीवनशक्ति",
    "Appendix · The dosha checks": "परिशिष्ट · दोष जाँचें",
    "The three big ones, shown": "तीन बड़ी जाँचें, दिखाई गईं",
    "The dosha checks, calculated": "दोष जाँचें, कैलकुलेटेड",
    "How each verdict was reached": "हर फ़ैसले तक कैसे पहुँचा गया",
    "Manglik": "मांगलिक",
    "Both": "दोनों",
    "Manglik if Mars ∈ houses {1,2,4,7,8,12} from Moon.":
        "मांगलिक तब, जब चंद्रमा से मंगल भाव {1,2,4,7,8,12} में हो।",
    "Present": "मौजूद",
    "Dosha only on a 2/12, 5/9, or 6/8 axis.": "दोष सिर्फ़ 2/12, 5/9 या 6/8 अक्ष पर।",
    "Same rules, applied the same way, for every couple.":
        "एक ही नियम, एक ही तरीक़े से, हर जोड़े पर लागू।",
    "Appendix · The method": "परिशिष्ट · विधि",
    "The fine print, in plain words": "बारीक बातें, आसान शब्दों में",
    "Method & glossary": "विधि और शब्दावली",
    "So you can check it yourself": "ताकि आप ख़ुद जाँच सकें",
    "Verify it yourself": "ख़ुद जाँच कर देखिए",
    "The math is yours. The stars did the rest.": "गणित आपका है। बाक़ी सितारों ने किया।",

    # ---- sticky actions ----
    "⬇ Download PDF": "⬇ PDF डाउनलोड करें",
    "Share on WhatsApp": "WhatsApp पर शेयर करें",

    # ---- common connectors seen as standalone nodes ----
    "· the sign the world knows you by": "· वह राशि जिससे दुनिया आपको जानती है",
    "· your love sign": "· आपकी प्रेम राशि",

    # ---- repeated "protect it" template (fixed for every strong theme) ----
    "The unglamorous, foundational fit a lot of couples never have — you begin with it built in.":
        "वह साधारण-सी, बुनियादी अनुकूलता जो बहुत से जोड़ों को कभी नहीं मिलती — आपके पास शुरू से ही है।",
    "is taking it for granted. When this comes naturally, couples stop being intentional — and let routine quietly replace connection.":
        "इसे हल्के में लेना है। जब ये सहज होता है, तो जोड़े सोच-समझकर चलना छोड़ देते हैं — और रोज़मर्रा चुपचाप जुड़ाव की जगह ले लेती है।",
    "You laugh off the small stuff — and neither keeps score.":
        "आप छोटी बातों पर हँस देते हैं — और कोई हिसाब नहीं रखता।",
    "You don’t need to fix this one. Just don’t sleepwalk through how good it is.":
        "इसे ठीक करने की ज़रूरत नहीं। बस ये कितना अच्छा है, इसे यूँ ही मत जाने दें।",

    # ---- toolkit action headers ----
    "🧲 For mutual pull": "🧲 आपसी खिंचाव के लिए",
    "🍀 For luck & wellbeing": "🍀 सौभाग्य और कुशलता के लिए",
    "🔥 For physical chemistry": "🔥 शारीरिक कैमिस्ट्री के लिए",
    "❤️ For emotional bond": "❤️ भावनात्मक बंधन के लिए",

    # ---- score-means (section 22) ----
    "Read this before you worry": "चिंता करने से पहले ये पढ़ें",

    # ---- proof paragraphs (section 21, fixed) ----
    "We computed the true positions of the Moon and planets from your two birth details — NASA-grade astronomy (Swiss Ephemeris), sidereal zodiac, Lahiri ayanamsa.":
        "हमने आप दोनों की जन्म जानकारी से चंद्रमा और ग्रहों की असली स्थिति की गणना की — NASA-स्तर की खगोल विद्या (Swiss Ephemeris), निरयन राशिचक्र, लाहिरी अयनांश।",
    "Your match runs on the classical Ashtakoota (36-guna) system — your two Moon positions across 8 factors, dosha rules applied exactly.":
        "आपका मिलान शास्त्रीय अष्टकूट (36-गुण) प्रणाली पर चलता है — आप दोनों की चंद्र स्थितियाँ 8 फ़ैक्टरों में, दोष नियम ठीक वैसे ही लागू।",
    "Every number here traces to your charts — not a horoscope generality or an astrologer’s mood.":
        "यहाँ का हर नंबर आपकी कुंडली से आता है — किसी राशिफल की आम बात या ज्योतिषी के मूड से नहीं।",

    # ---- appendix intro + koota names (sections 26-28) ----
    "longitude ÷ 30° = Rashi (sign) · ÷ 13°20′ = Nakshatra · ÷ 3°20′ = Pada":
        "देशांतर ÷ 30° = राशि · ÷ 13°20′ = नक्षत्र · ÷ 3°20′ = पद",
    "Varna": "वर्ण", "Vashya": "वश्य", "Tara": "तारा", "Yoni": "योनि",
    "Graha Maitri": "ग्रह मैत्री", "Gana": "गण", "Bhakoot": "भकूट", "Nadi": "नाड़ी",

    # ---- appendix dosha verdict cells ----
    "Clear ✓": "कोई दोष नहीं ✓",
    "Dosha only if identical → cleared.": "दोष सिर्फ़ तभी जब बिल्कुल एक जैसे हों → साफ़।",

    # ---- method glossary (section 30) ----
    "Rashi": "राशि", "Nakshatra": "नक्षत्र", "Guna": "गुण", "Dosha": "दोष", "Ayanamsa": "अयनांश",
    "— your Moon’s zodiac sign (÷30° of the sky)": "— आपकी चंद्र राशि (आकाश का ÷30°)",
    "— the lunar mansion (÷13°20′), pinned to real stars": "— नक्षत्र (÷13°20′), असली तारों से जुड़ा",
    "— a compatibility point; 36 is the maximum": "— एक मिलान अंक; अधिकतम 36",
    "— a classical caution flag (Manglik, Nadi, Bhakoot)": "— एक शास्त्रीय चेतावनी (मांगलिक, नाड़ी, भकूट)",
    "— the star-based correction (Lahiri) making it sidereal":
        "— तारा-आधारित सुधार (लाहिरी) जो इसे निरयन बनाता है",
    "Put these birth details into any Lahiri-based panchang — the Moon positions will match, exactly. That’s the point: no opinion, only calculation.":
        "इन जन्म विवरणों को किसी भी लाहिरी-आधारित पंचांग में डालें — चंद्र स्थितियाँ बिल्कुल मिलेंगी। यही तो बात है: कोई राय नहीं, सिर्फ़ गणना।",

    # ---- archetype names + taglines (element-pair based; hero/certificate/share) ----
    "The Passionate Pair": "जोशीली जोड़ी",
    "Two sparks, double the passion": "दो चिंगारियाँ, दोगुना जोश",
    "The Steady Pair": "स्थिर जोड़ी",
    "Steady, safe, built to last": "स्थिर, सुरक्षित, टिकने के लिए बनी",
    "The Best Friends": "पक्के दोस्त",
    "Endless talks, always on the same page": "अंतहीन बातें, हमेशा एक सुर में",
    "The Deep Feelers": "गहरे एहसास वाले",
    "You feel everything, together": "आप हर चीज़ साथ महसूस करते हैं",
    "Passion Meets Patience": "जोश मिले धीरज से",
    "Drive meets steadiness": "रफ़्तार मिले ठहराव से",
    "The Adventurers": "सैलानी जोड़ी",
    "Energy that keeps growing": "ऊर्जा जो बढ़ती रहती है",
    "The Magnetic Pair": "चुंबकीय जोड़ी",
    "Strong pull, strong feelings": "गहरा खिंचाव, गहरे एहसास",
    "The Dreamer & The Builder": "सपने और हक़ीक़त",
    "Ideas meet real plans": "विचार मिलें असली योजनाओं से",
    "The Caring Pair": "ख़याल रखने वाली जोड़ी",
    "The most naturally caring match": "सबसे स्वाभाविक रूप से ख़याल रखने वाला मैच",
    "Head & Heart": "दिमाग़ और दिल",
    "Clear thinking meets deep feeling": "साफ़ सोच मिले गहरे एहसास से",
    "One of a Kind": "अपने आप में अनोखी",
    "Your own kind of match": "आपके अपने ढंग का मैच",
}
HI.update(HI_DATA)

# --------------------------------------------------------------------------- #
# Proper-noun TOKENS (signs, nakshatras, yoni animals, planets, nadis, ganas,
# varnas, elements). These appear standalone and in combinatorial pairs
# ("Rat – Cow", "Leo · Magha", "Venus – Sun"). Applied token-wise, but ONLY to a
# node whose every alphabetic word is a known token — so prose is never touched.
# --------------------------------------------------------------------------- #
TOK = {
    # signs (English)
    "Aries": "मेष", "Taurus": "वृषभ", "Gemini": "मिथुन", "Cancer": "कर्क",
    "Leo": "सिंह", "Virgo": "कन्या", "Libra": "तुला", "Scorpio": "वृश्चिक",
    "Sagittarius": "धनु", "Capricorn": "मकर", "Aquarius": "कुंभ", "Pisces": "मीन",
    # signs (Sanskrit)
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
    # planets
    "Sun": "सूर्य", "Moon": "चंद्र", "Mars": "मंगल", "Mercury": "बुध", "Jupiter": "गुरु",
    "Venus": "शुक्र", "Saturn": "शनि", "Rahu": "राहु", "Ketu": "केतु",
    # yoni animals
    "Buffalo": "भैंस", "Cat": "बिल्ली", "Cow": "गाय", "Deer": "हिरण", "Dog": "कुत्ता",
    "Elephant": "हाथी", "Horse": "घोड़ा", "Lion": "शेर", "Mongoose": "नेवला",
    "Monkey": "बंदर", "Rat": "चूहा", "Serpent": "साँप", "Sheep": "भेड़", "Tiger": "बाघ",
    # gana / varna / nadi
    "Deva": "देव", "Manushya": "मनुष्य", "Rakshasa": "राक्षस",
    "Brahmin": "ब्राह्मण", "Kshatriya": "क्षत्रिय", "Vaishya": "वैश्य", "Shudra": "शूद्र",
    "Adi": "आदि", "Madhya": "मध्य", "Antya": "अंत्य",
    # elements
    "Fire": "अग्नि", "Earth": "पृथ्वी", "Air": "वायु", "Water": "जल",
    # compound label word
    "Moon": "चंद्र",
}
_TOK_SORTED = sorted(TOK, key=len, reverse=True)
_TOK_RE = re.compile(r"(?<![A-Za-z])(" + "|".join(re.escape(t) for t in _TOK_SORTED) + r")(?![A-Za-z])")
# a node is "data-only" if, after token substitution, no ASCII letters remain
_ASCII_LETTER = re.compile(r"[A-Za-z]")


def _tok_line(key: str):
    """If every alphabetic word in `key` is a known proper-noun token, return the
    fully Devanagari-substituted string; else None (leave prose to the HI dict)."""
    out = _TOK_RE.sub(lambda m: TOK[m.group(1)], key)
    return out if not _ASCII_LETTER.search(out) else None


# Longest keys first so multi-word runs win before any short substring.
_PAIRS = sorted(HI.items(), key=lambda kv: -len(kv[0]))

_SEG = re.compile(r">([^<>]+)<")          # text runs between tags
_EMO = r"\U0001F000-\U0001FAFF☀-➿←-⇿⬀-⯿️‍"
_TRAIL = re.compile(rf"^(.*?)(\s*[{_EMO}]+)\s*$")   # "<text> <trailing emoji>"
_LEAD = re.compile(rf"^([{_EMO}]+\s*)(.*)$")        # "<leading emoji> <text>"
_QUOTED = re.compile(r'^([“"\'])(.*)([”"\'])$', re.DOTALL)  # wrapped in quotes
_SKIP = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)


def _t(s):
    """Translate a sub-part via HI (phrase) or proper-noun tokens; else None."""
    s = s.strip()
    if s in HI:
        return HI[s]
    return _tok_line(s)

def _tt(s):
    return _t(s) or s

def _tlist(s):
    return ", ".join(_tt(x) for x in s.split(", "))

_SUFFIX = {"protect it": "इसे बचाए रखें", "1 of 2": "1 / 2", "2 of 2": "2 / 2",
           "the play": "क्या करें"}


def _template(key):
    """Fixed wrappers with interpolated values (theme names, %, nadi tokens,
    nakshatra/element/planet). Returns Devanagari or None."""
    m = re.match(r"^(.+?) · (protect it|1 of 2|2 of 2|the play)$", key)
    if m and _t(m.group(1)):
        return f"{_t(m.group(1))} · {_SUFFIX[m.group(2)]}"
    m = re.match(r"^Your report flagged (.+?) as your growth area\. Here’s the real, computed reason — and it’s more interesting than it sounds\.$", key)
    if m:
        return (f"आपकी रिपोर्ट ने {_tt(m.group(1))} को आपका ग्रोथ एरिया बताया। यहाँ असली, कैलकुलेटेड "
                f"वजह है — और यह सुनने में जितनी लगती है उससे कहीं ज़्यादा दिलचस्प है।")
    m = re.match(r"^What (\d+)% really means$", key)
    if m:
        return f"{m.group(1)}% का असल मतलब"
    m = re.match(r"^(\d+)% · (.+)$", key)
    if m:
        return f"{m.group(1)}% · {_tt(m.group(2))}"
    m = re.match(r"^You’ve got a strong hand: (\d+)%, with your deepest foundations already solid\. Compatibility gets you to the start line; the playbook wins the race\.$", key)
    if m:
        return (f"आपके हाथ में मज़बूत पत्ते हैं: {m.group(1)}%, और आपकी सबसे गहरी नींव पहले से ठोस है। "
                f"अनुकूलता आपको शुरुआती रेखा तक लाती है; प्लेबुक रेस जिताता है।")
    m = re.match(r"^Countless lasting marriages began below (\d+)%\. Use the number as information, not a verdict\.$", key)
    if m:
        return (f"अनगिनत टिकाऊ शादियाँ {m.group(1)}% से नीचे शुरू हुई हैं। नंबर को जानकारी की तरह "
                f"इस्तेमाल करें, फ़ैसले की तरह नहीं।")
    m = re.match(r"^(\d+) of your 5 areas are naturally strong\.$", key)
    if m:
        return f"आपके 5 में से {m.group(1)} क्षेत्र स्वाभाविक रूप से मज़बूत हैं।"
    m = re.match(r"^You’re strong where it’s hardest to build — (.+)\.$", key)
    if m:
        return f"आप वहाँ मज़बूत हैं जहाँ बनाना सबसे कठिन है — {_tlist(m.group(1))}।"
    m = re.match(r"^— strong across (.+) — with one honest growth edge:$", key)
    if m:
        return f"— {_tlist(m.group(1))} में मज़बूत — एक ईमानदार ग्रोथ किनारे के साथ:"
    m = re.match(r"^Your two “Nadis” are different \((\w+) & (\w+)\) — the ideal, complementary result\. The single hardest factor to build if it’s missing, and you start with it fully intact\.$", key)
    if m:
        return (f"आपकी दोनों “नाड़ियाँ” अलग हैं ({_tt(m.group(1))} और {_tt(m.group(2))}) — आदर्श, पूरक "
                f"नतीजा। अगर यह न हो तो यह बनाना सबसे कठिन पहलू है, और आप इसे पूरी तरह बरक़रार लेकर शुरू करते हैं।")
    m = re.match(r"^Nadis differ \((\w+) vs (\w+)\)\.$", key)
    if m:
        return f"नाड़ियाँ अलग हैं ({_tt(m.group(1))} बनाम {_tt(m.group(2))})।"
    m = re.match(r"^Nadis are the same \((\w+)\)\.$", key)
    if m:
        return f"नाड़ियाँ समान हैं ({_tt(m.group(1))})।"
    m = re.match(r"^(.+?) · (Fire|Earth|Air|Water) · ruled by (\w+)$", key)
    if m and _t(m.group(1)):
        return f"{_t(m.group(1))} · {TOK.get(m.group(2), m.group(2))} · शासक {TOK.get(m.group(3), m.group(3))}"
    m = re.match(r"^Your nakshatra’s animal is the (\w+) — (.+)\.$", key)
    if m and m.group(1) in TOK:
        return f"आपके नक्षत्र का पशु {TOK[m.group(1)]} है — {_tt(m.group(2))}।"
    m = re.match(r"^(.+?) — (the (?:Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu) mind)$", key)
    if m:
        return f"{m.group(1)} — {_tt(m.group(2))}"
    m = re.match(r"^(.+?) — the (\w+) instinct$", key)
    if m and m.group(2) in TOK:
        return f"{m.group(1)} — {TOK[m.group(2)]} सहज-प्रवृत्ति"
    m = re.match(r"^(Agni \(fire\)|Prithvi \(earth\)|Vayu \(air\)|Jal \(water\)) meets (Agni \(fire\)|Prithvi \(earth\)|Vayu \(air\)|Jal \(water\))$", key)
    if m:
        return f"{_tt(m.group(1))} मिले {_tt(m.group(2))} से"
    m = re.match(r"^(Fire|Earth|Air|Water) · (.+)$", key)
    if m and _t(m.group(2)):
        return f"{TOK.get(m.group(1), m.group(1))} · {_t(m.group(2))}"
    m = re.match(r"^(\w+) & (\w+) — (a neutral pair|a perfect match|natural allies|natural opposites|different instincts)$", key)
    if m and m.group(1) in TOK and m.group(2) in TOK:
        return f"{TOK[m.group(1)]} और {TOK[m.group(2)]} — {_tt(m.group(3))}"
    # ---- name / planet / theme interpolated wrappers ----
    m = re.match(r"^(.+) ✕ (.+) — Love Compatibility$", key)
    if m:
        return f"{m.group(1)} ✕ {m.group(2)} — लव कम्पैटिबिलिटी"
    m = re.match(r"^(.+?) brings one energy, (.+?) brings another\. Let each lead where they’re natural instead of competing\.$", key)
    if m:
        return (f"{m.group(1)} एक तरह की ऊर्जा लाते हैं, {m.group(2)} दूसरी। दोनों को वहाँ अगुआई करने दें "
                f"जहाँ वे स्वाभाविक हैं, आपस में होड़ करने के बजाय।")
    m = re.match(r"^(.+?)’s instinct is to analyse and solve\. (.+?)’s is to sit with the feeling first\. Neither is wrong — they just need to meet in the middle, on purpose\.$", key)
    if m:
        return (f"{m.group(1)} की सहज-प्रवृत्ति है विश्लेषण करके सुलझाना। {m.group(2)} की है पहले भावना के "
                f"साथ ठहरना। कोई ग़लत नहीं — बस दोनों को जानबूझकर बीच का रास्ता निकालना है।")
    m = re.match(r"^Dear (.+?) & (.+?), your charts tell the story of a bond with real staying power\. Where you differ isn’t a crack — it’s the one place a little patience turns difference into depth\. You already have the rare thing\. Tend the rest gently, and you have the makings of a beautiful life together\.$", key)
    if m:
        return (f"प्रिय {m.group(1)} और {m.group(2)}, आपकी कुंडलियाँ एक ऐसे बंधन की कहानी कहती हैं जिसमें सच्चा "
                f"ठहराव है। जहाँ आप अलग हैं वह दरार नहीं — वही एक जगह है जहाँ थोड़ा धीरज फ़र्क़ को गहराई में बदल "
                f"देता है। दुर्लभ चीज़ आपके पास पहले से है। बाक़ी को कोमलता से सँभालें, और आपके पास एक ख़ूबसूरत "
                f"साथ की ज़िंदगी की नींव है।")
    m = re.match(r"^(\w+) and (\w+) aren’t natural friends in the classical system — that’s the actual, calculated reason your (.+?) score is low\. You connect deeply; you just run different operating systems\.$", key)
    if m:
        return (f"{TOK.get(m.group(1), m.group(1))} और {TOK.get(m.group(2), m.group(2))} शास्त्रीय प्रणाली में "
                f"स्वाभाविक मित्र नहीं हैं — यही असली, कैलकुलेटेड वजह है कि आपका {_tt(m.group(3))} स्कोर कम है। "
                f"आप गहराई से जुड़ते हैं; बस आप अलग ऑपरेटिंग सिस्टम पर चलते हैं।")
    m = re.match(r"^(🧭|🧠|🎭|🧬|❤️|🔥|🧲|🍀) For (.+)$", key)
    if m:
        theme_hi = _TOOLKIT_FOR.get(m.group(2).lower())
        if theme_hi:
            return f"{m.group(1)} {theme_hi}"
    m = re.match(r"^(.+?) \+ (.+?), bridged, is poetry\. Once (.+?) learns not everything is logic, and (.+?) learns not everything needs saying — you don’t just communicate\. You complete each other\.$", key)
    if m:
        return (f"{_tt(m.group(1))} + {_tt(m.group(2))}, जोड़ दिए जाएँ तो कविता है। जब {m.group(3)} सीख ले "
                f"कि हर चीज़ तर्क नहीं होती, और {m.group(4)} सीख ले कि हर बात अनकही नहीं रह सकती — तो आप सिर्फ़ "
                f"बात नहीं करते। आप एक-दूसरे को पूरा करते हैं।")
    m = re.match(r"^(.+?) carries a (\w+) \((.+?)\) temperament, (.+?) a (\w+) \((.+?)\) one — a pairing that reads the same emotional weather\. No walking on eggshells\.$", key)
    if m:
        return (f"{m.group(1)} में {_tt(m.group(2))} ({_tt(m.group(3))}) स्वभाव है, {m.group(4)} में "
                f"{_tt(m.group(5))} ({_tt(m.group(6))}) — एक ऐसी जोड़ी जो एक ही भावनात्मक मौसम पढ़ती है। "
                f"कोई एहतियात नहीं बरतनी पड़ती।")
    m = re.match(r"^(.+?) carries a (\w+) \((.+?)\) temperament, (.+?) a (\w+) \((.+?)\) one\. Let each lead where they’re natural instead of competing\.$", key)
    if m:
        return (f"{m.group(1)} में {_tt(m.group(2))} ({_tt(m.group(3))}) स्वभाव है, {m.group(4)} में "
                f"{_tt(m.group(5))} ({_tt(m.group(6))})। दोनों को वहाँ अगुआई करने दें जहाँ वे स्वाभाविक हैं, "
                f"होड़ के बजाय।")
    return None


_TOOLKIT_FOR = {
    "mutual pull": "आपसी खिंचाव के लिए",
    "luck & wellbeing": "सौभाग्य और कुशलता के लिए",
    "physical chemistry": "शारीरिक कैमिस्ट्री के लिए",
    "emotional bond": "भावनात्मक बंधन के लिए",
    "drive & ego balance": "जोश और अहं के संतुलन के लिए",
    "vibe & temperament": "अंदाज़ और स्वभाव के लिए",
    "mental wavelength": "मानसिक तरंग के लिए",
    "health & family": "सेहत और परिवार के लिए",
}


def _resolve(key, depth=0):
    """Translate a whole text run to Devanagari, or None. Handles wrappers
    (surrounding quotes, leading/trailing emoji) recursively, then falls back to
    proper-noun tokens and templated patterns."""
    key = key.strip()
    if not key or depth > 4:
        return None
    if key in HI:
        return HI[key]
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
    for pre, hpre in (("Optional ritual: ", "वैकल्पिक रीति: "), ("Optional: ", "वैकल्पिक: ")):
        if key.startswith(pre):
            inner = _resolve(key[len(pre):], depth + 1)
            if inner is not None:
                return hpre + inner
    tk = _tok_line(key)
    if tk is not None:
        return tk
    return _template(key)


def localize(html: str) -> str:
    """Translate the fixed English shell of a rendered milan v2 report to Devanagari.
    Safe: only whole text runs present in HI are swapped; scripts/styles/attrs and
    any unknown text (incl. Devanagari LLM prose, names, numbers) are left as-is."""
    # protect <script>/<style> blocks
    holds = []
    def _hold(m):
        holds.append(m.group(0)); return f"\x00{len(holds)-1}\x00"
    tmp = _SKIP.sub(_hold, html)

    def _tr(m):
        raw = m.group(1)
        key = _htmlmod.unescape(raw.strip())
        lead = raw[:len(raw) - len(raw.lstrip())]
        tail = raw[len(raw.rstrip()):]
        hi = _resolve(key)
        if hi is not None:
            return ">" + lead + hi + tail + "<"
        return m.group(0)
    tmp = _SEG.sub(_tr, tmp)

    # restore protected blocks
    tmp = re.sub(r"\x00(\d+)\x00", lambda m: holds[int(m.group(1))], tmp)

    # Devanagari rendering: set lang + retarget the report's --disp/--body font vars
    # to Devanagari-capable webfonts (Mukta for display, Noto Sans Devanagari for body).
    tmp = tmp.replace('<html lang="en"', '<html lang="hi"', 1)
    tmp = tmp.replace("</head>", _HEAD_HI + "</head>", 1)
    tmp = _flip_lang_toggle(tmp)
    return tmp


def _flip_lang_toggle(html: str) -> str:
    """On the Devanagari compatibility landing, make the हिंदी control active.
    The English source (milan.html) ships the URL toggle EN-active; regenerating
    the Hindi page must flip it so हिंदी is the current locale — automatically,
    with no manual re-edit. No-op anywhere the compatibility toggle isn't present
    (e.g. reports), so it's safe to run on every localize()."""
    m = re.search(r'<div id="axlang"[^>]*>.*?</div>', html, re.S)
    if not m or '/en/compatibility' not in m.group(0):
        return html
    new = ('<div id="axlang" data-axlang="hi">'
           '<a href="/en/compatibility" hreflang="en">EN</a>'
           '<a class="on" href="/hi/compatibility" aria-current="page">हिंदी</a></div>')
    return html[:m.start()] + new + html[m.end():]


_HEAD_HI = (
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Mukta:wght@400;500;600;700;800'
    '&family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap" rel="stylesheet">'
    "<style>:root{--disp:'Mukta','Noto Sans Devanagari',system-ui,sans-serif;"
    "--body:'Noto Sans Devanagari','Mukta',system-ui,sans-serif}</style>"
)
