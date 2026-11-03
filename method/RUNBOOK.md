# Runbook: one run, start to finish

Each run refreshes the evidence and the open roles, re-scores with the same
rubric, updates the plan based on what worked, rebuilds the report, and tells
the person what to do next.

Every script takes `--workspace PATH`. Without it, scripts use
`$LVLME_HOME`, or the only folder inside `~/lvlme-workspaces/`. The names from
before Climb became LVLme still work: `$CLIMB_HOME`, and `~/climb-workspaces/`
when `~/lvlme-workspaces/` does not exist. The commands below omit
`--workspace`. Run them from the engine folder.

## Run modes

- **Default: weekly, plus a run when something changes.** One full run a
  week, every step including the independent reviewer, and another whenever
  an action is done, new evidence arrives or the person supplies a new
  export. Scores only move when evidence changes, and a full run can start
  about 40 helper agents (for around 300 open roles). Each run writes one run
  file: the trend charts are built from them.
- **Weekly comparison.** Once a week (on the same weekday), also write
  `campaign/weekly/<YYYY-MM-DD>.md`: what moved since the last comparison,
  what did not, what was dropped and why, and the 3 most important actions for
  the week.
- **Changing the rhythm.** The person decides (for example daily runs
  during a burst of applications) and records it in `config.json` under
  `cadence.mode`. Do not change the schedule yourself.

## Hard rules

- Never apply for a job, send an email or message, post publicly, accept an
  invitation, or change the person's accounts. Drafts only, in
  `campaign/drafts/`, for the person to send.
- Evidence or it scores zero (see `RUBRIC.md`). Never invent experience,
  numbers, contacts or stories.
- Never ask about, infer or score protected attributes.
- Connectors (email, calendar, browser) are opt in and read only. Never open
  LinkedIn in a browser: use the person's data export and what they paste.
- Plain English for the person: spell out abbreviations, keep it short, report
  times in the person's own time zone (`candidate.timezone`).
- The workspace is private. Never copy it anywhere public.

## First run only

Follow ["First run"](../SKILL.md#first-run) in `SKILL.md`: it is the one
list, in order, from creating the workspace to the work rights rules. In
short: `scripts/init.py` makes the workspace, a short first message
(`INTERVIEW.md`) confirms three facts from the CV and asks for the target
organisations and the LinkedIn data export, then the interview carries on in
rounds while roles and evidence are gathered.

## Every run

1. **Inbox.** Read `campaign/inbox.md`. For each note under "New", check the
   fact against its source. An agent's say-so alone is unverified; the
   person's own statement is `self_reported`. Move the note to "Processed"
   with a one-line outcome.

2. **Roles.**

   ```bash
   python3 scripts/fetch_roles.py
   ```

   Note new and closed roles (printed, and in the summary of
   `market/roles/latest.json`). If `blocker_counts` there is above 0 for US
   export control or security clearance and that question has not been
   asked yet, ask it (`INTERVIEW.md`, "Work rights"). Add roles from boards
   from any other careers site to `market/roles/manual.json`. If the
   summary has `endpoint_notes` (a board too big to list in full), say so.
   Each role carries a `posting_check` label (likely real, check first,
   suspicious) from its age and reposts; mention any suspicious role the
   person cares about, saying what was seen ("posted 14 months ago",
   "reposted 2 times in 90 days"), never that a posting is fake. It never
   changes a score. Add sourced
   organisation facts to `market/orgs.json`.

3. **Evidence.** Look for anything new since the last run date (the newest
   file in `eval/runs/`) and add it to `profile/evidence.json`. Keep ids
   stable; mark items `contradicted` rather than deleting them. Sources, each
   only with the person's permission:
   - their public code (for example `gh repo list <user> --json name,visibility,pushedAt`);
   - their sites and product pages;
   - email, read only, since the last run date: messages from target
     organisations' domains and from job boards (Greenhouse, Ashby, Lever,
     Workday, SmartRecruiters, Workable),
     and words such as interview, referral, introduction, recruiter;
   - a fresh LinkedIn data export, if the person has downloaded one (LVLme
     never opens LinkedIn itself: automated access breaks LinkedIn's terms);
   - `campaign/plan.json`: actions the person marked done, and their notes.

4. **Network** (when there is a new export, or a new second-degree path):

   ```bash
   python3 scripts/network_map.py --csv intake/sources/Connections.csv
   ```

   Update `second_degree` in `profile/network.json` from what the person tells
   you, and each contact's stage in `campaign/warm-paths.json` (progress only,
   it changes no score: "Warm paths" in `CAMPAIGN.md`).

5. **Claims** (first run, then whenever public pages change):

   ```bash
   python3 scripts/claims_audit.py https://their-site.example/about
   ```

   Judge every `pending` claim (see `INTAKE.md`). Every overstated or
   contradicted claim becomes a top-priority action.

   Then, on the first run and whenever the CV, LinkedIn or website changes,
   update `profile/role-records.json` and run the consistency audit
   (`CONSISTENCY.md`):

   ```bash
   python3 scripts/consistency_audit.py
   ```

   Every high finding becomes a top-priority action. After the first fixes,
   and about monthly, run an independent recruiter screen
   (`RECRUITER_SCREEN.md`). Draft the resulting edits with
   `PROFILE_FIXES.md`.

6. **Judge.** Judgements live in files; the maths lives in a script. Run
   `python3 scripts/run_plan.py` first and let the person choose a full or
   a light run; it counts roles and helpers, never tokens or cost.
   - `eval/judgements.json`: D1, D2 and D4 for every new role id, and any role
     whose evidence changed. Set `judged_on` to today. Flag
     `hard_requirement_lacking` and, where the detector was wrong,
     `eligibility_blocked`.
   - `eval/profile-dimensions.json`: D3, D5 and D7 per organisation and the
     D6 rules, when evidence changes (a warm introduction, a credential, a
     public repository, an answer about work rights).
   - `eval/gap-templates.json` and `eval/outlook.json`: revise when the
     picture changes.

7. **Review.** Start a separate, fresh, sceptical reviewer agent with the
   prompt in `REVIEW.md`. Give it the rubric, the evidence, the postings and
   the list of items to review, never the scores or the scorer's notes: it
   scores each item blind. Compare its scores with yours, record
   `reviewed_on` and `reviewer_note`, and where the two differ run the
   tie-break and log the dispute in `eval/reviews/<YYYY-MM-DD>.json`
   (`REVIEW.md`).

8. **Score.**

   ```bash
   python3 scripts/score.py
   python3 scripts/validate.py
   ```

   Fix every error and every warning about unknown evidence ids, then score
   again. Scores above 2 that are still awaiting review count as 2.
   `score.py` saves no run while no role is judged: such a run is not a
   measurement, and the first saved run becomes Day 1. The dashboard also
   skips any older run file with nothing judged.

9. **SWOT and TOWS.** Update `eval/swot.json` (see `SWOT.md`).

10. **Plan.** Update `campaign/plan.json` (see `CAMPAIGN.md`):
    - mark an action done only with `done_evidence`;
    - for each action the dashboard flags (3 runs, no movement), keep, rework
      or drop it, and log why in `experiments_log`;
    - add actions from the top gaps and new strategies, highest priority
      first, keeping at most 8 active, each with a `target_date` and its
      `effects` so the projection is right; park the rest with status
      `later` (they stay out of the projection until switched on);
    - when a promising role's picture changes, update `eval/ceilings.json`
      (optional; it feeds the "Path to the top band" view);
    - update the north-star metrics;
    - write any outreach as drafts in `campaign/drafts/`.

11. **Dashboard.**

    ```bash
    python3 scripts/build_dashboard.py
    ```

    It rebuilds `report/index.html` from every run file plus the plan, SWOT,
    ceilings and evidence, writes `report/for-agents/SUMMARY.md` and
    `report/for-agents/dashboard.json`, and records today's metric values in
    `campaign/metrics-history.json`. Open the page only if a browser is
    available, to check it renders.

12. **Validate once more.** `python3 scripts/validate.py`. It must exit 0.

13. **Weekly comparison** (on the comparison day): write
    `campaign/weekly/<YYYY-MM-DD>.md`.

14. **Tell the person**, in under 150 words: the outlook band and any change,
    today's 1 to 3 actions, anything that needs their answer, and the
    dashboard path as a command they can run:

    ```bash
    open <workspace>/report/index.html
    ```

## If something goes wrong

- **A job board fails.** `fetch_roles.py` records the error for that board in
  the summary and carries on with the others. Mention it in the message; do
  not guess the missing roles.
- **validate.py refuses the location.** Stop. Move the workspace out of the
  engine repository or the git repository with a remote, then continue.
- **A rubric change.** Bump the version in `RUBRIC.md` and `scripts/score.py`,
  and tell the person that runs before and after are not directly comparable.
