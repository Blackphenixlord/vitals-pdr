"""Is this a medical question at all? Decided BEFORE the model is called.

VITALS is a medical tool. When someone types "what's the weather in Houston"
or "can you fix the printer", the right answer is not a differential, and not
"nothing in the knowledge base fits" either - that reads like a medical
verdict. The right answer is "that's not something I do", in plain words.

WHY THIS IS CODE, NOT A LINE IN THE PROMPT
    1. It is deterministic. Same text, same answer, so it can be tested.
    2. It costs nothing. No model call, so "hi" answers instantly - even when
       ollama is off.
    3. It cannot be talked out of. A model told "only answer medical
       questions" will still write a poem if asked nicely enough.

IT LEANS HARD TOWARD "MEDICAL" ON PURPOSE
    Calling a real complaint off-topic is the dangerous mistake. Calling an
    off-topic message medical just costs one model call that returns nothing.
    So a message is only off-topic when ALL of these are true:
      - the extractor found no symptom in it, and
      - it contains no health word at all (body parts, feelings, pain, sleep,
        medicine, the names of every condition in the knowledge base).
    "I've been feeling really low" is medical. "My quantum flux capacitor
    feels misaligned" is medical too - "feels" is enough. That is fine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .extract import KeywordExtractor
from .knowledge_base import KnowledgeBase

MEDICAL = "medical"
OFF_TOPIC = "off_topic"
GREETING = "greeting"
THANKS = "thanks"
HELP = "help"

MESSAGES = {
    GREETING: (
        "Hi, I'm VITALS. Tell me what's wrong - what you feel, where it is, "
        "and when it started - and I'll help you work out what it could be."
    ),
    THANKS: (
        "You're welcome. If anything changes or gets worse, tell me right away."
    ),
    HELP: (
        "I'm VITALS, a medical assistant for the crew. Describe a symptom or an "
        "injury in your own words - what you feel, where, how bad, and since "
        "when. I'll list what it could be, what to do now, and whether to "
        "contact ground medical. I only handle health questions."
    ),
    OFF_TOPIC: (
        "That doesn't sound like a health question, so I can't help with it - "
        "VITALS only handles medical concerns. If you or a crewmate feel unwell "
        "or got hurt, describe what you feel, where, and since when."
    ),
}

_END = r"[\s!.,?]*$"
GREETING_PATTERN = re.compile(
    r"^(hi|hii+|hello|hey+|hiya|yo|sup|howdy|greetings|good (morning|afternoon|evening|night))"
    r"( there)?( vitals)?" + _END
)
THANKS_PATTERN = re.compile(
    r"^(thanks|thank you|thx|ty|ok|okay|k|cool|got it|great|perfect|awesome|nice|will do|understood)"
    r"( (so much|a lot|vitals|again))?" + _END
)
HELP_PATTERN = re.compile(
    r"^(help|what can you do|what do you do|who are you|what are you|how does this work"
    r"|how do (i|you) use (this|you|vitals))" + _END
)

# Word STEMS: a word counts if it STARTS with one of these. Only stems long
# enough not to hit ordinary words ("ear" would catch "earth", "pain" "paint").
HEALTH_STEMS = (
    # feeling and pain
    "hurt", "aching", "unwell", "injur", "wound", "bleed", "blood", "bruis",
    "swell", "swollen", "itch", "fever", "chill", "sweat", "dizz", "faint",
    "nause", "vomit", "puke", "cough", "sneez", "breath", "tired", "fatigue",
    "exhaust", "numb", "tingl", "cramp", "sprain", "blister", "infect",
    "allerg", "symptom", "diagnos", "sick", "migrain", "headach", "stomachach",
    "toothach", "earach", "backach",
    # body
    "nasal", "sinus", "throat", "mouth", "tongue", "tooth", "teeth", "chest",
    "heart", "lung", "stomach", "belly", "abdom", "bowel", "spine", "flank",
    "shoulder", "elbow", "wrist", "finger", "thumb", "ankle", "muscle", "joint",
    "kidney", "bladder", "urin", "diarr", "constipat", "nerve", "eyelid",
    "nostril", "forehead", "cheek",
    # care
    "medic", "doctor", "surgeon", "nurse", "health", "hospital", "clinic",
    "bandage", "ibuprofen", "tylenol", "aspirin", "antibiotic", "vaccin",
    "antacid", "inhaler", "prescri",
    # mind and sleep (behavioural health is routed to a human, but it IS health)
    "sleep", "insomni", "stress", "anxi", "panic", "depress", "lonel",
    "scared", "afraid", "worried", "overwhelm",
    # environment that can hurt a person
    "radiat", "smoke", "fumes", "toxic", "ammonia", "oxygen", "spacewalk",
    "decompress", "prebreath",
)

# Short words that only count as an EXACT match.
HEALTH_WORDS = {
    "feel", "feels", "feeling", "felt", "pain", "pains", "painful", "ache", "aches",
    "achy", "sore", "ill", "burn", "burns", "burned", "burnt", "rash", "temp",
    "weak", "cut", "cuts", "scratch", "lump", "bump", "twisted", "strain",
    "head", "eye", "eyes", "ear", "ears", "nose", "lip", "lips", "gum", "gums",
    "jaw", "face", "neck", "pulse", "gut", "back", "side", "arm", "arms", "hand",
    "hands", "hip", "hips", "leg", "legs", "knee", "knees", "foot", "feet", "toe",
    "toes", "skin", "bone", "bones", "pee", "peeing", "poop", "stool", "vision",
    "hearing", "body", "brain", "pill", "pills", "dose", "drug", "drugs", "meds",
    "kit", "treat", "sad", "mood", "low", "cry", "crying", "worry", "co2", "eva",
    "air", "pressure", "throw", "threw", "vertigo",
}

# Words that appear in condition names but say nothing about health.
_NAME_NOISE = {
    "space", "spaceflight", "flight", "and", "from", "with", "the", "for", "upper",
    "acute", "mild", "moderate", "elevated", "environmental", "adaptation",
    "associated", "secondary", "small", "large", "early", "late", "system",
    # aliases are written the way crew talk, so they carry everyday words
    "something", "common", "contact", "cabin", "food", "lost", "open", "loose",
    "landing", "internal", "middle", "media", "shift", "fluid", "leak", "filling",
    "attack", "post", "misalignment", "moisture", "impairment", "reaction",
    "visual", "severe", "irregular", "chemical", "exposure", "blocked", "motion",
    "lengthening", "elongation", "cuff", "rotator", "thermal", "shock", "swimmer",
}


@dataclass(frozen=True)
class Scope:
    """What kind of message this is, and what to say if it is not medical."""

    kind: str
    message: str = ""

    @property
    def is_medical(self) -> bool:
        return self.kind == MEDICAL


def classify(text: str, knowledge_base: KnowledgeBase) -> Scope:
    """Medical, or one of greeting / thanks / help / off_topic."""
    normalized = " ".join((text or "").lower().split())
    if not normalized:
        return Scope(OFF_TOPIC, MESSAGES[OFF_TOPIC])

    for kind, pattern in ((GREETING, GREETING_PATTERN), (THANKS, THANKS_PATTERN), (HELP, HELP_PATTERN)):
        if pattern.match(normalized):
            return Scope(kind, MESSAGES[kind])

    if _mentions_a_symptom(normalized, knowledge_base) or _has_health_word(normalized, knowledge_base):
        return Scope(MEDICAL)

    return Scope(OFF_TOPIC, MESSAGES[OFF_TOPIC])


def _mentions_a_symptom(text: str, knowledge_base: KnowledgeBase) -> bool:
    """Did the phrasebook find anything about the PERSON in it?

    Contextual findings (mission day, a cabin leak) do not count on their own:
    "what's on the schedule for flight day 12" is not a complaint.
    """
    found = KeywordExtractor().extract(text, knowledge_base)
    return any(
        value is not None and not knowledge_base.findings[finding_id].contextual
        for finding_id, value in found.items()
        if finding_id in knowledge_base.findings
    )


def _has_health_word(text: str, knowledge_base: KnowledgeBase) -> bool:
    words = re.findall(r"[a-z0-9]+", text)
    vocabulary = _knowledge_base_words(knowledge_base)
    return any(
        word in HEALTH_WORDS or word in vocabulary or word.startswith(HEALTH_STEMS)
        for word in words
    )


def _knowledge_base_words(knowledge_base: KnowledgeBase) -> set[str]:
    """Every distinctive word in a condition name or alias - "shingles",
    "conjunctivitis", "nosebleed" - so a new rule widens the net by itself."""
    words: set[str] = set()
    for condition in knowledge_base.conditions.values():
        for phrase in [condition.name, *condition.aka]:
            for word in re.findall(r"[a-z0-9]+", phrase.lower()):
                if len(word) >= 4 and word not in _NAME_NOISE:
                    words.add(word)
    return words


__all__ = ["Scope", "classify", "MESSAGES", "MEDICAL", "OFF_TOPIC", "GREETING", "THANKS", "HELP"]
