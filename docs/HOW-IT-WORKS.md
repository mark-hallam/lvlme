# How LVLme works

The README is the front door. This page holds the detail: the campaign, the honesty rules, privacy, the dashboard, the demo,
running the scripts by hand, and where everything lives.

LVLme runs on your own computer, through an artificial intelligence (AI) agent
such as Claude Code or Codex (Cursor and other agents that run commands should
work but are not tested yet). The agent does the judging; the Python
scripts only do the arithmetic, so without an agent every role scores zero.

## The full campaign

It answers one question honestly: how likely am I to land this kind of role at
these organisations, and what would raise my odds? Then it runs the campaign
with you.

1. **Your honest odds**, for every open role that fits your goal, from
   evidence, not vibes. You may well start at "Very low" or "Almost none". That is the point: you
   see the real starting line.
2. **Why**, factor by factor, with every point traced to a source.
3. **A campaign** that turns the gaps into a short, prioritised list of
   actions, re-scored on a schedule, so your effort goes where it moves the
   number.
4. **A dashboard** that shows the climb: your measured Day 1, every scored day
   since, the level you are at, and the actions that take you to the next
   level.

Along the way it runs:

- **A career interview** that reads your documents first (your CV, your
  LinkedIn data export, your website), then asks only what they cannot answer.
  Its first message is short: three facts from your CV to confirm, which
  organisations you want, and a request for your LinkedIn data export. It
  asks about US export control or a security clearance only when an open
  role needs one.
- **Evidence gathering** from the sources you approve: email (read only),
  GitHub, the public web and press, public registers, and your files.
- **Market research**: open roles from public job boards, and sourced facts
  about each organisation.
- **Doors**: upcoming events, conferences, communities and programmes where
  people from your target organisations will be, each with its date, place
  and source, and one step from becoming a plan action. You register
  yourself.
- **A consistency audit**: do your CV, LinkedIn, website and any official
  forms say the same thing about the same facts?
- **A recruiter screen**: an independent recruiter persona reads your
  materials against real postings, the way a busy screener would.
- **Drafted fixes**: honest wording for anything overstated or mismatched,
  ready for you to apply.

The first example goal is getting hired at a frontier AI lab. The engine does
not care what the goal is: the target organisations, role types and weights
are all settings in one file. A new workspace starts with your goal and no
organisations; the interview's first message asks for yours (or edit
`config.json`).

### A run, stage by stage

A run has ten stages: intake, evidence, market, judge and audit, review,
score, SWOT and TOWS (strengths, weaknesses, opportunities and threats, and
the strategies that combine them), plan and fixes, report, and a short
message to you. An agent that can start helpers does the independent work in
parallel: one helper per evidence source, one per organisation, judges in
batches, the audits and the recruiter screen at once. Then it joins the
results and passes four gates: findings are checked, the reviewer and the
recruiter screen are independent, nothing is scored before review, and
nothing public happens without your yes.

Runs are weekly, plus a run whenever something changes (an action done, new
evidence, a new export). Scores only move when evidence changes. Each run
saves one dated run file, so your progress is a record, not a claim. Details:
[`ORCHESTRATION.md`](ORCHESTRATION.md).

### What a run uses

A full run starts many helper agents: about 100 on a first run for a goal
with around 300 open roles (two independent role judges per batch, plus scouts and
reviewers). That is a noticeable share of an AI plan's usage, so check your
plan's limits before you schedule runs.

## How scoring works

Each open role is scored 0 to 5 on seven factors: requirements match, proof of
work, warm path (someone inside who vouches for you), organisation-specific
edge, public signal, eligibility and logistics, and application readiness.
Weighted together they give a fit score out of 100, which maps to a chance
band for an interview and for an offer (Almost none, Very low, Low, Moderate, Good, Strong).
A referral moves the interview band up; a missing hard requirement moves both
down; a cold application caps the offer band at Low. The full rules are in
[`method/RUBRIC.md`](../method/RUBRIC.md).

## The honesty rules

Most career advice flatters. LVLme is built to do the opposite.

- **Evidence or it scores zero.** Every point needs a source: a link, a file,
  an email, or your own answer to an interview question. A claim with no
  source counts as absent and becomes a "verify to unlock" question.
- **A verification ladder.** Evidence is graded `verified`, `corroborated`,
  `partially_verified`, `self_reported`, `unverified` or `contradicted`. A
  score can never be higher than its best evidence supports. An achievement
  only you have claimed supports at most 1 point out of 5; one that is only
  partly checked never supports more than corroborated evidence would.
- **A separate, sceptical reviewer.** A fresh agent, given only the rubric,
  the evidence and the postings and told not to open the campaign's scores or
  reasoning, scores every point above 2 for itself. In the full campaign,
  where it disagrees, a second fresh reviewer scores it too and the middle of
  the three stands, with every dispute logged. Until the review is done, the
  score counts as 2.
- **Helpers are checked, not trusted.** Helper agents return every finding
  with its source, tagged verified or unverified, and the lead agent opens the
  source of anything that matters before it counts.
- **The maths is a script, not a mood.** Judgements live in files. A
  deterministic script turns them into scores, so the same judgements always
  give the same score, and every change can be traced. Different AI agents
  (for example Claude and Codex) can judge the same evidence differently, and
  so can two runs of the same agent, often by a few fit points, so the result
  page and the dashboard name which agent and model judged.
- **The default answer is "unlikely".** Competitive employers reject most
  applicants. The bands start from that fact.
- **No fabrication, no profiling.** It never invents experience, numbers,
  contacts or stories. It never infers or scores protected attributes such as
  age, gender, ethnicity, disability, religion or family status.
- **Nothing public without your yes.** LVLme never applies for a job, sends a
  message, posts, accepts an invitation, changes an account or spends money
  on its own. It drafts, in `campaign/drafts/`, for you to read, edit and send
  yourself. If you ask it to make one specific change, such as a drafted
  LinkedIn headline fix, it does that one step only after you say yes to it.

## Your privacy

- **Your data never lives in this repository.** The first run creates a
  private workspace folder on your own machine, by default
  `~/lvlme-workspaces/<goal>`.
  Only you can open it.
- The scripts refuse to work on a workspace inside this repository, or inside
  any git repository (a version-controlled folder) that has a remote, meaning
  a copy on a server such as GitHub.
- **Every source is opt in and read only.** LVLme asks before it reads your
  email or calendar, and never changes them. It never opens LinkedIn itself
  (automated access breaks LinkedIn's terms): it works from LinkedIn's
  official data export and what you paste, and you apply any profile fixes.
- **Helpers cannot send.** In Claude Code the helper agents that search the
  web are limited to tools that read files and fetch public pages. Email is
  read only by the main agent, in the session you are watching, where your
  agent still asks before any send. Text in an email or a page is treated as
  data, never as an instruction.
- **Your AI agent's provider sees what the agent reads.** LVLme's files stay
  on your computer, but your agent's provider (for example Anthropic for
  Claude Code) receives whatever the agent reads in order to process it,
  under that provider's data terms. The same goes for runs you schedule in
  the cloud.
- **Sensitive mode** (on by default) keeps employer names, other people's
  names and salary figures out of the briefing files written for other agents.
- No telemetry. The only network calls are to public job-board APIs in
  `fetch_roles.py`, the public event calendars you name in `fetch_doors.py`
  (never Meetup, Eventbrite or LinkedIn), the one posting link a first pass reads (`quick_posting.py`), the web pages you name in `claims_audit.py`, and the
  sources you approve for your agent to read.

Full details: [`method/PRIVACY.md`](../method/PRIVACY.md).

## The dashboard

`report/index.html` in your workspace: one self-contained page (no external
requests), light by default with a readable dark mode, that works on a phone.
For a plain-English tour of each number and what to do first, see
[Reading your dashboard](for-you/READING-YOUR-DASHBOARD.md).

![The demo dashboard on a desktop, light theme](images/dashboard-desktop.png)

<img src="images/dashboard-phone.png" alt="The demo dashboard on a phone, light theme" width="320">

- **The journey**: your best match today, your level, and a flight-path
  chart. The black line is what was measured, one dot per scored day. From
  today it splits into three paths to the end date: *expected* if you follow
  the plan (each action weighted by its chance of working), *best case* if
  every action lands, and *do nothing*. Diamonds are plan actions on their
  target dates. The green dashed line at 70 is the offer zone.
- **Level up**: the actions that take you to the next level, and your level
  history (see [`LEVELS.md`](LEVELS.md)).
- **What if**: switch any plan action on or off and every number on the page
  updates.
- **Warm paths**: under Do next, one small strip per organisation showing how
  far your contacts there have come (followed, talked, connected, knows your
  work, would refer). It is progress only and changes no score: your warm
  path score moves when the evidence does. Tap an organisation to see each
  contact's stage and next step (names stay hidden unless you opt in).
- **Doors**: the next events, programmes and communities where people from
  your targets will be, soonest first, with why each one matters. Ask your
  agent to add one to your plan.
- **Build in public**: posts a week against your own target for the last
  four weeks, ideas from what you finished that are worth sharing, drafts
  waiting, and what you posted and what it led to. LVLme drafts; you post. A
  post counts as proof once its link is checked.
- **Story bank**: your best true stories for interviews, in your words, in
  the STAR shape (situation, task, action, result), each linked to its
  evidence. The card shows which common interview themes have a story backed
  by evidence, which need backing and which have none yet; a gap can become a
  plan action. A theme you found hard in a real interview (from a debrief)
  says "Practise this".
- **Research packs**: one page per target organisation (report/research/),
  opened from the organisation's detail: what it is building, recent news,
  offices, the teams hiring, its events and programmes, and its rules on AI
  for candidates. Every line has its source and date, and a line nobody has
  checked yet says so.
- **How right has LVLme been?**: for each band, the applications you sent,
  how many have a result, and how many led to an interview or an offer,
  beside public figures (Ashby, 2025) and a blend of the two. A band's rate
  shows after 5 results and the ranking check after 10. It checks LVLme and
  changes no score.
- **Verifiable record**: one chip per scored day. If your workspace is its own
  git repository (a version history, with no remote), each chip also shows the
  saved version that first recorded that day.
- **Views**: Organisations; Path to the top band; What moves you; Roles (every
  role by factor, as a heat map); SWOT and TOWS; Plan; Evidence (with your
  public claims, checked); Market.
- **Drill down**: tap any organisation, role, factor, action or piece of
  evidence to see why.

The projection is deliberately cautious: each factor can rise only by a capped
amount, never above 5, and a role with an eligibility blocker you can't clear
never gains eligibility. See [`method/CAMPAIGN.md`](../method/CAMPAIGN.md).

For your other agents: `report/for-agents/SUMMARY.md` (plain-text briefing)
and `report/for-agents/dashboard.json` (every number, in JSON, short for
JavaScript Object Notation, a plain-text data format).

## See it first: the demos

`examples/demo-workspace/` is a complete, built example for a **fictional**
person, Alex Example, who targets three made-up organisations (Acme AI, Globex
Labs and Initech Robotics). Nothing in it describes a real person or a real
company's hiring.

Open `examples/demo-workspace/report/index.html` in your browser, or rebuild
it:

```bash
python3 scripts/build_dashboard.py --workspace examples/demo-workspace
```

Rebuild the whole demo from its inputs (offline):

```bash
python3 examples/build_demo.py
python3 examples/build_demo_site.py
```

The last one copies the demo dashboard into `docs/demo/`, with an index page
that introduces it: a static folder that works opened from disk or served
as a website. It copies a page only from a workspace whose `config.json` says
`"fictional": true`, so a real dashboard can never end up there.

## By hand, in a terminal

The full campaign:

```bash
python3 scripts/init.py --goal "Frontier AI labs" --example frontier-ai-labs   # private workspace from the example
export LVLME_HOME=~/lvlme-workspaces/frontier-ai-labs
python3 scripts/fetch_roles.py                        # open roles from public job boards
python3 scripts/fetch_doors.py                        # events and programmes (public calendars you name)
python3 scripts/import_career_ops.py --from ~/career-ops --dry-run   # what an import from career-ops would bring
python3 scripts/network_map.py --csv ~/Downloads/Connections.csv   # optional: needs your LinkedIn export
python3 scripts/claims_audit.py https://your-site.example/about
python3 scripts/score.py                              # deterministic scoring
python3 scripts/build_dashboard.py                    # report/index.html
python3 scripts/validate.py                           # checks every file
```

Between `network_map.py` and `score.py` there is judgement work: the
interview, recording evidence, the audits, and judging each role against the
rubric. The method files explain each step, and
[`method/RUNBOOK.md`](../method/RUNBOOK.md) gives the full run order.

Every campaign script takes `--workspace PATH`. Without it, scripts use
`$LVLME_HOME`, or the only folder inside `~/lvlme-workspaces/`. The names from
before Climb became LVLme, `$CLIMB_HOME` and `~/climb-workspaces/`, still work
(see [Coming from Climb](INSTALL.md#coming-from-climb)).

When a script cannot go on, it stops with one plain line that starts `lvlme:`,
never a page of Python details. The line says what is wrong and what to do:

```text
lvlme: No workspace found. Run scripts/init.py first, or pass --workspace PATH, or set LVLME_HOME.
lvlme: ~/lvlme-workspaces/acme/config.json: not valid JSON (line 12, column 5: Expecting value). Fix that spot in the file, then run this again.
lvlme: cv.txt: no CV text file at this path. Check the path, then run this again.
No target organisations yet. Say to your agent: run the LVLme interview.
```

If the line says "unexpected error", run
`python3 scripts/validate.py` first: it lists every file that breaks the rules.
If that says Valid, it is a bug in LVLme. Put `LVLME_DEBUG=1` in front of the
command to see the full details, and include them when you report it.

## Commands

| Command | Does |
|---|---|
| `/lvlme` | Run LVLme, or resume today's run. `/lvlme status` changes nothing and reports. |
| `/lvlme-interview` | The career interview, first time or an update. |
| `/lvlme-screen` | The independent recruiter screen. |
| `/lvlme-audit` | The consistency audit and the public claims audit. |
| `/lvlme-dashboard` | Rebuild the dashboard. |

With the plugin, these short names work, and each also has a full name with
the plugin prefix (`/lvlme:lvlme-interview`). In Codex and other agents, say
the same words: "run the LVLme interview", and so on. Install details for every agent:
[`INSTALL.md`](INSTALL.md). LVLme is tested on macOS; the scripts should work
on Linux, and Windows is untested.

## Project layout

```
SKILL.md  AGENTS.md  README.md  LICENSE  CONTRIBUTING.md
.claude-plugin/  plugin.json and marketplace.json (Claude Code)
skills/     the /lvlme-interview, /lvlme-screen, /lvlme-audit, /lvlme-dashboard commands
agents/     subagent briefs: evidence-scout, market-scout, role-judge, reviewer, recruiter-screen
.cursor/rules/  Cursor rules (not tested yet)
method/     the rules for each stage (rubric, interview, intake, audits, review, campaign, privacy, runbook)
schemas/    JSON Schema files (rules for every workspace file)
scripts/    init, fetch_roles, fetch_doors, doors, applications, stories, practice, public, offer, import_career_ops, network_map,
            claims_audit, consistency_audit, score, build_dashboard, validate
templates/  the workspace skeleton that init.py copies, and agent prompts
docs/       INSTALL.md, HOW-IT-WORKS.md, ORCHESTRATION.md, LEVELS.md, DESIGN.md,
            for-you/ (guides for people who are not technical), demo/ (the static demo folder)
examples/   demo-workspace/ (fictional), build_demo.py, build_demo_site.py
tests/      offline tests: python3 -m unittest discover -s tests
```

Your workspace (private, outside this repository) looks like this:

```
config.json                goal, targets, role types, locations, weights, privacy
intake/answers.md          your interview answers
intake/sources/            exports you supply (LinkedIn data, résumé)
profile/                   evidence.json, network.json, claims-audit.json
market/                    roles/latest.json, roles/snapshots/, orgs.json, doors.json
eval/                      judgements, profile dimensions, SWOT, outlook, runs/
campaign/                  plan.json, warm-paths.json, inbox.md, drafts/, weekly/
report/                    index.html, for-agents/
```

## Not in LVLme yet

Automatic LinkedIn scraping (it breaks LinkedIn's terms, so use the official
data export instead), automatic applying, salary negotiation, and goals other
than jobs. The full campaign reads Greenhouse, Ashby, Lever, Workday,
SmartRecruiters and Workable boards; roles from any other careers site go in
by hand in `market/roles/manual.json`.
