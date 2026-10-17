# Constraints and requirements

Every requirement has an ID, where it came from, how we prove it, and where it stands today.
Source key: **NB** = NASA HUNCH project brief/PDF · **T** = team decision · **UI** = `UI_ACCEPTANCE_CRITERIA` (Cruz).
Mentor Michael Hayes' requirements document has not arrived yet — this table will be revised when it does.

## Constraints (things we don't get to choose)

| ID | Constraint | Source |
|---|---|---|
| C1 | Communication delay 4–40 min; blackouts up to 2 weeks — **must work fully offline** | NB |
| C2 | No physician on board; user is non-medical, possibly stressed | NB |
| C3 | Limited computing power — target is a **Jetson Orin Nano 8 GB** | NB, T |
| C4 | Very little in-flight medical data exists — **no dataset to train a classifier on** | Research 1 |
| C5 | Sensitive health data — privacy is a requirement, not a feature | NB |
| C6 | Small screens, gloves, bad lighting | UI |
| C7 | Three students, one school year, school-funded parts (~$250–300 order pending) | T |

## Functional requirements

| ID | The system shall… | Source | Verified by | Status |
|---|---|---|---|---|
| F1 | accept a complaint in the crewmember's own words | NB | B5 mission, prompt bank | ✅ |
| F2 | return a ranked list of possible conditions with the reasoning for each | NB | `vitals ask`, bench | ✅ |
| F3 | name **only** conditions in the knowledge base (no invented conditions) | T | `test_reason.py` | ✅ |
| F4 | show a source for every condition, looked up from the KB — the model never writes a citation | T | `test_reason.py`, UI 2.3 | ✅ |
| F5 | escalate urgent/emergency conditions, even if the model forgets to | NB | A2 mission, bench "missed escalations" | 🟡 18/19 on 17 Oct — misses pain-only bends after EVA |
| F6 | ask one useful follow-up question at a time and never repeat one | NB, UI 4 | UI test, `test_reason.py` | ✅ |
| F7 | let the crewmember correct something it misunderstood | UI 5 | `test_server.py` corrections test | ✅ |
| F8 | say "nothing in the knowledge base fits" instead of guessing | T | bench refusal rate | 🔴 weakest area (0–1 of 7) |
| F9 | reply plainly to non-medical messages without calling the model | T | B3 mission | ✅ |
| F10 | require a PIN login; enforce roles on the **server** | NB | `test_accounts.py`, `test_server.py` | ✅ |
| F11 | offer an emergency button that skips the PIN | T | `test_server.py` | ✅ |
| F12 | save every medical answer as a case | T | B6 mission, `test_cases.py` | ✅ |
| F12b | ground crew screen: review cases, redact, send to a doctor; doctor screen: agree / disagree / own read; ground releases the reply to the astronaut | T | — | 🔵 planned — `/ground`, `/doctor` show the plan |
| F13 | reserve slots for sensors (HR, SpO₂, BP, temp) and **never invent a reading** | T | B2 mission, `test_sensors.py` | ✅ slots, 🔴 hardware |
| F14 | log every event with subsystem, element, status and timestamp | HUNCH list | `test_missionlog.py` | ✅ |
| F15 | voice input | NB | — | 🔴 not started |

## Performance and quality requirements

| ID | Requirement | Target | Verified by | Status |
|---|---|---|---|---|
| P1 | Answer time on the Jetson | ≤ 15 s | timed run on the board | 🔴 not measured — board not flashed |
| P2 | Answer time on a desktop GPU | ≤ 10 s | bench timing | ✅ ~4 s (3B), ~8 s (8B) |
| P3 | Missed escalations on the prompt bank | **0** | `vitals bench`, mission A2 | 🟡 0 on the 33-prompt bank (26 Sep); **1 of 19** on the 60-prompt bank (17 Oct, llama3.2) |
| P4 | Hit rate on the prompt bank | ≥ 80% | `vitals bench` | 🟡 73% (3B) / 85% (8B) |
| P5 | Refusal rate ("nothing fits") | ≥ 70% | `vitals bench` | 🔴 0–14% |
| P6 | Same complaint → same answer | deterministic | temperature 0 | ✅ |
| Q1 | No percentages on the crew screen (our priors aren't defensible) | none shown | `test_server.py` | ✅ |
| Q2 | UI tap targets ≥ 44 px, contrast ≥ 4.5:1, usable at 800 px | UI 9 | Cruz's checklist | 🟡 |
| Q3 | UI is self-contained — no CDN, no internet | UI 7 | `test_server.py` | ✅ |
| Q4 | User testing with ≥ 5 people who didn't build it | UI 10 | test log | 🔴 |

## Out of scope for v1 (a choice, not an omission)

- **Behavioral health** — a scoring engine is the wrong tool and a wrong answer does real harm.
  Routed to a human.
- **Radiation** — it's dosimetry and long-term cancer risk, not a symptom you diagnose from a
  complaint. The bank has a prompt (`none_radiation`) that checks we refuse it.
- **Treatment dosing** — VITALS says what to do next and when to escalate; dosing stays with the
  flight surgeon.
