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

# ---- life-stage labels (form value -> display text) ----
STAGE_LABEL = {
    "10th": "10th grade — choosing a stream",
    "12th": "12th grade — choosing a degree/field",
    "college": "College/Undergrad — job vs postgrad",
    "postgrad": "Postgrad — business vs job",
}

# ---- field-specific notes, shown only for "college"/"postgrad" stages where
# the student has already committed to a field. Short, honest, connects the
# existing house-based direction to what it plausibly means for that field —
# does NOT overclaim ("you will succeed in X"), just names what the general
# indication tends to look like in that context. ----
FOLLOWTHROUGH_TEXT = {
    "exalted": "discipline comes easily to you when it matters — Saturn is exceptionally well-placed, "
               "and hard, sustained effort is genuinely one of your natural strengths, not a struggle.",
    "own": "you have real staying power — Saturn sits in a sign it governs, so consistent, unglamorous "
          "effort is something you're built for more than most.",
    "neutral": "follow-through isn't automatic, but it isn't fighting you either — a little structure "
              "(a fixed routine, a visible checklist) is usually enough to make it stick.",
    "debilitated": "this is what's actually holding you back, not talent or planets — comfort-seeking "
                  "quietly wins over the harder task unless you name the hard task each day, out loud.",
}

# ---- what-to-do advice, shown only when a factor scores "watch" (needs
# attention) — one concrete, doable action per factor, not a vague platitude ----
FACTOR_ADVICE = {
    "study": "Set ONE fixed daily study block — same time, same place — for the next two weeks, no "
            "exceptions. Discipline that's scheduled beats discipline that's willed. Once the habit is "
            "about 21 days old, this factor stops being a weakness.",
    "exam": "Protect your sleep and solitude in the final week before any exam, more than one more "
           "revision session. A calm, rested mind outperforms a crammed one on this placement specifically.",
    "highered": "Don't wait for higher-education opportunities to come to you — apply, ask, and follow "
               "up more than feels natural. This house rewards initiative more than it rewards waiting.",
    "career": "Get specific about the *kind* of role you want, on paper, this month. A vague direction "
             "underuses this placement; a named target doesn't.",
    "followthrough": "Each morning, before you open your phone, say out loud the one hard task you're "
                    "avoiding. Comfort-seeking wins by default — naming the task first removes its "
                    "biggest advantage: silence.",
}

FIELD_NOTE = {
    "Engineering": "For engineering, this house energy usually shows up as either strong "
        "execution ability or a tendency to over-engineer simple problems — worth noticing which one you lean toward.",
    "Medicine": "For medicine, this tends to translate into either strong diagnostic patience or "
        "burnout risk from carrying others' outcomes personally — both are real patterns worth watching for.",
    "Commerce/Finance": "For commerce and finance, this usually shows up as either sharp numerical "
        "instinct or a pull toward safe, conventional choices over genuinely better ones — worth questioning which is driving a decision.",
    "Law": "For law, this tends to show up as either strong argumentative clarity or a habit of "
        "over-arguing in situations that don't call for it — both are worth being aware of.",
    "Arts/Design": "For arts and design, this usually shows up as either a distinct creative voice or "
        "self-doubt about whether the work is 'serious enough' — the chart doesn't answer that, only you can.",
    "Science/Research": "For science and research, this tends to translate into either genuine depth "
        "of focus or getting stuck perfecting one problem too long — worth checking which is happening.",
    "Civil Services": "For civil services, this usually shows up as either steady, disciplined "
        "preparation or repeated near-misses from spreading effort too thin — the difference is usually a plan, not luck.",
    "Business": "For business and entrepreneurship, this tends to show up as either real risk-taking "
        "instinct or restlessness that abandons ideas before they're tested — both look similar from outside.",
    "Other": "The general direction above still applies — the specific field matters less than "
        "whether the daily habits underneath it are actually being followed.",
}
