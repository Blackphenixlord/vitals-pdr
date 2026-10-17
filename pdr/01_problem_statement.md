# Problem statement

## The problem

On the ISS a flight surgeon is a radio call away. On the Moon the delay is seconds; on Mars it is
**4 to 40 minutes each way**, and there are communication blackouts that NASA plans for at
**up to two weeks** (NASA HUNCH project brief). A crew on a long mission will usually have **no
physician on board** — at best a crewmember with paramedic-level training.

When someone gets sick or hurt, the person helping them has to answer three questions fast:

1. **What could this be?**
2. **How serious is it — do we need the ground right now?**
3. **What do we do in the meantime?**

Earth telemedicine assumes a live link. Earth symptom checkers assume Earth: they don't know that
a stuffy nose on day 2 is the fluid shift, not a cold, or that joint pain right after a spacewalk is
decompression sickness until proven otherwise.

## Who it is for

A **non-medical crewmember** (NASA's framing: "from a non-medical person's perspective"), under
stress, possibly in gloves, on a small screen, with no internet. Second users: the **ground crew**
who review what the system said, and a **doctor** who reviews a redacted case when the link is up.

## Problem statement (board version)

> Crews on long-duration Moon and Mars missions will face medical problems with no doctor on board
> and a communication delay of up to 40 minutes. They need an onboard system that a non-medical
> crewmember can talk to in plain words, that works with no network connection, that knows
> spaceflight medicine, that says clearly when to call for help — and that shows where every
> answer came from.

## What success looks like at the end of the year

- A crewmember types (later: says) how they feel and gets a ranked list of what it might be, how
  urgent it is, what to do next, and the source for every rule.
- It **never misses an escalation** on the test bank — the number we care about most.
- It runs **completely offline** on a Jetson in the habitat, with three screens: astronaut,
  ground crew, doctor. *(Astronaut screen working now; the other two are planned.)*
- It is honest: no invented vital signs, no invented percentages, no invented citations.
