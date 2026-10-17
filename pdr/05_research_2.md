# Research 2 — hardware, models and real numbers

Research 1 decided *what* VITALS has to know. Research 2 answered *what it runs on* and *how we'll
know if it works*.

## 1. The computer: NVIDIA Jetson Orin Nano Developer Kit (8 GB)

- 40 TOPS, 6-core Arm A78AE, 1024-core Ampere GPU, 8 GB shared memory.
- Runs Ollama in Docker on NVIDIA's Jetson image (`dustynv/ollama`, per NVIDIA's Jetson AI Lab
  guide) with the NVIDIA runtime — the stock image tends to land on the CPU.
- 8 GB is shared between CPU and GPU → **llama3.2 (3B)** fits comfortably; 8B is tight.
- Image tag must match the board's JetPack (`cat /etc/nv_tegra_release`).
- **Not run on the real board yet** — first job once it's flashed (see schedule).

## 2. Which language model? (measured, not guessed)

Same 33-prompt benchmark, Joshua's PC GPU, 26 Sep 2026. Raw output: [`docs/bench/`](../docs/bench/).

| Model | Named the right condition | Said "nothing fits" when right to | Missed escalations | Time per answer |
|---|---|---|---|---|
| llama3.2 (3B), before fixes | 19/26 (73%) | 1/7 | **3** | ~4 s |
| llama3.2 (3B), after fixes | 19/26 (73%) | 1/7 | **0** | ~4 s |
| llama3.1 (8B), after fixes | 22/26 (85%) | 0/7 | **0** | ~8 s |
| llama3.2:1b (spot test) | ranked back pain over a kidney stone and invented a symptom | — | escalated (backstop) | ~80 s CPU |

"Fixes" = the engine escalation backstop + phrasebook entries for DCS, dental and wounds. The
backstop is why missed escalations went from 3 to 0 while the hit rate didn't move.

**Takeaway:** 3B for the Orin Nano; 8B if we get an Orin NX. Never demo on 1B.
*(The bank has since grown to 60 prompts — re-run before PDR.)*

## 3. Real incidence numbers: NASA IMM CliFF baselines

NASA publishes the incidence its Integrated Medical Model uses for each condition, with the arithmetic.
Examples (full table + 50 sources: [`docs/DATA_incidence_sources.md`](../docs/DATA_incidence_sources.md)):

| Condition | Published | What we had invented |
|---|---|---|
| Space motion sickness | 71.3% of crew (419/588) | 35% |
| Back pain, adaptation | 48.8% of crew (425/871) | 40% |
| Kidney stone | 0.004 per person-year | 0.04 (10× too high) |
| Dental emergency | ~0.009 per person-year | 0.08 |

The model never sees these numbers — they only feed the backup engine. Swapping the invented
priors for these is on the schedule (Joaquin + team decide).

## 4. Sensors (for the vitals slots)

From the team's hardware thread (Sep 2026): target heart rate, SpO₂, blood pressure, temperature.

| Vital | Candidate | Status |
|---|---|---|
| HR + SpO₂ | MAX30102 pulse-ox module (~$7 each) | picked |
| Blood pressure | salvaged cuff pump + valve, HX710B pressure sensor (0–40 kPa ≈ 0–300 mmHg), MOSFET drive (IRLZ44N) | hardest; loads measured (pump 0.71 A, valve 0.08 A) |
| Temperature | contact vs non-contact | undecided |
| Respiration | R60ABD1 60 GHz radar | too expensive, reference only |

Until hardware is wired, `sensors.py` returns **nothing** and tells the model not to assume normal
vitals. A fake vital is worse than a missing one.
