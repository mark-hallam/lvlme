# Changelog

What changed in each version of LVLme, newest first. A version number is the
`version` in `.claude-plugin/plugin.json`, and a released version also has a
git tag (`v0.2.0` and so on). LVLme was called Climb until 3 November 2026,
so the versions before 0.3.0 carry that name.

**Added** is new, **Changed** works differently and **Fixed** was wrong
before. Nothing here changes how a score is worked out unless it says so.

## 0.7.2 (6 November 2026)

From a real search for senior project roles: no role reached a fit of 70,
and the reason was mostly not the jobs. Fit adds three factors about the
person's campaign (who they know, how findable they are, a tailored CV) that
are the same for every role at an organisation, and a warm path nobody asked
about counted the same as knowing nobody. Fit, the bands and the levels are
unchanged. The full notes are in [LVLme 0.7.2](docs/RELEASE-0.7.2.md).

### Added

- **Job match:** every role now has a job match beside its fit, from the four
  factors judged against the job itself (requirements, proof of work, what the
  organisation values, eligibility and location), with their weights, on 0 to
  100. Use it to find well matched jobs; fit stays the estimate of your chance
  if you applied today. Shown in the role panel and in the agent file.
- **Warm path not asked:** when nobody asked whether you know anyone at an
  organisation, the run says so, the warm path is marked "not asked yet"
  instead of reading as nobody, and the questions to unlock list one
  "Do you know anyone at ...?" per organisation. It still counts as 0 until
  you answer: evidence or zero.

Tests: 704 pass.

## 0.7.1 (5 November 2026)

Fixes from three rounds of independent review of 0.7 (a Claude reviewer and a
Codex reviewer, blind, in a real browser). How a score is worked out did not
change. The full notes are in [LVLme 0.7.1](docs/RELEASE-0.7.1.md).

Tests: 689 pass.

### Changed

- **Goal reached says what it is:** a measured level, not a job offer.
- **One accent:** the switches in Mission control use the same orange as Today.
- **Plainer next level:** when no date is expected, it says so plainly.
- **Phones:** a slimmer level-up banner and no theme switch crowding the header.

### Fixed

- **The demo agrees with itself:** its Friday review now matches the demo
  data, and the goal-reached demo has a Level 3 goal.
- **The demo profile says its example.com source links are made up.**

## 0.7.0 (5 November 2026)

LVLme now works with goals and campaigns only. 0.7.0 has three parts: the
engine (every factor judged twice, a fit range, LVLme quick retired as a
product), the journey (set a goal, a starting line, a Today screen, a weekly
rhythm, level-up events, outcomes you can choose to share) and a proof
profile. The scoring rules are now version 1.2. **This release changes how a
score is worked out**: see Changed.

Tests: 687 pass.

**Known items.** Judging twice did not make scores steadier in the three-run
test below (26, 24 and 19 on the same CV); nothing in this release claims
otherwise. Today, Mission control and the result page now share one orange
accent. Mission control keeps its aviation labels for the chart; Today, the
first thing you see, does not use them. Tested on macOS; Windows is not tested
yet.

### Added

- **Set a goal.** `scripts/goal.py` and setup ask for the role, the
  organisations, where and by when. LVLme tests the goal against the starting
  line and, when no plan reaches it in time, proposes a stepping stone with the
  reason. You choose.
- **The starting line.** The first result gives your level, the fit range and
  the date the plan is expected to reach the next level, or says plainly that
  no plan gets there yet and what is missing. A first run judges only the best
  few roles so it comes in about 15 minutes; the rest are judged on the next
  runs and Today says what is still being checked.
- **Today first.** The dashboard opens on Today in plain words: your level, one
  sentence on where you stand (with "fit about X to Y" when a role was judged
  twice), the one move for today and the next level date. The full dashboard
  (Mission control) is one tap away.
- **A weekly rhythm.** A Monday plan note and a Friday review under
  `campaign/weekly/`, and a count of weeks in a row with real evidence.
- **Level-up and goal-reached events** in `eval/levels.json`, marked on Today,
  with a share card that shows level and dates and no names.
- **Outcomes you can share, if you choose.** `scripts/outcomes.py` writes a
  numbers-only export (scores, bands, rubric version, role family, outcome; no
  CV, no names) after a plain consent screen. LVLme sends nothing anywhere.
- **A proof profile.** `scripts/proof_profile.py` builds
  `report/profile/index.html`, a clean page of your goal, your level history
  and only the claims checked at verified or corroborated level, each with its
  public source link. It refuses to write the page if it would contain an
  email address, a phone number, a folder path, a private or local link or an
  unchecked claim. Private by default; see
  [the proof profile](docs/PROOF-PROFILE.md).
- **Every role shows a fit range.** Each role in the run file has `fit_low`
  and `fit_high` beside `fit`, and so does each organisation's best role. They
  are the fit with every factor at its lower judging and at its higher one. A
  factor judged once has a range of one fit, so an older judgement file still
  works.
- **`judgings` on each judged factor.** Requirements match, proof of work and
  organisation edge are judged twice, independently, and both scores are
  recorded as `judgings: [first, second]` in `eval/judgements.json` and in the
  run file.
- **A test that keeps quick gone.** `tests/test_packaging.py` fails if a quick
  skill, script, schema, demo or link comes back.

### Changed

These are the scoring rules version 1.2.

- **Judge twice and average.** The agent judges D1, D2 and D4 twice, with two
  helper agents or two passes that cannot see each other. Scoring caps each
  judging on its own, then averages them to a whole point. A half always
  rounds down: 3 and 4 give 3. A doubtful half point is not given. The
  blind review and the rule that keeps a score when only the judging agent
  changed work as before.
- **A `score` beside `judgings` is the settled score.** After a blind review
  settles a factor, the `score` written counts and the judgings only set the
  range.
- **Helper counts are doubled for judges.** `run_plan.py` now counts two
  judges per batch of roles, so a first run of about 300 roles starts about
  100 helper agents, not about 40.
- **Plain words in what the person reads first.** The run message uses fit,
  chance, level and next level, and the score summary names the interview and
  offer chance and the fit range.
- **A run says how much it varied.** The score summary prints the fit range
  for any role judged twice.
- **The demo is rebuilt** under the new rules, with one role judged twice.
- **The first pass stays as an internal path** for the app's goal-first first
  run: `scripts/quick.py` (`new`, `review-items`, `build`, `promote`),
  `scripts/quick_posting.py`, `scripts/_promote.py`, `schemas/quick.schema.json`
  and `eval/quick.json` all work as before, with their messages saying "first
  pass". The agent instructions moved from `skills/lvlme-quick/SKILL.md` to
  `method/FIRST-PASS.md`. The shared page style moved to
  `scripts/_page_html.py`. The demo CV also lives in
  `examples/demo-workspace/intake/sources/`.
- **Measured spread.** Three Codex runs of the same CV and job under the new
  rules gave best fits of 26, 24 and 19. We do not claim the score is steadier;
  the range now shows the disagreement. See the release notes.
- **Version 0.7.0.**

### Removed

- **LVLme quick, as a product.** The `/lvlme-quick` command and skill, its
  result page on the demo site, its screenshots and every page of the docs
  that described it. Someone who says "run LVLme quick" is told that LVLme now
  works with a goal and is offered to set one. Nothing the person reads
  offers it any more.

## 0.6.3 (5 November 2026)

Fixes from four end-to-end tests with real AI agents (a stranger installing
from GitHub, three simulated weeks of a campaign, and the same CV scored
again and again to measure how steady the score is), and the scoring rules
version 1.1. **This release changes how a score is worked out**: the rules
are listed under Changed. The full notes are in
[LVLme 0.6.3](docs/RELEASE-0.6.3.md).

Tests: 591 pass.

### Changed

These are the scoring rules version 1.1.

- **A one-point disagreement uses the reviewer's score.** When the first
  judge and the blind reviewer differ by one point, the reviewer's score
  counts, within the evidence and other caps. A bigger difference still
  waits for a tie-break, as before. The old rule counted it as 2, lower than
  either of them gave.
- **Eligibility has written anchors.** D6 now has a table, including "the
  employer says it sponsors visas" (a possible route, scored 2, never a
  confirmed one) and what to do in LVLme quick when there is no location rule.
- **Which links count as checked.** A link counts at the verified or
  corroborated level only if a stranger can open it on the public web without
  signing in. Local, private network and file links count as self-reported.
  Documents, emails, exports and references are not links and keep their level.
- **A new lowest chance band, Almost none,** for an interview below 15 and
  an offer below 25, so a weak fit and an unrelated one no longer read the
  same. The five fit levels did not change, and applications already
  recorded keep the bands they were given.
- **Show it or Build it.** Every gap and every LVLme quick fix says whether
  the proof is missing (Show it, usually days) or the skill is (Build it,
  usually weeks or months). LVLme quick lists Show it fixes first; which
  fixes are shown, and their points, are worked out as before.
- **A score holds when only the judging AI changed.** If a different AI
  agent judges a role again and the evidence it cites is unchanged, the
  previous score stands and the run says so. New evidence means the new
  score counts.

### Fixed

- **Plain words start LVLme quick and the other skills** in Claude Code
  ("run LVLme quick"), not only a typed slash command. Autopilot and public
  still need the typed command, because they set up schedules and publish.
- **The autopilot timer line can run.** It names the full path to Claude
  Code and Python and the commands the morning run may use.
- **`--workspace` works before or after the sub-command** in every script.
- **The same job title in different cities is not a repost.**
- **A morning when the job boards cannot be reached says so,** and keeps
  the date of the last real data instead of looking like a normal day.
- **Progress made after the morning note is reported** in the next note.
- **The morning run refreshes events** as well as roles.
- **Small fixes:** clone commands are pinned to the release; the hard
  requirement line reads properly; the weekly note rebuilds the dashboard for
  the date it was given; the applications list takes a date and shows the
  organisation's name; a thank-you draft is named thankyou; autopilot and
  doors status can print JSON; late plan actions are marked late; the open
  command is the full path; run_plan prints both the full and the light run.

## 0.6.2 (5 November 2026)

A first-run polish release after a second new-user test and five rounds of
independent design review (Claude, Codex and Grok, each blind). It makes the
first answer a stranger gets agree with itself everywhere: in the chat, on
the result page and on the dashboard. How a score is worked out did not
change. The full notes are in [LVLme 0.6.2](docs/RELEASE-0.6.2.md).

Tests: 546 pass.

### Fixed

- **The blind review is read whichever way the reviewer writes it.** A
  reviewer that wrote the factor as "D1 Requirements match" or by its name
  alone was not read, so the result said "Waiting for the reviewer" next to
  the reviewer's own score. `quick.py` now reads the code, the name or both,
  and a reply it still cannot read is said plainly ("no readable score ...
  counts as 2"), never shown as waiting.
- **A promoted campaign keeps its role.** `quick.py promote` made the role
  family's keyword from the title without its punctuation, so "Customer
  Success Manager, Commercial" matched nothing and the first job-board
  refresh after promoting dropped the campaign's only role. The keyword now
  matches the title's own words in order. The dashboard's market table also
  counts the promoted role before any job-board summary exists.
- **A promoted campaign keeps the blind review's disagreement.** It is
  written to `eval/reviews/<date>.json`, waiting for a tie-break, so the
  dashboard says the reviewer disagreed (first score 3, reviewer 2) instead
  of "Waiting for the reviewer".
- **The saved posting keeps the visa and pay lines** that the job board
  gives apart from the description. Agents read `posting.md`; one told the
  person the posting did not say whether the role sponsors visas.
- **Every fix the agent suggested is accounted for.** The result page names
  every left-out fix with its reason (including "it is not in the top 3"),
  and names the factor that cannot move in a few months, so an agent cannot
  tell the person the page lists something it does not.
- **The dashboard's no-script page** shows the date it was scored.

### Changed

- **The result page's top card** says why in short (the three factors with
  the most points still to win), what to do first, and who judged. The fit
  bar says the fixes total and the "up to" range are two different cases,
  and the fixes card says where the next band starts when the fixes do not
  reach it.
- **One status per factor**, for example "First score 3, blind reviewer 2:
  counts as 2", and a plain review summary. The page says who did the blind
  review when the agent records it (new optional `reviewed_by` in
  `eval/quick.json`), and when it was the same model as the first judge, in
  a fresh session. It also explains how a factor's fit points are worked
  out, what E01 and the other evidence ids are, what the AI provider sees,
  and folds the inputs fingerprint into Technical details.
- **Honest about run to run differences.** The result page, the dashboard
  and the docs say that another AI agent, or another run of the same one,
  can judge the same evidence differently, often by a few fit points; the
  maths after the judging is the same.
- **Dashboard.** Altitude (fit) and Flight level (chance) say what they are.
  Do next keeps one number per action and explains it with a worked example
  ("8 points if it works, at about a 30% chance, is 2.4 expected") and a
  tooltip; the promote message says so too. Do next ends with the career
  interview while the campaign has no outlook, and the outlook and the empty
  strengths and risks point there, so there is one list of next steps.
  Biggest unlocks says its numbers have no time limit; What is missing
  explains its rows; summary tiles say when they show a plan mode; Campaign
  progress says its targets can be changed. The theme switch has Auto, the
  new default, which follows the device. On a phone the title wraps and the
  pending tick is a full-size tap target.
- **The quick skill.** Agents never write or edit the blind review
  themselves (if they cannot start a separate reviewer, the scores wait for
  one), record who reviewed, write notes in plain words with no file paths,
  paste the result as it is, ask about work rights as yes or no, and open no
  page beyond the posting and up to three links in the CV.
- **Docs.** LVLme quick asks at most two short questions (not one), and the
  first message can carry the job link and where the CV is. If the
  `/lvlme-quick` command is not found right after installing, start a new
  Claude Code session. Cursor, other agents, Linux and Windows are described
  as not tested yet, without predicting that they work. Codex users say "run
  LVLme quick".

## 0.6.1 (5 November 2026)

A fix release after a new-user test: we installed LVLme the way a new person
would, followed only the public instructions, and fixed what got in the way.
How a score is worked out did not change. The full notes are in
[LVLme 0.6.1](docs/RELEASE-0.6.1.md).

Tests: 532 pass.

### Fixed

- **Job links on Python from python.org.** That Python has no website
  certificates until its "Install Certificates" step has been run, so every
  job link failed with "Could not open the link", and the full campaign said
  "every job board failed". Now, on a certificate error, the scripts that
  read links try once more with the Mac's own certificate file
  (`/etc/ssl/cert.pem`, or the certifi package if it happens to be
  installed). If that fails too, they say in one plain line what to run
  ("Install Certificates.command" in Python's Applications folder), and
  LVLme quick adds that you can paste the job ad text instead. Certificate
  checking is never turned off. The shared code is `scripts/_certs.py`.
- **Climb from here keeps the quick fixes.** `quick.py promote` now writes
  the fixes the quick result showed into `campaign/plan.json` as the plan's
  first open actions, each raising its factor for that role to the fix's
  target, so the new dashboard no longer says "No open actions yet". Effort
  and chance are first estimates you can change.
- **Climb from here names the role.** Its message says the role's title and
  organisation (for example "Deployment Program Manager at Globex Labs"), not an
  internal code, and the agent summary (`report/for-agents/SUMMARY.md`) no
  longer repeats the goal.
- **LVLme quick follows `LVLME_HOME`** (the setting for where your files
  live), as the rest of LVLme does: when it is set, quick results go in a
  `quick/` folder next to the workspace it names. When both
  `~/lvlme-workspaces` and the older `~/climb-workspaces` exist, the scripts
  say once which one they use, so a campaign in the old folder is never
  dropped without a word.
- **Which AI judged.** Different AI agents can judge the same evidence
  differently (in the test, one gave a fit of 20 and another 12 for the
  same CV and job). `eval/quick.json` and `eval/judgements.json` take an
  optional `judged_by` (the agent, and the model when known), and the quick
  result page, the dashboard and the agent summary say which one judged, or
  that it was not recorded. The skill tells agents to fill it in.
- **Install guide.** Claude Code's download option now installs from your
  own copy of the folder as a local marketplace, so the main `/lvlme`
  command is listed (a copy cloned straight into the skills folder listed
  only the nine other commands). For Codex, run the exact `git clone`
  command: a skill installer copies only part of the folder, and the
  instructions now say how to repair a partial copy. The Claude chat section
  lists all ten skills, not six. Cursor and other agents that run commands
  should work but are not tested yet, and the docs now say so.
- **Agents ask first.** `AGENTS.md` starts its hard rules with: stop and wait
  for the person's yes before each install or run, even when they asked to
  be set up.
- **Release notes link the changelog by its full address**, so the link
  works on the GitHub release page. The 0.4.0, 0.5.0 and 0.6.0 notes are
  fixed too.

## 0.6.0 (4 November 2026)

From plan to people: LVLme now finds the events and programmes where you can
meet the people who hire, checks its own odds against what happened to your
applications, and gets you ready for the conversations that follow, with a
research pack for each target, an interview story bank, practice and
debriefs, help building in public, an offer checklist, and an import from
career-ops. The full notes are in [LVLme 0.6.0](docs/RELEASE-0.6.0.md).

Tests: 499 pass.

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
- **Offer help.** `scripts/offer.py <application>` writes a checklist for an
  application at Interview or Offer: the pay range the posting advertised
  (only when it published one) beside what you say you were offered, and what
  to ask the employer and a lawyer before signing. A checklist, not advice:
  it never says an offer is fair or safe to sign.
- **Build in public.** `/lvlme-public` and `scripts/public.py` help you show
  your work steadily: ideas from what you finished that is worth sharing
  (never private work, and no one named without their yes), a draft brief
  with only checked facts and your own voice rules (`config.json`
  `public.voice`), and a record of what you posted and what it led to. A new
  card counts posts a week against your own target over the last four weeks,
  and the weekly note says how this week is going. A post counts as proof
  only once its link is opened and checked: then it becomes a verified public
  signal. LVLme drafts; you post. It never posts.
- **Practise before an interview, debrief after.** `/lvlme-practice` builds
  a question set for one role from its posting's hard requirements, the story
  themes and questions already asked there, suggests which of your stories
  fits each, and gives feedback on structure and evidence, never a script.
  `/lvlme-debrief` records a real interview's questions, each rated strong,
  solid or gap (`scripts/practice.py record --real`), moves the application
  to Interview, and a theme you found hard shows as "Practise this" on the
  Story bank card. Both refuse while an interview is happening.
- **Import from career-ops.** `scripts/import_career_ops.py --from <folder>`
  reads a career-ops folder, read only, and brings in its applications with
  their status history, contacts at your target organisations (name, company
  and title only, at stage Talked) and its interview stories, all marked as
  imported. `--dry-run` shows what it would bring first. Importing again
  never makes a second copy and picks up a changed stage. Tested against
  career-ops' own tracker and row-splitting test files (version 1.38.0).
- **Interview story bank.** Your best true stories, in your words, in
  `profile/stories.json`: each in the STAR shape (situation, task, action,
  result) with what you would do differently, the evidence behind it and the
  interview themes it answers. `scripts/stories.py add` records one (the
  career interview's stories go in at the end of the interview), `gaps` lists
  the themes with no story backed by evidence, and `plan` turns a gap into a
  plan action. A new Story bank card shows every theme's status. Themes are
  inferred from common interview guidance and can be replaced in
  `config.json` (`stories.themes`). LVLme never writes a story for you.
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
