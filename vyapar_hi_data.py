# -*- coding: utf-8 -*-
"""
vyapar_hi_data.py — Devanagari translations of the FIXED template strings emitted
by report_view.render_vyapar (the /vyapar business-growth report).

Scope, deliberately lean (mirrors milan_hi_data's shape):
  * Every STATIC visible run authored literally inside render_vyapar — page
    headings, eyebrows, verdict capsules, point labels, CTAs, notes, disclaimers,
    the thank-you page, the footer and the sticky bar.
  * The render-module label constants (VY_HOUSE_ROLE / VY_HOUSE_TITLE / VY_WIN)
    and the small, label-like status vocab (dignity flags, tone labels, the
    solo/wealth verdict words, the business-period themes BIZ_DASHA).

NOT here (handled elsewhere / degrades gracefully to English, exactly as in
milan_hi): the chart-VARIABLE interpretive prose from products.py / jyotish_maps
(temperament / sector / partnership / obstacle / remedy / wealth-pattern bodies).
That is the narrative layer's job — narrative.py renders it in Devanagari at
runtime — and any string not found here is simply left untouched.

Proper-noun tokens (the 12 signs, 9 planets) are REUSED from milan_hi.TOK, not
re-authored here.

Machine-authored first pass — QUEUED FOR NATIVE-HINDI REVIEW.
"""

HI_DATA = {
    # ================= 01 COVER =================
    "AxtroShastra · Vyapar — Business Growth": "AxtroShastra · व्यापार — कारोबार में तरक़्क़ी",
    "The problem was never your effort. It was the timing — and timing changes.":
        "दिक़्क़त कभी आपकी मेहनत में नहीं थी। दिक़्क़त समय में थी — और समय बदलता है।",

    # ================= 02 A NOTE FOR YOU =================
    "A note for you": "आपके लिए एक बात",
    "Before you read on": "आगे पढ़ने से पहले",
    "— Your astrologer, AxtroShastra": "— आपका ज्योतिषी, AxtroShastra",

    # ================= 03 SUMMARY =================
    "In one look": "एक नज़र में",
    "Your business, in one look": "आपका कारोबार, एक नज़र में",
    "Every line above is explained in the pages that follow, with the reason from your chart. This is a phase with an end date — not a verdict on you.":
        "ऊपर की हर बात आगे के पन्नों में समझाई गई है, आपकी कुंडली से मिली वजह के साथ। यह एक दौर है जिसकी ख़त्म होने की तारीख़ तय है — आप पर कोई फ़ैसला नहीं।",
    # summary capsule labels
    "Your type": "आपका अंदाज़",
    "Best-fit line": "सबसे सही काम",
    "Solo or partner": "अकेले या साझेदारी",
    "Last 3 years": "पिछले 3 साल",
    "Right now": "अभी",
    "When it turns": "कब बदलेगा",
    "Money": "पैसा",
    "Be careful": "सावधानी",
    # summary capsule VALUE words (short, label-like)
    "Mixed": "मिला-जुला",
    "Supportive": "अनुकूल",
    "Hard": "कठिन",
    "Built to go solo": "अकेले चलने के लिए बने",
    "Better with a partner": "साझेदार के साथ बेहतर",
    "Solo by nature, open to the right partner": "स्वभाव से अकेले, पर सही साझेदार के लिए तैयार",
    "Wealth yoga present": "धन योग मौजूद",
    "Effort-built wealth": "मेहनत से बना धन",

    # ================= 04 HOW YOU WORK =================
    "Your business nature": "आपका कारोबारी स्वभाव",
    "How you work": "आप कैसे काम करते हैं",
    "How you naturally work — your strength is trust, and your growth is deciding a little faster.":
        "आप स्वाभाविक रूप से कैसे काम करते हैं — आपकी ताक़त है भरोसा, और आपका सुधार है थोड़ा जल्दी फ़ैसला लेना।",
    "In business you lead through people and relationships. Here is how your birth chart shapes the way you naturally work — and the one habit that will change the most.":
        "कारोबार में आप लोगों और रिश्तों के ज़रिए आगे बढ़ते हैं। यहाँ बताया गया है कि आपकी जन्म कुंडली आपके काम करने के तरीक़े को कैसे गढ़ती है — और वह एक आदत जो सबसे ज़्यादा बदलेगी।",
    "Your weak spot": "आपकी कमज़ोरी",
    "Knowing this pattern is half of managing it.": "इस पैटर्न को पहचान लेना ही इसे सँभालने का आधा काम है।",
    "See your chart →": "अपनी कुंडली देखें →",

    # ================= 05 INSTINCT & PRESSURE =================
    "Your instinct & how you take pressure": "आपकी सहज-समझ और आप दबाव कैसे झेलते हैं",
    "How you handle hard times — you stay steady, and the heavy phase now will pass.":
        "आप कठिन समय को कैसे सँभालते हैं — आप स्थिर रहते हैं, और अभी का भारी दौर गुज़र जाएगा।",
    "Two things decide whether a business owner survives the hard years: patience, and how they carry pressure.":
        "एक कारोबारी कठिन साल पार कर पाएगा या नहीं, यह दो बातें तय करती हैं: धीरज, और वह दबाव को कैसे झेलता है।",
    "A patient builder": "धीरज से बनाने वाला",
    "You do your best work building something solid over time, not chasing quick, flashy wins. Your strength shows up in the long run — just don't let caution tip over into never moving at all.":
        "आप अपना सबसे अच्छा काम समय के साथ कुछ ठोस बनाकर करते हैं, न कि जल्दी और दिखावटी जीत के पीछे भागकर। आपकी ताक़त लंबे समय में दिखती है — बस सावधानी को इतना हावी न होने दें कि आप कभी आगे ही न बढ़ें।",
    "How your mind reads money": "आपका मन पैसे को कैसे पढ़ता है",
    "The weight now is real": "अभी का बोझ असली है",
    "Saturn is not in its heaviest phase for you right now — the usual discipline on cash and commitments is enough.":
        "शनि अभी आपके लिए अपने सबसे भारी दौर में नहीं है — पैसे और वादों पर हमेशा वाला अनुशासन ही काफ़ी है।",
    "Note:": "ध्यान दें:",
    "your birth time is approximate, so this reading uses the Moon chart (the classical Chandra Lagna method) for personality.":
        "आपका जन्म समय अनुमानित है, इसलिए यह पाठ स्वभाव के लिए चंद्र कुंडली (शास्त्रीय चंद्र लग्न विधि) का इस्तेमाल करता है।",

    # ================= 06 THE WORK THAT FITS =================
    "What business suits you": "कौन-सा कारोबार आपके लायक़ है",
    "The work that fits you": "आपके लायक़ काम",
    # BIZ_SECTOR_10L labels (short line-of-work headlines; reused across pages)
    "Leadership, Brand or Public-facing work": "नेतृत्व, ब्रांड या जन-सामने का काम",
    "Public, Food or Care businesses": "जन-सेवा, खाना या देखभाल का कारोबार",
    "Technical, Property or Competitive trades": "तकनीकी, संपत्ति या मुक़ाबले वाले काम",
    "Trade, Communication or Advisory": "व्यापार, संचार या सलाह",
    "Advisory, Education or Finance": "सलाह, शिक्षा या वित्त",
    "Creative, Luxury or Lifestyle trade": "रचनात्मक, विलासिता या लाइफ़स्टाइल का कारोबार",
    "Manufacturing, Infrastructure or Long-cycle trade": "निर्माण, बुनियादी ढाँचा या लंबी-अवधि का कारोबार",
    "What to avoid": "किससे बचें",

    # ================= 07 PARTNERSHIP =================
    "Should you go alone?": "क्या आपको अकेले चलना चाहिए?",
    "The blessing": "फ़ायदा",
    "But choose carefully": "पर सोच-समझकर चुनें",
    "Who to pick": "किसे चुनें",
    "Always put the deal in writing, and keep money transparent from day one.":
        "सौदा हमेशा लिखित में करें, और पहले दिन से पैसे का हिसाब साफ़ रखें।",
    "See the houses →": "भाव देखें →",

    # ================= 08 / 09 LAST 3 YEARS =================
    "The last three years": "पिछले तीन साल",
    "Why it felt so hard": "यह इतना कठिन क्यों लगा",
    "Why the last three years were the way they were — the cycle, not your effort.":
        "पिछले तीन साल जैसे रहे, वैसे क्यों रहे — यह चक्र था, आपकी मेहनत नहीं।",
    "See the timeline →": "समय-रेखा देखें →",
    "The pattern — and what it means": "पैटर्न — और इसका मतलब",
    "The whole stretch, in one line": "पूरा दौर, एक पंक्ति में",
    "It is lifting now": "अब यह हल्का हो रहा है",
    "Why this matters": "यह क्यों मायने रखता है",
    "The same chart that explained the hard years also holds the good ones. What you're feeling is the turning point of a cycle, not the shape of your whole business life.":
        "जिस कुंडली ने कठिन सालों की वजह बताई, उसी में अच्छे साल भी हैं। आप जो महसूस कर रहे हैं वह एक चक्र का मोड़ है, आपके पूरे कारोबारी जीवन की तस्वीर नहीं।",

    # ================= 10 / 11 STRONG WINDOW =================
    "When the road opens": "जब रास्ता खुलता है",
    "Your strongest window": "आपका सबसे मज़बूत दौर",
    "STRONG": "मज़बूत",
    "What to do": "क्या करें",
    "What not to do": "क्या न करें",
    "How this was scored →": "यह कैसे आँका गया →",
    "The years after": "उसके बाद के साल",
    "Beyond the strongest window, the upcoming periods keep giving in gentler waves. Here is what follows.":
        "सबसे मज़बूत दौर के बाद भी आने वाली दशाएँ हल्की लहरों में देती रहती हैं। आगे यह है।",
    "Windows raise your odds — they don't remove the effort. Even a strong window still rewards the work you put in.":
        "अच्छे दौर आपकी संभावना बढ़ाते हैं — मेहनत नहीं हटाते। मज़बूत दौर में भी आपकी लगाई मेहनत ही रंग लाती है।",
    # STRONG_WINDOW_DO / DONT (fixed action lines)
    "Launch, expand or raise capital in this window — the wind is behind you.":
        "इस दौर में शुरुआत करें, फैलाएँ या पूँजी जुटाएँ — हवा आपके साथ है।",
    "Lock in your best clients and long contracts while trust is high.":
        "जब भरोसा ऊँचा है, अपने सबसे अच्छे ग्राहक और लंबे अनुबंध पक्के कर लें।",
    "Reinvest early gains into the business rather than spending them.":
        "शुरुआती मुनाफ़े को ख़र्च करने के बजाय कारोबार में दोबारा लगाएँ।",
    "Don't sit idle waiting for perfect — this window rewards decisive action.":
        "सब कुछ सही होने का इंतज़ार करते हुए ख़ाली न बैठें — यह दौर पक्के फ़ैसले को फल देता है।",
    "Don't over-leverage on the optimism; always keep a working reserve.":
        "उम्मीद में हद से ज़्यादा क़र्ज़ न लें; हमेशा काम-चलाऊ भंडार रखें।",

    # ================= 12 RISK =================
    "Careful stretches": "सावधानी वाले दौर",
    "When to hold back": "कब रुकना है",
    "When to play it safe — keep cash in hand and avoid big risks in the careful stretches below.":
        "कब बचकर चलना है — नीचे दिए सावधानी वाले दौरों में पैसा हाथ में रखें और बड़े जोखिम से बचें।",
    "A caution window doesn't mean everything goes wrong — it means being careful here is the smart play. The owner who knows cash will be tight simply plans for it in advance.":
        "सावधानी का दौर मतलब यह नहीं कि सब कुछ ग़लत होगा — मतलब यह है कि यहाँ सँभलकर चलना ही समझदारी है। जो कारोबारी जानता है कि पैसा तंग रहेगा, वह पहले से उसकी योजना बना लेता है।",
    "The point of this page": "इस पन्ने का मक़सद",
    "Forewarned is forearmed. Knowing these dates in advance turns them from nasty surprises into simple, manageable planning.":
        "पहले से चेत जाना ही बचाव है। इन तारीख़ों को पहले से जान लेना उन्हें बुरे झटकों के बजाय आसान, सँभालने लायक़ योजना बना देता है।",
    "See why →": "वजह देखें →",

    # ================= 13 / 14 MONEY =================
    "Money & cash flow": "पैसा और नक़दी",
    "How money moves for you": "आपके लिए पैसा कैसे चलता है",
    "How money comes and goes — the earning, the growing, and where it leaks.":
        "पैसा कैसे आता और जाता है — कमाई, बढ़त, और कहाँ रिसता है।",
    "The money houses in your chart tell the story of how wealth comes in, how it grows, and where it goes.":
        "आपकी कुंडली के धन-भाव यह कहानी कहते हैं कि धन कैसे आता है, कैसे बढ़ता है, और कहाँ जाता है।",
    "How you earn": "आप कैसे कमाते हैं",
    "How gains arrive": "मुनाफ़ा कैसे आता है",
    "Keep a reserve": "भंडार रखें",
    "See the wealth check →": "धन-जाँच देखें →",
    "Your wealth potential": "आपकी धन-संभावना",
    "You have a wealth combination": "आपके पास एक धन योग है",
    "Wealth built by effort": "मेहनत से बना धन",
    "How your wealth actually grows": "आपका धन असल में कैसे बढ़ता है",
    "so holding on is the real work — and": "इसलिए इसे थामे रखना ही असली काम है — और",
    "Best money years from your strong window": "आपके मज़बूत दौर के सबसे अच्छे कमाई-वर्ष",

    # ================= 15 OBSTRUCTION =================
    "What's holding you": "आपको क्या रोक रहा है",
    "The blocks, honestly": "रुकावटें, ईमानदारी से",
    "The current testing phase": "अभी का परखने वाला दौर",
    "The current sub-period asks for patience more than expansion. It passes — and the roadmap ahead shows exactly when.":
        "अभी की उप-दशा फैलाव से ज़्यादा धीरज माँगती है। यह गुज़र जाती है — और आगे का नक़्शा ठीक-ठीक बताता है कि कब।",
    "The shadow planets": "छाया ग्रह",
    "None of it is permanent": "इनमें से कुछ भी स्थायी नहीं है",
    "Both blocks are passing cycles, not the shape of your chart. Naming them is the first step to managing them.":
        "दोनों रुकावटें गुज़रने वाले चक्र हैं, आपकी कुंडली की बनावट नहीं। इन्हें पहचानना ही इन्हें सँभालने का पहला क़दम है।",
    "See the detail →": "ब्योरा देखें →",

    # ================= 16 REMEDIES =================
    "Remedies & your plan": "उपाय और आपकी योजना",
    "What to actually do": "असल में क्या करें",
    "Simple, classical remedies": "आसान, शास्त्रीय उपाय",
    "Simple, classical support — offered to steady you, never to frighten you. No remedy replaces the plan below.":
        "आसान, शास्त्रीय सहारा — आपको स्थिर करने के लिए, डराने के लिए कभी नहीं। कोई उपाय नीचे दी योजना की जगह नहीं ले सकता।",

    # ================= 17 KUNDLI =================
    "Your chart · the proof": "आपकी कुंडली · प्रमाण",
    "Your kundli": "आपकी कुंडली",
    "Vyapar Kundli": "व्यापार कुंडली",
    "Your birth chart, South-Indian style · Ascendant marked in gold. Every reading in this report is calculated from this chart — nothing is guessed, and any astrologer can verify it.":
        "आपकी जन्म कुंडली, दक्षिण-भारतीय शैली में · लग्न सुनहरे रंग में। इस रिपोर्ट का हर पाठ इसी कुंडली से गणना किया गया है — कुछ भी अंदाज़े से नहीं, और कोई भी ज्योतिषी इसे जाँच सकता है।",

    # ================= 18 PLANETS =================
    "Every planet, placed": "हर ग्रह, अपनी जगह",
    "Planet": "ग्रह",
    "Sign": "राशि",
    "House": "भाव",
    "What it means": "इसका मतलब",
    # VY_HOUSE_ROLE (planet-note roles)
    "self & trade sense": "ख़ुद और व्यापार-समझ",
    "savings & money": "बचत और पैसा",
    "drive & courage": "जोश और हिम्मत",
    "base & assets": "नींव और संपत्ति",
    "ideas & risk": "विचार और जोखिम",
    "effort & competition": "मेहनत और मुक़ाबला",
    "partners & deals": "साझेदार और सौदे",
    "upheaval & change": "उथल-पुथल और बदलाव",
    "fortune & mentors": "भाग्य और मार्गदर्शक",
    "work & status": "काम और रुतबा",
    "gains & income": "लाभ और आमदनी",
    "outflow & distance": "ख़र्च और दूरी",
    # dignity / status flags
    "own": "स्वगृही",
    "exalted": "उच्च",
    "debilitated": "नीच",
    "combust": "अस्त",
    "retro": "वक्री",
    "Sade Sati now": "अभी साढ़े साती",
    "A personable, trusted presence is a genuinely good start for any business.":
        "एक मिलनसार, भरोसेमंद मौजूदगी किसी भी कारोबार के लिए सचमुच अच्छी शुरुआत है।",
    "The most crowded corner of your chart, and the clearest driver of its theme.":
        "आपकी कुंडली का सबसे भरा हुआ कोना, और इसके मिज़ाज का सबसे साफ़ चालक।",

    # ================= 19 / 20 HOUSES =================
    "Your chart · business houses": "आपकी कुंडली · कारोबारी भाव",
    "The houses that matter": "वे भाव जो मायने रखते हैं",
    "A handful of houses run a business. Here are the ones your chart puts front and centre.":
        "मुट्ठी भर भाव ही कारोबार चलाते हैं। यहाँ वे हैं जिन्हें आपकी कुंडली सबसे आगे रखती है।",
    "Gains, strength & the loaded corner": "लाभ, ताक़त और भरा हुआ कोना",
    # VY_HOUSE_TITLE
    "Savings": "बचत",
    "Partners & trade": "साझेदार और व्यापार",
    "Work & status": "काम और रुतबा",
    "Gains & income": "लाभ और आमदनी",

    # ================= 21 / 22 TIMELINE =================
    "Your chart · timeline": "आपकी कुंडली · समय-रेखा",
    "Your timeline — the recent stretch": "आपकी समय-रेखा — हाल का दौर",
    "Your life runs in planetary periods, called dashas. These are the recent sub-periods — and they explain the stretch behind you.":
        "आपका जीवन ग्रहों की दशाओं में चलता है। ये हाल की उप-दशाएँ हैं — और ये पीछे के दौर को समझाती हैं।",
    "Now": "अभी",
    "current period": "मौजूदा दशा",
    "Your timeline — the years ahead": "आपकी समय-रेखा — आगे के साल",
    "And these are the periods that take over next — the shape of the road in front of you.":
        "और ये वे दशाएँ हैं जो आगे सँभालती हैं — आपके सामने के रास्ते की तस्वीर।",

    # ================= 23 / 24 WINDOW SCORING =================
    "Your chart · window scoring": "आपकी कुंडली · दौर की परख",
    "Why \"Strong\" — shown": "\"मज़बूत\" क्यों — दिखाया गया",
    "The other windows": "बाक़ी दौर",
    "The careful stretch": "सावधानी वाला दौर",
    "Windows are chances, not fixed dates.": "दौर मौक़े हैं, तय तारीख़ें नहीं।",
    "They raise your odds; the effort is still yours to bring.":
        "ये आपकी संभावना बढ़ाते हैं; मेहनत फिर भी आपको ही लानी है।",
    "When a helpful planet leads the period, its theme turns straight into opportunity.":
        "जब कोई मददगार ग्रह दशा की अगुआई करता है, तो उसका मिज़ाज सीधे मौक़े में बदल जाता है।",
    "One of the strongest placements a driving planet can have — it means this window carries real weight, not just a hopeful label.":
        "किसी चालक ग्रह की सबसे मज़बूत स्थितियों में से एक — इसका मतलब यह दौर सचमुच वज़न रखता है, सिर्फ़ एक उम्मीद-भरा नाम नहीं।",
    "The pressure lifts alongside it": "दबाव इसके साथ ही हल्का होता है",

    # ================= 25 SADE SATI =================
    "Your chart · Sade Sati": "आपकी कुंडली · साढ़े साती",
    "Sade Sati, explained": "साढ़े साती, समझाई हुई",
    "What it is": "यह क्या है",
    "Sade Sati is not running on your Moon right now — Saturn's heaviest cycle is not the story of this phase for you.":
        "आपके चंद्रमा पर अभी साढ़े साती नहीं चल रही — शनि का सबसे भारी चक्र इस दौर की कहानी नहीं है।",
    "What you feel": "आप क्या महसूस करते हैं",
    "Delays, heavier decisions, and a steadier worry about money. It's real, and — importantly — it's temporary.":
        "देरी, भारी फ़ैसले, और पैसे की लगातार चिंता। यह असली है, और — ख़ास बात — यह अस्थायी है।",
    "The good news": "अच्छी ख़बर",

    # ================= 26 SHADOWS =================
    "Your chart · the shadow planets": "आपकी कुंडली · छाया ग्रह",
    "Rahu, Ketu & the shadows": "राहु, केतु और छायाएँ",
    "Adds worry, restlessness and over-thinking to the current stretch — the day-to-day strain you've been feeling.":
        "मौजूदा दौर में चिंता, बेचैनी और ज़्यादा सोचना जोड़ता है — वही रोज़मर्रा का तनाव जो आप महसूस कर रहे हैं।",
    "Pulls you toward letting-go — part of why focus and, at times, money slip away so easily right now.":
        "आपको छोड़ देने की ओर खींचता है — यही एक वजह है कि अभी ध्यान और, कभी-कभी, पैसा इतनी आसानी से फिसल जाता है।",

    # ================= 27 DHANA =================
    "Your chart · wealth": "आपकी कुंडली · धन",
    "Wealth combinations": "धन योग",
    "We checked your chart for the classical wealth combinations (Dhana Yogas). Here is what we found.":
        "हमने आपकी कुंडली में शास्त्रीय धन योगों की जाँच की। यह हमें मिला।",
    "You have a wealth yoga": "आपके पास एक धन योग है",
    "Wealth by deliberate effort": "सोच-समझकर की मेहनत से धन",
    "Where gains come from": "मुनाफ़ा कहाँ से आता है",
    "Hold the line on cash": "नक़दी पर पकड़ बनाए रखें",

    # ================= 28 YEAR BY YEAR =================
    "Your chart · year by year": "आपकी कुंडली · साल-दर-साल",
    "The next years": "आने वाले साल",
    "A quick year-by-year view, so you can hold the shape of what's coming.":
        "एक झटपट साल-दर-साल नज़र, ताकि आप आगे आने वाले की तस्वीर मन में रख सकें।",
    "Guidance, not a guarantee. Timing windows are chances, not fixed dates. This is not legal or financial advice.":
        "मार्गदर्शन, गारंटी नहीं। समय के दौर मौक़े हैं, तय तारीख़ें नहीं। यह क़ानूनी या वित्तीय सलाह नहीं है।",

    # ================= 29 ENDING =================
    "With gratitude": "आभार के साथ",
    "Thank you for trusting AxtroShastra with your business questions. We hope this reading brings you clarity — and a little calm — about the road ahead.":
        "अपने कारोबारी सवालों के लिए AxtroShastra पर भरोसा करने के लिए धन्यवाद। हमें उम्मीद है कि यह पाठ आपको आगे के रास्ते के बारे में साफ़ समझ — और थोड़ा सुकून — देगा।",
    "Have another question about your life? Each of these is on our site, computed the same honest way:":
        "अपने जीवन के बारे में कोई और सवाल है? इनमें से हर एक हमारी साइट पर है, उसी ईमानदार तरीक़े से गणना किया हुआ:",
    "Compatibility": "अनुकूलता",
    "Whether two charts truly work together.": "क्या दो कुंडलियाँ सचमुच साथ चलती हैं।",
    "Marriage Timing": "विवाह का समय",
    "When marriage is most likely, and with whom.": "विवाह कब सबसे संभावित है, और किसके साथ।",
    "Job Change": "नौकरी बदलना",
    "The right time to switch jobs — and where to go next.": "नौकरी बदलने का सही समय — और आगे कहाँ जाएँ।",
    "Vyapar — Business": "व्यापार — कारोबार",
    "This report: when to build, when to hold.": "यही रिपोर्ट: कब बनाएँ, कब रुकें।",
    "Every AxtroShastra report is computed from your real birth chart — never guessed. That is our promise.":
        "हर AxtroShastra रिपोर्ट आपकी असली जन्म कुंडली से गणना की जाती है — कभी अंदाज़े से नहीं। यही हमारा वादा है।",

    # ================= STICKY BAR =================
    "Download PDF": "PDF डाउनलोड करें",
    "Share on WhatsApp": "WhatsApp पर शेयर करें",

    # ================= BIZ_DASHA period themes (central to timelines/summary) =====
    "authority, visibility and standing in your own name — good for brand, slower for pure trade":
        "अधिकार, पहचान और अपने नाम की साख — ब्रांड के लिए अच्छा, सीधे व्यापार के लिए धीमा",
    "public connection and steady demand — a people-and-cashflow phase":
        "जनता से जुड़ाव और लगातार माँग — लोगों-और-नक़दी का दौर",
    "drive and competition run high, but haste and conflict can cost you":
        "जोश और मुक़ाबला ऊँचा रहता है, पर जल्दबाज़ी और टकराव भारी पड़ सकते हैं",
    "commerce, deals and communication — intellect turns straight into income":
        "व्यापार, सौदे और संचार — बुद्धि सीधे आमदनी में बदलती है",
    "expansion, trust and new markets — doors open through knowledge and reputation":
        "फैलाव, भरोसा और नए बाज़ार — ज्ञान और साख से दरवाज़े खुलते हैं",
    "comfort, creativity and wealth-enjoyment — earnings and lifestyle both rise":
        "आराम, रचनात्मकता और धन का सुख — कमाई और जीवनशैली दोनों बढ़ती हैं",
    "a slow, disciplined grind — durable if you endure, but gains come late and hard":
        "धीमी, अनुशासित मेहनत — टिकाऊ अगर आप सह लें, पर फ़ायदा देर से और मुश्किल से आता है",
    "ambitious, unconventional rise — fast growth, but restless and risk-prone":
        "महत्वाकांक्षी, लीक से हटकर उठान — तेज़ बढ़त, पर बेचैन और जोखिम-भरी",
    "detachment and endings — a phase to simplify and cut, not to expand":
        "अलगाव और अंत — सरल करने और काटने का दौर, फैलाने का नहीं",
}
