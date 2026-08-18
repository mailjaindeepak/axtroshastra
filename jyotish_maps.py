"""Shared Jyotish content maps for Axtroshastra reports. Pure data, no logic."""

# ---- 27 nakshatra profiles: (symbol, one-line nature, relationship line) ----
NAK_PROFILE = {
0:("Horse's head","Fast, healing, pioneering — you begin things others hesitate to start","In love you move quickly and openly; you need a partner who can keep pace, not one who tests patience"),
1:("Yoni","Intense, creative, carrying — you hold and transform whatever you take on","You love deeply and possessively; trust built slowly, but once built, unshakeable"),
2:("Razor / flame","Sharp, purifying, protective — you cut through confusion for yourself and others","You test partners early; behind the sharpness is fierce loyalty to the one who passes"),
3:("Chariot / ox-cart","Steady, magnetic, growth-giving — things flourish under your care","You are romantic and devoted; stability and sensory comfort are your love languages"),
4:("Deer's head","Searching, gentle, restless — always seeking the next meaningful thing","You need mental chase and novelty in love; boredom, not conflict, is your relationship risk"),
5:("Teardrop / gem","Stormy, brilliant, transformative — you grow through intensity","Love for you is passionate and turbulent; the right partner is a steady anchor, not another storm"),
6:("Bow and quiver","Renewing, optimistic, generous — you always find the way back","You forgive easily and love expansively; you need a partner who values your goodness, not exploits it"),
7:("Flower / udder","Nourishing, dutiful, spiritually inclined — people feel safe around you","You express love through care and service; you flourish with a partner who reciprocates, not just receives"),
8:("Coiled serpent","Perceptive, private, penetrating — you see what others hide","You guard your heart; intimacy comes in layers, and betrayal is the one unforgivable"),
9:("Throne","Regal, ancestral, proud — lineage and legacy matter to you","You love with dignity and expect respect; public loyalty from a partner matters as much as private love"),
10:("Front of the bed","Playful, generous, pleasure-loving — you bring warmth to every room","Romance, celebration and affection are essentials for you, not luxuries"),
11:("Back of the bed","Balanced, dependable, contract-honouring — your word is your bond","You take commitment seriously and expect the same; casual love does not satisfy you"),
12:("Hand","Skilled, witty, resourceful — you fix things, literally and socially","You show love through practical help and humour; you need appreciation, not grand drama"),
13:("Pearl / jewel","Charismatic, artistic, form-loving — you shape beauty from chaos","You are attracted to charm and polish; the lesson is choosing substance beneath the shine"),
14:("Young sprout in wind","Independent, adaptable, diplomatic — you move alone and gracefully","You need space inside love; the right partner holds you loosely and gains all of you"),
15:("Triumphal archway","Ambitious, focused, dual-natured — victory is your vocabulary","You love with purpose; partnership works when you are building something together"),
16:("Lotus","Devoted, friendly, harmonising — you soften hard rooms","You are built for deep committed partnership; loyalty comes naturally and is deeply needed in return"),
17:("Earring / umbrella","Senior, intense, protective — you carry responsibility early","You protect the ones you love fiercely; softness is there, under the armour"),
18:("Bundle of roots","Deep-digging, truth-seeking, uprooting — surface answers never satisfy you","In love you go to the root of everything; partners must survive your honesty to earn your depth"),
19:("Elephant tusk / fan","Invincible-spirited, proud, purifying — you rise after every fall","You love wholeheartedly and expect faith in your comeback; doubt from a partner wounds most"),
20:("Elephant tusk / cot","Universal, principled, enduring — you win slowly and permanently","You commit for the long arc; you value character over chemistry, and keep both when you find them"),
21:("Ear / three footprints","Listening, learned, connective — knowledge flows through you","You fall for minds; conversation is your intimacy, silence together your comfort"),
22:("Drum","Rhythmic, wealthy-spirited, generous — you keep many worlds in beat","You need a partner in rhythm with your ambitions; you give abundantly when met halfway"),
23:("Empty circle / 100 healers","Mystic, solitary, healing — you restore what the world breaks","You need real space and real depth; shallow closeness drains you, true intimacy heals you"),
24:("Sword / two-faced man","Intense, transformative, fire-carrying — you burn and rebuild","Love transforms you completely; you need a partner unafraid of your depths"),
25:("Twins / serpent of the deep","Wise, compassionate, stabilising — the calm after others' storms","You are the steady one in love; your challenge is asking for the care you constantly give"),
26:("Fish / drum","Nurturing, complete, transcendent — endings and beginnings meet in you","You love selflessly and dream deeply; you need a partner who protects your softness")}

# ---- Devanagari twins of NAK_PROFILE's (persona, love) — authored Hindi, not
# machine-translated. Used by the Hindi funnel teaser (products.compute_milan's
# *_hi fields). Index-parallel with NAK_PROFILE; keep lengths comparable to the
# English lines so the preview boxes don't overflow. ----
NAK_PROFILE_HI = {
0:("तेज़, राह खोलने वाले, हौसले से भरे — जो काम शुरू करने में लोग हिचकते हैं, आप कर गुज़रते हैं","प्यार में आप तेज़ और खुलकर आगे बढ़ते हैं; आपको ऐसा साथी चाहिए जो आपकी रफ़्तार से चल सके, धीरज की परीक्षा न ले"),
1:("गहरे, रचनात्मक, सँभालने वाले — जो भी ज़िम्मा उठाते हैं, उसे थामते भी हैं और बदल भी देते हैं","आप गहराई से और पूरे हक़ से प्यार करते हैं; भरोसा धीरे-धीरे बनता है, पर बन जाए तो अटूट"),
2:("तेज़ धार वाले, खरे, रक्षक — अपनी और अपनों की उलझनें काटकर साफ़ कर देते हैं","आप साथी को शुरुआत में ही परखते हैं; उस तीखेपन के पीछे उसके लिए गहरी वफ़ादारी है जो परख में खरा उतरे"),
3:("स्थिर, चुंबकीय, बढ़ाने वाले — आपकी देखरेख में चीज़ें खिल उठती हैं","आप रोमांटिक और समर्पित हैं; ठहराव और सुकून-भरा आराम ही आपके प्यार की भाषा है"),
4:("खोजी, कोमल, बेचैन — हमेशा अगली मायने रखने वाली चीज़ की तलाश में","प्यार में आपको दिमाग़ी खिंचाव और नयापन चाहिए; आपके रिश्ते का ख़तरा झगड़ा नहीं, ऊब है"),
5:("तूफ़ानी, चमकदार, बदल देने वाले — आप तीव्रता से गुज़रकर ही बढ़ते हैं","आपके लिए प्यार जोशीला और उथल-पुथल भरा है; सही साथी एक ठहरा हुआ लंगर है, एक और तूफ़ान नहीं"),
6:("नई शुरुआत वाले, आशावादी, दिलदार — आप हमेशा लौटने का रास्ता खोज लेते हैं","आप आसानी से माफ़ करते हैं और खुले दिल से प्यार करते हैं; आपको ऐसा साथी चाहिए जो आपकी अच्छाई की क़दर करे, फ़ायदा न उठाए"),
7:("पोषण देने वाले, कर्तव्यनिष्ठ, आध्यात्मिक झुकाव वाले — आपके पास लोग सुरक्षित महसूस करते हैं","आप देखभाल और सेवा से प्यार जताते हैं; आप उस साथी के साथ खिलते हैं जो बदले में देना जानता हो, सिर्फ़ लेना नहीं"),
8:("पैनी नज़र वाले, निजी, गहरे — जो लोग छिपाते हैं, आप देख लेते हैं","आप अपना दिल सँभालकर खोलते हैं; नज़दीकी परत-दर-परत आती है, और धोखा वो एक चीज़ है जो माफ़ नहीं होती"),
9:("शाही, विरासत से जुड़े, स्वाभिमानी — खानदान और विरासत आपके लिए मायने रखते हैं","आप गरिमा से प्यार करते हैं और सम्मान चाहते हैं; साथी की सबके सामने वफ़ादारी उतनी ही मायने रखती है जितना अकेले में प्यार"),
10:("खिलंदड़े, दिलदार, आनंद-प्रेमी — आप हर महफ़िल में गर्मजोशी ले आते हैं","रोमांस, जश्न और लाड़ आपके लिए ज़रूरत हैं, विलासिता नहीं"),
11:("संतुलित, भरोसेमंद, वचन निभाने वाले — आपकी ज़ुबान ही आपका वादा है","आप कमिटमेंट को गंभीरता से लेते हैं और वही उम्मीद रखते हैं; हल्का-फुल्का प्यार आपको रास नहीं आता"),
12:("हुनरमंद, हाज़िरजवाब, जुगाड़ू — चीज़ें भी सुधार देते हैं और रिश्ते भी","आप काम आकर और हँसाकर प्यार जताते हैं; आपको क़दर चाहिए, बड़ा ड्रामा नहीं"),
13:("करिश्माई, कलात्मक, सौंदर्य-प्रेमी — आप बिखराव से भी ख़ूबसूरती गढ़ देते हैं","आपको आकर्षण और चमक खींचती है; सीख बस यह है कि चमक के नीचे ठोसपन देखकर चुनें"),
14:("आज़ाद, ढल जाने वाले, सुलझे हुए — आप अकेले भी सलीक़े से चलते हैं","आपको प्यार के भीतर भी थोड़ी जगह चाहिए; जो साथी हल्के हाथ से थामता है, उसे आप पूरे मिल जाते हैं"),
15:("महत्वाकांक्षी, एकाग्र, दो रंगों वाले — जीत आपकी ज़ुबान पर रहती है","आप मक़सद के साथ प्यार करते हैं; रिश्ता तब चलता है जब आप दोनों मिलकर कुछ बना रहे हों"),
16:("समर्पित, मिलनसार, तालमेल बिठाने वाले — सख़्त माहौल भी आपसे नरम पड़ जाता है","आप गहरे, टिकाऊ रिश्ते के लिए बने हैं; वफ़ादारी आपमें सहज है और बदले में उतनी ही चाहिए भी"),
17:("बड़प्पन वाले, गहरे, रक्षक — ज़िम्मेदारी आपने जल्दी उठा ली","आप अपनों की पूरी शिद्दत से हिफ़ाज़त करते हैं; कवच के नीचे नरमी भी है"),
18:("जड़ तक जाने वाले, सच के खोजी — ऊपरी जवाबों से आपको कभी तसल्ली नहीं होती","प्यार में आप हर बात की जड़ तक जाते हैं; आपकी गहराई उसी को मिलती है जो आपकी साफ़गोई झेल सके"),
19:("अजेय हौसले वाले, स्वाभिमानी, खरे — हर गिरावट के बाद आप फिर उठ खड़े होते हैं","आप पूरे दिल से प्यार करते हैं और अपनी वापसी पर भरोसा चाहते हैं; साथी का शक ही सबसे गहरा चुभता है"),
20:("सबको साथ लेने वाले, उसूलों के पक्के, टिकाऊ — आप धीरे जीतते हैं, पर हमेशा के लिए","आप लंबे सफ़र के लिए जुड़ते हैं; कैमिस्ट्री से ज़्यादा चरित्र देखते हैं — और दोनों मिल जाएँ तो सँजोकर रखते हैं"),
21:("सुनने वाले, ज्ञानी, जोड़ने वाले — ज्ञान आपसे होकर बहता है","आपको दिमाग़ से इश्क़ होता है; बातचीत आपकी नज़दीकी है, और साथ की ख़ामोशी आपका सुकून"),
22:("लय वाले, बड़े दिल वाले, दिलदार — आप कई दुनियाएँ एक ताल में साधे रखते हैं","आपको अपनी महत्वाकांक्षाओं की ताल से मिलता साथी चाहिए; आधे रास्ते कोई मिल जाए तो आप दिल खोलकर देते हैं"),
23:("रहस्यमय, एकांत-प्रिय, भर देने वाले — दुनिया जो तोड़ती है, आप जोड़ देते हैं","आपको सच्ची जगह और सच्ची गहराई दोनों चाहिए; उथली नज़दीकी थका देती है, सच्ची आत्मीयता भर देती है"),
24:("गहरे, बदल देने वाले, भीतर आग लिए — आप जलते भी हैं और फिर से गढ़ते भी हैं","प्यार आपको पूरी तरह बदल देता है; आपको ऐसा साथी चाहिए जो आपकी गहराइयों से न घबराए"),
25:("समझदार, करुणा से भरे, थाम लेने वाले — दूसरों के तूफ़ानों के बाद की शांति","प्यार में ठहराव आप ही हैं; आपकी चुनौती बस यह है कि जो देखभाल आप हमेशा देते हैं, वो माँगना भी सीखें"),
26:("पालने वाले, संपूर्ण, पार ले जाने वाले — अंत और आरंभ आपमें आकर मिलते हैं","आप निःस्वार्थ प्यार करते हैं और गहरे सपने देखते हैं; आपको ऐसा साथी चाहिए जो आपकी कोमलता की हिफ़ाज़त करे")}

# ---- Venus love-style by sign (0-11) ----
VENUS_STYLE = {
0:"direct and impulsive in love — you pursue openly and lose interest in games",
1:"sensory and loyal — love means comfort, food, touch and permanence",
2:"playful and verbal — flirting is conversation, and conversation is intimacy",
3:"protective and emotional — you love like family, deep and enveloping",
4:"grand and warm-hearted — romance should feel like celebration",
5:"careful and devoted — you love through acts of service and quiet standards",
6:"harmonising and partnership-built — you are at your best in a committed pair",
7:"intense and all-or-nothing — you love deeply or not at all",
8:"adventurous and idealistic — love must have meaning and room to roam",
9:"reserved and enduring — slow to open, near-impossible to shake once committed",
10:"unconventional and friendship-first — you love minds and freedom",
11:"romantic and self-giving — you love like poetry, and must guard against over-giving"}

# ---- Wealth: 2nd lord house placement (1-12) — earning pattern ----
WEALTH_2L = ["self-made earning — income tied directly to your own effort and name",
"strong accumulation instinct — money grows when kept close and managed personally",
"earning through skill, communication or courage — income follows initiative",
"asset-building pattern — property, vehicles and home-linked wealth suit you",
"gains through creativity, speculation or teaching — calculated risks can pay",
"earning through service and problem-solving — steady but competitive fields",
"wealth through partnership — business partners and spouse's fortune both matter",
"sudden gains and others' resources — insurance, inheritance, transformation-linked money",
"fortune through knowledge, distance or dharma — earnings rise away from home base",
"career-linked wealth — position and status directly drive income",
"network-scale gains — the larger the circle, the larger the earning",
"earning with expense — money flows in and out; foreign or institutional links help retention"]

# ---- Wealth: 11th lord house placement (1-12) — gains pattern ----
GAINS_11L = ["gains come through personal initiative — you must ask, apply, start",
"gains consolidate through savings and family resources",
"gains through siblings, media, writing or short ventures",
"gains through property, homeland and emotional stability",
"gains through children, students, creativity or markets",
"gains after effort and competition — earned, never gifted",
"gains through partnerships and public dealing",
"gains through deep research, others' money, or sudden turns",
"gains through gurus, higher learning and long journeys",
"gains through career excellence — reputation converts to reward",
"a strong gains signature — networks multiply whatever you build",
"gains that fund growth elsewhere — watch leakage, use it for investment"]

# ---- Health tendencies by 6th-house sign (0-11), classical framing ----
HEALTH_6 = ["heat and head-related tendencies — manage anger and rushing",
"throat and weight-related tendencies — routine and moderation protect you",
"nervous and respiratory sensitivity — rest the mind, breathe deliberately",
"digestive and emotional-somatic links — the stomach mirrors the mood",
"heart and vitality themes — sustainable pace over heroic bursts",
"gut and worry links — precision helps work, hurts sleep; separate them",
"kidney and balance themes — hydration and equilibrium in all things",
"deep-seated and hidden tendencies — regular check-ups over guesswork",
"hip, liver and excess themes — the appetite for more needs a governor",
"joints, knees and chronic patterns — consistency beats intensity",
"circulation and stress themes — movement is your medicine",
"immunity and sleep themes — boundaries protect the body too"]

# ---- Element by sign & pair dynamics ----
SIGN_ELEMENT = ["fire","earth","air","water","fire","earth","air","water","fire","earth","air","water"]
ELEMENT_HI = {"fire":"Agni (fire)","earth":"Prithvi (earth)","air":"Vayu (air)","water":"Jal (water)"}
ELEMENT_PAIR = {
frozenset(["fire"]):"Do fire moons — passion, speed aur honesty double; conflict bhi bright jalta hai par jaldi bujhta hai. Rule seekhiye: ek waqt par ek hi jale.",
frozenset(["earth"]):"Do earth moons — stability, saving, building. Rishta ghar jaisa lagta hai; risk sirf yeh ki routine romance ko na kha jaaye.",
frozenset(["air"]):"Do air moons — baatein kabhi khatam nahi hongi. Mental match excellent; grounding (routine, decisions) ko conscious effort dena hoga.",
frozenset(["water"]):"Do water moons — bina bole samajhna. Emotional depth rare-level ki hai; mood ek dusre par lehron ki tarah aate hain, isliye ek ka calm rehna zaroori.",
frozenset(["fire","earth"]):"Fire + earth — spark aur zameen. Ek raftaar laata hai, doosra thehraav. Fire ko patience, earth ko thodi spontaneity seekhni hogi — phir yeh builder-jodi hai.",
frozenset(["fire","air"]):"Fire + air — hawa aag ko badhaati hai. Energy, plans, adventures — natural chemistry. Dhyaan bas itna: dono udna jaante hain, landing kaun karayega yeh tay kar lo.",
frozenset(["fire","water"]):"Fire + water — bhaap banti hai: intense attraction, intense reactions. Fire ko softness, water ko directness seekhni hogi. Mehnat maangta hai, magic deta hai.",
frozenset(["earth","air"]):"Earth + air — practical milta hai conceptual se. Air ideas laata hai, earth unhe khada karta hai. Pace ka difference hi friction hai, aur wahi complementarity bhi.",
frozenset(["earth","water"]):"Earth + water — mitti aur paani: sabse naturally nourishing pair. Ek security deta hai, doosra depth. Classical texts ise sahaj-anukool maanti hain.",
frozenset(["air","water"]):"Air + water — words milte hain feelings se. Air ko seekhna hoga ki har baat logic nahi hoti; water ko, ki har baat kehni padti hai. Bridge bana toh poetry hai."}

# ---- Couple-voiced koota interpretations: (high, mid, low) per koota ----
KOOTA_TEXT = {
"Varna":("Kaam aur ego ke matters mein aap dono ka natural order milta hai — ghar ke decisions mein tug-of-war kam hoga.",
 "","Kaam-kaaj aur ego ke sawaalon mein role-clarity conscious rakhni hogi — kaun kya lead karta hai, yeh baat-cheet se tay karo, assumption se nahi."),
"Vashya":("Aap dono ka ek dusre par sway balanced hai — koi kisi ko 'chala' nahi raha, dono saath chal rahe hain.",
 "Influence ek taraf thoda zyada hai — jab tak dominant partner ise care se use kare, yeh stability deta hai.",
 "Mutual pull kam hai — matlab rishta convince karne se nahi, respect karne se chalega. Space dena yahan pyaar dikhaane ka tareeka hai."),
"Tara":("Nakshatra-count dono taraf shubh hai — saath rehne se dono ki wellbeing badhti hai, classical texts ise strong protection maanti hain.",
 "Ek direction shubh, ek nahi — ek partner ko rishtey se zyada milta hai. Balance ke liye giving conscious rakhni hogi.",
 "Tara count inauspicious hai — traditionally health/wellbeing par dhyaan. Practical matlab: ek dusre ki sehat aur stress ka khayal is jodi ka zaroori ritual hona chahiye."),
"Yoni":("Instinctive aur physical wavelength naturally milti hai — bina koshish ke comfort, jo har jodi ko naseeb nahi hota.",
 "Physical-instinctive match neutral hai — chemistry banayi ja sakti hai, bas dono ki pace alag ho sakti hai; patience rakho.",
 "Yoni enemy-pair hai — instincts alag chalti hain. Yeh attraction ko nahi rokta, par daily-life habits (sona, uthna, touch, space) mein adjustment maangta hai. Naam se mat daro, pattern samjho."),
"Graha Maitri":("Moon-lords doston mein hain — aap dono ka sochne ka tareeka compatible hai. Behas hogi toh bhi bhasha ek hi hogi.",
 "Moon-lords neutral hain — mental wavelength banti hai shared experiences se. Saath cheezein karo, wavelength khud align hogi.",
 "Moon-lords ki adaawat hai — matlab default sochne ke tareeke alag hain. Iska ilaaj hai 'translate' karna seekhna: partner ki baat ko uske frame mein samajhna, apne mein nahi."),
"Gana":("Temperament same category ka hai — energy levels, social style, gussa-shanti ka pattern milta hai.",
 "Deva-Manushya pairing — ek zyada idealist, ek zyada practical. Achhi jodi, bas expectations ko naam dena seekho.",
 "Gana mismatch hai — temperament genuinely alag hain (jaise ek ko bheed chahiye, ek ko sannata). Yeh deal-breaker nahi, design-brief hai: ghar aisa banao jismein dono modes ki jagah ho."),
"Bhakoot":("Moon-signs ki relative position shubh hai — emotional bond aur family-growth ke liye classical green signal.",
 "","Bhakoot dosha hai — 6-8, 2-12 ya 5-9 ki position. Traditionally emotional distance ya financial friction se joda jaata hai. Cancellation check neeche dekho — aksar lords ki dosti ise cancel kar deti hai."),
"Nadi":("Nadi alag hai — sabse heavy koota clear hai. Classical texts iske liye sabse zyada points isi liye deti hain.",
 "","Nadi same hai — traditionally sabse serious dosha, progeny aur vitality se juda. LEKIN: iske cancellation rules sabse well-defined hain. Neeche ka cancellation-check hi asli verdict hai, yeh zero nahi.")}

# ---- Remedies keyed to 7th lord (classical, agency-first) ----
REMEDY_7L = {
"Sun":("Sunday","Om Ghrini Suryaya Namah","Ruby — only if Sun is well-placed"),
"Moon":("Monday","Om Som Somaya Namah","Pearl — only if Moon is well-placed"),
"Mars":("Tuesday","Om Ang Angarakaya Namah","Red Coral — only if Mars is well-placed"),
"Mercury":("Wednesday","Om Bum Budhaya Namah","Emerald — only if Mercury is well-placed"),
"Jupiter":("Thursday","Om Brim Brihaspataye Namah","Yellow Sapphire — only if Jupiter is well-placed"),
"Venus":("Friday","Om Shum Shukraya Namah","Diamond/White Sapphire — only if Venus is well-placed"),
"Saturn":("Saturday","Om Sham Shanaishcharaya Namah","Blue Sapphire — only after expert trial, if Saturn is well-placed")}

MD_LORD_HI = {"Sun":"Surya","Moon":"Chandra","Mars":"Mangal","Mercury":"Budh",
"Jupiter":"Guru","Venus":"Shukra","Saturn":"Shani","Rahu":"Rahu","Ketu":"Ketu"}

# ---- Remedy note for node (Rahu/Ketu) dasha periods (no classical gemstone here) ----
# REMEDY_7L covers the 7 planets; the nodes get a plain, agency-first note instead.
REMEDY_NODE = {
"Rahu":("Saturday","Om Ram Rahave Namah",
        "No gemstone advised for a Rahu period — keep routines steady and decisions unhurried."),
"Ketu":("Tuesday","Om Kem Ketave Namah",
        "No gemstone advised for a Ketu period — favour clarity, closure and simple habits."),
}

# ---- Manglik guidance: verdict framing + Dos & Don'ts, keyed by manglik.status ----
# Deliberately non-fatalistic. Rendered on the deterministic Manglik pages (no LLM).
MANGLIK_DOSDONTS = {
"non_manglik": {
    "line": "Mars does not sit in a Manglik house from either your Lagna or your Moon, "
            "so the classical Mangal dosha simply does not apply to you.",
    "do": [
        "Answer the question confidently: on this chart, you are not Manglik.",
        "Match on the things that actually last — values, temperament, timing.",
        "Keep the focus on your marriage windows rather than this checkbox.",
    ],
    "dont": [
        "Don't let anyone invent a dosha that your chart does not show.",
        "Don't pay for 'Manglik remedies' you do not need.",
    ],
},
"manglik_cancelled": {
    "line": "Mars is in a Manglik position, but a recognised classical cancellation "
            "applies — so in practice this is treated as effectively non-Manglik.",
    "do": [
        "Understand the cancellation so you can explain it calmly to family.",
        "State it plainly in a match: technically present, classically cancelled.",
        "Weigh compatibility on the whole chart, not this single factor.",
    ],
    "dont": [
        "Don't accept fear-based framing — a cancelled dosha is not a warning.",
        "Don't over-spend on remedies for a dosha that is already neutralised.",
    ],
},
"manglik": {
    "line": "Mars sits in a Manglik house. This is not a curse or a verdict on your "
            "marriage — classical texts treat it as a factor to handle thoughtfully, "
            "and it becomes neutral in a Manglik–Manglik match.",
    "do": [
        "Give the relationship time to mature before big commitments — patience suits this placement.",
        "Consider a partner who is also Manglik, where the factor cancels out.",
        "Channel the Mars energy into shared goals and honest, quick conflict-resolution.",
    ],
    "dont": [
        "Don't panic or treat this as doom — it is common and manageable.",
        "Don't rush into expensive or fear-driven remedies; start with awareness.",
        "Don't let this single factor override an otherwise strong match.",
    ],
},
}

# ---- Weak / quiet period guidance (Component 5). Generic, agency-first actions. ----
WEAK_PERIOD_ACTION = {
    "line": "In a quiet phase, matches may still come but tend not to convert. This is "
            "pattern, not personal failure — and it is the best time to prepare rather than push.",
    "do": [
        "Use the time for clarity — what you actually want in a partner and a life.",
        "Keep your profile current and doors open, without forcing outcomes.",
        "Invest in yourself: health, work, and the conversations with family that make later 'yes' easier.",
    ],
    "dont": [
        "Don't read a slow phase as a closed door — it is a low-activation window, not a verdict.",
        "Don't force a decision that doesn't feel right just because time is passing.",
    ],
}

# ============================================================ VYAPAR (business)
# All tables below are authored, deterministic classical framings for the
# business-growth report (products.compute_vyapar). No LLM, no randomness —
# same style as WEALTH_2L / HEALTH_6 above.

# ---- Business temperament by lagna / moon sign (0-11) ----
# type: the one-line temperament label; work: how they run a business (lagna
# line); gut: money/emotional instinct (moon line); weak: the one weak-spot
# habit; solo: natural leaning ("solo" or "partner").
BIZ_TEMPERAMENT = {
0:{"type":"First-mover operator",
   "work":"you start fast and lead from the front — you'd rather launch and fix than plan and wait",
   "work_short":"You launch fast and fix as you go.",
   "gut":"you buy and sell on instinct and speed; boredom, not risk, is your real enemy",
   "weak":"you start more than you finish — three half-built ventures instead of one completed",
   "solo":"solo"},
1:{"type":"Steady value-builder",
   "work":"you build slowly, hold what you build and compound — patience is your whole edge",
   "work_short":"You build slowly and let it compound.",
   "gut":"you trust tangible assets, stock and cash-in-hand over paper promises",
   "weak":"you hold too long — you miss the exit because letting go feels like loss",
   "solo":"solo"},
2:{"type":"Deal-making communicator",
   "work":"you live on information, contacts and quick turns — you trade ideas as easily as goods",
   "work_short":"You earn on contacts and quick turns.",
   "gut":"you chase many small margins over one big bet; variety keeps you sharp",
   "weak":"you spread thin — too many deals open, none closed all the way",
   "solo":"partner"},
3:{"type":"People-first trader",
   "work":"you build a business like a family — loyalty, care and repeat customers are your moat",
   "work_short":"You win on loyalty and repeat custom.",
   "gut":"your money mood swings with the room; you hoard cash when anxious",
   "weak":"you take business personally — one harsh client can sink a good week",
   "solo":"partner"},
4:{"type":"Brand-led leader",
   "work":"you lead from the front and put your name on it — reputation is your real product",
   "work_short":"You lead up front; your name is the product.",
   "gut":"you spend to look the part; visible success matters as much as the balance sheet",
   "weak":"ego runs the P&L — you resist advice that dents the image",
   "solo":"solo"},
5:{"type":"Systems-and-service operator",
   "work":"you improve everything you touch — process, quality and detail are your advantage",
   "work_short":"You win on process, quality and detail.",
   "gut":"you save carefully and cost every rupee; you distrust flash",
   "weak":"you over-perfect and under-price — you polish while the window closes",
   "solo":"partner"},
6:{"type":"Partnership dealmaker",
   "work":"you think in deals and relationships — you're strongest with the right co-owner beside you",
   "work_short":"You're strongest with the right partner beside you.",
   "gut":"you weigh both sides so long the decision passes; fairness is your instinct",
   "weak":"you avoid the hard 'no' — a bad partner or client stays too long",
   "solo":"partner"},
7:{"type":"All-in strategist",
   "work":"you go deep, play the long game and out-last rivals — you transform a business, not tweak it",
   "work_short":"You play the long game and out-last rivals.",
   "gut":"you keep your cards hidden and your reserves deeper than you admit",
   "weak":"you hold grudges and secrets — control tightens until it chokes growth",
   "solo":"solo"},
8:{"type":"Big-vision expander",
   "work":"you scale on belief and reach — new markets, new places, bigger swings",
   "work_short":"You scale on belief and reach.",
   "gut":"you bet on growth and worry about the details later; optimism is both fuel and trap",
   "weak":"you over-promise and over-extend — the vision outruns the cash",
   "solo":"partner"},
9:{"type":"Long-game builder",
   "work":"you climb in decades, not days — structure, discipline and durable assets are your play",
   "work_short":"You build durable assets over decades.",
   "gut":"you're frugal to a fault and plan for the downside first",
   "weak":"you move too slow and trust too little — caution costs you the early lead",
   "solo":"solo"},
10:{"type":"Unconventional systems-builder",
   "work":"you build at network scale — platforms, communities and models others haven't tried",
   "work_short":"You build at network scale.",
   "gut":"you detach from money emotionally, which helps you take risk but can blur urgency",
   "weak":"you're so early or so different that the market takes years to arrive",
   "solo":"partner"},
11:{"type":"Intuitive creative trader",
   "work":"you flow with the market and sense demand before the data shows it — imagination is your asset",
   "work_short":"You sense demand before the data shows it.",
   "gut":"money slips through easily; you give discounts your margins can't afford",
   "weak":"boundaries blur — you mix generosity with the ledger and lose track",
   "solo":"partner"}}

# ---- Fitting business sector by 10th lord (career-action planet). ----
# label: the line-of-work headline; sub: one-line why; types: 3 business
# families that suit; avoid: what to steer clear of. Keyed by the 7 classical
# planets (sign lords are always one of these).
BIZ_SECTOR_10L = {
"Sun":{"label":"Leadership, Brand or Public-facing work",
  "sub":"your name and authority carry the sale — put yourself in front of the business",
  "sub_short":"Your name and authority carry the sale.",
  "types":[
    {"title":"Premium brand & retail","body":"Building a name-led label — where the brand and your reputation ARE the product."},
    {"title":"Leadership & consulting","body":"Advisory, management or a firm run under your own name and standing."},
    {"title":"Civic & institution-facing supply","body":"Government-linked contracts, public projects and authority-facing trade."}],
  "avoid":"silent-partner roles where your name is hidden — you underperform out of the spotlight"},
"Moon":{"label":"Public, Food or Care businesses",
  "sub":"you thrive serving the everyday needs of ordinary people, with repeat custom",
  "sub_short":"You thrive on everyday needs and repeat custom.",
  "types":[
    {"title":"Food & daily essentials","body":"FMCG, groceries, restaurants — steady demand that renews every day."},
    {"title":"Care, wellness & hospitality","body":"Services that look after people — health, comfort, guest-facing work."},
    {"title":"Public-facing retail","body":"Shops and outlets built on loyalty and repeat customers, not one-off deals."}],
  "avoid":"cold, purely transactional B2B where relationships don't compound over time"},
"Mars":{"label":"Technical, Property or Competitive trades",
  "sub":"you win where energy, skill and nerve decide the outcome",
  "sub_short":"You win where skill and nerve decide it.",
  "types":[
    {"title":"Engineering & manufacturing","body":"Tools, machinery, workshops — hands-on trades that reward technical skill."},
    {"title":"Real estate & construction","body":"Building, developing and dealing in property and land."},
    {"title":"High-competition trades","body":"Sports, security, or fast trading — arenas where drive and nerve pay."}],
  "avoid":"slow, consensus-heavy partnerships that blunt your drive and pace"},
"Mercury":{"label":"Trade, Communication or Advisory",
  "sub":"buying-selling, information and quick turns are your natural home",
  "sub_short":"Buying, selling and quick turns suit you.",
  "types":[
    {"title":"Trading & distribution","body":"Wholesale, import-export, dealerships — margin on movement and turnover."},
    {"title":"Media & communication","body":"Content, marketing, publishing and communication-led services."},
    {"title":"Advisory & brokerage","body":"Accounting, agency, consulting and brokerage — you sell know-how and access."}],
  "avoid":"capital-heavy, slow-cycle businesses that punish your restlessness"},
"Jupiter":{"label":"Advisory, Education or Finance",
  "sub":"knowledge, trust and counsel are what people pay you for",
  "sub_short":"People pay you for knowledge and trust.",
  "types":[
    {"title":"Education & training","body":"Coaching, courses, institutes — turning what you know into a business."},
    {"title":"Finance & consulting","body":"Advisory, wealth, finance — trades built on expertise and trust."},
    {"title":"Publishing, law & ethics-led trade","body":"Reputation-first enterprises where integrity is the moat."}],
  "avoid":"grey-area, cut-corner trades — reputational risk hits you hardest of all"},
"Venus":{"label":"Creative, Luxury or Lifestyle trade",
  "sub":"beauty, comfort and taste are what you sell best",
  "sub_short":"You sell beauty, comfort and taste best.",
  "types":[
    {"title":"Fashion, jewellery & beauty","body":"Luxury and lifestyle goods where aesthetics drive the price."},
    {"title":"Design, arts & events","body":"Creative services, entertainment and experience-led businesses."},
    {"title":"Hospitality & lifestyle retail","body":"Wellness, décor, fine dining — selling comfort and refinement."}],
  "avoid":"grim, aesthetic-blind commodity trades that drain your spark"},
"Saturn":{"label":"Manufacturing, Infrastructure or Long-cycle trade",
  "sub":"you build slow, durable machines that pay out for decades",
  "sub_short":"You build slow, durable, decades-long value.",
  "types":[
    {"title":"Manufacturing & supply chain","body":"Heavy industry, production and the long backbone of the economy."},
    {"title":"Infrastructure & raw materials","body":"Real estate, mining, materials — patient capital, durable returns."},
    {"title":"Long-contract service","body":"Labour-led and long-tenure service businesses that compound over years."}],
  "avoid":"fast-fashion, hype-driven bets — you compound, you don't sprint"}}

# ---- Partnership read by 7th lord (partner/other-party planet). ----
BIZ_PARTNERSHIP_7L = {
"Sun":{"verdict":"Partner only with a clear pecking order",
  "verdict_short":"Partner only with a clear pecking order.",
  "blessing":"a partner adds reach and public weight to your name",
  "caution":"two egos, one throne — power struggles surface if roles blur",
  "who":"someone senior or complementary who won't compete for the spotlight"},
"Moon":{"verdict":"Partnership suits you emotionally",
  "verdict_short":"Partnership suits you emotionally.",
  "blessing":"a trusted partner steadies your moods and shares the daily load",
  "caution":"you pick partners with your heart — vet them with your head too",
  "who":"a calm, loyal partner who grounds your swings"},
"Mars":{"verdict":"Partner with caution — you run hot",
  "verdict_short":"Partner with caution — you run hot.",
  "blessing":"the right co-founder matches your drive and pace",
  "caution":"friction and control fights are the real risk here",
  "who":"a disciplined partner who absorbs your intensity, not one who feeds it"},
"Mercury":{"verdict":"Partnership is a natural fit",
  "verdict_short":"Partnership is a natural fit.",
  "blessing":"a partner covers the follow-through you tend to skip",
  "caution":"keep every term in writing — loose deals sour good friendships",
  "who":"a detail-strong, steady partner to balance your quick mind"},
"Jupiter":{"verdict":"Partnership is favoured and fortunate",
  "verdict_short":"Partnership is favoured and fortunate.",
  "blessing":"a good partner multiplies trust and opens doors",
  "caution":"your generosity can be over-trusting — verify before you commit",
  "who":"an honest, values-aligned partner who shares the vision"},
"Venus":{"verdict":"Partnership is one of your strengths",
  "verdict_short":"Partnership is one of your strengths.",
  "blessing":"you're at your best paired — shared taste and harmony compound",
  "caution":"you avoid hard conversations, so a bad partner lingers too long",
  "who":"an equal with complementary skills and matching standards"},
"Saturn":{"verdict":"Go solo, or partner very carefully",
  "verdict_short":"Go solo, or partner very carefully.",
  "blessing":"a disciplined partner can shoulder a heavy, slow build with you",
  "caution":"delays and mistrust strain partnerships; loyalty is tested by time",
  "who":"a proven, patient partner earned over years — not a quick handshake"}}

# ---- Business obstacle by afflicting planet (paired with REMEDY_7L / REMEDY_NODE). ----
BIZ_OBSTACLE = {
"Sun":"authority clashes and ego-driven calls that stall the business",
"Moon":"mood-driven decisions and an unstable cash-mood cycle",
"Mars":"conflict, haste and burnt bridges with partners or staff",
"Mercury":"scattered focus — too many deals, weak follow-through",
"Jupiter":"over-optimism and over-extension beyond what the cash allows",
"Venus":"over-spending on comfort and image, leaving margins thin",
"Saturn":"delay, slow cash cycles and self-doubt that freezes decisions",
"Rahu":"restless over-reach and shortcut temptation that invites risk",
"Ketu":"detachment and half-hearted follow-through that stalls momentum"}

# ---- Business meaning of a mahadasha / antardasha period, by lord. ----
# tone feeds the good/warn/neutral verdicts and the strong-window search.
BIZ_DASHA = {
"Sun":{"tone":"neutral","body":"authority, visibility and standing in your own name — good for brand, slower for pure trade","body_short":"Authority and standing in your own name."},
"Moon":{"tone":"good","body":"public connection and steady demand — a people-and-cashflow phase","body_short":"Public connection and steady demand."},
"Mars":{"tone":"warn","body":"drive and competition run high, but haste and conflict can cost you","body_short":"Drive runs high, but haste can cost you."},
"Mercury":{"tone":"good","body":"commerce, deals and communication — intellect turns straight into income","body_short":"Deals and communication turn into income."},
"Jupiter":{"tone":"good","body":"expansion, trust and new markets — doors open through knowledge and reputation","body_short":"Expansion, trust and new markets open."},
"Venus":{"tone":"good","body":"comfort, creativity and wealth-enjoyment — earnings and lifestyle both rise","body_short":"Earnings and lifestyle both rise."},
"Saturn":{"tone":"warn","body":"a slow, disciplined grind — durable if you endure, but gains come late and hard","body_short":"A slow grind — gains come late and hard."},
"Rahu":{"tone":"neutral","body":"ambitious, unconventional rise — fast growth, but restless and risk-prone","body_short":"Fast growth, but restless and risk-prone."},
"Ketu":{"tone":"warn","body":"detachment and endings — a phase to simplify and cut, not to expand","body_short":"A phase to simplify and cut, not expand."}}

# planets whose dasha is a strongly benefic business turning-window
BENEFIC_BIZ = ("Jupiter", "Venus", "Mercury", "Moon")

# generic action guidance for the strong window and the careful phases
STRONG_WINDOW_DO = [
    "Launch, expand or raise capital in this window — the wind is behind you.",
    "Lock in your best clients and long contracts while trust is high.",
    "Reinvest early gains into the business rather than spending them."]
STRONG_WINDOW_DONT = [
    "Don't sit idle waiting for perfect — this window rewards decisive action.",
    "Don't over-leverage on the optimism; always keep a working reserve."]


# =====================================================================
# Devanagari (Hindi) twins of the five business-astrology tables above.
# Same keys / structure as their English source dicts — only the human-
# readable prose values are translated. Logic tokens ("solo"/"partner"
# in BIZ_TEMPERAMENT, and the "tone" enums in BIZ_DASHA) are left as-is.
# Used by the Vyapar Hindi funnel to show Devanagari teaser values,
# mirroring how compatibility uses NAK_PROFILE_HI.
# =====================================================================

BIZ_TEMPERAMENT_HI = {
0: {"type":"सबसे पहले क़दम रखने वाला संचालक","solo":"solo",
    "work":"आप तेज़ी से शुरू करते हैं और आगे रहकर अगुआई करते हैं — योजना बनाकर इंतज़ार करने के बजाय आप शुरू करके सुधारना पसंद करते हैं",
    "work_short_hi":"आप तेज़ शुरू करते हैं और आगे रहकर अगुआई करते हैं।",
    "gut":"आप सहज-समझ और रफ़्तार से ख़रीदते-बेचते हैं; आपका असली दुश्मन जोखिम नहीं, ऊब है",
    "weak":"आप ख़त्म करने से ज़्यादा शुरू करते हैं — एक पूरे किए काम के बजाय तीन अधूरे उद्यम"},
1: {"type":"धीरज से मूल्य बनाने वाला","solo":"solo",
    "work":"आप धीरे-धीरे बनाते हैं, जो बनाते हैं उसे थामे रखते हैं और बढ़ाते हैं — धीरज ही आपकी पूरी बढ़त है",
    "work_short_hi":"आप धीरे-धीरे बनाते हैं और टिकाकर बढ़ाते हैं।",
    "gut":"आप काग़ज़ी वादों से ज़्यादा ठोस संपत्ति, माल और हाथ में मौजूद नक़दी पर भरोसा करते हैं",
    "weak":"आप बहुत देर तक थामे रहते हैं — छोड़ना नुक़सान जैसा लगता है, इसलिए निकलने का मौक़ा चूक जाते हैं"},
2: {"type":"सौदे करने वाला संचार-कुशल व्यापारी","solo":"partner",
    "work":"आप जानकारी, संपर्कों और तेज़ लेन-देन पर जीते हैं — आप विचारों का व्यापार माल जितनी ही आसानी से करते हैं",
    "work_short_hi":"आप संपर्कों और तेज़ लेन-देन से कमाते हैं।",
    "gut":"आप एक बड़े दांव के बजाय कई छोटे मुनाफ़ों के पीछे भागते हैं; विविधता आपको चुस्त रखती है",
    "weak":"आप बहुत जगह बँट जाते हैं — बहुत सारे सौदे खुले, कोई पूरी तरह बंद नहीं"},
3: {"type":"लोगों को पहले रखने वाला व्यापारी","solo":"partner",
    "work":"आप कारोबार को परिवार की तरह बनाते हैं — वफ़ादारी, देखभाल और बार-बार लौटने वाले ग्राहक आपकी सुरक्षा-दीवार हैं",
    "work_short_hi":"आप ग्राहक को परिवार जैसा जोड़कर चलते हैं।",
    "gut":"पैसे को लेकर आपका मिज़ाज माहौल के साथ बदलता है; घबराहट में आप नक़दी जमा करने लगते हैं",
    "weak":"आप कारोबार को दिल पर ले लेते हैं — एक कठोर ग्राहक अच्छे-भले हफ़्ते को डुबो सकता है"},
4: {"type":"ब्रांड से चलने वाला अगुआ","solo":"solo",
    "work":"आप आगे रहकर अगुआई करते हैं और अपना नाम उस पर लगाते हैं — साख ही आपका असली उत्पाद है",
    "work_short_hi":"आप आगे रहकर अपने नाम से कारोबार चलाते हैं।",
    "gut":"आप दिखावे के लिए ख़र्च करते हैं; दिखने वाली कामयाबी आपके लिए बही-खाते जितनी ही मायने रखती है",
    "weak":"अहं आपके नफ़े-नुक़सान को चलाता है — जो सलाह आपकी छवि को ठेस पहुँचाए, उसे आप ठुकरा देते हैं"},
5: {"type":"व्यवस्था-और-सेवा वाला संचालक","solo":"partner",
    "work":"आप जिस भी चीज़ को छूते हैं उसे बेहतर बनाते हैं — तरीक़ा, गुणवत्ता और बारीकी आपकी बढ़त हैं",
    "work_short_hi":"आप हर काम को तरीक़े और बारीकी से बेहतर बनाते हैं।",
    "gut":"आप सोच-समझकर बचत करते हैं और हर रुपये का हिसाब रखते हैं; दिखावे पर आपको भरोसा नहीं",
    "weak":"आप ज़रूरत से ज़्यादा परिपूर्ण बनाते हैं और दाम कम रखते हैं — आप सँवारते रहते हैं और मौक़ा हाथ से निकल जाता है"},
6: {"type":"साझेदारी में सौदे करने वाला","solo":"partner",
    "work":"आप सौदों और रिश्तों में सोचते हैं — सही सह-मालिक आपके साथ हो तो आप सबसे मज़बूत होते हैं",
    "work_short_hi":"आप सौदों और रिश्तों में सोचते हैं — साथी के साथ मज़बूत।",
    "gut":"आप दोनों पक्षों को इतनी देर तौलते हैं कि फ़ैसले का वक़्त निकल जाता है; निष्पक्षता आपकी सहज-समझ है",
    "weak":"आप कड़ा 'ना' कहने से बचते हैं — ग़लत साझेदार या ग्राहक बहुत देर तक टिका रहता है"},
7: {"type":"पूरा दांव लगाने वाला रणनीतिकार","solo":"solo",
    "work":"आप गहराई में जाते हैं, लंबी बाज़ी खेलते हैं और प्रतिद्वंद्वियों से ज़्यादा टिकते हैं — आप कारोबार में मामूली फेरबदल नहीं, कायापलट करते हैं",
    "work_short_hi":"आप गहराई और लंबी बाज़ी में सबसे मज़बूत होते हैं।",
    "gut":"आप अपने पत्ते छिपाकर रखते हैं और आपका भंडार आपके बताए से ज़्यादा गहरा होता है",
    "weak":"आप रंजिश और राज़ थामे रखते हैं — नियंत्रण इतना कसता जाता है कि वह बढ़त का गला घोंट देता है"},
8: {"type":"बड़ी सोच वाला विस्तारक","solo":"partner",
    "work":"आप विश्वास और पहुँच के बल पर फैलते हैं — नए बाज़ार, नई जगहें, बड़े दांव",
    "work_short_hi":"आप भरोसे और पहुँच के बल पर फैलते हैं।",
    "gut":"आप बढ़त पर दांव लगाते हैं और बारीकियों की चिंता बाद में करते हैं; उम्मीद आपका ईंधन भी है और जाल भी",
    "weak":"आप ज़रूरत से ज़्यादा वादे और फैलाव कर लेते हैं — सोच नक़दी से आगे निकल जाती है"},
9: {"type":"लंबी बाज़ी का निर्माता","solo":"solo",
    "work":"आप दिनों में नहीं, दशकों में ऊपर चढ़ते हैं — ढाँचा, अनुशासन और टिकाऊ संपत्ति आपका दांव हैं",
    "work_short_hi":"आप सालों में ढाँचा और टिकाऊ संपत्ति बनाते हैं।",
    "gut":"आप हद से ज़्यादा किफ़ायती हैं और पहले नुक़सान की आशंका के लिए योजना बनाते हैं",
    "weak":"आप बहुत धीरे चलते हैं और बहुत कम भरोसा करते हैं — सावधानी आपसे शुरुआती बढ़त छीन लेती है"},
10: {"type":"लीक से हटकर व्यवस्था बनाने वाला","solo":"partner",
     "work":"आप नेटवर्क के पैमाने पर बनाते हैं — मंच, समुदाय और ऐसे मॉडल जो औरों ने आज़माए नहीं",
     "work_short_hi":"आप नेटवर्क के पैमाने पर नई व्यवस्था बनाते हैं।",
     "gut":"आप पैसे से भावनात्मक रूप से अलग रहते हैं, जिससे जोखिम लेना आसान होता है पर ज़रूरी तेज़ी धुँधली पड़ सकती है",
     "weak":"आप इतने पहले या इतने अलग होते हैं कि बाज़ार को पहुँचने में सालों लग जाते हैं"},
11: {"type":"सहज-समझ वाला रचनात्मक व्यापारी","solo":"partner",
     "work":"आप बाज़ार के साथ बहते हैं और आँकड़ों के दिखने से पहले माँग को भाँप लेते हैं — कल्पनाशीलता आपकी पूँजी है",
     "work_short_hi":"आप माँग को पहले भाँप लेते हैं — कल्पना आपकी पूँजी है।",
     "gut":"पैसा आसानी से फिसल जाता है; आप ऐसी छूट दे देते हैं जो आपका मुनाफ़ा सह नहीं सकता",
     "weak":"हदें धुँधली पड़ जाती हैं — आप उदारता को बही-खाते से मिला देते हैं और हिसाब खो बैठते हैं"}}

BIZ_SECTOR_10L_HI = {
"Jupiter": {"label":"सलाह, शिक्षा या वित्त",
            "sub":"ज्ञान, भरोसा और सलाह — इन्हीं के लिए लोग आपको पैसे देते हैं",
            "sub_short_hi":"ज्ञान, भरोसा और सलाह के लिए लोग आपको पैसे देते हैं।",
            "avoid":"संदिग्ध, कोना-काटने वाले सौदे — साख का जोखिम आप पर सबसे ज़्यादा भारी पड़ता है",
            "types":[{"title":"शिक्षा और प्रशिक्षण",
                      "body":"कोचिंग, पाठ्यक्रम, संस्थान — जो आप जानते हैं उसे कारोबार में बदलना।"},
                     {"title":"वित्त और परामर्श",
                      "body":"सलाह, धन-प्रबंधन, वित्त — विशेषज्ञता और भरोसे पर टिके सौदे।"},
                     {"title":"प्रकाशन, क़ानून और नैतिकता-प्रधान व्यापार",
                      "body":"साख को सबसे आगे रखने वाले उद्यम, जहाँ ईमानदारी ही सुरक्षा-दीवार है।"}]},
"Mars": {"label":"तकनीकी, संपत्ति या मुक़ाबले वाले काम",
         "sub":"आप वहाँ जीतते हैं जहाँ ऊर्जा, हुनर और हिम्मत नतीजा तय करते हैं",
         "sub_short_hi":"जहाँ हुनर और हिम्मत नतीजा तय करें, वहाँ आप जीतते हैं।",
         "avoid":"धीमी, हर बात पर सहमति माँगने वाली साझेदारियाँ जो आपके जोश और रफ़्तार को कुंद कर दें",
         "types":[{"title":"इंजीनियरिंग और विनिर्माण",
                   "body":"औज़ार, मशीनें, कार्यशालाएँ — हाथ से किए जाने वाले काम जो तकनीकी हुनर को फल देते हैं।"},
                  {"title":"अचल संपत्ति और निर्माण",
                   "body":"संपत्ति और ज़मीन को बनाना, विकसित करना और उसमें लेन-देन।"},
                  {"title":"कड़े मुक़ाबले वाले काम",
                   "body":"खेल, सुरक्षा, या तेज़ ट्रेडिंग — ऐसे मैदान जहाँ जोश और हिम्मत का फल मिलता है।"}]},
"Mercury": {"label":"व्यापार, संचार या सलाह",
            "sub":"ख़रीद-बिक्री, जानकारी और तेज़ लेन-देन आपका स्वाभाविक ठिकाना हैं",
            "sub_short_hi":"ख़रीद-बिक्री और तेज़ लेन-देन आपका सहज ठिकाना है।",
            "avoid":"भारी पूँजी वाले, धीमे चक्र के कारोबार जो आपकी बेचैनी को सज़ा देते हैं",
            "types":[{"title":"व्यापार और वितरण",
                      "body":"थोक, आयात-निर्यात, डीलरशिप — माल की आवाजाही और बिक्री पर मुनाफ़ा।"},
                     {"title":"मीडिया और संचार",
                      "body":"कंटेंट, मार्केटिंग, प्रकाशन और संचार-प्रधान सेवाएँ।"},
                     {"title":"सलाह और दलाली",
                      "body":"लेखा, एजेंसी, परामर्श और दलाली — आप जानकारी और पहुँच बेचते हैं।"}]},
"Moon": {"label":"जन-सेवा, खाना या देखभाल का कारोबार",
         "sub":"आप आम लोगों की रोज़मर्रा की ज़रूरतें पूरी करते हुए फलते-फूलते हैं, जहाँ ग्राहक बार-बार लौटते हैं",
         "sub_short_hi":"रोज़मर्रा की ज़रूरतें पूरी करने में आप फलते हैं।",
         "avoid":"ठंडे, महज़ लेन-देन वाले B2B सौदे जहाँ रिश्ते समय के साथ गहरे नहीं होते",
         "types":[{"title":"खाना और रोज़मर्रा की ज़रूरतें",
                   "body":"एफएमसीजी, किराना, रेस्तराँ — ऐसी स्थिर माँग जो हर रोज़ नई होती है।"},
                  {"title":"देखभाल, तंदुरुस्ती और आतिथ्य",
                   "body":"लोगों की देखभाल करने वाली सेवाएँ — स्वास्थ्य, आराम, मेहमानों से जुड़ा काम।"},
                  {"title":"जनता से जुड़ी दुकानदारी",
                   "body":"वफ़ादारी और बार-बार लौटने वाले ग्राहकों पर टिकी दुकानें और आउटलेट, न कि एक-बार के सौदे।"}]},
"Saturn": {"label":"निर्माण, बुनियादी ढाँचा या लंबी-अवधि का कारोबार",
           "sub":"आप धीमे पर टिकाऊ तंत्र बनाते हैं जो दशकों तक कमाई देते हैं",
           "sub_short_hi":"आप धीमे पर टिकाऊ तंत्र बनाते हैं जो सालों कमाते हैं।",
           "avoid":"तेज़-फ़ैशन, हो-हल्ले से चलने वाले दांव — आप धीरे-धीरे बढ़ते हैं, दौड़ नहीं लगाते",
           "types":[{"title":"विनिर्माण और आपूर्ति शृंखला",
                     "body":"भारी उद्योग, उत्पादन और अर्थव्यवस्था की लंबी रीढ़।"},
                    {"title":"बुनियादी ढाँचा और कच्चा माल",
                     "body":"अचल संपत्ति, खनन, सामग्री — धैर्यवान पूँजी, टिकाऊ मुनाफ़ा।"},
                    {"title":"लंबे अनुबंध वाली सेवा",
                     "body":"श्रम-प्रधान और लंबी अवधि वाले सेवा-कारोबार जो सालों में बढ़ते हैं।"}]},
"Sun": {"label":"नेतृत्व, ब्रांड या जन-सामने का काम",
        "sub":"आपका नाम और रुतबा बिक्री को आगे ले जाते हैं — ख़ुद को कारोबार के सामने रखें",
        "sub_short_hi":"आपका नाम और रुतबा बिक्री को आगे ले जाते हैं।",
        "avoid":"मूक-साझेदार की भूमिकाएँ जहाँ आपका नाम छिपा रहे — सुर्ख़ियों से दूर आप कमज़ोर प्रदर्शन करते हैं",
        "types":[{"title":"प्रीमियम ब्रांड और खुदरा",
                  "body":"नाम से चलने वाला लेबल बनाना — जहाँ ब्रांड और आपकी साख ही उत्पाद हैं।"},
                 {"title":"नेतृत्व और परामर्श",
                  "body":"सलाह, प्रबंधन या आपके अपने नाम और रुतबे पर चलने वाली फ़र्म।"},
                 {"title":"सरकारी और संस्थानों से जुड़ी आपूर्ति",
                  "body":"सरकार से जुड़े अनुबंध, सार्वजनिक परियोजनाएँ और प्रशासन से जुड़ा व्यापार।"}]},
"Venus": {"label":"रचनात्मक, विलासिता या लाइफ़स्टाइल का कारोबार",
          "sub":"सुंदरता, आराम और अभिरुचि — इन्हें आप सबसे अच्छा बेचते हैं",
          "sub_short_hi":"सुंदरता, आराम और अभिरुचि आप सबसे अच्छा बेचते हैं।",
          "avoid":"नीरस, सौंदर्य से अनजान वस्तु-व्यापार जो आपकी चमक सोख लेते हैं",
          "types":[{"title":"फ़ैशन, आभूषण और सौंदर्य",
                    "body":"विलासिता और लाइफ़स्टाइल की वस्तुएँ जहाँ सुंदरता दाम तय करती है।"},
                   {"title":"डिज़ाइन, कला और आयोजन",
                    "body":"रचनात्मक सेवाएँ, मनोरंजन और अनुभव-प्रधान कारोबार।"},
                   {"title":"आतिथ्य और लाइफ़स्टाइल खुदरा",
                    "body":"तंदुरुस्ती, सजावट, बढ़िया भोजन — आराम और नफ़ासत बेचना।"}]}}

BIZ_PARTNERSHIP_7L_HI = {
"Jupiter": {"verdict":"साझेदारी अनुकूल और भाग्यशाली है",
            "verdict_short_hi":"साझेदारी आपके लिए अच्छी और भाग्यशाली है।",
            "blessing":"अच्छा साझेदार भरोसे को कई गुना करता है और रास्ते खोलता है",
            "caution":"आपकी उदारता कभी-कभी हद से ज़्यादा भरोसे में बदल जाती है — वचन देने से पहले जाँच लें",
            "who":"एक ईमानदार, समान मूल्यों वाला साझेदार जो आपकी सोच में हिस्सेदार हो"},
"Mars": {"verdict":"सावधानी से साझेदारी करें — आपका मिज़ाज गरम रहता है",
         "verdict_short_hi":"साझेदारी सोच-समझकर करें — मिज़ाज गरम रहता है।",
         "blessing":"सही सह-संस्थापक आपके जोश और रफ़्तार से मेल खाता है",
         "caution":"यहाँ असली जोखिम टकराव और नियंत्रण की लड़ाइयों का है",
         "who":"एक अनुशासित साझेदार जो आपकी तीव्रता को सँभाल ले, न कि उसे और भड़काए"},
"Mercury": {"verdict":"साझेदारी आपके लिए स्वाभाविक रूप से उपयुक्त है",
            "verdict_short_hi":"साझेदारी आपको स्वाभाविक रूप से रास आती है।",
            "blessing":"साझेदार उस पूर्ति को सँभाल लेता है जिसे आप अक्सर छोड़ देते हैं",
            "caution":"हर शर्त लिखित में रखें — ढीले सौदे अच्छी दोस्तियों को बिगाड़ देते हैं",
            "who":"बारीकियों में मज़बूत, धीरजवाला साझेदार जो आपके तेज़ दिमाग़ को संतुलित करे"},
"Moon": {"verdict":"साझेदारी आपको भावनात्मक रूप से रास आती है",
         "verdict_short_hi":"साझेदारी आपके मन को रास आती है।",
         "blessing":"भरोसेमंद साझेदार आपके मिज़ाज को स्थिर करता है और रोज़ का बोझ बाँटता है",
         "caution":"आप साझेदार दिल से चुनते हैं — उन्हें दिमाग़ से भी परखें",
         "who":"एक शांत, वफ़ादार साझेदार जो आपके उतार-चढ़ाव को थामे"},
"Saturn": {"verdict":"अकेले चलें, या बहुत सावधानी से साझेदारी करें",
           "verdict_short_hi":"अकेले चलें, या बहुत सावधानी से साझेदारी करें।",
           "blessing":"अनुशासित साझेदार आपके साथ भारी, धीमे निर्माण का बोझ उठा सकता है",
           "caution":"देरी और अविश्वास साझेदारियों पर दबाव डालते हैं; वफ़ादारी की परीक्षा समय लेता है",
           "who":"एक परखा हुआ, धीरजवाला साझेदार जो सालों में कमाया गया हो — न कि झटपट का हाथ मिलाना"},
"Sun": {"verdict":"साझेदारी तभी करें जब पद-क्रम साफ़ हो",
        "verdict_short_hi":"साझेदारी तभी करें जब भूमिकाएँ साफ़ हों।",
        "blessing":"साझेदार आपके नाम में पहुँच और सार्वजनिक वज़न जोड़ता है",
        "caution":"दो अहं, एक सिंहासन — भूमिकाएँ धुँधली हों तो सत्ता की खींचतान उभर आती है",
        "who":"कोई वरिष्ठ या पूरक व्यक्ति जो सुर्ख़ियों के लिए आपसे होड़ न करे"},
"Venus": {"verdict":"साझेदारी आपकी ताक़तों में से एक है",
          "verdict_short_hi":"साझेदारी आपकी ताक़तों में से एक है।",
          "blessing":"आप जोड़ी में सबसे बेहतर होते हैं — साझा अभिरुचि और तालमेल बढ़ते जाते हैं",
          "caution":"आप कठिन बातचीत से बचते हैं, इसलिए ग़लत साझेदार बहुत देर तक टिका रहता है",
          "who":"एक बराबरी का साथी जिसके हुनर पूरक हों और स्तर आपसे मेल खाता हो"}}

BIZ_OBSTACLE_HI = {
"Sun":"रुतबे की टक्करें और अहं से लिए गए फ़ैसले जो कारोबार को रोक देते हैं",
"Moon":"मिज़ाज से चलने वाले फ़ैसले और नक़दी-मिज़ाज का अस्थिर चक्र",
"Mars":"टकराव, जल्दबाज़ी और साझेदारों या कर्मचारियों से बिगड़े रिश्ते",
"Mercury":"बिखरा हुआ ध्यान — बहुत सारे सौदे, कमज़ोर पूर्ति",
"Jupiter":"हद से ज़्यादा उम्मीद और नक़दी की इजाज़त से आगे का फैलाव",
"Venus":"आराम और छवि पर हद से ज़्यादा ख़र्च, जिससे मुनाफ़ा पतला रह जाता है",
"Saturn":"देरी, धीमे नक़दी-चक्र और आत्म-संदेह जो फ़ैसलों को जकड़ देता है",
"Rahu":"बेचैन हद-पार पहुँच और छोटे रास्तों का लालच जो जोखिम को न्योता देता है",
"Ketu":"उदासीनता और अधूरे मन से की गई पूर्ति जो गति को रोक देती है"}

BIZ_DASHA_HI = {
"Sun":{"tone":"neutral","body":"अधिकार, पहचान और अपने नाम की साख — ब्रांड के लिए अच्छा, सीधे व्यापार के लिए धीमा","body_short_hi":"नाम-साख को बल, व्यापार में धीमा।"},
"Moon":{"tone":"good","body":"जनता से जुड़ाव और लगातार माँग — लोगों-और-नक़दी का दौर","body_short_hi":"जनता से जुड़ाव और लगातार माँग।"},
"Mars":{"tone":"warn","body":"जोश और मुक़ाबला ऊँचा रहता है, पर जल्दबाज़ी और टकराव भारी पड़ सकते हैं","body_short_hi":"जोश ऊँचा, पर जल्दबाज़ी भारी पड़े।"},
"Mercury":{"tone":"good","body":"व्यापार, सौदे और संचार — बुद्धि सीधे आमदनी में बदलती है","body_short_hi":"व्यापार और सौदे, बुद्धि से कमाई।"},
"Jupiter":{"tone":"good","body":"फैलाव, भरोसा और नए बाज़ार — ज्ञान और साख से दरवाज़े खुलते हैं","body_short_hi":"फैलाव, भरोसा और नए बाज़ार।"},
"Venus":{"tone":"good","body":"आराम, रचनात्मकता और धन का सुख — कमाई और जीवनशैली दोनों बढ़ती हैं","body_short_hi":"कमाई और जीवनशैली दोनों बढ़ें।"},
"Saturn":{"tone":"warn","body":"धीमी, अनुशासित मेहनत — टिकाऊ अगर आप सह लें, पर फ़ायदा देर से और मुश्किल से आता है","body_short_hi":"धीमी मेहनत, फल देर से आता है।"},
"Rahu":{"tone":"neutral","body":"महत्वाकांक्षी, लीक से हटकर उठान — तेज़ बढ़त, पर बेचैन और जोखिम-भरी","body_short_hi":"तेज़ पर बेचैन और जोखिम-भरी उठान।"},
"Ketu":{"tone":"warn","body":"अलगाव और अंत — सरल करने और काटने का दौर, फैलाने का नहीं","body_short_hi":"सरल करने और काटने का दौर।"}}
