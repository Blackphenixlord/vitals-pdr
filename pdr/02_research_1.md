# Research 1 — critical effort

Research 1 answered one question: **what medical problems actually happen in spaceflight, and how
do they behave differently from Earth?** Full notes with every source:
[`docs/RESEARCH_spaceflight_conditions.md`](../docs/RESEARCH_spaceflight_conditions.md).

## The finding that shaped the whole design

NASA's own risk-modelling papers say **in-flight medical event data is severely limited**. For
several serious conditions the recorded in-flight count is **zero** — kidney stones with colic are
modelled as a mission-threatening risk that *has not yet happened in flight*.

**Consequence:** there is nothing to *train* a diagnostic model on. That is why VITALS grounds a
pretrained language model in a cited knowledge base instead of training a classifier (see the
decision matrix). It is also the best answer to "why does this need to exist" — the crew has to
be ready for the first case, and there is no case history to learn from.

## What microgravity changes (examples encoded in the knowledge base)

| Condition | What's different in space | Why it matters for VITALS |
|---|---|---|
| Space motion sickness | Early-flight, triggered by head movement; resolves in days | Same symptoms on day 60 must **not** be called motion sickness |
| Fluid-shift congestion | Near-universal from day 1; looks like a cold | "Since I got here" + no fever ≠ infection |
| SANS (eye/brain) | Vision changes on long flights; headache alone is not enough | Needs ocular findings, not just a headache |
| Renal stone | Bone loss + dehydration raise risk | Back pain in waves + blood in urine = escalate |
| Jugular vein clot (VTE) | Found on ISS in crew with no symptoms | Rare, dangerous — must escalate on red flags |
| Decompression sickness | Every EVA is a decompression | Joint pain right after EVA must outrank a strain |
| Wounds | Blood floats instead of falling; closed vehicle | Infection risk higher than the same cut on Earth |

## Where the knowledge base comes from

- 35 conditions, each one a YAML file in `kb/conditions/` with its citations
  (`python -m vitals explain <id>` prints any rule with its sources).
- Incidence numbers from **NASA's Integrated Medical Model (IMM) CliFF baselines** — NASA's own
  flight-data-based rates (e.g. motion sickness 71.3% of crew, 419/588).
  Table: [`docs/DATA_incidence_sources.md`](../docs/DATA_incidence_sources.md).

## The NASA project brief, read against our design

From *Design and Prototype an AI/ML Medical Diagnosis System* (HUNCH project PDF):

| Brief says | VITALS answer |
|---|---|
| Start from "Where does it hurt?" | Free-text chat, one follow-up question at a time |
| User authentication, session management | PIN login, server-side roles, saved cases |
| Emergency alerts | Escalation banner first; engine backstop can't be overridden by the model |
| Knowledge base of medical information | 35 cited conditions, 145 findings, JSON-schema validated |
| NLP for keyboard/audio/video input | Keyboard now; voice and camera slots reserved (not faked) |
| "Can be built initially as an LLM" | Local LLM (Ollama) is the reasoner |
| Limited computing power, variable internet | Runs on a Jetson Orin Nano, fully offline, model baked into the image |
| Vigorously tested | 262 automated tests, 60-prompt benchmark, logged missions |
| Disease coverage incl. shingles, kidney stones, appendicitis, head trauma | All four are in the KB |

Sources: [HUNCH project page](https://nasahunch.com/projects/sft-2025-26-27-medical-diagnostic-system-with-machine-learning-artificial-intelligence-from-a-non-medical-persons-perspective--gphimvf8m8y7m9a6s30xuwl8) ·
[project PDF](https://cdn.nasahunch.com/Design_and_Prototype_an_AI_ML_Medical_Diagnosis_System_8cfe20930f.pdf)
