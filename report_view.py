"""
Axtroshastra report renderer — 9-page mobile-first report from engine JSON.
Deterministic templates only; every fact comes from the payload.
LLM narrative layer can later replace individual section texts via the same slots.
"""
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
<style>html.ax-pre body{visibility:hidden}@media print{#axlang{display:none!important}#ax-pdf{display:none!important}.pg{page-break-after:always;break-after:page}.pg:last-of-type{page-break-after:auto}body{background:#fff}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}}</style>"""


REPORT_I18N = r"""<script>
(function(){
  var FRAG = [
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
    ["par CAREER bhejiye","send CAREER on"]
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
@media print{{.btnrow{{display:none}}.pg{{border:none;page-break-after:always;padding:28px 8px}}
body{{background:#fff}}.cover{{background:var(--midnight)!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}}}}
</style></head><body>

<section class="pg cover">
  <p class="brand">✦ AXTROSHASTRA</p>
  <h1>{name}</h1>
  <p class="bd">Marriage Timing Report · Generated {meta['generated']}</p>
  {north_chart_svg(p)}
  <p class="method">NASA JPL data (Swiss Ephemeris) · Lahiri ayanamsa · Whole-sign houses · {system_note}</p>
</section>

<section class="pg"><p class="plabel">Chart snapshot</p>
<h2>Aapka chart — marriage lens se</h2>
<div class="facts">
  <div class="row"><span class="k">Lagna</span><span class="v">{p['chart']['lagna']}</span></div>
  <div class="row"><span class="k">Moon · Nakshatra</span><span class="v">{p['teaser']['moon_sign']} · {p['teaser']['nakshatra']}</span></div>
  <div class="row"><span class="k">7th house</span><span class="v">{seventh_sign}</span></div>
  <div class="row"><span class="k">7th lord</span><span class="v">{sl} — {dignity_txt}</span></div>
  <div class="row"><span class="k">Marriage karaka</span><span class="v">{' + '.join(sig['karakas'])}</span></div>
  <div class="row"><span class="k">Darakaraka</span><span class="v">{sig['darakaraka']}</span></div>
  <div class="row"><span class="k">Current period</span><span class="v">{p['teaser']['current_dasha']}<br>till {p['teaser']['dasha_till']}</span></div>
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
  <a class="btn p" id="ax-pdf" href="#" onclick="window.print();return false;">Download PDF</a>
  <a class="btn s" href="https://wa.me/919650973345?text=Hi%20Axtroshastra">WhatsApp Support</a>
</div></section>

<footer>Windows are probability estimates from classical dasha–transit principles,
not guarantees. 100% refund within 7 days — <a href='https://wa.me/919650973345' style='color:inherit'>WhatsApp +91 96509 73345</a> · axtroshastra@gmail.com<br>Axtroshastra · Computational Vedic Astrology · by Cultnuts · <a href="/privacy" style="color:inherit">Privacy</a> · <a href="/terms" style="color:inherit">Terms</a> · <a href="/refunds" style="color:inherit">Refund Policy</a></footer>
        {REPORT_I18N}
</body></html>"""


# ============================================================ MILAN RENDERER
VERDICT_COLOR = {"excellent": "#2E7D53", "verygood": "#2E7D53",
                 "ok": "#E4B04A", "weak": "#C93B2E"}

def render_milan(p: dict) -> str:
    m = p["meta"]
    m = {**m, "p1": escape(m["p1"]), "p2": escape(m["p2"])}  # user-supplied names: escape
    rows = ""
    for k in p["kootas"]:
        pct = k["score"] / k["max"] * 100
        bar_color = "#2E7D53" if pct >= 75 else ("#E4B04A" if pct >= 40 else "#C93B2E")
        rows += f"""<div class='koota'>
<div class='ktop'><b>{k['name']}</b><span class='ks'>{k['score']}/{k['max']}</span></div>
<div class='kbar'><div style='width:{pct:.0f}%;background:{bar_color}'></div></div>
<p class='kd'>{k['detail']} · <i>{k['meaning']}</i></p>
<p class='kt'>{k.get('text','')}</p></div>"""

    # ---------- cancellations & effective score ----------
    canc_html = ""
    if p.get("cancellations"):
        cards = "".join(
            f"<div class='canc'>✅ <b>{c['koota']} dosha cancelled</b> (+{c['restored']} restored)"
            f"<p>{c['rule']}</p></div>" for c in p["cancellations"])
        canc_html = (f"<h2>Dosha cancellation check</h2>{cards}"
                     f"<div class='effbox'>Cancellations ke baad effective score: "
                     f"<b>{p['effective']}/36</b> — {p['effective_verdict']}</div>")
    elif any(k['name'] in ('Nadi','Bhakoot') and k['score']==0 for k in p['kootas']):
        canc_html = ("<h2>Dosha cancellation check</h2>"
                     "<div class='canc' style='border-color:#C93B2E'>Is jodi mein dosha ke standard "
                     "cancellation rules apply nahi hote — dosha effective hai. Iska matlab section "
                     "'Score ka matlab' mein neeche padhiye; dar se nahi, samajh se decide kijiye.</div>")

    # ---------- strengths & watchouts ----------
    sw_html = ""
    if p.get("strengths") or p.get("watchouts"):
        st = "".join(f"<li><b>{s}</b> — {next(k['text'] for k in p['kootas'] if k['name']==s)}</li>"
                     for s in p.get("strengths", []))
        wo = "".join(f"<li><b>{s}</b> — {next(k['text'] for k in p['kootas'] if k['name']==s)}</li>"
                     for s in p.get("watchouts", []))
        sw_html = "<h2>Is jodi ki taakat — aur dhyaan ki jagah</h2>"
        if st: sw_html += f"<p class='swh' style='color:#2E7D53'>💪 Strengths</p><ul class='swl'>{st}</ul>"
        if wo: sw_html += f"<p class='swh' style='color:#C93B2E'>⚠️ Watch-outs</p><ul class='swl'>{wo}</ul>"

    # ---------- element dynamic + nakshatra lines ----------
    el_html = ""
    if p.get("element"):
        el = p["element"]; nl = p.get("nak_lines", {})
        el_html = (f"<h2>Aap dono ki energy</h2>"
                   f"<div class='elbox'><b>{m['p1']}: {el['p1']} · {m['p2']}: {el['p2']}</b>"
                   f"<p>{el['text']}</p></div>"
                   f"<div class='nlbox'><p><b>{m['p1']}:</b> {nl.get('p1','')}</p>"
                   f"<p style='margin-top:8px'><b>{m['p2']}:</b> {nl.get('p2','')}</p></div>")

    # ---------- low score guidance ----------
    low_html = ""
    if p.get("effective", p["total"]) < 24:
        low_html = ("<h2>Score kam hai — iska matlab kya hai?</h2>"
            "<div class='lowbox'>"
            "<p><b>Pehli baat:</b> guna milan ek classical input hai, poora faisla nahi. "
            "Yeh Moon-positions ki compatibility napta hai — values, maturity aur commitment nahi, "
            "jo kisi bhi rishtey ke asli pillars hain.</p>"
            "<p><b>Dusri baat:</b> upar dekhiye kaunse kootas mein kami hai. Gana ya Graha Maitri "
            "ki kami <i>improvable</i> hai — yeh communication-patterns ki baat hai jo couples seekh "
            "lete hain. Nadi/Bhakoot dosha (agar cancelled nahi) traditional weight zyada rakhta hai — "
            "wahan family-elders aur apne vivek dono se salaah kijiye.</p>"
            "<p><b>Teesri baat:</b> lakhs of successful marriages kam score ke saath hui hain. "
            "Score ko information ki tarah use kijiye — kis cheez par kaam karna hoga yeh jaanne ke "
            "liye — verdict ki tarah nahi.</p></div>")

    notes = "".join(f"<div class='note'>{n}</div>" for n in p["notes"])
    vcol = VERDICT_COLOR[p["verdict_key"]]
    return f"""<!DOCTYPE html><html lang="hi-IN"><head><meta charset="utf-8">
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
.ktop{{display:flex;justify-content:space-between;font-family:var(--display)}}
.ks{{font-weight:800}}
.kbar{{height:7px;background:#EFE8D8;border-radius:4px;margin:8px 0;overflow:hidden}}
.kbar div{{height:100%;border-radius:4px}}
.kd{{font-size:13px;color:var(--muted)}}
.mg,.note{{background:#F6E7C6;border-radius:12px;padding:15px;font-size:14px;margin:10px 0}}
.note{{background:#fff;border:1.5px solid var(--haldi)}}
.tn{{font-size:12px;color:var(--muted);margin-top:24px}}
.kt{{font-size:14px;margin-top:8px;color:#33355000;color:#3A3C55}}
.canc{{background:#fff;border:2px solid #2E7D53;border-radius:12px;padding:14px 16px;margin-bottom:10px;font-size:14px}}
.canc p{{margin-top:5px}}
.effbox{{background:var(--midnight);color:#F3EFE4;border-radius:12px;padding:16px;font-size:15px;text-align:center}}
.effbox b{{color:var(--haldi);font-family:var(--display);font-size:20px}}
.swh{{font-family:var(--display);font-weight:800;font-size:14px;margin:14px 0 6px}}
.swl{{margin-left:20px}}.swl li{{font-size:14px;margin-bottom:8px}}
.elbox,.nlbox,.lowbox{{background:#fff;border:1.5px solid var(--line);border-radius:12px;padding:15px 16px;margin-bottom:10px;font-size:14px}}
.elbox b{{font-family:var(--display)}}.elbox p{{margin-top:6px}}
.lowbox p{{margin-bottom:10px}}
</style></head><body>
<div class="hero"><p class="brand">✦ AXTROSHASTRA · KUNDLI MILAN</p>
<h1>{m['p1']} ✕ {m['p2']}</h1>
<p class="score">{p['total']}<small>/36</small></p>
<span class="verdict">{p['verdict'].upper()}</span>
{("<p style='margin-top:10px;font-size:14px;color:#B9BBD0'>Dosha cancellation ke baad: <b style='color:#E4B04A'>" + str(p['effective']) + "/36</b></p>") if p.get('cancellations') else ""}</div>
<h2>Ashtakoota — aatho kootas ka breakdown</h2>{rows}
{canc_html}
{sw_html}
{el_html}
<h2>Manglik check</h2><div class="mg">{p['manglik']['note']}</div>
{('<h2>Important notes</h2>' + notes) if notes else ''}
{low_html}
<p class="tn">System: {m['system']} · {m['time_note']} · Generated {m['generated']}<br>
Guna milan is one classical input to a marriage decision, not the whole decision.
100% refund within 7 days — <a href='https://wa.me/919650973345' style='color:inherit'>WhatsApp +91 96509 73345</a> · <a href="/privacy" style="color:inherit">Privacy</a> · <a href="/terms" style="color:inherit">Terms</a> · <a href="/refunds" style="color:inherit">Refund Policy</a></p>
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
100% refund within 7 days — <a href='https://wa.me/919650973345' style='color:inherit'>WhatsApp +91 96509 73345</a> · <a href="/privacy" style="color:inherit">Privacy</a> · <a href="/terms" style="color:inherit">Terms</a> · <a href="/refunds" style="color:inherit">Refund Policy</a></p>
</body></html>"""
