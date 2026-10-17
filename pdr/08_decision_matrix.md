# Decision matrix

Scores 1 (poor) – 5 (excellent). Weights come from the constraints: offline and safety are
non-negotiable, so they weigh most. **Team: re-score together and initial it — the numbers below
are the starting point, the reasoning column is what a judge will ask about.**

## Decision 1 — what makes the diagnosis?

| Criterion | Weight | A. Trained classifier | B. Rules engine | D. Local LLM alone | **E. Grounded LLM + rules backstop** |
|---|---|---|---|---|---|
| Works fully offline (C1) | 5 | 5 | 5 | 5 | **5** |
| Safety — never misses an escalation | 5 | 2 | 4 | 2 | **5** |
| Explains itself / shows sources | 4 | 1 | 5 | 2 | **5** |
| Understands how people actually talk | 4 | 3 | 2 | 5 | **4** |
| Possible with the data that exists (C4) | 4 | 1 | 4 | 4 | **4** |
| Runs on the Jetson Orin Nano (C3) | 3 | 5 | 5 | 3 | **3** |
| Can be tested and repeated | 3 | 3 | 5 | 2 | **5** |
| Buildable by 3 students this year | 2 | 2 | 4 | 5 | **3** |
| **Weighted total (max 150)** | | **83** | **127** | **104** | **132** |

How the totals are worked out: sum of weight × score, e.g.
E = 5·5 + 5·5 + 4·5 + 4·4 + 4·4 + 3·3 + 3·5 + 2·3 = 25+25+20+16+16+9+15+6 = **132**.
Showing the arithmetic on the board is part of the point.

**Why E wins:** it's the only option that is conversational *and* checkable. B is close and is kept
inside E as the cross-check and the escalation backstop — on the September benchmark that backstop
took missed escalations from 3 to 0.

## Decision 2 — which model on the Jetson?

| Criterion | Weight | llama3.2:1b | **llama3.2 (3B)** | llama3.1 (8B) |
|---|---|---|---|---|
| Fits 8 GB shared memory with headroom | 5 | 5 | **4** | 2 |
| Names the right condition (bench) | 4 | 1 (failed spot test) | **3** (73%) | 4 (85%) |
| Missed escalations (bench) | 5 | 3 (only via backstop) | **5** (0) | 5 (0) |
| Speed | 3 | 4 | **4** | 3 |
| **Weighted total (max 85)** | | **56** | **69** | **60** |

**Decision:** llama3.2 (3B) on the Orin Nano. Revisit 8B if an Orin NX is available, and re-bench
after the prompt bank grew to 60.

## Decision 3 — deployment

| Criterion | Weight | Laptop only | Copy on every screen | **Jetson server + 3 Pi screens** |
|---|---|---|---|---|
| Flight-like (NASA asked for embedded) | 4 | 1 | 3 | **5** |
| One source of truth for cases | 4 | 5 | 1 | **5** |
| Survives a screen rebooting | 3 | 2 | 4 | **5** |
| Cost / parts we have | 3 | 5 | 2 | **4** |
| **Weighted total (max 70)** | | **45** | **34** | **67** |
