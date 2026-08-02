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
"Sun":("Ravivar (Sunday)","Om Ghrini Suryaya Namah","Ruby (Manik) — only if Sun is well-placed"),
"Moon":("Somvar (Monday)","Om Som Somaya Namah","Pearl (Moti) — only if Moon is well-placed"),
"Mars":("Mangalvar (Tuesday)","Om Ang Angarakaya Namah","Red Coral (Moonga) — only if Mars is well-placed"),
"Mercury":("Budhvar (Wednesday)","Om Bum Budhaya Namah","Emerald (Panna) — only if Mercury is well-placed"),
"Jupiter":("Guruvar (Thursday)","Om Brim Brihaspataye Namah","Yellow Sapphire (Pukhraj) — only if Jupiter is well-placed"),
"Venus":("Shukravar (Friday)","Om Shum Shukraya Namah","Diamond/White Sapphire — only if Venus is well-placed"),
"Saturn":("Shanivar (Saturday)","Om Sham Shanaishcharaya Namah","Blue Sapphire (Neelam) — only after expert trial, if Saturn is well-placed")}

MD_LORD_HI = {"Sun":"Surya","Moon":"Chandra","Mars":"Mangal","Mercury":"Budh",
"Jupiter":"Guru","Venus":"Shukra","Saturn":"Shani","Rahu":"Rahu","Ketu":"Ketu"}

# ---- Remedy note for node (Rahu/Ketu) dasha periods (no classical gemstone here) ----
# REMEDY_7L covers the 7 planets; the nodes get a plain, agency-first note instead.
REMEDY_NODE = {
"Rahu":("Shanivar (Saturday)","Om Ram Rahave Namah",
        "No gemstone advised for a Rahu period — keep routines steady and decisions unhurried."),
"Ketu":("Mangalvar (Tuesday)","Om Kem Ketave Namah",
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
