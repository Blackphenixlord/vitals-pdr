# Brainstorming 2 — how should the system be used and deployed?

Brainstorming 1 picked the brain (grounded local LLM + rules backstop). Round 2 asked **who touches
it, on what screens, and how a doctor fits in when the link is delayed.**

## 2a. Who sees what?

| # | Idea | Pros | Cons | Result |
|---|---|---|---|---|
| 1 | One screen, astronaut only | Simplest | No human check on the AI; no doctor in the loop | Built first (27 Sep AUI) |
| 2 | Astronaut + doctor | Doctor can correct the AI | Doctor sees everything — privacy (C5); no one manages the link | Rejected |
| 3 | **Astronaut → Ground crew → Doctor → Ground → Astronaut** | Ground crew sees everything, decides what the doctor sees (redaction), verifies the doctor's reply before the crew gets it | Three UIs to build | **Chosen** — Sep whiteboard. Astronaut screen built; ground crew + doctor screens planned |

## 2b. Where does it run?

| # | Idea | Pros | Cons | Result |
|---|---|---|---|---|
| 1 | Laptop | Easy to demo | Not flight-like; not what NASA asked for (C3) | Dev only |
| 2 | Every screen runs its own copy | No single point of failure | 3× the model; cases split across devices | Rejected |
| 3 | **Jetson = the one server; three Raspberry Pis = screens only** | One model, one set of cases; a Pi can reboot and nothing is lost | Jetson is a single point of failure | **Chosen** (4 Oct); one installer for all four boards |

## 2c. How does the crewmember tell it what's wrong?

| # | Idea | Status |
|---|---|---|
| 1 | Chat in their own words | ✅ built |
| 2 | Guided question-by-question interview | ✅ `vitals interview` (CLI) |
| 3 | Tap the body diagram ("where does it hurt?") | idea — fits the NASA brief's opening question |
| 4 | Voice | 🔴 NASA brief asks for it — CDR candidate |
| 5 | Camera (facial pain/anxiety cues) | slot reserved; "Doctor notes" tab replaced the camera tab for now |

## 2d. How do we keep the AI honest on screen?

- Escalation **word + color** first, never color alone.
- **No percentages** — our priors aren't sourced well enough to show "99%".
- "What VITALS understood" list with a **Wrong?** button on each item.
- Every condition shows its **source link**, from the KB.

> 🟡 **Team:** add Cruz's paper/Figma sketches of the three screens here, dated.
