# Changelog

What changed in each version of LVLme, newest first. A version number is the
`version` in `.claude-plugin/plugin.json`, and a released version also has a
git tag (`v0.2.0` and so on). LVLme was called Climb until 3 November 2026,
so the versions before 0.3.0 carry that name.

**Added** is new, **Changed** works differently and **Fixed** was wrong
before. Nothing here changes how a score is worked out unless it says so.

## Unreleased

### Added

- **Doors: where to meet the people who hire.** Referrals come from people,
  and people are met at events and programmes. `scripts/fetch_doors.py`
  reads the public Luma calendars you name in `config.json`
  (`doors.calendars`) and keeps upcoming events that name a target
  organisation or are in your home city; it also lists fellowship,
  residency and ambassador postings already on the job boards. Doors an
  employer's events page or the market scout found go in with
  `scripts/doors.py add`. Each door has a date, a place, a link, its source
  and the factor it can move, shows on a new Doors card on the dashboard,
  and becomes a plan action with `scripts/doors.py plan`. Someone you met
  there goes into warm paths by the name you give (`scripts/doors.py met`).
  Meetup, Eventbrite and LinkedIn are never fetched, and a test keeps it so.
  You register, RSVP or apply yourself. The weekly note's "event worth a
  look" is now the next door.
- **How right has LVLme been?** A new dashboard card checks LVLme's odds
  against what happened. Each application recorded as sent keeps the bands
  its role had that day (`predicted` in `campaign/applications.json`), and the
  card shows, for each band, how many led to an interview or an offer,
  beside public figures (Ashby, 16 May 2025: 3% of inbound and 40% of referred
  applications reach interview) and a blend of the two. A band's rate stays
  hidden until it has 5 results, and a ranking check (did the higher-rated
  applications do better?) until 10. Advisory only: a test proves scores are
  identical with or without outcomes. The demo now has made-up applications.
- **Research packs.** One page per target organisation, in
  `report/research/`, linked from the organisation's detail on the
  dashboard: what it is building, recent news, offices, the teams hiring,
  its events and programmes, and its rules on AI for candidates. Built from
  facts LVLme already holds, so it fetches nothing; every line has its source
  and date, and a fact nobody opened the source for says "Not yet checked".
  `market/orgs.json` facts gain the kinds `building` and `news`, and the
  fields `published_on` and `verified`.
- `scripts/build_dashboard.py --today` builds the page for a given day, so
  the demo is the same whenever it is rebuilt.

### Fixed

- The dashboard page ranked a plan action whose roles all look suspicious
  as high as any other, while the Python ranking (and the static summary)
  put it last. Both now put it last.

## 0.5.0 (3 November 2026)

Autopilot for your career: a check-in that runs itself each week, an
applications tracker with timed follow-ups, a check on whether each job is
still a real opening, all six job boards in the full campaign, and a way to
turn a LVLme quick result into a full campaign with nothing redone. The full
notes are in [LVLme 0.5.0](docs/RELEASE-0.5.0.md).

Tests: 434 pass.

### Added

- **All six job boards in the full campaign.** A target can now be on
  Workday, SmartRecruiters or Workable as well as Greenhouse, Ashby or Lever,
  read with the same code LVLme quick uses. Those boards list titles only,
  so LVLme reads in full only the postings whose title fits a role family
  and lists the rest as excluded. A Workday target names its careers page in
  `careers_url`.
- **The first-draft rule, checked in code.** For an employer that asks for
  your own first draft, `scripts/validate.py` reports any draft in
  `campaign/drafts/` that is not a brief, a review of your draft,
  preparation or outreach, and asks you to re-read the employer's AI policy
  when it was last checked over 30 days ago.
- **LVLme quick names Anthropic's AI guidance** on an Anthropic posting:
  "Anthropic asks for your own first draft. Write it, then I'll review it.",
  with a link to the page.
- **Climb from here.** `python3 scripts/quick.py promote` turns a LVLme
  quick result into a full campaign with nothing redone: the same evidence
  and levels, the posting as the first role, its employer as the first
  target on its own job board, and the judgements carried across, with the
  blind review's agreements and open disputes kept. The campaign's first
  score matches quick's, and the LinkedIn export can come later.
- **Autopilot: a check-in that runs itself.** `/lvlme-autopilot` explains
  what will run, asks for each permission once (rhythm, light or full run,
  which read-only sources, whether helper agents may run), then sets up the
  schedule with the Claude desktop app's scheduled tasks or prints a line
  for your computer's own scheduler. Each run leaves a "This week" note, the
  dashboard's new first card: what changed, your level, new and closed
  roles, follow-ups due, one event worth a look, and the one thing to do.
  Off is one command. It never sends, applies or contacts anyone.
- **Know the size of a run before it starts.** `scripts/run_plan.py` says
  how many roles need judging (new, changed posting, or new evidence) and
  about how many helpers a full run and a light run (your top 30, plus new
  roles) would start, so you choose. Unchanged roles keep their last
  judgement, so a run with nothing new starts no judging helpers. It counts
  helpers only, never tokens or cost.
- **Applications and follow-ups.** `scripts/applications.py` tracks each
  application in `campaign/applications.json` with career-ops' ten stage
  names, and keeps every change in an append-only log. Follow-ups are timed
  (7 days, then 7 more, at most 2; a thank-you note the day after an
  interview), shown on a new Applications card, and drafted for you to
  finish and send. Nothing is ever sent for you.
- **Is this job still open?** Every role gets a quiet label from its age and
  reposts: likely real, check first, or suspicious ("Open, but posted 14
  months ago", "reposted 2 times in 90 days"), on the dashboard and in
  `market/roles/latest.json`. A plan action whose roles all look suspicious
  ranks lower in Do next. Scores never change, and LVLme never calls a
  posting fake.
- **Install in Claude chat**, tried for real: `docs/INSTALL.md` has the
  steps (Customize, Plugins, add the `mark-hallam/lvlme` marketplace) and
  says what works in chat and what needs Claude Code.

### Fixed

- In Claude chat, LVLme quick shares the result page as a file rather than
  an open command, which cannot work there.
- Three method files told the agent to give the blind reviewer the scores.
  Every file now says the reviewer never sees them, and a test keeps it so.

## 0.4.0 (3 November 2026)

Warm paths, a reading guide, six job boards for LVLme quick, and a round of
honesty fixes found by testing the public version end to end. The full notes
are in [LVLme 0.4.0](docs/RELEASE-0.4.0.md).

Tests: 374 pass.

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

- **Scoring again with nothing changed no longer breaks your streak.** A
  later day with the same inputs and no plan action finished since was saved
  as a day with no progress, which reset "Progress you can trust" to 0.
  `scripts/score.py` now says nothing changed and saves no new day;
  `--force` saves it anyway.
- **LVLme quick names a fix it leaves out, and why.** A fix that cannot move
  in a few months, adds nothing or is already met used to vanish, so the
  page said "The top 2 fixes" with no word about the third. It now gets a
  "Not listed" line on the page, and in the chat message when fewer than
  three fixes show.
- **Biggest unlocks reads as fit points on one role.** On a phone it showed
  totals such as "+144" beside scores out of 100, with no explanation. Each
  row now shows what a role gains on average and how many roles it lifts
  ("+12 each, lifts 11 roles"), with the same one-line explanation on every
  screen.
- **Warm paths count your LinkedIn connections.** After
  `scripts/network_map.py` found a connection at an organisation with no
  warm path yet, the card still said "No one yet". It now says "1
  connection, not asked yet" and how to start a warm path.
- **A role nobody has judged is no longer shown as measured.** Such a role
  kept a fit worked out from the profile-wide factors alone, and it showed up
  as an organisation's best role, in the home region list, in the tile counts
  and in the Biggest unlocks role counts, on the dashboard and in
  `report/for-agents/SUMMARY.md`. Now it is "not judged yet": an organisation
  with nothing judged says "No role judged yet", the counts say "of N judged",
  the gap leaderboard counts only judged roles, and the Roles table marks the
  factors nobody has judged instead of showing them as 0. This changes the
  gap numbers in a run, not any role's fit.
- **LVLme quick says when a missing hard requirement holds the odds down.**
  The chat summary and the fixes card now say in one line that both chances
  drop a step and that no listed fix changes it, and why the requirements
  match fix is not listed.
- **Hybrid roles are no longer called remote.** Ashby boards mark most
  office based roles with both a remote flag and the label Hybrid, and
  LVLme believed the flag. A London role three days a week in the office
  showed as "Remote" in LVLme quick and counted as remote in
  `market/roles/latest.json`. The board's own label (Remote, Hybrid or
  Onsite) now wins, is kept on each role as `workplace`, and the LVLme quick
  header says "Hybrid" when the board does. A role that lists a remote
  location as one of its options still counts as remote.
- **The roles heat map reads the same in dark mode.** Its caption said
  "darker is stronger", which was the wrong way round in dark mode, where a
  5 is the lightest cell. It now says a stronger score stands out more from
  the page, which holds in both themes, and the dark 1 and 2 cells are
  easier to tell apart.
- **One answer for "where will I be if I follow the plan".** When roles
  tied for today's best fit, the journey chart, its tiles, the phone bar,
  the share card and What if followed whichever role was listed first,
  while Level up followed the role the plan lifts most. They now all use
  the best fit across your roles under the switches, the same number Level
  up gives. Organisation cards do the same within each organisation.
- **LVLme quick names the employer properly from a board link.** An Ashby
  or Lever link gives no employer name, so `openai` came out as "Openai".
  The name is now read from how the posting writes it ("OpenAI"), and when
  nothing confirms it the output says it is a guess, so your agent checks
  it with you and passes `--org`.
- **Engineering and construction jobs stay out of the example market.** With
  the frontier AI labs example (you don't write production code), titles
  such as Android Engineer or Engineering Manager, and construction project
  manager jobs, no longer count as roles open to you. An engineering title
  now counts as heavy coding unless the posting says otherwise.
- **The share card no longer claims an offer.** Its headline said "From
  Low to an offer" even when no offer had come. It now states only what was
  measured, in the dashboard's own words, for example "Level 2, Low to
  Level 3, Moderate by day 29". The saved image says the same.
- **Links work.** Links to files in the repository follow its default
  branch, so "How to install it" and "Reading your dashboard" no longer open
  a page that is not there.
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
  `/plugin install lvlme --marketplace mark-hallam/lvlme`.
- **Commands**: `/lvlme`, `/lvlme-quick`, `/lvlme-interview`,
  `/lvlme-screen`, `/lvlme-audit` and `/lvlme-dashboard`. **Helper agents**:
  `lvlme:evidence-scout`, `lvlme:market-scout`, `lvlme:role-judge`,
  `lvlme:reviewer` and `lvlme:recruiter-screen`. In Codex, type `$lvlme`.
- **The workspace** setting is `LVLME_HOME`, and the folder is
  `~/lvlme-workspaces/`.
- **The repository** is https://github.com/mark-hallam/lvlme. GitHub
  forwards the old climb address here.

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
