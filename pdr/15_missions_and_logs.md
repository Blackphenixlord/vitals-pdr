# Missions and logs

The PDR list: *"Complete Some Basic Missions. Produce some log entries — must record subsystem,
element, current status, and timestamp."* (CDR adds advanced missions and statistics from the logs.)

## Run them

```bash
python -m vitals missions                     # basic missions, offline, about one second
python -m vitals missions --advanced          # + missions through the local LLM (needs ollama)
python -m vitals log                          # print the newest log as a table
python -m vitals log --subsystem ENGINE       # one subsystem
```

Logs are JSON Lines in `data/logs/` (one object per line). The running server also writes
`data/logs/server.jsonl`: startup, logins, every answer (level, how many conditions, how long — never
what the crewmember said), and every step of the case review loop.

## The log format

| Field | Meaning | Example |
|---|---|---|
| `timestamp` | UTC, ISO 8601, to the second | `2026-10-17T22:08:59Z` |
| `subsystem` | a box on the functional diagram | `ENGINE` |
| `element` | the specific thing inside it | `case:demo_renal_colic` |
| `status` | `OK` `PASS` `FAIL` `WARN` `SKIP` `NOT_CONNECTED` `INFO` | `PASS` |
| `detail` | plain English | `top = renal_stone (expected renal_stone)` |

## Basic missions (PDR)

| Mission | Subsystem | What it proves |
|---|---|---|
| B1 | KB | The knowledge base loads and passes its JSON schema |
| B2 | SENSORS | No sensor connected → it says so, invents nothing, and tells the model not to assume normal vitals |
| B3 | SCOPE | "hi", "thanks", "what's the weather" are not medical; a symptom is |
| B4 | ENGINE | All 29 saved demo cases give the expected top condition and escalation decision |
| B5 | EXTRACT | The same 29 cases, from the crewmember's own words → text in, right answer out |
| B6 | CASES | The astronaut's answers are saved as one case on the server, follow-ups join it, nobody else can write to it. The ground crew → doctor → astronaut steps are logged as **planned** (INFO), never as a pass |

## Advanced missions (started for PDR, required for CDR)

| Mission | Subsystem | What it proves |
|---|---|---|
| A1 | REASON | Ollama is reachable and the demo model is installed |
| A2 | REASON | Every benchmark prompt that must escalate does escalate through the real model path |

Planned for CDR: A3 run on the Jetson with timing; A4 sensor readings (once wired) flow into an
answer; A5 three Pis complete the case loop over the network.

## Sample logs in this folder

[`logs/`](logs/) holds real runs, unedited:
- `basic_missions_*.jsonl` — from the cloud build machine
- `missions_pc_2026-10-17.jsonl` — Joshua's PC with llama3.2: B1–B6 PASS, A1 PASS, **A2 18/19** —
  the miss is `mimic_sprain_vs_dcs` (pain-only bends after EVA). Left in as found: a log that only
  ever shows PASS isn't evidence of testing.

Print one: `python -m vitals log pdr/logs/<file>.jsonl`
