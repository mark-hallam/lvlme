# Demo workspace: everything here is made up

This is a complete, built workspace for a **fictional** person, Alex Example,
who wants a program, applied AI or policy role at one of three **made-up**
organisations: Acme AI, Globex Labs and Initech Robotics. The people, the
employer (Contoso Freight), the contacts, the job postings, the links and
every score are invented for the demo. Nothing here describes a real person or
a real company's hiring.

Open `report/index.html` to see the dashboard.

## The scored days are fictional too

To show the climb, the demo replays five weekly runs, from 4 October to
1 November 2026, each with the evidence, judgements and postings as they stood
that week (`examples/build_demo.py` does this with the real scripts). The
made-up story behind the movement:

| Day | Best fit | What changed |
|---|---|---|
| 4 Oct 2026 | 40 | Day 1, measured: no network mapped, little public proof. |
| 11 Oct 2026 | 44 | The network map found contacts at Acme AI and Globex Labs. |
| 18 Oct 2026 | 46 | A recorded talk made the public signal stronger. |
| 25 Oct 2026 | 55 | Initech Robotics' new fleet role (posted the week before) was judged: it fits Alex's warehouse background. A checked case study lifted proof of work. |
| 1 Nov 2026 | 57 | A tailored application for that role. |

`campaign/plan.json` gives each open action a target date and its effects, so
the dashboard can draw the expected and best-case paths to 31 January 2027.
`eval/ceilings.json` feeds the "Path to the top band" view. One Acme AI role
needs US citizenship and a clearance, so its judgement sets
`hard_eligibility_block`, and the projection keeps its eligibility at zero.

## Rebuild it

From the repository root:

```bash
python3 scripts/build_dashboard.py --workspace examples/demo-workspace
```

or rebuild every generated file from the hand-written inputs (offline):

```bash
python3 examples/build_demo.py
```

`config.json` sets `"fictional": true`, which is what lets this workspace live
inside the engine's repository. Your own workspace must live outside it.
