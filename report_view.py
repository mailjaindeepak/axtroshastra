"""
Axtroshastra report renderer — 9-page mobile-first report from engine JSON.
Deterministic templates only; every fact comes from the payload.
LLM narrative layer can later replace individual section texts via the same slots.
"""
import json
from datetime import datetime
from html import escape
import report_addons  # escape user-supplied fields (name/place) before HTML interpolation

SIGNS = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
         "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena"]
SIGN_NUM = {s: i for i, s in enumerate(SIGNS)}

# ---- partner-indication vocab (classical, bounded, warm) ----
SIGN_PARTNER = {
    "Mesha": "direct, energetic, quick to decide — someone who takes initiative",
    "Vrishabha": "steady, comfort-loving, loyal — someone who values stability and family",
    "Mithuna": "communicative, witty, sociable — someone you can talk to for hours",
    "Karka": "caring, family-oriented, emotionally deep — a nurturing presence",
    "Simha": "confident, warm, dignified — someone with presence and generosity",
    "Kanya": "practical, detail-minded, helpful — someone organised and sincere",
    "Tula": "balanced, charming, partnership-minded — marriage matters deeply to them",
    "Vrishchika": "intense, private, deeply loyal — a bond that runs deep once formed",
    "Dhanu": "optimistic, principled, freedom-loving — someone with strong beliefs",
    "Makara": "responsible, ambitious, mature — often settled or career-established",
    "Kumbha": "independent, idealistic, unconventional — a friend first",
    "Meena": "gentle, intuitive, adaptable — emotionally giving and artistic",
}
DK_PARTNER = {
    "Sun": "a dignified, self-respecting partner, possibly from an established family",
    "Moon": "an emotionally attuned, caring partner; family approval flows easily",
    "Mars": "an energetic, protective partner with strong drive",
    "Mercury": "a younger-feeling, intelligent, talkative partner",
    "Jupiter": "a wise, well-educated, principled partner — often traditional values",
    "Venus": "an attractive, artistic, pleasure-loving partner; strong mutual affection",
    "Saturn": "a mature, dutiful, patient partner — possibly older or met later",
}
GRADE_ACTION = {
    "Strong": ("Lean in.", "Treat serious conversations in this period seriously — "
               "involve family early, say yes to meetings, and don't postpone "
               "decisions that feel right. This is your highest-activation phase."),
    "Moderate": ("Stay active.", "Keep profiles current and meetings on — matches "
                 "formed here can absolutely convert, especially in the strongest "
                 "months. Don't force outcomes; do keep doors open."),
    "Building": ("Prepare.", "Use this phase to get ready — clarity on what you "
                 "want, conversations with family, self-work. Momentum built here "
                 "pays off in the next stronger window."),
}
GRADE_COLOR = {"Strong": "#C93B2E", "Moderate": "#E4B04A", "Building": "#8F92AB"}

# North Indian chart: house polygon centers (viewBox 0 0 400 400), houses 1-12
HOUSE_POS = {1: (200, 105), 2: (105, 58), 3: (55, 105), 4: (105, 200),
             5: (55, 295), 6: (105, 345), 7: (200, 295), 8: (295, 345),
             9: (345, 295), 10: (295, 200), 11: (345, 105), 12: (295, 58)}
PLANET_ABBR = {"Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me",
               "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa",
               "Rahu": "Ra", "Ketu": "Ke"}


def _houses_from(ref: int, target: int) -> int:
    return ((target - ref) % 12) + 1


def north_chart_svg(payload: dict) -> str:
    lagna = SIGN_NUM[payload["chart"]["lagna"]]
    by_house = {h: [] for h in range(1, 13)}
    for pname, pdata in payload["chart"]["planets"].items():
        h = _houses_from(lagna, SIGN_NUM[pdata["sign"]])
        tag = PLANET_ABBR[pname] + ("↺" if pdata["retro"] and pname not in ("Rahu", "Ketu") else "")
        by_house[h].append(tag)
    cells = []
    for h, (cx, cy) in HOUSE_POS.items():
        sign_num = ((lagna + h - 1) % 12) + 1
        cells.append(f"<text x='{cx}' y='{cy-16}' class='sn'>{sign_num}</text>")
        row = " ".join(by_house[h][:4])
        if row:
            cells.append(f"<text x='{cx}' y='{cy+6}' class='pl'>{row}</text>")
        if len(by_house[h]) > 4:
            cells.append(f"<text x='{cx}' y='{cy+24}' class='pl'>{' '.join(by_house[h][4:])}</text>")
    return f"""<svg viewBox="0 0 400 400" class="kchart" role="img" aria-label="Birth chart">
<rect x="8" y="8" width="384" height="384" fill="none" stroke="#E4B04A" stroke-width="2"/>
<path d="M8 8 L392 392 M392 8 L8 392" stroke="#E4B04A" stroke-width="1.5" fill="none"/>
<path d="M200 8 L392 200 L200 392 L8 200 Z" stroke="#E4B04A" stroke-width="2" fill="none"/>
<style>.sn{{font:600 13px sans-serif;fill:#8F92AB;text-anchor:middle}}
.pl{{font:800 15px sans-serif;fill:#F3EFE4;text-anchor:middle}}</style>
{''.join(cells)}</svg>"""


def _weak_periods(payload: dict) -> list:
    """Gaps > 10 months between consecutive windows inside the horizon."""
    ws = payload["windows"]
    if not ws:
        return []
    fmt = lambda s: datetime.strptime(s, "%Y-%m")
    gaps, hz = [], payload["teaser"]["horizon"]
    prev_end = fmt(f"{hz[0]}-01")
    bounds = [(fmt(w["start"]), fmt(w["end"])) for w in ws] + [(fmt(f"{hz[1]}-01"),) * 2]
    for (s, e) in bounds:
        if (s - prev_end).days > 300:
            gaps.append((prev_end.strftime("%b %Y"), s.strftime("%b %Y")))
        prev_end = max(prev_end, e)
    return gaps[:2]


AX_PRE = r"""<script>
(function(){
  try{
    var l = localStorage.getItem('axlang') || 'en';
    if(l === 'en') document.documentElement.classList.add('ax-pre');
  }catch(e){}
  setTimeout(function(){ document.documentElement.classList.remove('ax-pre'); }, 1500);
})();
</script>
<style>html.ax-pre body{visibility:hidden}@media print{#axlang{display:none!important}#ax-pdf{display:none!important}.cover{break-after:page;break-inside:avoid}h2,h1,.plabel{break-after:avoid}body{background:#fff}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}.ax-wm{display:flex!important}.ax-share{display:none!important}}.ax-wm{display:none;position:fixed;inset:0;z-index:9998;pointer-events:none;flex-direction:column;align-items:center;justify-content:center;transform:rotate(-28deg);opacity:.08;color:#151C39;font-family:Georgia,serif}.ax-wm b{font-size:66px;letter-spacing:.12em;line-height:1}.ax-wm span{font-size:18px;letter-spacing:.35em;margin-top:6px}.ax-share{display:inline-block;background:#25D366;color:#fff;border:0;border-radius:10px;padding:12px 18px;font:600 15px/1 sans-serif;cursor:pointer;text-decoration:none}.ax-disc{max-width:640px;margin:28px auto 8px;padding:14px 16px;border:1px solid #E7E0D2;border-radius:10px;background:#fbf7ef;font-size:12.5px;line-height:1.5;color:#6b6f80}.ax-endcard{max-width:640px;margin:12px auto 28px;text-align:center;padding:18px;border-top:2px solid #E4B04A}.ax-endcard b{font-size:18px;color:#151C39}.ax-endcard a{color:#C93B2E;text-decoration:none;font-weight:600}.ans{max-width:640px;margin:8px auto 4px;padding:20px 22px;border:1px solid #E4B04A;border-radius:14px;background:#FFF9EC}.ans .plabel{color:#B8860B;margin:0 0 2px}.ans h2{margin:.15em 0 .55em}.ans-win{font-size:17px;margin:.3em 0}.ans-win .g{color:#2E7D53;font-weight:700}.ans-win2{color:#4a4d5e;margin:.15em 0}.ans-mg{margin:.55em 0 .2em;font-weight:600}.ans-note{font-size:12.5px;color:#6b6f80;margin-top:.6em;line-height:1.5}.facts .why{font-size:12px;color:#8a7a5c;margin:3px 0 11px;line-height:1.45}</style>"""


REPORT_I18N = r"""<script>
(function(){
  var FRAG = [
    ["Aapka jawab — ek nazar mein","Your answer — at a glance"],
    ["Shaadi kab hogi? — seedha jawab","When will you get married? — the direct answer"],
    ["Sabse strong window:","Strongest window:"],
    ["Uske baad:","After that:"],
    ["Manglik: Nahi — is taraf koi rukaawat nahi.","Manglik: No — no obstacle on this front."],
    ["Manglik: technically haan, par cancel ho gaya — practically Nahi.","Manglik: technically yes, but cancelled — practically No."],
    ["Manglik: Haan — page 5 par detail aur cancellation check dekhiye.","Manglik: Yes — see the detail and cancellation check on page 5."],
    ["Yeh jawab aapke poore chart se nikla hai. Neeche har window ki wajah, aapka Navamsa, aur beete periods — taaki aap khud milaa sakein.","This answer comes from your full chart. Below: the reason for each window, your Navamsa, and past periods — so you can check it yourself."],
    ["Aapki personality aur poore chart ka base — har bhaav isi se gina jaata hai.","The base of your personality and whole chart — every house is counted from here."],
    ["Aapka mann aur emotional nature. Aapki dasha timeline isi Moon-nakshatra se chalti hai — yahi timing ka engine hai.","Your mind and emotional nature. Your dasha timeline runs from this Moon-nakshatra — this is the engine of timing."],
    ["Shaadi, partner aur commitment ka ghar — marriage ka main area.","The house of marriage, partner and commitment — the main area for marriage."],
    ["Shaadi ka main switch. Iski dignity (upar) timing ki quality batati hai — strong matlab saaf timing, tender matlab zyada soch-samajh.","The main switch for marriage. Its dignity (above) shows the quality of the timing — strong means clear timing, tender means more thought is needed."],
    ["Rishton ka natural indicator (Venus/Jupiter) — yeh shaadi ka promise dikhata hai.","The natural indicator of relationships (Venus/Jupiter) — it shows the marriage promise."],
    ["Jaimini system ka spouse-significator — partner ki ek jhalak.","The spouse-significator in the Jaimini system — a glimpse of the partner."],
    ["Abhi kaunsi dasha chal rahi hai. Windows isi timeline par bante hain — isliye yeh sabse relevant.","Which dasha is running now. The windows form on this timeline — which is why this is the most relevant."],
    ["Yeh report classical Vedic Jyotish (dasha-transit) principles par computed hai — guidance ke liye, guarantee nahi. Timing windows probability hain, fixed dates nahi. Yeh legal, medical ya financial advice nahi hai. Apne life decisions aap apni samajh se lijiye; Axtroshastra kisi outcome ki zimmedari nahi leta.","This report is computed from classical Vedic Jyotish (dasha-transit) principles — for guidance, not a guarantee. Timing windows are probabilities, not fixed dates. This is not legal, medical or financial advice. Make your own life decisions using your own judgement; Axtroshastra takes no responsibility for any outcome."],
    ["Yeh report Axtroshastra ne banayi — apna report paayein:","Made with Axtroshastra — get your own report at:"],
    ["self-respecting, strong-willed partner — individuality rishtey mein central; ek dusre ke ego ko space dena seekhna faydemand","self-respecting, strong-willed partner — individuality is central to the relationship; learning to give each other's ego space pays off"],
    ["emotionally attuned, caring partner — ghar-parivar ka warmth bond ka kendra; mood-tuning dono ki saanjhi zimmedari","emotionally attuned, caring partner — the warmth of home and family is the heart of the bond; mood-tuning is a shared responsibility"],
    ["energetic, passionate bond — kabhi tez-mizaji bhi (Manglik check upar dekhiye); jhagdon ko jaldi suljhana rishtey ko majboot karta hai","energetic, passionate bond — sometimes hot-tempered too (see the Manglik check above); resolving quarrels quickly makes the relationship stronger"],
    ["youthful, communicative partner — baat-cheet aapka asli gum hai; aksar partner young-natured ya age-gap kam","youthful, communicative partner — conversation is your real glue; often the partner is young-natured or the age gap is small"],
    ["wise, principled, often traditional-values partner — 7th house mein Guru ko classical texts shubh maante hain; family-approved yog","wise, principled, often traditional-values partner — classical texts consider Jupiter in the 7th house auspicious; a family-approved match"],
    ["affectionate, harmony-loving partner — romance aur comfort sahaj; marriage karaka apni hi jagah, isliye achha placement","affectionate, harmony-loving partner — romance and comfort come naturally; the marriage karaka is in its own place, so a good placement"],
    ["mature, committed, possibly older ya seriously-minded partner — bond dheere banta hai par tikau; shuruaati sabr baad mein rang laata hai","mature, committed, possibly older or seriously-minded partner — the bond builds slowly but lasts; early patience pays off later"],
    ["unconventional attraction — partner alag background/community/desh se ho sakta hai; shuruaat sudden ya intense","unconventional attraction — the partner may come from a different background/community/country; the start can be sudden or intense"],
    ["gehra par thoda detached bond — partner spiritually-inclined ho sakta hai; over-analysis se bachna, dil se judna","a deep but slightly detached bond — the partner may be spiritually-inclined; avoid over-analysis, connect from the heart"],
    ["Is chart mein koi graha vargottama nahi — normal hai, zyaadatar charts mein 0–2 hote hain.","No planet is vargottama in this chart — that's normal; most charts have only 0–2."],
    ["aapka 7th lord","your 7th lord"],
    ["vargottama hai (D1 aur D9 mein ek hi rashi) — marriage promise strong","is vargottama (same sign in D1 and D9) — a strong marriage promise"],
    ["vargottama hai — sneh aur nibhaav ki strength","is vargottama — strength of affection and commitment"],
    ["debilitated hai — timing par thoda extra dhyaan","is debilitated — a little extra care on timing"],
    ["D9 mein debilitated hai — expression mein narmi ki zaroorat","is debilitated in D9 — expression needs some gentleness"],
    ["(upar windows dekhiye).","(see the windows above)."],
    ["Navamsa thoda tender hai — iska matlab shaadi nahi hoti aisa nahi, balki partner-choice aur timing mein soch-samajh zyada zaroori hai. Yeh warning nahi, awareness hai.","The Navamsa is a bit tender — this doesn't mean marriage won't happen; rather, partner-choice and timing need more thought. This is not a warning, it's awareness."],
    ["Navamsa marriage promise ko steadily support karta hai — koi badi rukaawat nahi, D1 windows hi driver hain.","The Navamsa steadily supports the marriage promise — no major obstacle; the D1 windows are the driver."],
    ["D9 mein koi strong plus ya minus signal nahi — neutral promise, timing D1 se aati hai.","No strong plus or minus signal in D9 — a neutral promise; the timing comes from D1."],
    ["Aapka chart — marriage lens se","Your chart — through a marriage lens"],
    ["Yeh 6-7 factors milkar aapki marriage timing decide karte hain. Agle page par inhi se nikale gaye aapke windows hain.","These 6–7 factors together decide your marriage timing. The next page has your windows, derived from them."],
    ["Yeh 6–7 factors milkar aapki marriage timing decide karte hain. Agle page par inhi se nikale gaye aapke windows hain.","These 6–7 factors together decide your marriage timing. The next page has your windows, derived from them."],
    ["timing par extra dhyaan","pay extra attention to timing"],
    ["apne hi sign mein — strong placement","in its own sign — strong placement"],
    ["theek-thaak","steady"],
    ["Aapka poora chart — verify kijiye","Your full chart — verify it"],
    ["Hum kuch chhupate nahi. Neeche aapke saare 9 grahon ki exact position hai — koi bhi astrologer ise apni panchang se milaa sakta hai. Yahi hamari transparency hai.","We hide nothing. Below are the exact positions of all 9 of your planets — any astrologer can check them against their panchang. That is our transparency."],
    ["Bhaav (house) lagna se gina gaya hai","Houses are counted from the lagna"],
    ["Yeh windows kaise nikle","How these windows were derived"],
    ["Har window ke card mein uske reasons diye hain — kaunsi dasha, kaunsa connection. Broad logic:","Each window's card gives its reasons — which dasha, which connection. Broad logic:"],
    ["marriage typically triggers jab dasha/antardasha lord aapke 7th house ya uske lord se connect hota hai, aur Jupiter ka transit usko confirm karta hai.","marriage typically triggers when the dasha/antardasha lord connects to your 7th house or its lord, and Jupiter's transit confirms it."],
    ["Timing windows probability bands hain, appointments nahi — ±15 minute ka birth time difference bhi boundaries ko months tak shift kar sakta hai. Isliye hum honest ranges dete hain, fake precision nahi.","Timing windows are probability bands, not appointments — even a ±15-minute birth-time difference can shift the boundaries by months. So we give honest ranges, not fake precision."],
    ["Aapke top window ka scorecard","Your top window's scorecard"],
    ["Yeh window","This window"],
    ["ko humne","was scored"],
    ["diye, isliye grade","points, hence grade"],
    ["Har point ke peeche ek classical rule hai","Behind each point is a classical rule"],
    ["neeche exact","the exact breakdown below,"],
    ["mila.","points."],
    ["Koi astrologer chaahe toh in rules ko apne haath se verify kar sakta hai — kyunki yeh judgement nahi, calculation hai.","Any astrologer can verify these rules by hand — because this is not judgement, it is calculation."],
    ["Aap manglik nahi hain","You are not manglik"],
    ["Aap manglik hain","You are manglik"],
    ["Mars aapke chart mein manglik houses","Mars is not in the manglik houses"],
    ["mein nahi hai — lagna se bhi, Moon se bhi.","in your chart — from the lagna, and from the Moon too."],
    ["Rishtey ki baat-cheet mein yeh sawaal aaye toh confidently 'nahi' kah sakte hain.","If this comes up in match discussions, you can confidently say 'no'."],
    ["Rishtey ki baat-cheet mein yeh sawaal aaye toh confidently","If this comes up in match discussions, you can confidently"],
    ["'nahi' kah sakte hain.","say 'no'."],
    ["kah sakte hain.","say so."],
    ["shaadi ka asli sheesha","the true mirror of marriage"],
    ["batata hai; Navamsa","tells; Navamsa"],
    ["nibhega — isiliye classical Jyotish mein shaadi ke liye","will last — which is why, in classical Jyotish, for marriage"],
    ["sabse zaroori divisional chart hai. Aapka","is the most important divisional chart. Your"],
    ["houses ke andar","within the houses"],
    ["Vargottama aur","Vargottama and"],
    ["mein ek hi rashi — extra","in the same sign — an extra"],
    ["Navamsa marriage promise ko strongly support karta hai — yog pakka hai, sirf timing ki baat hai","The Navamsa strongly supports the marriage promise — the promise is solid, it is only a matter of timing"],
    ["(upar windows","(windows above"],
    ["D9 mein 7th lord","In D9, the 7th lord"],
    ["apni acchi dignity mein hai","is in good dignity"],
    ["D9 mein strong hai","is strong in D9"],
    ["mein strong hai","is strong in"],
    ["promise ki baat hai, timing ki nahi — timing upar ke windows batate hain.","this speaks to the promise, not the timing — the windows above give the timing."],
    ["Dono milkar poori tasveer dete hain.","Together they give the full picture."],
    ["Quiet periods — aur unka matlab","Quiet periods — and what they mean"],
    ["Jitna important yeh jaanna hai ki kab yog strong hai, utna hi yeh ki kab नहीं hai.","It is as important to know when the chance is strong as when it is not."],
    ["Jitna important yeh jaanna hai ki kab yog strong hai, utna hi yeh ki kab","It is as important to know when the chance is strong as when it is not"],
    ["In periods mein rishtey aa sakte hain, par convert hone ka pattern weak rehta hai:","In these periods matches may come, but the pattern of converting stays weak:"],
    ["In periods mein rishtey aa sakte hain, par convert hone ka pattern weak rehta","In these periods matches may come, but the pattern of converting stays weak"],
    ["Agar pichhle saalon mein baat banti-banti reh gayi ho — chart mein aksar uski wajah dikh jaati hai. Yeh aapki kami nahi thi; timing thi.","If matches kept almost-happening in past years — the chart often shows why. This was not your shortcoming; it was timing."],
    ["Pichhle saal","Past years"],
    ["Ab tak kya hua — aur kyun","What has happened so far — and why"],
    ["Aapke pichhle periods ka chart-analysis. Agar rishtey aaye par bane nahi, ya bilkul shaant raha — yahan uski wajah","A chart-analysis of your past periods. If matches came but did not work out, or it stayed completely quiet — here is why"],
    ["Yeh section isliye hai taaki aap dekh","This section is here so that you can see"],
    ["timing ek pattern hai, aapki kami nahi. Jo beet gaya usmein bhi chart ka logic tha.","timing is a pattern, not your shortcoming. Even what has passed had the chart's logic in it."],
    ["Saal-dar-saal","Year by year"],
    ["saal — ek nazar mein","years — at a glance"],
    ["Agle ","The next "],
    ["Jupiter ka transit is saal supportive houses mein hai — conversations ko aage badhaane ka saath milega.","Jupiter's transit this year is in supportive houses — it will help move conversations forward."],
    ["Jupiter ka transit is saal neutral zone mein hai — effort par zyada, luck par kam depend kijiye.","Jupiter's transit this year is in a neutral zone — rely more on effort, less on luck."],
    ["Yeh page save kar lijiye — har saal ke shuru mein dobara padhne layak hai.","Save this page — it is worth re-reading at the start of each year."],
    ["Yeh indications hain, portrait nahi — chart directions batata hai, details zindagi bharti hai.","These are indications, not a portrait — the chart gives directions, life fills in the details."],
    ["house khaali hai","house is empty"],
    ["koi graha 7th mein nahi. Yeh normal aur aksar shubh maana jaata hai: partner ka pattern 7th ke","no planet sits in the 7th. This is normal and often considered auspicious: the partner pattern is read from the 7th's"],
    ["koi graha ismein nahi. Yeh normal aur aksar shubh maana jaata hai","no planet sits in it. This is normal and often considered auspicious"],
    ["partner ka pattern","the partner pattern"],
    ["aur karaka se padha jaata hai (upar diya hai), naa ki kisi baithe graha se.","and karaka (given above), not from any planet sitting there."],
    ["Chart ka jhukaav","The chart leans toward"],
    ["ki taraf hai — introductions aur family networks se hi strong yog banta hai.","— the strongest chance forms through introductions and family networks."],
    ["se connection hai — partner doori se, alag community se, ya unexpected background se aane ka yog hai. Surprise ke liye taiyaar rahiye.","connection — the partner may come from a distance, a different community, or an unexpected background. Be ready for a surprise."],
    ["Ab karna kya hai","What to do now"],
    ["Kundli timing batati hai; effort aur choice aapke haath mein hai. Strong window mein bhi rishtey dhoondhne padte hain — bas conversion rate better hota hai.","The chart tells you the timing; effort and choice are in your hands. Even in a strong window you still have to look for matches — the conversion rate is simply better."],
    ["Aap pyaar kaise karte hain — chart ke hisaab se","How you love — according to the chart"],
    ["combust hai, isliye expression mein hesitation aa sakti hai; feelings genuine, awaaz dheemi","is combust, so there can be hesitation in expression; the feelings are genuine, the voice soft"],
    ["Jo aapne nahi poocha, par jaanna chahenge","What you did not ask, but would want to know"],
    ["Saturn ka influence aapke","Saturn's influence is on your"],
    ["house par hai — timing mein maturity-factor hai. Matlab: shaadi thodi der se, par zyada soch-samajh ke. Late ≠ never.","house — there is a maturity-factor in the timing. Meaning: marriage a little later, but with more thought. Late ≠ never."],
    ["abhi nahi chal rahi.","is not running right now."],
    ["se. Filhaal Shani ka is angle se koi delay-pressure nahi.","onwards. For now, no delay-pressure from Saturn on this angle."],
    ["Next phase","Next phase from"],
    ["Weak periods mein","In weak periods"],
    ["Traditional support — bina dar ke","Traditional support — without fear"],
    ["ke hisaab se, weak windows mein classical","accordingly, in weak windows classical"],
    ["baar, Ravivar (Sunday) ko","times, on Ravivar (Sunday)"],
    ["ki current condition mein gemstone recommend nahi karte — mantra aur fast kaafi hain.","in its current condition — we do not recommend a gemstone; mantra and fasting are enough."],
    ["Order yaad","Remember the order"],
    ["pehla remedy hamesha action hai — strong window mein actively dhoondhna. Yeh support hai, substitute nahi.","the first remedy is always action — actively searching in a strong window. This is a support, not a substitute."],
    ["Ek aur sawaal, usi chart","One more question, from the same chart"],
    ["career kab lift hoga?","when will your career take off?"],
    ["par CAREER bhejiye","send CAREER on"],
    // ---- Manglik page (page 5) ----
    ["Manglik placement hai — par cancelled hai","There is a Manglik placement — but it is cancelled"],
    ["Manglik placement hai — calmly samjhiye","There is a Manglik placement — understand it calmly"],
    ["Mars manglik position mein hai, lekin classical cancellation rules apply hote hain:","Mars is in a manglik position, but classical cancellation rules apply:"],
    ["Tradition mein cancelled manglik ko manglik nahi mana jaata — matching mein isse issue nahi banna chahiye.","In tradition a cancelled manglik is not counted as manglik — it should not be an issue in matching."],
    ["Mars manglik houses mein hai. Yeh koi shraap nahi hai — classical texts iske liye simple remedial framing dete hain, aur manglik-manglik matching mein yeh neutral ho jaata hai. Dar ki nahi, jaankari ki baat hai.","Mars is in the manglik houses. This is no curse — classical texts give it a simple remedial framing, and in manglik-manglik matching it becomes neutral. This is a matter of information, not fear."],
    ["manglik houses mein","in the manglik houses"],
    // ---- Sade Sati (in '3 aur sach' section) ----
    ["Sade Sati check: chal rahi hai","Sade Sati check: currently running"],
    ["Iska matlab delay ka pressure, denial nahi — Shani ke period mein bani shaadiyan sabse tikau maani jaati hain. Windows upar isi ko account karke grade hue hain.","This means delay-pressure, not denial — marriages made during Saturn's period are considered the most durable. The windows above are graded taking this into account."],
    ["Sade Sati check: abhi nahi chal rahi.","Sade Sati check: not currently running."],
    ["rising (pehla charan)","rising (first phase)"],
    ["peak (dusra charan)","peak (second phase)"],
    ["setting (aakhri charan)","setting (final phase)"],
    // ---- Section titles / headlines ----
    ["Aapka pattern","Your pattern"],
    ["Aapka nakshatra:","Your nakshatra:"],
    ["Aapka Venus","Your Venus"],
    ["3 aur sach","3 more truths"],
    // ---- Venus love-style suffix (own/exalted) ----
    ["Venus apne hi sign mein strong hai; pyaar mein aapki instinct par bharosa kiya ja sakta hai.","Venus is strong in its own sign; in love, your instincts can be trusted."],
    // ---- '3 aur sach' check bodies (untranslated branches) ----
    ["Saturn ka koi direct influence aapke 7th house par nahi — classical 'late marriage' indicator aapke chart mein absent hai.","Saturn has no direct influence on your 7th house — the classical 'late marriage' indicator is absent from your chart."],
    ["Aapke chart mein 5th–7th connection hai — love-marriage ya self-driven rishtey ka yog. Arranged setup mein bhi pasand aapki hi chalegi.","Your chart has a 5th–7th connection — a leaning toward love-marriage or a self-driven relationship. Even in an arranged setup, your own preference will prevail."],
    ["Rahu/12th ka 7th se connection hai — partner doori se, alag community se, ya unexpected background se aane ka yog hai. Surprise ke liye taiyaar rahiye.","There's a Rahu/12th-to-7th connection — the partner may come from a distance, a different community, or an unexpected background. Be ready for a surprise."],
    ["Partner ka yog aapke apne circle aur community ke aas-paas ka hai — door ka yog chart mein prominent nahi.","The partner is indicated within your own circle and community — a distant match is not prominent in the chart."]
  ];
  var EXACT = {"HAAN":"YES","NAHI":"NO","नहीं":"NO","HAN":"YES","Pichhle saal":"Past years","kab":"when","aur":"and","Graha":"Planet","Bhaav":"House","hai.":"."};
  var TITLE = { en: "Marriage Timing Report | Axtroshastra" };
  function norm(s){ return s.replace(/\u00a0/g," ").replace(/ [‐‑‒–—-] /g," — ").replace(/[‐‑‒–—]/g,"—").replace(/\s+/g," "); }
  var SORTED = FRAG.map(function(p){ return [norm(p[0]), p[1]]; }).sort(function(a,b){ return b[0].length - a[0].length; });
  function walk(node, fn){
    for(var i=0;i<node.childNodes.length;i++){
      var n=node.childNodes[i];
      if(n.nodeType===3){ fn(n); }
      else if(n.nodeType===1 && n.tagName!=='SCRIPT' && n.tagName!=='STYLE' && n.id!=='axlang'){ walk(n, fn); }
    }
  }
  function translate(hi){
    var t=norm(hi), trimmed=t.trim();
    if(Object.prototype.hasOwnProperty.call(EXACT, trimmed)){ return t.replace(trimmed, EXACT[trimmed]); }
    for(var i=0;i<SORTED.length;i++){ if(t.indexOf(SORTED[i][0])>=0){ t = t.split(SORTED[i][0]).join(SORTED[i][1]); } }
    return t;
  }
  function apply(lang){
    walk(document.body, function(tn){
      if(lang!=='en'){ if(tn.__hi!=null) tn.nodeValue = tn.__hi; return; }
      if(tn.__hi==null) tn.__hi = tn.nodeValue;
      if(!tn.__hi.trim()) return;
      tn.nodeValue = translate(tn.__hi);
    });
    document.documentElement.lang = (lang==='en')?'en':'hi-IN';
    if(lang==='en' && TITLE.en){ if(!window.__titlehi) window.__titlehi=document.title; document.title=TITLE.en; }
    else if(window.__titlehi){ document.title=window.__titlehi; }
    try{ localStorage.setItem('axlang', lang); }catch(e){}
    var box=document.getElementById('axlang');
    if(box){ box.querySelector('[data-l=hi]').classList.toggle('on', lang!=='en'); box.querySelector('[data-l=en]').classList.toggle('on', lang==='en'); }
    window.__axlang=lang;
    document.documentElement.classList.remove('ax-pre');
  }
  var css=document.createElement('style');
  css.textContent='#axlang{position:fixed;top:10px;right:10px;z-index:9999;display:flex;background:rgba(21,28,57,.92);border:1px solid #E4B04A;border-radius:20px;overflow:hidden;font:600 12px/1 -apple-system,Segoe UI,sans-serif;box-shadow:0 4px 14px rgba(0,0,0,.25)}#axlang button{background:transparent;color:#C9CBDB;border:0;padding:7px 13px;cursor:pointer;letter-spacing:.02em}#axlang button.on{background:#E4B04A;color:#151C39}@media print{#axlang{display:none}}';
  document.head.appendChild(css);
  var box=document.createElement('div'); box.id='axlang';
  box.innerHTML='<button data-l="hi">Hinglish</button><button data-l="en">English</button>';
  box.addEventListener('click', function(e){ var b=e.target.closest('button'); if(b) apply(b.getAttribute('data-l')); });
  document.body.appendChild(box);
  var saved='en'; try{ saved=localStorage.getItem('axlang')||'en'; }catch(e){}
  apply(saved);
  window.axShare=function(){var url=location.href;var t=(window.__axlang==='en'?'Check out my marriage timing report from Axtroshastra':'Meri marriage timing report Axtroshastra se');if(navigator.share){navigator.share({title:'Axtroshastra',text:t,url:url}).catch(function(){});}else{window.open('https://wa.me/?text='+encodeURIComponent(t+' '+url),'_blank');}};
})();
</script>
"""


MILAN_I18N = r"""<script>
(function(){
  var FRAG = [
    // ---- static strings in render_milan ----
    ["✦ AXTROSHASTRA · KUNDLI MILAN","✦ AXTROSHASTRA · HOROSCOPE MATCHING"],
    ["Ashtakoota — aatho kootas ka breakdown","Ashtakoota — a breakdown of all eight kootas"],
    ["Dosha cancellation ke baad:","After the flaw cancellation:"],
    ["Dosha cancellation check","Flaw cancellation check"],
    ["Cancellations ke baad effective score:","Effective score after cancellations:"],
    ["Is jodi mein dosha ke standard cancellation rules apply nahi hote — dosha effective hai. Iska matlab section 'Score ka matlab' mein neeche padhiye; dar se nahi, samajh se decide kijiye.","For this couple the standard cancellation rules for the flaw do not apply — the flaw is effective. Read what this means in the 'What the score means' section below; decide not from fear but from understanding."],
    ["Is jodi ki taakat — aur dhyaan ki jagah","This couple's strengths — and where to pay attention"],
    ["Aap dono ki energy","Your combined energy"],
    ["Score kam hai — iska matlab kya hai?","The score is low — what does it mean?"],
    ["Pehli baat:","First:"],
    ["guna milan ek classical input hai, poora faisla nahi. Yeh Moon-positions ki compatibility napta hai — values, maturity aur commitment nahi, jo kisi bhi rishtey ke asli pillars hain.","guna milan is one classical input, not the whole verdict. It measures the compatibility of Moon-positions — not values, maturity and commitment, which are the real pillars of any relationship."],
    ["Dusri baat:","Second:"],
    ["upar dekhiye kaunse kootas mein kami hai. Gana ya Graha Maitri ki kami","look above to see which kootas fall short. A shortfall in Gana or Graha Maitri is"],
    ["hai — yeh communication-patterns ki baat hai jo couples seekh lete hain. Nadi/Bhakoot dosha (agar cancelled nahi) traditional weight zyada rakhta hai — wahan family-elders aur apne vivek dono se salaah kijiye.","— this is about communication-patterns that couples learn. The Nadi/Bhakoot flaw (if not cancelled) carries more traditional weight — there, seek counsel from both family-elders and your own judgement."],
    ["Teesri baat:","Third:"],
    ["lakhs of successful marriages kam score ke saath hui hain. Score ko information ki tarah use kijiye — kis cheez par kaam karna hoga yeh jaanne ke liye — verdict ki tarah nahi.","lakhs of successful marriages have happened with a low score. Use the score as information — to learn what you will need to work on — not as a verdict."],
    // ---- manglik_note (products.py) ----
    ["Dono charts mein manglik placement hai — classical rule mein manglik-manglik pairing neutral ho jaati hai. Not an obstacle.","Both charts have a manglik placement — in the classical rule a manglik-manglik pairing becomes neutral. Not an obstacle."],
    ["Ek chart mein manglik placement hai (Moon-based check). Cancellation rules aksar apply hote hain — full lagna-based check ke liye exact birth times chahiye.","One chart has a manglik placement (Moon-based check). Cancellation rules often apply — for a full lagna-based check, exact birth times are needed."],
    ["Kisi bhi chart mein manglik dosha nahi hai (Moon-based check). ✅","Neither chart has a manglik flaw (Moon-based check). ✅"],
    // ---- nadi / bhakoot cancellation rules (products.py) — split around interpolated lord names ----
    ["Same nakshatra, alag pada — classical rule mein Nadi dosha cancelled.","Same nakshatra, different pada — in the classical rule the Nadi flaw is cancelled."],
    ["Moon rashi alag hai — widely-followed classical rule mein Nadi dosha cancelled.","The Moon rashi is different — in a widely-followed classical rule the Nadi flaw is cancelled."],
    ["Dono rashiyon ka lord ek hi hai (","Both signs share the same lord ("],
    [") — Bhakoot dosha cancelled.",") — the Bhakoot flaw is cancelled."],
    ["Rashi lords (","The sign lords ("],
    [") mutual friends hain — Bhakoot dosha cancelled.",") are mutual friends — the Bhakoot flaw is cancelled."],
    // ---- notes (products.py, English but carry the token 'dosha') ----
    ["Nadi dosha present — traditionally the most weighted dosha. Note: cancellation applies if moon signs differ or nakshatra padas differ; a detailed pada-level check is recommended.","Nadi flaw present — traditionally the most weighted affliction. Note: cancellation applies if moon signs differ or nakshatra padas differ; a detailed pada-level check is recommended."],
    ["Low score is spread across kootas rather than one dosha — often improvable factors (understanding, timing) rather than structural.","Low score is spread across kootas rather than one flaw — often improvable factors (understanding, timing) rather than structural."],
    // ---- KOOTA_TEXT couple-voiced bands (jyotish_maps.py) ----
    ["Kaam aur ego ke matters mein aap dono ka natural order milta hai — ghar ke decisions mein tug-of-war kam hoga.","In matters of work and ego you both fall into a natural order — there will be less tug-of-war in household decisions."],
    ["Kaam-kaaj aur ego ke sawaalon mein role-clarity conscious rakhni hogi — kaun kya lead karta hai, yeh baat-cheet se tay karo, assumption se nahi.","On questions of work and ego you will have to keep role-clarity conscious — decide who leads what through conversation, not assumption."],
    ["Aap dono ka ek dusre par sway balanced hai — koi kisi ko 'chala' nahi raha, dono saath chal rahe hain.","Your sway over each other is balanced — neither is 'driving' the other, you are both moving together."],
    ["Influence ek taraf thoda zyada hai — jab tak dominant partner ise care se use kare, yeh stability deta hai.","The influence tilts a little to one side — as long as the dominant partner uses it with care, it lends stability."],
    ["Mutual pull kam hai — matlab rishta convince karne se nahi, respect karne se chalega. Space dena yahan pyaar dikhaane ka tareeka hai.","The mutual pull is low — meaning the relationship will run on respect, not persuasion. Giving space is the way to show love here."],
    ["Nakshatra-count dono taraf shubh hai — saath rehne se dono ki wellbeing badhti hai, classical texts ise strong protection maanti hain.","The nakshatra-count is auspicious both ways — being together raises the wellbeing of both, and classical texts consider this strong protection."],
    ["Ek direction shubh, ek nahi — ek partner ko rishtey se zyada milta hai. Balance ke liye giving conscious rakhni hogi.","One direction is auspicious, one is not — one partner gains more from the relationship. To keep balance, giving will have to stay conscious."],
    ["Tara count inauspicious hai — traditionally health/wellbeing par dhyaan. Practical matlab: ek dusre ki sehat aur stress ka khayal is jodi ka zaroori ritual hona chahiye.","The Tara count is inauspicious — traditionally, attention to health/wellbeing. Practical meaning: caring for each other's health and stress should be an essential ritual for this couple."],
    ["Instinctive aur physical wavelength naturally milti hai — bina koshish ke comfort, jo har jodi ko naseeb nahi hota.","The instinctive and physical wavelength meets naturally — effortless comfort, which not every couple is blessed with."],
    ["Physical-instinctive match neutral hai — chemistry banayi ja sakti hai, bas dono ki pace alag ho sakti hai; patience rakho.","The physical-instinctive match is neutral — chemistry can be built, only your paces may differ; keep patience."],
    ["Yoni enemy-pair hai — instincts alag chalti hain. Yeh attraction ko nahi rokta, par daily-life habits (sona, uthna, touch, space) mein adjustment maangta hai. Naam se mat daro, pattern samjho.","This is a Yoni enemy-pair — instincts run differently. This does not stop attraction, but it asks for adjustment in daily-life habits (sleeping, waking, touch, space). Do not fear the name, understand the pattern."],
    ["Moon-lords doston mein hain — aap dono ka sochne ka tareeka compatible hai. Behas hogi toh bhi bhasha ek hi hogi.","The Moon-lords are friends — the two of you think in compatible ways. Even when there is an argument, the language will be the same."],
    ["Moon-lords neutral hain — mental wavelength banti hai shared experiences se. Saath cheezein karo, wavelength khud align hogi.","The Moon-lords are neutral — mental wavelength builds through shared experiences. Do things together and the wavelength will align on its own."],
    ["Moon-lords ki adaawat hai — matlab default sochne ke tareeke alag hain. Iska ilaaj hai 'translate' karna seekhna: partner ki baat ko uske frame mein samajhna, apne mein nahi.","The Moon-lords are at odds — meaning your default ways of thinking differ. The remedy is learning to 'translate': understanding your partner's point in their frame, not your own."],
    ["Temperament same category ka hai — energy levels, social style, gussa-shanti ka pattern milta hai.","The temperament is of the same category — energy levels, social style, and the anger-and-calm pattern all match."],
    ["Deva-Manushya pairing — ek zyada idealist, ek zyada practical. Achhi jodi, bas expectations ko naam dena seekho.","A Deva-Manushya pairing — one more idealist, one more practical. A good match, just learn to name your expectations."],
    ["Gana mismatch hai — temperament genuinely alag hain (jaise ek ko bheed chahiye, ek ko sannata). Yeh deal-breaker nahi, design-brief hai: ghar aisa banao jismein dono modes ki jagah ho.","There is a Gana mismatch — temperaments are genuinely different (say, one needs a crowd, the other silence). This is not a deal-breaker, it is a design-brief: build a home that has room for both modes."],
    ["Moon-signs ki relative position shubh hai — emotional bond aur family-growth ke liye classical green signal.","The relative position of the Moon-signs is auspicious — a classical green signal for the emotional bond and family-growth."],
    ["Bhakoot dosha hai — 6-8, 2-12 ya 5-9 ki position. Traditionally emotional distance ya financial friction se joda jaata hai. Cancellation check neeche dekho — aksar lords ki dosti ise cancel kar deti hai.","There is a Bhakoot flaw — a 6-8, 2-12 or 5-9 position. Traditionally it is linked to emotional distance or financial friction. See the cancellation check below — often the lords' friendship cancels it."],
    ["Nadi alag hai — sabse heavy koota clear hai. Classical texts iske liye sabse zyada points isi liye deti hain.","The Nadi is different — the heaviest koota is clear. That is exactly why classical texts award the most points for it."],
    ["Nadi same hai — traditionally sabse serious dosha, progeny aur vitality se juda. LEKIN: iske cancellation rules sabse well-defined hain. Neeche ka cancellation-check hi asli verdict hai, yeh zero nahi.","The Nadi is the same — traditionally the most serious flaw, tied to progeny and vitality. BUT: its cancellation rules are the most well-defined. The cancellation-check below is the real verdict, not this zero."],
    // ---- ELEMENT_PAIR couple text (jyotish_maps.py) ----
    ["Do fire moons — passion, speed aur honesty double; conflict bhi bright jalta hai par jaldi bujhta hai. Rule seekhiye: ek waqt par ek hi jale.","Two fire moons — passion, speed and honesty are doubled; conflict too burns bright but dies down fast. Learn the rule: only one burns at a time."],
    ["Do earth moons — stability, saving, building. Rishta ghar jaisa lagta hai; risk sirf yeh ki routine romance ko na kha jaaye.","Two earth moons — stability, saving, building. The relationship feels like home; the only risk is that routine may eat the romance."],
    ["Do air moons — baatein kabhi khatam nahi hongi. Mental match excellent; grounding (routine, decisions) ko conscious effort dena hoga.","Two air moons — the conversations will never end. The mental match is excellent; grounding (routine, decisions) will need conscious effort."],
    ["Do water moons — bina bole samajhna. Emotional depth rare-level ki hai; mood ek dusre par lehron ki tarah aate hain, isliye ek ka calm rehna zaroori.","Two water moons — understanding without words. The emotional depth is rare; moods wash over each other like waves, so it is essential that one stays calm."],
    ["Fire + earth — spark aur zameen. Ek raftaar laata hai, doosra thehraav. Fire ko patience, earth ko thodi spontaneity seekhni hogi — phir yeh builder-jodi hai.","Fire + earth — spark and ground. One brings pace, the other steadiness. Fire will have to learn patience, earth a little spontaneity — then this is a builder-couple."],
    ["Fire + air — hawa aag ko badhaati hai. Energy, plans, adventures — natural chemistry. Dhyaan bas itna: dono udna jaante hain, landing kaun karayega yeh tay kar lo.","Fire + air — air feeds the flame. Energy, plans, adventures — natural chemistry. Just note: both know how to fly, so settle who will handle the landing."],
    ["Fire + water — bhaap banti hai: intense attraction, intense reactions. Fire ko softness, water ko directness seekhni hogi. Mehnat maangta hai, magic deta hai.","Fire + water — steam forms: intense attraction, intense reactions. Fire will have to learn softness, water directness. It demands effort, it gives magic."],
    ["Earth + air — practical milta hai conceptual se. Air ideas laata hai, earth unhe khada karta hai. Pace ka difference hi friction hai, aur wahi complementarity bhi.","Earth + air — the practical meets the conceptual. Air brings ideas, earth stands them up. The difference in pace is the friction, and also the very complementarity."],
    ["Earth + water — mitti aur paani: sabse naturally nourishing pair. Ek security deta hai, doosra depth. Classical texts ise sahaj-anukool maanti hain.","Earth + water — soil and water: the most naturally nourishing pair. One gives security, the other depth. Classical texts consider this innately compatible."],
    ["Air + water — words milte hain feelings se. Air ko seekhna hoga ki har baat logic nahi hoti; water ko, ki har baat kehni padti hai. Bridge bana toh poetry hai.","Air + water — words meet feelings. Air will have to learn that not everything is logic; water, that not everything can go unsaid. Build the bridge and it is poetry."],
    // ---- ELEMENT_HI labels (jyotish_maps.py) ----
    ["Agni (fire)","Fire"],
    ["Prithvi (earth)","Earth"],
    ["Vayu (air)","Air"],
    ["Jal (water)","Water"],
    // ---- catch-all: any residual 'dosha' token -> 'flaw' (applied last, shortest) ----
    ["dosha","flaw"]
  ];
  var EXACT = {"HAAN":"YES","NAHI":"NO","नहीं":"NO","HAN":"YES","Pichhle saal":"Past years","kab":"when","aur":"and","Graha":"Planet","Bhaav":"House","hai.":"."};
  var TITLE = { en: "Horoscope Matching | Axtroshastra" };
  function norm(s){ return s.replace(/ /g," ").replace(/ [‐‑‒–—-] /g," — ").replace(/[‐‑‒–—]/g,"—").replace(/\s+/g," "); }
  var SORTED = FRAG.map(function(p){ return [norm(p[0]), p[1]]; }).sort(function(a,b){ return b[0].length - a[0].length; });
  function walk(node, fn){
    for(var i=0;i<node.childNodes.length;i++){
      var n=node.childNodes[i];
      if(n.nodeType===3){ fn(n); }
      else if(n.nodeType===1 && n.tagName!=='SCRIPT' && n.tagName!=='STYLE' && n.id!=='axlang'){ walk(n, fn); }
    }
  }
  function translate(hi){
    var t=norm(hi), trimmed=t.trim();
    if(Object.prototype.hasOwnProperty.call(EXACT, trimmed)){ return t.replace(trimmed, EXACT[trimmed]); }
    for(var i=0;i<SORTED.length;i++){ if(t.indexOf(SORTED[i][0])>=0){ t = t.split(SORTED[i][0]).join(SORTED[i][1]); } }
    return t;
  }
  function apply(lang){
    walk(document.body, function(tn){
      if(lang!=='en'){ if(tn.__hi!=null) tn.nodeValue = tn.__hi; return; }
      if(tn.__hi==null) tn.__hi = tn.nodeValue;
      if(!tn.__hi.trim()) return;
      tn.nodeValue = translate(tn.__hi);
    });
    document.documentElement.lang = (lang==='en')?'en':'hi-IN';
    if(lang==='en' && TITLE.en){ if(!window.__titlehi) window.__titlehi=document.title; document.title=TITLE.en; }
    else if(window.__titlehi){ document.title=window.__titlehi; }
    try{ localStorage.setItem('axlang', lang); }catch(e){}
    var box=document.getElementById('axlang');
    if(box){ box.querySelector('[data-l=hi]').classList.toggle('on', lang!=='en'); box.querySelector('[data-l=en]').classList.toggle('on', lang==='en'); }
    window.__axlang=lang;
    document.documentElement.classList.remove('ax-pre');
  }
  var css=document.createElement('style');
  css.textContent='#axlang{position:fixed;top:10px;right:10px;z-index:9999;display:flex;background:rgba(21,28,57,.92);border:1px solid #E4B04A;border-radius:20px;overflow:hidden;font:600 12px/1 -apple-system,Segoe UI,sans-serif;box-shadow:0 4px 14px rgba(0,0,0,.25)}#axlang button{background:transparent;color:#C9CBDB;border:0;padding:7px 13px;cursor:pointer;letter-spacing:.02em}#axlang button.on{background:#E4B04A;color:#151C39}@media print{#axlang{display:none}}';
  document.head.appendChild(css);
  apply('en');   // language toggle removed — Milan report is English-only
  window.axShare=function(){var url=location.href;var t=window.AX_SHARE_TEXT||'Check out our compatibility report from Axtroshastra';if(navigator.share){navigator.share({title:'Axtroshastra',text:t,url:url}).catch(function(){});}else{window.open('https://wa.me/?text='+encodeURIComponent(t+' '+url),'_blank');}};
})();
</script>
"""


def render_report(p: dict) -> str:
    meta, sig, mg = p["meta"], p["significators"], p["manglik"]
    name = escape(meta["name"])  # user-supplied: escape to prevent stored XSS
    system_note = ("Chandra Lagna system (Moon-as-ascendant) — the classical Parashari "
                   "method used when birth time is approximate. Fully traditional; "
                   "windows are shown with honest wider ranges."
                   if meta["system"] == "chandra_lagna" else
                   "Lagna-based analysis with full house precision.")

    # ---- page 3: windows + timeline ----
    hz = p["teaser"]["horizon"]
    tl_windows = ""
    for i, w in enumerate(p["windows"]):
        s = datetime.strptime(w["start"], "%Y-%m"); e = datetime.strptime(w["end"], "%Y-%m")
        left = max(0, (s - datetime(hz[0], 1, 1)).days / ((hz[1] - hz[0]) * 365.25) * 100)
        width = max(6, (e - s).days / ((hz[1] - hz[0]) * 365.25) * 100)
        tl_windows += (f"<div class='tlw' style='left:{left:.1f}%;width:{min(width, 100-left):.1f}%;"
                       f"background:{GRADE_COLOR[w['grade']]}'></div>")
    years_axis = "".join(f"<span>{y}</span>" for y in range(hz[0], hz[1] + 1, 2))

    window_cards = ""
    for i, w in enumerate(p["windows"], 1):
        pretty = lambda ym: datetime.strptime(ym, "%Y-%m").strftime("%b %Y")
        core = (f"<p class='core'>Core period: {pretty(w['core_start'])} – {pretty(w['core_end'])}</p>"
                if w["start"] != w["core_start"] else "")
        peak = (f"<p class='peak'>⭐ Strongest months: {', '.join(w['peak_months'])}</p>"
                if w["peak_months"] else "")
        reasons = "".join(f"<li>{r['why']}</li>" for r in w["rules_fired"]
                          if not r["id"].startswith(("AD_WEAK", "AD_DRY", "TR_SAT")))[:600]
        window_cards += f"""
<div class="wcard" style="border-left-color:{GRADE_COLOR[w['grade']]}">
  <div class="wtop"><span class="wnum">Window {i}</span>
  <span class="wgrade" style="background:{GRADE_COLOR[w['grade']]}">{w['grade'].upper()}</span></div>
  <p class="wdates">{pretty(w['start'])} → {pretty(w['end'])}</p>
  {core}{peak}
  <p class="wdasha">{w['dasha']}</p>
  <ul class="wwhy">{reasons}</ul>
</div>"""

    # ---- page 5: manglik ----
    mg_head = {"non_manglik": "Aap manglik nahi hain ✅",
               "manglik_cancelled": "Manglik placement hai — par cancelled hai ✅",
               "manglik": "Manglik placement hai — calmly samjhiye"}[mg["status"]]
    mg_body = {
        "non_manglik": "Mars aapke chart mein manglik houses (1, 2, 4, 7, 8, 12) mein "
                       "nahi hai — lagna se bhi, Moon se bhi. Rishtey ki baat-cheet mein "
                       "yeh sawaal aaye toh confidently 'nahi' kah sakte hain.",
        "manglik_cancelled": "Mars manglik position mein hai, lekin classical cancellation "
                             "rules apply hote hain: <b>" + ", ".join(mg["cancellations"]) +
                             "</b>. Tradition mein cancelled manglik ko manglik nahi mana "
                             "jaata — matching mein isse issue nahi banna chahiye.",
        "manglik": "Mars manglik houses mein hai. Yeh koi shraap nahi hai — classical "
                   "texts iske liye simple remedial framing dete hain, aur manglik-manglik "
                   "matching mein yeh neutral ho jaata hai. Dar ki nahi, jaankari ki baat hai.",
    }[mg["status"]]

    # ---- page 6: weak periods ----
    weak = _weak_periods(p)
    weak_html = ""
    if weak:
        rows = "".join(f"<div class='quiet'><b>{a} – {b}</b><p>Low-activation phase: "
                       f"matches may come but tend not to convert. Delays here are "
                       f"pattern, not personal failure.</p></div>" for a, b in weak)
        weak_html = f"""
<section class="pg"><p class="plabel">Quiet periods</p>
<h2>Quiet periods — aur unka matlab</h2>
<p>Jitna important yeh jaanna hai ki kab yog strong hai, utna hi yeh ki kab नहीं hai.
In periods mein rishtey aa sakte hain, par convert hone ka pattern weak rehta hai:</p>
{rows}
<p class="soft">Agar pichhle saalon mein baat banti-banti reh gayi ho — chart mein
aksar uski wajah dikh jaati hai. Yeh aapki kami nahi thi; timing thi.</p></section>"""

    # ---- page 7: partner ----
    seventh_sign = sig["seventh_sign"]
    partner_html = f"""
<p><b>7th house — {seventh_sign}:</b> {SIGN_PARTNER[seventh_sign]}.</p>
<p><b>Darakaraka {sig['darakaraka']}:</b> indications of {DK_PARTNER[sig['darakaraka']]}.</p>
<p><b>Meeting context:</b> {"7th lord in house " + str(sig['seventh_lord_house']) +
" suggests the connection may come through that area of life — " +
["self-initiated or through your own efforts", "family networks or finances",
 "siblings, neighbours, or short travels", "home circle or mother's side",
 "social settings, children's events, or romance first", "workplace or daily circles",
 "direct proposals — partnership-driven", "in-law networks or transformative settings",
 "distant places, education circles, or a different community",
 "career settings or father's network", "friends' circles — a friend's introduction",
 "quiet or private settings, possibly at some distance"][sig['seventh_lord_house']-1] + "."}</p>
<p class="soft">Yeh indications hain, portrait nahi — chart directions batata hai,
details zindagi bharti hai.</p>"""

    # ---- page 8: actions ----
    actions = ""
    for i, w in enumerate(p["windows"], 1):
        head, body = GRADE_ACTION[w["grade"]]
        pretty = lambda ym: datetime.strptime(ym, "%Y-%m").strftime("%b %Y")
        actions += (f"<div class='act'><b>Window {i} ({pretty(w['start'])} – "
                    f"{pretty(w['end'])}): {head}</b><p>{body}</p></div>")

    # ---- page 9: summary ----

    # ---------- NEW: past analysis ----------
    ex = p.get("extras", {})
    past_html = ""
    if ex.get("past"):
        rows_p = ""
        lbl = {"active": ("#2E7D53", "ACTIVE"), "mild": ("#E4B04A", "MILD"),
               "quiet": ("#8F92AB", "QUIET")}
        for pp in ex["past"]:
            c, t = lbl[pp["label"]]
            rows_p += (f"<div class='past'><span class='pl' style='background:{c}'>{t}</span>"
                       f"<b>{pp['from']} – {pp['to']}</b>"
                       f"<p class='pd'>{pp['dasha']}</p>"
                       f"<p class='pw'>{' · '.join(pp['why'])}</p></div>")
        past_html = f"""<section class="pg"><p class="plabel">Pichhle saal</p>
<h2>Ab tak kya hua — aur kyun</h2>
<p>Aapke pichhle periods ka chart-analysis. Agar rishtey aaye par bane nahi,
ya bilkul shaant raha — yahan uski wajah dikhegi:</p>{rows_p}
<p class="soft">Yeh section isliye hai taaki aap dekh sakein: timing ek pattern hai,
aapki kami nahi. Jo beet gaya usmein bhi chart ka logic tha.</p></section>"""

    # ---------- NEW: year-by-year outlook ----------
    yo_html = ""
    if ex.get("year_outlook"):
        cards_y = ""
        for y in ex["year_outlook"]:
            gr = (f"<span class='ygrade' style='background:{GRADE_COLOR[y['grade']]}'>{y['grade'].upper()} WINDOW</span>"
                  if y["grade"] else "<span class='ygrade' style='background:#8F92AB'>NO MAJOR WINDOW</span>")
            jup = ("Jupiter ka transit is saal supportive houses mein hai — conversations ko aage badhaane ka saath milega."
                   if y["jupiter_supportive"] else
                   "Jupiter ka transit is saal neutral zone mein hai — effort par zyada, luck par kam depend kijiye.")
            fav = (f"<p class='yfav'>⭐ Favourable months: {', '.join(y['fav_months'])}</p>"
                   if y["fav_months"] else "")
            cards_y += (f"<div class='ycard'><div class='ytop'><b>{y['year']}</b>{gr}</div>"
                        f"<p class='yd'>{' / '.join(y['dashas'])}</p><p>{jup}</p>{fav}</div>")
        yo_html = f"""<section class="pg"><p class="plabel">Saal-dar-saal</p>
<h2>Agle 3 saal — ek nazar mein</h2>{cards_y}
<p class="soft">Yeh page save kar lijiye — har saal ke shuru mein dobara padhne layak hai.</p></section>"""

    # ---------- NEW: love pattern (nakshatra + venus) ----------
    lp_html = ""
    if ex.get("nak_profile"):
        np_ = ex["nak_profile"]
        lp_html = f"""<section class="pg"><p class="plabel">Aapka pattern</p>
<h2>Aap pyaar kaise karte hain — chart ke hisaab se</h2>
<div class="card2"><b>Aapka nakshatra: {np_['nakshatra']} ({np_['symbol']})</b>
<p>{np_['nature']}.</p><p style="margin-top:8px">{np_['relationship']}.</p></div>
<div class="card2" style="margin-top:12px"><b>Aapka Venus</b>
<p>Your love-style is {ex['venus_style']}.</p></div></section>"""

    # ---------- NEW: three checks + sade sati ----------
    ck_html = ""
    if ex.get("checks"):
        ck = ex["checks"]; ss = ex.get("sade_sati", {})
        def yn(v, yes, no):
            return (f"<div class='chk'><span class='cy'>HAAN</span><p>{yes}</p></div>" if v
                    else f"<div class='chk'><span class='cn'>NAHI</span><p>{no}</p></div>")
        ss_html = ""
        if ss.get("active"):
            ss_html = (f"<div class='ss'><b>Sade Sati check: chal rahi hai</b> — {ss['phase']}, "
                       f"till <b>{ss['ends']}</b>. Iska matlab delay ka pressure, denial nahi — "
                       f"Shani ke period mein bani shaadiyan sabse tikau maani jaati hain. "
                       f"Windows upar isi ko account karke grade hue hain.</div>")
        else:
            ss_html = (f"<div class='ss'><b>Sade Sati check: abhi nahi chal rahi.</b> "
                       f"Next phase {ss.get('next_starts','—')} se. Filhaal Shani ka is angle se koi delay-pressure nahi.</div>")
        ck_html = f"""<section class="pg"><p class="plabel">3 aur sach</p>
<h2>Jo aapne nahi poocha, par jaanna chahenge</h2>
{yn(ck['late_marriage_influence'],
"Saturn ka influence aapke 7th house par hai — timing mein maturity-factor hai. Matlab: shaadi thodi der se, par zyada soch-samajh ke. Late ≠ never.",
"Saturn ka koi direct influence aapke 7th house par nahi — classical 'late marriage' indicator aapke chart mein absent hai.")}
{yn(ck['love_leaning'],
"Aapke chart mein 5th–7th connection hai — love-marriage ya self-driven rishtey ka yog. Arranged setup mein bhi pasand aapki hi chalegi.",
"Chart ka jhukaav traditional/arranged path ki taraf hai — introductions aur family networks se hi strong yog banta hai.")}
{yn(ck['foreign_or_intercommunity'],
"Rahu/12th ka 7th se connection hai — partner doori se, alag community se, ya unexpected background se aane ka yog hai. Surprise ke liye taiyaar rahiye.",
"Partner ka yog aapke apne circle aur community ke aas-paas ka hai — door ka yog chart mein prominent nahi.")}
{ss_html}</section>"""

    # ---------- NEW: remedies (agency-first) ----------
    rem_html = ""
    if ex.get("remedies"):
        rm = ex["remedies"]
        gem_line = (f"<li><b>Gemstone:</b> {rm['gem']} — kisi qualified jeweller/astrologer se " 
                    f"trial ke baad hi.</li>" if rm["gem"] else
                    f"<li><b>Gemstone:</b> {rm['gem_note']}</li>")
        rem_html = f"""<section class="pg"><p class="plabel">Weak periods mein</p>
<h2>Traditional support — bina dar ke</h2>
<p>Aapke 7th lord <b>{rm['lord']}</b> ke hisaab se, weak windows mein classical support:</p>
<ul class="rem"><li><b>Vrat/fast:</b> {rm['fast_day']}</li>
<li><b>Mantra:</b> {rm['mantra']} — 108 baar, {rm['fast_day']} ko</li>{gem_line}</ul>
<p class="soft">Order yaad rakhiye: pehla remedy hamesha action hai — strong window mein
actively dhoondhna. Yeh support hai, substitute nahi.</p></section>"""

    w1 = p["windows"][0] if p["windows"] else None
    pretty = lambda ym: datetime.strptime(ym, "%Y-%m").strftime("%b %Y")
    summary = (f"<p class='sline'><b>Top window:</b> {pretty(w1['start'])} – "
               f"{pretty(w1['end'])} ({w1['grade']})</p>" if w1 else "")
    mg_short = {"non_manglik": "No", "manglik_cancelled": "Cancelled (effectively no)",
                "manglik": "Yes — see page 5"}[mg["status"]]
    w2 = p["windows"][1] if p["windows"] and len(p["windows"]) > 1 else None
    _mg_line = {"non_manglik": "Manglik: Nahi — is taraf koi rukaawat nahi.",
                "manglik_cancelled": "Manglik: technically haan, par cancel ho gaya — practically Nahi.",
                "manglik": "Manglik: Haan — page 5 par detail aur cancellation check dekhiye."}[mg["status"]]
    top_summary = ""
    if w1:
        top_summary = (
            "<section class='pg'><div class='ans'>"
            + "<p class='plabel'>Aapka jawab — ek nazar mein</p>"
            + "<h2>Shaadi kab hogi? — seedha jawab</h2>"
            + f"<p class='ans-win'><b>Sabse strong window:</b> {pretty(w1['start'])} – {pretty(w1['end'])} <span class='g'>({w1['grade']})</span></p>"
            + (f"<p class='ans-win2'>Uske baad: {pretty(w2['start'])} – {pretty(w2['end'])} ({w2['grade']})</p>" if w2 else "")
            + f"<p class='ans-mg'>{_mg_line}</p>"
            + "<p class='ans-note'>Yeh jawab aapke poore chart se nikla hai. Neeche har window ki wajah, aapka Navamsa, aur beete periods — taaki aap khud milaa sakein.</p>"
            + "</div></section>"
        )

    rectify_hook = ""
    if meta["time_quality"] in ("T1", "T2", "T3"):
        rectify_hook = """<div class="upsell"><b>Birth time approximate tha?</b>
<p>Rectification analysis aapke life events se exact time narrow karta hai —
windows 6 months tak refine ho sakte hain. <a href='https://wa.me/919650973345?text=RECTIFY' style='color:#C93B2E;font-weight:700'>WhatsApp par RECTIFY bhejiye →</a></p></div>"""

    facts = p["chart"]["planets"]
    sl = sig["seventh_lord"]
    sl_d = facts[sl]["dignity"]
    dignity_txt = {"own": "apne hi sign mein — strong placement",
                   "exalted": "exalted — best possible dignity",
                   "debilitated": "debilitated — timing par extra dhyaan",
                   "neutral": "neutral dignity"}[sl_d]

    return f"""<!DOCTYPE html><html lang="hi-IN"><head>{AX_PRE}<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name} — Marriage Timing Report | Axtroshastra</title>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&display=swap" rel="stylesheet">
<style>
:root{{--ink:#23253B;--midnight:#151C39;--paper:#FAF6ED;--sindoor:#C93B2E;
--haldi:#E4B04A;--haldi-soft:#F6E7C6;--muted:#6B6D82;--line:#E7E0D2;
--display:'Bricolage Grotesque',sans-serif;
--body:-apple-system,'Segoe UI',Roboto,sans-serif}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:var(--body);background:var(--paper);color:var(--ink);line-height:1.6;font-size:15.5px}}
.pg{{max-width:640px;margin:0 auto;padding:40px 22px;border-bottom:1.5px dashed var(--line)}}
.plabel{{font-family:var(--display);font-weight:700;font-size:11px;letter-spacing:.16em;
text-transform:uppercase;color:var(--sindoor);margin-bottom:10px}}
h1,h2{{font-family:var(--display);line-height:1.15}}
h2{{font-size:24px;font-weight:800;margin-bottom:14px}}
.soft{{color:var(--muted);font-size:13.5px;margin-top:14px}}
/* cover */
.cover{{background:radial-gradient(900px 500px at 50% -10%,#1D2547,var(--midnight));
color:#F3EFE4;text-align:center;border:none}}
.cover .brand{{font-family:var(--display);font-weight:800;color:var(--haldi);
letter-spacing:.06em;font-size:14px;margin-bottom:26px}}
.cover h1{{font-size:30px;font-weight:800;color:#fff}}
.cover .bd{{color:#A9ABC0;font-size:13.5px;margin:8px 0 24px}}
.kchart{{max-width:320px;margin:0 auto}}
.cover .method{{font-size:11.5px;color:#8F92AB;margin-top:20px}}
/* snapshot */
.facts{{background:#fff;border:1.5px solid var(--line);border-radius:14px;padding:6px 18px}}
.facts .row{{display:flex;justify-content:space-between;gap:14px;padding:11px 0;
border-bottom:1px dashed var(--line);font-size:14.5px}}
.facts .row:last-child{{border:none}}
.facts .k{{color:var(--muted)}}.facts .v{{font-weight:700;text-align:right}}
/* timeline + windows */
.tl{{background:var(--midnight);border-radius:14px;padding:18px 14px 12px;margin:18px 0}}
.tltrack{{position:relative;height:40px;background:#1D2547;border-radius:8px;overflow:hidden}}
.tlw{{position:absolute;top:0;bottom:0;opacity:.9}}
.tlyrs{{display:flex;justify-content:space-between;color:#7C7F99;font-size:10.5px;margin-top:7px}}
.wcard{{background:#fff;border:1.5px solid var(--line);border-left:6px solid;
border-radius:14px;padding:18px;margin-bottom:14px}}
.wtop{{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}}
.wnum{{font-family:var(--display);font-weight:700;font-size:12px;letter-spacing:.1em;
text-transform:uppercase;color:var(--muted)}}
.wgrade{{color:#fff;font-family:var(--display);font-weight:800;font-size:11px;
letter-spacing:.08em;border-radius:20px;padding:4px 12px}}
.wdates{{font-family:var(--display);font-weight:800;font-size:22px}}
.core{{font-size:13px;color:var(--muted);margin-top:2px}}
.peak{{font-size:13.5px;color:#2E7D53;font-weight:600;margin-top:6px}}
.wdasha{{font-size:12.5px;color:var(--muted);margin-top:6px}}
.wwhy{{margin:10px 0 0 18px;font-size:13.5px}}.wwhy li{{margin-bottom:4px}}
/* manglik */
.mgcard{{background:var(--haldi-soft);border-radius:14px;padding:20px}}
.mgcard b.h{{font-family:var(--display);font-size:17px;display:block;margin-bottom:8px}}
/* quiet + actions */
.quiet,.act{{background:#fff;border:1.5px solid var(--line);border-radius:12px;
padding:14px 16px;margin-bottom:10px;font-size:14.5px}}
.quiet b,.act b{{font-family:var(--display)}}
/* summary */
.sumcard{{background:var(--midnight);color:#F3EFE4;border-radius:16px;padding:24px;text-align:center}}
.sumcard .nm{{font-family:var(--display);font-weight:800;font-size:20px;color:#fff}}
.sline{{margin-top:10px;font-size:15px}}
.sumcard .sline b{{color:var(--haldi)}}
.past{{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:10px}}
.pl{{color:#fff;font-family:var(--display);font-weight:800;font-size:10.5px;letter-spacing:.08em;border-radius:16px;padding:3px 10px;margin-right:10px}}
.pd{{font-size:12.5px;color:var(--muted);margin-top:5px}}.pw{{font-size:13.5px;margin-top:4px}}
.ycard{{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:15px 16px;margin-bottom:10px}}
.ytop{{display:flex;justify-content:space-between;align-items:center;font-family:var(--display);font-size:19px;margin-bottom:6px}}
.ygrade{{color:#fff;font-family:var(--display);font-weight:800;font-size:10.5px;letter-spacing:.06em;border-radius:16px;padding:4px 10px}}
.yd{{font-size:12.5px;color:var(--muted);margin-bottom:5px}}.ycard p{{font-size:14px}}
.yfav{{color:#2E7D53;font-weight:600;font-size:13.5px;margin-top:5px}}
.card2{{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:16px}}
.card2 b{{font-family:var(--display);display:block;margin-bottom:6px}}.card2 p{{font-size:14.5px}}
.chk{{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:10px;display:flex;gap:12px;align-items:flex-start}}
.cy,.cn{{flex:none;color:#fff;font-family:var(--display);font-weight:800;font-size:11px;border-radius:16px;padding:4px 11px;margin-top:2px}}
.cy{{background:#2E7D53}}.cn{{background:#8F92AB}}.chk p{{font-size:14px}}
.ss{{background:var(--haldi-soft);border-radius:12px;padding:15px;font-size:14px;margin-top:14px}}
.rem{{margin:12px 0 0 20px}}.rem li{{margin-bottom:8px;font-size:14.5px}}
.upsell{{background:#fff;border:2px solid var(--haldi);border-radius:14px;
padding:16px;margin-top:16px;font-size:14px}}
.btnrow{{display:flex;gap:10px;margin-top:20px}}
.btn{{flex:1;font-family:var(--display);font-weight:800;font-size:14px;text-align:center;
padding:13px;border-radius:11px;border:0;cursor:pointer;text-decoration:none}}
.btn.p{{background:var(--sindoor);color:#fff}}.btn.s{{background:#fff;border:1.5px solid var(--line);color:var(--ink)}}
footer{{text-align:center;font-size:11.5px;color:var(--muted);padding:26px 20px 44px;max-width:640px;margin:0 auto}}
@media print{{.btnrow{{display:none}}.pg{{border:none;padding:14px 6px;max-width:100%}}
.wcard,.mgcard,.quiet,.act,.ycard,.card2,.chk,.past,.ss,.rem,.upsell,.ans,.sumcard,.review,.facts .row,.acard{{break-inside:avoid}}
.cover{{padding:40px 8px}}
body{{background:#fff}}.cover{{background:var(--midnight)!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}}}}
</style></head><body>

<section class="pg cover">
  <p class="brand">✦ AXTROSHASTRA</p>
  <h1>{name}</h1>
  <p class="bd">Marriage Timing Report · Generated {meta['generated']}</p>
  {north_chart_svg(p)}
  <p class="method">NASA JPL data (Swiss Ephemeris) · Lahiri ayanamsa · Whole-sign houses · {system_note}</p>
</section>

{top_summary}
<section class="pg"><p class="plabel">Chart snapshot</p>
<h2>Aapka chart — marriage lens se</h2>
<div class="facts">
  <div class="row"><span class="k">Lagna</span><span class="v">{p['chart']['lagna']}</span></div>
  <p class="why">Aapki personality aur poore chart ka base — har bhaav isi se gina jaata hai.</p>
  <div class="row"><span class="k">Moon · Nakshatra</span><span class="v">{p['teaser']['moon_sign']} · {p['teaser']['nakshatra']}</span></div>
  <p class="why">Aapka mann aur emotional nature. Aapki dasha timeline isi Moon-nakshatra se chalti hai — yahi timing ka engine hai.</p>
  <div class="row"><span class="k">7th house</span><span class="v">{seventh_sign}</span></div>
  <p class="why">Shaadi, partner aur commitment ka ghar — marriage ka main area.</p>
  <div class="row"><span class="k">7th lord</span><span class="v">{sl} — {dignity_txt}</span></div>
  <p class="why">Shaadi ka main switch. Iski dignity (upar) timing ki quality batati hai — strong matlab saaf timing, tender matlab zyada soch-samajh.</p>
  <div class="row"><span class="k">Marriage karaka</span><span class="v">{' + '.join(sig['karakas'])}</span></div>
  <p class="why">Rishton ka natural indicator (Venus/Jupiter) — yeh shaadi ka promise dikhata hai.</p>
  <div class="row"><span class="k">Darakaraka</span><span class="v">{sig['darakaraka']}</span></div>
  <p class="why">Jaimini system ka spouse-significator — partner ki ek jhalak.</p>
  <div class="row"><span class="k">Current period</span><span class="v">{p['teaser']['current_dasha']}<br>till {p['teaser']['dasha_till']}</span></div>
  <p class="why">Abhi kaunsi dasha chal rahi hai. Windows isi timeline par bante hain — isliye yeh sabse relevant.</p>
</div>
<p class="soft">Yeh 6-7 factors milkar aapki marriage timing decide karte hain.
Agle page par inhi se nikale gaye aapke windows hain.</p></section>
{report_addons.planet_table_html(p)}

<section class="pg"><p class="plabel">The Answer</p>
<h2>Aapke marriage windows</h2>
<div class="tl"><div class="tltrack">{tl_windows}</div>
<div class="tlyrs">{years_axis}</div></div>
{window_cards}</section>

<section class="pg"><p class="plabel">Method</p>
<h2>Yeh windows kaise nikle</h2>
<p>Har window ke card mein uske reasons diye hain — kaunsi dasha, kaunsa connection.
Broad logic: <b>marriage typically triggers jab dasha/antardasha lord aapke 7th house
ya uske lord se connect hota hai, aur Jupiter ka transit usko confirm karta hai.</b></p>
<p style="margin-top:10px">Timing windows probability bands hain, appointments nahi —
±15 minute ka birth time difference bhi boundaries ko months tak shift kar sakta hai.
Isliye hum honest ranges dete hain, fake precision nahi.</p></section>
{report_addons.scoring_box_html(p)}

<section class="pg"><p class="plabel">Manglik</p>
<h2>Manglik check</h2>
<div class="mgcard"><b class="h">{mg_head}</b><p>{mg_body}</p></div>
<p class="soft">Technical: Mars from lagna — {'manglik houses mein' if mg['from_lagna'] else 'clear'};
from Moon — {'manglik houses mein' if mg['from_moon'] else 'clear'}.</p></section>
{report_addons.d9_section_html(p)}

{weak_html}
{past_html}
{yo_html}

<section class="pg"><p class="plabel">Partner</p>
<h2>Partner indications</h2>
{partner_html}
{report_addons.occupants_html(p)}</section>

<section class="pg"><p class="plabel">Action plan</p>
<h2>Ab karna kya hai</h2>
{actions}
<p class="soft">Kundli timing batati hai; effort aur choice aapke haath mein hai.
Strong window mein bhi rishtey dhoondhne padte hain — bas conversion rate better hota hai.</p></section>

{lp_html}
{ck_html}
{rem_html}

<section class="pg"><p class="plabel">Summary</p>
<div class="sumcard">
  <p class="nm">{name}</p>
  {summary}
  <p class="sline"><b>Manglik:</b> {mg_short}</p>
  <p class="sline"><b>Partner direction:</b> {sig['darakaraka']}-type — see page 7</p>
</div>
{rectify_hook}
<div class="upsell"><b>Ek aur sawaal, usi chart se: career kab lift hoga?</b>
<p>Career Timing Report — same precision, ₹299 for report holders. <a href='https://wa.me/919650973345?text=CAREER' style='color:#C93B2E;font-weight:700'>WhatsApp par CAREER bhejiye →</a></p></div>
<div class="btnrow">
  <a class="btn p" id="ax-pdf" href="#" onclick="window.print();return false;">Download PDF</a> <button class="ax-share" onclick="axShare()">Share on WhatsApp</button>
  <a class="btn s" href="https://wa.me/919650973345?text=Hi%20Axtroshastra">WhatsApp Support</a>
</div></section>

<footer>Windows are probability estimates from classical dasha–transit principles,
not guarantees. <a href='https://wa.me/919650973345' style='color:inherit'>WhatsApp +91 96509 73345</a> · axtroshastra@gmail.com<br>Axtroshastra · Computational Vedic Astrology · by Cultnuts · <a href="/privacy" style="color:inherit">Privacy</a> · <a href="/terms" style="color:inherit">Terms</a> · <a href="/refunds" style="color:inherit">Refund Policy</a></footer>
        <div class="ax-wm" aria-hidden="true"><b>AXTROSHASTRA</b><span>axtroshastra.com</span></div>
<section class="pg"><div class="ax-disc"><b>Disclaimer:</b> Yeh report classical Vedic Jyotish (dasha-transit) principles par computed hai — guidance ke liye, guarantee nahi. Timing windows probability hain, fixed dates nahi. Yeh legal, medical ya financial advice nahi hai. Apne life decisions aap apni samajh se lijiye; Axtroshastra kisi outcome ki zimmedari nahi leta.</div><div class="ax-endcard"><b>Axtroshastra</b><br>Yeh report Axtroshastra ne banayi — apna report paayein: <a href="https://www.axtroshastra.com/shaadi">axtroshastra.com</a></div></section>
{REPORT_I18N}
</body></html>"""


# ============================================================ MILAN RENDERER
VERDICT_COLOR = {"excellent": "#2E7D53", "verygood": "#2E7D53",
                 "ok": "#E4B04A", "weak": "#C93B2E"}

# Plain-language decode of each classical koota — modern label + emoji + real-life meaning.
# Sanskrit name (the dict key) is kept as a small credibility subtitle in the UI.
KOOTA_UI = {
    "Varna":        {"emoji": "🧭", "label": "Drive & Ego Balance",
                     "blurb": "who naturally takes the lead — without it turning into a power struggle"},
    "Vashya":       {"emoji": "🧲", "label": "Mutual Pull",
                     "blurb": "how naturally you're drawn to and influence each other"},
    "Tara":         {"emoji": "🍀", "label": "Luck & Wellbeing",
                     "blurb": "whether being together tends to make life feel smoother for you both"},
    "Yoni":         {"emoji": "🔥", "label": "Physical Chemistry",
                     "blurb": "instinctive, physical and intimate compatibility"},
    "Graha Maitri": {"emoji": "🧠", "label": "Mental Wavelength",
                     "blurb": "how easily your minds click and how you talk things through"},
    "Gana":         {"emoji": "🎭", "label": "Vibe & Temperament",
                     "blurb": "your everyday energy, social style and how your moods land"},
    "Bhakoot":      {"emoji": "❤️", "label": "Emotional Bond",
                     "blurb": "long-term closeness and building a life and family together"},
    "Nadi":         {"emoji": "🧬", "label": "Health & Family",
                     "blurb": "vitality and the classical health / progeny factor"},
}

# 5 relatable themes that group the 8 kootas (each koota belongs to exactly one).
THEMES = [
    {"emoji": "🔥", "name": "Chemistry & Attraction", "kootas": ["Yoni", "Vashya"],
     "blurb": "the spark — physical pull and how you gravitate toward each other"},
    {"emoji": "🎭", "name": "Everyday Vibe", "kootas": ["Gana"],
     "blurb": "your day-to-day energy and whether your moods sync"},
    {"emoji": "🧠", "name": "Mind & Values", "kootas": ["Graha Maitri", "Varna"],
     "blurb": "how your minds click, and who leads what"},
    {"emoji": "❤️", "name": "Love & Long-Term", "kootas": ["Bhakoot", "Tara"],
     "blurb": "long-term closeness and how good you are for each other"},
    {"emoji": "🧬", "name": "Health & Vitality", "kootas": ["Nadi"],
     "blurb": "vitality and the traditional family / progeny factor"},
]

def _theme_rows(kootas: list) -> str:
    """Build the 5-theme 'at a glance' cards, strongest first (confidence-first)."""
    out = ""
    for t in _theme_scores(kootas):
        th, got, mx, pct = t["theme"], t["got"], t["mx"], t["pct"]
        if pct >= 75:
            chip, chip_bg, bar_color, verdict = "Strong 💚", "#2E7D53", "#2E7D53", "You're naturally strong here."
        elif pct >= 45:
            chip, chip_bg, bar_color, verdict = "Solid 💛", "#B4881B", "#E4B04A", "Good foundation — a little effort keeps it easy."
        else:
            chip, chip_bg, bar_color, verdict = "Needs work ❤️‍🔥", "#C93B2E", "#C93B2E", "Takes a little conscious effort — and the exact fix is on this factor's card in the breakdown below. 👇"
        got_disp = int(got) if float(got).is_integer() else got
        out += f"""<div class='theme'>
<div class='ttop'><span class='temoji'>{th['emoji']}</span><b>{th['name']}</b>
<span class='tchip' style='background:{chip_bg}'>{chip}</span></div>
<div class='kbar'><div style='width:{pct:.0f}%;background:{bar_color}'></div></div>
<p class='tblurb'>{th['blurb']}. <b>{verdict}</b></p></div>"""
    return out

# For weak / non-matching factors: a practical thing to work on + an optional
# traditional remedy. Agency-first — the action is the real lever, the remedy is
# a cultural add-on for those who want it. No medical or gemstone-buying claims.
# Each weak factor gets: a shared "together" line, a clear who-does-what split
# (p1/p2 by name where the two jobs genuinely differ, or "each" where the action
# is the same for both), and an optional traditional remedy. Splitting the
# responsibility means neither partner assumes the other will handle it.
REMEDIES = {
    "Varna": {
        "work_on": "Spell out who owns which calls — money, home, plans, social life — out loud, instead of assuming.",
        "p1": "Name the one area you most want to lead — and say it plainly.",
        "p2": "Name the one area you're happy to hand over — and genuinely let go of it.",
        "remedy": "A gentle classical practice: offer water to the rising sun together on Sunday mornings — a small shared ritual said to balance ego and authority."},
    "Vashya": {
        "work_on": "A lower pull just means the bond runs on respect, not gravity — so make closeness deliberate, not left to chance.",
        "p1": "Own the plan — set up one proper, protected date this week.",
        "p2": "Own the daily thread — keep the small check-ins going through the week.",
        "remedy": "Venus rules attraction — on Fridays keep something white nearby and repeat 'Om Shukraya Namah' a few times together."},
    "Tara": {
        "work_on": "Make each other's wellbeing a shared project — sleep, food, stress — instead of assuming the other is fine.",
        "p1": "Keep an eye on the basics — nudge each other on rest, food and sleep.",
        "p2": "Keep an eye on the load — check in on stress and what's draining them.",
        "remedy": "On Thursdays, share a simple home-cooked meal and donate a little food or grain together — a traditional gesture for mutual wellbeing."},
    "Yoni": {
        "work_on": "This is about different instincts, not low attraction — so talk openly about pace, touch and daily rhythms.",
        "each": "Name one rhythm — sleep, space or affection — you'd like the other to understand, and ask for theirs.",
        "remedy": "Venus is your ally here too — Friday is the day; soft, warm tones at home and 'Om Shukraya Namah' are the classical nudges for closeness."},
    "Graha Maitri": {
        "work_on": "You think in different 'languages', so practise translating before you react.",
        "each": "In a disagreement, say your partner's point back in their words before you reply — until they say 'yes, that's it.'",
        "remedy": "For mental harmony: green on Wednesdays with 'Om Budhaya Namah' (Mercury), and an unhurried moonlit walk together on Mondays (Moon)."},
    "Gana": {
        "work_on": "Your energies genuinely differ (say, one loves a crowd, one loves quiet). Don't try to fix it — design around it.",
        "each": "Tell the other plainly what recharges you — a night out or a night in — and agree a simple signal for it.",
        "remedy": "A shared calming ritual helps — light a small oil lamp at dusk and chant 'Om Namah Shivaya' together; traditionally it settles temperament clashes."},
    "Bhakoot": {
        "work_on": "The classic risks here are emotional distance and money friction — get ahead of both, and keep daily affection non-negotiable.",
        "p1": "Own the money rhythm — a light monthly 'us & money' check-in.",
        "p2": "Own the emotional rhythm — a regular, honest 'how are we, really?' talk.",
        "remedy": "A Moon remedy: on Mondays wear white, chant 'Om Somaya Namah', and offer milk or white flowers at a Shiva temple together."},
    "Nadi": {
        "work_on": "Traditionally the heaviest factor, tied to health and children — so the real 'remedy' is proactive care, together.",
        "each": "Book your own basics — a check-up, better sleep, less chronic stress; treat wellbeing as a team sport.",
        "remedy": "A classical Nadi practice is the Maha Mrityunjaya mantra and donating toward medicines/health; the modern equivalent is a simple pre-marriage health check for both."},
}

def _koota_fix_html(k: dict, cancelled: set, names=("Partner 1", "Partner 2")) -> str:
    """Inline fix + who-does-what split + traditional remedy, rendered INSIDE a weak
    koota's own card so the concern and its answer are never separated (anxiety stays
    low). The split divides responsibility so neither partner assumes the other will act."""
    if not (k["max"] and k["score"] / k["max"] < 0.5):
        return ""
    rem = REMEDIES.get(k["name"])
    if not rem or not rem.get("work_on"):
        return ""
    n1, n2 = names
    ap = ACTION_PLAN.get(k["name"])
    canc = ("<p class='wcanc'>✅ Traditionally cancelled for you — treat this as a lighter priority.</p>"
            if k["name"] in cancelled else "")
    # who does what — split the responsibility clearly
    if rem.get("each"):
        split = f"<div class='wsplit'><p><span class='wpk'>👥 Each of you</span> {rem['each']}</p></div>"
    else:
        rows = ""
        if rem.get("p1"): rows += f"<p><span class='wpk'>👤 {n1}</span> {rem['p1']}</p>"
        if rem.get("p2"): rows += f"<p><span class='wpk'>👤 {n2}</span> {rem['p2']}</p>"
        split = f"<div class='wsplit'>{rows}</div>" if rows else ""
    talk = (f"<p class='wtalk'><b>💬 Say this:</b> {ap['talk']}</p>"
            if ap and ap.get("talk") else "")
    rem_line = (f"<p class='wrem'><b>🪔 Traditional remedy:</b> {rem['remedy']}</p>"
                if rem.get("remedy") else "")
    return (f"<div class='kfix'>{canc}"
            f"<p class='wdo'><b>💡 Work on it — together:</b> {rem['work_on']}</p>"
            f"{split}{talk}{rem_line}</div>")

# ---------------- Phase-1 expanded-report content + builders ----------------
ELEMENT_EMOJI = {"fire": "🔥", "earth": "🌿", "air": "💨", "water": "🌊"}

LOVE_LANG = {
    "fire": "being pursued — spontaneity, passion, and a partner who matches your spark",
    "earth": "being shown up for — reliability, steady effort, and physical care",
    "air": "being understood — real conversation, wit, and mental connection",
    "water": "being felt — emotional attunement, tenderness, and a sense of safety",
}

# Couple archetype keyed by the frozenset of the two Moon elements (same-element sets have 1 item).
ARCHETYPE = {
    frozenset({"fire"}): {"name": "The Passionate Pair", "emoji": "🔥", "tagline": "Two sparks, double the passion",
        "body": "You two run hot — big feelings, big fun, and the occasional big argument that's over as fast as it started. Your superpower is intensity; your homework is learning that only one of you needs to catch fire at a time."},
    frozenset({"earth"}): {"name": "The Steady Pair", "emoji": "🏡", "tagline": "Steady, safe, built to last",
        "body": "You're the couple friends call 'solid'. You value security, loyalty and a life built brick by brick. The only risk: don't let the routine quietly replace the romance."},
    frozenset({"air"}): {"name": "The Best Friends", "emoji": "💭", "tagline": "Endless talks, always on the same page",
        "body": "You'll never run out of things to talk about — ideas, plans, jokes only you two get. The thing to practise together: turning all those brilliant plans into actual decisions."},
    frozenset({"water"}): {"name": "The Deep Feelers", "emoji": "🌊", "tagline": "You feel everything, together",
        "body": "Rare, almost wordless understanding — you read each other's moods like weather. Beautiful, but when you're both caught in a wave, someone has to be the calm shore."},
    frozenset({"fire", "earth"}): {"name": "Passion Meets Patience", "emoji": "🔥🌿", "tagline": "Drive meets steadiness",
        "body": "One of you brings the pace, the other the patience. Fire learns to slow down, earth learns to loosen up — and together you actually build the things you dream about."},
    frozenset({"fire", "air"}): {"name": "The Adventurers", "emoji": "🔥💨", "tagline": "Energy that keeps growing",
        "body": "Air feeds the flame — adventures, plans, natural chemistry. You both love to fly; just decide early who's handling the landing."},
    frozenset({"fire", "water"}): {"name": "The Magnetic Pair", "emoji": "🔥🌊", "tagline": "Strong pull, strong feelings",
        "body": "Fire and water make steam — magnetic attraction and big reactions. Fire learns softness, water learns directness. It takes effort, and it makes magic."},
    frozenset({"earth", "air"}): {"name": "The Dreamer & The Builder", "emoji": "🌿💨", "tagline": "Ideas meet real plans",
        "body": "Air brings the ideas, earth makes them real. Your different speeds are the friction — and exactly what makes you complete each other."},
    frozenset({"earth", "water"}): {"name": "The Caring Pair", "emoji": "🌿🌊", "tagline": "The most naturally caring match",
        "body": "Soil and water — classical texts call this innately compatible. One gives security, the other depth. This is the easy, home-feeling kind of love."},
    frozenset({"air", "water"}): {"name": "Head & Heart", "emoji": "💭🌊", "tagline": "Clear thinking meets deep feeling",
        "body": "Air learns that not everything is logic; water learns that not everything can go unsaid. Build that bridge and it's pure poetry."},
}
ARCHETYPE_DEFAULT = {"name": "One of a Kind", "emoji": "✨", "tagline": "Your own kind of match",
    "body": "You don't fit a neat box — which is its own kind of interesting."}

# Rich strength copy, keyed by theme name (shown when a theme is strong).
THEME_DEEP = {
    "Chemistry & Attraction": "The spark is real and it's mutual — you're drawn to each other in a way that doesn't need forcing. That easy physical comfort is something a lot of couples spend years trying to build. Keep novelty alive and it stays a strength, not a given.",
    "Everyday Vibe": "Your day-to-day energies just fit — similar social batteries, similar humour, a similar way of handling good days and bad ones. This is the quiet superpower that makes living together feel light instead of like work.",
    "Mind & Values": "You think in the same language. Even your disagreements will make sense to each other, because your values and mental wiring line up. This is the stuff long conversations — and long marriages — are made of.",
    "Love & Long-Term": "Emotionally, you're built to go the distance. Classical texts read this as a green signal for closeness, family and growing together — the deep, settle-in kind of bond rather than just a spark.",
    "Health & Vitality": "On the heaviest traditional factor, you're clear — read as vitality and a healthy foundation for a life (and a family) together. It's the factor astrologers weigh the most, and it's working in your favour.",
}

# Extra action-plan detail for weak factors, keyed by koota.
ACTION_PLAN = {
    "Varna": {"try": "This week, each of you names one area you'd love to lead and one you'd happily hand over.", "talk": "“Where do you want me to take charge — and where do you want to?”", "green": "You stop quietly keeping score of who decided what."},
    "Vashya": {"try": "Lock one proper date into the calendar for the next two weeks — non-negotiable.", "talk": "“What makes you feel closest to me?”", "green": "Time together starts to feel chosen, not squeezed in."},
    "Tara": {"try": "Do one small health thing together — a walk, cooking a real meal, an early night.", "talk": "“What's been draining you lately, and how can I help?”", "green": "You both feel better after time together, not more tired."},
    "Yoni": {"try": "Compare your daily rhythms — sleep, energy, affection — and pick one to sync.", "talk": "“What does feeling close look like for you, day to day?”", "green": "Different paces stop feeling like rejection."},
    "Graha Maitri": {"try": "One 20-minute, phones-away conversation this week — no fixing, just listening.", "talk": "“Let me say that back — did I get it right?”", "green": "You argue in the same language, not past each other."},
    "Gana": {"try": "Agree a simple signal for 'I need people' vs 'I need quiet' — and honour it once.", "talk": "“What recharges you — a night out, or a night in?”", "green": "Different moods stop getting taken personally."},
    "Bhakoot": {"try": "Do a light 15-minute 'us, money & feelings' check-in.", "talk": "“What's something you've been carrying that I haven't noticed?”", "green": "Small distances get named before they grow."},
    "Nadi": {"try": "Book the unglamorous stuff — check-ups, good sleep, less chronic stress — as a team.", "talk": "“How do we want to look after each other's health?”", "green": "You treat wellbeing as a shared project, not a solo one."},
}


def _theme_scores(kootas: list) -> list:
    """Per-theme aggregate scores, strongest first."""
    by = {k["name"]: k for k in kootas}
    out = []
    for th in THEMES:
        got = sum(by[n]["score"] for n in th["kootas"] if n in by)
        mx = sum(by[n]["max"] for n in th["kootas"] if n in by)
        out.append({"theme": th, "got": got, "mx": mx, "pct": (got / mx * 100) if mx else 0})
    out.sort(key=lambda t: t["pct"], reverse=True)
    return out


def _archetype(profiles: dict) -> dict:
    return ARCHETYPE.get(frozenset({profiles["p1"]["element"], profiles["p2"]["element"]}), ARCHETYPE_DEFAULT)


def _match_band(pct: int):
    if pct >= 80: return ("an exceptional match", "#2E7D53")
    if pct >= 67: return ("a strong match", "#2E7D53")
    if pct >= 50: return ("a workable match", "#B4881B")
    return ("a match that'll take some work", "#C93B2E")


def _match_pct(p: dict) -> int:
    return int(p.get("match_pct") or round(p.get("effective", p["total"]) / 36 * 100))


def _share_text(p: dict) -> str:
    """Personalised share caption (couple type + match %). Plain text, not HTML."""
    arche = _archetype(p["profiles"]); pct = _match_pct(p)
    p1 = p["profiles"]["p1"]["name"]; p2 = p["profiles"]["p2"]["name"]
    return (f"{p1} ✕ {p2}: turns out we're {arche['name']} {arche['emoji']} — "
            f"{pct}% compatible on what actually matters 💫 Checked it on Axtroshastra:")


def _opening_note(p: dict) -> str:
    arche = _archetype(p["profiles"])
    ts = _theme_scores(p["kootas"])
    p1 = escape(p["profiles"]["p1"]["name"]); p2 = escape(p["profiles"]["p2"]["name"])
    pct = _match_pct(p); phrase, _ = _match_band(pct)
    top = ts[0]["theme"]; weak = ts[-1]
    strong_line = f"You're strongest in <b>{top['name'].lower()}</b> — {top['blurb']}."
    if weak["pct"] < 55:
        grow_line = (f" The one area worth a little intention is <b>{weak['theme']['name'].lower()}</b> — "
                     "and we've put simple, doable steps for it further down.")
    else:
        grow_line = " And honestly, there's no weak link here worth losing sleep over."
    return (f"<div class='opennote'><p>{p1} &amp; {p2} — on the classical Ashtakoota system you come out as "
            f"<b>{arche['name']}</b> {arche['emoji']}, {phrase} at <b>{pct}%</b> on the things that actually "
            f"matter in a relationship.</p><p>{strong_line}{grow_line}</p>"
            f"<p class='onsub'>Here's the full picture — the good stuff first. 💛</p></div>")


def _sharecard_html(p: dict) -> str:
    arche = _archetype(p["profiles"])
    ts = _theme_scores(p["kootas"])
    strong = [t for t in ts if t["pct"] >= 60][:3] or ts[:2]
    chips = "".join(f"<span class='scchip'>{t['theme']['emoji']} {t['theme']['name']}</span>" for t in strong)
    p1 = escape(p["profiles"]["p1"]["name"]); p2 = escape(p["profiles"]["p2"]["name"])
    pct = _match_pct(p)
    return (f"<div class='sharecard' id='sharecard'>"
            f"<div class='scbrand'>✦ AXTROSHASTRA · COMPATIBILITY</div>"
            f"<div class='scnames'>{p1} <span>✕</span> {p2}</div>"
            f"<div class='scarch'>{arche['emoji']} {arche['name']}</div>"
            f"<div class='scpct'>{pct}<small>% match on what matters</small></div>"
            f"<div class='scchips'>{chips}</div>"
            f"<div class='sctag'>“{arche['tagline']}”</div></div>"
            f"<p class='sctag2'>{arche['body']}</p>"
            f"<div class='sharebtns'>"
            f"<button class='sharebtn' onclick='axShare()'>Share link 💫</button>"
            f"</div>")


def _milan_chart_block(pr: dict) -> str:
    """Render this partner's kundli. Lagna chart when the birth time is known,
    otherwise a Moon chart (stable, honest, and consistent with Moon-based matching)."""
    ch = pr.get("chart")
    if not ch or not ch.get("planets"):
        return ""
    tk = ch.get("time_known")
    house1 = ch["lagna"] if tk else ch.get("moon_sign", ch["lagna"])
    svg = north_chart_svg({"chart": {"lagna": house1, "planets": ch["planets"]}})
    cap = ("Lagna (ascendant) chart — cast from the exact birth time"
           if tk else "Moon chart — from date &amp; place (birth time not given, so the ascendant isn't fixed)")
    return f"<div class='kchartwrap'>{svg}<p class='kcap'>{cap}</p></div>"


def _profiles_html(p: dict) -> str:
    def card(who):
        pr = p["profiles"][who]
        el = pr["element"]
        return (f"<div class='prof'>"
                f"<div class='prtop'><span class='prel'>{ELEMENT_EMOJI.get(el,'✨')}</span>"
                f"<span class='prname'><b>{escape(pr['name'])}</b>"
                f"<span class='prsign'>{pr['sign']} Moon · {pr['nak']} nakshatra</span></span></div>"
                f"<p class='prline'><b>Their nature:</b> {pr['persona']}.</p>"
                f"<p class='prline'><b>In love:</b> {pr['love']}.</p>"
                f"<p class='prline'><b>Feels most loved by:</b> {LOVE_LANG.get(el,'')}.</p>"
                f"{_milan_chart_block(pr)}</div>")
    has_chart = bool(p["profiles"].get("p1", {}).get("chart"))
    legend = ("<p class='klegend'>Chart key: <b>Su</b> Sun · <b>Mo</b> Moon · <b>Ma</b> Mars · "
              "<b>Me</b> Mercury · <b>Ju</b> Jupiter · <b>Ve</b> Venus · <b>Sa</b> Saturn · "
              "<b>Ra</b> Rahu · <b>Ke</b> Ketu · ↺ retrograde. The small numbers are the zodiac "
              "signs (1 Aries … 12 Pisces). This is the North-Indian style your family astrologer uses — "
              "so you can verify every placement yourself.</p>") if has_chart else ""
    return ("<h2>The two of you, decoded 🔮</h2>"
            "<p class='lead'>A quick read on each of you — plus your actual birth chart, "
            "drawn from your Moon sign and birth-star (nakshatra).</p>"
            f"<div class='profwrap'>{card('p1')}{card('p2')}</div>{legend}")


def _strength_deepdive_html(p: dict) -> str:
    strong = [t for t in _theme_scores(p["kootas"]) if t["pct"] >= 60]
    if not strong:
        return ""
    items = "".join(
        f"<div class='deep'><div class='dtop'><span class='demoji'>{t['theme']['emoji']}</span>"
        f"<b>{t['theme']['name']}</b></div><p>{THEME_DEEP.get(t['theme']['name'],'')}</p></div>"
        for t in strong)
    return ("<h2>Why you two work 💚</h2>"
            "<p class='lead'>The areas where you're genuinely strong — and what they'll feel like in real life.</p>"
            + items)


def _askbesties_html(p: dict) -> str:
    return ("<h2>Share it with your friends 💌</h2>"
            "<div class='besties'>"
            "<p>Share this report with a few friends who know you both. Then ask them the "
            "real question: <b>“Does this actually sound like us?”</b></p>"
            "<p>The people close to you know you better than any chart — their gut-check is the best second "
            "opinion you'll get. And for the bits marked <b>‘work on it’</b>, they're exactly the people who'll "
            "keep you honest and cheer you on.</p>"
            "<div class='sharebtns'>"
            "<button class='sharebtn' onclick='axShare()'>Share link 💫</button></div>"
            "<div class='friendnote'><b>👀 Hey — did a friend send you this?</b>"
            "<p>They shared it because your honest take matters more than any chart. Two ways to be a great "
            "friend right now: tell them if the ‘you two’ bits actually ring true, and for anything marked "
            "<b>‘work on it’</b>, be the one who cheers them on. That's the whole point. 💛</p></div>"
            "<p class='bnote'>Shared with love · your report stays private unless you send it.</p></div>")


def _certificate_html(p: dict) -> str:
    arche = _archetype(p["profiles"]); pct = _match_pct(p)
    p1 = escape(p["profiles"]["p1"]["name"]); p2 = escape(p["profiles"]["p2"]["name"])
    return ("<h2>Your keepsake ✦</h2>"
            "<div class='cert'><div class='certin'>"
            "<div class='certseal'>✦</div>"
            "<div class='certk'>Certificate of Compatibility</div>"
            f"<div class='certnames'>{p1} <span>&amp;</span> {p2}</div>"
            f"<div class='certarch'>are officially<br><b>{arche['emoji']} {arche['name']}</b></div>"
            f"<div class='certpct'>{pct}% match on what matters</div>"
            f"<div class='certfoot'>Computed {p['meta']['generated']} · Classical Ashtakoota system<br>"
            "✦ AXTROSHASTRA · Computational Vedic Astrology</div>"
            "</div></div>")


def _method_html(p: dict, m: dict) -> str:
    def row(pr):
        return (f"<tr><td>{escape(pr['name'])}</td><td>{pr['sign']}</td>"
                f"<td>{pr['nak']} · pada {pr['pada']}</td><td>{pr['element'].title()}</td></tr>")
    table = ("<table class='meth'><thead><tr><th>Person</th><th>Moon sign</th><th>Birth-star</th>"
             f"<th>Element</th></tr></thead><tbody>{row(p['profiles']['p1'])}{row(p['profiles']['p2'])}</tbody></table>")
    gloss = "".join(
        f"<li><b>{KOOTA_UI[k]['label']}</b> <span class='gsan'>({k} · out of {mx})</span> — {KOOTA_UI[k]['blurb']}.</li>"
        for k, mx in [("Yoni", 4), ("Gana", 6), ("Graha Maitri", 5), ("Bhakoot", 7),
                      ("Nadi", 8), ("Vashya", 2), ("Tara", 3), ("Varna", 1)])
    return ("<h2>How we calculated this 🔬</h2><div class='methbox'>"
            "<p>Your match is computed with the classical <b>Ashtakoota</b> (eight-fold) system of Vedic "
            "astrology — the same method a family astrologer uses — but from precise, <b>NASA-grade planetary "
            "positions</b> and the standard <b>Lahiri ayanamsa</b>. Same inputs, same score, every time — "
            "consistent and verifiable, not mood-of-the-day.</p>"
            f"<p>Here's exactly what we read from your birth details:</p>{table}"
            f"<p class='methsub'>{m['time_note']}</p></div>"
            "<h3 class='glossh'>The 8 factors, in plain English</h3><ul class='gloss'>" + gloss + "</ul>")


def _tldr_html(p: dict) -> str:
    """Scannable, low-text summary shown directly under the hero. Answers the three
    questions a reader actually has — what's good, what to watch, what to do — before
    any long-form detail. Built entirely from existing payload fields, so it renders
    for older stored reports too (render-time only, no payload-shape dependency)."""
    ts = _theme_scores(p["kootas"])
    strong = [t for t in ts if t["pct"] >= 60]
    weak = [t for t in ts if t["pct"] < 45]

    # --- what's working ---
    if strong:
        good_chips = "".join(f"<span class='sx-chip good'>{t['theme']['emoji']} {t['theme']['name']}</span>" for t in strong)
        good_note = f"{len(strong)} of 5 big areas — naturally strong."
    else:
        good_chips = "<span class='sx-chip good'>💚 A workable, balanced match</span>"
        good_note = "Steady across the board — no runaway strengths, no big gaps."

    # --- what to watch ---
    cancelled = {c.get("koota") for c in (p.get("cancellations") or [])}
    weak_cancelled = any(k["name"] in cancelled for k in p["kootas"]
                         if k["max"] and k["score"] / k["max"] < 0.5)
    if weak:
        watch_chips = "".join(f"<span class='sx-chip warn'>{t['theme']['emoji']} {t['theme']['name']}</span>" for t in weak)
        watch_note = ("A classical flaw shows up here — <b>and it's cancelled for you</b>. "
                      "Fixable with habits, not luck." if weak_cancelled
                      else "Not a dealbreaker — just the area to be a little intentional about.")
    else:
        watch_chips = "<span class='sx-chip ok'>✅ Nothing major</span>"
        watch_note = "No weak link here worth losing sleep over."

    # --- your moves (pulled up from the weak factors' fixes; capped at 3) ---
    weak_k = sorted([k for k in p["kootas"] if k["max"] and k["score"] / k["max"] < 0.5],
                    key=lambda k: k["score"] / k["max"])
    moves = []
    for k in weak_k:
        rem = REMEDIES.get(k["name"])
        if not rem or not rem.get("work_on"):
            continue
        ui = KOOTA_UI.get(k["name"], {"emoji": "•", "label": k["name"]})
        moves.append((ui["emoji"], ui["label"], rem["work_on"]))
        if len(moves) == 3:
            break
    if moves:
        items = "".join(
            f"<li><span class='sx-n'>{i}</span><div><span class='sx-tag'>{em} {lab}</span>{txt}</div></li>"
            for i, (em, lab, txt) in enumerate(moves, 1))
        plan_h = "Your move" if len(moves) == 1 else f"Your {len(moves)} moves"
        plan_card = (f"<div class='sx-card plan'><div class='sx-h'>🎯 {plan_h}</div>"
                     f"<ul class='sx-moves'>{items}</ul></div>")
    else:
        plan_card = ("<div class='sx-card plan'><div class='sx-h'>🎯 Your move</div>"
                     "<p class='sx-note'>Nothing to fix here — just don't take a good thing for granted. "
                     "Keep making time for each other.</p></div>")

    return (
        "<div class='sx-wrap'>"
        f"<div class='sx-card good'><div class='sx-h'>💚 What's working</div>"
        f"<div class='sx-chips'>{good_chips}</div><p class='sx-note'>{good_note}</p></div>"
        f"<div class='sx-card watch'><div class='sx-h'>🚧 Watch-out{'' if len(weak) == 1 else 's'}</div>"
        f"<div class='sx-chips'>{watch_chips}</div><p class='sx-note'>{watch_note}</p></div>"
        f"{plan_card}"
        "</div>"
        "<p class='sx-cue'>That's the gist — the full breakdown is below ↓</p>")


def render_milan(p: dict) -> str:
    m = p["meta"]
    m = {**m, "p1": escape(m["p1"]), "p2": escape(m["p2"])}  # user-supplied names: escape
    theme_html = _theme_rows(p["kootas"])
    cancelled = {c.get("koota") for c in (p.get("cancellations") or [])}
    rows = ""
    for k in sorted(p["kootas"], key=lambda k: (k["score"] / k["max"]) if k["max"] else 0, reverse=True):
        pct = k["score"] / k["max"] * 100
        bar_color = "#2E7D53" if pct >= 75 else ("#E4B04A" if pct >= 40 else "#C93B2E")
        if k["name"] in cancelled and pct < 40:
            bar_color = "#E4B04A"  # softened — this dosha is cancelled for this couple
        ui = KOOTA_UI.get(k["name"], {"emoji": "•", "label": k["name"], "blurb": k.get("meaning", "")})
        score_disp = int(k["score"]) if float(k["score"]).is_integer() else k["score"]
        fix = _koota_fix_html(k, cancelled, (m['p1'], m['p2']))
        rows += f"""<div class='koota'>
<div class='ktop'><div class='klabel'><span class='kemoji'>{ui['emoji']}</span><span class='kname'><b>{ui['label']}</b><span class='ksan'>{k['name']} koota</span></span></div><span class='ks'>{score_disp}/{k['max']}</span></div>
<div class='kbar'><div style='width:{pct:.0f}%;background:{bar_color}'></div></div>
<p class='kd'>{ui['blurb']}</p>
<p class='kt'>{k.get('text','')}</p>{fix}</div>"""

    # ---------- cancellations & effective score ----------
    canc_html = ""
    if p.get("cancellations"):
        cards = "".join(
            f"<div class='canc'>✅ <b>{c['koota']} dosha cancelled</b> (+{c['restored']} restored)"
            f"<p>{c['rule']}</p></div>" for c in p["cancellations"])
        canc_html = (f"<h2>Dosha cancellation check</h2>{cards}"
                     f"<div class='effbox'>Effective score after cancellations: "
                     f"<b>{p['effective']}/36</b> — {p['effective_verdict']}</div>")
    elif any(k['name'] in ('Nadi','Bhakoot') and k['score']==0 for k in p['kootas']):
        canc_html = ("<h2>Dosha cancellation check</h2>"
                     "<div class='canc' style='border-color:#E4B04A'>For your two charts, the usual "
                     "rules that cancel this dosha don't apply — so it stays active. This isn't a verdict. "
                     "It simply marks this as an area to be intentional about; the practical steps are on "
                     "that factor's own card in the breakdown above. Decide with understanding, not fear.</div>")

    # ---------- strengths ----------
    sw_html = ""
    if p.get("strengths"):
        st = "".join(f"<li><b>{KOOTA_UI.get(s, {'label': s})['label']}</b> — {next(k['text'] for k in p['kootas'] if k['name']==s)}</li>"
                     for s in p.get("strengths", []))
        if st:
            sw_html = f"<h2>Where you're naturally strong 💚</h2><ul class='swl'>{st}</ul>"

    # ---------- element dynamic + nakshatra lines ----------
    el_html = ""
    if p.get("element"):
        el = p["element"]
        el_html = (f"<h2>Your combined energy</h2>"
                   f"<div class='elbox'><b>{m['p1']}: {el['p1']} · {m['p2']}: {el['p2']}</b>"
                   f"<p>{el['text']}</p></div>")

    # ---------- Manglik: keep the concern and its reassurance together ----------
    mg = p["manglik"]
    if mg.get("p1") or mg.get("p2"):
        mg_extra = ("<p class='mgfix'><b>What to do:</b> this is not a curse, and in matching it is very "
                    "often mild or fully cancelled. Read the cancellation note above, and if it matters to "
                    "your families, the classical remedy is a simple Mangal / Hanuman practice on Tuesdays. "
                    "Treat it as information to understand, not a verdict to fear.</p>")
    else:
        mg_extra = ("<p class='mgfix'><b>All clear:</b> neither chart carries a Manglik placement on this "
                    "check — one less thing to worry about.</p>")
    manglik_html = f"<h2>Manglik check</h2><div class=\"mg\">{mg['note']}{mg_extra}</div>"

    # ---------- low score guidance ----------
    low_html = ""
    if p.get("effective", p["total"]) < 24:
        low_html = ("<h2>What a lower score really means</h2>"
            "<div class='lowbox'>"
            "<p><b>First:</b> guna milan is one classical input, not the whole verdict. It measures how "
            "compatible your Moon positions are — not values, maturity or commitment, which are the real "
            "pillars of any marriage.</p>"
            "<p><b>Second:</b> look at which factors scored low. A shortfall in the softer factors — "
            "temperament, mental wavelength — is improvable; those are communication patterns couples "
            "learn. A Nadi or Bhakoot dosha, if it isn't cancelled, carries more traditional weight — "
            "there, take counsel from your elders and your own judgement together.</p>"
            "<p><b>Third:</b> countless happy marriages began with a low score. Use the number as "
            "information — to see what you'll want to work on — not as a verdict.</p></div>")

    # ---------- Phase-1 expanded sections (present only on newer reports) ----------
    has_profiles = bool(p.get("profiles"))
    opening_html = _opening_note(p) if has_profiles else ""
    couple_html = ("<h2>Your couple type ✨</h2>" + _sharecard_html(p)) if has_profiles else ""
    deepdive_html = _strength_deepdive_html(p) if has_profiles else sw_html
    profiles_html = _profiles_html(p) if has_profiles else ""
    method_html = _method_html(p, m) if has_profiles else ""
    if method_html:
        method_body = method_html.replace("<h2>How we calculated this 🔬</h2>", "", 1)
        method_acc = ("<details class=\"acc\"><summary><span class=\"acc-t\">🔬 How we calculated this</span>"
                      "<span class=\"acc-x\">the method <span class=\"caret\">▾</span></span></summary>"
                      f"<div class=\"acc-body\">{method_body}</div></details>")
    else:
        method_acc = ""
    besties_html = _askbesties_html(p) if has_profiles else ""
    cert_html = _certificate_html(p) if has_profiles else ""
    matchpct_html = (f"<p class='matchpct'>{_match_pct(p)}% match on what matters</p>"
                     if has_profiles else "")
    # personalised share text for axShare (couple-card image download removed)
    share_js = ""
    if has_profiles:
        share_js = "<script>window.AX_SHARE_TEXT=" + json.dumps(_share_text(p)) + ";</script>"

    # bottom-sticky actions: print-to-PDF + WhatsApp share (report link via axShare)
    sticky_bar = (
        "<style>@media screen{body{padding-bottom:80px}}"
        "#ax-stickybar{position:fixed;left:0;right:0;bottom:0;z-index:9997;"
        "background:rgba(16,20,40,.96);border-top:1px solid rgba(228,176,74,.35);"
        "box-shadow:0 -6px 20px rgba(0,0,0,.28);"
        "padding:10px 12px calc(10px + env(safe-area-inset-bottom))}"
        "#ax-stickybar .inner{max-width:640px;margin:0 auto;display:flex;gap:10px}"
        "#ax-stickybar a{flex:1;text-align:center;text-decoration:none;border-radius:12px;"
        "padding:13px 10px;font:800 15px/1 'Bricolage Grotesque',system-ui,sans-serif}"
        "#ax-stickybar .pdf{background:#C93B2E;color:#fff}"
        "#ax-stickybar .wa{background:#25D366;color:#0b2f18}"
        "@media print{#ax-stickybar{display:none!important}}</style>"
        "<div id='ax-stickybar'><div class='inner'>"
        "<a class='pdf' href='#' onclick='window.print();return false;'>&#11015; Download PDF</a>"
        "<a class='wa' href='#' onclick='axShare();return false;'>Share on WhatsApp</a>"
        "</div></div>")

    notes = "".join(f"<div class='note'>{n}</div>" for n in p["notes"])
    tldr_html = _tldr_html(p)
    vcol = VERDICT_COLOR[p["verdict_key"]]
    return f"""<!DOCTYPE html><html lang="hi-IN"><head>{AX_PRE}<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{m['p1']} ✕ {m['p2']} — Kundli Milan | Axtroshastra</title>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&display=swap" rel="stylesheet">
<style>
:root{{--ink:#23253B;--midnight:#151C39;--paper:#FAF6ED;--sindoor:#C93B2E;
--haldi:#E4B04A;--muted:#6B6D82;--line:#E7E0D2;--display:'Bricolage Grotesque',sans-serif}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,'Segoe UI',sans-serif;background:var(--paper);color:var(--ink);
line-height:1.6;font-size:15.5px;max-width:640px;margin:0 auto;padding:0 20px 60px}}
.hero{{background:var(--midnight);color:#F3EFE4;margin:0 -20px;padding:36px 22px;text-align:center}}
.hero .brand{{font-family:var(--display);font-weight:800;color:var(--haldi);font-size:13px;letter-spacing:.08em}}
.hero h1{{font-family:var(--display);font-size:26px;margin-top:14px;color:#fff}}
.score{{font-family:var(--display);font-weight:800;font-size:56px;color:var(--haldi);margin:14px 0 2px}}
.score small{{font-size:22px;color:#8F92AB}}
.verdict{{display:inline-block;background:{vcol};color:#fff;font-family:var(--display);
font-weight:800;font-size:13px;border-radius:20px;padding:7px 18px;margin-top:10px}}
h2{{font-family:var(--display);font-size:21px;margin:34px 0 14px}}
.koota{{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:10px}}
.ktop{{display:flex;justify-content:space-between;align-items:center;gap:10px;font-family:var(--display)}}
.ks{{font-weight:800;flex:none;font-size:17px}}
.lead{{color:var(--muted);font-size:14px;margin:-8px 0 14px}}
.theme{{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:10px}}
.ttop{{display:flex;align-items:center;gap:9px;font-family:var(--display)}}
.temoji{{font-size:20px;line-height:1;flex:none}}
.ttop b{{font-size:16px;flex:1;min-width:0}}
.tchip{{color:#fff;font-family:var(--display);font-weight:800;font-size:11px;border-radius:20px;padding:4px 10px;white-space:nowrap;flex:none}}
.tblurb{{font-size:13.5px;color:#3A3C55;margin-top:9px}}
.klabel{{display:flex;align-items:center;gap:10px;min-width:0}}
.kemoji{{font-size:20px;line-height:1;flex:none}}
.kname{{display:flex;flex-direction:column;line-height:1.2;min-width:0}}
.kname b{{font-size:16px}}
.ksan{{font-size:10.5px;color:var(--muted);font-weight:700;letter-spacing:.03em;text-transform:uppercase;margin-top:2px}}
.work{{background:#fff;border:1.5px solid var(--line);border-left:4px solid var(--sindoor);border-radius:12px;padding:14px 16px;margin-bottom:10px;font-size:14px}}
.work.good{{border-left-color:#2E7D53}}
.work.good b{{font-family:var(--display);font-size:15.5px}}.work.good p{{margin-top:7px}}
.wtop{{display:flex;align-items:center;gap:9px;font-family:var(--display)}}
.wemoji{{font-size:19px;line-height:1;flex:none}}
.wtop b{{font-size:15.5px;flex:1;min-width:0}}
.wtag{{font-family:var(--display);font-weight:800;font-size:10.5px;text-transform:uppercase;letter-spacing:.03em;color:var(--sindoor);background:#FBE7E3;border-radius:20px;padding:3px 9px;flex:none}}
.wcanc{{display:inline-block;font-size:12px;color:#2E7D53;font-weight:600;margin-top:6px}}
.wdo{{margin-top:9px}}
.wrem{{margin-top:7px;color:var(--muted);font-size:13.5px}}
.wdo b,.wrem b{{font-family:var(--display)}}
.kbar{{height:7px;background:#EFE8D8;border-radius:4px;margin:8px 0;overflow:hidden}}
.kbar div{{height:100%;border-radius:4px}}
.kd{{font-size:13px;color:var(--muted)}}
.mg,.note{{background:#F6E7C6;border-radius:12px;padding:15px;font-size:14px;margin:10px 0}}
.note{{background:#fff;border:1.5px solid var(--haldi)}}
.tn{{font-size:12px;color:var(--muted);margin-top:24px}}
.kt{{font-size:14px;margin-top:8px;color:#33355000;color:#3A3C55}}
.kfix{{margin-top:12px;padding-top:12px;border-top:1px dashed var(--line)}}
.kfix .wdo{{margin-top:0}}
.mgfix{{margin-top:10px;font-size:13.5px}}
.mgfix b{{font-family:var(--display)}}
.canc{{background:#fff;border:2px solid #2E7D53;border-radius:12px;padding:14px 16px;margin-bottom:10px;font-size:14px}}
.canc p{{margin-top:5px}}
.effbox{{background:var(--midnight);color:#F3EFE4;border-radius:12px;padding:16px;font-size:15px;text-align:center}}
.effbox b{{color:var(--haldi);font-family:var(--display);font-size:20px}}
.swh{{font-family:var(--display);font-weight:800;font-size:14px;margin:14px 0 6px}}
.swl{{margin-left:20px}}.swl li{{font-size:14px;margin-bottom:8px}}
.elbox,.nlbox,.lowbox{{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:15px 16px;margin-bottom:10px;font-size:14px}}
.elbox b{{font-family:var(--display)}}.elbox p{{margin-top:6px}}
.lowbox p{{margin-bottom:10px}}
/* ---- Phase-1 expanded sections ---- */
.matchpct{{display:inline-block;margin-top:12px;font-family:var(--display);font-weight:800;font-size:15px;color:#151C39;background:var(--haldi);border-radius:20px;padding:7px 16px}}
.opennote{{background:#fff;border:1.5px solid var(--line);border-radius:14px;padding:18px;margin-top:22px;font-size:15px}}
.opennote p{{margin-bottom:9px}}.opennote p:last-child{{margin-bottom:0}}
.onsub{{color:var(--muted);font-size:13.5px;font-style:italic}}
.sharecard{{background:radial-gradient(1200px 500px at 50% -30%, #23305C, var(--midnight) 70%);color:#F3EFE4;border-radius:18px;padding:26px 22px 24px;text-align:center;box-shadow:0 14px 40px rgba(21,28,57,.28)}}
.scbrand{{font-family:var(--display);font-weight:800;color:var(--haldi);font-size:11px;letter-spacing:.14em}}
.scnames{{font-family:var(--display);font-weight:800;font-size:24px;color:#fff;margin-top:12px}}
.scnames span{{color:var(--haldi);margin:0 6px}}
.scarch{{font-family:var(--display);font-weight:700;font-size:15px;color:#E9E4D5;margin-top:6px}}
.scpct{{font-family:var(--display);font-weight:800;font-size:52px;color:var(--haldi);margin:14px 0 0;line-height:1}}
.scpct small{{display:block;font-size:12px;color:#B9BBD0;font-weight:700;letter-spacing:.02em;margin-top:6px}}
.scchips{{display:flex;flex-wrap:wrap;gap:7px;justify-content:center;margin-top:16px}}
.scchip{{background:rgba(228,176,74,.16);border:1px solid rgba(228,176,74,.5);color:#F1E4C4;font-size:11.5px;font-weight:700;border-radius:20px;padding:5px 11px}}
.sctag{{color:#D9D4C3;font-style:italic;font-size:13.5px;margin-top:16px}}
.sctag2{{font-size:14px;color:#3A3C55;margin:12px 2px 0}}
.sharebtn{{display:block;width:100%;border:0;border-radius:12px;background:var(--sindoor);color:#fff;font-family:var(--display);font-weight:800;font-size:16px;padding:14px;margin-top:14px;cursor:pointer}}
.sharebtns{{display:flex;gap:10px}}.sharebtns .sharebtn{{flex:1}}
.sharebtn.ghost{{background:transparent;color:var(--sindoor);border:2px solid var(--sindoor);padding:12px}}
.friendnote{{background:#F6E7C6;border-radius:12px;padding:14px 15px;margin-top:14px;font-size:13.5px}}
.friendnote b{{font-family:var(--display)}}.friendnote p{{margin-top:6px;margin-bottom:0}}
.cert{{background:linear-gradient(#FFFDF7,#F7EFDD);border:2px solid var(--haldi);border-radius:16px;padding:8px;box-shadow:0 12px 34px rgba(35,37,59,.12)}}
.certin{{border:1.5px dashed #CDA43E;border-radius:12px;padding:24px 18px;text-align:center}}
.certseal{{font-size:30px;color:var(--haldi);line-height:1}}
.certk{{font-family:var(--display);font-weight:700;font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);margin-top:8px}}
.certnames{{font-family:var(--display);font-weight:800;font-size:24px;color:var(--ink);margin-top:12px}}
.certnames span{{color:var(--haldi);margin:0 5px;font-weight:700}}
.certarch{{font-size:14px;color:#4A4C63;margin-top:10px;line-height:1.5}}
.certarch b{{font-family:var(--display);font-size:18px;color:var(--ink)}}
.certpct{{display:inline-block;font-family:var(--display);font-weight:800;font-size:14px;color:#151C39;background:var(--haldi);border-radius:20px;padding:6px 15px;margin-top:14px}}
.certfoot{{font-size:11px;color:var(--muted);margin-top:16px;line-height:1.5;letter-spacing:.02em}}
.profwrap{{display:flex;flex-direction:column;gap:10px}}
.prof{{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:15px 16px}}
.prtop{{display:flex;align-items:center;gap:11px;margin-bottom:6px}}
.prel{{font-size:26px;line-height:1;flex:none}}
.prname{{display:flex;flex-direction:column;line-height:1.25}}
.prname b{{font-family:var(--display);font-size:17px}}
.prsign{{font-size:11px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.02em;margin-top:3px;line-height:1.5}}
.prline{{font-size:14px;margin-top:6px}}.prline b{{font-family:var(--display)}}
@media(min-width:560px){{.profwrap{{flex-direction:row}}.prof{{flex:1}}}}
.kchartwrap{{background:var(--midnight);border-radius:12px;padding:12px 12px 8px;margin-top:12px}}
.kchart{{width:100%;max-width:290px;height:auto;display:block;margin:0 auto}}
.kcap{{color:#B9BBD0;font-size:11.5px;text-align:center;margin-top:8px;line-height:1.4}}
.klegend{{font-size:11.5px;color:var(--muted);line-height:1.6;margin:12px 2px 0;background:#fbf7ef;border:1px solid var(--line);border-radius:10px;padding:11px 13px}}
.klegend b{{color:var(--ink)}}
.deep{{background:#F3F8F3;border:1.5px solid #CDE4D3;border-radius:12px;padding:14px 16px;margin-bottom:10px}}
.dtop{{display:flex;align-items:center;gap:9px;font-family:var(--display);margin-bottom:6px}}
.dtop b{{font-size:16px}}.demoji{{font-size:19px;flex:none}}
.deep p{{font-size:14px}}
.wplan{{background:#FBF4E6;border-radius:10px;padding:11px 12px;margin-top:10px;font-size:13.5px}}
.wplan p{{margin:5px 0}}
.wpk{{display:inline-block;font-family:var(--display);font-weight:800;font-size:10px;text-transform:uppercase;letter-spacing:.03em;color:#8a6a1f;background:#F6E7C6;border-radius:6px;padding:2px 7px;margin-right:6px}}
.wsplit{{background:#FBF4E6;border-radius:10px;padding:9px 12px;margin-top:9px;font-size:13.5px}}
.wsplit p{{margin:5px 0}}
.wtalk{{margin-top:8px;font-size:13.5px}}
.besties{{background:#fff;border:2px dashed var(--haldi);border-radius:14px;padding:18px}}
.besties p{{font-size:14.5px;margin-bottom:10px}}
.bnote{{font-size:12px;color:var(--muted);margin-top:12px;text-align:center}}
.methbox{{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:15px 16px;font-size:14px}}
.methbox p{{margin-bottom:9px}}
.meth{{width:100%;border-collapse:collapse;margin:6px 0;font-size:13px}}
.meth th,.meth td{{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line)}}
.meth th{{font-family:var(--display);font-size:11px;text-transform:uppercase;letter-spacing:.03em;color:var(--muted)}}
.methsub{{font-size:12.5px;color:var(--muted);margin-top:4px}}
.glossh{{font-family:var(--display);font-size:17px;margin:22px 0 10px}}
.gloss{{list-style:none}}
.gloss li{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-bottom:7px;font-size:13.5px}}
.gloss b{{font-family:var(--display)}}
.gsan{{color:var(--muted);font-size:11.5px;font-weight:600}}
/* ---- scannable TL;DR summary (directly under hero) ---- */
.sx-wrap{{display:grid;gap:10px;margin-top:16px}}
@media(min-width:560px){{.sx-wrap{{grid-template-columns:1fr 1fr}}}}
.sx-card{{background:#fff;border:1.5px solid var(--line);border-radius:14px;padding:15px 16px}}
.sx-card.good{{border-top:4px solid #2E7D53}}
.sx-card.watch{{border-top:4px solid var(--sindoor)}}
.sx-card.plan{{border:1.5px solid var(--haldi);background:#FBF4E6}}
@media(min-width:560px){{.sx-card.plan{{grid-column:1/-1}}}}
.sx-h{{font-family:var(--display);font-weight:800;font-size:13px;letter-spacing:.04em;text-transform:uppercase}}
.sx-card.good .sx-h{{color:#2E7D53}}.sx-card.watch .sx-h{{color:var(--sindoor)}}.sx-card.plan .sx-h{{color:#8A6410}}
.sx-chips{{display:flex;flex-wrap:wrap;gap:7px;margin-top:11px}}
.sx-chip{{display:inline-flex;align-items:center;gap:5px;font-family:var(--display);font-weight:700;font-size:13px;padding:6px 11px;border-radius:20px}}
.sx-chip.good,.sx-chip.ok{{background:#E3F0E8;color:#1E5A3C}}
.sx-chip.warn{{background:#FBE9E6;color:var(--sindoor-dark,#A82F24)}}
.sx-note{{margin-top:10px;font-size:12.5px;color:var(--muted)}}
.sx-note b{{color:var(--ink)}}
.sx-moves{{list-style:none;margin:11px 0 0;display:grid;gap:8px}}
.sx-moves li{{display:flex;gap:10px;align-items:flex-start;background:#fff;border-radius:10px;padding:10px 12px;font-size:13.5px}}
.sx-n{{font-family:var(--display);font-weight:800;color:var(--sindoor);flex:none;line-height:1.5}}
.sx-tag{{display:inline-block;font-family:var(--display);font-weight:800;font-size:10.5px;letter-spacing:.02em;text-transform:uppercase;color:#8a6a1f;background:#F6E7C6;border-radius:6px;padding:2px 7px;margin-right:7px;white-space:nowrap}}
.sx-cue{{text-align:center;color:var(--muted);font-size:12.5px;margin-top:14px}}
/* ---- tap-to-open detail sections ---- */
details.acc{{background:#fff;border:1.5px solid var(--line);border-radius:12px;margin-bottom:10px;overflow:hidden}}
details.acc>summary{{list-style:none;cursor:pointer;display:flex;align-items:center;gap:10px;padding:15px 16px;font-family:var(--display);font-weight:800;font-size:18px}}
details.acc>summary::-webkit-details-marker{{display:none}}
.acc-t{{flex:1;min-width:0}}
.acc-x{{font-family:var(--display);font-weight:700;font-size:12px;color:var(--muted);white-space:nowrap}}
.acc-body{{padding:2px 16px 16px;border-top:1px dashed var(--line)}}
.acc-body>.lead{{margin-top:12px}}
details.acc[open]>summary .acc-x .caret{{transform:rotate(180deg)}}
.caret{{display:inline-block;transition:transform .15s;color:var(--haldi)}}
@media print{{#axlang{{display:none!important}}details.acc>*{{display:block!important}}details.acc>summary .acc-x{{display:none}}body{{max-width:100%;padding:0 10px 16px;background:#fff}}.hero{{margin:0 -10px}}
.koota,.theme,.work,.canc,.note,.mg,.effbox,.elbox,.nlbox,.lowbox,.review,.swl li,.opennote,.sharecard,.prof,.deep,.besties,.methbox,.gloss li,.wplan,.cert,.friendnote,.sharebtns,.sharebtn,.matchpct,.profwrap,.kchartwrap{{break-inside:avoid}}
h2,h3{{break-after:avoid}}p{{orphans:2;widows:2}}*{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}}}
</style></head><body>
<div class="hero"><p class="brand">✦ AXTROSHASTRA · KUNDLI MILAN</p>
<h1>{m['p1']} ✕ {m['p2']}</h1>
<p class="score">{p['total']}<small>/36</small></p>
<span class="verdict">{p['verdict'].upper()}</span>
{matchpct_html}
{("<p style='margin-top:10px;font-size:14px;color:#B9BBD0'>After dosha cancellation: <b style='color:#E4B04A'>" + str(p['effective']) + "/36</b></p>") if p.get('cancellations') else ""}</div>
{tldr_html}
{opening_html}
{couple_html}
{profiles_html}
<h2>Your match, in plain English 💫</h2>
<p class="lead">The five things that actually make or break a relationship — scored straight from your two charts.</p>
{theme_html}
{deepdive_html}
<details class="acc"><summary><span class="acc-t">📊 The full breakdown — all 8 factors</span><span class="acc-x">{p['total']}/36 <span class="caret">▾</span></span></summary>
<div class="acc-body"><p class="lead">This is the classical 8-part Ashtakoota system, decoded. Every score here feeds the five themes above.</p>{rows}</div></details>
{canc_html}
{el_html}
{manglik_html}
{method_acc}
{cert_html}
{besties_html}
{('<h2>Important notes</h2>' + notes) if notes else ''}
{low_html}
<p class="tn">System: {m['system']} · {m['time_note']} · Generated {m['generated']}<br>
This compatibility score is one classical input to a marriage decision, not the whole decision.
<a href='https://wa.me/919650973345' style='color:inherit'>WhatsApp +91 96509 73345</a> · <a href="/privacy" style="color:inherit">Privacy</a> · <a href="/terms" style="color:inherit">Terms</a> · <a href="/refunds" style="color:inherit">Refund Policy</a></p>
{share_js}
<script>window.addEventListener('beforeprint',function(){{document.querySelectorAll('details.acc').forEach(function(d){{d.__wo=d.open;d.open=true;}});}});window.addEventListener('afterprint',function(){{document.querySelectorAll('details.acc').forEach(function(d){{if(d.__wo===false)d.open=false;}});}});</script>
{sticky_bar}
{MILAN_I18N}
</body></html>"""


# ============================================================ BLUEPRINT RENDERER
def render_blueprint(p: dict) -> str:
    m = p["meta"]
    m = {**m, "name": escape(m["name"])}  # user-supplied name: escape to prevent stored XSS
    road = ""
    for r in p["roadmap"]:
        cur = " · <b style='color:#C93B2E'>ABHI CHAL RAHA HAI</b>" if r["current"] else ""
        road += (f"<div class='ph'><b>{r['lord']} phase</b> "
                 f"<span class='yrs'>{r['from']} → {r['to']}</span>{cur}"
                 f"<p>{r['theme']}</p></div>")

    # ---------- new blueprint sections ----------
    ss = p.get("sade_sati", {})
    if ss.get("active"):
        ss_html = (f"<h2>Sade Sati check — bina poochhe jawab</h2><div class='ssb'>"
                   f"<b>Chal rahi hai:</b> {ss['phase']}, till <b>{ss['ends']}</b>. "
                   f"Iska classical matlab: Shani discipline aur restructuring karwata hai — "
                   f"delay lagta hai, par jo is period mein banta hai, tikau banta hai. "
                   f"Dar ka nahi, dhairya ka period hai.</div>")
    else:
        ss_html = (f"<h2>Sade Sati check — bina poochhe jawab</h2><div class='ssb'>"
                   f"<b>Abhi nahi chal rahi.</b> Next phase approx {ss.get('next_starts','—')} se shuru hoga. "
                   f"Filhaal Shani ka is angle se koi pressure nahi.</div>")

    np_ = p.get("nak_profile", {})
    nak_html = (f"<div class='card' style='margin-top:12px'><p><b>Aapka nakshatra: "
                f"{np_.get('nakshatra','')} ({np_.get('symbol','')}):</b> {np_.get('nature','')}.</p>"
                f"<p style='margin-top:8px'>{np_.get('relationship','')}.</p></div>") if np_ else ""

    el = p.get("elements", {})
    el_html = ""
    if el:
        miss = (f" Aapke chart mein {', '.join(el['missing'])} element ke planets nahi hain — "
                f"us quality ko conscious effort se laana hoga." if el.get("missing") else
                " Chaaron elements present hain — versatile temperament.")
        el_html = (f"<h2>Element balance</h2><div class='card'><p>Aapke chart ka dominant element: "
                   f"<b>{el['dominant']}</b> ({el['dominant_n']} planets).{miss}</p></div>")

    w = p.get("wealth", {})
    wealth_html = (f"<h2>Dhan — earning aur gains ka pattern</h2><div class='card'>"
                   f"<p><b>Earning pattern:</b> {w.get('second','')}.</p>"
                   f"<p style='margin-top:8px'><b>Gains pattern:</b> {w.get('gains','')}.</p></div>") if w else ""

    health_html = (f"<h2>Sharir — chart ki tendencies</h2><div class='card'>"
                   f"<p>{p.get('health','')}.</p>"
                   f"<p class='soft'>Yeh classical indications hain, medical advice nahi — "
                   f"sehat ke faisle hamesha doctor ke saath.</p></div>") if p.get("health") else ""

    rel = p.get("relationship", {})
    rel_html = (f"<h2>Rishtey — ek jhalak</h2><div class='card'>"
                f"<p>Aapka 7th house <b>{rel.get('seventh','')}</b> hai — partner indication: "
                f"{rel.get('line','')}.</p>"
                f"<p class='soft'>Shaadi ki exact timing windows ke liye Marriage Timing Report "
                f"dekhiye — usi chart se, minute-level depth ke saath.</p></div>") if rel else ""

    ya = p.get("year_ahead", {})
    ya_html = ""
    if ya:
        jup_t = ("Jupiter abhi aapke Moon se supportive house mein transit kar raha hai — growth "
                 "aur openings ka saath hai." if ya.get("jup_good") else
                 "Jupiter ka current transit neutral zone mein hai — is saal effort ka weight zyada rahega.")
        nx = ya.get("next_ad")
        nx_t = (f" Aapka agla sub-period <b>{nx['lord']}</b> ka hai, {nx['from']} se — "
                f"us theme ki taiyari abhi se ho sakti hai." if nx else "")
        ya_html = (f"<h2>Aane wala saal</h2><div class='card'><p>{jup_t}</p>"
                   f"<p style='margin-top:8px'>Saturn abhi aapke Moon se house {ya.get('sat_house','—')} "
                   f"mein hai.{nx_t}</p></div>")

    st = "".join(f"<li>{s}</li>" for s in p["strengths"])
    ls = "".join(f"<li>{s}</li>" for s in p["lessons"])
    chandra = ("<p class='soft'>Note: approximate birth time — personality read uses "
               "the Moon chart (classical Chandra Lagna method).</p>"
               if p["persona"]["note_chandra"] else "")
    return f"""<!DOCTYPE html><html lang="hi-IN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{m['name']} — Life Blueprint | Axtroshastra</title>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&display=swap" rel="stylesheet">
<style>
:root{{--ink:#23253B;--midnight:#151C39;--paper:#FAF6ED;--sindoor:#C93B2E;
--haldi:#E4B04A;--muted:#6B6D82;--line:#E7E0D2;--display:'Bricolage Grotesque',sans-serif}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,'Segoe UI',sans-serif;background:var(--paper);color:var(--ink);
line-height:1.6;font-size:15.5px;max-width:640px;margin:0 auto;padding:0 20px 60px}}
.hero{{background:var(--midnight);color:#F3EFE4;margin:0 -20px;padding:36px 22px;text-align:center}}
.hero .brand{{font-family:var(--display);font-weight:800;color:var(--haldi);font-size:13px;letter-spacing:.08em}}
.hero h1{{font-family:var(--display);font-size:26px;margin-top:14px;color:#fff}}
.hero p{{color:#A9ABC0;font-size:13px;margin-top:6px}}
h2{{font-family:var(--display);font-size:21px;margin:34px 0 12px}}
.card{{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:16px;margin-bottom:12px}}
.ph{{background:#fff;border-left:5px solid var(--haldi);border:1.5px solid var(--line);
border-left:5px solid var(--haldi);border-radius:12px;padding:14px 16px;margin-bottom:10px}}
.ph .yrs{{color:var(--muted);font-size:13px;margin-left:8px}}
.ph p{{font-size:14px;margin-top:5px}}
ul{{margin-left:20px}} li{{margin-bottom:6px;font-size:14.5px}}
.soft{{color:var(--muted);font-size:13px;margin-top:10px}}
.tn{{font-size:12px;color:var(--muted);margin-top:24px}}
.ssb{{background:#F6E7C6;border-radius:12px;padding:15px 16px;font-size:14.5px}}
</style></head><body>
<div class="hero"><p class="brand">✦ AXTROSHASTRA · LIFE BLUEPRINT</p>
<h1>{m['name']}</h1><p>Lagna {p['chart']['lagna']} · Moon {p['teaser']['moon_sign']} ·
{p['teaser']['nakshatra']} · Generated {m['generated']}</p></div>

<h2>Aap kaun hain — chart ke hisaab se</h2>
<div class="card"><p><b>Outer self (Lagna {p['chart']['lagna']}):</b> {p['persona']['lagna_line']}.</p>
<p style="margin-top:8px"><b>Inner self (Moon {p['teaser']['moon_sign']}):</b> {p['persona']['moon_line']}.</p>{chandra}</div>
{nak_html}

<h2>Career direction</h2>
<div class="card"><p>Aapka 10th house <b>{p['career']['tenth_sign']}</b> hai aur uska lord
<b>{p['career']['tenth_lord']}</b> jis jagah baitha hai, wahan se indication milta hai:
<b>{p['career']['direction']}</b>.</p></div>

<h2>Built-in strengths</h2><div class="card"><ul>{st}</ul></div>
<h2>Growth lessons</h2><div class="card"><ul>{ls}</ul></div>

<h2>Aapka life roadmap — agle 3 phases</h2>{road}
<p class="soft">Har phase ke andar chhote periods (antardashas) hote hain jo timing ko
refine karte hain — specific sawaal ke liye Marriage Timing ya Career report dekhiye.</p>

{ss_html}
{el_html}
{wealth_html}
{health_html}
{rel_html}
{ya_html}

<h2>Current period</h2>
<div class="card"><p><b>{p['teaser']['current_dasha']}</b> — till {p['teaser']['dasha_till']}.
Is period ka rang upar roadmap ke pehle phase se aata hai; abhi ke decisions usi theme
mein sabse achha kaam karte hain.</p></div>

<p class="tn">System: {'Chandra Lagna' if m['system']=='chandra_lagna' else 'Lagna-based'} ·
Lahiri ayanamsa · Indications, not fate — chart direction batata hai, choice aapki hai.<br>
<a href='https://wa.me/919650973345' style='color:inherit'>WhatsApp +91 96509 73345</a> · <a href="/privacy" style="color:inherit">Privacy</a> · <a href="/terms" style="color:inherit">Terms</a> · <a href="/refunds" style="color:inherit">Refund Policy</a></p>
</body></html>"""


# Per-window framing by rank (0=nearest, 1=next, 2=furthest) -- replaces a
# single generic per-grade paragraph that was identical on every "Strong"
# window (a real complaint: 3 windows reading as the same content 3 times).
# The lede now differs by POSITION, which is always true regardless of the
# chart, so windows never repeat verbatim again.
RANK_TAG = ["Right now", "Second wave", "Further out"]
RANK_TAG_COLOR = ["#C93B2E", "#E4B04A", "#6C5CE7"]
RANK_LEDE = [
    "This is your best shot in the near term — the reasons below are specific to this window.",
    "A second window in the same broader phase — driven by a different part of your chart, so it plays out differently.",
    "A window further out — usually a genuinely new chapter, not a continuation of what came before.",
]


def render_vidyarthi(p: dict) -> str:
    """/padhai — student career & academic timing report. Structure mirrors
    render_milan's shareable/keepsake pattern (sharecard, keepsake certificate,
    emoji section headers, plain-English leads) for a consistent voice across
    products, adapted for career/academic timing instead of compatibility."""
    m = p["meta"]
    m = {**m, "name": escape(m["name"])}  # user-supplied name: escape to prevent stored XSS
    ex = p.get("extras", {})
    arche = ex.get("career_archetype") or {"name": "Your Path", "emoji": "✦",
                                            "tagline": "", "body": ""}

    pretty = lambda ym: datetime.strptime(ym, "%Y-%m").strftime("%b %Y")
    w1 = p["windows"][0] if p["windows"] else None

    win_html = ""
    for i, w in enumerate(p["windows"]):
        rank = min(i, 2)
        reasons = "".join(f"<li>{r['why']}</li>" for r in w["rules_fired"] if r["why"])[:3] or \
                  "".join(f"<li>{r['why']}</li>" for r in w["rules_fired"][:3] if r["why"])
        peak = (f"<span class='wpeak'>🔥 Best months: {', '.join(w['peak_months'])}</span>"
                if w.get("peak_months") else "")
        win_html += f"""<div class='wcard'>
<span class='wtag' style='background:{RANK_TAG_COLOR[rank]}'>{RANK_TAG[rank]}</span>
<p class='wdate'>{pretty(w['start'])} – {pretty(w['end'])} <span class='wgrade'>{w['grade']}</span></p>
<p class='wdasha'>{w['dasha']}</p>
<p class='wlede'>{RANK_LEDE[rank]}</p>
{f"<ul class='wwhy'>{reasons}</ul>" if reasons else ''}
{peak}</div>"""

    hardship_html = ""
    if ex.get("has_hardship"):
        gem_line = (f"<li><b>Gemstone:</b> {ex['gem']} — only via a qualified jeweller/astrologer trial.</li>"
                    if ex.get("gem") else f"<li><b>Gemstone:</b> {ex.get('gem_note', '')}</li>")
        hardship_html = f"""<div class='honest'><h3>💬 Real talk</h3><p>{ex['line']}</p>
<p style='margin-top:8px'><b>Classical support for this period:</b></p>
<ul class='rem'><li><b>Fast day:</b> {ex.get('fast_day', '—')}</li>
<li><b>Mantra:</b> {ex.get('mantra', '—')} — 108 times, on {ex.get('fast_day', 'the fast day')}</li>
{gem_line}</ul>
<p class='soft'>The first remedy is always action — showing up in the windows above. This is support, not a substitute.</p></div>"""
    else:
        hardship_html = f"<div class='honest'><h3>💬 Real talk</h3><p>{ex.get('line', '')}</p></div>"

    ss = ex.get("sade_sati", {})
    if ss.get("active"):
        ss_html = (f"<div class='ssb'><b>Sade Sati — currently active:</b> {ss['phase']}, till <b>{ss['ends']}</b>. "
                   f"Classically this means discipline and restructuring — it can feel like delay, "
                   f"but what's built in this period tends to be durable. Not a warning; a work period.</div>")
    else:
        ss_html = (f"<div class='ssb'><b>Sade Sati — not currently active.</b> Next phase approx "
                   f"{ss.get('next_starts', '—')}. No Saturn pressure on this axis right now.</div>")

    stage_html = (f"<p style='margin-top:10px'><b>{escape(ex['stage_label'])}:</b> {ex['stage_note']}</p>"
                  if ex.get("stage_note") else "")

    # ---------- shareable "career card" — mirrors render_milan's .sharecard ----------
    chips = [f"✨ {arche['tagline']}"]
    chips.append(f"🎯 {p['teaser']['windows_count']} breakthrough window"
                 f"{'s' if p['teaser']['windows_count'] != 1 else ''} found")
    if ex.get("natural_gift"):
        chips.append(f"💎 {ex['natural_gift']}")
    chips_html = "".join(f"<span class='scchip'>{c}</span>" for c in chips)
    sharecard_html = f"""<div class="sharecard" id="sharecard">
<p class="scbrand">✦ AXTROSHASTRA</p>
<p class="scname">{m['name']}'s Career Card</p>
<p class="scarche">{arche['emoji']} {escape(arche['name'])}</p>
{f"<p class='scwin'>Next breakthrough window<br><b>{pretty(w1['start'])} – {pretty(w1['end'])}</b> · {w1['grade']}</p>" if w1 else ""}
<div class="scchips">{chips_html}</div>
</div>
<button class="sharebtn" onclick="axShare()">📲 Share my Career Card</button>"""

    # ---------- "answer at a glance" — mirrors render_report's top_summary ----------
    honest_line = (ex.get("line") or "").split(". ")[0].rstrip(".") + "."
    glance_html = ""
    if w1:
        glance_html = (
            "<div class='glance'>"
            "<p class='plabel'>The short version</p>"
            f"<p class='win'><b>Your nearest window: {pretty(w1['start'])} – {pretty(w1['end'])}</b> "
            f"<span class='g'>● {w1['grade']}</span></p>"
            f"<p class='dir'><b>What suits you:</b> {ex.get('career_direction', '')}.</p>"
            f"<p class='note'>{honest_line} Everything below is the \"why,\" section by section.</p>"
            "</div>"
        )

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{m['name']} — Career &amp; Academic Timing | Axtroshastra</title>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&display=swap" rel="stylesheet">
<style>
:root{{--ink:#23253B;--midnight:#151C39;--midnight2:#23305C;--paper:#FAF6ED;--card:#fff;
--haldi:#E4B04A;--haldi-soft:#F6E7C6;--sindoor:#C93B2E;--green:#2E7D53;--green-soft:#E6F2EA;
--violet:#6C5CE7;--violet-soft:#EEEBFC;--muted:#6B6D82;--line:#E7E0D2;--display:'Bricolage Grotesque',sans-serif}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,'Segoe UI',sans-serif;background:var(--paper);color:var(--ink);
line-height:1.6;font-size:15.5px;max-width:640px;margin:0 auto;padding:0 20px 60px}}
h2{{font-family:var(--display);font-size:20px;margin:32px 0 8px}}
.lead{{color:var(--muted);font-size:13.5px;margin:0 0 12px}}
.hero{{background:radial-gradient(1000px 460px at 50% -25%, var(--midnight2), var(--midnight) 68%);
color:#F3EFE4;margin:0 -20px;padding:32px 24px 26px;text-align:center}}
.hero .brand{{font-family:var(--display);font-weight:800;color:var(--haldi);font-size:11px;letter-spacing:.14em}}
.hero h1{{font-family:var(--display);font-size:25px;color:#fff;margin-top:12px}}
.hero .meta{{color:#8F92AB;font-size:12.5px;margin-top:10px}}
.sharecard{{background:radial-gradient(1000px 420px at 50% -30%, #26325E, var(--midnight) 72%);color:#F3EFE4;
border-radius:18px;padding:24px 22px 22px;text-align:center;box-shadow:0 14px 40px rgba(21,28,57,.28);margin-top:22px}}
.scbrand{{font-family:var(--display);font-weight:800;color:var(--haldi);font-size:11px;letter-spacing:.14em}}
.scname{{font-family:var(--display);font-weight:800;font-size:20px;color:#fff;margin-top:10px}}
.scarche{{font-family:var(--display);font-weight:700;font-size:16px;color:var(--haldi);margin-top:4px}}
.scwin{{font-size:13.5px;color:#D9D4C3;margin-top:12px}}
.scwin b{{color:#fff;font-family:var(--display)}}
.scchips{{display:flex;flex-wrap:wrap;gap:7px;justify-content:center;margin-top:14px}}
.scchip{{background:rgba(228,176,74,.16);border:1px solid rgba(228,176,74,.5);color:#F1E4C4;font-size:11px;
font-weight:700;border-radius:20px;padding:5px 10px}}
.sharebtn{{display:block;width:100%;border:0;border-radius:12px;background:#25D366;color:#fff;
font-family:var(--display);font-weight:800;font-size:14.5px;padding:12px;margin-top:12px;cursor:pointer}}
.glance{{background:var(--haldi-soft);border:1.5px solid var(--haldi);border-radius:14px;padding:18px 18px 16px;margin-top:18px}}
.glance .plabel{{font-family:var(--display);font-weight:800;font-size:11px;letter-spacing:.12em;text-transform:uppercase;
color:#9C6B0E;margin-bottom:6px}}
.glance .win{{font-size:15.5px;margin:2px 0}}
.glance .g{{color:var(--green);font-weight:800}}
.glance .dir{{font-size:13.5px;margin-top:8px}}
.glance .note{{font-size:12px;color:#8a7a4e;margin-top:10px}}
.wcard{{background:var(--card);border:1.5px solid var(--line);border-radius:14px;padding:16px 18px;margin-bottom:12px}}
.wtag{{display:inline-block;font-family:var(--display);font-weight:800;font-size:10.5px;letter-spacing:.05em;
text-transform:uppercase;color:#fff;padding:3px 10px;border-radius:20px;margin-bottom:8px}}
.wdate{{font-family:var(--display);font-weight:800;font-size:16.5px}}
.wgrade{{margin-left:7px;font-size:11px;font-weight:700;background:var(--haldi-soft);color:#9C6B0E;padding:2px 8px;border-radius:20px}}
.wdasha{{color:var(--muted);font-size:12.5px;margin:2px 0 8px}}
.wlede{{font-size:14px}}
.wwhy{{list-style:none;margin:9px 0 0}}
.wwhy li{{position:relative;padding-left:17px;font-size:13px;color:var(--muted);margin-bottom:5px}}
.wwhy li::before{{content:"";position:absolute;left:0;top:7px;width:6px;height:6px;border-radius:50%;background:var(--haldi)}}
.wpeak{{display:inline-block;margin-top:9px;font-size:11.5px;background:var(--green-soft);color:var(--green);
padding:3px 10px;border-radius:20px;font-weight:700}}
.fcard{{background:var(--card);border:1.5px solid var(--line);border-radius:12px;padding:14px 16px;margin-bottom:10px}}
.ftop{{display:flex;align-items:center;gap:10px;font-family:var(--display)}}
.femoji{{font-size:21px;line-height:1;flex:none}}
.ftop b{{font-size:15.5px}}
.fcard p{{font-size:13.5px;margin-top:7px}}
.honest{{background:var(--violet-soft);border:1.5px solid var(--violet);border-radius:14px;padding:18px;margin-top:14px}}
.honest h3{{font-family:var(--display);font-size:15.5px;margin-bottom:8px;color:var(--violet)}}
.honest p{{font-size:13.5px;margin-bottom:8px}}
.honest .rem{{margin:8px 0 0 20px}}
.honest .soft{{color:var(--muted);font-size:12px;margin-top:8px}}
.ssb{{background:var(--haldi-soft);border-radius:12px;padding:14px 16px;font-size:13.5px;margin-top:12px}}
.card{{background:var(--card);border:1.5px solid var(--line);border-radius:12px;padding:16px;margin-bottom:12px}}
.cert{{background:linear-gradient(#FFFDF7,#F7EFDD);border:2px solid var(--haldi);border-radius:16px;padding:8px;
margin-top:14px;box-shadow:0 12px 34px rgba(35,37,59,.12)}}
.certin{{border:1.5px dashed #CDA43E;border-radius:12px;padding:22px 18px;text-align:center}}
.certseal{{font-size:26px;color:var(--haldi);line-height:1}}
.certk{{font-family:var(--display);font-weight:700;font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);margin-top:8px}}
.certname{{font-family:var(--display);font-weight:800;font-size:20px;margin-top:10px}}
.certarch{{font-size:14.5px;color:var(--muted);margin-top:5px}}
.certwin{{font-size:14px;color:#4A4C63;margin-top:10px}}
.certwin b{{font-family:var(--display);font-size:16px;color:var(--ink)}}
.certfoot{{font-size:11px;color:var(--muted);margin-top:12px;letter-spacing:.02em}}
.actions{{display:flex;gap:10px;margin-top:24px}}
.btn{{flex:1;text-align:center;font-family:var(--display);font-weight:800;font-size:14px;padding:12px 10px;
border-radius:12px;border:0;text-decoration:none;display:flex;align-items:center;justify-content:center;gap:7px;cursor:pointer}}
.btn.pdf{{background:var(--midnight);color:#fff}}
.btn.share{{background:#25D366;color:#fff}}
.tn{{font-size:11.5px;color:var(--muted);margin-top:22px;line-height:1.6}}
@media print{{#ax-pdf,.sharebtn,.btn.share{{display:none!important}}body{{background:#fff}}
.wcard,.fcard,.honest,.cert,.sharecard{{break-inside:avoid}}h2{{break-after:avoid}}
*{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}}}
</style></head><body>

<header class="hero">
<p class="brand">✦ AXTROSHASTRA · CAREER &amp; ACADEMIC TIMING</p>
<h1>{m['name']}</h1>
<p class="meta">Lagna {p['chart']['lagna']} · Moon {p['teaser']['moon_sign']} · {p['teaser']['nakshatra']} · Generated {m['generated']}</p>
</header>

{sharecard_html}

{glance_html}

<h2>Your breakthrough windows 🚀</h2>
<p class="lead">Strongest first — each window is genuinely different, not the same line repeated.</p>
{win_html if win_html else "<div class='card'><p>No standout window in this horizon — the report below still covers your study, exam and career reads.</p></div>"}

<h2>The rest of your chart, decoded</h2>
<p class="lead">How you learn, how you test, where your luck sits, and the work you're built for.</p>
<div class="fcard"><div class="ftop"><span class="femoji">📚</span><b>How you study best</b></div>
<p>{ex.get('study_strength', '')}.</p></div>
<div class="fcard"><div class="ftop"><span class="femoji">🎯</span><b>Your exam pattern</b></div>
<p>{ex.get('exam_strength', '')}.</p></div>
<div class="fcard"><div class="ftop"><span class="femoji">🎓</span><b>Higher education &amp; luck</b></div>
<p>{ex.get('higher_education', '')}.</p></div>
<div class="fcard"><div class="ftop"><span class="femoji">🧭</span><b>Career direction — {arche['emoji']} {escape(arche['name'])}</b></div>
<p>{ex.get('career_direction', '')}. {arche['body']}</p>
{stage_html}</div>

{hardship_html}
{ss_html}

<h2>Current period</h2>
<div class="card"><p><b>{p['teaser']['current_dasha']}</b> — till {p['teaser']['dasha_till']}.
Decisions made now tend to carry the theme of whichever window above is closest.</p></div>

<h2>Your keepsake ✦</h2>
<div class="cert"><div class="certin">
<div class="certseal">✦</div>
<p class="certk">Axtroshastra · Career Timing</p>
<p class="certname">{m['name']}</p>
<p class="certarch">is officially {arche['emoji']} {escape(arche['name'])}</p>
{f"<p class='certwin'>Standout window<br><b>{pretty(w1['start'])} – {pretty(w1['end'])}</b></p>" if w1 else ""}
<p class="certfoot">Screenshot this. Come back to it when the doubt hits.</p>
</div></div>

<div class="actions">
<a class="btn pdf" id="ax-pdf" href="#" onclick="window.print();return false;">⬇️ Download PDF</a>
<a class="btn share" href="#" onclick="axShare();return false;">📲 Share on WhatsApp</a>
</div>

<p class="tn">System: {'Chandra Lagna' if m['system']=='chandra_lagna' else 'Lagna-based'} ·
Lahiri ayanamsa · Indications, not fate — the chart shows direction, the effort is yours.<br>
100% refund within 7 days — <a href='https://wa.me/919650973345' style='color:inherit'>WhatsApp +91 96509 73345</a> · <a href="/privacy" style="color:inherit">Privacy</a> · <a href="/terms" style="color:inherit">Terms</a> · <a href="/refunds" style="color:inherit">Refund Policy</a></p>

<script>
window.axShare=function(){{var url=location.href;var t=(window.__axlang==='en'?'Check out my career timing report from Axtroshastra':'Meri career timing report Axtroshastra se');if(navigator.share){{navigator.share({{title:'Axtroshastra',text:t,url:url}}).catch(function(){{}});}}else{{window.open('https://wa.me/?text='+encodeURIComponent(t+' '+url),'_blank');}}}};
</script>
</body></html>"""
