# Example of Figma + code for the functional diagram

The requirement: show a box on the functional diagram, what it looks like (Figma), and the code
that makes it work. Here: the **astronaut asks → VITALS answers** path, the centre of the diagram.

## Figma (Cruz)

> 🟡 **Cruz:** paste the Figma link and export three frames into `pdr/img/`:
> `figma_login.png`, `figma_astronaut_chat.png`, `figma_answer_card.png`.
> Note on the board: the Figma is the **idea**; the built screens follow it but not pixel for pixel.

| Figma frame | Built as | Route |
|---|---|---|
| Login (keypad, dots, emergency button) | `src/vitals/ui/login.html` | `/` |
| Astronaut chat + rail (Chats · Profile · Vitals · Supplies · Doctor notes — the last three marked planned) | `src/vitals/ui/astronaut.html` | `/astronaut` |
| Answer card (level first, conditions, what to do, sources, *Wrong?*) | `astronaut.html` render code | `/api/ask` |
| Ground crew queue (Needs action · With doctor · Released) | planned — `planned.html` says what it will do | `/ground` |
| Doctor packet (agree / disagree / own read) | planned — `planned.html` says what it will do | `/doctor` |

## Code for each box on the diagram

The whole REASON path is one function, `run_pipeline()` in `src/vitals/server.py` — the CLI's
`vitals ask` runs the same steps, so the screen can never drift from what was tested:

```python
# src/vitals/server.py - run_pipeline (trimmed)
latest_scope = classify(latest, knowledge_base) if latest else None          # SCOPE
if latest_scope is not None and not latest_scope.is_medical:
    answer = not_medical_answer(latest_scope, model)                          #  -> plain reply
else:
    observations = KeywordExtractor().extract(complaint, knowledge_base)      # EXTRACT
    observations.update(sensors.as_observations(sensors.read_all()))          # SENSORS (none yet)
    observations.update(clean_corrections(knowledge_base, corrections))       # crew "Wrong?" fixes
    retrieved = retrieve(knowledge_base, complaint, observations,             # RETRIEVAL
                         limit=RETRIEVAL_LIMIT)
    answer = ask(knowledge_base, complaint, retrieved,                        # REASON + ENGINE backstop
                 observations=observations, model=model)
```

Inside `ask()` (`src/vitals/reason.py`) are the checks that make the model safe to show:

| Rule | Where | Test that proves it |
|---|---|---|
| Can only name conditions it was given | `_validated_differential` | `test_model_cannot_name_a_condition_it_was_not_given` |
| Never writes a citation | sources looked up from `kb/` | `test_citations_come_from_the_kb_not_the_model` |
| Escalates even if the model forgets | `_escalation`, `_engine_backstop` | `test_escalation_is_added_when_the_model_forgets`, `test_engine_backstop_escalates_when_the_model_misses_the_bends` |
| Never asks something already answered | `_next_questions` | `test_never_asks_about_something_already_known` |
| The model never sees our invented numbers | `as_context()` | `test_context_does_not_leak_the_invented_numbers` |

And the screen side — the answer card leads with the escalation **word**, then color:

```text
astronaut.html  ->  POST /api/ask {complaint, corrections, latest, case_id}
                <-  {escalation: {level, conditions}, differential: [...], known: [...],
                     next_questions: [...], sources per condition, case_id}
```

## Try it

```bash
python -m vitals serve          # http://127.0.0.1:8000  - demo PINs are in accounts.example.json
python -m vitals ask "flight day 63, bad pain in my right side, comes in waves, blood in my urine" --verbose
```
