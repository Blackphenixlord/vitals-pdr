"""Is it a medical question at all?

The costly mistake here is calling a REAL complaint off-topic - so most of
these tests check that vague, oddly worded or half-medical messages still go
through. Calling an off-topic message medical only costs one model call.
"""

import json

import pytest

from vitals import load_knowledge_base
from vitals.reason import ask
from vitals.scope import GREETING, HELP, MEDICAL, OFF_TOPIC, THANKS, classify
from vitals.server import run_pipeline


@pytest.fixture(scope="module")
def kb():
    return load_knowledge_base()


@pytest.mark.parametrize("text", [
    "what's the weather like in houston today",
    "Can you help me fix the printer in Node 2? It keeps jamming.",
    "tell me a joke",
    "write me a poem about the moon",
    "how do I reset the router",
    "what's on the schedule for flight day 12",
    "can you paint a picture",
])
def test_not_medical_is_off_topic(kb, text):
    scope = classify(text, kb)
    assert scope.kind == OFF_TOPIC
    assert "health" in scope.message.lower()


@pytest.mark.parametrize("text", [
    "I have a headache.",
    "fd2. naseaus. head movement makes it worse. threw up.",
    "I've been feeling really low and disconnected from the crew for a couple weeks now.",
    "There was a solar particle event alert. Should I be worried about my radiation dose?",
    "my quantum flux capacitor feels misaligned",
    "my nose started bleeding",
    "i think i have shingles",
    "is ibuprofen ok to take",
    "something in my eye",
    "i'm dizzy",
    "hi, my ear hurts",
    "hey i cut my finger",
])
def test_anything_about_a_person_stays_medical(kb, text):
    """Vague, typo'd, behavioural, or opening with a greeting - still medical."""
    assert classify(text, kb).kind == MEDICAL


@pytest.mark.parametrize("text,kind", [
    ("hi", GREETING), ("Hello VITALS!", GREETING), ("good morning", GREETING),
    ("thanks", THANKS), ("thank you so much", THANKS),
    ("help", HELP), ("what can you do?", HELP),
])
def test_small_talk_gets_its_own_reply(kb, text, kind):
    scope = classify(text, kb)
    assert scope.kind == kind
    assert scope.message


def test_every_prompt_with_a_condition_is_medical(kb):
    """The whole prompt bank is the regression test: no real complaint may be
    turned away as off-topic."""
    from vitals.bench import load_prompts
    for prompt in load_prompts():
        if prompt.get("category") == "off_topic":
            assert classify(prompt["text"], kb).kind != MEDICAL, prompt["id"]
        else:
            assert classify(prompt["text"], kb).kind == MEDICAL, prompt["id"]


def test_off_topic_never_calls_the_model(kb, monkeypatch):
    """No model call at all - it answers even with ollama switched off."""
    def boom(*args, **kwargs):
        raise AssertionError("the model was called for an off-topic message")
    monkeypatch.setattr("vitals.reason.generate", boom)

    answer = ask(kb, "what's the weather like in houston", [], observations={})
    assert answer.scope == OFF_TOPIC
    assert answer.differential == []
    assert answer.escalate is False
    assert answer.message


def test_server_checks_the_newest_message_on_its_own(kb, monkeypatch):
    """Mid-chat "thanks" must not re-run the whole case through the model."""
    def boom(*args, **kwargs):
        raise AssertionError("the model was called for a thank-you")
    monkeypatch.setattr("vitals.reason.generate", boom)

    reply = run_pipeline(kb, "my ear hurts\nthanks", "llama3.2", latest="thanks")
    assert reply["ok"] is True
    assert reply["scope"] == THANKS
    assert reply["differential"] == []
    assert reply["escalate"] is False
    json.dumps(reply)        # the screen gets it as JSON


def test_medical_reply_says_it_is_medical(kb, monkeypatch):
    monkeypatch.setattr(
        "vitals.reason.generate",
        lambda *a, **k: json.dumps({"differential": [], "escalate": False,
                                    "escalation_reason": "", "next_findings": [],
                                    "uncertainty": ""}),
    )
    reply = run_pipeline(kb, "my ear hurts", "llama3.2", latest="my ear hurts")
    assert reply["scope"] == MEDICAL
    assert reply["message"] == ""
