"""
milan_v2.py — redesigned Kundli Milan report (Warm palette, GenZ positioning).

Full ~30-page payload-driven renderer for compute_milan() output. Feature-flagged:
the web layer calls this only via /report/{id}?v2=1, so the live render_milan in
report_view.py is untouched while it's built out.

Every FACT is engine-computed and read here — no astrology in the view. Reuses the
classical tables (THEMES/KOOTA_UI/REMEDIES/ACTION_PLAN/ARCHETYPE) from
report_view.py. Descriptive PROSE slots call the LLM via narr(); when the LLM is
off/unfunded, narr() returns None and the deterministic bank text is used.
"""
from html import escape
from narrative import narr
from report_view import (THEMES, KOOTA_UI, REMEDIES, ACTION_PLAN, THEME_DEEP,
                         ARCHETYPE, ARCHETYPE_DEFAULT, _theme_scores,
                         milan_one_breath)

SIGN_GLYPH = {"Aries": "♈", "Taurus": "♉", "Gemini": "♊", "Cancer": "♋",
              "Leo": "♌", "Virgo": "♍", "Libra": "♎", "Scorpio": "♏",
              "Sagittarius": "♐", "Capricorn": "♑", "Aquarius": "♒", "Pisces": "♓"}

NAK_ANIMAL = {
    "Ashwini": "Horse", "Bharani": "Elephant", "Krittika": "Sheep",
    "Rohini": "Serpent", "Mrigashira": "Serpent", "Ardra": "Dog",
    "Punarvasu": "Cat", "Pushya": "Sheep", "Ashlesha": "Cat",
    "Magha": "Rat", "Purva Phalguni": "Rat", "Uttara Phalguni": "Cow",
    "Hasta": "Buffalo", "Chitra": "Tiger", "Swati": "Buffalo",
    "Vishakha": "Tiger", "Anuradha": "Deer", "Jyeshtha": "Deer",
    "Mula": "Dog", "Purva Ashadha": "Monkey", "Uttara Ashadha": "Mongoose",
    "Shravana": "Monkey", "Dhanishta": "Lion", "Shatabhisha": "Horse",
    "Purva Bhadrapada": "Lion", "Uttara Bhadrapada": "Cow", "Revati": "Elephant",
}
ANIMAL_EMOJI = {
    "Horse": "🐎", "Elephant": "🐘", "Sheep": "🐑", "Serpent": "🐍",
    "Dog": "🐕", "Cat": "🐈", "Rat": "🐀", "Cow": "🐄", "Buffalo": "🦬",
    "Tiger": "🐅", "Deer": "🦌", "Monkey": "🐒", "Mongoose": "🦡", "Lion": "🦁",
}
ANIMAL_ADJ = {
    "Horse": "free, spirited, independent",
    "Elephant": "steady, loyal, protective",
    "Sheep": "gentle, nurturing, patient",
    "Serpent": "magnetic, subtle, intense",
    "Dog": "devoted, alert, protective",
    "Cat": "independent, graceful, selective",
    "Rat": "clever, resourceful, quick",
    "Cow": "nurturing, patient, grounded",
    "Buffalo": "strong, persistent, dependable",
    "Tiger": "fierce, passionate, dominant",
    "Deer": "gentle, sensitive, alert",
    "Monkey": "playful, clever, energetic",
    "Mongoose": "quick, sharp, fearless",
    "Lion": "warm, proud, wholehearted",
}

LORD_SYMBOL = {"Sun": "☉", "Moon": "☽", "Mars": "♂", "Mercury": "☿",
               "Jupiter": "♃", "Venus": "♀", "Saturn": "♄", "Rahu": "☊", "Ketu": "☋"}
LORD_SHORT = {
    "Sun": ("the Sun mind", "authoritative, proud, leading"),
    "Moon": ("the Moon mind", "nurturing, intuitive, receptive"),
    "Mars": ("the Mars mind", "action-first, direct, brave"),
    "Mercury": ("the Mercury mind", "quick, curious, verbal"),
    "Jupiter": ("the Jupiter mind", "deep, feeling, meaning-led"),
    "Venus": ("the Venus mind", "harmonious, aesthetic, connecting"),
    "Saturn": ("the Saturn mind", "structured, patient, enduring"),
    "Rahu": ("the Rahu mind", "intense, unconventional, boundary-pushing"),
    "Ketu": ("the Ketu mind", "detached, spiritual, old-soul"),
}
LORD_ELEM_CLS = {"Mercury": "air", "Jupiter": "water", "Venus": "rose",
                 "Mars": "rose", "Saturn": "air", "Sun": "gold",
                 "Moon": "water", "Rahu": "air", "Ketu": "water"}

LORD_BODY = {
    "Mercury": "Your Moon is ruled by Mercury — the planet of the fast, logical, talk-it-out mind. You process by speaking, want the why and the what-next, and move on quickly.",
    "Jupiter": "Your Moon is ruled by Jupiter — the planet of meaning, faith and feeling. You process inwardly, lead with the heart, and go deep before you speak.",
    "Venus": "Your Moon is ruled by Venus — the planet of harmony, beauty and connection. You lead with warmth, seek balance, and love through care and closeness.",
    "Mars": "Your Moon is ruled by Mars — the planet of action and drive. You process by doing, lead with courage, and love fiercely and protectively.",
    "Saturn": "Your Moon is ruled by Saturn — the planet of structure and endurance. You process slowly and deeply, lead with patience, and love through commitment and consistency.",
    "Sun": "Your Moon is ruled by the Sun — the planet of identity and authority. You process through self-expression, lead naturally, and love with generosity.",
    "Moon": "Your Moon is self-ruled — intuitive, receptive, emotionally attuned. You process through feeling, lead with empathy, and love by nurturing.",
    "Rahu": "Your Moon is ruled by Rahu — intense, unconventional, always pushing boundaries. You process through transformation, and love with an all-or-nothing depth.",
    "Ketu": "Your Moon is ruled by Ketu — detached yet deeply spiritual. You process through intuition, and love with a quiet, old-soul wisdom.",
}

NAK_GANA = {
    "Ashwini": "Deva", "Bharani": "Manushya", "Krittika": "Rakshasa",
    "Rohini": "Manushya", "Mrigashira": "Deva", "Ardra": "Manushya",
    "Punarvasu": "Deva", "Pushya": "Deva", "Ashlesha": "Rakshasa",
    "Magha": "Rakshasa", "Purva Phalguni": "Manushya",
    "Uttara Phalguni": "Manushya", "Hasta": "Deva", "Chitra": "Rakshasa",
    "Swati": "Deva", "Vishakha": "Rakshasa", "Anuradha": "Deva",
    "Jyeshtha": "Rakshasa", "Mula": "Rakshasa", "Purva Ashadha": "Manushya",
    "Uttara Ashadha": "Manushya", "Shravana": "Deva", "Dhanishta": "Rakshasa",
    "Shatabhisha": "Rakshasa", "Purva Bhadrapada": "Manushya",
    "Uttara Bhadrapada": "Manushya", "Revati": "Deva",
}
GANA_ADJ = {"Deva": "idealist", "Manushya": "grounded, practical", "Rakshasa": "intense, driven"}

NAK_NADI = {
    "Ashwini": "Adi", "Bharani": "Madhya", "Krittika": "Antya",
    "Rohini": "Antya", "Mrigashira": "Madhya", "Ardra": "Adi",
    "Punarvasu": "Adi", "Pushya": "Madhya", "Ashlesha": "Antya",
    "Magha": "Antya", "Purva Phalguni": "Madhya", "Uttara Phalguni": "Adi",
    "Hasta": "Adi", "Chitra": "Madhya", "Swati": "Antya",
    "Vishakha": "Antya", "Anuradha": "Madhya", "Jyeshtha": "Adi",
    "Mula": "Adi", "Purva Ashadha": "Madhya", "Uttara Ashadha": "Antya",
    "Shravana": "Antya", "Dhanishta": "Madhya", "Shatabhisha": "Adi",
    "Purva Bhadrapada": "Adi", "Uttara Bhadrapada": "Madhya", "Revati": "Antya",
}

THEME_MEASURES = {
    "Health & Vitality": "The deepest, most durable layer of compatibility — long-term vitality, health, and (whenever, and if, you want it) family. It's the factor classical astrologers weigh the most.",
    "Love & Long-Term": "Long-term closeness, family life, and shared prosperity — the layer that turns a relationship into a home.",
    "Everyday Vibe": "Your social batteries, humour, and how your moods land in a shared room — the stuff that decides whether living together feels light or like work.",
    "Chemistry & Attraction": "Instinctive, physical compatibility — the pull, the closeness, the daily rhythm of how your bodies share space.",
    "Mind & Values": "How your minds click, how you talk things through, and who leads what — the stuff long conversations and long marriages are made of.",
}

YONI_SCORE_DESC = {4: "a perfect match", 3: "natural allies", 2: "a neutral pair", 1: "different instincts", 0: "natural opposites"}

CSS = """
:root{--cream:#FAF6EE;--beige:#DFCCB1;--espresso1:#3a2c18;--espresso2:#241810;
--gold:#C9A34E;--gold-lt:#E7CE8F;--ink:#2A2338;--muted:#8A8199;--line:#ECE3D3;
--green:#3E7D5A;--amber:#B9862E;--terra:#B4674A;--bronze:#6E4F2E;
--disp:'Fraunces',Georgia,serif;--body:'Jost',-apple-system,Segoe UI,sans-serif}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--body);background:#E8E1D4;color:var(--ink);line-height:1.62;-webkit-font-smoothing:antialiased}
.book{max-width:440px;margin:0 auto}
.pg{position:relative;min-height:720px;padding:46px 30px;overflow:hidden;background:var(--cream);border-bottom:1px solid #ded4c2}
.pn{position:absolute;bottom:20px;left:0;right:0;text-align:center;font-size:10px;letter-spacing:.12em;color:var(--muted)}
.atag{position:absolute;top:20px;right:26px;font-size:9px;color:#c9bfa8;text-transform:uppercase}
.ctag{position:absolute;top:20px;right:26px;font-size:9px;color:#b9a97e;text-transform:uppercase}
.eb{font-size:10.5px;text-transform:uppercase;font-weight:600;color:var(--amber);text-align:center}
.h2{font-family:var(--disp);font-weight:400;font-size:28px;text-align:center;margin-top:8px;color:var(--ink);line-height:1.2}
.sub{color:var(--muted);text-align:center;font-size:13.5px;margin-top:7px;margin-bottom:24px}
.lead{font-family:var(--disp);font-size:16.5px;line-height:1.55;color:#3d352b;text-align:center;margin-bottom:8px}
.payoff{font-family:var(--disp);font-style:italic;font-size:15.5px;color:#3d352b;text-align:center;margin-top:18px;line-height:1.5}
.rule{width:34px;height:1px;background:var(--gold);margin:14px auto}
/* cover */
.cover{background:#DFCCB1;background-image:radial-gradient(120% 80% at 50% 0%,rgba(255,255,255,.32),rgba(255,255,255,0));color:#3A2E1F;text-align:center}
.brand{font-weight:700;font-size:11px;text-transform:uppercase;color:#7A5A24;margin:6px 0 30px}
.cover h1{font-family:var(--disp);font-weight:400;font-size:44px;color:#2A2015}
.cover h1 .amp{color:#7A5A24;font-style:italic;font-size:34px;margin:0 4px}
.ringn{font-family:var(--disp);font-size:38px;fill:#2A2015}.ringl{font-size:9px;fill:rgba(58,46,31,.6)}
.arch{font-family:var(--disp);font-style:italic;font-size:21px;color:#6E4F2E;margin-top:6px}
.tag{font-family:var(--disp);font-style:italic;font-size:15px;color:rgba(58,46,31,.74);max-width:290px;margin:14px auto 0}
.pill{display:inline-block;margin-top:22px;border:1px solid rgba(58,46,31,.42);color:#4A3A24;border-radius:100px;padding:8px 20px;font-size:12px;text-transform:uppercase;font-weight:600}
/* scorecard */
.area{margin:0 0 17px}.atop{display:flex;align-items:center;gap:10px;margin-bottom:7px}
.aem{font-size:19px}.anm{font-family:var(--disp);font-size:16px;flex:1}.apct{font-family:var(--disp);font-size:15px;color:var(--muted)}
.bar{height:8px;border-radius:6px;background:#EEE6D6;overflow:hidden}.bar>i{display:block;height:100%;border-radius:6px}
.fg{background:linear-gradient(90deg,#4E9C72,#3E7D5A)}.fa{background:linear-gradient(90deg,#E0B45C,#C9A34E)}.ft{background:linear-gradient(90deg,#E0A583,#C57E56)}
.growtag{font-size:11px;color:var(--terra);font-weight:600;margin-top:5px}
.foot{text-align:center;color:var(--muted);font-size:13.5px;margin-top:4px;font-style:italic;font-family:var(--disp)}
/* flags/super */
.flag{display:flex;gap:14px;align-items:flex-start;background:#fff;border:1px solid var(--line);border-radius:16px;padding:16px 18px;margin-bottom:13px;box-shadow:0 4px 18px rgba(90,60,20,.05)}
.flag .ic{width:36px;height:36px;flex:0 0 auto;border-radius:50%;background:#E7F1EA;color:var(--green);display:flex;align-items:center;justify-content:center;font-size:17px}
.flag b{font-family:var(--disp);font-size:15.5px;display:block}.flag p{font-size:13.5px;color:var(--muted);margin-top:2px}
.super{background:linear-gradient(135deg,var(--espresso1),var(--espresso2));color:#F3EEE4;border-radius:18px;padding:20px;margin-top:18px;text-align:center}
.super .l{color:var(--gold);font-size:10px;font-weight:700}.super p{font-family:var(--disp);font-size:17px;line-height:1.5;margin-top:9px;color:#EDE7DA}
/* playbook/acts */
.growbox{background:#FBEFE3;border:1px solid #EFD9C4;border-radius:16px;padding:18px;margin-bottom:18px}
.growbox .t{font-family:var(--disp);font-size:18px;color:var(--terra)}.growbox p{font-size:14px;color:#7a5a48;margin-top:6px}
.act{background:#fff;border:1px solid var(--line);border-left:3px solid var(--gold);border-radius:12px;padding:12px 15px;margin-bottom:10px;box-shadow:0 3px 12px rgba(90,60,20,.04)}
.act .k{font-size:10px;text-transform:uppercase;color:var(--amber);font-weight:700}.act .v{font-size:14px;margin-top:3px}.act .v em{font-family:var(--disp);font-style:italic;color:#6a5a48}
.ritual{font-size:11.5px;color:var(--muted);text-align:center;margin-top:12px;font-style:italic;font-family:var(--disp)}
/* will */
.will{background:radial-gradient(120% 70% at 50% 0%,var(--espresso1),var(--espresso2) 68%);color:#F3EEE4;text-align:center}
.will .eb{color:var(--gold-lt)}.will .h2{color:#fff}
.bigyes{font-family:var(--disp);font-style:italic;font-size:40px;color:#E0B45C;margin:6px 0 12px}
.will .bd{font-family:var(--disp);font-size:15.5px;line-height:1.5;color:#D8CBB4;max-width:310px;margin:0 auto}
.norm{font-size:12px;color:#B3A488;max-width:290px;margin:16px auto 0}
.scard{background:var(--cream);color:var(--ink);border-radius:18px;padding:20px;margin:22px auto 0;max-width:320px;box-shadow:0 12px 32px rgba(0,0,0,.3)}
.scard .n{font-family:var(--disp);font-size:22px}.scard .a{color:var(--amber);font-style:italic;font-family:var(--disp);font-size:13px;margin-top:2px}
.scard .b{font-family:var(--disp);font-size:36px;color:var(--gold);margin-top:8px}.scard .st{color:var(--gold);letter-spacing:4px;margin-top:3px}.scard .v{font-size:10px;text-transform:uppercase;color:var(--muted);margin-top:6px}
/* profiles */
.prof{background:#fff;border:1px solid var(--line);border-radius:18px;padding:11px 18px;margin-bottom:8px;box-shadow:0 5px 20px rgba(90,60,20,.05);text-align:center}
.prof .g{display:inline-flex;align-items:center;justify-content:center;width:40px;height:40px;border-radius:12px;background:#FFF9F3;border:1px solid #F1E7D6;color:var(--amber);font-size:20px;font-family:var(--body)}
.prof .nm{font-family:var(--disp);font-size:19px;margin-top:5px}
.brg{margin:6px 0 2px}.br{display:flex;gap:7px;justify-content:center;align-items:baseline;padding:2px 0;flex-wrap:wrap}
.br b{font-family:var(--disp);font-weight:600}.br span{font-size:10px;color:var(--muted)}
.br.s{color:#9a8fae;font-size:13.5px}.br.m{background:#FBF4E7;border:1px solid #F0E2C4;border-radius:11px;padding:6px 10px;margin-top:3px;font-size:15px}.br.m b{color:var(--amber);font-size:16px}
.pmeta{font-size:11.5px;color:var(--muted);margin-top:3px}
.plove{font-family:var(--disp);font-style:italic;font-size:13.5px;color:#4a4459;margin-top:7px;border-top:1px solid var(--line);padding-top:7px;line-height:1.4}
.between{text-align:center;font-family:var(--disp);font-style:italic;font-size:15px;color:var(--terra);margin:4px 0 2px}
.moonwhy{background:#FBEFE3;border:1px solid #EFD9C4;border-radius:12px;padding:9px 14px;margin-top:10px;text-align:center}
.moonwhy p{font-size:11.6px;color:#7a5a48;font-style:italic;font-family:var(--disp);line-height:1.45}
/* mind cards (deep-dive) */
.mind{background:#fff;border:1px solid var(--line);border-radius:16px;padding:16px 18px;margin-bottom:13px;box-shadow:0 4px 16px rgba(90,60,20,.04)}
.mind .mh{display:flex;align-items:center;gap:9px}
.mind .planet{width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;flex:0 0 auto}
.mind .planet.air{background:#EAF0F5;color:#5b7791}.mind .planet.water{background:#EAF1F0;color:#3E7D6E}
.mind .planet.rose{background:#F7ECEF;color:#C06E86}.mind .planet.gold{background:#F6EFDF;color:#B9862E}
.mind b{font-family:var(--disp);font-size:15.5px}.mind .who{font-size:11px;color:var(--muted)}
.mind p{font-size:14px;color:#4a4459;margin-top:8px}
.friction{background:#F6EFDF;border:1px solid #EBDCBB;border-radius:14px;padding:14px 15px;margin-top:6px}
.friction .t{font-family:var(--disp);font-size:14.5px;color:var(--amber)}.friction p{font-size:14px;color:#6b5f42;margin-top:6px}
/* area/koota */
.scorebig{font-family:var(--disp);font-size:42px;text-align:center}.scorebig small{font-size:19px;color:var(--muted)}
.trophy{width:60px;height:60px;border-radius:50%;background:linear-gradient(135deg,#EAF1EC,#DDEBE1);display:flex;align-items:center;justify-content:center;font-size:28px;margin:0 auto 4px}
.trophy.a{background:linear-gradient(135deg,#FBEFE3,#F1DEC8)}
.scene{background:#FBEFE3;border:1px solid #EFD9C4;border-radius:13px;padding:14px 15px;margin-bottom:14px}
.scene .t{font-family:var(--disp);font-size:14px;color:var(--terra);font-style:italic}.scene p{font-size:13.5px;color:#7a5a48;margin-top:5px}
.why{background:#fff;border:1px solid var(--line);border-radius:13px;padding:14px;margin-top:14px}.why .t{font-family:var(--disp);font-size:14.5px;color:var(--green)}.why.a .t{color:var(--terra)}.why p{font-size:14px;color:#4a4459;margin-top:5px}
.story{font-family:var(--disp);font-size:16.5px;line-height:1.65;color:#3d352b;text-align:center;margin-top:8px}.story b{color:var(--amber);font-weight:600}
/* checks/timing */
.chk{display:flex;gap:12px;align-items:flex-start;padding:13px 0;border-top:1px solid var(--line)}
.chk .bd{width:26px;height:26px;border-radius:50%;flex:0 0 auto;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;color:#fff}
.chk .bd.ok{background:var(--green)}.chk .bd.mild{background:var(--amber)}.chk .bd.ic{background:transparent;font-size:17px}
.chk b{font-family:var(--disp);font-size:14.5px}.chk p{font-size:13.5px;color:var(--muted);margin-top:2px}
/* letter/cert */
.letter{background:#fff;border:1px solid var(--line);border-radius:18px;padding:22px 20px;margin-top:14px;box-shadow:0 6px 22px rgba(90,60,20,.06)}
.letter p{font-family:var(--disp);font-size:15px;line-height:1.7;color:#3d352b}.letter .sign{font-family:var(--disp);font-style:italic;font-size:14px;color:var(--amber);margin-top:14px;text-align:right}
.cert{border:2px solid var(--gold);border-radius:16px;padding:26px 20px;margin-top:16px;text-align:center;background:linear-gradient(180deg,#fffdf8,#FAF3E4)}
.cert .seal{font-size:26px;color:var(--gold)}.cert .lbl{letter-spacing:.26em;font-size:10px;color:var(--amber);font-weight:700;margin-top:6px}
.cert .n{font-family:var(--disp);font-size:26px;margin-top:8px}.cert .a{font-family:var(--disp);font-style:italic;color:var(--amber);font-size:14px;margin-top:2px}
.cert .st{color:var(--gold);letter-spacing:5px;font-size:17px;margin:11px 0}.cert .b{font-family:var(--disp);font-size:19px}.cert .q{font-family:var(--disp);font-style:italic;font-size:13.5px;color:var(--muted);margin-top:11px}
/* dark/method/appendix */
.dark{background:linear-gradient(135deg,var(--espresso1),var(--espresso2));color:#E9E3D6}.dark .eb{color:var(--gold-lt)}.dark .h2{color:#fff}
.dark .pn{color:rgba(201,163,78,.7)}
.mstep{display:flex;gap:12px;align-items:flex-start;margin-top:15px}.mstep .n{width:26px;height:26px;border-radius:50%;border:1px solid var(--gold);color:var(--gold);flex:0 0 auto;display:flex;align-items:center;justify-content:center;font-size:12px;font-family:var(--disp)}
.mstep b{font-family:var(--disp);font-size:14px;color:#fff}.mstep p{font-size:13.5px;color:#CBBFA6;margin-top:2px}
.moons{display:flex;gap:12px;justify-content:center;margin-top:18px}.moonchip{background:rgba(255,255,255,.06);border:1px solid rgba(201,163,78,.3);border-radius:12px;padding:10px 14px;text-align:center}.moonchip .g{font-size:20px;color:var(--gold-lt)}.moonchip .s{font-size:10px;color:#CBBFA6;margin-top:3px}
.tagline{font-family:var(--disp);font-style:italic;font-size:15px;color:var(--gold-lt);text-align:center;margin-top:20px}
.gloss{font-size:13.5px;color:#4a4459;padding:8px 0;border-top:1px solid var(--line)}.gloss:first-of-type{border-top:0}.gloss b{font-family:var(--disp);color:var(--ink)}
.inbox{background:#fff;border:1px solid var(--line);border-radius:14px;padding:8px 16px;margin-bottom:14px}
.inrow{display:flex;justify-content:space-between;gap:10px;font-size:13.5px;padding:9px 0;border-top:1px solid var(--line)}.inrow:first-child{border-top:0}.inrow .ik{color:var(--muted)}.inrow .iv{font-weight:600;text-align:right}
.derive{background:#FBEFE3;border:1px solid #EFD9C4;border-radius:10px;padding:11px 13px;font-size:11.5px;color:#6a5f52;margin-top:6px}
.crow{background:#fff;border:1px solid var(--line);border-radius:12px;padding:11px 14px;margin-bottom:8px}
.crow .ct{display:flex;justify-content:space-between;align-items:baseline}.crow .cn{font-family:var(--disp);font-size:14px}.crow .cn small{color:var(--muted);font-weight:400;font-size:10px}
.crow .sc{font-family:var(--disp);font-weight:600;color:var(--amber);font-size:14px}.crow .val{font-size:13.5px;margin-top:5px;color:#4a4459}.crow .val b{color:var(--ink)}
.crow .rl{font-size:11px;color:#8a7f99;margin-top:4px;font-style:italic;width:auto;height:auto;background:none;display:block}
.total{text-align:center;background:var(--espresso2);color:#fff;border-radius:12px;padding:11px;font-family:var(--disp);font-weight:600;margin:12px 0 4px}
.verify{background:rgba(62,125,90,.14);border:1px solid rgba(62,125,90,.4);border-radius:12px;padding:14px 15px;margin-top:14px}.verify b{font-family:var(--disp);color:#9fe0bd}.verify p{font-size:13.5px;color:#B9D6C6;margin-top:5px}
/* actions */
.actbar{max-width:440px;margin:0 auto;padding:18px 30px 34px;background:var(--cream);text-align:center}
.actbar a{display:inline-block;margin:4px;background:linear-gradient(135deg,var(--espresso1),var(--espresso2));color:#F3EEE4;text-decoration:none;border-radius:100px;padding:12px 22px;font-weight:700;font-size:14px;font-family:var(--body)}
.actbar a.wa{background:#25D366;color:#0b2f18}
@page{size:440px 812px;margin:0}
@media print{body{background:#fff;-webkit-print-color-adjust:exact;print-color-adjust:exact}.book{max-width:440px}
.pg{width:440px;height:812px;page-break-after:always;border-bottom:none}.pg:last-child{page-break-after:auto}.actbar{display:none}}
"""

AX_PRE = ('<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
          '<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;'
          '0,9..144,600;1,9..144,400&family=Jost:wght@400;500;600;700&display=swap" rel="stylesheet">')


def _chip(pct):
    if pct >= 75: return ("fg", "var(--green)", "Strong \U0001F49A")
    if pct >= 45: return ("fa", "var(--amber)", "Solid \U0001F49B")
    return ("ft", "var(--terra)", "Grow \U0001F331")


def _ring(pct):
    circ = 439.8; dash = max(0.0, min(pct, 100)) / 100 * circ
    return (f'<svg width="164" height="164" viewBox="0 0 164 164">'
            f'<circle cx="82" cy="82" r="70" fill="none" stroke="rgba(58,46,31,.18)" stroke-width="7"/>'
            f'<circle cx="82" cy="82" r="70" fill="none" stroke="#5C4426" stroke-width="7" stroke-linecap="round" '
            f'stroke-dasharray="{dash:.1f} {circ}" transform="rotate(-90 82 82)"/>'
            f'<text class="ringn" x="82" y="84" text-anchor="middle">{pct}%</text>'
            f'<text class="ringl" x="82" y="104" text-anchor="middle">COMPATIBLE</text></svg>')


def _verdict_word(pct):
    if pct >= 88: return "Excellent Match"
    if pct >= 68: return "Very Good Match"
    if pct >= 50: return "Good Match"
    return "Worth Understanding"


def _stars(pct):
    n = max(1, min(5, round(pct / 20)))
    return "★ " * n + "☆ " * (5 - n)


def _sc(k):
    return int(k["score"]) if float(k["score"]).is_integer() else k["score"]


# ------------------------------------------------------------------ builders
def render_milan_v2(p: dict) -> str:
    m = p.get("meta", {})
    p1n = escape(m.get("p1", "Partner 1")); p2n = escape(m.get("p2", "Partner 2"))
    kootas = p.get("kootas", []); by = {k["name"]: k for k in kootas}
    pct = int(p.get("match_pct") or round((p.get("effective") or p.get("total", 0)) / 36 * 100))
    prof = p.get("profiles") or {}; pr1, pr2 = prof.get("p1", {}), prof.get("p2", {})
    arch = ARCHETYPE.get(frozenset({pr1.get("element"), pr2.get("element")}), ARCHETYPE_DEFAULT)
    themes = _theme_scores(kootas)
    strong = [t for t in themes if t["pct"] >= 75]
    weakest = themes[-1] if themes else None
    S = []

    # 1 cover
    S.append(("cover",
        f'<div class="brand">✦ Axtroshastra · Love Compatibility</div>'
        f'<h1>{p1n} <span class="amp">&amp;</span> {p2n}</h1>'
        f'<div style="display:flex;justify-content:center;margin:22px 0 6px">{_ring(pct)}</div>'
        f'<div class="arch">{escape(arch["name"])} {arch.get("emoji","")}</div>'
        f'<div class="tag">{narr(p,"headline") or escape(arch.get("tagline",""))}</div>'
        f'<div class="pill">{_verdict_word(pct)}</div>'))

    # 2 scorecard
    rows = ""
    for t in themes:
        th = t["theme"]; ap = int(round(t["pct"])); fill, _, _ = _chip(t["pct"])
        extra = ""
        if t is weakest and ap < 45:
            extra = f'<div class="growtag">\U0001F331 Your growth area — the good news: it’s the most fixable one</div>'
        rows += (f'<div class="area"><div class="atop"><span class="aem">{th["emoji"]}</span>'
                 f'<span class="anm">{escape(th["name"])}</span><span class="apct">{ap}%</span></div>'
                 f'<div class="bar"><i class="{fill}" style="width:{max(ap,6)}%"></i></div>{extra}</div>')
    S.append(("", f'<div class="eb">At a glance</div><div class="h2">How you match, in {len(themes)} areas</div>'
                  f'<div class="sub">Strongest first</div>{rows}'
                  f'<div class="foot">{len(strong)} of your {len(themes)} areas are naturally strong.</div>'))

    # 3 why you work
    flags = ""
    for t in strong[:3]:
        th = t["theme"]
        flags += (f'<div class="flag"><div class="ic">{th["emoji"]}</div><div><b>{escape(th["name"])}</b>'
                  f'<p>{escape(th["blurb"])}.</p></div></div>')
    if not flags:
        flags = '<div class="flag"><div class="ic">✨</div><div><b>Your own kind of match</b><p>A mix that’s uniquely yours.</p></div></div>'
    superp = narr(p, "summary") or (f"You’re strong where it’s hardest to build — "
              f"{', '.join(escape(t['theme']['name']) for t in strong[:3]) or 'the foundations'}.")
    S.append(("", f'<div class="eb">Your green flags</div><div class="h2">Why you two work</div>'
                  f'<div class="sub">The strengths worth celebrating \U0001F49A</div>{flags}'
                  f'<div class="super"><div class="l">YOUR SUPERPOWER</div><p>{superp}</p></div>'))

    # 4 playbook
    S += _playbook(p, by)
    # 5 will it last
    S.append(("will",
        f'<div class="eb">The honest answer</div><div class="h2">Will it last?</div>'
        f'<div class="bigyes">Yes — with intention.</div>'
        f'<p class="bd">You’ve got a strong hand: {pct}%, with your deepest foundations already solid. '
        f'Compatibility gets you to the start line; the playbook wins the race.</p>'
        f'<p class="norm">Most happy couples aren’t 100%. A strong base + a little effort = a genuinely lasting match.</p>'
        f'<div class="scard"><div class="n">{p1n} &amp; {p2n}</div><div class="a">{escape(arch["name"])} {arch.get("emoji","")}</div>'
        f'<div class="b">{pct}%</div><div class="st">{_stars(pct)}</div><div class="v">{_verdict_word(pct)}</div></div>'))

    # 6 two of you
    S += _two_of_you(p, pr1, pr2)
    # 7..N area deep-dives: growth area first, then rest by strength
    S += _area_pages(themes, by, p, pr1, pr2)
    # synthesis
    S += _synthesis(p, themes, strong)
    # checks
    S += _checks(p, by)
    # timing
    S += _timing()
    # toolkit
    S += _toolkit(p, by)
    # method (standalone dark page)
    S += _method(pr1, pr2)
    # what score means
    S += _score_means(p, pct)
    # note
    S += _note(p, p1n, p2n)
    # keepsake
    S.append(("", f'<div class="eb">Yours to keep</div><div class="h2">Compatibility Certificate</div>'
                  f'<div class="cert"><div class="seal">✦</div><div class="lbl">AXTROSHASTRA</div>'
                  f'<div class="n">{p1n} &amp; {p2n}</div><div class="a">{escape(arch["name"])} {arch.get("emoji","")}</div>'
                  f'<div class="st">{_stars(pct)}</div><div class="b">{pct}% · {_verdict_word(pct)}</div>'
                  f'<div class="q">“According to Vedic astrology, this relationship holds warm and auspicious potential.”</div></div>'))
    # appendix
    S += _appendix(p, pr1, pr2, kootas, by)

    # assemble + auto-number
    pages = "".join(f'<section class="pg {cls}">{inner}<div class="pn">{i:02d}</div></section>'
                    for i, (cls, inner) in enumerate(S, 1))
    # Share the LIVE report URL alongside the score — recipients need the link,
    # not just the number. Uses navigator.share when available, else wa.me with
    # the current page URL appended (built at click time so it's correct in every
    # environment). Mirrors report_view.axShare; the old href shared text only.
    share_text = f"Our Kundli Milan: {pct}% ✨"
    actbar = (f'<div class="actbar"><a href="#" onclick="window.print();return false;">&#11015; Download PDF</a> '
              f'<a class="wa" href="#" rel="noopener" onclick="'
              f"var u=location.href,t='{share_text}';"
              f"if(navigator.share){{navigator.share({{title:'Axtroshastra',text:t,url:u}}).catch(function(){{}});}}"
              f"else{{window.open('https://wa.me/?text='+encodeURIComponent(t+' '+u),'_blank');}}"
              f'return false;">Share on WhatsApp</a></div>')
    return (f'<!DOCTYPE html><html lang="en"><head>{AX_PRE}<title>{p1n} ✕ {p2n} — Love Compatibility</title>'
            f'<style>{CSS}</style></head><body><div class="book">{pages}</div>{actbar}</body></html>')


def _playbook(p, by):
    ranked = sorted((k for k in by.values() if k["max"]), key=lambda k: k["score"] / k["max"])
    t = next((k for k in ranked if k["name"] in REMEDIES and k["score"] / k["max"] < 0.6), None)
    if not t:
        return []
    ui = KOOTA_UI.get(t["name"], {"emoji": "\U0001F331", "label": t["name"]})
    rem = REMEDIES.get(t["name"], {}); ap = ACTION_PLAN.get(t["name"], {})
    intro = narr(p, "growth") or escape(rem.get("work_on", t.get("text", "")))
    acts = ""
    if ap.get("try"): acts += f'<div class="act"><div class="k">\U0001F3AF Try this week</div><div class="v">{escape(ap["try"])}</div></div>'
    if ap.get("talk"): acts += f'<div class="act"><div class="k">\U0001F4AC Say this</div><div class="v"><em>{escape(ap["talk"])}</em></div></div>'
    if ap.get("green"): acts += f'<div class="act"><div class="k">✅ Green flag you’ll notice</div><div class="v">{escape(ap["green"])}</div></div>'
    rit = f'<div class="ritual">Optional ritual: {escape(rem["remedy"])}</div>' if rem.get("remedy") else ""
    return [("", f'<div class="eb">Your playbook</div><div class="h2">One thing worth working on</div>'
                 f'<div class="sub">Small effort, big payoff</div>'
                 f'<div class="growbox"><div class="t">{ui["emoji"]} {escape(ui["label"])}</div><p>{intro}</p></div>{acts}{rit}')]


def _two_of_you(p, pr1, pr2):
    def card(pr):
        sun = pr.get("sun_western"); moon = escape(pr.get("sign", "")); nm = escape(pr.get("name", ""))
        glyph = SIGN_GLYPH.get(pr.get("sign"), "✦")
        srow = (f'<div class="br s">☀️ <b>{escape(sun)}</b> <span>· the sign the world knows you by</span></div>'
                if sun else "")
        return (f'<div class="prof"><div class="g">{glyph}︎</div><div class="nm">{nm}</div>'
                f'<div class="brg">{srow}<div class="br m">\U0001F319 <b>{moon} Moon</b> <span>· your love sign</span></div></div>'
                f'<div class="pmeta">{escape(pr.get("nak",""))} · {escape((pr.get("element") or "").title())} · ruled by {escape(pr.get("lord",""))}</div>'
                f'<div class="plove">“{escape(pr.get("love",""))}”</div></div>')
    el = p.get("element") or {}
    return [("", f'<div class="atag">The full reading</div>'
                 f'<div class="eb">Where it begins</div><div class="h2">The two of you</div>'
                 f'<div class="sub">You know your Sun sign. For love, we read your Moon.</div>'
                 f'{card(pr1)}<div class="between">{escape(el.get("p1",""))} meets {escape(el.get("p2",""))}</div>{card(pr2)}'
                 f'<div class="moonwhy"><p>The Sun is who you are to the world; the Moon is who you are in love — '
                 f'so Vedic matching reads the Moon, not the Sun.</p></div>')]


def _mind_card(pr, sym, title_label, adj):
    nm = escape(pr.get("name", ""))
    lord = pr.get("lord", "")
    elem_cls = LORD_ELEM_CLS.get(lord, "air")
    body = escape(LORD_BODY.get(lord, ""))
    return (f'<div class="mind"><div class="mh"><div class="planet {elem_cls}">{sym}</div>'
            f'<div><b>{nm} — {escape(title_label)}</b><div class="who">{escape(adj)}</div></div></div>'
            f'<p>{body}</p></div>')


def _animal_card(pr):
    nm = escape(pr.get("name", ""))
    nak = pr.get("nak", "")
    animal = NAK_ANIMAL.get(nak, "")
    emoji = ANIMAL_EMOJI.get(animal, "\U0001F43E")
    adj = ANIMAL_ADJ.get(animal, "")
    elem = (pr.get("element") or "").lower()
    elem_cls = "rose" if elem in ("fire", "water") else "gold"
    return (f'<div class="mind"><div class="mh"><div class="planet {elem_cls}">{emoji}</div>'
            f'<div><b>{nm} — the {escape(animal)} instinct</b><div class="who">{escape(adj)}</div></div></div>'
            f'<p>Your nakshatra’s animal is the {escape(animal)} — {escape(ANIMAL_ADJ.get(animal, ""))}.</p></div>')


def _area_pages(themes, by, p, pr1, pr2):
    secs = []
    if not themes:
        return secs
    weakest_name = themes[-1]["theme"]["name"]
    strongest_name = themes[0]["theme"]["name"]
    is_chem = lambda th: th["name"] == "Chemistry & Attraction"

    # growth area first, then rest strongest-to-weakest
    ordered = [themes[-1]] + [t for t in themes[:-1]]

    for idx, t in enumerate(ordered):
        th = t["theme"]; tpct = int(round(t["pct"])); ks = [by[n] for n in th["kootas"] if n in by]
        is_strong = tpct >= 55
        is_growth = th["name"] == weakest_name
        is_strongest = th["name"] == strongest_name

        if is_growth:
            secs += _growth_pages(t, ks, p, pr1, pr2)
        elif is_chem(th):
            secs += _chemistry_pages(t, ks, p, pr1, pr2)
        elif is_strong:
            secs += _strong_pages(t, ks, p, pr1, pr2, is_strongest)
        else:
            secs += _weak_pages(t, ks, p, pr1, pr2)
    return secs


def _growth_pages(t, ks, p, pr1, pr2):
    th = t["theme"]; tpct = int(round(t["pct"]))
    n1 = escape(pr1.get("name", "")); n2 = escape(pr2.get("name", ""))
    l1 = pr1.get("lord", ""); l2 = pr2.get("lord", "")
    s1 = LORD_SYMBOL.get(l1, "☆"); s2 = LORD_SYMBOL.get(l2, "☆")
    ls1 = LORD_SHORT.get(l1, ("the mind", "")); ls2 = LORD_SHORT.get(l2, ("the mind", ""))
    e1 = (pr1.get("element") or "").title(); e2 = (pr2.get("element") or "").title()

    lead_text = narr(p, "deepdive_growth") or (
        f"Your report flagged {escape(th['name'])} as your growth area. "
        f"Here’s the real, computed reason — and it’s more interesting than it sounds.")

    friction_body = (f"{escape(l1)} and {escape(l2)} aren’t natural friends in the classical system — "
                     f"that’s the actual, calculated reason your {escape(th['name'])} score is low. "
                     f"You connect deeply; you just run different operating systems.")

    page1 = (f'<div class="atag">{escape(th["name"])} · 1 of 2</div>'
             f'<div class="eb">Your growth area, decoded</div>'
             f'<div class="h2">Two minds, two languages</div><div class="rule"></div>'
             f'<p class="lead">{lead_text}</p>'
             f'{_mind_card(pr1, s1, ls1[0], e1 + " · " + ls1[1])}'
             f'{_mind_card(pr2, s2, ls2[0], e2 + " · " + ls2[1])}'
             f'<div class="friction"><div class="t">Why the friction is real (not imagined)</div>'
             f'<p>{friction_body}</p></div>')

    wk = min(ks, key=lambda k: (k["score"] / k["max"]) if k["max"] else 1) if ks else {}
    ap = ACTION_PLAN.get(wk.get("name", ""), {})
    rem = REMEDIES.get(wk.get("name", ""), {})
    acts = ""
    if ap.get("try"): acts += f'<div class="act"><div class="k">\U0001F3AF Try this week</div><div class="v">{escape(ap["try"])}</div></div>'
    if ap.get("talk"): acts += f'<div class="act"><div class="k">\U0001F4AC Say this</div><div class="v"><em>{escape(ap["talk"])}</em></div></div>'
    if ap.get("green"): acts += f'<div class="act"><div class="k">✅ Green flag you’ll notice</div><div class="v">{escape(ap["green"])}</div></div>'
    payoff = (f'{e1} + {e2}, bridged, is poetry. Once {n1} learns not everything is logic, '
              f'and {n2} learns not everything needs saying — you don’t just communicate. You complete each other.')
    page2 = (f'<div class="atag">{escape(th["name"])} · 2 of 2</div>'
             f'<div class="eb">The play</div><div class="h2">You don’t need to match. Just translate.</div>'
             f'<div class="sub">The same difference, turned into a strength</div>'
             f'<div class="scene"><div class="t">When something’s wrong…</div>'
             f'<p>{n1}’s instinct is to analyse and solve. {n2}’s is to sit with the feeling first. '
             f'Neither is wrong — they just need to meet in the middle, on purpose.</p></div>'
             f'{acts}<p class="payoff">{payoff}</p>')
    return [("", page1), ("", page2)]


def _chemistry_pages(t, ks, p, pr1, pr2):
    th = t["theme"]; tpct = int(round(t["pct"]))
    a1 = NAK_ANIMAL.get(pr1.get("nak", ""), ""); a2 = NAK_ANIMAL.get(pr2.get("nak", ""), "")
    yoni_k = next((k for k in ks if k["name"] == "Yoni"), None)
    yoni_sc = int(yoni_k["score"]) if yoni_k else 2
    pair_desc = YONI_SCORE_DESC.get(yoni_sc, "a unique pair")
    _, col, _ = _chip(t["pct"])

    lead = f"A pull built on respect and effort — which, honestly, outlasts fireworks." if tpct < 60 else f"The spark is real and mutual."

    page1 = (f'<div class="atag">Chemistry · 1 of 2</div>'
             f'<div class="eb">Chemistry &amp; Attraction</div>'
             f'<div class="h2">The spark — {"real, but not on autopilot" if tpct < 60 else "alive and well"}</div>'
             f'<div class="scorebig" style="color:{col}">{tpct}<small>%</small></div>'
             f'<p class="lead" style="margin-top:8px">{lead}</p>'
             f'{_animal_card(pr1)}{_animal_card(pr2)}'
             f'<div class="friction"><div class="t">{escape(a1)} &amp; {escape(a2)} — {escape(pair_desc)}</div>'
             f'<p>{"Not natural allies, not enemies. Your chemistry is real, but it’s built on attraction you nurture, not pure gravity. The upside — that kind deepens with time instead of fading." if yoni_sc == 2 else "Your instinctive styles have a natural pull — the chemistry is already there to build on."}</p></div>')

    wk = min(ks, key=lambda k: (k["score"] / k["max"]) if k["max"] else 1) if ks else {}
    rem = REMEDIES.get(wk.get("name", ""), {})
    ap = ACTION_PLAN.get(wk.get("name", ""), {})
    acts = ""
    if ap.get("try"): acts += f'<div class="act"><div class="k">\U0001F3AF Try this fortnight</div><div class="v">{escape(ap["try"])}</div></div>'
    if ap.get("talk"): acts += f'<div class="act"><div class="k">\U0001F4AC Say this</div><div class="v"><em>{escape(ap["talk"])}</em></div></div>'
    if ap.get("green"): acts += f'<div class="act"><div class="k">✅ Green flag you’ll notice</div><div class="v">{escape(ap["green"])}</div></div>'
    rit = f'<div class="ritual">Optional: Fridays are Venus’s day — warm tones, unhurried evenings, a little more touch.</div>' if rem.get("remedy") else ""
    page2 = (f'<div class="atag">Chemistry · 2 of 2</div>'
             f'<div class="eb">The play</div><div class="h2">Keep the spark deliberate</div>'
             f'<div class="sub">Chemistry you tend to, stays</div>'
             f'<div class="scene"><div class="t">The trap to avoid…</div>'
             f'<p>A respect-based pull can quietly slide into “comfortable.” The fix isn’t more heat — '
             f'it’s more intention: closeness you choose, not leave to chance.</p></div>'
             f'{acts}{rit}')
    return [("", page1), ("", page2)]


def _strong_pages(t, ks, p, pr1, pr2, is_strongest):
    th = t["theme"]; tpct = int(round(t["pct"]))
    n1 = escape(pr1.get("name", "")); n2 = escape(pr2.get("name", ""))
    top_k = max(ks, key=lambda k: (k["score"] / k["max"]) if k["max"] else 0) if ks else {}
    score_disp = f'{_sc(top_k)}<small>/{top_k.get("max","")}</small>' if top_k else f'{tpct}<small>%</small>'

    kicker = "Your strongest factor" if is_strongest else "A quiet superpower"
    measures = THEME_MEASURES.get(th["name"], f"How strong you are in {th['name'].lower()}.")
    deep = narr(p, "deepdive_strength") if is_strongest else None
    if not deep:
        deep = THEME_DEEP.get(th["name"], "")

    why_aced = _why_aced(th, ks, pr1, pr2)

    page1 = (f'<div class="atag">{escape(th["name"])}</div>'
             f'<div class="trophy">{th["emoji"]}</div>'
             f'<div class="eb" style="text-align:center">{kicker}</div>'
             f'<div class="h2">{escape(th["name"])}</div>'
             f'<div class="scorebig">{score_disp}</div>'
             f'<p class="lead" style="margin-top:8px">{escape(deep) if deep else ""}</p>'
             f'<div class="why"><div class="t">What it measures</div><p>{escape(measures)}</p></div>'
             f'<div class="why"><div class="t">Why you aced it</div><p>{why_aced}</p></div>'
             f'<p class="payoff" style="margin-top:18px">The unglamorous, foundational fit a lot of couples never have — you begin with it built in.</p>')

    nak1 = pr1.get("nak", ""); nak2 = pr2.get("nak", "")
    g1 = NAK_GANA.get(nak1, ""); g2 = NAK_GANA.get(nak2, "")
    ga1 = GANA_ADJ.get(g1, ""); ga2 = GANA_ADJ.get(g2, "")
    scene_body = (f"is taking it for granted. When this comes naturally, couples stop being intentional — "
                  f"and let routine quietly replace connection.")
    act1_label = "\U0001F33F Honour both roles"
    act1_body = f"{n1} brings one energy, {n2} brings another. Let each lead where they’re natural instead of competing."
    if th["name"] == "Everyday Vibe" and g1 and g2:
        act1_body = (f"{n1} carries a {g1} ({ga1}) temperament, {n2} a {g2} ({ga2}) one. "
                     f"Let each lead where they’re natural instead of competing.")

    page2 = (f'<div class="atag">{escape(th["name"])} · protect it</div>'
             f'<div class="eb">Keep the good thing good</div><div class="h2">How to protect it</div>'
             f'<div class="sub">Even strengths need light care</div>'
             f'<div class="scene"><div class="t">The only risk with easy harmony…</div>'
             f'<p>{scene_body}</p></div>'
             f'<div class="act"><div class="k">{act1_label}</div><div class="v">{act1_body}</div></div>'
             f'<div class="act"><div class="k">✅ Green flag you’ll notice</div>'
             f'<div class="v">You laugh off the small stuff — and neither keeps score.</div></div>'
             f'<p class="payoff" style="margin-top:18px">You don’t need to fix this one. Just don’t sleepwalk through how good it is.</p>')
    return [("", page1), ("", page2)]


def _weak_pages(t, ks, p, pr1, pr2):
    th = t["theme"]; tpct = int(round(t["pct"]))
    _, col, _ = _chip(t["pct"])
    wk = min(ks, key=lambda k: (k["score"] / k["max"]) if k["max"] else 1) if ks else {}
    rem = REMEDIES.get(wk.get("name", ""), {}); ap = ACTION_PLAN.get(wk.get("name", ""), {})

    page1 = (f'<div class="atag">{escape(th["name"])}</div>'
             f'<div class="trophy a">{th["emoji"]}</div>'
             f'<div class="eb" style="text-align:center">Worth a look</div>'
             f'<div class="h2">{escape(th["name"])}</div>'
             f'<div class="scorebig" style="color:{col}">{tpct}<small>%</small></div>'
             f'<p class="lead" style="margin-top:8px">{escape(th["blurb"]).capitalize()}.</p>'
             f'<div class="why a"><div class="t">What it measures</div><p>{escape(THEME_MEASURES.get(th["name"], ""))}</p></div>'
             f'<div class="why a"><div class="t">What it means for you</div><p>{escape(wk.get("text", ""))}</p></div>')

    acts = ""
    if ap.get("try"): acts += f'<div class="act"><div class="k">\U0001F3AF Try this week</div><div class="v">{escape(ap["try"])}</div></div>'
    if ap.get("talk"): acts += f'<div class="act"><div class="k">\U0001F4AC Say this</div><div class="v"><em>{escape(ap["talk"])}</em></div></div>'
    rit = f'<div class="ritual">Optional ritual: {escape(rem["remedy"])}</div>' if rem.get("remedy") else ""
    page2 = (f'<div class="atag">{escape(th["name"])} · the play</div>'
             f'<div class="eb">The play</div><div class="h2">You don’t need to match. Just translate.</div>'
             f'<div class="sub">The same difference, turned into a strength</div>'
             f'<div class="scene"><div class="t">Why this is your growth edge</div><p>{escape(rem.get("work_on", ""))}</p></div>'
             f'{acts}{rit}')
    return [("", page1), ("", page2)]


def _why_aced(th, ks, pr1, pr2):
    nak1 = pr1.get("nak", ""); nak2 = pr2.get("nak", "")
    if th["name"] == "Health & Vitality":
        n1 = NAK_NADI.get(nak1, ""); n2 = NAK_NADI.get(nak2, "")
        if n1 and n2 and n1 != n2:
            return (f'Your two “Nadis” are different ({escape(n1)} &amp; {escape(n2)}) — '
                    f'the ideal, complementary result. The single hardest factor to build if it’s missing, '
                    f'and you start with it fully intact.')
        return "Your Nadi factor is strong — a positive classical sign."
    if th["name"] == "Everyday Vibe":
        g1 = NAK_GANA.get(nak1, ""); g2 = NAK_GANA.get(nak2, "")
        ga1 = GANA_ADJ.get(g1, ""); ga2 = GANA_ADJ.get(g2, "")
        return (f'{escape(pr1.get("name",""))} carries a {escape(g1)} ({escape(ga1)}) temperament, '
                f'{escape(pr2.get("name",""))} a {escape(g2)} ({escape(ga2)}) one — '
                f'a pairing that reads the same emotional weather. No walking on eggshells.')
    if th["name"] == "Love & Long-Term":
        return ("Your Moon signs sit in a mutually supportive position — the classical “green signal” "
                "for emotional closeness, family life, and shared prosperity.")
    if th["name"] == "Mind & Values":
        return ("Your Moon-lords are naturally friendly — you think in the same language. "
                "Even your disagreements make sense to each other.")
    if th["name"] == "Chemistry & Attraction":
        return ("Your instinctive styles have a natural pull — the chemistry is real "
                "and doesn’t need forcing.")
    return "Your scores here are strong — a solid classical foundation."


def _synthesis(p, themes, strong):
    # One-breath line comes from the shared helper (report_view.milan_one_breath)
    # so the report and the free teaser preview stay identical.
    return [("", f'<div class="eb">The whole picture</div><div class="h2">Your relationship, in one breath</div>'
                 f'<div class="rule"></div>'
                 f'<p class="story">{milan_one_breath(p.get("kootas", []), html=True)}</p>'
                 f'<p class="story" style="margin-top:14px">The rare part — the deep, hard-to-build compatibility — you already <b>have</b>. '
                 f'The workable part is exactly the kind couples <b>grow into</b>.</p>'
                 f'<p class="payoff" style="margin-top:20px">That’s not a fragile match. It’s a strong one, with a clear path.</p>')]


def _checks(p, by):
    mg = p.get("manglik") or {}
    mgy = bool(mg.get("p1") or mg.get("p2"))
    nadi = by.get("Nadi", {}); bhak = by.get("Bhakoot", {})
    cx = {c.get("koota") for c in (p.get("cancellations") or [])}
    nadi_ok = nadi.get("score", 0) > 0; bhak_ok = bhak.get("score", 0) > 0 or "Bhakoot" in cx
    def row(b, s, n, t):
        return f'<div class="chk"><div class="bd {b}">{s}</div><div><b>{n}</b><p>{escape(t)}</p></div></div>'
    ch = row("mild" if mgy else "ok", "!" if mgy else "✓", "Manglik (Mangal Dosha)", mg.get("note", ""))
    ch += row("ok" if nadi_ok else "mild", "✓" if nadi_ok else "!", "Nadi Dosha",
              "Your Nadis differ — no Nadi dosha, a strong positive sign." if nadi_ok
              else "Nadi is shared — often lifted when moon-signs differ; a pada-level check is advised.")
    ch += row("ok" if bhak_ok else "mild", "✓" if bhak_ok else "!", "Bhakoot Dosha",
              "Your Moon signs sit in a favourable position — long-term harmony supported." if bhak_ok
              else "A Bhakoot placement is present — check whether friendly moon-lords cancel it.")
    return [("", f'<div class="atag">The traditional checks</div>'
                 f'<div class="eb">The three big ones</div><div class="h2">The traditional checks</div>'
                 f'<div class="sub">Demystified — no fear, just facts</div>{ch}'
                 f'<p class="payoff" style="margin-top:16px">Read them as information to understand, not verdicts to fear.</p>')]


def _timing():
    rows = [("\U0001F48D", "For commitments", "Fridays and full-moon days are traditionally warm for love and vows."),
            ("\U0001F3E1", "For a new beginning", "Start something together on a rising-moon fortnight for a settled, growing start."),
            ("✈️", "For travel together", "Shared journeys deepen your bond — try to plan one each season.")]
    body = "".join(f'<div class="chk"><div class="bd ic">{e}</div><div><b>{t}</b><p>{d}</p></div></div>' for e, t, d in rows)
    return [("", f'<div class="atag">Auspicious timing</div>'
                 f'<div class="eb">Good moments</div><div class="h2">Auspicious timing</div>'
                 f'<div class="sub">General guidance — not chart-specific dates</div>{body}')]


def _toolkit(p, by):
    weak = [k for k in by.values() if k["max"] and k["score"] / k["max"] < 0.6 and k["name"] in REMEDIES]
    acts = ""
    for k in weak[:4]:
        ui = KOOTA_UI.get(k["name"], {"emoji": "•", "label": k["name"]}); ap = ACTION_PLAN.get(k["name"], {})
        if ap.get("try"):
            acts += f'<div class="act"><div class="k">{ui["emoji"]} For {escape(ui["label"]).lower()}</div><div class="v">{escape(ap["try"])}</div></div>'
    if not acts:
        acts = '<div class="act"><div class="k">\U0001F49B You’re in great shape</div><div class="v">No major work needed — just keep choosing each other.</div></div>'
    rits = ""
    for k in weak[:3]:
        rem = REMEDIES.get(k["name"], {})
        if rem.get("remedy"):
            rits += f'<div class="chk"><div class="bd ic">\U0001F54E</div><div><b>{escape(KOOTA_UI.get(k["name"],{}).get("label",k["name"]))}</b><p>{escape(rem["remedy"])}</p></div></div>'
    if not rits:
        rits = '<div class="chk"><div class="bd ic">\U0001F54E</div><div><b>A shared calm</b><p>Light a small lamp together at dusk — a grounding ritual for any couple.</p></div></div>'
    return [("", f'<div class="atag">Your toolkit · 1 of 2</div>'
                 f'<div class="eb">What to actually do</div><div class="h2">Your toolkit — the actions</div>'
                 f'<div class="sub">The real levers, in one place</div>{acts}'
                 f'<p class="payoff" style="margin-top:14px">The first remedy is always action. Do one this week.</p>'),
            ("", f'<div class="atag">Your toolkit · 2 of 2</div>'
                 f'<div class="eb">Optional · the traditional touch</div><div class="h2">If you like the rituals</div>'
                 f'<div class="sub">A cultural add-on — never a substitute for the actions</div>{rits}')]


def _method(pr1, pr2):
    g1 = SIGN_GLYPH.get(pr1.get("sign"), "✦"); g2 = SIGN_GLYPH.get(pr2.get("sign"), "✦")
    n1 = escape(pr1.get("name", "")); n2 = escape(pr2.get("name", ""))
    s1 = escape(pr1.get("sign", "")); s2 = escape(pr2.get("sign", ""))
    nk1 = escape(pr1.get("nak", "")); nk2 = escape(pr2.get("nak", ""))
    return [("dark",
        f'<div class="atag" style="color:rgba(201,163,78,.6)">The proof</div>'
        f'<div class="eb">The proof</div><div class="h2">How this was calculated</div>'
        f'<div class="sub" style="color:#B3A488">Not guessed. Computed.</div>'
        f'<div class="mstep"><div class="n">1</div><div><b>Your real sky, at birth</b>'
        f'<p>We computed the true positions of the Moon and planets from your two birth details — '
        f'NASA-grade astronomy (Swiss Ephemeris), sidereal zodiac, Lahiri ayanamsa.</p></div></div>'
        f'<div class="mstep"><div class="n">2</div><div><b>The 1000-year-old method</b>'
        f'<p>Your match runs on the classical Ashtakoota (36-guna) system — your two Moon positions '
        f'across 8 factors, dosha rules applied exactly.</p></div></div>'
        f'<div class="mstep"><div class="n">3</div><div><b>No opinions, only calculation</b>'
        f'<p>Every number here traces to your charts — not a horoscope generality or an astrologer’s mood.</p></div></div>'
        f'<div class="moons"><div class="moonchip"><div class="g">{g1}︎</div>'
        f'<div class="s">{n1}<br>{s1} · {nk1}</div></div>'
        f'<div class="moonchip"><div class="g">{g2}︎</div>'
        f'<div class="s">{n2}<br>{s2} · {nk2}</div></div></div>'
        f'<div class="tagline">Jyotish, calculated — no opinion, only calculation.</div>')]


def _score_means(p, pct):
    return [("", f'<div class="eb">Read this before you worry</div><div class="h2">What {pct}% really means</div>'
                 f'<div class="sub">A map, not a verdict</div>'
                 f'<div class="why a"><div class="t">It’s one input, not the whole story</div>'
                 f'<p>Guna milan measures your natural fit — not maturity, values or commitment, the real pillars of any marriage.</p></div>'
                 f'<div class="why a"><div class="t">The pattern matters more than the number</div>'
                 f'<p>You’re strong where it’s hardest to fix and grow where it’s easiest — the best-shaped score there is.</p></div>'
                 f'<div class="why a"><div class="t">Numbers don’t marry people</div>'
                 f'<p>Countless lasting marriages began below {pct}%. Use the number as information, not a verdict.</p></div>')]


def _note(p, p1n, p2n):
    default = (f"Dear {p1n} &amp; {p2n}, your charts tell the story of a bond with real staying power. "
               f"Where you differ isn’t a crack — it’s the one place a little patience turns difference into depth. "
               f"You already have the rare thing. Tend the rest gently, and you have the makings of a beautiful life together.")
    note = narr(p, "closing_note") or default
    return [("", f'<div class="atag">A note for you</div>'
                 f'<div class="eb">From us to you</div><div class="h2">A note to the couple</div><div class="rule"></div>'
                 f'<div class="letter"><p>{note}</p><div class="sign">— Your astrologer, Axtroshastra</div></div>')]


def _appendix(p, pr1, pr2, kootas, by):
    def crow(k, rule=""):
        sc = _sc(k)
        rl = f'<div class="rl">{escape(rule)}</div>' if rule else ""
        return (f'<div class="crow"><div class="ct"><div class="cn">{escape(k["name"])} '
                f'<small>· {escape(k.get("meaning",""))}</small></div><div class="sc">{sc}/{k["max"]}</div></div>'
                f'<div class="val">{escape(k.get("detail",""))}</div>{rl}</div>')

    g1 = SIGN_GLYPH.get(pr1.get("sign"), "✦"); g2 = SIGN_GLYPH.get(pr2.get("sign"), "✦")
    n1 = escape(pr1.get("name", "")); n2 = escape(pr2.get("name", ""))
    s1 = escape(pr1.get("sign", "")); s2 = escape(pr2.get("sign", ""))
    nk1 = escape(pr1.get("nak", "")); nk2 = escape(pr2.get("nak", ""))
    total = p.get("total") or 0; eff = p.get("effective")
    pct_val = p.get("match_pct") or (round((eff or total) / 36 * 100) if total else 0)

    secs = []
    # A charts computed (with birth details)
    p1charts = (f'<div class="moons"><div class="moonchip"><div class="g">{g1}︎</div>'
                f'<div class="s">{n1}<br>{s1} · {nk1}</div></div>'
                f'<div class="moonchip"><div class="g">{g2}︎</div>'
                f'<div class="s">{n2}<br>{s2} · {nk2}</div></div></div>')
    meta = p.get("meta") or {}
    secs.append(("", f'<div class="ctag">Appendix · The receipts</div>'
                     f'<div class="eb">Nothing hidden</div><div class="h2">The Calculations</div>'
                     f'<div class="sub">Every number in this report, shown its working</div>'
                     f'<p class="lead" style="font-size:15px">It starts with your exact birth details — turned into the real position of the Moon.</p>'
                     f'{p1charts}'
                     f'<div class="derive">longitude ÷ 30° = Rashi (sign) · ÷ 13°20′ = Nakshatra · ÷ 3°20′ = Pada</div>'
                     f'<p style="text-align:center;font-size:11.5px;color:var(--muted);margin-top:10px">'
                     f'Kundli Milan is Moon-based — these two Moon positions drive every score.</p>'))
    # B scores 1-4
    secs.append(("", f'<div class="ctag">Appendix · The 8 scores</div>'
                     f'<div class="eb">Shown, one by one</div><div class="h2">How each score was made</div>'
                     f'<div class="sub">Factors 1–4 · every score is a rule, not an opinion</div>'
                     + "".join(crow(k) for k in kootas[:4])))
    # C scores 5-8 + total
    score_sum = " + ".join(str(_sc(k)) for k in kootas[:8])
    # The headline % is the EFFECTIVE score (after any dosha cancellation), which
    # can exceed the raw koota sum. Show that step explicitly — the old
    # "{total}/36 → {pct}%" was mathematically false whenever a dosha was
    # cancelled (e.g. 18.0/36 shown as 72%, when 72% is really 26/36).
    if eff is not None and round(eff, 1) != round(total, 1):
        total_eq = (f'{score_sum} = {total}/36'
                    f'<span style="font-size:.82em;opacity:.85"> &middot; with dosha '
                    f'cancellation, {eff}/36 = {pct_val}%</span>')
    else:
        total_eq = f'{score_sum} = {total}/36 = {pct_val}%'
    secs.append(("", f'<div class="ctag">Appendix · The 8 scores</div>'
                     f'<div class="eb">Shown, one by one</div><div class="h2">…and factors 5–8</div>'
                     f'<div class="sub">Then simply added up</div>'
                     + "".join(crow(k) for k in kootas[4:8])
                     + f'<div class="total">{total_eq}</div>'))
    # D dosha checks calculated
    secs += _dosha_appendix(p, pr1, pr2, by)
    # E method + glossary (dark)
    gloss = [("Rashi", "your Moon’s zodiac sign (÷30° of the sky)"),
             ("Nakshatra", "the lunar mansion (÷13°20′), pinned to real stars"),
             ("Guna", "a compatibility point; 36 is the maximum"),
             ("Dosha", "a classical caution flag (Manglik, Nadi, Bhakoot)"),
             ("Ayanamsa", "the star-based correction (Lahiri) making it sidereal")]
    glossary = "".join(f'<div class="gloss" style="color:#D8CBB4;border-color:rgba(255,255,255,.08)">'
                       f'<b style="color:#fff">{n}</b> — {d}</div>' for n, d in gloss)
    secs.append(("dark", f'<div class="ctag" style="color:rgba(201,163,78,.6)">Appendix · The method</div>'
                         f'<div class="eb">The fine print, in plain words</div><div class="h2">Method &amp; glossary</div>'
                         f'<div class="sub" style="color:#B3A488">So you can check it yourself</div>'
                         f'<div style="background:rgba(255,255,255,.04);border:1px solid rgba(201,163,78,.2);border-radius:14px;padding:6px 16px;margin-bottom:12px">{glossary}</div>'
                         f'<div class="verify"><b>Verify it yourself</b><p>Put these birth details into any Lahiri-based panchang — '
                         f'the Moon positions will match, exactly. That’s the point: no opinion, only calculation.</p></div>'
                         f'<div class="tagline">The math is yours. The stars did the rest.</div>'))
    return secs


def _dosha_appendix(p, pr1, pr2, by):
    mg = p.get("manglik") or {}
    mgy_p1 = mg.get("p1"); mgy_p2 = mg.get("p2")
    n1 = escape(pr1.get("name", "")); n2 = escape(pr2.get("name", ""))
    nadi = by.get("Nadi", {}); bhak = by.get("Bhakoot", {})
    nak1 = pr1.get("nak", ""); nak2 = pr2.get("nak", "")
    nd1 = NAK_NADI.get(nak1, ""); nd2 = NAK_NADI.get(nak2, "")
    nadi_ok = nadi.get("score", 0) > 0
    bhak_ok = bhak.get("score", 0) > 0

    mg_status = "One-sided" if (mgy_p1 or mgy_p2) and not (mgy_p1 and mgy_p2) else ("Both" if mgy_p1 and mgy_p2 else "Clear ✓")
    mg_color = "var(--amber)" if mgy_p1 or mgy_p2 else "var(--green)"
    mg_detail = escape(mg.get("note", ""))

    nadi_status = "Clear ✓" if nadi_ok else "Shared"
    nadi_color = "var(--green)" if nadi_ok else "var(--amber)"
    nadi_detail = f"Nadis differ ({escape(nd1)} vs {escape(nd2)})." if nadi_ok else f"Nadis are the same ({escape(nd1)})."

    bhak_detail_text = escape(bhak.get("detail", ""))
    bhak_status = "Clear ✓" if bhak_ok else "Present"
    bhak_color = "var(--green)" if bhak_ok else "var(--amber)"

    rows = (f'<div class="crow"><div class="ct"><div class="cn">Manglik</div>'
            f'<div class="sc" style="color:{mg_color}">{mg_status}</div></div>'
            f'<div class="val">{mg_detail}</div>'
            f'<div class="rl">Manglik if Mars ∈ houses {{1,2,4,7,8,12}} from Moon.</div></div>'
            f'<div class="crow"><div class="ct"><div class="cn">Nadi Dosha</div>'
            f'<div class="sc" style="color:{nadi_color}">{nadi_status}</div></div>'
            f'<div class="val">{nadi_detail}</div>'
            f'<div class="rl">Dosha only if identical → {"cleared" if nadi_ok else "flagged"}.</div></div>'
            f'<div class="crow"><div class="ct"><div class="cn">Bhakoot Dosha</div>'
            f'<div class="sc" style="color:{bhak_color}">{bhak_status}</div></div>'
            f'<div class="val">{bhak_detail_text}</div>'
            f'<div class="rl">Dosha only on a 2/12, 5/9, or 6/8 axis.</div></div>')

    return [("", f'<div class="ctag">Appendix · The dosha checks</div>'
                 f'<div class="eb">The three big ones, shown</div><div class="h2">The dosha checks, calculated</div>'
                 f'<div class="sub">How each verdict was reached</div>{rows}'
                 f'<p style="text-align:center;margin-top:16px;font-family:var(--disp);font-style:italic;color:var(--muted);font-size:12.5px">'
                 f'Same rules, applied the same way, for every couple.</p>')]
