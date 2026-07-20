"""Content maps for the /padhai (student career & academic) report.
Pure data, no logic — mirrors jyotish_maps.py's structure.

DRAFT COPY NOTE FOR REVIEW: these lines are a first pass in the requested
motivating-but-honest voice. Brand voice/tone should get a review pass before
shipping, same as any other customer-facing text on this site.
"""

# ---- 4th-lord house placement (1-12): foundation / environment for study ----
STUDY_HOUSE = [
    "self-driven study habits — you learn best on your own terms, not by being pushed",
    "steady, comfort-seeking study style — a settled routine and a familiar desk matter more than you think",
    "restless, curious learner — short bursts of focused effort beat long forced sessions",
    "home is your real classroom — a calm, stable household directly lifts your results",
    "learning through creativity and self-expression — rote methods will always underserve you",
    "disciplined, detail-oriented study style — checklists and structure are your edge",
    "you study better with a partner or group — explaining things to others locks them in for you",
    "deep, research-minded learner — you go slow but you go deep, and depth compounds later",
    "philosophical, big-picture learner — you need the 'why' before the 'how'",
    "ambition-driven study habits — a clear goal (rank, exam, career) is what actually gets you working",
    "you thrive with peer groups and networks — study circles multiply your output",
    "solitary, reflective learner — you need real quiet to think; noisy environments cost you more than most",
]

# ---- 5th-lord house placement (1-12): intelligence & exam-success pattern ----
EXAM_HOUSE = [
    "sharp, self-reliant exam performance — you rise to the occasion when it's on you alone",
    "steady, methodical preparation pays off more than last-minute brilliance for you",
    "quick recall and quick writing — time-pressured exams actually suit your mind",
    "your exam performance mirrors your mental peace — a settled mind before the exam matters more than one more revision",
    "genuine intellectual spark — you do best in exams that reward original thinking, not memorisation",
    "careful, disciplined preparation — you are the person who benefits most from a study plan followed exactly",
    "you perform best when the stakes are shared — group study or a study partner sharpens your focus",
    "intense, come-from-behind exam energy — you may underperform in mocks and outperform in the real thing",
    "your exam luck genuinely improves with faith and preparation together — this is not superstition, it's a real pattern in your chart",
    "exam success tracks your ambition — when the goal feels personal, your results jump",
    "you gain from studying in groups or coaching environments — isolated prep underuses your potential",
    "quiet, deep-focus exam preparation — protect your sleep and solitude in the final stretch",
]

# ---- 9th-lord house placement (1-12): higher education, luck, guru-grace ----
HIGHERED_HOUSE = [
    "higher education fortune tied to your own initiative — scholarships and opportunities favour those who apply, not those who wait",
    "steady support from family for higher studies — the resources are there if you use them consistently",
    "higher learning through communication-heavy fields — writing, media, and language-based courses suit your fortune",
    "your higher-education luck is tied to emotional stability — a settled home life directly lifts your academic fortune",
    "creative and unconventional higher-study paths bring real luck — don't force yourself into a conventional track if it doesn't fit",
    "higher education gained through sustained effort, not shortcuts — competitive, service-oriented fields reward you specifically",
    "partnership and mentorship-driven fortune — the right teacher or guide changes your trajectory more than any single exam",
    "research and specialisation is where your real luck lies — depth, not breadth, is the winning path",
    "this is your strongest house for higher education and guru-grace — foreign study, publishing or advanced degrees are genuinely favoured",
    "career and higher education are tightly linked for you — the right course choice is really a career choice",
    "networks and communities open doors to higher study — cohort-based and alumni-linked opportunities favour you",
    "foreign or institutional higher education is favoured — the path may look unconventional but the fortune is real",
]

# ---- per-planet hardship framing, keyed to the weakest key-lord (motivating,
# honest, and correction-oriented — the discipline angle the student asked for)
HARDSHIP_LINE = {
    "Sun": "Authority and self-confidence are the correctable habit here — hesitation to claim credit for your own work "
           "quietly costs you marks and opportunities. The fix isn't talent, it's practice at speaking up.",
    "Moon": "Emotional steadiness before exams and deadlines is the correctable habit — your results genuinely swing "
           "with your mental state. Protecting your sleep and calm in the run-up matters as much as revision.",
    "Mars": "Impatience and rushed work are the correctable habit — your instinct to finish fast costs you careless "
           "errors. Slowing down deliberately in the last 20% of any task is your highest-leverage fix.",
    "Mercury": "Scattered focus is the correctable habit — you start strong and drift. A fixed daily study block, "
               "not motivation, is what actually closes this gap.",
    "Jupiter": "Over-optimism about 'there's still time' is the correctable habit — faith without a plan doesn't "
               "convert to results. Pair your natural optimism with an actual weekly schedule.",
    "Venus": "Comfort-seeking and procrastination are the correctable habit — an easier, more pleasant task quietly "
             "replaces the harder one that actually matters. Naming the one hard task each day fixes this.",
    "Saturn": "This is classic Saturn territory — delay, self-doubt, and a sense that things take longer than they "
              "should. The honest news: this is real, and it is also exactly the placement most associated with "
              "durable, hard-won success once the discipline is built. What you achieve under this influence "
              "tends to last.",
    "Rahu": "Restlessness and chasing the next shiny goal before finishing the current one is the correctable habit — "
            "pick one target and see it through past the point it stops feeling exciting.",
    "Ketu": "Detachment and a 'why does this even matter' feeling toward routine work is the correctable habit — "
            "anchoring daily effort to a concrete goal (not a vague one) counters this.",
    "_none": "No single placement stands out as the weak point right now — the more useful question is which "
             "habit, not which planet, is holding back your results.",
}
