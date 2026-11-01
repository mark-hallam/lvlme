# For AI agents (Codex, Cursor and others)

This repository is **Climb**: a method and small scripts that estimate,
honestly, how likely a person is to land a specific kind of role at specific
organisations, and turn the gaps into a prioritised campaign.

The full procedure is in [`SKILL.md`](SKILL.md). The rules for each stage are
in [`method/`](method/). This file is the short version.

## Hard rules

- **Never** apply for a job, send an email or message, post publicly, accept
  an invitation, or change the person's accounts. Drafts only, in
  `campaign/drafts/` in their workspace, for the person to send.
- **Evidence or it scores zero.** Never invent experience, numbers, contacts
  or stories. Every point cites an evidence id.
- **Never** ask about, infer or score protected attributes (age, gender,
  ethnicity, disability, religion, family status).
- The person's data lives in a **private workspace** outside this repository
  (`$CLIMB_HOME`, or a folder in `~/climb-workspaces/`). Never
  write personal data into this repository and never copy the workspace
  anywhere public.
- Read-only access to any source (email, calendar, LinkedIn), and only when
  the person has said yes.

## If you are a helper agent, not the one running the campaign

Read `report/for-agents/SUMMARY.md` and `report/for-agents/dashboard.json` in
the person's workspace. The only file you may write to is
`campaign/inbox.md`: append a dated note under "New", say who you are, and give
a source for every fact. The next run checks it. Your say-so alone is not
evidence.

## The run

Every script takes `--workspace PATH`.

1. **Intake**: interview the person with `method/INTAKE.md`; save answers in
   `intake/answers.md`.
2. **Evidence**: record facts in `profile/evidence.json`; run
   `python3 scripts/network_map.py --csv <Connections.csv>`; run
   `python3 scripts/claims_audit.py <their pages>` and judge each pending claim.
3. **Market**: `python3 scripts/fetch_roles.py`; add sourced facts to
   `market/orgs.json`.
4. **Judge**: fill `eval/judgements.json` and `eval/profile-dimensions.json`
   using `method/RUBRIC.md`.
5. **Review**: a separate, fresh agent follows `method/REVIEW.md`. It never
   sees the scorer's reasoning.
6. **Score**: `python3 scripts/score.py`, then `python3 scripts/validate.py`.
7. **SWOT and TOWS**: `eval/swot.json`, using `method/SWOT.md`.
8. **Plan**: `campaign/plan.json` (each action with a `target_date` and its
   `effects`), and optionally `eval/ceilings.json`, using `method/CAMPAIGN.md`.
9. **Report**: `python3 scripts/build_dashboard.py`.
10. **Tell the person**: under 150 words, the outlook, today's 1 to 3 actions,
    anything that needs their answer, and the path to `report/index.html`.

The detailed run order, run modes and weekly comparison are in
[`method/RUNBOOK.md`](method/RUNBOOK.md).

## Working on the engine itself

- Python 3.9 or newer, standard library only. No telemetry. Network calls only
  in `fetch_roles.py` (public job-board APIs, or application programming
  interfaces) and `claims_audit.py` (addresses
  the person passes).
- Tests run offline: `python3 -m unittest discover -s tests`.
- The demo in `examples/demo-workspace/` is fictional. Rebuild it with
  `python3 examples/build_demo.py`.
- See [`CONTRIBUTING.md`](CONTRIBUTING.md).
