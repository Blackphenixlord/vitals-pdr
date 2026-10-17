"""Missions: scripted runs of the whole system, each one logged.

The HUNCH 2026-27 requirement list asks teams to "Complete some basic
missions" for PDR and "basic and advanced missions" for CDR, with log entries
that record subsystem, element, status and timestamp. This is that.

    python -m vitals missions                 basic missions - no model needed
    python -m vitals missions --advanced      also the missions that need ollama
    python -m vitals missions --log out.jsonl write the log somewhere specific

BASIC MISSIONS (offline, deterministic - they run anywhere, every time)
    B1  KB        the knowledge base loads and validates
    B2  SENSORS   the sensor layer reports honestly: nothing connected, no
                  invented readings, and the model is told not to assume
    B3  SCOPE     "hi" and "what's the weather" are NOT treated as medical;
                  a symptom IS
    B4  ENGINE    every saved demo case in cases/ produces the expected top
                  condition and the expected escalation decision
    B5  EXTRACT   the crewmember's own words for each demo case, run through
                  the offline keyword extractor and then the engine, still
                  reach the expected answer (text in, right answer out)
    B6  CASES     one case makes the full trip: astronaut -> ground crew ->
                  doctor -> ground crew -> astronaut, and the doctor never
                  sees what the ground crew hid

ADVANCED MISSIONS (need ollama and a model - the main LLM path)
    A1  REASON    ollama is reachable and the demo model is present
    A2  REASON    every prompt in the bank that MUST escalate does escalate,
                  through the exact pipeline `vitals ask` uses

Missed escalations are the number that matters most, so A2 is the advanced
mission, not the hit rate. `vitals bench` reports the hit rate.
"""

from __future__ import annotations

import glob
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from . import sensors
from .engine import diagnose
from .extract import KeywordExtractor
from .knowledge_base import KnowledgeBaseError, load_knowledge_base
from .missionlog import MissionLog
from .scope import classify

REPO_ROOT = Path(__file__).resolve().parents[2]
CASES_DIR = REPO_ROOT / "cases"

NOT_MEDICAL_PROBES = ("hi", "thanks!", "what's the weather like today")
MEDICAL_PROBE = "my head hurts and I feel sick to my stomach"


@dataclass
class MissionReport:
    log: MissionLog
    results: dict[str, list[str]] = field(default_factory=dict)   # mission -> statuses

    def add(self, mission: str, status: str) -> None:
        self.results.setdefault(mission, []).append(status)

    def mission_status(self, mission: str) -> str:
        statuses = self.results.get(mission, [])
        if not statuses:
            return "SKIP"
        if "FAIL" in statuses:
            return "FAIL"
        if all(s in ("SKIP", "NOT_CONNECTED") for s in statuses):
            return "SKIP"
        return "PASS"

    @property
    def failed(self) -> bool:
        return any(self.mission_status(m) == "FAIL" for m in self.results)


def _check(report: MissionReport, mission: str, subsystem: str, element: str,
           passed: bool, detail: str) -> bool:
    status = "PASS" if passed else "FAIL"
    report.log.record(subsystem, element, status, f"[{mission}] {detail}")
    report.add(mission, status)
    return passed


# --- basic ----------------------------------------------------------------


def mission_kb(report: MissionReport, kb_path=None):
    try:
        knowledge_base = load_knowledge_base(kb_path)
    except KnowledgeBaseError as exc:
        _check(report, "B1", "KB", "kb/", False, f"knowledge base invalid: {exc}")
        return None
    _check(report, "B1", "KB", "kb/", True,
           f"{len(knowledge_base.conditions)} conditions, "
           f"{len(knowledge_base.findings)} findings, schema valid")
    return knowledge_base


def mission_sensors(report: MissionReport) -> None:
    readings = sensors.read_all()
    line = sensors.status()
    context = sensors.as_context(readings)
    if not sensors.REGISTERED:
        report.log.record("SENSORS", "sensors.py", "NOT_CONNECTED", f"[B2] {line}")
    _check(report, "B2", "SENSORS", "read_all", sensors.REGISTERED or not readings,
           f"{len(readings)} readings returned - none invented")
    _check(report, "B2", "SENSORS", "as_context",
           bool(readings) or "Do NOT assume any vital sign is normal" in context,
           "model is told no instruments are connected and not to assume normal vitals")


def mission_scope(report: MissionReport, knowledge_base) -> None:
    for probe in NOT_MEDICAL_PROBES:
        kind = classify(probe, knowledge_base).kind
        _check(report, "B3", "SCOPE", f'"{probe}"', kind != "medical",
               f"classified as {kind} - never reaches the model")
    kind = classify(MEDICAL_PROBE, knowledge_base).kind
    _check(report, "B3", "SCOPE", f'"{MEDICAL_PROBE}"', kind == "medical",
           f"classified as {kind}")


def _demo_cases(cases_dir: Path) -> list[tuple[str, dict[str, Any]]]:
    out = []
    for path in sorted(glob.glob(os.path.join(cases_dir, "*.yaml"))):
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        if raw.get("expect_top"):
            out.append((Path(path).stem, raw))
    return out


def mission_engine(report: MissionReport, knowledge_base, cases_dir: Path) -> None:
    for name, case in _demo_cases(cases_dir):
        result = diagnose(knowledge_base, case.get("observations") or {})
        top = result.top.id if result.top else "nothing"
        ok = top == case["expect_top"]
        detail = f"top = {top} (expected {case['expect_top']})"
        if "expect_escalate" in case:
            ok = ok and result.escalate == case["expect_escalate"]
            detail += f", escalate = {result.escalate} (expected {case['expect_escalate']})"
        _check(report, "B4", "ENGINE", f"case:{name}", ok, detail)


def mission_extract(report: MissionReport, knowledge_base, cases_dir: Path) -> None:
    extractor = KeywordExtractor()
    for name, case in _demo_cases(cases_dir):
        narrative = (case.get("narrative") or "").strip()
        if not narrative:
            continue
        observations = extractor.extract(narrative, knowledge_base)
        result = diagnose(knowledge_base, observations)
        top = result.top.id if result.top else "nothing"
        ok = top == case["expect_top"]
        if case.get("expect_escalate"):
            ok = ok and result.escalate
        _check(report, "B5", "EXTRACT", f"case:{name}", ok,
               f"{len(observations)} findings read from the text; top = {top} "
               f"(expected {case['expect_top']}), escalate = {result.escalate}")


def mission_case_flow(report: MissionReport) -> None:
    from .cases import CaseStore, RELEASED

    store = CaseStore(None)
    answer = {"scope": "medical", "escalate": True,
              "escalation": {"level": "urgent"},
              "differential": [{"id": "renal_stone", "name": "Renal Stone",
                                "urgency": "urgent", "confidence": "high"}]}
    case = store.record_turn(None, crew={"name": "Mission Test", "profile": {"Age": "41 years"}},
                             owner="mission-test", text="side pain in waves",
                             complaint="side pain in waves", answer=answer)
    _check(report, "B6", "CASES", "astronaut:record_turn", bool(case.get("id")),
           f"case {case.get('id')} opened")

    hide = ["name", "profile:Age"]
    store.send_to_doctor(case["id"], hide, "please review", "Ground Test")
    packet = str(store.packet(case["id"])["content"])
    leaked = [value for value in ("Mission Test", "41 years") if value in packet]
    _check(report, "B6", "CASES", "ground:send_to_doctor", not leaked,
           f"redacted packet built on the server; withheld {', '.join(hide)}; "
           f"{'LEAKED ' + ', '.join(leaked) if leaked else 'none of it reached the doctor'}")

    store.review(case["id"], "agree", "", "Doctor Test")
    final = store.release(case["id"], "Doctor agrees. Drink water, rest, report changes.",
                          "Ground Test")
    _check(report, "B6", "CASES", "ground:release", final["status"] == RELEASED,
           f"status = {final['status']}")
    notes = store.notes_for("mission-test")
    _check(report, "B6", "CASES", "astronaut:notes", len(notes) == 1,
           f"{len(notes)} released doctor note visible to the crewmember")


# --- advanced -------------------------------------------------------------


def mission_model_present(report: MissionReport, model: str) -> bool:
    from .ollama_client import OLLAMA_HOST, list_models

    try:
        models = list_models(OLLAMA_HOST)
    except Exception as exc:  # noqa: BLE001 - any failure here means "not available"
        report.log.record("REASON", "ollama", "SKIP", f"[A1] not reachable: {exc}")
        report.add("A1", "SKIP")
        return False
    present = any(m == model or m == f"{model}:latest" or m.split(":")[0] == model
                  for m in models)
    _check(report, "A1", "REASON", f"model:{model}", present,
           f"{'present' if present else 'missing'} on {OLLAMA_HOST}; "
           f"{len(models)} model(s) installed")
    return present


def mission_escalations(report: MissionReport, knowledge_base, model: str) -> None:
    from .bench import load_prompts, run_one

    must_escalate = [p for p in load_prompts() if p.get("escalate")]
    for prompt in must_escalate:
        outcome = run_one(knowledge_base, prompt, model=model)
        if outcome.error:
            report.log.record("REASON", f"prompt:{prompt['id']}", "SKIP",
                              f"[A2] {outcome.error.splitlines()[0]}")
            report.add("A2", "SKIP")
            continue
        _check(report, "A2", "REASON", f"prompt:{prompt['id']}", outcome.got_escalate,
               f"escalated = {outcome.got_escalate}; top = {outcome.got} "
               f"(expected {outcome.expect}); {outcome.elapsed}s on {model}")


# --- the run --------------------------------------------------------------


def run_missions(*, kb_path=None, advanced: bool = False, model: str = "llama3.2",
                 log_path: Optional[Path] = None, cases_dir: Path = CASES_DIR) -> MissionReport:
    report = MissionReport(MissionLog(log_path))
    started = time.time()
    report.log.record("MISSION", "run", "INFO",
                      f"start: basic{' + advanced' if advanced else ''} missions")

    knowledge_base = mission_kb(report, kb_path)
    mission_sensors(report)
    if knowledge_base is not None:
        mission_scope(report, knowledge_base)
        mission_engine(report, knowledge_base, cases_dir)
        mission_extract(report, knowledge_base, cases_dir)
    mission_case_flow(report)

    if advanced and knowledge_base is not None:
        if mission_model_present(report, model):
            mission_escalations(report, knowledge_base, model)

    verdicts = ", ".join(f"{m} {report.mission_status(m)}" for m in sorted(report.results))
    report.log.record("MISSION", "run", "FAIL" if report.failed else "OK",
                      f"done in {time.time() - started:.1f}s: {verdicts}")
    return report
