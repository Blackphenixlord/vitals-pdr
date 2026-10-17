# Next steps and schedule — weekly deliverables

Official milestones (HUNCH Generic Schedule + nasahunch.com/fdr):

| Milestone | Date | Target |
|---|---|---|
| PDR — in person with NASA HUNCH, science-fair style | **~November 2026 — exact date not published; confirm with Michael Hayes** | 60–90% working prototype + tri-fold |
| CDR — NASA HUNCH selects national contenders | ~March 2027 | 90% prototype + tri-fold or laptop |
| FDR — Johnson Space Center (invitation only) | **May 4–6, 2027** | 100% prototype + USB |

Owners: **J** = Joshua · **Q** = Joaquin · **C** = Cruz · **All** = everyone.
Every week, everyone: a D.A.A.N. entry for each day worked.

## Before PDR (week by week)

| Week of | Deliverable | Owner | Done when |
|---|---|---|---|
| Oct 19 | Confirm PDR date, team number, registration (closes Nov 1) | J | email from Hayes / Ms. Odoms |
| Oct 19 | Re-run `vitals bench` on the 60-prompt bank, 3B and 8B; commit the dated output | J | file in `docs/bench/` |
| Oct 19 | Start D.A.A.N.; back-fill nothing | All | daily entries exist |
| Oct 19 | Fix the missed escalation: pain-only bends after EVA (DCS weights), re-run `vitals missions --advanced` | Q, J | A2 19/19 |
| Oct 19 | Host the website, generate the QR code | J | QR scans to the live site |
| Oct 26 | User testing round 1: 5 people, 3 symptoms × 5 phrasings (UI criteria §10) | C | `pdr/test_log/` filled in |
| Oct 26 | Every missed phrasing → `patterns.py` + a test | J, C | tests pass |
| Oct 26 | Review the weights and red flags on the 14 original conditions | Q | checklist signed in `KNOWLEDGE_BASE_FORMAT.md` |
| Oct 26 | Paste Figma frames + whiteboard photos into Brainstorming 1/2 and file 09 | C | images in `pdr/img/` |
| Nov 2 | Record the 4-min prototype video and 3-min presentation video | All | uploaded, linked from the site |
| Nov 2 | Print and build the tri-fold | All | board assembled |
| Nov 2 | Dry run: present to the class, collect questions | All | question list + answers |
| Nov 9 | **PDR** (if it falls here) — bring laptop running `vitals serve` offline | All | — |

## PDR → CDR (deliverables per month)

| Month | Deliverable | Owner |
|---|---|---|
| Nov | Flash the Jetson; first run on the real board; time an answer (P1 ≤ 15 s) | J |
| Nov | Fix refusals — say "nothing fits" (P5 ≥ 70%) | J, Q |
| Nov | Swap invented priors for NASA IMM numbers; re-bench | Q, J |
| Dec | Real medical reviewer (nurse/EMT/doctor) checks the rules — biggest credibility gap | All |
| Dec | MAX30102 heart rate + SpO₂ wired into `sensors.py` (after parts order is approved) | J + hardware teammate |
| Jan | Three Pis running the three screens from the Jetson; full case loop on real hardware | J, C |
| Jan | User testing round 2 on the Pis | C |
| Feb | Voice input (NASA brief); temperature sensor; blood pressure if feasible | J |
| Feb | Advanced missions on the Jetson, full test data + statistics from logs (CDR list) | J |
| Mar | CDR package: Research 3, Brainstorming 3, info-flow diagram, install instructions, brochure, new videos, testimonial | All |

## Open blockers

- Michael Hayes' requirements document (may change the output format).
- Parts order (~$250–300) — needs school approval.
- A real medical source to review the knowledge base.
