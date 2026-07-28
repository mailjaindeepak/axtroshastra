# -*- coding: utf-8 -*-
"""
milan_hi_data.py — Devanagari translations of the milan report's DATA-MAP and
milan_v2 constant prose (koota texts, element pairings, nakshatra love-lines,
remedies, action-plans, moon-lord descriptions, animal instincts, etc.).

Machine-authored first pass — QUEUED FOR NATIVE-HINDI REVIEW. Edit the Hindi
values here (or via the review workbook) and re-render to verify. milan_hi.py
merges HI_DATA into its HI dictionary.
"""

HI_DATA = {
    # ---- KOOTA "what it measures" short labels (KOOTA_UI / THEME_MEASURES) ----
    "how easily your minds click and how you talk things through":
        "आपके मन कितनी आसानी से मिलते हैं और आप बातें कैसे सुलझाते हैं",
    "how naturally you're drawn to and influence each other":
        "आप कितने स्वाभाविक रूप से एक-दूसरे की ओर खिंचते और प्रभाव डालते हैं",
    "whether being together tends to make life feel smoother for you both":
        "क्या साथ रहना आप दोनों के लिए ज़िंदगी को आसान बनाता है",
    "instinctive, physical and intimate compatibility":
        "सहज, शारीरिक और नज़दीकी अनुकूलता",
    "who naturally takes the lead — without it turning into a power struggle":
        "कौन स्वाभाविक रूप से आगे रहता है — बिना इसे रस्साकशी बने",
    "your everyday energy, social style and how your moods land":
        "आपकी रोज़मर्रा की ऊर्जा, सामाजिक अंदाज़ और मूड का असर",
    "long-term closeness and building a life and family together":
        "लंबा साथ और मिलकर एक जीवन व परिवार बनाना",
    "vitality and the classical health / progeny factor":
        "जीवनशक्ति और शास्त्रीय सेहत / संतान का पहलू",
    "long-term closeness and how good you are for each other.":
        "लंबा साथ और आप एक-दूसरे के लिए कितने अच्छे हैं।",

    # ---- THEME_MEASURES (long "what it measures" bodies) ----
    "How your minds click, how you talk things through, and who leads what — the stuff long conversations and long marriages are made of.":
        "आपके मन कैसे मिलते हैं, आप बातें कैसे सुलझाते हैं, और कौन क्या संभालता है — वो चीज़ें जिनसे लंबी बातचीत और लंबी शादियाँ बनती हैं।",
    "Your social batteries, humour, and how your moods land in a shared room — the stuff that decides whether living together feels light or like work.":
        "आपकी सामाजिक ऊर्जा, हास्य, और साझा कमरे में आपके मूड का असर — वो चीज़ें जो तय करती हैं कि साथ रहना हल्का लगे या मेहनत जैसा।",
    "Instinctive, physical compatibility — the pull, the closeness, the daily rhythm of how your bodies share space.":
        "सहज, शारीरिक अनुकूलता — खिंचाव, नज़दीकी, और आपके शरीर रोज़ किस लय में जगह साझा करते हैं।",
    "Long-term closeness, family life, and shared prosperity — the layer that turns a relationship into a home.":
        "लंबा साथ, पारिवारिक जीवन, और साझा समृद्धि — वह परत जो रिश्ते को घर बना देती है।",
    "The deepest, most durable layer of compatibility — long-term vitality, health, and (whenever, and if, you want it) family. It's the factor classical astrologers weigh the most.":
        "अनुकूलता की सबसे गहरी, सबसे टिकाऊ परत — दीर्घकालिक जीवनशक्ति, सेहत, और (जब और अगर आप चाहें) परिवार। यही वह पहलू है जिसे शास्त्रीय ज्योतिषी सबसे ज़्यादा तवज्जो देते हैं।",

    # ---- THEME_DEEP (per-theme deep paragraphs) ----
    "The spark is real and it's mutual — you're drawn to each other in a way that doesn't need forcing. That easy physical comfort is something a lot of couples spend years trying to build. Keep novelty alive and it stays a strength, not a given.":
        "चिंगारी असली है और दोतरफ़ा — आप एक-दूसरे की ओर यूँ खिंचते हैं जिसमें ज़ोर नहीं लगाना पड़ता। वो सहज शारीरिक सुकून, जिसे बहुत से जोड़े सालों में बना पाते हैं। नएपन को ज़िंदा रखें, तो यह ताक़त बनी रहती है, दी हुई चीज़ नहीं।",
    "On the heaviest traditional factor, you're clear — read as vitality and a healthy foundation for a life (and a family) together. It's the factor astrologers weigh the most, and it's working in your favour.":
        "सबसे भारी पारंपरिक पहलू पर आप साफ़ हैं — इसे जीवनशक्ति और साथ के जीवन (और परिवार) की स्वस्थ नींव के रूप में पढ़ा जाता है। यही वह पहलू है जिसे ज्योतिषी सबसे ज़्यादा तवज्जो देते हैं, और यह आपके पक्ष में है।",
    "Your day-to-day energies just fit — similar social batteries, similar humour, a similar way of handling good days and bad ones. This is the quiet superpower that makes living together feel light instead of like work.":
        "आपकी रोज़मर्रा की ऊर्जाएँ बस मिल जाती हैं — मिलती-जुलती सामाजिक ऊर्जा, मिलता-जुलता हास्य, अच्छे और बुरे दिनों को संभालने का मिलता-जुलता तरीक़ा। यही वह ख़ामोश सुपरपावर है जो साथ रहना मेहनत नहीं, हल्का बना देती है।",
    "You think in the same language. Even your disagreements will make sense to each other, because your values and mental wiring line up. This is the stuff long conversations — and long marriages — are made of.":
        "आप एक ही भाषा में सोचते हैं। आपकी असहमतियाँ भी एक-दूसरे को समझ आएँगी, क्योंकि आपके मूल्य और सोच की बनावट मेल खाती है। यही वो चीज़ है जिनसे लंबी बातचीत — और लंबी शादियाँ — बनती हैं।",
    "Emotionally, you're built to go the distance. Classical texts read this as a green signal for closeness, family and growing together — the deep, settle-in kind of bond rather than just a spark.":
        "भावनात्मक रूप से, आप लंबा साथ निभाने के लिए बने हैं। शास्त्र इसे नज़दीकी, परिवार और साथ बढ़ने का हरा संकेत मानते हैं — केवल एक चिंगारी नहीं, बल्कि गहरा, ठहरने वाला बंधन।",

    # ---- yoni pair descriptors ----
    "a neutral pair": "एक तटस्थ जोड़ी",
    "a perfect match": "एक बेहतरीन मेल",
    "natural allies": "स्वाभाविक साथी",
    "natural opposites": "स्वाभाविक विपरीत",
    "different instincts": "अलग सहज-प्रवृत्तियाँ",

    # ---- moon-lord "mind" descriptors (the X mind) ----
    "the Sun mind": "सूर्य मन", "the Moon mind": "चंद्र मन", "the Mars mind": "मंगल मन",
    "the Mercury mind": "बुध मन", "the Jupiter mind": "गुरु मन", "the Venus mind": "शुक्र मन",
    "the Saturn mind": "शनि मन", "the Rahu mind": "राहु मन", "the Ketu mind": "केतु मन",

    # ---- LORD_BODY (moon ruled by X — full descriptions) ----
    "Your Moon is ruled by the Sun — the planet of identity and authority. You process through self-expression, lead naturally, and love with generosity.":
        "आपका चंद्रमा सूर्य के अधीन है — पहचान और अधिकार का ग्रह। आप आत्म-अभिव्यक्ति से सोचते हैं, स्वाभाविक रूप से नेतृत्व करते हैं, और उदारता से प्रेम करते हैं।",
    "Your Moon is self-ruled — intuitive, receptive, emotionally attuned. You process through feeling, lead with empathy, and love by nurturing.":
        "आपका चंद्रमा स्वयं-स्वामी है — सहज, ग्रहणशील, भावनात्मक रूप से जुड़ा। आप भावना से सोचते हैं, सहानुभूति से नेतृत्व करते हैं, और पोषण से प्रेम करते हैं।",
    "Your Moon is ruled by Mars — the planet of action and drive. You process by doing, lead with courage, and love fiercely and protectively.":
        "आपका चंद्रमा मंगल के अधीन है — कर्म और जोश का ग्रह। आप करके सोचते हैं, साहस से नेतृत्व करते हैं, और तीव्रता व सुरक्षा-भाव से प्रेम करते हैं।",
    "Your Moon is ruled by Mercury — the planet of the fast, logical, talk-it-out mind. You process by speaking, want the why and the what-next, and move on quickly.":
        "आपका चंद्रमा बुध के अधीन है — तेज़, तार्किक, बात-से-सुलझाने वाले मन का ग्रह। आप बोलकर सोचते हैं, ‘क्यों’ और ‘आगे क्या’ चाहते हैं, और जल्दी आगे बढ़ जाते हैं।",
    "Your Moon is ruled by Jupiter — the planet of meaning, faith and feeling. You process inwardly, lead with the heart, and go deep before you speak.":
        "आपका चंद्रमा गुरु के अधीन है — अर्थ, आस्था और भावना का ग्रह। आप भीतर ही सोचते हैं, दिल से नेतृत्व करते हैं, और बोलने से पहले गहराई में जाते हैं।",
    "Your Moon is ruled by Venus — the planet of harmony, beauty and connection. You lead with warmth, seek balance, and love through care and closeness.":
        "आपका चंद्रमा शुक्र के अधीन है — सामंजस्य, सौंदर्य और जुड़ाव का ग्रह। आप गर्मजोशी से नेतृत्व करते हैं, संतुलन चाहते हैं, और देखभाल व नज़दीकी से प्रेम करते हैं।",
    "Your Moon is ruled by Saturn — the planet of structure and endurance. You process slowly and deeply, lead with patience, and love through commitment and consistency.":
        "आपका चंद्रमा शनि के अधीन है — संरचना और सहनशीलता का ग्रह। आप धीरे और गहराई से सोचते हैं, धीरज से नेतृत्व करते हैं, और प्रतिबद्धता व निरंतरता से प्रेम करते हैं।",
    "Your Moon is ruled by Rahu — intense, unconventional, always pushing boundaries. You process through transformation, and love with an all-or-nothing depth.":
        "आपका चंद्रमा राहु के अधीन है — तीव्र, अपरंपरागत, हमेशा सीमाएँ लाँघने वाला। आप रूपांतरण से सोचते हैं, और सब-कुछ-या-कुछ-नहीं वाली गहराई से प्रेम करते हैं।",
    "Your Moon is ruled by Ketu — detached yet deeply spiritual. You process through intuition, and love with a quiet, old-soul wisdom.":
        "आपका चंद्रमा केतु के अधीन है — निर्लिप्त फिर भी गहरे आध्यात्मिक। आप अंतर्ज्ञान से सोचते हैं, और एक शांत, पुरानी-आत्मा वाली समझ से प्रेम करते हैं।",

    # ---- LORD_ELEM_CLS / element-line descriptor adjectives ----
    "authoritative, proud, leading": "प्रभावशाली, स्वाभिमानी, अगुआई करने वाला",
    "nurturing, intuitive, receptive": "पोषक, सहज, ग्रहणशील",
    "action-first, direct, brave": "कर्म-पहले, सीधा, बहादुर",
    "quick, curious, verbal": "तेज़, जिज्ञासु, वाचाल",
    "deep, feeling, meaning-led": "गहरा, भावुक, अर्थ-प्रेरित",
    "harmonious, aesthetic, connecting": "सामंजस्यपूर्ण, सौंदर्यप्रिय, जोड़ने वाला",
    "structured, patient, enduring": "व्यवस्थित, धैर्यवान, सहनशील",
    "intense, unconventional, boundary-pushing": "तीव्र, अपरंपरागत, सीमाएँ लाँघने वाला",
    "detached, spiritual, old-soul": "निर्लिप्त, आध्यात्मिक, पुरानी-आत्मा",

    # ---- ANIMAL_ADJ (yoni animal instincts) ----
    "free, spirited, independent": "स्वच्छंद, जोशीला, स्वतंत्र",
    "steady, loyal, protective": "स्थिर, वफ़ादार, रक्षक",
    "gentle, nurturing, patient": "कोमल, पोषक, धैर्यवान",
    "magnetic, subtle, intense": "चुंबकीय, सूक्ष्म, तीव्र",
    "devoted, alert, protective": "समर्पित, सतर्क, रक्षक",
    "independent, graceful, selective": "स्वतंत्र, शालीन, चुनिंदा",
    "clever, resourceful, quick": "चतुर, जुगाड़ू, फुर्तीला",
    "nurturing, patient, grounded": "पोषक, धैर्यवान, ज़मीनी",
    "strong, persistent, dependable": "मज़बूत, दृढ़, भरोसेमंद",
    "fierce, passionate, dominant": "प्रचंड, जोशीला, प्रभावशाली",
    "gentle, sensitive, alert": "कोमल, संवेदनशील, सतर्क",
    "warm, proud, wholehearted": "गर्मजोश, स्वाभिमानी, पूरे दिल से",
    "playful, clever, energetic": "खिलंदड़ा, चतुर, ऊर्जावान",
    "quick, sharp, fearless": "फुर्तीला, तेज़, निडर",

    # ---- GANA_ADJ ----
    "idealist": "आदर्शवादी",
    "grounded, practical": "ज़मीनी, व्यावहारिक",
    "intense, driven": "तीव्र, लक्ष्य-प्रेरित",

    # ---- ELEMENT_HI standalone labels ----
    "Agni (fire)": "अग्नि", "Prithvi (earth)": "पृथ्वी", "Vayu (air)": "वायु", "Jal (water)": "जल",

    # ---- KOOTA_UI theme names / weak-area labels ----
    "Mental Wavelength": "मानसिक तरंग",
    "Drive & Ego Balance": "जोश और अहं का संतुलन",
    "Vibe & Temperament": "अंदाज़ और स्वभाव",
    "Emotional Bond": "भावनात्मक बंधन",
    "Health & Family": "सेहत और परिवार",

    # ---- nakshatra love-lines (NAK_PROFILE) ----
    "In love you move quickly and openly; you need a partner who can keep pace, not one who tests patience":
        "प्रेम में आप तेज़ी और खुलेपन से बढ़ते हैं; आपको ऐसा साथी चाहिए जो साथ चल सके, न कि धीरज आज़माए",
    "Love for you is passionate and turbulent; the right partner is a steady anchor, not another storm":
        "आपके लिए प्रेम जोशीला और उथल-पुथल भरा है; सही साथी एक स्थिर सहारा है, कोई और तूफ़ान नहीं",
    "You love with dignity and expect respect; public loyalty from a partner matters as much as private love":
        "आप गरिमा से प्रेम करते हैं और सम्मान की अपेक्षा रखते हैं; साथी की सार्वजनिक निष्ठा निजी प्रेम जितनी ही मायने रखती है",
    "You are romantic and devoted; stability and sensory comfort are your love languages":
        "आप रोमांटिक और समर्पित हैं; स्थिरता और इंद्रिय-सुख आपकी प्रेम-भाषाएँ हैं",
    "You need mental chase and novelty in love; boredom, not conflict, is your relationship risk":
        "प्रेम में आपको मानसिक पीछा और नयापन चाहिए; ऊब, न कि टकराव, आपके रिश्ते का ख़तरा है",
    "You protect the ones you love fiercely; softness is there, under the armour":
        "आप अपने प्रियजनों की प्रचंड रक्षा करते हैं; कोमलता है, बस कवच के नीचे",
    "You need a partner in rhythm with your ambitions; you give abundantly when met halfway":
        "आपको ऐसा साथी चाहिए जो आपकी महत्वाकांक्षाओं की लय में हो; आधा रास्ता तय हो तो आप भरपूर देते हैं",
    "You express love through care and service; you flourish with a partner who reciprocates, not just receives":
        "आप देखभाल और सेवा से प्रेम जताते हैं; ऐसे साथी के साथ खिलते हैं जो लौटाए भी, केवल ले न",
    "You guard your heart; intimacy comes in layers, and betrayal is the one unforgivable":
        "आप अपना दिल सँभालकर रखते हैं; नज़दीकी परतों में आती है, और विश्वासघात इकलौती अक्षम्य बात है",
    "Romance, celebration and affection are essentials for you, not luxuries":
        "रोमांस, उत्सव और स्नेह आपके लिए ज़रूरतें हैं, विलासिता नहीं",
    "You love wholeheartedly and expect faith in your comeback; doubt from a partner wounds most":
        "आप पूरे दिल से प्रेम करते हैं और अपनी वापसी में भरोसे की उम्मीद रखते हैं; साथी का शक सबसे ज़्यादा चुभता है",
    "You show love through practical help and humour; you need appreciation, not grand drama":
        "आप व्यावहारिक मदद और हास्य से प्रेम जताते हैं; आपको सराहना चाहिए, बड़ा नाटक नहीं",
    "You fall for minds; conversation is your intimacy, silence together your comfort":
        "आप मन पर मोहित होते हैं; बातचीत आपकी नज़दीकी है, साथ की ख़ामोशी आपका सुकून",
    "You need space inside love; the right partner holds you loosely and gains all of you":
        "प्रेम के भीतर आपको जगह चाहिए; सही साथी आपको ढीला थामता है और आपका पूरा पा लेता है",
    "You take commitment seriously and expect the same; casual love does not satisfy you":
        "आप प्रतिबद्धता को गंभीरता से लेते हैं और वैसी ही अपेक्षा रखते हैं; हल्का-फुल्का प्रेम आपको संतुष्ट नहीं करता",
    "You test partners early; behind the sharpness is fierce loyalty to the one who passes":
        "आप साथी को शुरू में ही परखते हैं; तीखेपन के पीछे उसके लिए प्रचंड निष्ठा है जो खरा उतरे",
    "You love with purpose; partnership works when you are building something together":
        "आप उद्देश्य के साथ प्रेम करते हैं; साझेदारी तब चलती है जब आप साथ मिलकर कुछ बना रहे हों",
    "In love you go to the root of everything; partners must survive your honesty to earn your depth":
        "प्रेम में आप हर चीज़ की जड़ तक जाते हैं; साथी को आपकी गहराई पाने के लिए आपकी ईमानदारी झेलनी पड़ती है",
    "You need a partner who can keep pace, not one who tests patience; you move quickly and openly":
        "आपको ऐसा साथी चाहिए जो साथ चल सके, न कि धीरज आज़माए; आप तेज़ी और खुलेपन से बढ़ते हैं",
    "You commit for the long arc; you value character over chemistry, and keep both when you find them":
        "आप लंबी राह के लिए प्रतिबद्ध होते हैं; आप कैमिस्ट्री से ज़्यादा चरित्र को महत्व देते हैं, और दोनों मिलें तो दोनों सँभालते हैं",
    "You need real space and real depth; shallow closeness drains you, true intimacy heals you":
        "आपको सच्ची जगह और सच्ची गहराई चाहिए; उथली नज़दीकी आपको थका देती है, सच्ची आत्मीयता आपको भर देती है",
    "You forgive easily and love expansively; you need a partner who values your goodness, not exploits it":
        "आप आसानी से माफ़ करते हैं और विशाल हृदय से प्रेम करते हैं; आपको ऐसा साथी चाहिए जो आपकी भलाई को महत्व दे, उसका फ़ायदा न उठाए",
    "You are the steady one in love; your challenge is asking for the care you constantly give":
        "प्रेम में आप स्थिर वाले हैं; आपकी चुनौती है वह देखभाल माँगना जो आप लगातार देते हैं",
    "You love selflessly and dream deeply; you need a partner who protects your softness":
        "आप निःस्वार्थ प्रेम करते हैं और गहरे सपने देखते हैं; आपको ऐसा साथी चाहिए जो आपकी कोमलता की रक्षा करे",
    "You are attracted to charm and polish; the lesson is choosing substance beneath the shine":
        "आप आकर्षण और चमक की ओर खिंचते हैं; सबक़ है चमक के नीचे की गहराई चुनना",
    "You are built for deep committed partnership; loyalty comes naturally and is deeply needed in return":
        "आप गहरी, प्रतिबद्ध साझेदारी के लिए बने हैं; निष्ठा स्वाभाविक है और बदले में उतनी ही ज़रूरी",
    "You love deeply and possessively; trust built slowly, but once built, unshakeable":
        "आप गहरे और अधिकार-भाव से प्रेम करते हैं; भरोसा धीरे बनता है, पर बन जाए तो अटल",
    "Love transforms you completely; you need a partner unafraid of your depths":
        "प्रेम आपको पूरी तरह बदल देता है; आपको ऐसा साथी चाहिए जो आपकी गहराइयों से न डरे",

    # ---- ELEMENT_PAIR — milan_v2 English versions ----
    "Air brings the ideas, earth makes them real. Your different speeds are the friction — and exactly what makes you complete each other.":
        "वायु विचार लाती है, पृथ्वी उन्हें हक़ीक़त बनाती है। आपकी अलग रफ़्तारें ही टकराव हैं — और यही आपको एक-दूसरे का पूरक बनाती हैं।",
    "Air feeds the flame — adventures, plans, natural chemistry. You both love to fly; just decide early who's handling the landing.":
        "वायु आग को हवा देती है — रोमांच, योजनाएँ, स्वाभाविक कैमिस्ट्री। आप दोनों उड़ना पसंद करते हैं; बस पहले तय कर लें कि उतरना कौन संभालेगा।",
    "Air learns that not everything is logic; water learns that not everything can go unsaid. Build that bridge and it's pure poetry.":
        "वायु सीखती है कि हर चीज़ तर्क नहीं होती; जल सीखता है कि हर बात अनकही नहीं रह सकती। वह पुल बना लें, तो यह शुद्ध कविता है।",
    "Fire and water make steam — magnetic attraction and big reactions. Fire learns softness, water learns directness. It takes effort, and it makes magic.":
        "अग्नि और जल भाप बनाते हैं — चुंबकीय आकर्षण और बड़ी प्रतिक्रियाएँ। अग्नि कोमलता सीखती है, जल सीधापन। इसमें मेहनत लगती है, और यह जादू रचती है।",
    "One of you brings the pace, the other the patience. Fire learns to slow down, earth learns to loosen up — and together you actually build the things you dream about.":
        "एक रफ़्तार लाता है, दूसरा धीरज। अग्नि धीमा होना सीखती है, पृथ्वी थोड़ा ढीला पड़ना — और साथ मिलकर आप सचमुच वो चीज़ें बनाते हैं जिनके सपने देखते हैं।",
    "One of you brings the pace, the other the patience. Fire learns to slow down, earth learns to loosen up — and together you build the things you dream about.":
        "एक रफ़्तार लाता है, दूसरा धीरज। अग्नि धीमा होना सीखती है, पृथ्वी थोड़ा ढीला पड़ना — और साथ मिलकर आप वो चीज़ें बनाते हैं जिनके सपने देखते हैं।",
    "Soil and water — classical texts call this innately compatible. One gives security, the other depth. This is the easy, home-feeling kind of love.":
        "मिट्टी और पानी — शास्त्र इसे सहज-अनुकूल कहते हैं। एक सुरक्षा देता है, दूसरा गहराई। यह आसान, घर-सा महसूस होने वाला प्रेम है।",
    "You two run hot — big feelings, big fun, and the occasional big argument that's over as fast as it started. Your superpower is intensity; your homework is learning that only one of you needs to catch fire at a time.":
        "आप दोनों गरम मिज़ाज हैं — बड़ी भावनाएँ, बड़ा मज़ा, और कभी-कभार बड़ी बहस जो जितनी तेज़ी से शुरू होती है उतनी ही तेज़ी से ख़त्म। आपकी सुपरपावर है तीव्रता; आपका होमवर्क है यह सीखना कि एक बार में सिर्फ़ एक को ही भड़कना है।",
    "You'll never run out of things to talk about — ideas, plans, jokes only you two get. The thing to practise together: turning all those brilliant plans into actual decisions.":
        "आपके पास बात करने को कभी कमी नहीं होगी — विचार, योजनाएँ, ऐसे चुटकुले जो सिर्फ़ आप दोनों समझें। साथ अभ्यास करने की बात: उन सारी शानदार योजनाओं को असली फ़ैसलों में बदलना।",
    "You're the couple friends call 'solid'. You value security, loyalty and a life built brick by brick. The only risk: don't let the routine quietly replace the romance.":
        "आप वो जोड़ी हैं जिसे दोस्त ‘सॉलिड’ कहते हैं। आप सुरक्षा, निष्ठा और ईंट-दर-ईंट बनी ज़िंदगी को महत्व देते हैं। इकलौता ख़तरा: रोज़मर्रा को चुपचाप रोमांस की जगह मत लेने दें।",
    "Rare, almost wordless understanding — you read each other's moods like weather. Beautiful, but when you're both caught in a wave, someone has to be the calm shore.":
        "दुर्लभ, लगभग बिना शब्दों की समझ — आप एक-दूसरे के मूड को मौसम की तरह पढ़ते हैं। ख़ूबसूरत, पर जब आप दोनों एक ही लहर में बह रहे हों, किसी एक को शांत किनारा बनना होगा।",

    # ---- KOOTA_TEXT (Hinglish source) → Devanagari ----
    "Kaam aur ego ke matters mein aap dono ka natural order milta hai — ghar ke decisions mein tug-of-war kam hoga.":
        "काम और अहं के मामलों में आप दोनों का स्वाभाविक क्रम मिलता है — घर के फ़ैसलों में रस्साकशी कम होगी।",
    "Kaam-kaaj aur ego ke sawaalon mein role-clarity conscious rakhni hogi — kaun kya lead karta hai, yeh baat-cheet se tay karo, assumption se nahi.":
        "काम-काज और अहं के सवालों में भूमिका की स्पष्टता सोच-समझकर रखनी होगी — कौन क्या संभालता है, यह बातचीत से तय करें, अनुमान से नहीं।",
    "Aap dono ka ek dusre par sway balanced hai — koi kisi ko 'chala' nahi raha, dono saath chal rahe hain.":
        "आप दोनों का एक-दूसरे पर प्रभाव संतुलित है — कोई किसी को ‘चला’ नहीं रहा, दोनों साथ चल रहे हैं।",
    "Influence ek taraf thoda zyada hai — jab tak dominant partner ise care se use kare, yeh stability deta hai.":
        "प्रभाव एक तरफ़ थोड़ा ज़्यादा है — जब तक प्रभावी साथी इसे सावधानी से बरते, यह स्थिरता देता है।",
    "Mutual pull kam hai — matlab rishta convince karne se nahi, respect karne se chalega. Space dena yahan pyaar dikhaane ka tareeka hai.":
        "आपसी खिंचाव कम है — यानी रिश्ता मनाने से नहीं, सम्मान से चलेगा। जगह देना यहाँ प्यार जताने का तरीक़ा है।",
    "Nakshatra-count dono taraf shubh hai — saath rehne se dono ki wellbeing badhti hai, classical texts ise strong protection maanti hain.":
        "नक्षत्र-गणना दोनों तरफ़ शुभ है — साथ रहने से दोनों की कुशलता बढ़ती है, शास्त्र इसे मज़बूत रक्षा मानते हैं।",
    "Ek direction shubh, ek nahi — ek partner ko rishtey se zyada milta hai. Balance ke liye giving conscious rakhni hogi.":
        "एक दिशा शुभ, एक नहीं — एक साथी को रिश्ते से ज़्यादा मिलता है। संतुलन के लिए देना सोच-समझकर रखना होगा।",
    "Tara count inauspicious hai — traditionally health/wellbeing par dhyaan. Practical matlab: ek dusre ki sehat aur stress ka khayal is jodi ka zaroori ritual hona chahiye.":
        "तारा-गणना अशुभ है — परंपरा में सेहत/कुशलता पर ध्यान। व्यावहारिक अर्थ: एक-दूसरे की सेहत और तनाव का ख़याल इस जोड़ी की ज़रूरी आदत होनी चाहिए।",
    "Instinctive aur physical wavelength naturally milti hai — bina koshish ke comfort, jo har jodi ko naseeb nahi hota.":
        "सहज और शारीरिक तरंग स्वाभाविक रूप से मिलती है — बिना कोशिश का सुकून, जो हर जोड़ी को नसीब नहीं होता।",
    "Physical-instinctive match neutral hai — chemistry banayi ja sakti hai, bas dono ki pace alag ho sakti hai; patience rakho.":
        "शारीरिक-सहज मेल तटस्थ है — कैमिस्ट्री बनाई जा सकती है, बस दोनों की रफ़्तार अलग हो सकती है; धीरज रखें।",
    "Yoni enemy-pair hai — instincts alag chalti hain. Yeh attraction ko nahi rokta, par daily-life habits (sona, uthna, touch, space) mein adjustment maangta hai. Naam se mat daro, pattern samjho.":
        "योनि शत्रु-जोड़ी है — सहज-प्रवृत्तियाँ अलग चलती हैं। यह आकर्षण को नहीं रोकता, पर रोज़मर्रा की आदतों (सोना, उठना, स्पर्श, जगह) में तालमेल माँगता है। नाम से मत डरें, पैटर्न समझें।",
    "Moon-lords doston mein hain — aap dono ka sochne ka tareeka compatible hai. Behas hogi toh bhi bhasha ek hi hogi.":
        "चंद्र-स्वामी मित्र हैं — आप दोनों के सोचने का तरीक़ा अनुकूल है। बहस होगी तो भी भाषा एक ही होगी।",
    "Moon-lords neutral hain — mental wavelength banti hai shared experiences se. Saath cheezein karo, wavelength khud align hogi.":
        "चंद्र-स्वामी तटस्थ हैं — मानसिक तरंग साझा अनुभवों से बनती है। साथ चीज़ें करें, तरंग ख़ुद जुड़ जाएगी।",
    "Moon-lords ki adaawat hai — matlab default sochne ke tareeke alag hain. Iska ilaaj hai 'translate' karna seekhna: partner ki baat ko uske frame mein samajhna, apne mein nahi.":
        "चंद्र-स्वामियों में अनबन है — यानी सोचने के मूल तरीक़े अलग हैं। इसका इलाज है ‘अनुवाद’ करना सीखना: साथी की बात को उसके नज़रिए में समझना, अपने में नहीं।",
    "Temperament same category ka hai — energy levels, social style, gussa-shanti ka pattern milta hai.":
        "स्वभाव एक ही श्रेणी का है — ऊर्जा-स्तर, सामाजिक अंदाज़, ग़ुस्सा-शांति का पैटर्न मिलता है।",
    "Deva-Manushya pairing — ek zyada idealist, ek zyada practical. Achhi jodi, bas expectations ko naam dena seekho.":
        "देव-मनुष्य जोड़ी — एक ज़्यादा आदर्शवादी, एक ज़्यादा व्यावहारिक। अच्छी जोड़ी, बस अपेक्षाओं को नाम देना सीखें।",
    "Gana mismatch hai — temperament genuinely alag hain (jaise ek ko bheed chahiye, ek ko sannata). Yeh deal-breaker nahi, design-brief hai: ghar aisa banao jismein dono modes ki jagah ho.":
        "गण बेमेल है — स्वभाव सचमुच अलग हैं (जैसे एक को भीड़ चाहिए, एक को सन्नाटा)। यह डील-ब्रेकर नहीं, डिज़ाइन-ब्रीफ़ है: घर ऐसा बनाएँ जिसमें दोनों अंदाज़ों की जगह हो।",
    "Moon-signs ki relative position shubh hai — emotional bond aur family-growth ke liye classical green signal.":
        "चंद्र-राशियों की सापेक्ष स्थिति शुभ है — भावनात्मक बंधन और परिवार-वृद्धि के लिए शास्त्रीय हरा संकेत।",
    "Bhakoot dosha hai — 6-8, 2-12 ya 5-9 ki position. Traditionally emotional distance ya financial friction se joda jaata hai. Cancellation check neeche dekho — aksar lords ki dosti ise cancel kar deti hai.":
        "भकूट दोष है — 6-8, 2-12 या 5-9 की स्थिति। परंपरा में इसे भावनात्मक दूरी या आर्थिक टकराव से जोड़ा जाता है। रद्दीकरण जाँच नीचे देखें — अक्सर स्वामियों की मित्रता इसे रद्द कर देती है।",
    "Nadi alag hai — sabse heavy koota clear hai. Classical texts iske liye sabse zyada points isi liye deti hain.":
        "नाड़ी अलग है — सबसे भारी कूट साफ़ है। शास्त्र इसीलिए इसके लिए सबसे ज़्यादा अंक देते हैं।",
    "Nadi same hai — traditionally sabse serious dosha, progeny aur vitality se juda. LEKIN: iske cancellation rules sabse well-defined hain. Neeche ka cancellation-check hi asli verdict hai, yeh zero nahi.":
        "नाड़ी समान है — परंपरा में सबसे गंभीर दोष, संतान और जीवनशक्ति से जुड़ा। लेकिन: इसके रद्दीकरण नियम सबसे स्पष्ट हैं। नीचे की रद्दीकरण-जाँच ही असली फ़ैसला है, यह शून्य नहीं।",

    # ---- ELEMENT_PAIR (Hinglish source) → Devanagari ----
    "Do fire moons — passion, speed aur honesty double; conflict bhi bright jalta hai par jaldi bujhta hai. Rule seekhiye: ek waqt par ek hi jale.":
        "दो अग्नि चंद्र — जोश, रफ़्तार और ईमानदारी दुगनी; टकराव भी चमककर जलता है पर जल्दी बुझता है। नियम सीखें: एक बार में एक ही जले।",
    "Do earth moons — stability, saving, building. Rishta ghar jaisa lagta hai; risk sirf yeh ki routine romance ko na kha jaaye.":
        "दो पृथ्वी चंद्र — स्थिरता, बचत, निर्माण। रिश्ता घर जैसा लगता है; ख़तरा सिर्फ़ यह कि रोज़मर्रा रोमांस को न खा जाए।",
    "Do air moons — baatein kabhi khatam nahi hongi. Mental match excellent; grounding (routine, decisions) ko conscious effort dena hoga.":
        "दो वायु चंद्र — बातें कभी ख़त्म नहीं होंगी। मानसिक मेल बेहतरीन; ज़मीनीपन (रोज़मर्रा, फ़ैसले) को सोच-समझकर मेहनत देनी होगी।",
    "Do water moons — bina bole samajhna. Emotional depth rare-level ki hai; mood ek dusre par lehron ki tarah aate hain, isliye ek ka calm rehna zaroori.":
        "दो जल चंद्र — बिना बोले समझना। भावनात्मक गहराई दुर्लभ स्तर की है; मूड एक-दूसरे पर लहरों की तरह आते हैं, इसलिए एक का शांत रहना ज़रूरी।",
    "Fire + earth — spark aur zameen. Ek raftaar laata hai, doosra thehraav. Fire ko patience, earth ko thodi spontaneity seekhni hogi — phir yeh builder-jodi hai.":
        "अग्नि + पृथ्वी — चिंगारी और ज़मीन। एक रफ़्तार लाता है, दूसरा ठहराव। अग्नि को धीरज, पृथ्वी को थोड़ी सहजता सीखनी होगी — फिर यह निर्माता-जोड़ी है।",
    "Fire + air — hawa aag ko badhaati hai. Energy, plans, adventures — natural chemistry. Dhyaan bas itna: dono udna jaante hain, landing kaun karayega yeh tay kar lo.":
        "अग्नि + वायु — हवा आग को बढ़ाती है। ऊर्जा, योजनाएँ, रोमांच — स्वाभाविक कैमिस्ट्री। ध्यान बस इतना: दोनों उड़ना जानते हैं, उतरना कौन कराएगा यह तय कर लें।",
    "Fire + water — bhaap banti hai: intense attraction, intense reactions. Fire ko softness, water ko directness seekhni hogi. Mehnat maangta hai, magic deta hai.":
        "अग्नि + जल — भाप बनती है: तीव्र आकर्षण, तीव्र प्रतिक्रियाएँ। अग्नि को कोमलता, जल को सीधापन सीखना होगा। मेहनत माँगता है, जादू देता है।",
    "Earth + air — practical milta hai conceptual se. Air ideas laata hai, earth unhe khada karta hai. Pace ka difference hi friction hai, aur wahi complementarity bhi.":
        "पृथ्वी + वायु — व्यावहारिक मिलता है वैचारिक से। वायु विचार लाती है, पृथ्वी उन्हें खड़ा करती है। रफ़्तार का फ़र्क़ ही टकराव है, और वही पूरकता भी।",
    "Earth + water — mitti aur paani: sabse naturally nourishing pair. Ek security deta hai, doosra depth. Classical texts ise sahaj-anukool maanti hain.":
        "पृथ्वी + जल — मिट्टी और पानी: सबसे स्वाभाविक रूप से पोषक जोड़ी। एक सुरक्षा देता है, दूसरा गहराई। शास्त्र इसे सहज-अनुकूल मानते हैं।",
    "Air + water — words milte hain feelings se. Air ko seekhna hoga ki har baat logic nahi hoti; water ko, ki har baat kehni padti hai. Bridge bana toh poetry hai.":
        "वायु + जल — शब्द मिलते हैं भावनाओं से। वायु को सीखना होगा कि हर बात तर्क नहीं होती; जल को, कि हर बात कहनी पड़ती है। पुल बना तो कविता है।",

    # ---- REMEDIES (p1/p2/work_on/remedy) ----
    "Name the one area you most want to lead — and say it plainly.":
        "वह एक क्षेत्र बताएँ जिसमें आप सबसे ज़्यादा आगे रहना चाहते हैं — और साफ़-साफ़ कहें।",
    "Name the one area you're happy to hand over — and genuinely let go of it.":
        "वह एक क्षेत्र बताएँ जो आप ख़ुशी से सौंप सकते हैं — और सचमुच उसे छोड़ दें।",
    "Spell out who owns which calls — money, home, plans, social life — out loud, instead of assuming.":
        "साफ़ कहें कि कौन-सा फ़ैसला किसका है — पैसा, घर, योजनाएँ, सामाजिक जीवन — मानकर चलने के बजाय।",
    "A gentle classical practice: offer water to the rising sun together on Sunday mornings — a small shared ritual said to balance ego and authority.":
        "एक सौम्य शास्त्रीय अभ्यास: रविवार की सुबह साथ मिलकर उगते सूरज को जल चढ़ाएँ — एक छोटी साझा रीति, कहा जाता है कि यह अहं और अधिकार को संतुलित करती है।",
    "Agree a simple signal for 'I need people' vs 'I need quiet' — and honour it once.":
        "‘मुझे लोग चाहिए’ बनाम ‘मुझे शांति चाहिए’ के लिए एक सरल संकेत तय करें — और एक बार उसका मान रखें।",
    "Tell the other plainly what recharges you — a night out or a night in — and agree a simple signal for it.":
        "दूसरे को साफ़ बताएँ कि आपको क्या तरोताज़ा करता है — बाहर की शाम या घर की शाम — और उसके लिए एक सरल संकेत तय करें।",
    "This is about different instincts, not low attraction — so talk openly about pace, touch and daily rhythms.":
        "यह अलग सहज-प्रवृत्तियों की बात है, कम आकर्षण की नहीं — तो रफ़्तार, स्पर्श और रोज़मर्रा की लय पर खुलकर बात करें।",
    "You think in different 'languages', so practise translating before you react.":
        "आप अलग ‘भाषाओं’ में सोचते हैं, तो प्रतिक्रिया देने से पहले अनुवाद करने का अभ्यास करें।",
    "In a disagreement, say your partner's point back in their words before you reply — until they say 'yes, that's it.'":
        "असहमति में, जवाब देने से पहले साथी की बात उन्हीं के शब्दों में दोहराएँ — जब तक वे न कहें ‘हाँ, बिल्कुल यही।’",
    "Your energies genuinely differ (say, one loves a crowd, one loves quiet). Don't try to fix it — design around it.":
        "आपकी ऊर्जाएँ सचमुच अलग हैं (जैसे एक को भीड़ पसंद, एक को शांति)। इसे ठीक करने की कोशिश न करें — इसके इर्द-गिर्द तालमेल बनाएँ।",
    "Make each other's wellbeing a shared project — sleep, food, stress — instead of assuming the other is fine.":
        "एक-दूसरे की कुशलता को साझा प्रोजेक्ट बनाएँ — नींद, खाना, तनाव — यह मानकर चलने के बजाय कि दूसरा ठीक है।",
    "Name one rhythm — sleep, space or affection — you'd like the other to understand, and ask for theirs.":
        "एक लय बताएँ — नींद, जगह या स्नेह — जिसे आप चाहते हैं दूसरा समझे, और उनकी भी पूछें।",
    "Book your own basics — a check-up, better sleep, less chronic stress; treat wellbeing as a team sport.":
        "अपनी बुनियादी बातें तय करें — जाँच, बेहतर नींद, कम लगातार तनाव; कुशलता को टीम-खेल की तरह लें।",
    "Book the unglamorous stuff — check-ups, good sleep, less chronic stress — as a team.":
        "साधारण-सी ज़रूरी बातें — जाँच, अच्छी नींद, कम लगातार तनाव — टीम बनकर तय करें।",
    "Traditionally the heaviest factor, tied to health and children — so the real 'remedy' is proactive care, together.":
        "परंपरा में सबसे भारी पहलू, सेहत और संतान से जुड़ा — तो असली ‘उपाय’ है साथ मिलकर सक्रिय देखभाल।",
    # remedy rituals
    "A Moon remedy: on Mondays wear white, chant 'Om Somaya Namah', and offer milk or white flowers at a Shiva temple together.":
        "एक चंद्र उपाय: सोमवार को सफ़ेद पहनें, ‘ॐ सोमाय नमः’ जपें, और साथ मिलकर शिव मंदिर में दूध या सफ़ेद फूल अर्पित करें।",
    "A classical Nadi practice is the Maha Mrityunjaya mantra and donating toward medicines/health; the modern equivalent is a simple pre-marriage health check for both.":
        "एक शास्त्रीय नाड़ी अभ्यास है महामृत्युंजय मंत्र और दवा/सेहत के लिए दान; आधुनिक समकक्ष है दोनों की एक सरल विवाह-पूर्व स्वास्थ्य जाँच।",
    "A shared calming ritual helps — light a small oil lamp at dusk and chant 'Om Namah Shivaya' together; traditionally it settles temperament clashes.":
        "एक साझा शांत करने वाली रीति मदद करती है — शाम को एक छोटा दीपक जलाएँ और साथ ‘ॐ नमः शिवाय’ जपें; परंपरा में यह स्वभाव के टकराव को शांत करती है।",
    "For mental harmony: green on Wednesdays with 'Om Budhaya Namah' (Mercury), and an unhurried moonlit walk together on Mondays (Moon).":
        "मानसिक सामंजस्य के लिए: बुधवार को हरा और ‘ॐ बुधाय नमः’ (बुध), और सोमवार को साथ इत्मीनान से चाँदनी में टहलना (चंद्र)।",
    "Venus rules attraction — on Fridays keep something white nearby and repeat 'Om Shukraya Namah' a few times together.":
        "शुक्र आकर्षण का स्वामी है — शुक्रवार को पास कुछ सफ़ेद रखें और साथ कुछ बार ‘ॐ शुक्राय नमः’ दोहराएँ।",
    "Venus is your ally here too — Friday is the day; soft, warm tones at home and 'Om Shukraya Namah' are the classical nudges for closeness.":
        "शुक्र यहाँ भी आपका साथी है — शुक्रवार वह दिन है; घर में कोमल, गर्म रंग और ‘ॐ शुक्राय नमः’ नज़दीकी के शास्त्रीय संकेत हैं।",
    "A Bhakoot placement is present — check whether friendly moon-lords cancel it.":
        "एक भकूट स्थिति मौजूद है — जाँचें कि क्या मित्र चंद्र-स्वामी इसे रद्द करते हैं।",
    "Nadi is shared — often lifted when moon-signs differ; a pada-level check is advised.":
        "नाड़ी समान है — अक्सर चंद्र-राशियाँ अलग होने पर हट जाती है; पद-स्तर की जाँच सुझाई जाती है।",

    # ---- ACTION_PLAN (try / talk / green) ----
    "This week, each of you names one area you'd love to lead and one you'd happily hand over.":
        "इस हफ़्ते, आप दोनों एक क्षेत्र बताएँ जिसमें आप अगुआई करना चाहेंगे और एक जो ख़ुशी से सौंप देंगे।",
    "You stop quietly keeping score of who decided what.":
        "आप चुपचाप यह हिसाब रखना बंद कर देते हैं कि कौन-सा फ़ैसला किसने किया।",
    "One 20-minute, phones-away conversation this week — no fixing, just listening.":
        "इस हफ़्ते एक 20-मिनट की, फ़ोन-दूर बातचीत — कुछ ठीक करना नहीं, बस सुनना।",
    "Time together starts to feel chosen, not squeezed in.":
        "साथ का समय चुना हुआ लगने लगता है, ठूँसा हुआ नहीं।",
    "Do a light 15-minute 'us, money & feelings' check-in.":
        "एक हल्की 15-मिनट की ‘हम, पैसा और भावनाएँ’ बातचीत करें।",
    "Small distances get named before they grow.":
        "छोटी दूरियाँ बढ़ने से पहले ही पहचान ली जाती हैं।",
    "Different moods stop getting taken personally.":
        "अलग-अलग मूड को दिल पर लेना बंद हो जाता है।",
    "Different paces stop feeling like rejection.":
        "अलग-अलग रफ़्तारें अस्वीकार जैसी महसूस होना बंद हो जाती हैं।",
    "You treat wellbeing as a shared project, not a solo one.":
        "आप कुशलता को साझा प्रोजेक्ट मानते हैं, अकेले का नहीं।",
    "You argue in the same language, not past each other.":
        "आप एक ही भाषा में बहस करते हैं, एक-दूसरे से कटकर नहीं।",
    "You both feel better after time together, not more tired.":
        "साथ बिताए समय के बाद आप दोनों बेहतर महसूस करते हैं, ज़्यादा थके नहीं।",
    "Book your own basics — a check-up, better sleep, less chronic stress; treat wellbeing as a team sport. ":
        "अपनी बुनियादी बातें तय करें — जाँच, बेहतर नींद, कम लगातार तनाव; कुशलता को टीम-खेल की तरह लें।",
    "Do one small health thing together — a walk, cooking a real meal, an early night.":
        "एक छोटा सेहत-काम साथ करें — टहलना, असली खाना पकाना, जल्दी सोना।",
    "On Thursdays, share a simple home-cooked meal and donate a little food or grain together — a traditional gesture for mutual wellbeing.":
        "गुरुवार को एक सरल घर का बना खाना साझा करें और साथ थोड़ा भोजन या अनाज दान करें — आपसी कुशलता के लिए एक पारंपरिक भाव।",
    "Compare your daily rhythms — sleep, energy, affection — and pick one to sync.":
        "अपनी रोज़मर्रा की लय की तुलना करें — नींद, ऊर्जा, स्नेह — और एक को मिलाने के लिए चुनें।",
    "Lock one proper date into the calendar for the next two weeks — non-negotiable.":
        "अगले दो हफ़्तों के लिए कैलेंडर में एक पक्की डेट तय करें — बिना किसी बहाने।",
    "The classic risks here are emotional distance and money friction — get ahead of both, and keep daily affection non-negotiable.":
        "यहाँ आम ख़तरे हैं भावनात्मक दूरी और पैसे का टकराव — दोनों से आगे रहें, और रोज़ का स्नेह बिना समझौते बनाए रखें।",
    "A lower pull just means the bond runs on respect, not gravity — so make closeness deliberate, not left to chance.":
        "कम खिंचाव का बस इतना मतलब है कि बंधन खिंचाव से नहीं, सम्मान से चलता है — तो नज़दीकी सोच-समझकर बनाएँ, संयोग पर न छोड़ें।",
    "Own the daily thread — keep the small check-ins going through the week.":
        "रोज़ की डोर संभालें — हफ़्ते भर छोटी-छोटी बातचीत जारी रखें।",
    "Own the emotional rhythm — a regular, honest 'how are we, really?' talk.":
        "भावनात्मक लय संभालें — एक नियमित, ईमानदार ‘हम सच में कैसे हैं?’ वाली बात।",
    "Own the money rhythm — a light monthly 'us & money' check-in.":
        "पैसे की लय संभालें — एक हल्की मासिक ‘हम और पैसा’ बातचीत।",
    "Own the plan — set up one proper, protected date this week.":
        "योजना संभालें — इस हफ़्ते एक पक्की, सुरक्षित डेट तय करें।",
    "Keep an eye on the basics — nudge each other on rest, food and sleep.":
        "बुनियादी बातों पर नज़र रखें — आराम, खाने और नींद के लिए एक-दूसरे को याद दिलाएँ।",
    "Keep an eye on the load — check in on stress and what's draining them.":
        "बोझ पर नज़र रखें — तनाव और जो उन्हें थका रहा है, उसकी ख़बर लेते रहें।",

    # ---- ACTION_PLAN "talk" lines (quoted) ----
    "“Where do you want me to take charge — and where do you want to?”":
        "“आप कहाँ चाहते हैं कि मैं ज़िम्मा लूँ — और कहाँ आप लेना चाहते हैं?”",
    "“What recharges you — a night out, or a night in?”":
        "“आपको क्या तरोताज़ा करता है — बाहर की शाम, या घर की शाम?”",
    "“What does feeling close look like for you, day to day?”":
        "“आपके लिए नज़दीकी महसूस होना रोज़मर्रा में कैसा दिखता है?”",
    "“What's something you've been carrying that I haven't noticed?”":
        "“ऐसी कोई बात जो आप ढो रहे हैं और मैंने ध्यान नहीं दी?”",
    "“Let me say that back — did I get it right?”":
        "“मैं इसे दोहरा दूँ — क्या मैंने सही समझा?”",
    "“How do we want to look after each other's health?”":
        "“हम एक-दूसरे की सेहत का ख़याल कैसे रखना चाहते हैं?”",
    "“What makes you feel closest to me?”":
        "“किस चीज़ से आप मेरे सबसे क़रीब महसूस करते हैं?”",
    "“What's been draining you lately, and how can I help?”":
        "“हाल में आपको क्या थका रहा है, और मैं कैसे मदद करूँ?”",

    # ---- milan_v2 inline (growth/chemistry/synthesis/checks) ----
    "You don’t need to match. Just translate.": "आपको एक जैसा होना ज़रूरी नहीं। बस अनुवाद करना सीखें।",
    "The same difference, turned into a strength": "वही फ़र्क़, ताक़त में बदला हुआ",
    "Two minds, two languages": "दो मन, दो भाषाएँ",
    "Why the friction is real (not imagined)": "टकराव असली क्यों है (कल्पना नहीं)",
    "When something’s wrong…": "जब कुछ गड़बड़ हो…",
    "You connect deeply; you just run different operating systems.":
        "आप गहराई से जुड़ते हैं; बस आप अलग ऑपरेटिंग सिस्टम पर चलते हैं।",
    "The rare part — the deep, hard-to-build compatibility — you already":
        "दुर्लभ हिस्सा — वह गहरी, मुश्किल-से-बनने वाली अनुकूलता — आपके पास पहले से",
    ". The workable part is exactly the kind couples":
        "। और सुधरने लायक हिस्सा ठीक वैसा है जैसा जोड़े",
    "Guna milan measures your natural fit — not maturity, values or commitment, the real pillars of any marriage.":
        "गुण मिलान आपके स्वाभाविक मेल को मापता है — परिपक्वता, मूल्य या प्रतिबद्धता को नहीं, जो किसी भी शादी के असली स्तंभ हैं।",
    "You’re strong where it’s hardest to fix and grow where it’s easiest — the best-shaped score there is.":
        "आप वहाँ मज़बूत हैं जहाँ सुधारना सबसे कठिन है और वहाँ बढ़ते हैं जहाँ सबसे आसान — इससे बेहतर आकार का स्कोर नहीं होता।",
    "Most happy couples aren’t 100%. A strong base + a little effort = a genuinely lasting match.":
        "ज़्यादातर ख़ुश जोड़े 100% नहीं होते। एक मज़बूत नींव + थोड़ी मेहनत = सचमुच टिकने वाला मैच।",
    "The Sun is who you are to the world; the Moon is who you are in love — so Vedic matching reads the Moon, not the Sun.":
        "सूर्य वह है जो आप दुनिया के लिए हैं; चंद्रमा वह है जो आप प्रेम में हैं — इसलिए वैदिक मिलान चंद्रमा को पढ़ता है, सूर्य को नहीं।",
    "If this felt true for you, it’ll mean the world to someone figuring out “is this the one?”":
        "अगर यह आपको सच लगा, तो यह उस किसी के लिए बहुत मायने रखेगा जो सोच रहा है “क्या यही वो हैं?”",
    "Your toolkit": "आपका टूलकिट",
    "Chemistry": "कैमिस्ट्री",
    "Keep the spark deliberate": "चिंगारी को जानबूझकर बनाए रखें",
    "Chemistry you tend to, stays": "जिस कैमिस्ट्री का ख़याल रखते हैं, वो टिकती है",
    "The trap to avoid…": "जिस जाल से बचना है…",
    "A respect-based pull can quietly slide into “comfortable.” The fix isn’t more heat — it’s more intention: closeness you choose, not leave to chance.":
        "सम्मान-आधारित खिंचाव चुपचाप “आरामदेह” में फिसल सकता है। इलाज ज़्यादा गर्मी नहीं — ज़्यादा इरादा है: नज़दीकी जो आप चुनें, संयोग पर न छोड़ें।",
    "Fridays are Venus’s day — warm tones, unhurried evenings, a little more touch.":
        "शुक्रवार शुक्र का दिन है — गर्म रंग, इत्मीनान भरी शामें, थोड़ा ज़्यादा स्पर्श।",
    "The spark — real, but not on autopilot": "चिंगारी — असली, पर अपने-आप चलने वाली नहीं",
    "The spark — alive and well": "चिंगारी — जीवंत और भरपूर",
    "The spark is real and mutual.": "चिंगारी असली और दोतरफ़ा है।",
    "A pull built on respect and effort — which, honestly, outlasts fireworks.":
        "सम्मान और मेहनत पर बना खिंचाव — जो सच कहें तो आतिशबाज़ी से ज़्यादा टिकता है।",
    "Not natural allies, not enemies. Your chemistry is real, but it’s built on attraction you nurture, not pure gravity. The upside — that kind deepens with time instead of fading.":
        "न स्वाभाविक साथी, न दुश्मन। आपकी कैमिस्ट्री असली है, पर वह उस आकर्षण पर बनी है जिसे आप पोषते हैं, महज़ खिंचाव पर नहीं। अच्छी बात — वैसी कैमिस्ट्री समय के साथ फीकी पड़ने के बजाय गहरी होती है।",
    "Your instinctive styles have a natural pull — the chemistry is already there to build on.":
        "आपकी सहज शैलियों में एक स्वाभाविक खिंचाव है — कैमिस्ट्री पहले से मौजूद है, बस उस पर बनाना है।",
    "the spark — physical pull and how you gravitate toward each other.":
        "चिंगारी — शारीरिक खिंचाव और आप एक-दूसरे की ओर कैसे बढ़ते हैं।",
    "A mix that’s uniquely yours.": "एक मेल जो बिल्कुल आपका अपना है।",

    # ---- KOOTA_UI blurbs (weak/other) ----
    "how your minds click, and who leads what.": "आपके मन कैसे मिलते हैं, और कौन क्या संभालता है।",
    "How your minds click, and who leads what.": "आपके मन कैसे मिलते हैं, और कौन क्या संभालता है।",
    "your day-to-day energy and whether your moods sync.":
        "आपकी रोज़मर्रा की ऊर्जा और क्या आपके मूड मिलते हैं।",
    "Your day-to-day energy and whether your moods sync.":
        "आपकी रोज़मर्रा की ऊर्जा और क्या आपके मूड मिलते हैं।",
    "vitality and the traditional family / progeny factor.":
        "जीवनशक्ति और पारंपरिक परिवार / संतान का पहलू।",
    "Long-term closeness and how good you are for each other.":
        "लंबा साथ और आप एक-दूसरे के लिए कितने अच्छे हैं।",
    "Why you aced it": "आपने इसमें कमाल क्यों किया",
    "Your Moon-lords are naturally friendly — you think in the same language. Even your disagreements make sense to each other.":
        "आपके चंद्र-स्वामी स्वाभाविक रूप से मित्र हैं — आप एक ही भाषा में सोचते हैं। आपकी असहमतियाँ भी एक-दूसरे को समझ आती हैं।",
    "What it means for you": "आपके लिए इसका क्या मतलब",
    "Why this is your growth edge": "यह आपका ग्रोथ किनारा क्यों है",
    "Worth a look": "देखने लायक",
    "Worth Understanding": "समझने लायक",
    "One-sided": "एकतरफ़ा",
    "Shared": "साझा",

    # ---- traditional checks (variants) ----
    "One chart carries a Manglik placement (Moon-based check). Cancellation rules usually apply — a full lagna-based check needs exact birth times for both.":
        "एक कुंडली में मांगलिक स्थिति है (चंद्र-आधारित जाँच)। रद्दीकरण नियम आमतौर पर लागू होते हैं — पूरी लग्न-आधारित जाँच के लिए दोनों के सटीक जन्म समय चाहिए।",
    "Both charts carry a Manglik placement — and in the classical rule a Manglik–Manglik pairing cancels out. Not an obstacle.":
        "दोनों कुंडलियों में मांगलिक स्थिति है — और शास्त्रीय नियम में मांगलिक–मांगलिक जोड़ी एक-दूसरे को रद्द कर देती है। कोई बाधा नहीं।",
    "Neither chart carries a Manglik placement (Moon-based check). ✅":
        "किसी भी कुंडली में मांगलिक स्थिति नहीं है (चंद्र-आधारित जाँच)। ✅",
    "Your Nadis differ — no Nadi dosha, a strong positive sign.":
        "आपकी नाड़ियाँ अलग हैं — कोई नाड़ी दोष नहीं, एक मज़बूत सकारात्मक संकेत।",
    "Your Moon signs sit in a favourable position — long-term harmony supported.":
        "आपकी चंद्र राशियाँ अनुकूल स्थिति में हैं — लंबे समय के सामंजस्य को समर्थन।",
    "Your Moon signs sit in a mutually supportive position — the classical “green signal” for emotional closeness, family life, and shared prosperity.":
        "आपकी चंद्र राशियाँ परस्पर सहायक स्थिति में हैं — भावनात्मक नज़दीकी, पारिवारिक जीवन और साझा समृद्धि का शास्त्रीय “हरा संकेत”।",
    "Dosha only if identical → flagged.": "दोष सिर्फ़ तभी जब बिल्कुल एक जैसे हों → चिह्नित।",
}
