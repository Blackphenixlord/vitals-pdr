# The 60% prototype — what works and what doesn't

PDR asks for a **60% working prototype** (HUNCH recommends aiming for 90%). This is an honest
breakdown, weighted by how much of the final system each part is. Every "works" line is proven by a
test or a logged mission you can run.

| Part | Weight | Done | What works now | What's left | Proof |
|---|---|---|---|---|---|
| Knowledge base | 15% | 85% | 35 cited conditions, 145 findings, schema-validated | Medical reviewer; swap in NASA IMM priors | `vitals validate`, mission B1 |
| Understanding the crewmember | 10% | 70% | Offline phrasebook, negation, crew corrections | Missed phrasings from user testing; voice | missions B3, B5 |
| Reasoning (local LLM, grounded) | 20% | 75% | Answers from KB pages only; can't invent conditions or citations; temperature 0 | Refusals ("nothing fits"); re-bench at 60 prompts | `test_reason.py`, `vitals bench` |
| Safety / escalation | 10% | 80% | Model + rules backstop; 18/19 must-escalate prompts escalated (17 Oct) | Pain-only bends after EVA — missed by model and backstop | mission A2, bench |
| Astronaut screen | 10% | 80% | PIN login, emergency button, chat, answer card, *Wrong?*, profile, vitals slots, doctor notes | User testing round 1; accessibility checks | `test_server.py` |
| Ground crew + doctor screens | 10% | 70% | Case queue, profile edits, redaction on the server, doctor verdicts, release | Run on real Pis; polish | mission B6, `test_cases.py` |
| Deployment (Jetson + 3 Pis) | 10% | 40% | Docker with the model baked in (verified offline); one installer for all boards | **Never run on the real Jetson** | `deploy/` |
| Sensors | 10% | 15% | Slots + contract; never invents a reading | Parts order; MAX30102 first | mission B2 |
| Logging / missions | 5% | 90% | Every event logged with subsystem, element, status, timestamp | Statistics from logs for CDR | `vitals missions`, `vitals log` |
| **Weighted total** | 100% | **~68%** | | | |

How it's worked out: 15·0.85 + 10·0.70 + 20·0.75 + 10·0.80 + 10·0.80 + 10·0.70 + 10·0.40 + 10·0.15 + 5·0.90
= 12.75 + 7 + 15 + 8 + 8 + 7 + 4 + 1.5 + 4.5 = **67.75 ≈ 68%** — past the 60% bar, short of the
recommended 90%. The two parts holding it back are hardware (Jetson run, sensors) — both
waiting on the board being flashed and the parts order.

## Demo setup for PDR (offline)

```bash
docker compose up               # model already inside the image - no internet needed
# or, on a laptop with ollama:
python -m vitals serve --no-open
python -m vitals missions       # show the logged missions passing, live
```

Bring: laptop (charged), the Jetson if it's running by then, printed demo PINs (from
`accounts.example.json`), the tri-fold, and a printed copy of the latest mission log.
