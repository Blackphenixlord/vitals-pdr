# Preliminary test plan

The NASA brief asks for a system that is "vigorously tested" with unit, integration, user acceptance,
performance and vignette testing. This plan maps each kind to something that exists or is scheduled.

## The numbers that matter (in priority order)

1. **Missed escalations — must be 0.** Naming the wrong condition is bad; failing to call for help is
   the one that hurts someone. `vitals bench` exits non-zero on any miss, even at 100% hits.
2. **Refusal rate** — of the prompts where the right answer is "nothing here fits", how many did it
   correctly refuse. A system with 100% hits and 0% refusals always names *something*.
3. **Hit rate** — named the right condition. Never quoted without #2.

## Test levels

| Level | What | How | Pass criteria | Status |
|---|---|---|---|---|
| Unit | Every module: KB loading, extraction, scoring, reasoning checks, accounts, cases, log | `python -m pytest -q` | all pass | ✅ 262 pass |
| Knowledge base | Schema, cross-references, every condition has a test prompt | `python -m vitals validate` + tests | KB VALID | ✅ |
| Integration — basic missions | B1–B6: KB, sensors, scope, 29 demo cases through the engine, 29 narratives through text→answer, astronaut cases saved (ground/doctor steps logged as planned) | `python -m vitals missions` | 6/6 PASS, logged | ✅ |
| Integration — advanced missions | A1 model present; A2 every must-escalate prompt escalates through the real LLM path | `python -m vitals missions --advanced` | 0 missed | 🟡 PC 17 Oct: 18/19 — `mimic_sprain_vs_dcs` missed |
| Vignette (benchmark) | 60 complaints written the way people talk: classic, mimics, phrasing, nothing-fits, off-topic | `python -m vitals bench` | P3 = 0, P4 ≥ 80%, P5 ≥ 70% | 🟡 Sep: 0 / 73–85% / 0–14% |
| Expert vignette | A clinician answers the same vignettes blind; compare | spreadsheet | agreement recorded | 🔴 needs a reviewer |
| User acceptance | ≥5 people who didn't build it; 3 symptoms × 5 natural phrasings; time to read the level (≤3 s) | `UI_ACCEPTANCE_CRITERIA.md` §10, log in `pdr/test_log/` | criteria 1–9 checked | 🔴 Cruz, week of Oct 26 |
| Performance | Time per answer, desktop and Jetson | bench timing, mission log | ≤10 s desktop, ≤15 s Jetson | 🟡 desktop ✅, Jetson not run |
| Offline | Network cable pulled; Docker with no internet route | manual + Docker test | answers, page loads, no CDN | ✅ verified 26 Sep (Docker) |
| Security | Wrong PIN, lockout, role checks, one crewmember can't write to another's case | `test_accounts.py`, `test_server.py`, `test_cases.py`, B6 | all pass | ✅ (redaction: planned with the ground crew screen) |
| Hardware | Each sensor vs a reference device (e.g. pulse-ox vs MAX30102) | Bland-Altman style table | within stated tolerance | 🔴 after parts arrive |

## How results are recorded

- Every mission and every server event writes a log line: **timestamp, subsystem, element, status**
  (`data/logs/*.jsonl`; `python -m vitals log`). Sample: [`logs/`](logs/).
- Every bench run is saved, dated and unedited, in `docs/bench/`.
- User testing: one row per attempt — date, tester (initials), symptom, exact phrasing, what VITALS
  said, missed? — in `pdr/test_log/user_testing.csv`.
- At CDR these logs become the "Test Results — Statistics based on Log" item.

## Known weaknesses going in (say them before a judge does)

- **One missed escalation (17 Oct, llama3.2):** *"Back from the EVA an hour ago and my elbow has a deep
  ache. I didn't hit it or twist it."* → VITALS said sprain; the right answer is decompression
  sickness. The backup engine scores pain-only bends below its alarm line, so the backstop didn't
  catch it either. Fix: DCS weights for `recent_decompression` + `joint_pain` (Joaquin), then re-run A2.

- Refusals are weak: both models nearly always guess.
- The extractor is a regex phrasebook — odd phrasings get missed (that's what user testing feeds).
- The priors and weights in the backup engine were estimated; NASA IMM numbers are collected but
  not swapped in yet. No percentage is ever shown to the crew because of this.
- Nothing has run on the real Jetson yet.
