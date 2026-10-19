# Next steps and schedule — weekly deliverables

Official milestones (HUNCH Generic Schedule + nasahunch.com/fdr):

| Milestone | Date | Target |
|---|---|---|
| PDR — in person with NASA HUNCH, science-fair style | **Wednesday, October 21, 2026** | 60–90% working prototype + tri-fold |
| CDR — NASA HUNCH selects national contenders | ~March 2027 | 90% prototype + tri-fold or laptop |
| FDR — Johnson Space Center (invitation only) | **May 4–6, 2027** | 100% prototype + USB |

Owners: **J** = Joshua · **Q** = Joaquin · **C** = Cruz · **All** = everyone.
The D.A.A.N. is optional on the HUNCH list — skipped this round.

## Before PDR — 4 days (Sat Oct 17 → Wed Oct 21)

| Day | Deliverable | Owner | Done when |
|---|---|---|---|
| Sat 17 | Website + brochure built in Gamma; QR codes made; brainstorm boards; all docs | J (done with Claude) | ✅ in the repo |
| Sun 18 | Record the 4-min prototype video (script: `14_video_scripts.md`) | J | uploaded, link on the website |
| Sun 18 | Fix the missed escalation if time allows: pain-only bends after EVA (DCS weights) | Q, J | `vitals missions --advanced` A2 19/19 |
| Mon 19 | Record the 3-min presentation video — each person takes a section | All | uploaded, link on the website |
| Wed 21 | Team number is assigned at PDR; write it on the header blank (school number TX151 is already printed) | All | number on the board |
| Mon 19 | Print: tri-fold board panels, header strip with QR, brochures (double-sided) | C | printed |
| Tue 20 | Build the tri-fold; dry run the 3-minute talk; practice the live demo offline | All | one full run with no internet |
| Tue 20 | Charge laptop; `docker compose up` or `vitals serve` tested on the demo laptop | J | answer shows with the network off |
| **Wed 21** | **PDR** — laptop running VITALS offline, tri-fold, brochures, mission log printout | All | — |

Pushed to after PDR: user testing round 1 (Cruz), Joaquin's weight review, re-running the 60-prompt bench.

## PDR → CDR (deliverables per month)

| Month | Deliverable | Owner |
|---|---|---|
| Nov | Flash the Jetson; first run on the real board; time an answer (P1 ≤ 15 s) | J |
| Nov | Fix refusals — say "nothing fits" (P5 ≥ 70%) | J, Q |
| Nov | Swap invented priors for NASA IMM numbers; re-bench | Q, J |
| Dec | Real medical reviewer (nurse/EMT/doctor) checks the rules — biggest credibility gap | All |
| Dec | MAX30102 heart rate + SpO₂ wired into `sensors.py` (after parts order is approved) | J + hardware teammate |
| Dec | Build the ground crew screen (case list, profile edits, redaction, send to doctor) | J, C |
| Jan | Build the doctor screen + Doctor notes on the astronaut screen; full case loop | J, C |
| Jan | Three Pis running the three screens from the Jetson | J, C |
| Jan | User testing round 2 on the Pis | C |
| Feb | Voice input (NASA brief); temperature sensor; blood pressure if feasible | J |
| Feb | Advanced missions on the Jetson, full test data + statistics from logs (CDR list) | J |
| Mar | CDR package: Research 3, Brainstorming 3, info-flow diagram, install instructions, brochure, new videos, testimonial | All |

## Open blockers

- Michael Hayes' requirements document (may change the output format).
- Parts order (~$250–300) — needs school approval.
- A real medical source to review the knowledge base.
