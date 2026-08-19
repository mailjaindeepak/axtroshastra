"""
career_growth_hi.py — Hindi (Devanagari) localisation for the career_growth
product: both the free-preview teaser (POST /api/kundli's response.teaser)
and the full paid report (career_growth_report.render_career_growth's HTML
output, served at /report/{rid} and reused by the PDF/WhatsApp pipeline).

Two mechanisms, matching what each surface needs:

1. translate_teaser(teaser) — the teaser is a small JSON dict (not HTML), so
   this does exact-value dictionary lookups directly on the dict's values.
   Every value compute_career_growth() can put there is drawn from a small,
   fixed set of Python constants in career_growth_report.py, so coverage is
   exact, not degraded.

2. localize(html) — the full report is a large, per-person HTML document
   (28 sections, English text banks interpolated with real chart data). This
   follows the exact same "safe, exact-text-node translation pass" milan_hi.py
   and shaadi_hi.py already use in production: only whole visible text runs
   present in the HI dict are swapped; anything else (names, dates, numbers,
   and — deliberately, see below — a handful of long prose sentences that
   interleave open-ended dynamic data with static English) is left as-is
   rather than guessed at, so the report degrades gracefully instead of ever
   shipping mangled or half-translated Hindi.

Wiring (api.py):
  - create_kundli(): after compute_career_growth() returns and lang == 'hi',
    call translate_teaser(report["teaser"]) before returning it.
  - _render_for(): after render_career_growth(payload) and lang == 'hi',
    call localize(html).

Scope of localize(): every section title, subtitle, card label, stat label,
and every value drawn from career_growth_report's enumerable text banks
(FIELD_FAMILIES, ABOUT_YOU_TRAITS, WORKPLACE_TEXT, the Job/Own-Business
verdict, WEALTH_2L, GAINS_11L, HIGHERED_HOUSE, LAGNA_PERSONA, PLANET_GIFT,
PLANET_LESSON, MD_PHASE, planet/day/month names, remedy mantras) is
translated. A handful of sentences that splice an open-ended, non-enumerable
value (a formatted date range, the rules-engine's free-text "why" explanation)
into the middle of an English sentence are NOT translated — enumerating every
combination isn't tractable and rewriting them would risk the working English
report. This mirrors milan_hi.py's own documented scope boundary for
chart-variable interpretive prose.
"""
import re
import html as _htmlmod

# ===========================================================================
# TEASER (JSON dict) translation
# ===========================================================================

MONTHS_HI = {
    "Jan": "जनवरी", "January": "जनवरी",
    "Feb": "फ़रवरी", "February": "फ़रवरी",
    "Mar": "मार्च", "March": "मार्च",
    "Apr": "अप्रैल", "April": "अप्रैल",
    "May": "मई",
    "Jun": "जून", "June": "जून",
    "Jul": "जुलाई", "July": "जुलाई",
    "Aug": "अगस्त", "August": "अगस्त",
    "Sep": "सितंबर", "September": "सितंबर",
    "Oct": "अक्तूबर", "October": "अक्तूबर",
    "Nov": "नवंबर", "November": "नवंबर",
    "Dec": "दिसंबर", "December": "दिसंबर",
}

PHASE_HI = {
    "Move Now": "अभी आगे बढ़ें",
    "Wait & Prepare": "इंतज़ार और तैयारी",
}

VERDICT_BLURRED_HI = {
    "Job, not Own Business": "नौकरी, अपना बिज़नेस नहीं",
    "Own Business, not a Job": "अपना बिज़नेस, नौकरी नहीं",
}

# Exact order/values must match career_growth_report.FIELD_FAMILIES.
FIELD_FAMILIES_HI = {
    "Technology & Engineering": "टेक्नोलॉजी और इंजीनियरिंग",
    "Product Management": "प्रोडक्ट मैनेजमेंट",
    "Data & Analytics": "डेटा और एनालिटिक्स",
    "Finance & Banking": "फाइनेंस और बैंकिंग",
    "Operations": "ऑपरेशंस",
    "Consulting": "कंसल्टिंग",
    "Sales & Business Development": "सेल्स और बिज़नेस डेवलपमेंट",
    "Marketing & Brand": "मार्केटिंग और ब्रांड",
    "Client Relations": "क्लाइंट रिलेशंस",
    "Real Estate & Assets": "रियल एस्टेट और एसेट्स",
    "Manufacturing": "मैन्युफैक्चरिंग",
    "Supply Chain": "सप्लाई चेन",
    "Education & Training": "शिक्षा और ट्रेनिंग",
    "Content & Media": "कंटेंट और मीडिया",
    "Design": "डिज़ाइन",
    "Healthcare Administration": "हेल्थकेयर एडमिनिस्ट्रेशन",
    "HR & People": "HR और पीपल",
    "Legal & Compliance": "लीगल और कंप्लायंस",
    "Startups & New Ventures": "स्टार्टअप्स और नए वेंचर",
    "Growth & Strategy": "ग्रोथ और स्ट्रैटेजी",
    "Research & Analysis": "रिसर्च और एनालिसिस",
    "Higher Education": "उच्च शिक्षा",
    "Cross-Border Roles": "विदेश से जुड़े काम",
    "General Management": "जनरल मैनेजमेंट",
    "Public Relations": "पब्लिक रिलेशंस",
    "Non-Profit / Social Impact": "गैर-लाभकारी / सामाजिक काम",
}

FIELD_ANTIFIT_NOTE_HI = [
    "बार-बार एक जैसा, बैक-ऑफिस वाला काम जिसमें कोई नयापन न हो",
    "सख्त नियमों वाला, कम आज़ादी वाला ऑपरेशनल काम",
    "बिल्कुल अकेला, कम बातचीत वाला तकनीकी काम",
    "तेज़ी से बदलने वाला, बिना तय ढांचे वाला माहौल",
    "ज़्यादा टकराव और मुक़ाबले वाला माहौल",
    "ढीले-ढाले, अनिश्चित काम",
    "धीमी रफ़्तार वाले, बहुत पदानुक्रम वाले संगठन",
    "सिर्फ़ लोगों से जुड़ा, कम सोच-विचार वाला काम",
    "सीमित, सिर्फ़ एक हुनर पर टिका काम",
    "अफ़रा-तफ़री वाला, बिना दिशा वाला शुरुआती माहौल",
    "अलग-थलग, कम दिखने वाला बैक-एंड काम",
    "सख्त नियमों वाला, सिर्फ़ आँकड़ों पर टिका, कम रचनात्मकता वाला काम",
]

# ABOUT_YOU_TRAITS[i]["strength"] values, in lagna-sign order (Aries..Pisces) —
# these become teaser["quote"]. Matches career_growth_report.ABOUT_YOU_TRAITS.
TEASER_QUOTE_HI = {
    "A natural first-mover with real initiative.": "असली पहलक़दमी वाला एक जन्मजात अगुआ।",
    "A steady hand others build on.": "एक भरोसेमंद सहारा, जिस पर दूसरे टिक सकें।",
    "A clear, persuasive communicator.": "साफ़ और असरदार तरीके से बात करने वाला।",
    "A trusted, steady presence under pressure.": "दबाव में भी भरोसेमंद और स्थिर मौजूदगी।",
    "A natural, credible leader.": "एक जन्मजात, भरोसेमंद नेता।",
    "A dependable problem-solver.": "एक भरोसेमंद समस्या-सुलझाने वाला।",
    "A natural relationship-builder.": "रिश्ते बनाने में माहिर।",
    "Genuine strategic depth.": "असली रणनीतिक गहराई।",
    "A big-picture thinker who inspires others.": "बड़ी तस्वीर देखने वाला, जो दूसरों को प्रेरित करता है।",
    "Genuine staying power.": "असली टिके रहने की ताकत।",
    "An original, future-facing thinker.": "एक मौलिक, भविष्य की सोच रखने वाला।",
    "A genuinely creative problem-solver.": "सच में रचनात्मक तरीके से समस्या सुलझाने वाला।",
}


def _translate_range(range_str: str) -> str:
    """'Jul 2025 – Sep 2028' -> 'जुलाई 2025 – सितंबर 2028'. Leaves years/dashes
    as-is; only swaps the English month abbreviations found in MONTHS_HI."""
    if not range_str or range_str == "—":
        return range_str
    out = range_str
    for en, hi in MONTHS_HI.items():
        out = out.replace(en, hi)
    return out


def translate_teaser(teaser: dict) -> dict:
    """Returns a new dict with known English enum values swapped for their
    Hindi equivalents. Unknown/unmapped values pass through unchanged — never
    raises, so an unrecognised value just ships in English rather than
    breaking the funnel."""
    if not teaser:
        return teaser
    t = dict(teaser)
    if t.get("phase") in PHASE_HI:
        t["phase"] = PHASE_HI[t["phase"]]
    if t.get("field_top") in FIELD_FAMILIES_HI:
        t["field_top"] = FIELD_FAMILIES_HI[t["field_top"]]
    if t.get("quote") in TEASER_QUOTE_HI:
        t["quote"] = TEASER_QUOTE_HI[t["quote"]]
    if t.get("verdict_h3_blurred") in VERDICT_BLURRED_HI:
        t["verdict_h3_blurred"] = VERDICT_BLURRED_HI[t["verdict_h3_blurred"]]
    if t.get("best_window_range"):
        t["best_window_range"] = _translate_range(t["best_window_range"])
    if t.get("do_by"):
        t["do_by"] = MONTHS_HI.get(t["do_by"], t["do_by"])
    return t


# ===========================================================================
# FULL REPORT (rendered HTML) translation
# ===========================================================================

PLANET_NAME_HI = {
    "Sun": "सूर्य", "Moon": "चंद्रमा", "Mars": "मंगल", "Mercury": "बुध",
    "Jupiter": "गुरु", "Venus": "शुक्र", "Saturn": "शनि", "Rahu": "राहु", "Ketu": "केतु",
}

DAY_HI = {
    "Sunday": "रविवार", "Monday": "सोमवार", "Tuesday": "मंगलवार",
    "Wednesday": "बुधवार", "Thursday": "गुरुवार", "Friday": "शुक्रवार", "Saturday": "शनिवार",
}

REMEDY_MANTRA_HI = {
    "Om Ghrini Suryaya Namah": "ॐ घृणि सूर्याय नमः",
    "Om Som Somaya Namah": "ॐ सों सोमाय नमः",
    "Om Ang Angarakaya Namah": "ॐ अं अंगारकाय नमः",
    "Om Bum Budhaya Namah": "ॐ बुं बुधाय नमः",
    "Om Brim Brihaspataye Namah": "ॐ ब्रीं बृहस्पतये नमः",
    "Om Shum Shukraya Namah": "ॐ शुं शुक्राय नमः",
    "Om Sham Shanaishcharaya Namah": "ॐ शं शनैश्चराय नमः",
    "Om Ram Rahave Namah": "ॐ रां राहवे नमः",
    "Om Kem Ketave Namah": "ॐ कें केतवे नमः",
}

# products.LAGNA_PERSONA translations, Aries..Pisces order (zipped against the
# real source list in _build_hi() below — both raw and .capitalize()'d forms
# get added to HI since render_career_growth() emits both).
LAGNA_PERSONA_HI = [
    "सीधे, खुद शुरुआत करने वाले, मुक़ाबले के शौकीन — आप पहले कदम बढ़ाते हैं और तुरंत सोचते हैं",
    "स्थिर, संतुलित, धैर्यवान — आप धीरे-धीरे बनाते हैं और जो बनाया उसे संभाल कर रखते हैं",
    "जिज्ञासु, बातूनी, हरफ़नमौला — आप विचारों और बातचीत से जीते हैं",
    "रक्षा करने वाले, सहज-बोध वाले, यादों से जुड़े — आप दिल से आगे बढ़ते हैं",
    "गरिमामय, अभिव्यक्तिशील, उदार — आपको एक मंच और एक मक़सद चाहिए",
    "बारीकी वाले, विश्लेषणात्मक, सेवा-भाव वाले — आप जो भी छूते हैं उसे बेहतर बना देते हैं",
    "संतुलन बनाने वाले, रिश्तों में माहिर, सुंदरता-पसंद — आप साझेदारी में सोचते हैं",
    "गहरे, निजी, रणनीतिक — आप सिर्फ़ ढलते नहीं, बदल देते हैं",
    "विस्तार पसंद, सिद्धांतवादी, आज़ादी-पसंद — आप मक़सद के पीछे चलते हैं",
    "अनुशासित, महत्वाकांक्षी, टिकाऊ — आप दिनों में नहीं, सालों में तरक्की करते हैं",
    "स्वतंत्र, व्यवस्थित सोच वाले, इंसानियत-पसंद — आप भविष्य के हैं",
    "लचीले, संवेदनशील, कल्पनाशील — आप सब कुछ अपने अंदर समा लेते हैं, सीमाएँ मिटा देते हैं",
]

PLANET_GIFT_HI = {
    "Sun": "स्वाभाविक अधिकार", "Moon": "भावनाओं को समझने की समझ",
    "Mars": "हिम्मत और ताकत", "Mercury": "पैनी बातचीत",
    "Jupiter": "समझदारी और बढ़ती किस्मत", "Venus": "आकर्षण और सुंदरता की समझ",
    "Saturn": "सहनशक्ति और अनुशासन",
}
PLANET_LESSON_HI = {
    "Sun": "अहंकार और पहचान की चाहत", "Moon": "भावनाओं में स्थिरता",
    "Mars": "गुस्सा और जल्दबाज़ी", "Mercury": "बिखरा हुआ ध्यान",
    "Jupiter": "ज़्यादा आशावाद", "Venus": "ज़्यादा भोग-विलास",
    "Saturn": "देरी और खुद पर शक",
}
MD_PHASE_HI = {
    "authority, visibility, father-figures — a phase of standing in your own name":
        "अधिकार, पहचान, पिता-तुल्य लोग — यह अपने ही नाम पर खड़े होने का दौर है",
    "emotional recalibration, home, public connect — inner life leads outer":
        "भावनाओं का संतुलन, घर, लोगों से जुड़ाव — अंदर की ज़िंदगी बाहर की दिशा तय करती है",
    "drive, conflict-and-conquest, property, siblings — energy seeks a battlefield":
        "जोश, टकराव और जीत, ज़मीन-जायदाद, भाई-बहन — ऊर्जा को एक मैदान चाहिए",
    "ambition, unconventional rise, foreign elements — rapid but restless growth":
        "महत्वाकांक्षा, पटरी से हटकर तरक्की, विदेश से जुड़ाव — तेज़ पर बेचैन बढ़त",
    "wisdom, expansion, children, teachers — doors open through knowledge and faith":
        "समझदारी, विस्तार, बच्चे, गुरु — ज्ञान और भरोसे से दरवाज़े खुलते हैं",
    "discipline, karma-settlement, slow durable gains — what you build now stays":
        "अनुशासन, कर्मों का हिसाब, धीमे पर टिकाऊ फ़ायदे — अभी जो बनाएँगे, वह टिकेगा",
    "commerce, communication, learning — intellect becomes income":
        "व्यापार, बातचीत, सीखना — दिमाग़ ही कमाई बन जाता है",
    "detachment, spiritual sharpening, endings that liberate — less becomes more":
        "अलगाव, आध्यात्मिक निखार, ऐसा अंत जो आज़ाद करे — कम में ही ज़्यादा मिलता है",
    "relationships, comfort, creativity, wealth-enjoyment — life softens and sweetens":
        "रिश्ते, आराम, रचनात्मकता, धन का सुख — ज़िंदगी नरम और मीठी हो जाती है",
}

# jyotish_maps.WEALTH_2L translations, zipped against the real source list.
WEALTH_2L_HI = [
    "खुद की मेहनत से कमाई — आपकी आमदनी सीधे आपकी अपनी मेहनत और नाम से जुड़ी है",
    "पैसा जोड़ने की मज़बूत आदत — पैसा तभी बढ़ता है जब आप इसे खुद संभालें",
    "हुनर, बातचीत या हिम्मत से कमाई — पहल करने से आमदनी बढ़ती है",
    "संपत्ति बनाने का रुझान — ज़मीन, गाड़ी और घर से जुड़ा धन आपके लिए सही है",
    "रचनात्मकता, सट्टे या पढ़ाने से फ़ायदा — सोच-समझकर लिया गया जोखिम काम आ सकता है",
    "सेवा और समस्या सुलझाने से कमाई — स्थिर पर मुक़ाबले वाले क्षेत्र",
    "साझेदारी से धन — बिज़नेस पार्टनर और जीवनसाथी की किस्मत, दोनों मायने रखते हैं",
    "अचानक मिलने वाला फ़ायदा और दूसरों के संसाधन — बीमा, विरासत, बदलाव से जुड़ा पैसा",
    "ज्ञान, दूरी या धर्म से किस्मत — घर से दूर जाकर कमाई बढ़ती है",
    "करियर से जुड़ा धन — पद और रुतबा सीधे आमदनी बढ़ाते हैं",
    "बड़े नेटवर्क से फ़ायदा — दायरा जितना बड़ा, कमाई उतनी ज़्यादा",
    "कमाई के साथ खर्च भी — पैसा आता-जाता रहता है; विदेश या संस्थाओं से जुड़ाव पैसा टिकाए रखने में मदद करता है",
]
# jyotish_maps.GAINS_11L translations, zipped against the real source list.
GAINS_11L_HI = [
    "फ़ायदा खुद पहल करने से मिलता है — आपको माँगना, अप्लाई करना, शुरू करना होगा",
    "फ़ायदा बचत और परिवार के संसाधनों से मज़बूत होता है",
    "भाई-बहन, मीडिया, लेखन या छोटे उद्यमों से फ़ायदा",
    "ज़मीन-जायदाद, अपनी जगह और भावनात्मक स्थिरता से फ़ायदा",
    "बच्चों, छात्रों, रचनात्मकता या बाज़ार से फ़ायदा",
    "मेहनत और मुक़ाबले के बाद फ़ायदा — कमाया हुआ, कभी मुफ़्त में नहीं मिला",
    "साझेदारी और लोगों से जुड़े काम से फ़ायदा",
    "गहरी रिसर्च, दूसरों के पैसे, या अचानक मोड़ से फ़ायदा",
    "गुरुओं, उच्च शिक्षा और लंबी यात्राओं से फ़ायदा",
    "करियर में बेहतरीन काम से फ़ायदा — नाम ही इनाम बन जाता है",
    "फ़ायदे का मज़बूत संकेत — नेटवर्क आपकी हर बनाई चीज़ को बढ़ा देते हैं",
    "ऐसा फ़ायदा जो कहीं और तरक्की के काम आता है — फ़िज़ूलख़र्ची से बचें, इसे निवेश में लगाएँ",
]
# vidyarthi_maps.HIGHERED_HOUSE translations, zipped against the real source list.
HIGHERED_HOUSE_HI = [
    "उच्च शिक्षा में किस्मत आपकी अपनी पहल से जुड़ी है — स्कॉलरशिप और मौके उन्हें मिलते हैं जो कोशिश करते हैं, इंतज़ार करने वालों को नहीं",
    "उच्च शिक्षा के लिए परिवार का साथ लगातार मिलता है — संसाधन मौजूद हैं, बस इस्तेमाल करते रहें",
    "बातचीत से जुड़े क्षेत्रों में उच्च शिक्षा फ़ायदेमंद है — लेखन, मीडिया और भाषा से जुड़े कोर्स आपकी किस्मत से मेल खाते हैं",
    "आपकी उच्च शिक्षा की किस्मत भावनात्मक स्थिरता से जुड़ी है — घर में शांति सीधे पढ़ाई की किस्मत बढ़ाती है",
    "रचनात्मक और पटरी से हटकर पढ़ाई के रास्ते असली किस्मत लाते हैं — अगर पारंपरिक रास्ता सही न लगे तो खुद को उसमें मत बाँधिए",
    "उच्च शिक्षा मेहनत से मिलती है, शॉर्टकट से नहीं — मुक़ाबले वाले, सेवा-भाव वाले क्षेत्र आपको खासतौर पर फ़ायदा देते हैं",
    "साझेदारी और गुरु-मार्गदर्शन से किस्मत बनती है — सही शिक्षक या गाइड किसी भी परीक्षा से ज़्यादा आपकी दिशा बदल सकता है",
    "रिसर्च और विशेषज्ञता में आपकी असली किस्मत है — गहराई ज़्यादा मायने रखती है, फैलाव नहीं",
    "उच्च शिक्षा और गुरु-कृपा के लिए यह आपका सबसे मज़बूत भाव है — विदेश में पढ़ाई, लेखन या ऊँची डिग्री सच में फ़ायदेमंद हैं",
    "आपके लिए करियर और उच्च शिक्षा गहराई से जुड़े हैं — सही कोर्स चुनना असल में करियर चुनना है",
    "नेटवर्क और समुदाय उच्च शिक्षा के दरवाज़े खोलते हैं — साथ पढ़ने वालों और पुराने छात्रों से जुड़े मौके आपके लिए अच्छे हैं",
    "विदेश या किसी बड़ी संस्था से उच्च शिक्षा फ़ायदेमंद है — रास्ता पटरी से हटकर लग सकता है, पर किस्मत असली है",
]

# ABOUT_YOU_TRAITS (work_ethic, approach, attitude) — strength is TEASER_QUOTE_HI above.
ABOUT_YOU_WORK_ETHIC_HI = {
    "Fast-starting — you'd rather act than overplan.": "तेज़ शुरुआत करने वाले — आप ज़्यादा सोचने से बेहतर काम करना पसंद करते हैं।",
    "Hardworking — you finish what you start.": "मेहनती — आप जो शुरू करते हैं, उसे पूरा करते हैं।",
    "Quick-adapting — you pick up new work fast.": "जल्दी ढलने वाले — आप नया काम जल्दी सीख लेते हैं।",
    "Committed — you care about the outcome, not just the task.": "समर्पित — आपको सिर्फ़ काम नहीं, नतीजे की भी परवाह होती है।",
    "Driven — you want your work to actually matter.": "जोशीले — आप चाहते हैं कि आपका काम सच में मायने रखे।",
    "Precise — details matter to you more than most.": "बारीकी वाले — बाकियों से ज़्यादा आपको छोटी-छोटी बातें अहम लगती हैं।",
    "Balanced — you pace yourself for the long run.": "संतुलित — आप लंबी दौड़ के हिसाब से अपनी रफ़्तार रखते हैं।",
    "Intense — once committed, you go deep.": "गहरे — एक बार ठान लें तो पूरी गहराई से जुटते हैं।",
    "Expansive — you're motivated by meaning, not just tasks.": "बड़ी सोच वाले — काम नहीं, मक़सद आपको आगे बढ़ाता है।",
    "Structured — you climb in decades, not days.": "अनुशासित — आप दिनों में नहीं, सालों में तरक्की करते हैं।",
    "Independent — you work best on your own terms.": "स्वतंत्र — आप अपने तरीके से काम करके सबसे बेहतर करते हैं।",
    "Fluid — you adapt your effort to what the moment needs.": "लचीले — हालात के हिसाब से अपनी मेहनत ढाल लेते हैं।",
}
ABOUT_YOU_APPROACH_HI = {
    "Direct — you say what needs saying, early and plainly.": "सीधे — जो कहना हो, साफ़ और समय पर कह देते हैं।",
    "Reliable — people count on your follow-through.": "भरोसेमंद — लोगों को पता है, आप अपने काम में टिके रहते हैं।",
    "Communicative — you think out loud and in writing.": "बातचीत में माहिर — आप बोलकर और लिखकर सोचते हैं।",
    "Protective — you look out for your team as much as the work.": "ख़याल रखने वाले — आप काम जितना ही अपनी टीम का भी ध्यान रखते हैं।",
    "Visible — you lead from the front, not the sidelines.": "आगे रहने वाले — आप किनारे से नहीं, आगे से नेतृत्व करते हैं।",
    "Improving — you can't leave a process alone if it's inefficient.": "सुधार करने वाले — अगर कोई तरीका ठीक न हो, तो आप उसे यूँ ही नहीं छोड़ते।",
    "Collaborative — you work best alongside people, not around them.": "साथ मिलकर काम करने वाले — आप लोगों के साथ मिलकर सबसे बेहतर करते हैं, अकेले नहीं।",
    "Private, strategic — you play the long game quietly.": "निजी, रणनीतिक — आप चुपचाप लंबी सोच के साथ खेलते हैं।",
    "Principled — you say what you believe, even when inconvenient.": "सिद्धांतवादी — जो सही लगे, वही कहते हैं, चाहे मुश्किल ही क्यों न हो।",
    "Enduring — you outlast problems others give up on.": "टिके रहने वाले — जहाँ दूसरे हार मान लें, आप वहाँ भी डटे रहते हैं।",
    "Systemic — you think in structures, not just tasks.": "व्यवस्थित सोच वाले — आप सिर्फ़ काम नहीं, पूरा ढांचा सोचते हैं।",
    "Empathetic — you sense what a room needs before it's said.": "संवेदनशील — कहने से पहले ही भाँप लेते हैं कि माहौल को क्या चाहिए।",
}
ABOUT_YOU_ATTITUDE_HI = {
    "Bold and competitive — you want to win on merit, not politics.": "साहसी और मुक़ाबले के शौकीन — आप हुनर से जीतना चाहते हैं, सियासत से नहीं।",
    "Ambitious, but deliberate — not impulsive.": "महत्वाकांक्षी, लेकिन सोच-समझकर — जल्दबाज़ी नहीं।",
    "Curious and versatile — variety keeps you sharp.": "जिज्ञासु और हरफ़नमौला — विविधता आपको चौकस रखती है।",
    "Intuitive, loyalty-driven — you read situations before they're said.": "सहज-बोध वाले, वफ़ादार — कहने से पहले ही हालात भाँप लेते हैं।",
    "Confident and generous — you build others up while building yourself.": "आत्मविश्वासी और उदार — खुद आगे बढ़ते हुए दूसरों को भी आगे बढ़ाते हैं।",
    "Analytical and service-minded — competence over showmanship.": "विश्लेषणात्मक और सेवा-भाव वाले — दिखावे से ज़्यादा असली काबिलियत को मानते हैं।",
    "Diplomatic and fair — you weigh both sides before deciding.": "कूटनीतिक और निष्पक्ष — फैसला लेने से पहले दोनों पहलू तौलते हैं।",
    "Transformative — you'd rather rebuild than patch.": "बदलाव लाने वाले — जोड़-तोड़ से बेहतर, नए सिरे से बनाना पसंद करते हैं।",
    "Optimistic and freedom-loving — you need room to grow.": "आशावादी और आज़ादी-पसंद — आपको बढ़ने के लिए खुली जगह चाहिए।",
    "Ambitious and patient — status earned the hard way, not shortcut.": "महत्वाकांक्षी और धैर्यवान — रुतबा मेहनत से कमाया जाता है, शॉर्टकट से नहीं।",
    "Humanitarian and forward-looking — you build for more than yourself.": "इंसानियत-पसंद और आगे की सोच वाले — आप सिर्फ़ अपने लिए नहीं, बड़े मक़सद के लिए बनाते हैं।",
    "Imaginative and absorbing — you dissolve boundaries between roles.": "कल्पनाशील और सब कुछ समेट लेने वाले — आप भूमिकाओं की सीमाएँ मिटा देते हैं।",
}

WORKPLACE_HI = {
    "Diplomat": "सुलझाने वाले",
    "Confronter": "सीधा सामना करने वाले",
    "Outlaster": "डटे रहने वाले",
    "You resolve friction by finding the middle ground, not by pushing harder or "
    "waiting it out. This reads as a genuine strength in cross-functional or "
    "client-facing roles — less so in environments that reward blunt confrontation.":
        "आप बीच का रास्ता निकालकर झगड़ा सुलझाते हैं, न कि ज़्यादा दबाव डालकर या बस इंतज़ार करके। "
        "अलग-अलग टीमों के साथ काम करने या ग्राहकों से जुड़े काम में यह आपकी असली ताकत है — "
        "लेकिन उन जगहों पर कम काम आती है, जहाँ सीधी लड़ाई को अच्छा माना जाता है।",
    "Competition doesn't energise you the way collaboration does — you'll do "
    "your best work where success is measured in outcomes, not internal rivalry.":
        "होड़ आपको उतनी ऊर्जा नहीं देती, जितना मिलकर काम करना देता है — आप वहाँ सबसे अच्छा काम "
        "करेंगे जहाँ सफलता नतीजों से आँकी जाती है, अंदर की होड़ से नहीं।",
    "Clear goals, light oversight": "साफ़ लक्ष्य, कम निगरानी",
    "Small, trusted teams": "छोटी, विश्वसनीय टीमें",
    "High-pressure, fast-scaling settings — without deliberate pacing":
        "बहुत दबाव और तेज़ी से बढ़ने वाली जगहें — अगर सही रफ़्तार से काम न हो तो",
    "You resolve friction head-on — direct, fast, and comfortable naming the "
    "problem rather than working around it. This reads as a genuine strength in "
    "fast-moving, high-stakes environments — less so in cultures that prize "
    "consensus over speed.":
        "आप झगड़े का सीधे सामना करते हैं — सीधे, तेज़ और बेझिझक होकर समस्या को नाम देना, "
        "उसके इर्द-गिर्द घूमना नहीं। तेज़ी से बदलते, बड़े दांव वाले माहौल में यह आपकी असली ताकत है — "
        "उन जगहों पर कम, जहाँ रफ़्तार से ज़्यादा सबकी सहमति को अहमियत दी जाती है।",
    "Competition energises you rather than draining you — you tend to do your "
    "best work when there's a clear target to hit or beat.":
        "मुक़ाबला आपको थकाता नहीं, बल्कि ऊर्जा देता है — जब कोई साफ़ लक्ष्य हो जिसे पाना या "
        "पीछे छोड़ना हो, तब आप सबसे अच्छा काम करते हैं।",
    "Clear targets, fast decisions": "साफ़ लक्ष्य, तेज़ फैसले",
    "Lean, high-ownership teams": "छोटी, ज़िम्मेदार टीमें",
    "Slow-moving, consensus-heavy organisations": "धीमी रफ़्तार वाले, हर बात पर सहमति चाहने वाले संगठन",
    "You resolve friction by holding steady — outlasting pressure rather than "
    "reacting to it. This reads as a genuine strength in long-cycle, high-stakes "
    "work — less so in fast-pivoting environments that reward quick improvisation.":
        "आप डटे रहकर झगड़ा सुलझाते हैं — दबाव पर फ़ौरन जवाब देने की बजाय, उसे झेलते हुए आगे "
        "निकल जाते हैं। लंबे समय तक चलने वाले, बड़े दांव वाले काम में यह आपकी असली ताकत है — "
        "उन तेज़ी से बदलते माहौल में कम, जहाँ फ़ौरन सूझबूझ को अहमियत दी जाती है।",
    "Competition doesn't rattle you; sustained effort does more for you than "
    "short bursts of intensity — you're built for the long haul, not the sprint.":
        "मुक़ाबला आपको हिलाता नहीं; थोड़ी देर के जोश से ज़्यादा लगातार मेहनत आपके काम आती है — "
        "आप लंबी दौड़ के लिए बने हैं, छोटी दौड़ के लिए नहीं।",
    "Defined processes, long time-horizons": "तय तरीके, लंबी समय-सीमा",
    "Stable, low-churn teams": "स्थिर टीमें, जहाँ लोग टिके रहते हैं",
    "Chaotic, constantly-shifting priorities without a settled process":
        "अफ़रा-तफ़री वाला माहौल, बिना किसी तय तरीके के लगातार बदलती प्राथमिकताएँ",
}

VERDICT_HI = {
    "Job, not Own Business — for now": "नौकरी, अपना बिज़नेस नहीं — फिलहाल के लिए",
    "Your strengths compound faster inside a team than solo, so structured "
    "employment reads stronger than independent business right now.":
        "आपकी ताकत अकेले काम करने से ज़्यादा, टीम में तेज़ी से बढ़ती है, इसलिए अभी नौकरी करना "
        "अपना बिज़नेस शुरू करने से बेहतर लगता है।",
    "Own Business, Over a Job — worth exploring": "अपना बिज़नेस, नौकरी से बेहतर — आज़माने लायक",
    "Your strengths read as more self-directed than team-dependent — building "
    "something of your own reads stronger here than structured employment.":
        "आपकी ताकत टीम पर निर्भर होने से ज़्यादा, खुद फैसले लेने वाली लगती है — यहाँ अपना कुछ "
        "बनाना नौकरी से बेहतर लगता है।",
    "Balanced — Either Path Can Work": "संतुलित — दोनों रास्ते सही हो सकते हैं",
    "Your chart doesn't lean hard either way — both structured employment and "
    "independent business are genuinely open paths; the choice comes down to "
    "opportunity and personal preference more than chart pressure.":
        "आपकी कुंडली किसी एक तरफ़ ज़्यादा नहीं झुकती — नौकरी और अपना बिज़नेस, दोनों ही सही रास्ते "
        "हो सकते हैं; फैसला मौके और अपनी पसंद पर ज़्यादा निर्भर करता है, कुंडली के दबाव पर कम।",
}

# ---- Static labels: page titles, subtitles, section/stat/card labels -------
STATIC_HI = {
    "Career Report": "करियर रिपोर्ट",
    "Career Timing & Decision Analysis": "करियर का सही समय और फैसलों का विश्लेषण",
    "Prepared for": "प्रति:",
    "Report generated": "रिपोर्ट तैयार होने की तिथि:",
    "What's Inside Your Report": "आपकी रिपोर्ट में क्या है",
    "Who You Are": "आप कौन हैं",
    "Your natural work style, decision-making, strengths and growth edge — how you're wired to operate.":
        "आप कैसे काम करते हैं, फैसले कैसे लेते हैं, आपकी ताकत क्या है और आगे बढ़ने की दिशा क्या है।",
    "Where You're Headed": "आपकी दिशा किस ओर है",
    "Which fields fit you best, and whether this chart favours a job or your own venture.":
        "आपके लिए कौन से क्षेत्र सबसे अच्छे हैं, और क्या यह कुंडली नौकरी की तरफ इशारा करती है या अपने बिज़नेस की तरफ।",
    "Your Timing": "आपका समय",
    "The hero of this report: your current phase, and the exact windows ahead — graded Strong, Moderate or a quieter stretch.":
        "इस रिपोर्ट की सबसे ज़रूरी बात: आप अभी किस चरण में हैं, और आगे के सही दौर — मज़बूत, मध्यम या शांत।",
    "Life Beyond the Move": "बदलाव के बाद की ज़िंदगी",
    "How your income tends to grow, your workplace style, and your relocation potential.":
        "आपकी कमाई कैसे बढ़ती है, आप ऑफिस में कैसे रहते हैं, और जगह बदलने की संभावना।",
    "Your Plan": "आपकी योजना",
    "A 90-day roadmap, light remedies, and a one-page summary of everything above.":
        "90 दिन का प्लान, आसान उपाय, और ऊपर बताई गई हर बात का एक पन्ने में सार।",
    "The closing pages explain the astrology behind every insight above — houses, planets, dashas and transits, connected step by step.":
        "आखिरी पन्नों में हर बात के पीछे की ज्योतिष गणना बताई गई है — भाव, ग्रह, दशा और गोचर, एक के बाद एक जुड़े हुए।",

    "About You": "आपके बारे में",
    "A quick read on your career personality, before the analysis begins.":
        "विश्लेषण शुरू होने से पहले, आपके करियर से जुड़े स्वभाव की एक छोटी झलक।",
    "How You Work": "आप कैसे काम करते हैं",
    "Work Ethic": "मेहनत",
    "Approach to Work": "काम के प्रति सोच",
    "Your Professional Edge": "आपकी करियर की खासियत",
    "Career Attitude": "करियर को लेकर सोच",
    "Professional Strength": "सबसे बड़ी खूबी",

    "Summary": "सारांश",
    "The whole report, at a glance — every row is explained in the pages that follow.":
        "पूरी रिपोर्ट, एक नज़र में — हर बात आगे के पन्नों में समझाई गई है।",
    "Next Strong Window": "अगला मज़बूत दौर",
    "Switch Outlook": "नौकरी बदलने के हालात",
    "Current Phase": "अभी का चरण",
    "Career Direction": "करियर की दिशा",
    "Growth Pattern": "तरक्की का तरीका",
    "Foreign Potential": "विदेश की संभावना",
    "Favorable": "अच्छे", "Building": "बन रहा है",
    "High": "ज़्यादा", "Moderate": "मध्यम", "Limited": "सीमित",
    "Strong": "मज़बूत", "Low": "कम",
    "Steady & Self-directed": "स्थिर और खुद तय किया हुआ", "Jump-led": "छलांग से",
    "Move Now": "अभी आगे बढ़ें", "Wait & Prepare": "इंतज़ार और तैयारी",

    "Who You Are at Work": "आप ऑफिस में कैसे हैं",
    "Decisions come easily when you can talk them through out loud; you're slower and more cautious when working in isolation.":
        "जब आप खुलकर अपनी बात रख पाते हैं, तो फैसले आसानी से हो जाते हैं; अकेले काम करते समय आप थोड़े धीमे और सावधान रहते हैं।",
    "As a leader, you guide more than you command — people tend to follow because they trust your read of a situation, not because of hierarchy.":
        "एक नेता के तौर पर, आप हुकुम देने की बजाय रास्ता दिखाते हैं — लोग आपका साथ इसलिए देते हैं क्योंकि उन्हें हालात की आपकी समझ पर भरोसा होता है, ओहदे की वजह से नहीं।",

    "Strength & Growth Edge": "आपकी ताकत और आगे बढ़ने की राह",
    "Core strength:": "सबसे बड़ी ताकत:",
    "Once committed, you see things to completion — steady effort over flashes of intensity, which reads well in senior roles.":
        "एक बार जब आप किसी काम को अपना लेते हैं, तो उसे पूरा करके ही दम लेते हैं — थोड़ी देर के जोश की बजाय लगातार मेहनत, जो बड़े ओहदों पर अच्छे नतीजे देती है।",
    "Under pressure:": "दबाव में:",
    "you slow down and reason it out rather than react — an asset in negotiation, a liability if it tips into over-deliberation.":
        "आप जवाब देने से पहले धीमे होकर, सोच-समझकर काम लेते हैं — यह बातचीत में एक ताकत है, लेकिन ज़्यादा सोचने में बदलने पर रुकावट भी बन सकता है।",
    "Growth edge:": "आगे बढ़ने की राह:",
    "Naming it in advance makes it easier to sit with.": "अगर आप इसे पहले से समझ लें, तो इसे संभालना आसान हो जाता है।",
    "restlessness during quiet periods can push toward premature moves":
        "शांत दौर में बेचैनी आपको जल्दबाज़ी में फैसले लेने पर मजबूर कर सकती है",

    "Where Your Chart Points": "आपकी कुंडली किस दिशा का इशारा करती है",
    "1. Strongest fit": "1. सबसे सही",
    "2. Also favorable": "2. अच्छा विकल्प",
    "3. Also favorable": "3. अच्छा विकल्प",
    "Less natural fit:": "कम सही बैठने वाला क्षेत्र:",
    "not closed to you, just a harder climb.": "यह आपके लिए मना नहीं है, बस थोड़ा मुश्किल रास्ता है।",

    "Job or Own Business?": "नौकरी करें या अपना बिज़नेस?",
    "Main takeaway": "सबसे ज़रूरी बात",
    "Own Business": "अपना बिज़नेस", "Job": "नौकरी",
    "This isn't about \"AI-proof\" or \"AI-safe\" work — it's about durable strengths: judgement, relationship-building and follow-through are hard to automate regardless of role or field.":
        "यह बात \"AI-प्रूफ\" या \"AI-सेफ\" काम की नहीं है — यह उन ताकतों की बात है जो हमेशा काम आती हैं: सही फैसले लेना, रिश्ते बनाना और लगे रहना — इन्हें मशीन से करवाना किसी भी काम या क्षेत्र में मुश्किल है।",

    "Your Current Period": "आपका मौजूदा दौर",
    "Current phase": "अभी का चरण",
    "The next section shows exactly how long, and what changes.":
        "अगले हिस्से में साफ़-साफ़ बताया गया है कि यह दौर कितना लंबा चलेगा, और आगे क्या बदलेगा।",

    "Your Switch Windows": "आपके बदलाव के सही समय",
    " &middot; the strongest window — see next page.": " &middot; आपका सबसे मज़बूत दौर — अगला पन्ना देखें।",
    " &middot; a strong window, worth planning around.": " &middot; एक मज़बूत दौर, जिसके हिसाब से योजना बनाना सही रहेगा।",
    " &middot; a second, meaningful opening.": " &middot; एक दूसरा, अच्छा मौका।",
    " &middot; early signals, worth watching quietly.": " &middot; शुरुआती संकेत, जिन पर चुपचाप नज़र रखनी चाहिए।",
    " &middot; no strong signal here — evaluate opportunities carefully rather than forcing a move.":
        " &middot; यहाँ कोई मज़बूत संकेत नहीं — मौकों को ध्यान से परखें, ज़बरदस्ती कोई कदम न उठाएँ।",

    "Your Strongest Window": "आपका सबसे मज़बूत दौर",
    "Do": "करें", "Avoid": "न करें",
    "Rushing a decision before you've actually explored your options.":
        "अपने विकल्पों को अच्छे से जाने बिना जल्दबाज़ी में फैसला लेना।",
    "A favorable window improves timing — the offer still comes from your skills, preparation and market opportunities.":
        "एक अच्छा दौर सिर्फ़ समय को बेहतर बनाता है — ऑफर तो आखिर में आपके हुनर, तैयारी और बाज़ार में मौजूद मौकों से ही मिलता है।",

    "Other Windows to Watch": "बाकी समय जिन पर नज़र रखें",

    "How Your Income Tends to Grow": "आपकी कमाई कैसे बढ़ती है",
    "Stability": "स्थिरता", "Upside via switching": "नौकरी बदलने से फ़ायदे की संभावना",

    "Your Workplace Archetype:": "आप काम पर कैसे हैं:",
    "Your Workplace Archetype: Diplomat": "आप काम पर कैसे हैं: सुलझाने वाले",
    "Your Workplace Archetype: Confronter": "आप काम पर कैसे हैं: सीधा सामना करने वाले",
    "Your Workplace Archetype: Outlaster": "आप काम पर कैसे हैं: डटे रहने वाले",

    "Environment That Suits You": "आपके लिए सही माहौल",
    "Best-fit structure": "सबसे सही सिस्टम", "Team size": "टीम का आकार", "Burnout risk": "थकने का खतरा",

    "Relocation & Foreign Potential": "जगह बदलने और विदेश की संभावना",
    "Foreign potential": "विदेश जाने की संभावना",
    "Best-supported form": "सबसे अच्छा तरीका",
    "Major career hub, international clients": "बड़े करियर हब, विदेशी ग्राहक",
    "No specific country is indicated; treat any interest in a hub or global-facing role as worth pursuing.":
        "कोई खास देश नहीं दिखता; अगर आपकी रुचि किसी बड़े करियर हब या दुनिया भर से जुड़े काम में है, तो उसे आगे बढ़ाएँ।",

    "Your 90-Day Plan": "आपका 90 दिन का प्लान",
    "Not the window itself — the groundwork that makes it land well when it arrives.":
        "यह दौर खुद नहीं है — बल्कि वह तैयारी है, जो सही समय आने पर काम आएगी।",
    "Settle & Audit": "संभलना और जायज़ा लेना",
    "Get honest about where you stand, while signals are still just building.":
        "जब तक संकेत अभी बन ही रहे हैं, अपनी असली स्थिति के बारे में ईमानदार रहें।",
    "Reconnect quietly with 3–5 people in your network — conversation, not cold outreach.":
        "अपने नेटवर्क के 3–5 लोगों से आराम से दोबारा बात करें — बातचीत, कोल्ड मैसेज नहीं।",
    "Applying anywhere yet, or reading early interest as the window itself.":
        "अभी कहीं आवेदन करना, या शुरुआती दिलचस्पी को ही सही दौर समझ लेना।",
    "Deepen & Test": "गहराई से जानना और परखना",
    "Sharpen your direction without committing to anything.": "बिना कुछ पक्का किए, अपनी दिशा साफ़ करें।",
    "Have a few honest, informal conversations in your target fields — testing fit, not applying.":
        "अपने पसंदीदा क्षेत्रों में कुछ ईमानदार और आराम से बातचीत करें — यह देखने के लिए कि यह सही है या नहीं, आवेदन के लिए नहीं।",
    "Notice what energises you vs. drains you in these conversations.":
        "इन बातचीत में देखें कि आपको क्या ऊर्जा देता है और क्या थकाता है।",
    "Mistaking a good conversation for an offer, or applying too early out of restlessness.":
        "अच्छी बातचीत को ऑफर समझ लेने की गलती करना, या बेचैनी में जल्दी आवेदन कर देना।",

    "Your 90-Day Plan, Continued": "आपका 90 दिन का प्लान, आगे",
    "Days 61–90.": "दिन 61–90।",
    "Consolidate": "मज़बूत बनाना",
    "Close the quarter with a genuinely ready profile, not a rushed one.":
        "इन तीन महीनों को सच में तैयार होकर खत्म करें, जल्दबाज़ी में नहीं।",
    "Finalise a resume and portfolio version you'd be proud to send without editing.":
        "अपना बायोडाटा और पोर्टफोलियो ऐसा बनाएँ, जिसे आप बिना बदलाव किए, गर्व से भेज सकें।",
    "Keep the network warm with light, periodic check-ins — not a hard push.":
        "हल्के, नियमित संपर्क से अपने नेटवर्क को जोड़े रखें — दबाव डालकर नहीं।",
    "Forcing a decision before the real window opens.": "असली दौर खुलने से पहले फैसला थोपना।",
    "The offer still comes from your skills, preparation and market opportunities — these 90 days are what make sure you're ready to meet it.":
        "ऑफर तो आखिर में आपके हुनर, तैयारी और बाज़ार में मौजूद मौकों से ही आता है — ये 90 दिन बस यह पक्का करते हैं कि आप उसे पाने के लिए तैयार हों।",

    "Light Remedies": "सरल उपाय",
    "linked discipline — a simple steadying practice for your current Mahadasha.":
        "से जुड़ा अनुशासन रखें — यह आपकी मौजूदा महादशा को स्थिर रखने का एक आसान तरीका है।",
    "for important conversations — your career-lord's day suits your communication strength.":
        "ज़रूरी बातचीत के लिए रखें — यह आपकी करियर-दशा के स्वामी का दिन है, जो बातचीत के लिए अच्छा है।",
    "Avoid starting anything irreversible during the quiet stretch identified on page 12.":
        "पृष्ठ 12 पर बताए गए शांत दौर में कोई भी ऐसा काम शुरू करने से बचें, जिसे बाद में बदला न जा सके।",
    "No notable hold period ahead — pace yourself by the windows above instead.":
        "आगे कोई खास रुकने वाला दौर नहीं है — ऊपर बताए गए सही समय के हिसाब से आगे बढ़ें।",

    "The Chain, at a Glance": "पूरी कड़ी, एक नज़र में",
    "Eight links connect your birth chart to your career recommendations.":
        "आठ कड़ियाँ आपकी जन्म-कुंडली को आपके करियर के सुझावों से जोड़ती हैं।",
    "1. Birth Chart": "1. जन्म-कुंडली", "Lagna sets your baseline.": "लग्न आपकी नींव तय करता है।",
    "2. Career Houses": "2. करियर भाव",
    "10th, 6th, 2nd, 11th, 9th & 12th mark the terrain.": "10वाँ, 6वाँ, 2रा, 11वाँ, 9वाँ और 12वाँ भाव इस पूरे क्षेत्र को तय करते हैं।",
    "3. Planetary Strengths": "3. ग्रह-शक्तियाँ",
    "Which planets are well-placed, which aren't.": "कौन-से ग्रह अच्छी स्थिति में हैं, कौन-से नहीं।",
    "4. Dasha & Antardasha": "4. दशा और अंतर्दशा",
    "Your current chapter, and its theme.": "आपका मौजूदा अध्याय, और उसका विषय।",
    "5. Transits": "5. गोचर",
    "What's moving right now — especially Jupiter and Saturn.": "अभी कौन-से ग्रह चल रहे हैं — खासकर गुरु और शनि।",
    "6. Career Themes": "6. करियर विषय",
    "Direction, workplace style, income pattern, foreign potential.": "दिशा, काम करने का तरीका, कमाई का तरीका, विदेश जाने की संभावना।",
    "7. Job-Change Windows": "7. नौकरी-परिवर्तन का सही समय",
    "When enough of the above align to act.": "जब ऊपर बताई गई बातें काम करने लायक हद तक साथ आ जाएँ।",
    "8. Recommendation": "8. सुझाव",
    "What to actually do, and when.": "असल में क्या करना है, और कब।",

    "Your Birth Chart: Lagna": "आपकी जन्म-कुंडली: लग्न",
    "Everything on pages 5–6 starts here.": "पृष्ठ 5–6 की हर बात यहीं से शुरू होती है।",
    "Lagna — how you show up": "लग्न — आप कैसे दिखते हैं",

    "The Career Houses": "करियर भाव",
    "10th, 6th, 2nd & 11th — the terrain behind pages 7, 13–14.": "10वाँ, 6वाँ, 2रा और 11वाँ — पृष्ठ 7, 13–14 के पीछे की बुनियाद।",
    "Direction": "दिशा", "Points toward": "इस तरफ़ इशारा करता है:",
    "Workplace conduct": "काम पर आपका बर्ताव",
    "Behind your Diplomat archetype (p.14).": "आपके सुलझाने वाले स्वभाव के पीछे (पृष्ठ 14)।",
    "Behind your Confronter archetype (p.14).": "आपके सीधा सामना करने वाले स्वभाव के पीछे (पृष्ठ 14)।",
    "Behind your Outlaster archetype (p.14).": "आपके डटे रहने वाले स्वभाव के पीछे (पृष्ठ 14)।",
    "Behind the Strong stability rating in your income pattern (p.13).":
        "आपकी कमाई में मज़बूत स्थिरता की रेटिंग के पीछे (पृष्ठ 13)।",
    "Behind the Moderate stability rating in your income pattern (p.13).":
        "आपकी कमाई में मध्यम स्थिरता की रेटिंग के पीछे (पृष्ठ 13)।",
    "Behind the Low stability rating in your income pattern (p.13).":
        "आपकी कमाई में कम स्थिरता की रेटिंग के पीछे (पृष्ठ 13)।",
    "Gains & networks": "फ़ायदा और नेटवर्क",
    "Behind your Steady & Self-directed growth pattern (p.13).":
        "आपके स्थिर और खुद तय किए तरक्की के तरीके के पीछे (पृष्ठ 13)।",
    "Behind your Jump-led growth pattern (p.13).": "आपके छलांग से बढ़ने के तरीके के पीछे (पृष्ठ 13)।",

    "9th & 12th Houses, and Rahu": "9वाँ और 12वाँ भाव, और राहु",
    "Behind the Relocation & Overseas Opportunities chapter, page 16.": "जगह बदलने और विदेश के मौकों वाले हिस्से के पीछे, पृष्ठ 16।",
    "adds the pull toward the unfamiliar — part of why relocation reads as worth actively exploring, not something to force.":
        "अनजान चीज़ों की तरफ खिंचाव जोड़ता है — यही एक वजह है कि जगह बदलना खुलकर तलाशने लायक लगता है, ज़बरदस्ती करने लायक नहीं।",

    "Planetary Strengths": "ग्रह-शक्तियाँ",
    "Which planets are carrying the most weight right now.": "अभी कौन-से ग्रह सबसे ज़्यादा असर डाल रहे हैं।",
    "Structure & Timing": "अनुशासन और समय",
    "your current Mahadasha lord (p.9).": "आपकी मौजूदा महादशा का स्वामी है (पृष्ठ 9)।",
    "Your 10th lord — behind your career direction (p.7).": "आपके 10वें भाव के मालिक — आपकी करियर दिशा के पीछे (पृष्ठ 7)।",
    "Growth & Drive": "तरक्की और जोश",
    "The planet most linked to expansion — watch its transits for your switch windows (p.10–11).":
        "विस्तार से सबसे ज़्यादा जुड़ा ग्रह — इसके गोचर पर नज़र रखें, यही आपके सही समय तय करता है (पृष्ठ 10–11)।",
    "Additional strengths": "एक और ताकत",
    "an additional real strength in this chart.": "इस कुंडली की एक और असली ताकत है।",
    "A further real strength in this chart.": "इस कुंडली की एक और असली ताकत है।",

    "Dasha & Antardasha": "दशा और अंतर्दशा",
    "Your timeline engine — the theme, and the current chapter within it.": "आपका समय का चक्र — इसका विषय, और इसके अंदर अभी का अध्याय।",
    "Mahadasha —": "महादशा —", "Antardasha —": "अंतर्दशा —",
    "The current flavour layered on top of the Mahadasha theme.": "अभी का रंग, महादशा के विषय के ऊपर जुड़ा हुआ।",

    "How It All Adds Up": "यह सब कैसे मिलकर बनता है",
    "Birth Chart": "जन्म-कुंडली", "Houses": "भाव",
    "foreign potential.": "विदेश की संभावना।",
    "Dasha": "दशा", "Transit": "गोचर",
    "Prepare now. Move in the window.": "अभी तैयारी करें। सही दौर में कदम बढ़ाएँ।",
    "Computed from classical Vedic principles, applied consistently — probabilities and tendencies, not guarantees.":
        "पुराने वैदिक नियमों से निकाला गया, हर जगह एक जैसे तरीके से लगाया गया — यह संभावनाएँ और रुझान हैं, गारंटी नहीं।",

    "Disclaimer:": "अस्वीकरण:",
    "This report is computed from classical Vedic Jyotish (dasha–transit) principles — for guidance, not a guarantee. Timing windows are probabilities, not fixed dates. This is not legal, medical or financial advice — please make your own decisions using your own judgement.":
        "यह रिपोर्ट पुराने वैदिक ज्योतिष (दशा–गोचर) के नियमों से बनाई गई है — रास्ता दिखाने के लिए, गारंटी के लिए नहीं। समय की बातें संभावनाएँ हैं, पक्की तारीखें नहीं। यह कानूनी, मेडिकल या पैसों से जुड़ी सलाह नहीं है — कृपया अपनी समझ से अपने फैसले खुद लें।",
    "Made with Axtroshastra — get your own report:": "Axtroshastra से बनी — अपनी रिपोर्ट पाएँ:",
    "Windows are probability estimates from classical dasha–transit principles, not guarantees.":
        "समय की बातें पुराने दशा–गोचर के नियमों पर आधारित अंदाज़े हैं, गारंटी नहीं।",
    "Computational Vedic Astrology": "गणना पर आधारित वैदिक ज्योतिष",
    "by Cultnuts": "Cultnuts की तरफ़ से",
    "Privacy": "गोपनीयता", "Terms": "नियम और शर्तें", "Refund Policy": "पैसे वापसी की नीति",

    "Download PDF": "PDF डाउनलोड करें", "Share on WhatsApp": "WhatsApp पर शेयर करें",
    "&#11015; Download PDF": "&#11015; PDF डाउनलोड करें",
    "&#128242; Share on WhatsApp": "&#128242; WhatsApp पर शेयर करें",
    "steady effort": "लगातार मेहनत",
}


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:].lower() if s else s


def _build_hi() -> dict:
    """Assemble the full English->Hindi text-run dictionary. For every source
    string that render_career_growth() may emit either raw or via .capitalize()
    (persona_line, wealth text, ninth_house_note, md_phase_text, etc.), both
    forms are added so the localizer matches whichever form actually appears
    in the rendered HTML."""
    hi = {}
    hi.update(STATIC_HI)
    hi.update(MONTHS_HI)
    hi.update(FIELD_FAMILIES_HI)
    hi.update(TEASER_QUOTE_HI)  # ABOUT_YOU_TRAITS strength values
    hi.update(PHASE_HI)
    hi.update(VERDICT_BLURRED_HI)
    hi.update(PLANET_NAME_HI)
    hi.update(DAY_HI)
    hi.update(REMEDY_MANTRA_HI)
    hi.update(MD_PHASE_HI)
    hi.update(WORKPLACE_HI)
    hi.update(VERDICT_HI)
    hi.update(ABOUT_YOU_WORK_ETHIC_HI)
    hi.update(ABOUT_YOU_APPROACH_HI)
    hi.update(ABOUT_YOU_ATTITUDE_HI)

    # index-based banks: pair each Hindi translation with its real English
    # source list (imported here, not hardcoded, so a source-text edit can't
    # silently drift out of sync with the index it's zipped against).
    from career_growth_report import FIELD_ANTIFIT_NOTE as _FAN_EN
    for en, hv in zip(_FAN_EN, FIELD_ANTIFIT_NOTE_HI):
        hi[en] = hv
    # PLANET_GIFT_HI/PLANET_LESSON_HI (authored above, keyed by planet name for
    # readability) must be re-keyed by the actual GIFT/LESSON TEXT for text-run
    # matching to work — render_career_growth() renders "wisdom and luck-
    # expansion", never the planet name, at these call sites.
    from products import PLANET_GIFT as _PG_EN, PLANET_LESSON as _PL_EN
    for planet, en_text in _PG_EN.items():
        if planet in PLANET_GIFT_HI:
            hi[en_text] = PLANET_GIFT_HI[planet]
    for planet, en_text in _PL_EN.items():
        if planet in PLANET_LESSON_HI:
            hi[en_text] = PLANET_LESSON_HI[planet]
    from jyotish_maps import WEALTH_2L as _W2L_EN, GAINS_11L as _G11L_EN
    for en, hv in zip(_W2L_EN, WEALTH_2L_HI):
        hi[en] = hv
    for en, hv in zip(_G11L_EN, GAINS_11L_HI):
        hi[en] = hv
    from vidyarthi_maps import HIGHERED_HOUSE as _HEH_EN
    for en, hv in zip(_HEH_EN, HIGHERED_HOUSE_HI):
        hi[en] = hv
    from products import LAGNA_PERSONA as _LP_EN
    for en, hv in zip(_LP_EN, LAGNA_PERSONA_HI):
        hi[en] = hv

    # add .capitalize()'d variants for every entry whose source may be
    # capitalize()'d by render_career_growth (persona_line, wealth text,
    # ninth_house_note, md_phase_text — all lowercase-first as authored).
    for en in list(hi.keys()):
        cap = _cap(en)
        if cap != en and cap not in hi:
            hi[cap] = hi[en]
    return hi


HI = _build_hi()

# Cover-page text runs that splice a real date/place into a static English
# prefix on the same text node (e.g. "Born 14 June 1996 · Bengaluru" or
# "Report generated 19 August 2026") — an exact-match lookup can never hit
# these since the full run is different for every person. Prefix-replace the
# static part, then let _MONTH_RE below translate the month name in the
# (still-dynamic) remainder.
PREFIX_HI = {
    "Prepared for ": "प्रति: ",
    "Report generated ": "रिपोर्ट तैयार होने की तिथि: ",
    "Born ": "जन्म: ",
    "Mahadasha — ": "महादशा — ",
    "Antardasha — ": "अंतर्दशा — ",
}

# Text runs that splice a HI-resolvable dynamic value (persona_line, a
# PLANET_GIFT phrase, etc.) followed by a fixed English tail — e.g.
# "Wisdom and luck-expansion — your current Mahadasha lord (p.9)." The
# dynamic prefix resolves via HI (it's already in there, capitalize()'d
# variant included); only the tail needs an explicit mapping here.
SUFFIX_HI = {
    " — an additional real strength in this chart.": " — इस कुंडली की एक और असली ताकत है।",
    " — your current Mahadasha lord (p.9).": " — आपकी मौजूदा महादशा का स्वामी (पृष्ठ 9)।",
    " (p.5) — this is the outward professional self your chart sets at birth.":
        " (पृष्ठ 5) — यह वह बाहरी पेशेवर रूप है जो आपकी कुंडली जन्म के समय तय करती है।",
}

# Text runs of the shape "{fixed prefix}{HI-resolvable dynamic value}{fixed
# suffix}" as ONE continuous node (no tag between the parts). Keyed by
# (en_prefix, en_suffix) -> (hi_prefix, hi_suffix); the dynamic middle is
# looked up in HI at match time, so this stays small even though the values
# it can plug in (field families, months, ...) are not.
COMBINED_HI = {
    ("Less natural fit: ", " — not closed to you, just a harder climb."):
        ("कम सही बैठने वाला क्षेत्र: ", " — यह आपके लिए मना नहीं है, बस थोड़ा मुश्किल रास्ता है।"),
    ("Start exploring by ", ", and treat the window as one arc."):
        ("ढूँढना शुरू कर दें (", " तक), और इस दौर को एक मौका मानें।"),
}

_MONTH_RE = re.compile(r"\b(" + "|".join(sorted(MONTHS_HI, key=len, reverse=True)) + r")\b")

_SEG = re.compile(r">([^<>]+)<")
_SKIP = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)


def _resolve_sentence(s):
    """Translate a single sentence (trailing period optional) via HI, or
    return None. Used by the multi-sentence fallback below."""
    s = s.strip()
    if not s:
        return None
    if s in HI:
        return HI[s]
    if s.endswith(".") and s[:-1] in HI:
        return HI[s[:-1]] + "।"
    return None


def localize(html: str) -> str:
    """Translate the fixed shell + enumerable data values of a rendered
    career_growth report to Devanagari. Safe: only whole text runs present in
    HI are swapped — directly, via a known dynamic-value prefix/suffix
    (PREFIX_HI/SUFFIX_HI, for cover-page dates and a few "{dynamic} — fixed
    tail" sentences), or via the multi-sentence fallback (splits a run on
    ". " and only substitutes if every resulting sentence independently
    resolves — covers "{dynamic}. {static}." runs like p5's opening
    paragraph without needing to enumerate every combination by hand).
    Scripts/styles/attrs and any text that still doesn't resolve (names,
    formatted window ranges, the handful of open-ended rules-engine
    sentences — see module docstring) are left as-is."""
    if not html:
        return html
    holds = []

    def _hold(m):
        holds.append(m.group(0))
        return f"\x00{len(holds) - 1}\x00"

    tmp = _SKIP.sub(_hold, html)

    def _tr(m):
        raw = m.group(1)
        key = _htmlmod.unescape(raw.strip())
        lead = raw[: len(raw) - len(raw.lstrip())]
        tail = raw[len(raw.rstrip()):]
        hi = HI.get(key)
        if hi is not None:
            return ">" + lead + hi + tail + "<"
        # a lone dynamic value immediately followed by ". " before the NEXT
        # tag (e.g. "...career choice. " right before "<b>Rahu</b>") has no
        # sibling sentence in this text run for the multi-sentence pass below
        # to split on — try it directly, trailing period included.
        if key.endswith(".") and key[:-1] in HI:
            return ">" + lead + HI[key[:-1]] + "।" + tail + "<"
        for en_prefix, hi_prefix in PREFIX_HI.items():
            if key.startswith(en_prefix):
                rest_raw = key[len(en_prefix):]
                rest = HI.get(rest_raw)
                if rest is None:
                    rest = _MONTH_RE.sub(lambda mm: MONTHS_HI[mm.group(1)], rest_raw)
                return ">" + lead + hi_prefix + rest + tail + "<"
        for (en_pre, en_suf), (hi_pre, hi_suf) in COMBINED_HI.items():
            if key.startswith(en_pre) and key.endswith(en_suf) and len(key) >= len(en_pre) + len(en_suf):
                mid = HI.get(key[len(en_pre): len(key) - len(en_suf)])
                if mid is not None:
                    return ">" + lead + hi_pre + mid + hi_suf + tail + "<"
        for en_suffix, hi_suffix in SUFFIX_HI.items():
            if key.endswith(en_suffix):
                dyn = HI.get(key[: -len(en_suffix)])
                if dyn is not None:
                    return ">" + lead + dyn + hi_suffix + tail + "<"
        if ". " in key or key.count(".") >= 1:
            sentences = re.split(r"(?<=\.)\s+", key)
            if len(sentences) > 1:
                resolved = [_resolve_sentence(s) for s in sentences]
                if all(r is not None for r in resolved):
                    return ">" + lead + " ".join(resolved) + tail + "<"
        return m.group(0)

    tmp = _SEG.sub(_tr, tmp)
    tmp = re.sub(r"\x00(\d+)\x00", lambda m: holds[int(m.group(1))], tmp)

    # Devanagari-capable webfonts, same pairing used site-wide (marriage-v2.hi.html etc.)
    tmp = tmp.replace(
        "</head>",
        "<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>"
        "<link href=\"https://fonts.googleapis.com/css2?family=Mukta:wght@400;500;600;700;800"
        "&family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap\" rel=\"stylesheet\">"
        "<style>:root{--disp:'Mukta','Noto Sans Devanagari',system-ui,sans-serif;"
        "--body:'Noto Sans Devanagari',system-ui,sans-serif}</style></head>",
        1,
    )
    tmp = tmp.replace("<html>", '<html lang="hi">', 1)
    return tmp
