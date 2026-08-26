"""
blueprint_hi_report.py — the Hindi (Devanagari) Life Blueprint report.

Unlike the earlier approach (a post-render text-node translator), this is a
REAL rendering function: render_blueprint_hi(p) builds the report's HTML
directly from the same compute_blueprint() payload report_view.render_blueprint()
uses for English — no English HTML is generated or translated. The two
renderers are independent; editing this file can never change a single byte
of English output.

Structure matches the finalized Hindi reference (Part 1 — ten life areas +
timing; Part 2 — the evidence/methodology: kundli, planet table, houses 1-12,
dasha timeline, "how every tag was set", a worked example, the full
area->house->lord->reading map, an honesty page, and a glossary) rather than
English's shorter 20-section design. Visual system is reused wherever
possible: _VYAPAR_CSS/_VYAPAR_DEFS/icon() from report_view.py (the same
primitives render_blueprint and render_vyapar already share), plus a small,
additive block of new classes (BLUEPRINT_HI_CSS below) for card/list shapes
English's design doesn't need (reason-cards, a Part-2 divider, a glossary
list) — nothing existing is edited.

Every personalized fact below is read from `p` (products.compute_blueprint's
real output for this exact birth chart) — house numbers, lords, signs and
dignities come from `p["area_detail"]`/`p["houses_1_12"]` (additive fields
compute_blueprint now returns; see products.py), the global roadmap comes
from `p["roadmap"]`/`p["dasha_current_md"]`/`p["dasha_current_ads"]`. No new
astrology is computed here, and no per-area timeline is invented — every
area's "through your chapters" section reads the SAME real global roadmap,
because that is the only real timeline compute_blueprint() has.
"""
from html import escape

from report_view import (
    _VYAPAR_CSS, _VYAPAR_DEFS, SIGN_PARTNER, VY_HOUSE_ROLE,
)


def icon(name, cls="ic pi"):
    """Same <svg><use> pattern report_view.py inlines directly wherever it
    needs an icon (there is no shared icon() helper there to import)."""
    return f'<svg class="{cls}"><use href="#{name}"/></svg>'
from products import (
    NAK_PROFILE, PLANET_GIFT, PLANET_LESSON, MD_PHASE, LAGNA_PERSONA,
    REMEDY_7L, REMEDY_NODE,
)
from engine import SIGNS, SIGNS_EN, NAKSHATRAS, SIGN_LORD

# ===========================================================================
# Vocabulary — every dict below is a straight Hindi rendering of a real,
# already-computed English value; nothing here changes what value is chosen.
# ===========================================================================
PLANET_HI = {
    "Sun": "सूर्य", "Moon": "चंद्र", "Mars": "मंगल", "Mercury": "बुध",
    "Jupiter": "गुरु", "Venus": "शुक्र", "Saturn": "शनि", "Rahu": "राहु", "Ketu": "केतु",
}
SIGN_HI_BY_EN = {
    "Aries": "मेष", "Taurus": "वृषभ", "Gemini": "मिथुन", "Cancer": "कर्क",
    "Leo": "सिंह", "Virgo": "कन्या", "Libra": "तुला", "Scorpio": "वृश्चिक",
    "Sagittarius": "धनु", "Capricorn": "मकर", "Aquarius": "कुंभ", "Pisces": "मीन",
}
SIGN_HI = {sa: SIGN_HI_BY_EN[en] for sa, en in zip(SIGNS, SIGNS_EN)}
MONTH_HI = {
    "Jan": "जन॰", "Feb": "फ़र॰", "Mar": "मार्च", "Apr": "अप्रैल", "May": "मई", "Jun": "जून",
    "Jul": "जुल॰", "Aug": "अग॰", "Sep": "सित॰", "Oct": "अक्तू॰", "Nov": "नव॰", "Dec": "दिस॰",
}


def month_hi(date_str):
    """'Jun 2033' -> 'जून 2033'. date_str is always '%b %Y' or a bare year."""
    if not date_str:
        return date_str
    parts = date_str.split()
    if len(parts) == 2 and parts[0] in MONTH_HI:
        return f"{MONTH_HI[parts[0]]} {parts[1]}"
    return date_str


def _time_of_day_hi(tob):
    """'16:15' -> 'शाम 4:15'. Real birth time already collected at intake --
    just formatted for display, nothing computed or inferred."""
    if not tob or ":" not in tob:
        return ""
    try:
        h, m = int(tob.split(":")[0]), int(tob.split(":")[1])
    except ValueError:
        return ""
    if 4 <= h < 12:
        part = "सुबह"
    elif 12 <= h < 16:
        part = "दोपहर"
    elif 16 <= h < 19:
        part = "शाम"
    else:
        part = "रात"
    h12 = h % 12
    if h12 == 0:
        h12 = 12
    return f"{part} {h12}:{m:02d}"


NAKSHATRA_HI = {
    "Ashwini": "अश्विनी", "Bharani": "भरणी", "Krittika": "कृत्तिका", "Rohini": "रोहिणी",
    "Mrigashira": "मृगशिरा", "Ardra": "आर्द्रा", "Punarvasu": "पुनर्वसु", "Pushya": "पुष्य",
    "Ashlesha": "आश्लेषा", "Magha": "मघा", "Purva Phalguni": "पूर्व फाल्गुनी",
    "Uttara Phalguni": "उत्तर फाल्गुनी", "Hasta": "हस्त", "Chitra": "चित्रा",
    "Swati": "स्वाति", "Vishakha": "विशाखा", "Anuradha": "अनुराधा", "Jyeshtha": "ज्येष्ठा",
    "Mula": "मूल", "Purva Ashadha": "पूर्व आषाढ़ा", "Uttara Ashadha": "उत्तर आषाढ़ा",
    "Shravana": "श्रवण", "Dhanishta": "धनिष्ठा", "Shatabhisha": "शतभिषा",
    "Purva Bhadrapada": "पूर्व भाद्रपद", "Uttara Bhadrapada": "उत्तर भाद्रपद", "Revati": "रेवती",
}

# NAK_PROFILE's (symbol, nature, relationship) English text — reused verbatim
# from shaadi_hi_data.HI_DATA, the same production translations career_growth
# products already ship with.
from shaadi_hi_data import HI_DATA as _SHI


def _shi(en):
    v = _SHI.get(en, en)
    return v[:-1] if v.endswith("।") else v


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
    "Sun": "अधिकार, पहचान, पिता-तुल्य लोग — यह अपने ही नाम पर खड़े होने का दौर है",
    "Moon": "भावनाओं का संतुलन, घर, लोगों से जुड़ाव — अंदर की ज़िंदगी बाहर की दिशा तय करती है",
    "Mars": "जोश, टकराव और जीत, ज़मीन-जायदाद, भाई-बहन — ऊर्जा को एक मैदान चाहिए",
    "Rahu": "महत्वाकांक्षा, पटरी से हटकर तरक्की, विदेश से जुड़ाव — तेज़ पर बेचैन बढ़त",
    "Jupiter": "समझदारी, विस्तार, बच्चे, गुरु — ज्ञान और भरोसे से दरवाज़े खुलते हैं",
    "Saturn": "अनुशासन, कर्मों का हिसाब, धीमे पर टिकाऊ फ़ायदे — अभी जो बनाएँगे, वह टिकेगा",
    "Mercury": "व्यापार, बातचीत, सीखना — दिमाग़ ही कमाई बन जाता है",
    "Ketu": "अलगाव, आध्यात्मिक निखार, ऐसा अंत जो आज़ाद करे — कम में ही ज़्यादा मिलता है",
    "Venus": "रिश्ते, आराम, रचनात्मकता, धन का सुख — ज़िंदगी नरम और मीठी हो जाती है",
}
CAREER_HOUSE_HI = [
    "अपनी शुरुआत किया हुआ काम — उद्यमिता, स्वतंत्र अभ्यास, अपने ही नाम से पहचान",
    "पैसों से जुड़े क्षेत्र — फाइनेंस, खाना, पारिवारिक बिज़नेस, आवाज़ से जुड़ा काम",
    "बातचीत और हिम्मत — मीडिया, सेल्स, लेखन, हाथ के हुनर वाला काम",
    "घर से जुड़ा काम — रियल एस्टेट, गाड़ियाँ, शिक्षा, अपने ठिकाने के पास काम करना",
    "रचनात्मक और जोखिम वाले क्षेत्र — पढ़ाना, मनोरंजन, बाज़ार, बच्चों-युवाओं के साथ काम",
    "सेवा और समस्या सुलझाने वाला काम — स्वास्थ्य, कानून, ऑपरेशंस, मुक़ाबले वाले क्षेत्र",
    "साझेदारी पर टिका काम — कंसल्टिंग, क्लाइंट का काम, व्यापार, लोगों से सीधा जुड़ाव",
    "रिसर्च और बदलाव — गहराई वाले क्षेत्र, बीमा, गूढ़ विद्या, दूसरों के संसाधनों से जुड़ा काम",
    "ज्ञान और दूरी — उच्च शिक्षा, प्रकाशन, विदेश से जुड़ाव, धर्म से जुड़े क्षेत्र",
    "करियर का पारंपरिक भाव — बड़े ओहदे, सरकारी नौकरी, कॉर्पोरेट तरक्की, सार्वजनिक ज़िम्मेदारी",
    "बड़े नेटवर्क वाला काम — बड़े संगठन, समुदाय, जान-पहचान से मिलने वाला फ़ायदा",
    "पर्दे के पीछे का काम या सरहद के पार — विदेश, बड़ी संस्थाएँ, कल्पनाशील क्षेत्र",
]
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
HEALTH_6_HI = [
    "गर्मी और सिर से जुड़ी तकलीफ़ें — गुस्से और जल्दबाज़ी पर काबू रखें",
    "गले और वज़न से जुड़ी तकलीफ़ें — नियमित दिनचर्या और संयम आपको बचाते हैं",
    "नसों और साँस से जुड़ी संवेदनशीलता — मन को आराम दें, सोच-समझकर साँस लें",
    "पाचन और भावनाओं का गहरा नाता — पेट आपके मूड को सीधा दिखाता है",
    "दिल और ऊर्जा से जुड़े मुद्दे — अचानक ज़ोर लगाने से बेहतर है टिकाऊ रफ़्तार",
    "पेट और चिंता का जुड़ाव — बारीकी काम में मदद करती है, पर नींद बिगाड़ती है; दोनों को अलग रखें",
    "किडनी और संतुलन से जुड़े मुद्दे — पानी पीना और हर चीज़ में संतुलन ज़रूरी है",
    "गहरी और छुपी हुई तकलीफ़ें — अंदाज़े लगाने से बेहतर है नियमित जाँच कराना",
    "कूल्हे, लिवर और ज़्यादा-पन से जुड़े मुद्दे — ज़्यादा पाने की चाहत पर लगाम ज़रूरी है",
    "जोड़ों, घुटनों और पुरानी तकलीफ़ों से जुड़े मुद्दे — तेज़ी से ज़्यादा असरदार है निरंतरता",
    "रक्त-संचार और तनाव से जुड़े मुद्दे — चलना-फिरना ही आपकी असली दवा है",
    "इम्युनिटी और नींद से जुड़े मुद्दे — सीमाएँ तय करना भी शरीर की रक्षा करता है",
]
HOME_4_HI = [
    "जल्दी घर बदलना और बिना सोचे खरीदारी — पहला घर लेने के लिए ठीक, लंबे समय तक रखने के लिए उतना नहीं",
    "अपना घर बनाने की मज़बूत चाहत — यहाँ रखी गई संपत्ति की क़ीमत बढ़ती है और वह परिवार में बनी रहती है",
    "एक से ज़्यादा ठिकाने होने की संभावना — किराए पर रहना, जगह बदलना या कई जगहों के बीच समय बाँटना",
    "घर से गहरा लगाव — आराम और भावनात्मक सुरक्षा घर के आकार से कहीं ज़्यादा मायने रखते हैं",
    "एक ऐसा घर जो अपनी पहचान बनाए — जगह, रुतबा और थोड़ी शान-शौकत मायने रखती है",
    "व्यावहारिक और सुव्यवस्थित रहन-सहन — दिखावे से ज़्यादा काम की चीज़, जगह बदलने से बेहतर मरम्मत",
    "तालमेल से लिए फैसले — घर को लेकर साथी की राय अक्सर आपकी अपनी राय से भारी पड़ती है",
    "बदलाव से जुड़ा — विरासत में मिली संपत्ति, बड़ी मरम्मत, या किसी बड़े बदलाव से जुड़ा घर",
    "दूरी से जुड़ा — एक दूसरा घर, फार्महाउस, या अपने बचपन की जगह से दूर कोई संपत्ति",
    "धीमी पर अनुशासित बचत — देर से ली गई संपत्ति जल्दी ली गई संपत्ति से ज़्यादा टिकाऊ साबित होती है",
    "पटरी से हटकर रहने का तरीका — साझा जगह, सामुदायिक रहन-सहन, या कोई अनोखी जगह",
    "भावनाओं से लिए फैसले — पानी के पास कोई घर, या ऐसा घर जो योजना से ज़्यादा दिल से चुना गया हो",
]
CHILDREN_5_HI = [
    "माता-पिता बनने की जल्दी और उत्साह भरी चाहत — यहाँ ज़्यादा न सोचना ही सही समय है",
    "स्थिर और धैर्यवान तरीका — अपने ही, बिना जल्दबाज़ी वाले समय पर परिवार बनाना",
    "बातचीत को पहले रखने वाली शैली — ऐसे बच्चे (या विचार) जो शुरू से ही ढेरों सवाल पूछते हैं",
    "गहरी देखभाल की सहज-बुद्धि — बच्चों के आने के बाद घर की पूरी दुनिया उन्हीं के इर्द-गिर्द घूमती है",
    "गर्व और अभिव्यक्ति भरा रिश्ता — ऐसे बच्चे, या रचनात्मक काम, जो आपका नाम आगे ले जाते हैं",
    "सावधान और बारीकी वाला तरीका — यहाँ अचानक फैसलों से ज़्यादा व्यावहारिक योजना मायने रखती है",
    "साझेदारी पर टिका तरीका — यहाँ समय और फैसले मिलकर लिए जाते हैं, अकेले शायद ही कभी",
    "गहरा और सुरक्षा से भरा रिश्ता — यहाँ निजता और गहराई खुलेपन से ज़्यादा मायने रखती है",
    "आशावादी और आज़ादी-पसंद शैली — ऐसे बच्चे, या काम, जो दूर तक यात्रा और खोज करते हैं",
    "देर से पर सोच-समझकर तय किया गया समय — फैसला हो जाने के बाद ज़िम्मेदारी को गंभीरता से लिया जाता है",
    "पटरी से हटकर तरीका — यहाँ अलग तरह के परिवार या अलग समय-सीमा सहज लगते हैं",
    "कल्पनाशील और भावनाओं से जुड़ा रिश्ता — इस क्षेत्र में रचनात्मकता और संवेदनशीलता गहरी बहती है",
]
FOREIGN_12_HI = [
    "विदेश जाने की बेचैन चाहत — अचानक लिए फैसले जितना सोचा था, उससे बेहतर निकलते हैं",
    "सिर्फ़ असली सुरक्षा के लिए जगह बदलना — बिना ठोस वजह और पक्की योजना के आप हिलते नहीं",
    "एक स्थायी बदलाव से ज़्यादा छोटी यात्राएँ और आना-जाना — एक जगह नहीं, कई जगहें",
    "किसी ऐसी जगह की भावनात्मक खिंचाव जो घर जैसी महसूस हो, भले ही वह आपकी शुरुआत से बहुत दूर हो",
    "ऐसा बदलाव जो आपका कद बढ़ाए — चुपचाप जगह बदलने से ज़्यादा संभावना विदेश में पहचान मिलने की है",
    "व्यावहारिक, काम से जुड़ा बदलाव — जीवनशैली की पसंद से ज़्यादा एक पोस्टिंग या असाइनमेंट",
    "किसी रिश्ते या साझेदारी से जुड़ा बदलाव — अकेले लिया गया फैसला शायद ही कभी",
    "एक बदलाव लाने वाला कदम — ऐसा जो सिर्फ़ जगह नहीं, आपको भी बदल देता है",
    "विदेश की तरफ़ मज़बूत और सहज खिंचाव — पढ़ाई, यात्रा या दूर के मौके आपके लिए अच्छे हैं",
    "करियर के ढांचे के लिए बदलाव — एक तबादला या तरक्की की सीढ़ी, कोई अंधा जोखिम नहीं",
    "पटरी से हटकर या दुनिया भर के समुदायों की तरफ़ खिंचाव — शायद आपको विदेश में उम्मीद से ज़्यादा अपनापन महसूस हो",
    "आध्यात्मिक या भावनात्मक खिंचाव — इस भाव की अपनी राशि होने से विदेश का पारंपरिक संकेत दोगुना हो जाता है",
]
FAMILY_9_HI = [
    "पिता-तुल्य लोगों के साथ सीधा, कभी-कभी बेबाक़ रिश्ता — इज़्ज़त ईमानदारी से कमाई जाती है, दूरी बनाकर नहीं",
    "स्थिर और भरोसेमंद पारिवारिक रिश्ते — ऐसे रिश्ते जिन्हें मज़बूत रहने के लिए बार-बार सींचने की ज़रूरत नहीं",
    "बातचीत पर टिके भाई-बहन के रिश्ते — दूरी मिलने से ज़्यादा आसानी से एक फ़ोन कॉल से पट जाती है",
    "पारिवारिक जड़ों से गहरा भावनात्मक जुड़ाव — माता-पिता की सलाह आज भी मायने रखती है, दूर रहकर भी",
    "पिता-तुल्य लोगों के साथ गर्व और तारीफ़ पर टिका रिश्ता — तारीफ़ दोनों तरफ़ से मानी जाने से कहीं ज़्यादा मायने रखती है",
    "फ़र्ज़ पर टिका पारिवारिक रिश्ता — देखभाल शब्दों से ज़्यादा व्यावहारिक मदद से जताई जाती है",
    "सही साबित होने से ज़्यादा पारिवारिक मेलजोल मायने रखता है — शांति बनाए रखना यहाँ एक ताक़त है, भले ही कभी-कभी इसकी क़ीमत चुकानी पड़े",
    "माता-पिता में से किसी एक के साथ गहरा, उलझा हुआ रिश्ता — इसमें गहराई और निजता, दोनों बहुत ज़्यादा हैं",
    "साझा विश्वास या सोच पर टिका रिश्ता — साझा मक़सद के इर्द-गिर्द पारिवारिक रिश्ते और मज़बूत होते हैं",
    "पिता-तुल्य लोगों के साथ औपचारिक, इज़्ज़त पर टिका रिश्ता — अपनापन असली है, पर खुलकर कम दिखता है",
    "पटरी से हटकर पारिवारिक ढांचा — चुना हुआ परिवार या अनोखी व्यवस्थाएँ खून के रिश्तों जितनी ही असली लगती हैं",
    "दयालु और माफ़ करने वाला रिश्ता — पुरानी पारिवारिक खटास समय के साथ सख़्त होने की बजाय नरम पड़ जाती है",
]
VY_HOUSE_ROLE_HI = {
    "self & trade sense": "खुद और व्यापारिक समझ", "savings & money": "बचत और पैसा",
    "drive & courage": "जोश और हिम्मत", "base & assets": "ठिकाना और संपत्ति",
    "ideas & risk": "विचार और जोखिम", "effort & competition": "मेहनत और मुक़ाबला",
    "partners & deals": "साझेदार और सौदे", "upheaval & change": "उथल-पुथल और बदलाव",
    "fortune & mentors": "किस्मत और गुरु", "work & status": "काम और रुतबा",
    "gains & income": "फ़ायदा और आमदनी", "outflow & distance": "खर्च और दूरी",
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
REMEDY_GEM_HI = {
    "Sun": "रूबी (माणिक) — सिर्फ़ तभी जब सूर्य अच्छी स्थिति में हो",
    "Moon": "मोती — सिर्फ़ तभी जब चंद्र अच्छी स्थिति में हो",
    "Mars": "मूँगा — सिर्फ़ तभी जब मंगल अच्छी स्थिति में हो",
    "Mercury": "पन्ना — सिर्फ़ तभी जब बुध अच्छी स्थिति में हो",
    "Jupiter": "पुखराज — सिर्फ़ तभी जब गुरु अच्छी स्थिति में हो",
    "Venus": "हीरा/सफ़ेद पुखराज — सिर्फ़ तभी जब शुक्र अच्छी स्थिति में हो",
    "Saturn": "नीलम — सिर्फ़ किसी जानकार की सलाह और परीक्षण के बाद, अगर शनि अच्छी स्थिति में हो",
}
REMEDY_NODE_HI = {
    "Rahu": "राहु के दौर में कोई रत्न सुझाया नहीं जाता — दिनचर्या स्थिर रखें और फैसले जल्दबाज़ी में न लें",
    "Ketu": "केतु के दौर में कोई रत्न सुझाया नहीं जाता — स्पष्टता, समापन और सादी आदतों को अहमियत दें",
}
DAY_HI = {
    "Sunday": "रविवार", "Monday": "सोमवार", "Tuesday": "मंगलवार",
    "Wednesday": "बुधवार", "Thursday": "गुरुवार", "Friday": "शुक्रवार", "Saturday": "शनिवार",
}

AREA_ORDER = ["career", "money", "marriage", "children", "home", "foreign", "health", "growth", "family"]
AREA_LABEL_HI = {
    "career": "करियर और दिशा", "money": "पैसा और आर्थिक सुरक्षा", "marriage": "विवाह और साथी",
    "children": "बच्चे और परिवार", "home": "घर और संपत्ति", "foreign": "विदेश यात्रा और स्थानांतरण",
    "health": "स्वास्थ्य और ऊर्जा", "growth": "व्यक्तिगत विकास और पहचान", "family": "पारिवारिक रिश्ते",
    "timing": "समय",
}
# House number -> where it surfaces in Part 1 -- the SAME house/area pairing
# _area_fact() already uses in products.py (10th=career, 2nd=money, 7th=
# marriage, 5th=children, 4th=home, 12th=foreign, 6th=health, 1st=growth,
# 9th=family); 3rd/8th/11th have no dedicated Part-1 page.
HOUSE_AREA_LINE_HI = {
    1: "व्यक्तिगत विकास और पहचान के रूप में शामिल",
    2: "पैसा और आर्थिक सुरक्षा के रूप में शामिल",
    3: "पास के तर्क को सहारा देता है",
    4: "घर और संपत्ति के रूप में शामिल",
    5: "बच्चे और परिवार के रूप में शामिल",
    6: "स्वास्थ्य और ऊर्जा के रूप में शामिल",
    7: "विवाह और साथी के रूप में शामिल",
    8: "पास के तर्क को सहारा देता है",
    9: "पारिवारिक रिश्ते के रूप में शामिल",
    10: "करियर और दिशा के रूप में शामिल",
    11: "पास के तर्क को सहारा देता है",
    12: "विदेश यात्रा और स्थानांतरण के रूप में शामिल",
}
AREA_TITLE_HI = {
    "career": "आपकी कुंडली क्या कहती है", "money": "आपके लिए पैसा कैसे चलता है",
    "marriage": "आपको साथी में क्या चाहिए", "children": "अपने तरीके से परिवार बनाना",
    "home": "आप कहाँ और कैसे जड़ें जमाते हैं", "foreign": "क्या दूरी आपको सूट करती है",
    "health": "आपका शरीर आम तौर पर कैसे चलता है", "growth": "क्या सहज आता है, और क्या नहीं",
    "family": "माता-पिता, भाई-बहन और पुराने रिश्ते",
}
AREA_ICON = {
    "career": "i-compass", "money": "i-coins", "marriage": "i-people", "children": "i-gem",
    "home": "i-shield", "foreign": "i-target", "health": "i-moon", "growth": "i-scales",
    "family": "i-people",
}
AREA_REFLECT_HI = {
    "career": "आपकी करियर ज़िंदगी में ऐसा कहाँ है, जहाँ आप अब भी किसी ऐसी इजाज़त का इंतज़ार कर रहे हैं जिसकी असल में ज़रूरत ही नहीं?",
    "money": "क्या आपका पैसों का तरीका विरासत में मिला है, या आपने असल में खुद चुना है?",
    "marriage": "आपको साथी से असल में क्या चाहिए — न कि वह जो आपको लगता है कि चाहना चाहिए?",
    "children": "क्या आप अपने परिवार को अपनी रफ़्तार से बना रहे हैं, या किसी और की रफ़्तार से?",
    "home": "आप अभी जहाँ रहते हैं, क्या वह जगह जड़ों जैसी महसूस होती है, या बस एक पड़ाव?",
    "foreign": "अगर कल कोई दूर की पुकार आए, तो क्या आप जाएँगे — या यह झिझक है, सच्चाई नहीं?",
    "health": "आपका शरीर आपको पहले से क्या बता रहा है, जिसे आप अनसुना करते आ रहे हैं?",
    "family": "कौन-सा पारिवारिक रिश्ता आप प्यार से निभा रहे हैं, और कौन-सा सिर्फ़ आदत से?",
    "growth": "मेरी ज़िंदगी के अलग-अलग हिस्सों में कौन-सा पैटर्न बार-बार सामने आता है?",
}
# Evergreen, non-astrology do/watch advice per area (matches the reference's
# own generic practical guidance — not derived from the chart, same for
# every user, exactly as the reference's own do/watch lists are).
AREA_DO_HI = {
    "career": ["आपको ग्राहक या पहचान दिलाने वाले हुनर को और तराशते रहें।",
               "उन रिश्तों और नेटवर्क में समय लगाएँ जो अक्सर आपके लिए दरवाज़े खोलते हैं।",
               "अगर भूमिका या दिशा बदलने का मौका सामने है, तो इसे परखने के लिए यह एक ठीक दौर है।"],
    "money": ["आमदनी का एक हिस्सा व्यवस्थित बचत में डालते रहें, सिर्फ़ ज़रूरत पड़ने पर खर्च करने के बजाय।",
              "आमदनी के तरीके अलग-अलग रखें — एक से ज़्यादा ज़रिया एक से बेहतर काम करता है।",
              "जल्दी, एकबारगी फ़ायदे के पीछे भागने के बजाय, फ़ायदे को बढ़ने दें।"],
    "marriage": ["साथी से जो वाकई उम्मीद है, वह कहें — यह मानने के बजाय कि बात समझी जा चुकी है।",
                 "रिश्ते को अपनी ही रफ़्तार से बढ़ने की उतनी ही जगह दें, जितनी आप अपने लिए चाहते हैं।",
                 "बड़े इशारों के बजाय निरंतरता और साथ निभाने को चुनें।"],
    "children": ["इस रिश्ते को खोलने पर मजबूर करने के बजाय, इसे जो गहराई और निजता चाहिए, उसकी रक्षा करें।",
                 "तुरंत नज़दीकी की उम्मीद करने के बजाय, भरोसे को धीरे-धीरे बनने दें।",
                 "बड़े पारिवारिक फैसले तब लें जब आप दोनों कम जल्दबाज़ी में हों।"],
    "home": ["कोई फैसला पक्का करने से पहले, इस जगह को साझा करने वालों को शामिल करें।",
             "सिर्फ़ थोड़े समय के लिए अच्छे दिखने वाले फैसले से ज़्यादा, लंबे समय की स्थिरता को प्राथमिकता दें।",
             "यहाँ तालमेल की तरफ़ अपने मन के खिंचाव पर भरोसा करें — यह आम तौर पर सही दिशा दिखाता है।"],
    "foreign": ["जिन योजनाओं को आप टालते रहे हैं, उन पर आगे बढ़ने का यह एक ठीक मौका है।",
                "आने वाले किसी शांत दौर के लिए भंडार बनाने में इस समय का इस्तेमाल करें — समय, बचत, सद्भावना।",
                "गति पर भरोसा करें, पर अपनी सामान्य समझ बनाए रखें; एक अच्छा मौका कोई खुली छूट नहीं है।"],
    "health": ["नियमित नींद और खाने के समय को किसी भी नई दिनचर्या से ज़्यादा प्राथमिकता दें।",
               "शरीर के शुरुआती संकेतों को गंभीरता से लें, इंतज़ार करने के बजाय।",
               "ऐसी हरकत चुनें जो असल में अच्छी लगे — अनुशासन तभी टिकता है जब वह सज़ा जैसा न लगे।"],
    "family": ["पुरानी खटास को ज़बरदस्ती सुलझाने के बजाय, उसे धीरे-धीरे नरम होने की जगह दें।",
               "रिश्ते में गर्मजोशी बनाए रखने वाला छोटा-सा इशारा करने वाले आप ही बनें।",
               "सही साबित होने की ज़िद के बजाय, करुणा को आगे रखें।"],
    "growth": ["भावना से आगे बढ़ने वाली अपनी सहज-बुद्धि पर भरोसा करें — यह यहाँ एक असली ताकत है, कमज़ोरी नहीं।",
               "अपनी ज़िंदगी के अलग-अलग हिस्सों में दोहराए जाने वाले पैटर्न पर ध्यान दें; वे आमतौर पर कुछ कह रहे होते हैं।",
               "सिर्फ़ तर्क से नहीं, अंतर्ज्ञान से भी आगे बढ़ने की खुद को इजाज़त दें।"],
}
AREA_WATCH_HI = {
    "career": ["एक आरामदायक दौर को चुपचाप ठहराव में न बदलने दें — बीच-बीच में अपनी दिशा जाँचते रहें।"],
    "money": ["दबाव में लिए गए जल्दबाज़ी वाले खर्च, उधार देने या लेने के फैसलों से बचें।"],
    "marriage": ["शांत दौर को उदासीनता न समझें — यह क्षेत्र अपनी ही रफ़्तार से चलता है।"],
    "children": ["बाहरी दबाव (परिवार, समय-सीमा) को यहाँ अपनी रफ़्तार पर हावी न होने दें।"],
    "home": ["किसी बड़े संपत्ति फैसले में किसी और की पसंद को अपनी पसंद पर पूरी तरह हावी न होने दें।"],
    "foreign": ["सिर्फ़ इसलिए कोई बड़ा फैसला न लें क्योंकि रास्ता अभी आसान महसूस हो रहा है।"],
    "health": ["सिर्फ़ इसलिए पुरानी आदतें न छोड़ें क्योंकि अभी तबीयत ठीक महसूस हो रही है।"],
    "family": ["सिर्फ़ इसलिए पुरानी बहसें न छेड़ें क्योंकि रिश्ता अभी शांत महसूस हो रहा है।"],
    "growth": ["किसी फैसले पर सिर्फ़ इसलिए दोबारा शक न करें क्योंकि वह सबसे 'तार्किक' नहीं था।"],
}
DUSTHANA_HOUSES = (6, 8, 12)
VERDICT_WORD_HI = {"thriving": "अच्छा", "building": "सामान्य", "watch": "ध्यान ज़रूरी"}
VERDICT_BADGE_HI = {"thriving": "अभी स्थिति अच्छी है", "building": "अभी स्थिति सामान्य है",
                     "watch": "अभी थोड़ा ध्यान ज़रूरी है"}
BODY_TEXT_HI = {
    "thriving": "यह क्षेत्र अभी मज़बूत स्थिति में है — कुंडली में यहाँ आपके पक्ष में असली समर्थन है।",
    "building": "यह क्षेत्र अभी धीरे-धीरे और लगातार मेहनत से मज़बूत हो रहा है — कोई अचानक बड़ा बदलाव नहीं।",
    "watch": "यह क्षेत्र अभी थोड़ी सावधानी माँगता है — जल्दबाज़ी से ज़्यादा धैर्य यहाँ काम आएगा।",
}
BALANCE_NOTE_HI = {
    "thriving": "यह एक असली फ़ायदा है — फिर भी यह मेहनत की जगह नहीं लेता।",
    "building": "यहाँ मददगार और ध्यान रखने लायक बातें, दोनों मौजूद हैं — बस इतना है कि जल्दबाज़ी से ज़्यादा धैर्य यहाँ काम आता है।",
    "watch": "यहाँ ध्यान रखने लायक बातें मददगार बातों से थोड़ी ज़्यादा हैं। इसका मतलब यह नहीं कि अच्छे नतीजे नहीं मिलेंगे — बस इतना है कि जल्दबाज़ी से ज़्यादा धैर्य यहाँ काम आता है।",
}


def _ord_hi(n):
    return {1: "पहला", 2: "दूसरा", 3: "तीसरा", 4: "चौथा", 5: "पांचवां", 6: "छठा",
            7: "सातवां", 8: "आठवां", 9: "नौवां", 10: "दसवां", 11: "ग्यारहवां",
            12: "बारहवां"}[n]


def _ord_hi_ob(n):
    """Oblique-case ordinal ('दसवें' not 'दसवां') -- required whenever the
    ordinal is followed by a postposition (के/में/से), e.g. 'दसवें भाव के'.
    Table cells and standalone labels use the nominative _ord_hi() instead."""
    return {1: "पहले", 2: "दूसरे", 3: "तीसरे", 4: "चौथे", 5: "पांचवें", 6: "छठे",
            7: "सातवें", 8: "आठवें", 9: "नौवें", 10: "दसवें", 11: "ग्यारहवें",
            12: "बारहवें"}[n]


def _dignity_phrase(dignity):
    return {"exalted": "अपनी सबसे मज़बूत स्थिति", "own": "अपनी ही राशि में मज़बूत स्थिति",
            "debilitated": "अपनी सबसे कमज़ोर स्थिति"}.get(dignity, "एक सामान्य, औसत स्थिति")


def _build_en_hi_map():
    """Zips each Hindi bank against its REAL English source list (imported,
    not hardcoded) so the already-computed English sentence in the payload
    can be translated by exact lookup -- same safe pattern used elsewhere in
    this codebase (career_growth_hi.py etc)."""
    from products import CAREER_HOUSE as _CH, WEALTH_2L as _W2, GAINS_11L as _G11, \
        HEALTH_6 as _H6, HOME_4 as _HM, CHILDREN_5 as _CD, FOREIGN_12 as _FR, FAMILY_9 as _FM
    m = {}
    for en_list, hi_list in ((_CH, CAREER_HOUSE_HI), (_W2, WEALTH_2L_HI), (_G11, GAINS_11L_HI),
                              (_H6, HEALTH_6_HI), (_HM, HOME_4_HI), (_CD, CHILDREN_5_HI),
                              (_FR, FOREIGN_12_HI), (_FM, FAMILY_9_HI)):
        m.update(zip(en_list, hi_list))
    for en_sign, en_line in SIGN_PARTNER.items():
        m[en_line] = _shi(en_line)
    return m


_EN_HI = _build_en_hi_map()


def _area_headline(area, p):
    """The one topic sentence for this area, translated by exact lookup from
    compute_blueprint()'s already-computed English prose -- the fact itself
    (which of the 12 stock sentences applies) is 100% the engine's choice."""
    en = {
        "career": p["career"]["direction"],
        "money": p["wealth"]["second"],
        "marriage": p["relationship"]["line"],
        "children": p["children"],
        "home": p["home"],
        "foreign": p["foreign"],
        "health": p["health"],
        "family": p["family"],
    }[area]
    return _EN_HI.get(en, en)


def _why_text(area, p, verdict_tag):
    """'X's Nth house lord is Y, sitting in Z sign at <dignity> -- so this
    reads <verdict>.' Built entirely from p["area_detail"][area] (house
    number, lord, lord's sign, lord's dignity) -- all already computed by
    compute_blueprint(), nothing new. Mirrors _wheel_tag()'s own dusthana
    exception (6th/8th/12th houses invert what a strong/weak lord means)."""
    d = p["area_detail"][area]
    house_num, lord, lord_sign, dignity = d["house"], d["lord"], d["lord_sign"], d["dignity"]
    lord_hi, sign_hi = PLANET_HI[lord], SIGN_HI[lord_sign]
    is_dusthana = house_num in DUSTHANA_HOUSES
    strong = dignity in ("exalted", "own")
    weak = dignity == "debilitated"
    lead = (f"आपके {AREA_LABEL_HI[area]} से जुड़े {_ord_hi_ob(house_num)} भाव के स्वामी {lord_hi} हैं, "
            f"और वे {sign_hi} राशि में {_dignity_phrase(dignity)} में बैठे हैं।")
    if is_dusthana and (strong or weak):
        if strong:
            tail = ("सीधी बात में, यहाँ स्वामी ग्रह की मज़बूत स्थिति उस भाव की मुश्किल को ज़्यादा सक्रिय रखती है "
                    "— इसलिए यहाँ थोड़ा ध्यान ज़रूरी माना गया है।")
        else:
            tail = ("सीधी बात में, यह मुश्किलों से जुड़ा भाव है, और यहाँ एक कमज़ोर स्वामी राहत की बात मानी जाती है "
                    "— इसलिए यहाँ स्थिति को अच्छा माना गया है।")
    elif strong:
        tail = "सीधी बात में, यह एक मज़बूत स्थिति है — इसलिए यहाँ स्थिति को अच्छा माना गया है।"
    elif weak:
        tail = "सीधी बात में, यह एक कमज़ोर स्थिति है — इसलिए यहाँ थोड़ा ध्यान ज़रूरी माना गया है।"
    else:
        tail = "सीधी बात में, यह न बहुत मज़बूत स्थिति है, न कमज़ोर — इसलिए यहाँ स्थिति को सामान्य माना गया है।"
    return lead + " " + tail


def _favour_watch(area, p, verdict_tag):
    """Reuses the exact same strengths[]/lessons[] cycling render_blueprint's
    own tcard() uses for English -- same real data, same index-cycle logic,
    just Hindi labels."""
    strengths, lessons = p.get("strengths") or [], p.get("lessons") or []
    idx = AREA_ORDER.index(area)

    _fallback_hi = {
        "A balanced chart — no single dominant planet; versatility is itself the gift":
            "एक संतुलित कुंडली — कोई एक ग्रह हावी नहीं; हर काम में ढल जाना ही आपकी असली ताकत है",
        "No major debilitations — your challenges are situational, not structural":
            "कोई बड़ी कमज़ोर स्थिति नहीं — आपकी चुनौतियाँ हालात पर निर्भर हैं, बुनियादी नहीं",
    }

    def _tr(entry):
        if entry in _fallback_hi:
            return _fallback_hi[entry]
        planet, rest = entry.split(" — ", 1)
        planet_hi = PLANET_HI.get(planet, planet)
        if rest.endswith(" (exalted)"):
            return f"{planet_hi} — {PLANET_GIFT_HI.get(planet, rest)} (उच्च का)"
        if rest.endswith(" (own sign)"):
            return f"{planet_hi} — {PLANET_GIFT_HI.get(planet, rest)} (स्वराशि)"
        return f"{planet_hi} — {PLANET_LESSON_HI.get(planet, rest)}"

    if verdict_tag == "watch":
        favour = "जो यहाँ पहले से काम कर रहा है, उसे करते रहें — लगातार मेहनत का फ़ायदा जुड़ता ही जाता है।"
        watching = _tr(lessons[idx % len(lessons)]) if lessons else "अभी यही एक क्षेत्र है जिसमें थोड़ा ज़्यादा धैर्य रखना सही रहेगा।"
    else:
        favour = _tr(strengths[idx % len(strengths)]) if strengths else "आपकी कुंडली यहाँ आपके साथ है — यह शक करने की नहीं, आगे बढ़ने की जगह है।"
        watching = "यहाँ कुछ भी ध्यान देने लायक नहीं — हमेशा जैसी सावधानी ही काफ़ी है।"
    return favour, watching


def _roadmap_phase_html(p):
    """The SAME real global roadmap (current + next 2 Mahadashas) shown
    identically on every area page -- the only real timeline
    compute_blueprint() has; no per-area window is invented."""
    rows = p.get("roadmap") or []
    out = []
    for i, r in enumerate(rows):
        lord_hi = PLANET_HI.get(r["lord"], r["lord"])
        theme_hi = MD_PHASE_HI.get(r["lord"], r["theme"])
        label = "मौजूदा महादशा" if r["current"] else "अगली महादशा"
        cls = "good" if r["current"] else ""
        out.append(
            f'<div class="phaserow {cls}"><div class="yrs">{label} <span class="tlrange">{r["from"]}&ndash;{r["to"]}</span></div>'
            f'<div><span class="tag">{lord_hi} महादशा</span></div>'
            f'<div class="note">{theme_hi}।</div></div>'
        )
    return "".join(out)


# ===========================================================================
# Additive CSS — new class names only. _VYAPAR_CSS already supplies .page,
# .eyebrow, h2.head, .rule, .lead, .pts/.pt/.tx, .verdict, .cov-*, .kundli/
# .kc, table.k/.tscroll, .callout, .win (all reused verbatim above); this
# block adds only the shapes English's design doesn't need. `.blockhead`
# gets the same card look as _VYAPAR_CSS's `.page` (cream, rounded, shadowed)
# so every new section reuses the same visual language, just sized to its
# own (denser, Part-2-heavy) content instead of a fixed one-screen height.
# ===========================================================================
BLUEPRINT_HI_CSS = """
.blockhead{width:min(430px,92vw);margin:0 auto 24px;min-height:min(830px,192vw);
  padding:clamp(30px,6.5vw,40px) clamp(22px,5.5vw,30px);
  display:flex;flex-direction:column;justify-content:center;text-align:center;background:var(--cream);
  border-radius:22px;box-shadow:0 14px 38px rgba(48,34,14,.18);position:relative}
.blockhead .area-open,.blockhead .area-close,.blockhead .area-close2{width:100%;margin-top:18px}
.blockhead .area-open:first-child{margin-top:0}
.blockhead.page-center{align-items:center;justify-content:center;min-height:min(500px,120vw)}
.page-center-inner{width:100%}
.divider{width:min(430px,92vw);margin:0 auto 24px;padding:60px 30px;text-align:center;
  background:linear-gradient(165deg,var(--sand),var(--sand2));border-radius:22px;
  box-shadow:0 14px 38px rgba(48,34,14,.18);display:flex;flex-direction:column;align-items:center;gap:10px}
.divider .dn{font-family:var(--serif,var(--display));font-size:40px;color:var(--gold);opacity:.6}
.divider .dt{font-family:var(--serif,var(--display));font-weight:600;font-size:26px;color:var(--ink)}
.divider .ds{font-size:14px;color:var(--muted);max-width:40ch}
.divider .dlist{margin-top:14px;columns:2;column-gap:18px;text-align:left;width:100%}
.divider .dlist div{font-size:12.5px;color:var(--body);padding:5px 0;border-bottom:1px solid var(--line)}
.sccols{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px;text-align:left}
.sccols.tight{gap:8px}
.sccard{background:var(--card,#fff);border:1px solid var(--line);border-radius:14px;padding:14px}
.sccard.str{border-left:3px solid var(--green)}
.sccard.chg{border-left:3px solid var(--terra)}
.sch{font-weight:700;font-size:13px;color:var(--ink);display:flex;align-items:center;gap:6px}
.scitem{font-size:13px;color:var(--muted);margin-top:6px;line-height:1.5}
.reasoncard{background:var(--gold-bg,#FBF4E7);border-radius:14px;padding:14px 16px;margin-top:14px;text-align:left}
.reasoncard.warn{background:var(--terra-bg)}
.reasoncard .rh{font-weight:700;font-size:12.5px;color:var(--gold);text-transform:uppercase;letter-spacing:.04em}
.reasoncard p{font-size:13.5px;color:var(--body);margin-top:6px;line-height:1.55}
.notecard{background:var(--card,#fff);border:1px solid var(--line);border-radius:16px;padding:18px;margin-top:14px}
.chapterband{background:var(--gold-bg,#FBF4E7);border-radius:14px;padding:12px 16px;margin-top:10px;text-align:left}
.chapterband .cl{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--gold);font-weight:700}
.chapterband .cv{font-size:14px;color:var(--ink);margin-top:2px}
.wheel-wrap{margin-top:14px;display:flex;flex-direction:column;align-items:center}
.wheel-legend{display:flex;justify-content:center;gap:16px;margin-top:6px;flex-wrap:wrap}
.wheel-legend-item{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--body)}
.wheel-legend-dot{width:9px;height:9px;border-radius:50%;display:inline-block}
.phaserow{border-top:1px solid var(--line);padding:10px 0;text-align:left}
.phaserow.good{background:rgba(62,125,90,.06)}
.phaserow .yrs{font-size:12px;font-weight:700;color:var(--ink)}
.phaserow .tlrange{font-weight:400;color:var(--muted);font-size:11px}
.phaserow .tag{display:inline-block;font-size:11px;background:var(--gold-bg,#FBF4E7);color:var(--gold);
  border-radius:999px;padding:2px 9px;margin-top:4px}
.phaserow .note{font-size:12.5px;color:var(--muted);margin-top:4px;line-height:1.5}
.dosdonts{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px;text-align:left}
.ddcol{background:var(--card,#fff);border-radius:14px;padding:12px 14px}
.ddcol h4{font-size:12.5px;display:flex;align-items:center;gap:6px;color:var(--ink)}
.ddcol.do{border-left:3px solid var(--green)}
.ddcol.dont{border-left:3px solid var(--terra)}
.ddcol ul{margin:8px 0 0 16px;padding:0}
.ddcol li{font-size:12px;color:var(--muted);margin-top:5px;line-height:1.5}
.reflect{font-style:italic;color:var(--gold);font-size:13.5px;margin-top:12px;text-align:center}
.tl{margin-top:14px;text-align:left}
.tlrow{border-top:1px solid var(--line);padding:12px 0;position:relative}
.tlrow.current{background:rgba(62,125,90,.06)}
.tlrow .yrs{font-size:13px;font-weight:700;color:var(--ink);display:inline-block}
.tlrow .badge{font-size:10.5px;background:var(--gold-bg,#FBF4E7);color:var(--gold);border-radius:999px;
  padding:2px 9px;margin-left:8px}
.tlrow .lord{font-size:13px;color:var(--ink);margin-top:4px;font-weight:600}
.tlrow .theme{font-size:12.5px;color:var(--muted);margin-top:2px;line-height:1.5}
.gitem{text-align:left;border-top:1px dotted var(--line);padding:10px 0}
.gitem dt{font-weight:700;font-size:13px;color:var(--ink)}
.gitem dd{font-size:12.5px;color:var(--muted);margin-top:4px;line-height:1.55}
"""

# ===========================================================================
# Shared visual pieces — parallel to report_view.py's blueprint_wheel_svg()
# and kundli-grid code (same CSS classes, same math), duplicated only because
# the English function's labels are hardcoded English strings. Nothing in
# report_view.py is touched.
# ===========================================================================
import math as _math

_WHEEL_ORDER = ["career", "money", "marriage", "children", "home", "foreign",
                "health", "growth", "family", "timing"]
_WHEEL_LABEL_HI = {"career": "करियर", "money": "पैसा", "marriage": "विवाह",
                    "children": "बच्चे", "home": "संपत्ति", "foreign": "स्थानांतरण",
                    "health": "स्वास्थ्य", "growth": "विकास", "family": "परिवार",
                    "timing": "समय"}
_WHEEL_COLOR = {"thriving": "#3E7D5A", "building": "#B9862E", "watch": "#B4572B"}


def _wheel_svg_hi(wheel, name, dasha_label):
    cx, cy, r, lr = 160, 160, 92, 122
    n = len(_WHEEL_ORDER)
    spokes, dots, labels = [], [], []
    for i, area in enumerate(_WHEEL_ORDER):
        ang = -_math.pi / 2 + i * (2 * _math.pi / n)
        col = _WHEEL_COLOR.get(wheel.get(area, "building"), _WHEEL_COLOR["building"])
        x, y = cx + r * _math.cos(ang), cy + r * _math.sin(ang)
        lx, ly = cx + lr * _math.cos(ang), cy + lr * _math.sin(ang)
        spokes.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{col}" stroke-width="1.3" opacity=".5"/>')
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5" fill="{col}"/>')
        anchor = "middle"
        if lx < cx - 8: anchor = "end"
        elif lx > cx + 8: anchor = "start"
        labels.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" dominant-baseline="middle" class="wl" fill="{col}">{_WHEEL_LABEL_HI[area]}</text>')
    return f"""<svg viewBox="0 0 320 320" class="wheelchart" role="img" aria-label="आपका जीवन चक्र">
<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#E9E1D0" stroke-width="1.4"/>
<circle cx="{cx}" cy="{cy}" r="{r*0.64:.0f}" fill="none" stroke="#E9E1D0" stroke-width="1"/>
{''.join(spokes)}
{''.join(dots)}
<circle cx="{cx}" cy="{cy}" r="44" fill="#FAF5ED" stroke="#B9862E" stroke-width="1.4"/>
<text x="{cx}" y="{cy-5}" text-anchor="middle" class="wn">{escape(name)}</text>
<text x="{cx}" y="{cy+12}" text-anchor="middle" class="wd">{dasha_label}</text>
<style>.wl{{font:700 11px sans-serif}}.wn{{font:700 14px 'Fraunces',Georgia,serif;fill:#2A2338}}.wd{{font:600 9.5px sans-serif;fill:#8A8199}}</style>
{''.join(labels)}
</svg>"""


# South-Indian fixed layout: (Sanskrit sign, grid-column, grid-row) -- same
# geometry report_view.py's VY_KUNDLI_LAYOUT uses for English.
_KUNDLI_LAYOUT = [("Meena", 1, 1), ("Mesha", 2, 1), ("Vrishabha", 3, 1),
                  ("Mithuna", 4, 1), ("Kumbha", 1, 2), ("Karka", 4, 2),
                  ("Makara", 1, 3), ("Simha", 4, 3), ("Dhanu", 1, 4),
                  ("Vrishchika", 2, 4), ("Tula", 3, 4), ("Kanya", 4, 4)]
_PLANET_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]


def _kundli_grid_html(p, name):
    lagna_sa = p["chart"]["lagna"]
    planets = p["chart"]["planets"]
    by_sign = {}
    for pl, info in planets.items():
        by_sign.setdefault(info["sign"], []).append(PLANET_HI[pl])
    cells = ""
    for sa, col, row in _KUNDLI_LAYOUT:
        occ = by_sign.get(sa, [])
        pl_html = f'<div class="pl">{" · ".join(occ)}</div>' if occ else ""
        is_asc = (sa == lagna_sa)
        label = f'{SIGN_HI[sa]}{" &middot; लग्न" if is_asc else ""}'
        cells += (f'<div class="kc{" asc" if is_asc else ""}" style="grid-column:{col};grid-row:{row}">'
                  f'<div class="sn">{label}</div>{pl_html}</div>')
    cells += (f'<div class="kc center" style="grid-column:2/4;grid-row:2/4">'
              f'<b>{escape(name)}</b><span>{SIGN_HI[lagna_sa]} लग्न</span></div>')
    return cells


def _planet_house(info, lagna_idx):
    return ((SIGNS.index(info["sign"]) - lagna_idx) % 12) + 1


_ASPECT_EXTRA = {"Mars": (4, 8), "Jupiter": (5, 9), "Saturn": (3, 10)}


def _house_connections(p, lagna_idx, target_house):
    """Who occupies or aspects a given house -- standard Parashari rules only:
    every classical graha aspects the 7th house from itself; Mars/Jupiter/
    Saturn additionally cast their special aspects (4th&8th / 5th&9th /
    3rd&10th). Rahu/Ketu are listed only when they occupy the house outright
    -- classical texts disagree on nodal aspects, so no aspect is asserted
    for them here rather than guess at a contested rule."""
    planets = p["chart"]["planets"]
    conns = []
    for pl in _PLANET_ORDER:
        info = planets.get(pl)
        if not info:
            continue
        h = _planet_house(info, lagna_idx)
        if h == target_house:
            conns.append((pl, "sit"))
            continue
        if pl in ("Rahu", "Ketu"):
            continue
        for off in (7,) + _ASPECT_EXTRA.get(pl, ()):
            if ((h - 1 + (off - 1)) % 12) + 1 == target_house:
                conns.append((pl, "aspect"))
                break
    return conns


def _planet_table_html(p):
    planets = p["chart"]["planets"]
    lagna_sa = p["chart"]["lagna"]
    lagna_num = SIGNS.index(lagna_sa)
    rows = ""
    for pl in _PLANET_ORDER:
        info = planets.get(pl)
        if not info:
            continue
        house_num = ((SIGNS.index(info["sign"]) - lagna_num) % 12) + 1
        role_en = VY_HOUSE_ROLE.get(house_num, "")
        role_hi = VY_HOUSE_ROLE_HI.get(role_en, role_en)
        dign_hi = {"exalted": "उच्च का", "own": "स्वराशि", "debilitated": "नीच का"}.get(info.get("dignity"), "सामान्य")
        retro = " &middot; वक्री" if info.get("retro") else ""
        rows += (f'<tr><td>{PLANET_HI[pl]}</td><td>{SIGN_HI[info["sign"]]}</td>'
                 f'<td>{_ord_hi(house_num)}</td><td>{dign_hi}{retro}</td></tr>')
    return rows


def area_block(area, p, num):
    """One Part-1 area page: verdict badge, headline, body, why-reasoncard,
    favour/watching cards, the shared real roadmap timeline, do/watch lists,
    balance note, reflection quote. Every dynamic value traces back to `p`."""
    tag = p["wheel"][area]
    cls = {"thriving": "good", "watch": "warn"}.get(tag, "")
    label_part = AREA_LABEL_HI[area]
    if area == "growth":
        lagna_idx = SIGNS.index(p["chart"]["lagna"])
        headline = LAGNA_PERSONA_HI[lagna_idx]
        body_extra = ""
    else:
        headline = _area_headline(area, p)
        body_extra = ""
    why_text = _why_text(area, p, tag)
    favour, watching = _favour_watch(area, p, tag)
    do_html = "".join(f"<li>{x}</li>" for x in AREA_DO_HI[area])
    watch_html = "".join(f"<li>{x}</li>" for x in AREA_WATCH_HI[area])
    phase_html = _roadmap_phase_html(p)
    reflect = AREA_REFLECT_HI[area]
    icon_name = AREA_ICON[area]
    verdict_icon = "i-check" if cls == "good" else ("i-alert" if cls == "warn" else "i-clock")
    return f"""<div class="blockhead">
  <div class="area-open">
  <div class="eyebrow">भाग 1 &middot; {num} में से 10 &middot; {label_part}</div>
  <h2 class="head">{AREA_TITLE_HI[area]}</h2>
  <div class="rule"></div>
  <div class="verdict {cls}">{icon(verdict_icon)} {VERDICT_BADGE_HI[tag]}</div>
  <div class="lead">{headline}।</div>
  <div class="lead" style="font-size:16px;margin-top:6px;line-height:1.5">{BODY_TEXT_HI[tag]}</div>
  <div class="reasoncard"><div class="rh">यह ऐसा क्यों पढ़ता है</div>
  <p>{why_text}</p></div>
  </div>
  <div class="area-close">
  <div class="sccols">
    <div class="sccard str"><div class="sch">{icon('i-check')} आपके पक्ष में क्या काम कर रहा है</div><div class="scitem">{favour}</div></div>
    <div class="sccard chg"><div class="sch">{icon('i-alert')} किस पर नज़र रखनी है</div><div class="scitem">{watching}</div></div>
  </div>
  <div class="eyebrow" style="margin-top:22px">भाग 1 &middot; {num} &middot; {label_part}</div>
  <h3 class="sub" style="margin-top:6px">आपके अध्यायों के हिसाब से</h3>
  <div>{phase_html}</div>
  </div>
  <div class="area-close2">
  <div class="dosdonts">
    <div class="ddcol do"><h4>{icon('i-check')} करें</h4><ul>{do_html}</ul></div>
    <div class="ddcol dont"><h4>{icon('i-alert')} ध्यान रखें</h4><ul>{watch_html}</ul></div>
  </div>
  <div class="note">{BALANCE_NOTE_HI[tag]}</div>
  <div class="reflect">&ldquo;{reflect}&rdquo;</div>
  </div>
</div>"""


def _timing_block(p):
    """Area 10 -- Timing. Not house-based like the other nine: its verdict
    reads the CURRENT Mahadasha lord's own dignity (or Sade Sati override),
    exactly matching compute_blueprint()'s own `wheel["timing"]` rule."""
    tag = p["wheel"]["timing"]
    cls = {"thriving": "good", "watch": "warn"}.get(tag, "")
    sade = p.get("sade_sati") or {}
    d = p["area_detail"]["timing"]
    md = p.get("dasha_current_md")
    lord_hi = PLANET_HI.get(d["lord"], d["lord"]) if d else "—"
    if sade.get("active"):
        why = (f"आपकी मौजूदा महादशा के स्वामी {lord_hi} हैं, लेकिन अभी साढ़े साती सक्रिय है "
               f"— शनि आपके जन्म-चंद्र के पास से गुज़र रहा है, इसलिए यहाँ थोड़ा ध्यान ज़रूरी माना गया है, "
               f"चाहे {lord_hi} की अपनी स्थिति कैसी भी हो।")
    else:
        why = _why_text_planet(lord_hi, d["lord_sign"] if d else None, d["dignity"] if d else None, tag)
    md_line = (f'{lord_hi} महादशा, {month_hi(md["from"])} से {month_hi(md["to"])} तक।' if md else "")
    phase_html = _roadmap_phase_html(p)
    return f"""<div class="blockhead">
  <div class="area-open">
  <div class="eyebrow">भाग 1 &middot; 10 में से 10 &middot; समय</div>
  <h2 class="head">क्या अभी वह पल है?</h2>
  <div class="rule"></div>
  <div class="verdict {cls}">{icon('i-check' if cls=='good' else ('i-alert' if cls=='warn' else 'i-clock'))} {VERDICT_BADGE_HI[tag]}</div>
  <div class="lead">{md_line}</div>
  <div class="reasoncard"><div class="rh">यह ऐसा क्यों पढ़ता है</div><p>{why}</p></div>
  </div>
  <div class="area-close">
  <h3 class="sub" style="margin-top:6px">आपके आगे के अध्याय</h3>
  <div>{phase_html}</div>
  <div class="note">दौर मौके होते हैं, पक्की तारीख़ें नहीं। ये आपके मौके बढ़ाते हैं — मेहनत फिर भी आपकी अपनी ही रहती है।</div>
  </div>
</div>"""


def _why_text_planet(lord_hi, lord_sign, dignity, tag):
    sign_hi = SIGN_HI.get(lord_sign, lord_sign) if lord_sign else ""
    dign_phrase = _dignity_phrase(dignity)
    concl = {"अच्छा": "मज़बूत", "सामान्य": "सामान्य, औसत", "ध्यान ज़रूरी": "कमज़ोर"}[VERDICT_WORD_HI[tag]]
    return (f"{lord_hi} अभी {sign_hi} राशि में {dign_phrase} में बैठे हैं। सीधी बात में, यह एक {concl} स्थिति है "
            f"— इसलिए यहाँ स्थिति को {VERDICT_WORD_HI[tag]} माना गया है।")


def render_blueprint_hi(p: dict) -> str:
    """The full, paid Hindi Life Blueprint report -- a real rendering
    function driven entirely by compute_blueprint()'s real output for this
    exact birth chart. Structure matches the finalized Hindi reference: Part
    1 (ten life areas) + Part 2 (kundli, planet table, houses, dasha
    timeline, transits, Sade Sati, "how every tag was set", a worked
    example, the full area-to-house-to-lord map, an honesty page and a
    glossary). No English HTML is generated or translated anywhere in this
    function -- report_view.render_blueprint() is never called."""
    m = p["meta"]
    name = escape(m.get("name", ""))
    lagna_sa = p["chart"]["lagna"]
    moon_sa = p["chart"]["planets"]["Moon"]["sign"]
    lagna_idx, moon_idx = SIGNS.index(lagna_sa), SIGNS.index(moon_sa)
    lagna_line_hi = LAGNA_PERSONA_HI[lagna_idx]
    moon_line_hi = LAGNA_PERSONA_HI[moon_idx]
    teaser = p["teaser"]
    wheel = p["wheel"]
    roadmap = p.get("roadmap") or []
    cur_md = roadmap[0] if roadmap else None
    ad_lord_hi = PLANET_HI.get(teaser.get("cur_ad_lord"), "") if teaser.get("cur_ad_lord") else ""
    dasha_label = f'{PLANET_HI.get(cur_md["lord"], "")} महादशा — {ad_lord_hi} अंतर्दशा' if cur_md and ad_lord_hi else (PLANET_HI.get(cur_md["lord"], "") + " महादशा" if cur_md else "")

    wheel_svg = _wheel_svg_hi(wheel, name, dasha_label)
    legend = ('<div class="wheel-legend">'
              '<span class="wheel-legend-item"><span class="wheel-legend-dot" style="background:#3E7D5A"></span>अच्छा</span>'
              '<span class="wheel-legend-item"><span class="wheel-legend-dot" style="background:#B9862E"></span>सामान्य</span>'
              '<span class="wheel-legend-item"><span class="wheel-legend-dot" style="background:#B4572B"></span>ध्यान ज़रूरी</span>'
              '</div>')

    # ---- Cover ----
    cover = f"""<div class="cover">
  <div class="cov-brand">AXTROSHASTRA &middot; जीवन ब्लूप्रिंट</div>
  <div class="cov-name">{name}</div>
  <div class="cov-line">{lagna_line_hi}</div>
  <div class="cov-pills">
    <span class="cp">&#9790; {SIGN_HI[moon_sa]} में चंद्र</span>
    <span class="cp">&#9651; {SIGN_HI[lagna_sa]} लग्न</span>
    <span class="cp">{dasha_label}</span>
  </div>
  <div class="cov-tag">आपके जीवन के दस क्षेत्र, एक ही कुंडली से पढ़े गए।</div>
  <div class="cov-footer">
    <div class="cov-meta">स्विस इफ़ेमेरिस &middot; लाहिड़ी अयनांश{f" &middot; जन्म समय {_time_of_day_hi(m.get('tob'))}" if _time_of_day_hi(m.get('tob')) else ""}</div>
    <div class="cov-meta right">तैयार की गई {m.get("generated", "")}</div>
  </div>
</div>"""

    # ---- Note for you ----
    first_name = name.split(" ")[0] if name else ""
    note = f"""<div class="blockhead" style="margin-top:40pt">
  <div class="eyebrow" style="text-align:center;display:block">आपके लिए एक बात</div>
  <h2 class="head" style="text-align:center">आगे पढ़ने से पहले</h2>
  <div class="rule" style="margin-left:auto;margin-right:auto"></div>
  <div class="notecard">
    <div class="lead">प्रिय {first_name}, यह रिपोर्ट एक ही जन्म-कुंडली से आपके जीवन के दस क्षेत्र पढ़ती है &mdash; और फिर आपको बिल्कुल दिखाती है कि हर बात किस आधार पर कही गई।</div>
    <div class="lead" style="font-size:16px;margin-top:10px">यहाँ कुछ भी अंदाज़े से नहीं कहा गया। जहाँ आपकी कुंडली मज़बूत है, हम वही कहते हैं। जहाँ धैर्य की ज़रूरत है, वह भी कहते हैं।</div>
    <div class="lead" style="font-size:16px;margin-top:10px">भाग 1 में पढ़ें कि यह क्या कहती है। भाग 2 में पढ़ें, अगर आप हमारा काम जाँचना चाहते हैं।</div>
    <div class="note" style="border-top:none;padding-top:6px;font-style:italic;text-align:center;color:var(--gold);font-weight:600">&mdash; आपका ज्योतिष, AxtroShastra</div>
  </div>
</div>"""

    # ---- Contents ----
    toc_rows = [("00", "एक नज़र में")] + [(f"0{i+1}" if i < 9 else str(i+1), AREA_LABEL_HI[a])
                                          for i, a in enumerate(AREA_ORDER + ["timing"])]
    toc_html = "".join(f'<div class="scitem" style="border-top:1px dotted var(--line);padding-top:8px;margin-top:8px"><b>{n}</b> &nbsp; {t}</div>' for n, t in toc_rows)
    toc = f"""<div class="blockhead">
  <div class="area-open">
  <div class="eyebrow">इस रिपोर्ट में क्या है</div>
  <h2 class="head">विषय-सूची</h2>
  <div class="rule"></div>
  <div class="lead" style="font-size:16px">भाग 1 आपके जीवन के दस क्षेत्र पढ़ता है। भाग 2 दिखाता है कि हर बात किस आधार पर कही गई।</div>
  <div style="margin-top:6px">{toc_html}</div>
  <div class="note">भाग 2 &mdash; &ldquo;यह निष्कर्ष कैसे निकले&rdquo; भाग 1 के बाद शुरू होता है।</div>
  </div>
</div>"""

    # ---- At a glance / wheel ----
    glance = f"""<div class="blockhead">
  <div class="area-open">
  <div class="eyebrow">एक नज़र में</div>
  <h2 class="head">आपका जीवन ब्लूप्रिंट</h2>
  <div class="rule"></div>
  <div class="chapterband"><div><div class="cl">मौजूदा अध्याय</div><div class="cv">{dasha_label}, {month_hi(teaser.get("dasha_till", ""))} तक</div></div></div>
  <div class="sccols" style="margin-top:16px">
    <div class="sccard str"><div class="sch">लग्न (राशि)</div><div class="scitem" style="border-top:none;margin-top:6px">{SIGN_HI[lagna_sa]} &mdash; हर भाव यहीं से गिना जाता है।</div></div>
    <div class="sccard str"><div class="sch">चंद्र राशि</div><div class="scitem" style="border-top:none;margin-top:6px">{SIGN_HI[moon_sa]} &mdash; {NAKSHATRA_HI.get(teaser["nakshatra"], teaser["nakshatra"])}, पाद {teaser["pada"]}।</div></div>
  </div>
  <div class="wheel-wrap">
    {wheel_svg}
    {legend}
  </div>
  </div>
</div>"""

    # ---- About you ----
    nakp = p["nak_profile"]
    about = f"""<div class="blockhead">
  <div class="area-open">
  <div class="eyebrow">आपके बारे में</div>
  <h2 class="head">कुंडली के अनुसार, आप कौन हैं</h2>
  <div class="rule"></div>
  <div class="pts">
    <div class="pt"><svg class="ic pi"><use href="#i-scales"/></svg><div class="tx"><b>{SIGN_HI[lagna_sa]} लग्न &mdash; आपका बाहरी रूप</b>{lagna_line_hi}।</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-moon"/></svg><div class="tx"><b>{SIGN_HI[moon_sa]} चंद्रमा &mdash; आप अंदर से कैसे चलते हैं</b>{moon_line_hi}।</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-book"/></svg><div class="tx"><b>{NAKSHATRA_HI.get(nakp["nakshatra"], nakp["nakshatra"])} नक्षत्र</b>{_shi(nakp["nature"])}।</div></div>
  </div>
  </div>
</div>"""

    # ---- Part 1: nine area pages + timing ----
    area_pages = "".join(area_block(a, p, f"{i+1:02d}") for i, a in enumerate(AREA_ORDER))
    timing_page = _timing_block(p)

    # ---- Part 2 divider ----
    divider = """<div class="divider">
  <div class="dn">II</div>
  <div class="dt">यह निष्कर्ष कैसे निकले</div>
  <div class="ds">भाग 1 के हर पन्ने के पीछे की पूरी वजह &mdash; आपकी कुंडली, आपके भाव, आपके ग्रह और आपका समय।</div>
  <div class="dlist">
    <div>आपकी कुंडली</div><div>लग्न, चंद्र और नक्षत्र</div>
    <div>हर ग्रह, उसकी जगह पर</div><div>वे भाव जो मायने रखते हैं</div>
    <div>दशाएँ और आपकी समय-रेखा</div><div>गोचर और साढ़े साती</div>
    <div>हर टैग कैसे तय हुआ</div><div>पद्धति और शब्दावली</div>
  </div>
</div>"""

    # ---- Kundli chart ----
    kundli = f"""<div class="blockhead">
  <div class="eyebrow">भाग 2 &middot; आपकी कुंडली</div>
  <h2 class="head">आपकी जन्म-कुंडली</h2>
  <div class="rule"></div>
  <div class="lead" style="font-size:16px">भाग 1 का हर पन्ना इसी एक कुंडली से आता है &mdash; कुछ भी अंदाज़े से नहीं कहा गया, और कोई भी ज्योतिषी इसे जाँच सकता है।</div>
  <div class="kundli">{_kundli_grid_html(p, name)}</div>
  <div class="note" style="text-align:center;border-top:none">दक्षिण-भारतीय शैली &middot; हर ख़ाना एक तय राशि है, आपका लग्न सुनहरे रंग में।</div>
</div>"""

    # ---- Lagna & Moon ----
    lagna_lord_hi = PLANET_HI[SIGN_LORD[lagna_idx]]
    moon_lord_hi = PLANET_HI[SIGN_LORD[moon_idx]]
    lagna_moon = f"""<div class="blockhead">
  <div class="eyebrow">भाग 2 &middot; शुरुआती बिंदु</div>
  <h2 class="head">आपका लग्न और चंद्र</h2>
  <div class="rule"></div>
  <div class="sccols">
    <div class="sccard str"><div class="sch">आपका लग्न</div><div class="scitem" style="border-top:none;margin-top:6px">{SIGN_HI[lagna_sa]} &mdash; जिसके स्वामी {lagna_lord_hi} हैं।</div></div>
    <div class="sccard str"><div class="sch">चंद्र राशि</div><div class="scitem" style="border-top:none;margin-top:6px">{SIGN_HI[moon_sa]} &mdash; {NAKSHATRA_HI.get(nakp["nakshatra"], nakp["nakshatra"])}, पाद {teaser["pada"]} &middot; जिसके स्वामी {moon_lord_hi} हैं।</div></div>
  </div>
  <h3 class="sub">लग्न इतना क्यों मायने रखता है</h3>
  <div class="lead" style="font-size:15px;margin-top:0">हर भाव लग्न से गिना जाता है। करियर, साझेदारी, घर &mdash; सब इसी एक राशि से गिने जाते हैं।</div>
  <h3 class="sub">हम इसे कैसे निकालते हैं</h3>
  <div class="lead" style="font-size:15px;margin-top:0">आपका लग्न सिर्फ़ तारीख़ पर नहीं, बल्कि आपके सटीक जन्म-समय और जगह पर निर्भर करता है &mdash; यह लगभग हर दो घंटे में बदल जाता है।</div>
</div>"""

    # ---- Every planet, placed ----
    planet_table = f"""<div class="blockhead">
  <div class="eyebrow">भाग 2 &middot; पूरी तस्वीर</div>
  <h2 class="head">हर ग्रह, उसकी जगह पर</h2>
  <div class="rule"></div>
  <div class="lead" style="font-size:16px">आपके जन्म के समय आपके नौ ग्रह कहाँ बैठे थे, और वे किस हाल में थे।</div>
  <div class="tscroll"><table class="k"><tr><th>ग्रह</th><th>राशि</th><th>भाव</th><th>स्थिति</th></tr>{_planet_table_html(p)}</table></div>
  <div class="note">स्थिति वाला कॉलम सबसे ज़्यादा मायने रखता है &mdash; भाग 1 का हर टैग यहीं से तय होता है।</div>
</div>"""

    # ---- Loudest voices (retrograde placements) ----
    retro_rows = "".join(
        f'<div class="sccard chg" style="margin-bottom:10px"><div class="sch">{PLANET_HI[pl]} &mdash; वक्री</div>'
        f'<div class="scitem" style="border-top:none;margin-top:6px">{SIGN_HI[info["sign"]]} में, आपके {_ord_hi_ob(_planet_house(info, lagna_idx))} भाव में।</div></div>'
        for pl in _PLANET_ORDER for info in [p["chart"]["planets"].get(pl)]
        if info and info.get("retro")
    )
    loudest = f"""<div class="blockhead">
  <div class="eyebrow">भाग 2 &middot; सबसे तेज़ आवाज़ें</div>
  <h2 class="head">ध्यान देने लायक स्थितियाँ</h2>
  <div class="rule"></div>
  <div class="lead" style="font-size:16px">हर ग्रह एक जैसी ज़ोर से नहीं बोलता। ये भाग 1 की आपकी रीडिंग के पीछे सबसे ज़्यादा काम करते हैं।</div>
  <div style="margin-top:10px">{retro_rows or '<div class="scitem" style="border-top:none">अभी कोई ग्रह वक्री नहीं है &mdash; इस समय कोई अतिरिक्त ज़ोर नहीं जुड़ता।</div>'}</div>
</div>"""

    # ---- House lords & connections (standard occupancy + graha-drishti) ----
    _CONN_AREAS = ["career", "money", "marriage", "children"]
    _CONN_SHORT_HI = {"career": "करियर", "money": "पैसा", "marriage": "विवाह", "children": "बच्चे"}
    conn_rows = ""
    for a in _CONN_AREAS:
        house_num = p["area_detail"][a]["house"]
        conns = [c for c in _house_connections(p, lagna_idx, house_num) if c[0] != p["area_detail"][a]["lord"]]
        items = ", ".join(f'{PLANET_HI[pl]} ({"यहीं बैठा है" if kind == "sit" else "दूर से असर डालता है"})' for pl, kind in conns) or "अभी कोई अतिरिक्त जुड़ाव नहीं।"
        conn_rows += f'<div class="scitem" style="border-top:1px dotted var(--line);padding-top:8px;margin-top:8px"><b>{_CONN_SHORT_HI[a]}</b><br>{items}</div>'
    connections = f"""<div class="blockhead">
  <div class="eyebrow">भाग 2 &middot; जुड़ाव</div>
  <h2 class="head">भावों के स्वामी और जुड़ाव</h2>
  <div class="rule"></div>
  <div class="lead" style="font-size:16px">एक भाव उसके स्वामी से, उसमें बैठे ग्रहों से, और कहीं और से असर डालने वाले ग्रहों &mdash; यानी दृष्टि &mdash; से आकार लेता है।</div>
  <div style="margin-top:6px">{conn_rows}</div>
  <div class="note">पूरी तस्वीर के लिए भाग 1 में हर क्षेत्र देखें।</div>
</div>"""

    # ---- Houses 1-6 / 7-12 ----
    h_all = p["houses_1_12"]
    h1_6, h7_12 = h_all[:6], h_all[6:]
    h1_6_tr = "".join(f'<tr><td>{h["house"]}वां</td><td>{SIGN_HI[h["sign"]]}</td><td>{PLANET_HI[h["lord"]]}</td></tr>' for h in h1_6)
    h7_12_tr = "".join(f'<tr><td>{h["house"]}वां</td><td>{SIGN_HI[h["sign"]]}</td><td>{PLANET_HI[h["lord"]]}</td></tr>' for h in h7_12)
    h1_6_map = "".join(f'<div class="scitem" style="border-top:none;padding-top:0;margin-top:6px">{h["house"]}वां &mdash; भाग 1 में {HOUSE_AREA_LINE_HI[h["house"]]}</div>' for h in h1_6)
    h7_12_map = "".join(f'<div class="scitem" style="border-top:none;padding-top:0;margin-top:6px">{h["house"]}वां &mdash; भाग 1 में {HOUSE_AREA_LINE_HI[h["house"]]}</div>' for h in h7_12)
    houses1 = f"""<div class="blockhead">
  <div class="eyebrow">भाग 2 &middot; बारह भाव</div>
  <h2 class="head">भाव 1&ndash;6</h2>
  <div class="rule"></div>
  <div class="lead" style="font-size:16px">आपकी कुंडली में बारह भाव हैं, हर एक जीवन के अलग हिस्से को दर्शाता है।</div>
  <div class="tscroll"><table class="k"><tr><th>भाव</th><th>राशि</th><th>स्वामी</th></tr>{h1_6_tr}</table></div>
  <h3 class="sub" style="margin-top:14px">भाग 1 में यह कहाँ दिखता है</h3>
  <div>{h1_6_map}</div>
</div>"""
    houses2 = f"""<div class="blockhead">
  <div class="eyebrow">भाग 2 &middot; बारह भाव</div>
  <h2 class="head">भाव 7&ndash;12</h2>
  <div class="rule"></div>
  <div class="tscroll"><table class="k"><tr><th>भाव</th><th>राशि</th><th>स्वामी</th></tr>{h7_12_tr}</table></div>
  <h3 class="sub" style="margin-top:14px">भाग 1 में यह कहाँ दिखता है</h3>
  <div>{h7_12_map}</div>
</div>"""

    # ---- Dashas, explained ----
    dashas_explained = """<div class="blockhead">
  <div class="eyebrow">भाग 2 &middot; समय की व्यवस्था</div>
  <h2 class="head">दशाएँ, समझाई गईं</h2>
  <div class="rule"></div>
  <div class="lead" style="font-size:16px">आपका समय वाला अध्याय एक ही व्यवस्था पर टिका है: ग्रहों के अध्यायों का 120 साल लंबा क्रम, जो आपके चंद्र की जन्म के समय की सटीक स्थिति से निकाला जाता है।</div>
  <div class="sccols">
    <div class="sccard str"><div class="sch">महादशा क्या है</div><div class="scitem" style="border-top:none;margin-top:6px">एक ग्रह के नेतृत्व वाला मुख्य अध्याय, जो 6 से 20 साल तक चलता है।</div></div>
    <div class="sccard str"><div class="sch">अंतर्दशा क्या है</div><div class="scitem" style="border-top:none;margin-top:6px">हर मुख्य अध्याय के भीतर एक उप-अध्याय, जिसका नेतृत्व एक दूसरा ग्रह करता है।</div></div>
  </div>
  <div class="reasoncard"><div class="rh">यह भविष्यवाणी क्यों नहीं है</div>
  <p>एक दशा आपको बताती है कि कौन-से विषय सक्रिय हैं, यह नहीं कि क्या होगा। इसीलिए हर पन्ना दौरों की भाषा में बात करता है।</p></div>
</div>"""

    # ---- Your dasha timeline (current MD's own antardashas) ----
    ads = p.get("dasha_current_ads") or []
    ad_rows = "".join(
        f'<tr><td>{PLANET_HI.get(a["lord"], a["lord"])}</td><td>{month_hi(a["from"])} &ndash; {month_hi(a["to"])}</td><td>{"अभी" if a["current"] else ""}</td></tr>'
        for a in ads
    )
    md = p.get("dasha_current_md")
    dasha_timeline = f"""<div class="blockhead">
  <div class="eyebrow">भाग 2 &middot; यह अध्याय</div>
  <h2 class="head">आपकी दशा समय-रेखा</h2>
  <div class="rule"></div>
  <div class="lead" style="font-size:16px">आपका मौजूदा मुख्य अध्याय {PLANET_HI.get(md["lord"], "") if md else ""} के नेतृत्व में है, जो {month_hi(md["from"]) if md else ""} से {month_hi(md["to"]) if md else ""} तक चलता है।</div>
  <div class="tscroll"><table class="k"><tr><th>उप-अध्याय</th><th>दौर</th><th></th></tr>{ad_rows}</table></div>
  <div class="note">मुख्य अध्याय बड़ा मौसम है; हर उप-अध्याय उसके भीतर का मौसम।</div>
</div>"""

    # ---- Chapters ahead (reuses the same real global roadmap) ----
    tl_rows = "".join(
        f'<div class="tlrow{" current" if r["current"] else ""}"><div class="yrs">{r["from"]} &ndash; {r["to"]}</div>'
        f'<span class="badge">{"अभी" if r["current"] else "आगे"}</span>'
        f'<div class="lord">{PLANET_HI.get(r["lord"], r["lord"])} अध्याय</div>'
        f'<div class="theme">{MD_PHASE_HI.get(r["lord"], r["theme"])}</div></div>'
        for r in roadmap
    )
    chapters_ahead = f"""<div class="blockhead">
  <div class="eyebrow">भाग 2 &middot; आगे के अध्याय</div>
  <h2 class="head">आपकी दशा समय-रेखा, आगे</h2>
  <div class="rule"></div>
  <div class="lead" style="font-size:16px">यह रिपोर्ट जिन मुख्य अध्यायों को देखती है, पूरे विस्तार से।</div>
  <div class="tl">{tl_rows}</div>
  <div class="note">हर &ldquo;आपके अध्यायों के हिसाब से&rdquo; पन्ना इन्हीं दौरों को उस क्षेत्र के भाव के आधार पर पढ़ता है।</div>
</div>"""

    # ---- Where the sky is today (transits) ----
    ya = p.get("year_ahead") or {}
    transits = f"""<div class="blockhead">
  <div class="eyebrow">भाग 2 &middot; अभी</div>
  <h2 class="head">आज आसमान कहाँ है</h2>
  <div class="rule"></div>
  <div class="lead" style="font-size:16px">आपकी दशा लंबे अध्याय दिखाती है। गोचर उसके ऊपर की धीमी चलने वाली मौसमी परत दिखाते हैं।</div>
  <div class="sccols">
    <div class="sccard str"><div class="sch">गुरु अभी है</div><div class="scitem" style="border-top:none;margin-top:6px">{SIGN_HI.get(ya.get("jup_sign"), "")} में &mdash; आपके {_ord_hi_ob(ya.get("jup_house", 1))} भाव में।</div></div>
    <div class="sccard str"><div class="sch">शनि अभी है</div><div class="scitem" style="border-top:none;margin-top:6px">{SIGN_HI.get(ya.get("sat_sign"), "")} में &mdash; आपके {_ord_hi_ob(ya.get("sat_house", 1))} भाव में।</div></div>
  </div>
  <div class="sccols" style="margin-top:12px">
    <div class="sccard str"><div class="sch">गुरु, गुज़रते हुए</div><div class="scitem" style="border-top:none;margin-top:6px">{"एक सहायक जगह — यह आम तौर पर एक अच्छा संकेत है।" if ya.get("jup_good") else "एक शांत जगह — कोई बुरा संकेत नहीं, बस अपनी सबसे मज़बूत जगहों की तुलना में थोड़ी हल्की।"}</div></div>
    <div class="sccard str"><div class="sch">शनि, गुज़रते हुए</div><div class="scitem" style="border-top:none;margin-top:6px">{"यही वजह है आपकी साढ़े साती रीडिंग के पीछे भी — धीमा, भारी दबाव जो धैर्य को इनाम देता है।" if (p.get("sade_sati") or {}).get("active") else "आपकी साढ़े साती से अलग एक हल्की परत — अभी हमेशा जैसा सामान्य अनुशासन ही काफ़ी है।"}</div></div>
  </div>
</div>"""

    # ---- Sade Sati ----
    sade = p.get("sade_sati") or {}
    sade_phase_hi = {"rising phase": "शुरुआती चरण", "peak phase": "सबसे तेज़ चरण", "setting phase": "ढलता चरण"}
    if sade.get("active"):
        verdict_txt = f"साढ़े साती, {sade_phase_hi.get(sade.get('phase'), '')} &mdash; {month_hi(sade.get('ends'))} तक"
        lead_txt = "आप अभी साढ़े साती में हैं &mdash; शनि इस समय आपके जन्म-चंद्र के पास से गुज़र रहा है।"
    else:
        verdict_txt = "अभी सक्रिय नहीं"
        lead_txt = "आप अभी साढ़े साती में नहीं हैं &mdash; इस समय शनि आपके जन्म-चंद्र के पास नहीं है।"
    sade_page = f"""<div class="blockhead">
  <div class="eyebrow">भाग 2 &middot; सबसे जाना-पहचाना चक्र</div>
  <h2 class="head">साढ़े साती</h2>
  <div class="rule"></div>
  <div class="verdict">{icon('i-check')} {verdict_txt}</div>
  <div class="lead" style="font-size:16px;margin-top:12px">{lead_txt}</div>
  <h3 class="sub">इसकी एक तय समाप्ति तारीख़ होती है</h3>
  <div class="lead" style="font-size:15px;margin-top:0">हर कोई जीवन में लगभग तीन बार इससे गुज़रता है। यह इस तरह की ज्योतिष में सबसे अच्छी तरह समझे जाने वाले दौरों में से एक है।</div>
</div>"""

    # ---- How every tag was set ----
    how_set = """<div class="blockhead">
  <div class="eyebrow">भाग 2 &middot; नियम</div>
  <h2 class="head">हर टैग कैसे तय हुआ</h2>
  <div class="rule"></div>
  <div class="lead" style="font-size:16px">हर टैग एक ही खुले नियम से तय होता है &mdash; कोई छिपी हुई गिनती नहीं, कोई बनावटी सटीकता नहीं।</div>
  <div class="sccols">
    <div class="sccard str"><div class="sch">अच्छा</div><div class="scitem" style="border-top:none;margin-top:6px">उस भाव का स्वामी ग्रह अपनी सबसे मज़बूत स्थिति में है &mdash; उच्च का, या अपनी ही राशि में।</div></div>
    <div class="sccard str"><div class="sch">सामान्य</div><div class="scitem" style="border-top:none;margin-top:6px">स्वामी ग्रह एक औसत, स्थिर हालत में है।</div></div>
  </div>
  <div class="sccard chg" style="margin-top:14px"><div class="sch">ध्यान ज़रूरी</div><div class="scitem" style="border-top:none;margin-top:6px">स्वामी ग्रह अपनी कमज़ोर स्थितियों में से एक में है, जिसे पारंपरिक रूप से नीच कहा जाता है।</div></div>
  <div class="note">एक अपवाद: छठे, आठवें और बारहवें भाव के लिए यह नियम पलट जाता है &mdash; वहाँ एक कमज़ोर स्वामी राहत की बात है। यह एक मानक तकनीक है, हमारी अपनी बनाई हुई नहीं।</div>
</div>"""

    # ---- Worked example (career, real data) ----
    cd = p["area_detail"]["career"]
    cd_lord_hi, cd_sign_hi = PLANET_HI[cd["lord"]], SIGN_HI[cd["lord_sign"]]
    cd_tag = wheel["career"]
    worked_example = f"""<div class="blockhead">
  <div class="eyebrow">भाग 2 &middot; उदाहरण के साथ</div>
  <h2 class="head">किसी क्षेत्र की स्थिति दूसरे से बेहतर क्यों होती है</h2>
  <div class="rule"></div>
  <div class="lead" style="font-size:16px">आपकी अपनी कुंडली से उदाहरण, क़दम-दर-क़दम।</div>
  <div class="reasoncard"><div class="rh">करियर &mdash; यहाँ स्थिति {VERDICT_WORD_HI[cd_tag]} क्यों है</div>
  <p>यह आपके {_ord_hi_ob(cd["house"])} भाव से जुड़ा है, और इसके स्वामी {cd_lord_hi} हैं। {cd_lord_hi} {cd_sign_hi} राशि में बैठे हैं, {_dignity_phrase(cd["dignity"])} में। यह हालत उस हर चीज़ पर असर डालती है जिस पर {cd_lord_hi} का स्वामित्व है &mdash; इसलिए यहाँ स्थिति को {VERDICT_WORD_HI[cd_tag]} माना गया है।</p></div>
  <div class="note">भाव &rarr; स्वामी &rarr; स्वामी की हालत। यही तीन क़दम सभी दस टैग के पीछे बैठे हैं।</div>
</div>"""

    # ---- Every reading, in one table ----
    map_rows = "".join(
        f"<tr><td>{AREA_LABEL_HI[a]}</td><td>{p['area_detail'][a]['house'] and _ord_hi(p['area_detail'][a]['house']) or 'दशा अध्याय'}</td>"
        f"<td>{PLANET_HI[p['area_detail'][a]['lord']]}</td><td>{VERDICT_WORD_HI[wheel[a]]}</td></tr>"
        for a in AREA_ORDER + ["timing"]
    )
    mapped_table = f"""<div class="blockhead page-center">
  <div class="page-center-inner">
  <div class="eyebrow">भाग 2 &middot; सब कुछ, नक़्शे पर</div>
  <h2 class="head">हर रीडिंग, एक तालिका में</h2>
  <div class="rule"></div>
  <div class="lead" style="font-size:16px">भाग 1 के दस क्षेत्रों से वापस उस भाव और ग्रह तक का पूरा नक़्शा, जहाँ से हर बात आई।</div>
  <div class="tscroll"><table class="k"><tr><th>क्षेत्र</th><th>भाव</th><th>स्वामी</th><th>रीडिंग</th></tr>{map_rows}</table></div>
  </div>
</div>"""

    # ---- What this report is ----
    what_report = f"""<div class="blockhead">
  <div class="eyebrow">भाग 2 &middot; ईमानदारी</div>
  <h2 class="head">यह रिपोर्ट क्या है</h2>
  <div class="rule"></div>
  <div class="sccols">
    <div class="sccard str"><div class="sch">{icon('i-check')} हम ईमानदारी से आपको क्या बता सकते हैं</div>
      <div class="scitem">आपके भावों और ग्रहों से मिली सामान्य प्रवृत्तियाँ।</div>
      <div class="scitem">अच्छे-बनाम-सावधानी वाले दौर।</div>
      <div class="scitem">आप अभी जीवन के किस अध्याय में हैं, और आगे क्या आता है।</div>
      <div class="scitem">पारंपरिक स्वास्थ्य प्रवृत्तियाँ, एक सामान्य पैटर्न के रूप में।</div>
    </div>
    <div class="sccard chg"><div class="sch">{icon('i-alert')} हम कभी क्या दावा नहीं करेंगे</div>
      <div class="scitem">विवाह, संतान या मृत्यु की सटीक तारीख़ें।</div>
      <div class="scitem">कोई भी चिकित्सीय, प्रजनन या गर्भावस्था संबंधी निदान।</div>
      <div class="scitem">निवेश की सलाह या निश्चित राशि।</div>
      <div class="scitem">गारंटीशुदा नतीजे, वीज़ा सलाह या परीक्षा के परिणाम।</div>
    </div>
  </div>
  <div class="note"><b>जन्म-समय मायने रखता है:</b> ग़लत समय आपके लग्न और उस पर बने हर भाव को बदल देता है। स्विस इफ़ेमेरिस &middot; लाहिड़ी अयनांश।</div>
</div>"""

    # ---- Glossary ----
    terms_hi = [
        ("लग्न (उदय राशि)", "वह राशि जो आपके जन्म के ठीक समय और जगह पर आकाश में उदय हो रही थी। आपकी कुंडली के हर भाव का शुरुआती बिंदु।"),
        ("भाव", "जीवन के बारह क्षेत्रों में से एक, आपके लग्न से गिना जाता है। दसवां करियर है, सातवां साझेदारी है, और इसी तरह आगे।"),
        ("भाव-स्वामी", "एक भाव का मालिक ग्रह &mdash; यह तय करने में सबसे बड़ा कारक कि वह भाव आम तौर पर कैसा नतीजा देता है।"),
        ("शक्ति (dignity)", "एक ग्रह जिस राशि में बैठा है, वहाँ वह कितना सहज है। उच्च और स्वराशि मज़बूत मानी जाती हैं; नीच कमज़ोर।"),
        ("महादशा", "एक ग्रह के नेतृत्व वाला जीवन का मुख्य अध्याय, जो 6 से 20 साल तक चलता है।"),
        ("अंतर्दशा", "एक महादशा के भीतर एक उप-अध्याय, जिसका नेतृत्व एक दूसरा ग्रह करता है।"),
        ("नक्षत्र", "आकाश के 27 तारा-आधारित विभाजनों में से एक। आपकी चंद्र राशि में एक बारीक, और ज़्यादा निजी परत जोड़ता है।"),
    ]
    terms_html = "".join(f'<div class="gitem"><dt>{t}</dt><dd>{d}</dd></div>' for t, d in terms_hi)
    glossary = f"""<div class="blockhead">
  <div class="area-open">
  <div class="eyebrow">भाग 2 &middot; सीधी भाषा में</div>
  <h2 class="head">एक छोटी शब्दावली</h2>
  <div class="rule"></div>
  <div style="margin-top:14px">{terms_html}</div>
  </div>
</div>"""

    # ---- Closing ----
    closing = f"""<div class="blockhead">
  <div class="eyebrow">आभार सहित</div>
  <h2 class="head">धन्यवाद, {name}</h2>
  <div class="rule"></div>
  <div class="lead" style="font-size:16px">अपने सवालों के लिए AxtroShastra पर भरोसा करने के लिए धन्यवाद। उम्मीद है इस रीडिंग ने आपको आगे की राह को लेकर थोड़ी स्पष्टता &mdash; और थोड़ा सुकून &mdash; दिया होगा।</div>
  <div class="pts">
    <div class="pt"><svg class="ic pi"><use href="#i-people"/></svg><div class="tx"><b>अनुकूलता</b>क्या दो कुंडलियाँ सच में एक-दूसरे के साथ चलती हैं।</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-clock"/></svg><div class="tx"><b>नौकरी बदलना</b>बदलाव का सही समय, और आगे कहाँ जाना है।</div></div>
    <div class="pt"><svg class="ic pi"><use href="#i-store"/></svg><div class="tx"><b>व्यापार</b>कब आगे बढ़ें, और कब रुकें।</div></div>
  </div>
  <div class="cov-trust">www.axtroshastra.com &middot; स्विस इफ़ेमेरिस &middot; लाहिड़ी अयनांश</div>
</div>"""

    parts = [cover, note, toc, glance, about, area_pages, timing_page, divider,
             kundli, lagna_moon, planet_table, loudest, houses1, houses2, connections,
             dashas_explained, dasha_timeline, chapters_ahead, transits, sade_page, how_set,
             worked_example, mapped_table, what_report, glossary, closing]

    return f"""<!DOCTYPE html><html lang="hi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} &mdash; जीवन ब्लूप्रिंट | AxtroShastra</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Mukta:wght@400;500;600;700;800&family=Noto+Serif+Devanagari:wght@500;600;700&family=Noto+Sans+Devanagari:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
{_VYAPAR_CSS}
{BLUEPRINT_HI_CSS}
</style></head><body>
{_VYAPAR_DEFS}
{"".join(parts)}
<style>
#ax-stickybar{{position:fixed;left:0;right:0;bottom:0;z-index:9997;
background:linear-gradient(180deg,rgba(250,245,237,0),var(--cream) 22%);
padding:14px 16px calc(14px + env(safe-area-inset-bottom))}}
#ax-stickybar .inner{{max-width:430px;margin:0 auto;display:flex;gap:10px}}
#ax-stickybar a{{flex:1;display:flex;align-items:center;justify-content:center;gap:8px;
min-height:52px;text-align:center;text-decoration:none;border-radius:12px;padding:12px 10px;
font:700 15px/1.15 var(--sans);-webkit-tap-highlight-color:transparent}}
#ax-stickybar a:active{{transform:scale(.97);filter:brightness(1.08)}}
#ax-stickybar svg{{width:19px;height:19px;flex:none}}
#ax-stickybar .pdf{{background:var(--ink);color:#F5EEE0;box-shadow:0 6px 16px rgba(42,35,56,.28)}}
#ax-stickybar .pdf svg{{color:var(--gold2)}}
#ax-stickybar .wa{{background:var(--green);color:#fff;box-shadow:0 6px 16px rgba(62,125,90,.28)}}
@media print{{#ax-stickybar{{display:none!important}}}}</style>
<div id='ax-stickybar'><div class='inner'>
<a class='pdf' id='ax-pdf' href='#' onclick='window.print();return false;'><svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round' aria-hidden='true'><path d='M12 3v12'/><path d='M6 11l6 6 6-6'/><path d='M4 21h16'/></svg>PDF डाउनलोड करें</a>
<a class='wa' href='#' onclick='axShare();return false;'><svg viewBox='0 0 24 24' fill='currentColor' aria-hidden='true'><path d='M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 2a8 8 0 1 1-4.1 14.9l-.5-.3-2.6.7.7-2.5-.3-.5A8 8 0 0 1 12 4zm-3.1 4.3c-.2 0-.5.1-.7.3-.7.7-1 1.6-.8 2.6.3 1.2 1 2.4 2.1 3.5 1.4 1.4 3 2.3 4.6 2.5.8.1 1.6-.2 2.2-.8.2-.2.3-.5.3-.8l-.1-.7c-.1-.2-.2-.4-.5-.5l-1.7-.8a.8.8 0 0 0-.9.2l-.5.5c-.1.2-.4.2-.6.1a6.7 6.7 0 0 1-2.9-2.9c-.1-.2 0-.4.1-.6l.5-.5c.2-.2.3-.6.2-.9l-.8-1.7c-.1-.2-.3-.4-.5-.4l-.5-.1z'/></svg>WhatsApp पर शेयर करें</a>
</div></div>
<script>
window.axShare=function(){{var url=location.href;var t='मेरी जीवन ब्लूप्रिंट रिपोर्ट देखें, AxtroShastra से';if(navigator.share){{navigator.share({{title:'AxtroShastra',text:t,url:url}}).catch(function(){{}});}}else{{window.open('https://wa.me/?text='+encodeURIComponent(t+' '+url),'_blank');}}}};
</script>
</body></html>"""
