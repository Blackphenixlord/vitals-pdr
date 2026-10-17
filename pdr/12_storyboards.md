# Storyboards

Three stories, each one runnable in the prototype today. Panel = one frame on the board.
(Cruz: these are the shot lists — draw or screenshot each panel.)

## Story 1 — "It comes in waves" (the main story)

Commander Rivera, flight day 63 on a Mars transit. Medical officer is asleep; ground is 18 minutes away.

| Panel | What happens | Screen |
|---|---|---|
| 1 | Rivera, doubled over, taps the astronaut screen and enters her PIN | Login keypad |
| 2 | Types: *"bad pain in my right side, 8 out of 10, comes in waves, goes toward my groin. blood when I pee"* | Chat |
| 3 | First thing on the answer card: **URGENT — contact the flight surgeon** (word + orange) | Answer card |
| 4 | Below it: Renal stone (kidney stone) — why: pain in waves, flank pain, blood in urine — with the NASA source link | Answer card |
| 5 | "What VITALS understood" list. She taps **Wrong?** on one item it misread; the answer updates | Understood list |
| 6 | One follow-up question at a time (never one she already answered) — she replies | Chat |
| 7 | *(planned)* Ground crew screen: the case appears under **Needs action**. They hide her name and send the packet | Ground UI |
| 8 | *(planned)* Doctor screen: sees the redacted packet only. Picks **Agree**, adds a note | Doctor UI |
| 9 | *(planned)* Ground verifies the reply and releases it. Rivera's **Doctor notes** tab lights up | AUI → Doctor notes |

Panels 1–6 run in the prototype today. Panels 7–9 are the plan — draw them as sketches, labelled *planned*.

*Prototype command:* `python -m vitals serve`, then the renal colic complaint from `cases/demo_renal_colic.yaml`.

## Story 2 — "Just my shoulder" (the safety story)

Flight engineer, two hours after a spacewalk: *"Came in off the EVA about two hours ago. My left shoulder has this deep boring ache… and there is a weird blotchy marbled rash on my forearm."*

| Panel | What happens |
|---|---|
| 1 | Sounds like a strain. A small model on its own said shoulder strain. |
| 2 | VITALS: **EMERGENCY — decompression sickness until proven otherwise.** The EVA in the first sentence is the whole diagnosis. |
| 3 | Even if the language model misses it, the rules engine escalates — the backstop can't be overridden. |

*Proof:* mission B4/B5 `case:demo_dcs_after_eva`, and `test_engine_backstop_escalates_when_the_model_misses_the_bends`.

## Story 3 — "Hi" and "what's the weather" (the honesty story)

| Panel | What happens |
|---|---|
| 1 | A new crewmember types *"hi"* → a plain greeting. The model is never called; nothing is diagnosed. |
| 2 | Opens the **Vitals** tab → *"Not connected"* on every slot. No fake heart rate. |
| 3 | Asks about a radiation dose → the right answer is *"not something I can diagnose — ask the ground"*. **Honest status:** today the model still tends to guess here; refusals are our weakest benchmark number and the first thing to fix after PDR. |

*Proof:* mission B2 (sensors), B3 (scope); prompt `none_radiation` in the bench tracks panel 3.

## Client storyboard — who uses it, where

```
 HABITAT                               |   GROUND (delayed link)
 ------------------------------------- | -----------------------------------------
 [Crewmember] --talks to--> [Pi 1 AUI] |   [Pi 2 Ground crew]   [Pi 3 Doctor]
                  |                    |        ^      |              ^   |
                  v                    |        |      +--redacted----+   |
            [Jetson: VITALS] <---------+--------+-----------verdict-------+
```
