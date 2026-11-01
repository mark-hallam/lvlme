# SWOT, then TOWS

A SWOT (strengths, weaknesses, opportunities, threats) grid describes the
position. A TOWS matrix (the same four letters, read the other way round)
turns that description into moves. This file says how to fill both, and how
the moves become plan actions.

Everything lives in `eval/swot.json` (see `schemas/swot.schema.json`), in two
scopes:

- `overall`: the whole campaign.
- `per_org`: one grid per target organisation id, for anything that is true
  of one organisation and not the others.

Update it after scoring (stage 7), when the run file shows what is strong and
what is missing.

## Step 1: SWOT

### Internal: strengths and weaknesses

About the person. Each item needs:

- `id`: `S1`, `S2` for strengths, `W1`, `W2` for weaknesses.
- `text`: one plain sentence.
- `dimension`: the one dimension (D1 to D7) it mainly affects.
- `evidence`: the evidence ids that back it. A strength with no evidence is
  not a strength yet; it is a "verify to unlock" question.
- `orgs` and `families` (optional): `"all"` or a list, to say which roles it
  moves.

Rules:

- A strength is something that scores 3 or more on its dimension for at
  least some roles. A weakness scores 2 or less where it matters.
- Be specific. "Strong communicator" is not a strength. "Published a case
  study read by 4,000 people (E07)" is.
- Name weaknesses plainly. They are where the campaign earns its keep.
- The dashboard counts how many of the top roles each item moves: for a
  strength, how many score 3 or more on its dimension; for a weakness, how
  many score 2 or less.

### External: opportunities and threats

About the market. Each item needs:

- `id`: `O1`, `O2` for opportunities, `T1`, `T2` for threats.
- `text`: one plain sentence.
- `source`: where it came from: a workspace file (for example
  `market/roles/latest.json`), a posting id, or a web address.
- `dimension` and `orgs` (optional), and `seen_on` (optional date).

Good sources: open roles in the person's region, new teams or offices, partner
programmes, events, hiring velocity (new and closed roles between snapshots),
eligibility rules, hiring freezes, and the likely competing applicant pool.

Rules:

- Opportunities and threats are facts about the world, with a source. "AI is
  booming" is not one. "Acme AI posted 3 new program roles in Sydney this month
  (market/roles/snapshots)" is.
- Never invent market facts. If you are not sure, leave it out, or add a
  research action to the plan.

## Step 2: TOWS strategies

A strategy combines one internal item with one external item. There are four
types:

| Type | Meaning | Uses at least one | Question to ask |
|---|---|---|---|
| SO | Use a strength to seize an opportunity | S and O | Which strength lets the person grab this opening first? |
| ST | Use a strength to blunt a threat | S and T | Which strength makes this threat matter less? |
| WO | Fix a weakness to unlock an opportunity | W and O | Which weakness stops the person taking this opening? |
| WT | Avoid the trap where a weakness meets a threat | W and T | Where would applying now waste effort or burn a chance? |

Each strategy needs:

- `id`: the type plus a number, for example `WO1`.
- `type`: `SO`, `ST`, `WO` or `WT`.
- `text`: one sentence that says the move.
- `uses`: the S, W, O and T ids it combines: at least one of each of its two
  letters, and no others (an SO strategy uses only S and O items).
- `actions`: the plan action ids (`A01` and so on) it creates. Every strategy
  should create at least one action, or say in its text why not yet.
- `scope` (optional): `overall` or an organisation id.

`scripts/validate.py` checks that every id in `uses` and `actions` exists. The
dashboard links each strategy to its actions.

### Which type first

Start with WT and WO. The binding constraints for most non-traditional
candidates are, in order: eligibility, a warm path, visible proof of work,
and a tailored application. A WT strategy that stops a wasted application, or
a WO strategy that opens a warm path, usually moves the number more than an SO
strategy that polishes a strength.

## From strategy to plan action

For each strategy:

1. Pick the matching move from the action library in `CAMPAIGN.md`.
2. Add it to `campaign/plan.json` with its `dimension`, an honest
   `expected_points`, `roles_affected`, `chance` and `effort_hours`, a
   `done_when` and the `strategy_ids` it serves.
3. Put the action id in the strategy's `actions` list.

## Worked example: Alex Example (fictional)

This is a short version of `examples/demo-workspace/eval/swot.json`. Alex
Example is a fictional program manager in Brisbane with ten years of warehouse
and transport operations at the fictional Contoso Freight. Alex targets three
fictional organisations: Acme AI, Globex Labs and Initech Robotics.

**Strengths**

- S1: Ten years running warehouse and transport operations and programs (E01
  corroborated, E02 self-reported job history). D1, program and applied roles.
- S2: A verified open-source evaluation tool with 14 releases and outside
  contributors (E04, verified). D2.
- S3: Full work rights in Australia and New Zealand, where Initech and Acme
  hire (E11, self-reported eligibility). D6.

**Weaknesses**

- W1: No warm path into Initech Robotics yet (E19: the network map shows no
  contacts there). D3.
- W2: No product management title, so product roles see a hard-requirement gap
  (E01, E02). D1.
- W3: The LinkedIn headline overstates team size: 40, when the evidence says 8
  (E16, contradicted). D5.
- W4: Nothing built specifically for Acme AI yet (E04). D4.

**Opportunities**

- O1: Initech Robotics has program and product roles open in Melbourne and
  Brisbane (`market/roles/latest.json`).
- O2: Globex Labs lists an AI Success role in Singapore that names logistics
  customers as a plus (posting `globex:g-0003`).
- O3: Acme AI runs a public evaluation challenge every quarter
  (`market/orgs.json`).

**Threats**

- T1: Government-facing roles at Acme AI need US citizenship and a clearance
  (posting `acme:4100006`).
- T2: Recruiters compare public profiles with résumés at screening, so a
  mismatch reads as dishonest (a note in `campaign/inbox.md`).
- T3: Product roles ask for 5 or more years with a product title (posting
  `globex:g-0001`).

**TOWS strategies**

- SO1 (S1 + O1): Use ten years of warehouse programs to go after Initech's
  fleet deployments role. Creates A05 (tailor the application) and A06 (apply).
- SO2 (S2 + O2): Send route-eval ahead of the Globex introduction. Creates A02.
- ST1 (S3 + T1): Focus on Australian roles, not US government ones. Creates A06.
- WO1 (W1 + O1): Open a warm path into Initech. Creates A07 (ask three
  logistics contacts) and A11 (go to the Initech operators meetup).
- WO2 (W4 + O3): Build a small route-eval demo for Acme's evaluation challenge.
  Creates A10.
- WT1 (W3 + T2): Fix the overstated headline before any application goes out.
  Creates A04, which the formula ranks first.
- WT2 (W2 + T3): Do not spend effort on product roles yet. No action; the roles
  go to the backlog, and the text says why.

Notice how each strategy names a real move with a done-when, rather than
restating the grid. Open the demo dashboard's SWOT view to see the grid, the
per-organisation grids for Initech and Globex, and each strategy linked to its
plan actions.
