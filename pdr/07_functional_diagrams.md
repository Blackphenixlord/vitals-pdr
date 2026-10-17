# Functional diagrams — the three best options

The three strongest ideas from Brainstorming 1, drawn the same way so they can be compared.
(GitHub renders these diagrams; for the board, screenshot them or redraw in Figma.)

## Option B — rules engine only

```mermaid
flowchart LR
    A[Crewmember types<br/>how they feel] --> X[Extract findings<br/>phrasebook / regex]
    X --> S[Score every condition<br/>weighted evidence]
    S --> R[Rank + escalate<br/>if red flag]
    R --> O[Ranked list<br/>+ sources]
```

Explainable and instant, but it can't hold a conversation, and every unusual phrasing it can't
read is a miss.

## Option D — local language model only

```mermaid
flowchart LR
    A[Crewmember types<br/>how they feel] --> L[Local LLM<br/>on the Jetson]
    L --> O[Free-text answer]
```

Conversational and offline — and nothing stops it answering from Earth medicine, naming a
condition we never researched, or writing a citation that doesn't exist.

## Option E — grounded LLM with a rules backstop ✅ chosen

```mermaid
flowchart TD
    A[Crewmember message] --> SC{SCOPE<br/>is it medical?}
    SC -- no: hi / weather --> P[Plain reply<br/>model never called]
    SC -- yes --> X[EXTRACT<br/>findings from the words]
    CR[Crew corrections<br/>'Wrong?' buttons] --> X
    SE[SENSORS<br/>none connected - says so] --> X
    X --> RT[RETRIEVAL<br/>pick the relevant cited KB conditions]
    KB[(KNOWLEDGE BASE<br/>35 conditions, 145 findings<br/>every rule cited)] --> RT
    RT --> RS[REASON<br/>local LLM reads ONLY those pages<br/>temperature 0]
    RS --> V[CHECK the reply<br/>drop invented conditions<br/>look up sources from KB]
    X --> EN[ENGINE<br/>deterministic cross-check]
    EN -- escalates? --> ESC
    V --> ESC{Escalate?<br/>model OR engine}
    ESC --> OUT[Answer: level word + color,<br/>ranked conditions, why, what to do,<br/>next question, sources]
    OUT --> CS[(CASES<br/>saved on the Jetson)]
    OUT -.every step.-> LOG[(MISSION LOG<br/>subsystem · element · status · time)]
```

Each box is a **subsystem** in the mission log, and a file in `src/vitals/`:

| Subsystem | File | Job |
|---|---|---|
| SCOPE | `scope.py` | Not medical → plain reply, model never runs |
| EXTRACT | `extract.py`, `patterns.py` | Words → findings (offline phrasebook) |
| SENSORS | `sensors.py` | Measured vitals — currently none, and it says so |
| KB | `knowledge_base.py`, `kb/` | Load + schema-validate the cited rules |
| RETRIEVAL | `retrieval.py` | Choose which KB pages the model may read |
| REASON | `reason.py`, `ollama_client.py` | The local model answers; reply is validated |
| ENGINE | `engine.py`, `scoring.py` | Deterministic cross-check + escalation backstop |
| CASES | `cases.py` | Saves every answer as a case (redaction + doctor review loop: planned) |
| ACCOUNTS | `accounts.py` | PINs, roles, sessions |
| SERVER | `server.py` | HTTP shell — owns no medical logic |

## System / deployment diagram (info flow between the three screens) — planned

Today the Jetson and the astronaut screen (Pi 1) work; Pi 2 and Pi 3 are the plan.

```mermaid
flowchart LR
    subgraph Habitat
      J[Jetson Orin Nano<br/>VITALS server + Ollama + KB + cases + log]
      P1[Pi 1 · Astronaut UI · WORKING<br/>chat · profile · vitals slots]
    end
    subgraph Ground
      P2[Pi 2 · Ground crew UI · PLANNED<br/>every case, full detail<br/>edit profile · choose what to hide]
      P3[Pi 3 · Doctor UI · PLANNED<br/>redacted packet only<br/>agree / disagree / own read]
    end
    P1 -- 1. complaint --> J
    J -- 2. answer + escalation --> P1
    J -- 3. full case --> P2
    P2 -- 4. redacted packet --> J
    J -- 5. packet only --> P3
    P3 -- 6. verdict + note --> J
    J -- 7. doctor reply --> P2
    P2 -- 8. verified + released --> J
    J -- 9. doctor note --> P1
```

Planned rule: redaction happens **on the Jetson**, not in the browser, so a hidden field never leaves
the server and can't reach the doctor's Pi.

The three-screen flow is a **proof of concept** of how a delayed doctor review would work — the Pis
are on one local network here, not a real 20-minute link.
