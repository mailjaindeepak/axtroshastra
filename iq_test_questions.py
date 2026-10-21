"""IQ Test — question bank, classification tables, and interpretive text."""

# ── 20 questions: 4 categories × 5, difficulty 1→3 ──────────────────────

QUESTIONS = [
    # ── Pattern Recognition (5) ──────────────────────────────────────────
    {
        "id": 1, "category": "pattern_recognition", "difficulty": 1,
        "text": "What comes next in the sequence: 2, 4, 6, 8, ?",
        "options": ["9", "10", "12", "14"],
        "correct": 1,
    },
    {
        "id": 2, "category": "pattern_recognition", "difficulty": 1,
        "text": "What comes next in the sequence: 3, 6, 12, 24, ?",
        "options": ["36", "48", "30", "42"],
        "correct": 1,
    },
    {
        "id": 3, "category": "pattern_recognition", "difficulty": 2,
        "text": "What comes next in the sequence: 1, 1, 2, 3, 5, 8, ?",
        "options": ["10", "11", "13", "15"],
        "correct": 2,
    },
    {
        "id": 4, "category": "pattern_recognition", "difficulty": 2,
        "text": "What comes next in the sequence: 2, 6, 18, 54, ?",
        "options": ["108", "162", "148", "216"],
        "correct": 1,
    },
    {
        "id": 5, "category": "pattern_recognition", "difficulty": 3,
        "text": "What comes next in the sequence: 1, 4, 9, 16, 25, ?",
        "options": ["30", "35", "36", "49"],
        "correct": 2,
    },

    # ── Logical Reasoning (5) ────────────────────────────────────────────
    {
        "id": 6, "category": "logical_reasoning", "difficulty": 1,
        "text": "All cats are animals. Some animals are pets. Which must be true?",
        "options": [
            "All cats are pets",
            "Some pets are cats",
            "All cats are animals",
            "All animals are cats",
        ],
        "correct": 2,
    },
    {
        "id": 7, "category": "logical_reasoning", "difficulty": 1,
        "text": "If it rains, the ground gets wet. The ground is wet. What can you conclude?",
        "options": [
            "It definitely rained",
            "It might have rained",
            "It did not rain",
            "The ground is always wet",
        ],
        "correct": 1,
    },
    {
        "id": 8, "category": "logical_reasoning", "difficulty": 2,
        "text": "Ravi is taller than Sita. Sita is taller than Meena. Priya is taller than Ravi. Who is the shortest?",
        "options": ["Ravi", "Sita", "Meena", "Priya"],
        "correct": 2,
    },
    {
        "id": 9, "category": "logical_reasoning", "difficulty": 2,
        "text": "In a row of children, Amit is 7th from the left and 12th from the right. How many children are in the row?",
        "options": ["18", "19", "20", "17"],
        "correct": 0,
    },
    {
        "id": 10, "category": "logical_reasoning", "difficulty": 3,
        "text": "A is the father of B. C is the daughter of B. D is the brother of A. What is D to C?",
        "options": ["Uncle", "Grandfather", "Grand-uncle", "Father"],
        "correct": 2,
    },

    # ── Verbal Analogies (5) ─────────────────────────────────────────────
    {
        "id": 11, "category": "verbal_analogies", "difficulty": 1,
        "text": "Book is to Reading as Fork is to ?",
        "options": ["Cooking", "Eating", "Drawing", "Writing"],
        "correct": 1,
    },
    {
        "id": 12, "category": "verbal_analogies", "difficulty": 1,
        "text": "Eye is to See as Ear is to ?",
        "options": ["Smell", "Touch", "Hear", "Taste"],
        "correct": 2,
    },
    {
        "id": 13, "category": "verbal_analogies", "difficulty": 2,
        "text": "Painter is to Canvas as Writer is to ?",
        "options": ["Pen", "Paper", "Book", "Ink"],
        "correct": 1,
    },
    {
        "id": 14, "category": "verbal_analogies", "difficulty": 2,
        "text": "Thermometer is to Temperature as Speedometer is to ?",
        "options": ["Distance", "Velocity", "Time", "Fuel"],
        "correct": 1,
    },
    {
        "id": 15, "category": "verbal_analogies", "difficulty": 3,
        "text": "Marathon is to Stamina as Chess is to ?",
        "options": ["Speed", "Strength", "Strategy", "Luck"],
        "correct": 2,
    },

    # ── Odd One Out (5) ──────────────────────────────────────────────────
    {
        "id": 16, "category": "odd_one_out", "difficulty": 1,
        "text": "Which does not belong: Apple, Banana, Carrot, Mango?",
        "options": ["Apple", "Banana", "Carrot", "Mango"],
        "correct": 2,
    },
    {
        "id": 17, "category": "odd_one_out", "difficulty": 2,
        "text": "Which does not belong: Triangle, Square, Circle, Cube?",
        "options": ["Triangle", "Square", "Circle", "Cube"],
        "correct": 3,
    },
    {
        "id": 18, "category": "odd_one_out", "difficulty": 2,
        "text": "Which does not belong: 2, 3, 5, 9, 11?",
        "options": ["2", "3", "9", "11"],
        "correct": 2,
    },
    {
        "id": 19, "category": "odd_one_out", "difficulty": 3,
        "text": "Which does not belong: Mercury, Venus, Moon, Mars?",
        "options": ["Mercury", "Venus", "Moon", "Mars"],
        "correct": 2,
    },
    {
        "id": 20, "category": "odd_one_out", "difficulty": 3,
        "text": "Which does not belong: Keyboard, Mouse, Monitor, CPU?",
        "options": ["Keyboard", "Mouse", "Monitor", "CPU"],
        "correct": 3,
    },
]

TOTAL_QUESTIONS = len(QUESTIONS)
CATEGORY_ORDER = ["pattern_recognition", "logical_reasoning",
                   "verbal_analogies", "odd_one_out"]

CATEGORY_LABELS = {
    "pattern_recognition": "Pattern Recognition",
    "logical_reasoning":   "Logical Reasoning",
    "verbal_analogies":    "Verbal & Analogical Thinking",
    "odd_one_out":         "Classification Ability",
}

CATEGORY_COUNT = {cat: sum(1 for q in QUESTIONS if q["category"] == cat)
                  for cat in CATEGORY_ORDER}

# ── IQ score calibration table (raw_score → base_iq) ────────────────────
# Linear interpolation between these anchor points.
IQ_TABLE = [
    (0,  70),
    (3,  78),
    (5,  85),
    (7,  92),
    (9,  98),
    (10, 100),
    (11, 103),
    (12, 107),
    (13, 111),
    (14, 115),
    (15, 119),
    (16, 123),
    (17, 127),
    (18, 132),
    (19, 138),
    (20, 145),
]

# ── Classification bands ────────────────────────────────────────────────
CLASSIFICATION_MAP = [
    (130, "Exceptional"),
    (120, "Superior"),
    (110, "Above Average"),
    (90,  "Average"),
    (0,   "Below Average"),
]

# ── Category performance labels ─────────────────────────────────────────
PERFORMANCE_LABELS = [
    (100, "Exceptional"),
    (80,  "Strong"),
    (60,  "Moderate"),
    (0,   "Developing"),
]

# ── Per-category interpretive text for the full report ───────────────────
PROFILE_TEXT = {
    "pattern_recognition": {
        "Exceptional": (
            "Your pattern recognition ability is outstanding. You naturally "
            "spot trends, sequences, and hidden structures that others miss. "
            "This is a powerful asset in fields like data analysis, engineering, "
            "and strategic planning."
        ),
        "Strong": (
            "You have a solid ability to identify patterns and sequences. "
            "You can connect dots across information and anticipate what comes "
            "next, which serves you well in problem-solving and planning."
        ),
        "Moderate": (
            "Your pattern recognition is developing. With practice, you can "
            "strengthen your ability to spot sequences and trends. Try puzzles, "
            "number games, and visual pattern exercises to build this skill."
        ),
        "Developing": (
            "Pattern recognition is an area with room for growth. This skill "
            "can be trained effectively with regular practice. Start with simple "
            "number sequences and work your way up to more complex patterns."
        ),
    },
    "logical_reasoning": {
        "Exceptional": (
            "Your logical reasoning is razor-sharp. You excel at deductive "
            "thinking, processing conditional statements, and drawing sound "
            "conclusions from limited information. This is the hallmark of "
            "strong analytical minds."
        ),
        "Strong": (
            "You reason logically and clearly. You can follow chains of logic "
            "and arrive at sound conclusions. This ability supports good "
            "decision-making across all areas of life."
        ),
        "Moderate": (
            "Your logical reasoning is functional and can be sharpened further. "
            "Practice with logic puzzles, brain teasers, and structured "
            "argument analysis will help you think more precisely."
        ),
        "Developing": (
            "Logical reasoning is an area where focused practice can yield "
            "significant improvement. Try breaking complex problems into "
            "smaller steps and practising if-then reasoning exercises."
        ),
    },
    "verbal_analogies": {
        "Exceptional": (
            "Your verbal-analogical thinking is exceptional. You grasp "
            "relationships between concepts quickly and can map one domain's "
            "logic onto another with ease. This is closely tied to strong "
            "communication and creative problem-solving."
        ),
        "Strong": (
            "You have a good grasp of verbal relationships and analogies. "
            "You can see how concepts relate and transfer ideas across "
            "different contexts effectively."
        ),
        "Moderate": (
            "Your analogical thinking is developing. Building vocabulary "
            "and reading widely will strengthen your ability to see "
            "relationships between ideas and concepts."
        ),
        "Developing": (
            "Verbal analogies are a trainable skill. Reading more, playing "
            "word games, and actively looking for parallels between different "
            "subjects will help build this ability over time."
        ),
    },
    "odd_one_out": {
        "Exceptional": (
            "Your classification ability is outstanding. You can quickly "
            "identify what doesn't belong in a group, which reflects "
            "strong categorical thinking and attention to defining features. "
            "This skill is valuable in quality analysis and critical evaluation."
        ),
        "Strong": (
            "You have a solid ability to classify and categorize. You can "
            "identify exceptions and distinguish key features that define "
            "a group, which helps in organizing information and spotting errors."
        ),
        "Moderate": (
            "Your classification skills are developing. Practising "
            "categorization exercises and paying attention to what makes "
            "items similar or different will sharpen this ability."
        ),
        "Developing": (
            "Classification ability can be strengthened with practice. "
            "Try sorting exercises, grouping games, and actively asking "
            "'what makes this different?' when encountering new information."
        ),
    },
}

# ── Per-category recommendations ────────────────────────────────────────
RECOMMENDATION_MAP = {
    "pattern_recognition": {
        "strong": "Keep challenging yourself with advanced puzzles like Sudoku, nonograms, or coding challenges that involve recognizing data patterns.",
        "growth": "Spend 10 minutes daily on number sequence puzzles or pattern-matching games. Apps like Lumosity or simple Sudoku are good starting points.",
    },
    "logical_reasoning": {
        "strong": "Your deductive skills are an asset. Consider activities like debate, strategic board games, or learning formal logic to go even further.",
        "growth": "Practice breaking problems into if-then steps. Logic puzzle books and apps, or even learning basic programming, can sharpen this area quickly.",
    },
    "verbal_analogies": {
        "strong": "Your verbal-relational thinking is a strength. Reading across diverse subjects and explaining concepts to others will keep this sharp.",
        "growth": "Read more widely and play word-association games. When you learn something new, try to find an analogy to something you already know.",
    },
    "odd_one_out": {
        "strong": "Your eye for what doesn't belong is sharp. Apply it to real life: reviewing documents for errors, evaluating arguments, or quality checks.",
        "growth": "Practice sorting and categorizing things in daily life. When you see a group of items, ask yourself: what's the common thread, and what breaks it?",
    },
}

# ── Learning style mapping (top-2 categories → style) ───────────────────
LEARNING_STYLE_MAP = {
    ("pattern_recognition", "logical_reasoning"): {
        "name": "Analytical-Systematic Learner",
        "description": (
            "You learn best when information is structured, logical, and "
            "sequential. You naturally break complex problems into smaller "
            "parts and look for underlying rules and patterns."
        ),
        "tips": [
            "Use flowcharts and decision trees when studying complex topics.",
            "Organize notes into hierarchies and cause-effect chains.",
            "Look for the 'formula' or rule behind what you are learning.",
        ],
    },
    ("pattern_recognition", "verbal_analogies"): {
        "name": "Conceptual-Creative Learner",
        "description": (
            "You connect ideas across different domains and see parallels "
            "others miss. You learn best when you can relate new concepts "
            "to things you already understand."
        ),
        "tips": [
            "Use analogies and metaphors when studying new material.",
            "Create mind maps that link new ideas to existing knowledge.",
            "Teach what you learn to someone else using everyday comparisons.",
        ],
    },
    ("pattern_recognition", "odd_one_out"): {
        "name": "Detail-Oriented Investigator",
        "description": (
            "You notice what others overlook. You learn best when you can "
            "examine data closely, spot exceptions, and understand what "
            "makes something tick."
        ),
        "tips": [
            "Focus on case studies and real-world examples when learning.",
            "When reading, actively look for exceptions to stated rules.",
            "Use comparison tables to understand differences between concepts.",
        ],
    },
    ("logical_reasoning", "verbal_analogies"): {
        "name": "Strategic Communicator",
        "description": (
            "You combine clear thinking with strong relational insight. "
            "You learn best through discussion, debate, and explaining "
            "ideas in your own words."
        ),
        "tips": [
            "Study with a partner or group where you can argue and discuss.",
            "Write summaries in your own words after learning something new.",
            "Use the Socratic method: ask 'why?' repeatedly to deepen understanding.",
        ],
    },
    ("logical_reasoning", "odd_one_out"): {
        "name": "Critical Evaluator",
        "description": (
            "You are naturally sceptical in the best way. You learn best "
            "by questioning, testing, and verifying information before "
            "accepting it."
        ),
        "tips": [
            "When learning, ask: 'What is the evidence for this?'",
            "Use pro-and-con lists to evaluate arguments and claims.",
            "Look for counterexamples to deepen your understanding of rules.",
        ],
    },
    ("verbal_analogies", "odd_one_out"): {
        "name": "Relational-Categorical Thinker",
        "description": (
            "You learn best by organizing information into groups and "
            "understanding the relationships between them. You are strong "
            "at both seeing similarities and spotting differences."
        ),
        "tips": [
            "Use Venn diagrams and classification trees when studying.",
            "Group new information into categories as you encounter it.",
            "Compare and contrast different theories or viewpoints side by side.",
        ],
    },
}

DEFAULT_LEARNING_STYLE = {
    "name": "Balanced Learner",
    "description": (
        "You have a well-rounded cognitive profile with no single dominant "
        "style. You can adapt your learning approach to fit different "
        "situations, which is a versatile strength."
    ),
    "tips": [
        "Experiment with different study methods to find what works for each subject.",
        "Combine visual, logical, and verbal approaches for the best retention.",
        "Use variety to keep your learning engaging and effective.",
    ],
}

# ── Strength/growth card text ───────────────────────────────────────────
STRENGTH_CARDS = {
    "pattern_recognition": {
        "title": "Pattern Spotter",
        "body": "You see the hidden structure in data and events. Where others see noise, you find the signal.",
    },
    "logical_reasoning": {
        "title": "Clear Thinker",
        "body": "You reason through problems step by step and arrive at sound conclusions. Complexity does not faze you.",
    },
    "verbal_analogies": {
        "title": "Connector of Ideas",
        "body": "You map relationships between concepts and bridge different domains of knowledge with ease.",
    },
    "odd_one_out": {
        "title": "Sharp Classifier",
        "body": "You spot what does not belong. Your eye for exceptions and defining features is above the curve.",
    },
}

GROWTH_CARDS = {
    "pattern_recognition": {
        "title": "Pattern Recognition",
        "body": "With focused practice on sequences and visual patterns, this area can improve noticeably within weeks.",
    },
    "logical_reasoning": {
        "title": "Logical Reasoning",
        "body": "Structured practice with logic puzzles and step-by-step problem decomposition will sharpen this quickly.",
    },
    "verbal_analogies": {
        "title": "Verbal Thinking",
        "body": "Reading widely and playing word-relationship games will strengthen the connections you draw between ideas.",
    },
    "odd_one_out": {
        "title": "Classification Skills",
        "body": "Daily sorting and 'spot the difference' exercises will train your brain to see categories and exceptions faster.",
    },
}
