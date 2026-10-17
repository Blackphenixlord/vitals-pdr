# VITALS — design-review documents

**Team TETHER · NASA HUNCH 2026–27 · Software & Technology Hardware Engineering plus Robotics**
**NASA project:** SFT 2025-26-27 Medical Diagnostic System with Machine Learning & Artificial Intelligence (From a non-Medical Person's Perspective)
**Team project:** VITALS

One file per item on the HUNCH 2026-27 PDR list
([Generic Schedule PDF](https://cdn.nasahunch.com/Generic_Schedule_1_7b74852edf.pdf)), in the order the list gives
them. The code in the rest of this repo is the working prototype: **the astronaut screen works; the ground crew
screen, doctor screen, sensors and the rest are shown in the app as planned** (see the main README).

Status key: ✅ ready · 🟡 drafted here, team must finish · 🔴 the team has to make it (a person, a camera, or a decision) · 🔵 planned for a later version

## The checklist

| # | PDR list item | Where | Status |
|---|---|---|---|
| — | **Header board:** school, name, team number, NASA project name, team project name, QR code (website) | [00_header_board.md](00_header_board.md) | 🟡 school/city/team # blanks |
| 1 | Problem statement | [01_problem_statement.md](01_problem_statement.md) | ✅ |
| 2 | Research 1 — critical effort | [02_research_1.md](02_research_1.md) | ✅ |
| 3 | Constraints — requirements | [03_constraints_requirements.md](03_constraints_requirements.md) | ✅ |
| 4 | Brainstorming 1 | [04_brainstorming_1.md](04_brainstorming_1.md) | 🟡 add the team's own sketches |
| 5 | Research 2 | [05_research_2.md](05_research_2.md) | ✅ |
| 6 | Brainstorming 2 | [06_brainstorming_2.md](06_brainstorming_2.md) | 🟡 add the team's own sketches |
| 7 | Functional diagram and/or conceptual diagrams of the **three best** brainstorming results | [07_functional_diagrams.md](07_functional_diagrams.md) | ✅ |
| 8 | Decision matrix | [08_decision_matrix.md](08_decision_matrix.md) | ✅ (team re-scores) |
| 9 | Example of Figma + code for the functional diagram | [09_figma_plus_code.md](09_figma_plus_code.md) | 🟡 paste Cruz's Figma link + screenshots |
| 10 | Next steps and schedule, weekly deliverables | [10_next_steps_schedule.md](10_next_steps_schedule.md) | ✅ |
| 11 | Preliminary test plan | [11_preliminary_test_plan.md](11_preliminary_test_plan.md) | ✅ |
| 12 | Client and/or project storyboards | [12_storyboards.md](12_storyboards.md) | ✅ |
| 13 | Website or Google Site | [website/](website/) | 🟡 host it, then make the QR |
| — | Marketing brochure (CDR list, but ready now) — tri-fold, front and back | [brochure/brochure.pdf](brochure/brochure.pdf) | 🟡 fill school / city, add QR codes, print |
| 14 | 4-minute video of the PDR prototype | [14_video_scripts.md](14_video_scripts.md) | 🔴 script ready, record it |
| 15 | 3-minute video of the presentation | [14_video_scripts.md](14_video_scripts.md) | 🔴 script ready, record it |
| 16 | Complete some basic missions | [15_missions_and_logs.md](15_missions_and_logs.md) · `python -m vitals missions` | ✅ basic 6/6 · advanced A2 18/19 |
| 17 | Log entries recording subsystem, element, current status, timestamp | [logs/](logs/) · `python -m vitals log` | ✅ |
| 18 | Team D.A.A.N. (engineering notebook) | [daan/](daan/) | 🔴 daily, by each person |
| — | 60% working prototype — what works, what doesn't | [13_prototype_status.md](13_prototype_status.md) | ✅ |

## Prove it in two commands

```bash
pip install -e ".[dev]"
python -m vitals missions          # the PDR basic missions - offline, ~1 second
python -m pytest -q                # 262 tests
```

With ollama running and a model pulled, `python -m vitals missions --advanced` adds the
missions that go through the language model.

## What is NOT in here, on purpose

- **Fake D.A.A.N. entries.** The notebook is a daily record by each person. Writing entries
  after the fact for days nobody wrote is exactly what a judge checks for. `daan/` has the
  official template and the dated git history as supporting evidence — not as entries.
- **Fake user-testing results.** The test plan says how Cruz runs it; the results get logged
  when real people do it.
- **Numbers we can't source.** Every figure in these files is either from a cited source or
  from a run of this code, and says which.
