# Video scripts

The PDR list wants two videos: a **4-minute video of the PDR prototype** and a **3-minute video of
the presentation**. Both get linked from the website. Record screen with OBS (free) at 1080p; record
voice separately on a phone in a quiet room if the laptop mic is bad.

Rule for both: **no student faces needed in product shots** (the brochure rule says pictures should not
include students — keep the prototype video the same way to be safe).

---

## Video 1 — Prototype demo (4:00)

| Time | Show | Say (roughly) |
|---|---|---|
| 0:00–0:20 | Title card: VITALS · Team TETHER · NASA HUNCH | "On Mars, the doctor is up to 40 minutes away. VITALS is the medical assistant that's already on board." |
| 0:20–0:40 | Terminal: `python -m vitals missions` scrolling, ending 6/6 PASS | "Before anything else — it runs, offline, and logs every check: subsystem, element, status, time." |
| 0:40–1:00 | Login screen: PIN keypad, then the red EMERGENCY button | "Each person has a PIN. In an emergency, anyone can skip it." |
| 1:00–2:00 | Astronaut screen: type the renal colic complaint. Answer card appears | Read the escalation word first. Point at the reasons and the NASA source link. "It can only name conditions we researched, and it never writes its own citations — we look them up." |
| 2:00–2:20 | Tap **Wrong?** on one understood item; answer updates | "If it misreads you, you fix it, and it re-thinks." |
| 2:20–2:50 | Type the post-EVA shoulder + rash complaint → EMERGENCY decompression sickness | "This one looks like a strain. It isn't. And if the AI ever misses it, our rules engine escalates anyway." |
| 2:50–3:10 | Vitals tab: "Not connected" everywhere | "No sensors are plugged in yet, so it shows nothing. A fake heart rate is worse than none." |
| 3:10–3:45 | Ground crew screen → hide name → send. Doctor screen → Agree. Ground → Release. Back to astronaut **Doctor notes** | "Ground crew decides what the doctor sees. The doctor's reply gets checked before the crew sees it." |
| 3:45–4:00 | Jetson + Pis photo/diagram, end card with QR | "All of it runs on one Jetson, three screens, no internet." |

Demo PINs: `accounts.example.json`. Use `docker compose up` or `python -m vitals serve`.

---

## Video 2 — Presentation (3:00)

Slides = the tri-fold sections. ~25 seconds each.

1. **Problem** (0:00) — No doctor on board, 4–40 minute delay, blackouts up to two weeks. A non-medical crewmember has to decide what to do.
2. **Research** (0:25) — Spaceflight changes medicine: congestion that isn't a cold, joint pain that's the bends. And there's almost no in-flight data — some conditions have never happened in flight.
3. **Why not just train an AI?** (0:50) — Nothing to train on. So: a local language model that reads only our cited knowledge base, plus a rules engine as a safety backstop. Decision matrix: 132 vs 127 vs 104 vs 83.
4. **How it works** (1:15) — Functional diagram, one sentence per box.
5. **Three screens** (1:40) — Astronaut, ground crew, doctor. Redaction happens on the server.
6. **Testing** (2:00) — 266 automated tests, logged missions, a benchmark that counts missed escalations first: 18 of 19 on our latest run — and we show the one it missed. Weakest point: saying "nothing fits".
7. **Next** (2:30) — Run on the real Jetson, wire the pulse-ox sensor, a medical reviewer for the rules, voice input. End with the QR code.

Each teammate takes at least one section on camera or voice — judges like hearing all three.
