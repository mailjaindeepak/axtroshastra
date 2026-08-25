#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-celebrity Google-autosuggest harvest (gl=IN) — the same data source as the
manager's screenshot. One request per (celeb x seed), politely rate-limited."""
import json, time, urllib.parse, urllib.request

UA={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
SEEDS=["{n} kundli","{n} horoscope","{n} astrology","{n} birth","{n} zodiac","{n} nakshatra","{n} manglik"]
ASTRO=("kundli","horoscope","astrolog","zodiac","nakshatra","birth chart","birth time",
       "birthday","manglik","numerolog","rashi","lagna","dasha","navamsa","sade sati","born")

def suggest(q):
    url=("https://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=in&q="
         +urllib.parse.quote(q))
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=10) as r:
            return json.loads(r.read().decode("utf-8","ignore"))[1]
    except Exception:
        return []

d=json.load(open("data.json"))
ALIAS={"Narendra Modi":"narendra modi","Virat Kohli":"virat kohli","Amitabh Bachchan":"amitabh bachchan",
"Shah Rukh Khan":"shah rukh khan","MS Dhoni":"ms dhoni","Aishwarya Rai Bachchan":"aishwarya rai",
"Salman Khan":"salman khan","Sachin Tendulkar":"sachin tendulkar","Mukesh Ambani":"mukesh ambani",
"Dharmendra":"dharmendra","Rohit Sharma":"rohit sharma","Katrina Kaif":"katrina kaif",
"Deepika Padukone":"deepika padukone","Kareena Kapoor Khan":"kareena kapoor","Rahul Gandhi":"rahul gandhi",
"Smriti Mandhana":"smriti mandhana","Rashmika Mandanna":"rashmika mandanna","Alia Bhatt":"alia bhatt",
"Yogi Adityanath":"yogi adityanath","Anushka Sharma":"anushka sharma",
"Vaibhav Sooryavanshi":"vaibhav suryavanshi","Hardik Pandya":"hardik pandya",
"Yuvraj Singh":"yuvraj singh","Ravi Kishan":"ravi kishan"}

out={}
for r in d:
    n=r["name"]; alias=ALIAS[n]
    hits=[]
    for s in SEEDS:
        for q in suggest(s.format(n=alias)):
            ql=q.lower()
            if any(a in ql for a in ASTRO) and ql not in [h.lower() for h in hits]:
                hits.append(q)
        time.sleep(0.35)
    out[n]=hits
    print(f"{n:26} {len(hits):3} queries   e.g. {hits[:3]}")
json.dump(out,open("_autosuggest_raw.json","w"),indent=1,ensure_ascii=False)
print("\nharvest complete:",sum(len(v) for v in out.values()),"total queries")
