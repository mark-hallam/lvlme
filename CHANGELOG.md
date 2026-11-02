# Changelog

What changed in each version of LVLme, newest first. A version number is the
`version` in `.claude-plugin/plugin.json`, and a released version also has a
git tag (`v0.2.0` and so on). LVLme was called Climb until 3 November 2026,
so the versions before 0.3.0 carry that name.

**Added** is new, **Changed** works differently and **Fixed** was wrong
before. Nothing here changes how a score is worked out unless it says so.

## Unreleased

Work on top of 0.3.0 that is not in a released version yet.

### Added

- **Warm paths.** A new workspace file, `campaign/warm-paths.json`, records
  how far each contact at a target organisation has come: followed, talked,
  connected, knows your work, would refer. The dashboard shows it as a small
  strip under Do next, and the files written for agents carry it too. It is
  progress only: the score never reads it, and the warm path factor is still
  judged from evidence.
- **Reading your dashboard.** A
  [one-page plain-English guide](docs/for-you/READING-YOUR-DASHBOARD.md) to
  each number on the dashboard, and what to do first.
- **Demo folder.** `docs/demo/` holds both fictional demos (an LVLme quick
  result and the full campaign dashboard) behind one page that opens straight
  from your computer. `examples/build_demo_site.py` rebuilds it, and refuses
  any workspace that is not marked fictional.
- **This changelog.**
- **LVLme quick reads Workday links properly.** Many large employers post
  jobs on Workday, whose careers pages hold only a flat summary: LVLme quick
  found no requirements in them and named the organisation by its legal
  entity ("2100 Example Corp USA"). It now reads the posting through
  Workday's public job feed, so the requirements, nice to haves and duties
  come through, and it uses the name people know. If the feed cannot be
  reached, it falls back to the page as before.
- **LVLme quick reads SmartRecruiters links properly.** Canva, ServiceNow,
  Bosch and many others post jobs on SmartRecruiters
  (`jobs.smartrecruiters.com`). Its pages open with the employer's welcome,
  and LVLme quick used to read that greeting as the role's requirements and
  find no location. It now reads the posting through SmartRecruiters' public
  posting API: the job description and qualifications as their own sections,
  the welcome last (never as a requirement), the city, whether the role is
  hybrid or remote, and the date it was posted. A welcome placed at the top of
  the job description is not read as a requirement either, a posting written
  entirely under the company description is still read, a closed posting gets
  a plain message, and the apply page's link works too.
- **LVLme quick reads Workable links.** Hugging Face and many smaller
  employers post jobs on Workable (`apply.workable.com`). Its pages are drawn
  in the browser and hold no posting text, so LVLme quick could not read them
  at all and asked for pasted text. It now reads the posting through
  Workable's public job feed: the description, the requirements (read as
  requirements even when the employer gives them no heading), any nice to
  haves, and the benefits last, never as a requirement. It also gives every
  city listed, whether the role is hybrid, remote or on site, the department,
  the date it was posted, and the employer's name as the employer writes it
  ("Hugging Face", not "huggingface"). The short `apply.workable.com/j/` links
  and the older `<employer>.workable.com` links work too, and a closed posting
  gets a plain message.

### Changed

- **More section headings are understood** when a posting is read, in LVLme
  quick and the full campaign: "What we need to see" lists requirements,
  "Ways to stand out" and "Good to have" list nice to haves, and "What you'll
  actually be doing" lists duties, "You're probably a match if" lists
  requirements, "This role is focused on" lists duties, and "What you'll
  learn" is about the role, not a requirement, and "Your missions" lists
  duties. Nothing about the scoring
  maths changed.

- **LVLme quick says what it could not check.** Public signal and
  application readiness cannot be judged from one posting and a CV. They used
  to count 0 without saying so. Now each is marked "Not checked" and the fit
  is a range, for example "41 today, up to 56 if these turn out strong".
  Today's odds and fit are worked out exactly as before.
- **LVLme quick takes a couple of minutes**, not five (a real run took 92
  seconds).
- **A shorter first run.** `SKILL.md` holds the one First run list, and the
  other docs link to it. The interview's first message is about 120 words at
  most and asks three things. Questions about US export control and security
  clearance come only when an open role needs them.
- **Plain errors.** For a missing workspace, a missing file or a file that is
  not valid JSON (the text format the workspace files use), every script
  stops with one line that starts `lvlme:`, names the file and says what to do
  next. It never shows a Python traceback (the long technical error listing).
  `LVLME_DEBUG=1` shows the full details.

### Fixed

- **The share card no longer claims an offer.** Its headline said "From
  Low to an offer" even when no offer had come. It now states only what was
  measured, in the dashboard's own words, for example "Level 2, Low to
  Level 3, Moderate by day 29". The saved image says the same.
- **Install lines and links work.** They point at the repository that
  exists, https://github.com/mark-hallam/climb, and links to files in it
  follow its default branch, so "How to install it" and "Reading your
  dashboard" no longer open a page that is not there.
- A contact recorded by one word, such as "Will", no longer hides the
  ordinary word "will" all over the dashboard.
- `scripts/validate.py` now says when it skipped the checks across files
  because `config.json` was missing or broken, instead of reading as if they
  had passed.
- The LVLme quick result page: the logo in dark mode, Windows contrast
  themes, the "increase contrast" setting, text smaller than 12 pixels, names
  for screen readers and the size of the posting link's tap area. A test keeps
  every text colour at WCAG AA contrast (the Web Content Accessibility
  Guidelines' standard level) in every theme.

## 0.3.0 (3 November 2026)

Climb is now LVLme, said "level me". Same engine, same method, same promise.
Nothing about scoring, evidence or privacy changed. The full notes are in
[LVLme 0.3.0](docs/RELEASE-0.3.0.md).

### Changed

- **The name**, everywhere: the docs, the skills, the helper agents, the
  Cursor rules, the dashboard and the quick result page.
- **The plugin and marketplace** are both named `lvlme`. Install with
  `/plugin install lvlme --marketplace mark-hallam/climb`.
- **Commands**: `/lvlme`, `/lvlme-quick`, `/lvlme-interview`,
  `/lvlme-screen`, `/lvlme-audit` and `/lvlme-dashboard`. **Helper agents**:
  `lvlme:evidence-scout`, `lvlme:market-scout`, `lvlme:role-judge`,
  `lvlme:reviewer` and `lvlme:recruiter-screen`. In Codex, type `$lvlme`.
- **The workspace** setting is `LVLME_HOME`, and the folder is
  `~/lvlme-workspaces/`.
- **The repository** stays at https://github.com/mark-hallam/climb for now,
  so every install line and link above uses that address.

### Still works

- `CLIMB_HOME`, the `~/climb-workspaces/` folder, the plugin name `climb`
  (the marketplace moves it to `lvlme`), saying "run Climb" or "run Climb
  quick", and the theme and Pending ticks the dashboard saved in your
  browser. Workspaces written by Climb 0.2.0 are read as they are. To move an
  existing install, see [Coming from Climb](docs/INSTALL.md#coming-from-climb).

### Removed

- The old commands (`/climb`, `/climb-quick` and the rest), the old helper
  agent names and `$climb` in Codex. Use the new names, or say "run Climb".

Tests: 221 pass.

## 0.2.0 (3 November 2026)

Climb quick, and one yardstick for actions on the dashboard.

### Added

- **Climb quick** (now LVLme quick): one job link and a CV give honest odds
  for that posting and the top 3 fixes, on a one-page result and in a short
  message. It reads Greenhouse, Ashby and Lever postings through their public
  job board APIs (the published ways for a program to read a board), any
  other page once, or pasted text. LinkedIn links are refused. A blind
  reviewer checks any score above 2. It gives fixes and a brief, never
  application answers.

### Changed

- **One ranked list of actions.** Do next, the quests, the badges, the Plan
  list, the static summary and the files written for agents all follow the
  same order. Each action shows one points number: the points it is expected
  to add toward the next level.
- "Your best chance today 57 / 100" became "Best match 57 of 100", because it
  is a fit score, not a probability.
- Internal ids moved off the main parts of the dashboard, and the sample
  progress switch needs `?preview=1` in the address.
- **The README** leads with the promise, the one install line and "run Climb
  quick". It says plainly that LVLme is for the job you can't get yet (a
  reach outside your usual path), not for tailoring a CV. The detail moved
  to [How it works](docs/HOW-IT-WORKS.md).

### Fixed

- Phones and accessibility on the dashboard: first-screen controls are 44
  points, the page has one main heading, screen readers can follow the tabs,
  every status dot has a word beside it, and the do nothing line has at
  least 3 to 1 contrast.
- The quick message said a reviewer had checked every score above 2, even
  when no score was above 2. Found in a real run.

Tests: 202 pass.

## 0.1.1 (2 November 2026)

Truth fixes: the tool now says only what is true about itself.

### Changed

- **New workspaces start with your own goal.** The template used to be the
  frontier AI labs example, so a newcomer's first scores were for someone
  else's goal. Now it has no targets until the interview, and the example is
  opt in: `init.py --example frontier-ai-labs`.
- **Weekly by default**, plus a run whenever something changes. Scores only
  move when evidence changes, and a full run can start about 40 helper
  agents, so daily runs mostly cost usage.
- **Organisations' rules on AI in applications.** A target can record its
  policy (`ai_policy` in `config.json`). Where an organisation asks
  candidates to write their own first draft, as Anthropic does, Climb writes
  a brief and reviews the person's draft. It never writes the application.
- **Honest privacy wording.** Climb's files stay on your computer, but your
  AI agent's provider (for example Anthropic for Claude Code) receives
  whatever the agent reads.
- Every helper agent's instructions treat what it reads as data, never as an
  instruction.
- In the frontier AI labs example, a contact who lists SpaceXSI counts for
  xAI, because that is the name on xAI's job board.

### Fixed

- `scripts/score.py` no longer saves a dated run when no role has been
  judged, so there is never a fake Day 1. The dashboard skips any such run
  saved before.
- With no target organisations yet, `scripts/validate.py` and
  `scripts/fetch_roles.py` stop with one plain line that says to run the
  interview, instead of fetching nothing and calling it a market.

Tests: 164 pass.

## 0.1.0 (2 November 2026)

The first public release, as Climb.

### Added

- **The method** (`method/`): a rubric of seven factors, each capped by how
  well its evidence is checked, so a score can never be higher than its best
  evidence supports. Also a bank of intake questions, SWOT then TOWS
  (strengths, weaknesses, opportunities and threats, then the actions they
  suggest), a library of campaign actions, the sceptical reviewer's rules,
  privacy rules and a runbook.
- **The scripts**, in standard library Python: set up a workspace, fetch open
  roles from Greenhouse, Ashby and Lever (or by hand), map contacts from the
  LinkedIn data export, check the claims on your own pages, score
  deterministically (the same inputs always give the same result), build the
  dashboard, and check a workspace.
- **The Mission control dashboard**: the flight path from Day 1 to today and
  on to the expected, best case and do nothing paths, the What if rail, the
  level badge, the Verifiable record, and files for agents that keep names
  and salaries out in sensitive mode.
- **Level up**: the smallest set of open actions that reaches the next
  level, quests sorted by points per hour, level history and a streak. See
  [Levels](docs/LEVELS.md).
- **The interview, consistency audit, recruiter screen and profile fixes.**
  The interview works from documents the person already has. The
  consistency audit (`scripts/consistency_audit.py`) compares work history
  across a CV, LinkedIn, a website and forms, and flags likely title
  inflation. The recruiter screen is an independent cold read that never sees
  the campaign.
- **The review rule**: when the scorer and the reviewer disagree, a third
  score breaks the tie, the middle of the three stands, and every dispute is
  logged.
- **Packaging**: a Claude Code plugin that is its own marketplace, command
  skills, five helper agents for the parallel run with read only tool lists,
  Codex and Cursor entry points, and
  [the run's stages and gates](docs/ORCHESTRATION.md).
- **Seven gaps closed** after a real migration, all backward compatible:
  partially verified evidence, longer evidence ids, `x_` extension fields,
  parked actions, a review log format, a static summary that reads without
  JavaScript, and a gap pool per organisation.
- **Safety from the publish review**: the agent never browses or edits
  LinkedIn, text it reads is data and never an instruction, and only the lead
  agent searches email.
- A fictional demo workspace for Alex Example, rebuilt by
  `examples/build_demo.py`.

Tests: 154 pass.

Each released version's test count is from `python3 -m pytest -q` run on
that version's files. The count is added when a version is released.
