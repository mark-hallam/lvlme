# Runbook: one run, start to finish

Each run refreshes the evidence and the open roles, re-scores with the same
rubric, updates the plan based on what worked, rebuilds the report, and tells
the person what to do next.

Every script takes `--workspace PATH`. Without it, scripts use
`$CLIMB_HOME`, or the only folder inside `~/climb-workspaces/`.
The commands below omit it. Run them from the engine folder.

## Run modes

- **Build-up (daily).** For the first `cadence.build_up_weeks` weeks (default
  4), run every step every day, including the independent reviewer. Write one
  run file per day: the trend charts are built from them.
- **Steady state (weekly).** After build-up, one full run a week.
- **Weekly comparison.** Once a week (on the same weekday), also write
  `campaign/weekly/<YYYY-MM-DD>.md`: what moved since the last comparison,
  what did not, what was dropped and why, and the 3 most important actions for
  the week.
- **Switching to weekly.** After build-up, if the last 7 daily runs produced
  no score change and no new evidence, say so and suggest weekly runs. Do not
  change the schedule yourself. The person decides, and records it in
  `config.json` under `cadence.mode`.

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

1. Create the workspace:

   ```bash
   python3 scripts/init.py --goal "Frontier AI labs"
   ```

   It refuses a non-empty folder, a folder inside the engine repository, or
   one inside a git repository that has a remote.
2. `config.json` starts with the goal and no targets or role families (unless
   you used `--example`), so `validate.py` and `fetch_roles.py` stop until
   they are set. Fill it in with the person: targets (organisation id, name,
   applicant tracking system (ATS): `greenhouse`, `ashby`, `lever` or
   `manual`, and the board slug), role families and keywords, location
   classes, `candidate.timezone`, `candidate.eligibility_cleared`,
   `privacy.redact_terms` (their employers' names).
3. Interview the person with the full question bank in `INTAKE.md`,
   document-led and in short rounds (`INTERVIEW.md`). Save the answers in
   `intake/answers.md`.
4. Ask for the LinkedIn data export and a résumé, saved in `intake/sources/`.
5. Fill `eval/profile-dimensions.json` D6 rules for every location class, from
   the work-rights answers.

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
   `market/roles/latest.json`). Add roles from boards without an adapter to
   `market/roles/manual.json`. Add sourced organisation facts to
   `market/orgs.json`.

3. **Evidence.** Look for anything new since the last run date (the newest
   file in `eval/runs/`) and add it to `profile/evidence.json`. Keep ids
   stable; mark items `contradicted` rather than deleting them. Sources, each
   only with the person's permission:
   - their public code (for example `gh repo list <user> --json name,visibility,pushedAt`);
   - their sites and product pages;
   - email, read only, since the last run date: messages from target
     organisations' domains and from job boards (Greenhouse, Ashby, Lever),
     and words such as interview, referral, introduction, recruiter;
   - a fresh LinkedIn data export, if the person has downloaded one (Climb
     never opens LinkedIn itself: automated access breaks LinkedIn's terms);
   - `campaign/plan.json`: actions the person marked done, and their notes.

4. **Network** (when there is a new export, or a new second-degree path):

   ```bash
   python3 scripts/network_map.py --csv intake/sources/Connections.csv
   ```

   Update `second_degree` in `profile/network.json` from what the person tells
   you.

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

6. **Judge.** Judgements live in files; the maths lives in a script.
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
   prompt in `REVIEW.md`. Give it the rubric, the evidence and the scores, not
   the scorer's notes. Apply the changes it justifies, and record
   `reviewed_on` and `reviewer_note`. Where the two scores differ, run the
   tie-break and log the dispute in `eval/reviews/<YYYY-MM-DD>.json`
   (`REVIEW.md`).

8. **Score.**

   ```bash
   python3 scripts/score.py
   python3 scripts/validate.py
   ```

   Fix every error and every warning about unknown evidence ids, then score
   again. Scores above 2 that are still awaiting review count as 2.

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
