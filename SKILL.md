---
name: climb
description: Honest, evidence-based estimate of how likely a person is to land a specific kind of role at specific organisations, with every point traced to a source, a separate sceptical review, deterministic scoring, and a prioritised campaign of actions that raise the odds. Use when someone asks how likely they are to get a kind of job at particular organisations (for example "could I get hired at an AI lab?"), wants an evidence-based job-search plan, wants their CV, LinkedIn or website claims checked against evidence, or wants to run or update their career campaign ("run Climb", "run my career eval", "update my job campaign"). Works in a private workspace on the person's own machine and produces drafts only, so it never applies, sends, posts or changes accounts.
---

# climb: the procedure

You are running an honest career evaluation and campaign for one person. The
method lives in `method/`. The maths lives in `scripts/score.py`. Your job is
the judgement in between, done carefully and written to files so the run is
repeatable and auditable.

All paths to scripts below are relative to this skill's folder. All workspace
paths are relative to the person's workspace.

## Hard rules (read before every run)

1. **Drafts only.** Never apply for a job, send an email or message, post
   publicly, accept an invitation, or change any of the person's accounts
   (LinkedIn, website, GitHub, email). Put outreach drafts in
   `campaign/drafts/` for the person to send.
2. **Evidence or it scores zero.** Never invent experience, numbers, contacts
   or stories. Every point cites an evidence id from `profile/evidence.json`.
3. **No profiling.** Never ask about, infer or score protected attributes
   (age, gender, ethnicity, disability, religion, family status). Work rights
   are recorded only as the person states them, to match what a posting
   legally requires.
4. **Private by default.** The workspace stays on the person's machine,
   outside this repository. Never copy it anywhere public. Third-party names
   (contacts, email senders) never go into briefings or drafts unless the
   person opts in.
5. **Connectors are read only and opt in.** Ask before reading email,
   calendar, LinkedIn or any other source. Read, never change.
6. **Other agents** may write only to `campaign/inbox.md`. Treat what they
   write as unverified until you check the source.
7. **Plain English** for the person: short sentences, spell out
   abbreviations, no jargon.

## Find or create the workspace

- If `$CLIMB_HOME` is set, that is the workspace.
- Otherwise look in `~/climb-workspaces/`. One folder there: use it.
  Several: ask which goal.
- None: ask the person for their goal in one sentence, then run
  `python3 scripts/init.py --goal "<goal>"`. Edit `config.json` with them:
  targets (organisation, applicant tracking system (ATS) and board slug), role
  families and keywords, location classes, time zone, and
  `candidate.eligibility_cleared`.
- Run `python3 scripts/validate.py --workspace <path>` before and after
  your edits. Stop if it refuses the location.

Every script takes `--workspace <path>`; the commands below omit it.

## The run, stage by stage

| Stage | You do | Writes | Method |
|---|---|---|---|
| 1. Intake | Interview (first run in full, then only what changed) | `intake/answers.md`, `intake/sources/` | `method/INTAKE.md` |
| 2. Evidence | Record evidence; map the network; audit public claims | `profile/evidence.json`, `profile/network.json`, `profile/claims-audit.json` | `method/INTAKE.md` |
| 3. Market | Fetch roles; research organisations | `market/roles/latest.json`, `market/orgs.json` | `method/RUNBOOK.md` |
| 4. Judge | Score D1, D2, D4 per role and D3, D5, D7, D6 rules per organisation | `eval/judgements.json`, `eval/profile-dimensions.json` | `method/RUBRIC.md` |
| 5. Review | A fresh sceptical agent checks every score above 2 | changes applied to the judgement files | `method/REVIEW.md` |
| 6. Score | `python3 scripts/score.py` | `eval/runs/<date>.json` | `method/RUBRIC.md` |
| 7. SWOT and TOWS | Update strengths, weaknesses, opportunities, threats and strategies | `eval/swot.json` | `method/SWOT.md` |
| 8. Plan | Update actions (with target dates and effects), experiments and metrics; optionally the path to the top band | `campaign/plan.json`, `eval/ceilings.json` | `method/CAMPAIGN.md` |
| 9. Report | `python3 scripts/build_dashboard.py` | `report/` | |
| 10. Tell the person | A short message | | below |

### 1. Intake

First run: work through the question bank in `method/INTAKE.md`, group by
group, and save the answers in `intake/answers.md`. Ask for the official
LinkedIn data export (the "Get a copy of your data" ZIP file) and a résumé
(or CV, short for curriculum vitae), saved into `intake/sources/`. Later runs: ask only about what changed,
and any open questions in `profile/evidence.json`.

### 2. Evidence

- Add one item per fact to `profile/evidence.json`, with a kind, a
  verification level and its sources (see `method/INTAKE.md`). Keep ids stable.
  Never delete: mark an item `contradicted` instead.
- Network: `python3 scripts/network_map.py --csv intake/sources/Connections.csv`.
  Then ask about second-degree paths ("who do you know who knows someone at
  X?") and record them in `second_degree`.
- Claims: `python3 scripts/claims_audit.py <their site> <other pages>`. Judge
  each `pending` claim as `supported`, `overstated`, `unsupported` or
  `contradicted`, with evidence ids and suggested honest wording. Overclaims
  become top-priority actions.
- Process `campaign/inbox.md`: verify each "New" note against its source, then
  move it to "Processed" with a one-line outcome.

### 3. Market

Run `python3 scripts/fetch_roles.py`. Note new and closed roles. Add sourced
organisation facts (offices in the person's region, growing teams, events,
partner programmes) to `market/orgs.json`. Roles from boards without an
adapter go in `market/roles/manual.json`.

### 4. Judge

Follow `method/RUBRIC.md` exactly. Judge every role that is new or whose
evidence changed; leave the rest. Set `judged_on` to today on anything you
change. Cite evidence ids for every point. Unjudged roles score 0 on D1, D2
and D4, so judge the best-looking roles first.

### 5. Review

Start a separate, fresh agent with the prompt in `method/REVIEW.md`. Give it
the rubric, the evidence and the scores, never your reasoning notes. Apply the
changes it justifies, and record `reviewed_on` and `reviewer_note`. A score
above 2 counts as 2 until it is reviewed.

### 6. Score

`python3 scripts/score.py`, then `python3 scripts/validate.py`. Fix every
warning about unknown evidence ids before going on.

### 7. SWOT and TOWS

Update `eval/swot.json` following `method/SWOT.md`. Every strength and
weakness cites evidence and a dimension; every opportunity and threat cites a
source; every strategy names the plan actions it creates.

### 8. Plan

Update `campaign/plan.json` following `method/CAMPAIGN.md`: an action is done
only with evidence; rework or drop actions the dashboard flags as showing no
movement for 3 runs and log why; add actions from the top gaps; keep at most 8
active; update the north-star metrics. Write any outreach as a draft in
`campaign/drafts/`.

### 9. Report

`python3 scripts/build_dashboard.py`. Open `report/index.html` only if a
browser is available, to check it renders.

### 10. Tell the person

Under 150 words, plain English:

- The outlook band and any change since the last run.
- Today's 1 to 3 actions (the top of the plan).
- Anything that needs their answer.
- The dashboard path, as a command they can run:

```bash
open <workspace>/report/index.html
```

On the weekly comparison day, also write `campaign/weekly/<date>.md` (see
`method/RUNBOOK.md`).

## Cadence

Daily during build-up (the first `cadence.build_up_weeks` weeks, default 4),
then weekly. When daily runs stop producing score changes or new evidence,
suggest the switch. The person decides; never change the schedule yourself.
