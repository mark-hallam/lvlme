# Climb

From a very low starting score to your dream job, one verified step at a time.

Climb answers one question honestly: **how likely am I to land this kind of
role at these organisations, and what would raise my odds?** Then it runs the
campaign with you. You, or a personal artificial intelligence (AI) agent
working for you, run it on your own computer.

Author: Mark Hallam. Licence: MIT (see `LICENSE`).

## What you get

1. **Your honest odds**, for every open role that fits your goal, from
   evidence, not vibes. Most people start "Very low". That is the point: you
   see the real starting line.
2. **Why**, factor by factor, with every point traced to a source.
3. **A campaign** that turns the gaps into a short, prioritised list of
   actions, re-scored on a schedule, so your effort goes where it actually
   moves the number.
4. **A dashboard** that shows the climb: your measured Day 1, every scored
   day since, the level you are at, and the actions that take you to the next
   level.

Along the way Climb runs:

- **A career interview** that reads your documents first (your CV, short for
  curriculum vitae, your LinkedIn data export, your website), then asks only
  what they cannot answer.
- **Evidence gathering** from the sources you approve: email (read only),
  GitHub, the public web and press, public registers, and your files.
- **Market research**: open roles from public job boards, and sourced facts
  about each organisation.
- **A consistency audit**: do your CV, LinkedIn, website and any official
  forms say the same thing about the same facts?
- **A recruiter screen**: an independent recruiter persona reads your
  materials against real postings, the way a busy screener would.
- **Drafted fixes**: honest wording for anything overstated or mismatched,
  ready for you to apply.

The first example goal is getting hired at a frontier AI lab. The engine does
not care what the goal is: the target organisations, role types and weights
are all settings in one file.

![The demo dashboard on a desktop, light theme](docs/images/dashboard-desktop.png)

<img src="docs/images/dashboard-phone.png" alt="The demo dashboard on a phone, light theme" width="320">

*Screenshots of the fictional demo (Alex Example and three made-up
organisations).*

## Install

You need Python 3.9 or newer (Climb uses only its standard library) and git.
Full details for every agent, and the documentation they follow, are in
[`docs/INSTALL.md`](docs/INSTALL.md).

**Claude Code, one step** (version 2.1.275 or later), once the repository is
published (replace `<github-user>` with its owner):

```text
/plugin install climb --marketplace <github-user>/climb
```

**Claude Code, the simple fallback:** clone the folder into your skills
folder, then start a new session.

```bash
git clone <repository address> ~/.claude/skills/climb
```

**Codex:** clone it into `~/.agents/skills/climb` and type `$climb`, or open
Codex in the folder and it follows `AGENTS.md`.

**Cursor:** open the folder. The rules in `.cursor/rules/` and `AGENTS.md`
load on their own.

Then say **"run Climb"**, or use a command:

| Command | Does |
|---|---|
| `/climb` | Run Climb, or resume today's run. `/climb status` changes nothing and reports. |
| `/climb-interview` | The career interview, first time or an update. |
| `/climb-screen` | The independent recruiter screen. |
| `/climb-audit` | The consistency audit and the public claims audit. |
| `/climb-dashboard` | Rebuild the dashboard. |

In Codex and Cursor, say the same words: "run the Climb interview", and so
on.

## Your privacy

- **Your data never lives in this repository.** The first run creates a
  private workspace folder on your own machine, by default
  `~/climb-workspaces/<goal>`. Only you can open it.
- The scripts refuse to work on a workspace inside this repository, or inside
  any git repository (a version-controlled folder) that has a remote, meaning
  a copy on a server such as GitHub.
- **Every source is opt in and read only.** Climb asks before it reads your
  email, calendar or LinkedIn, and never changes them.
- **Cloud agents see whatever they read.** If you point an online AI agent at
  your workspace, your evidence and contacts go to that service. Decide that
  on purpose. The same goes for scheduling runs in the cloud.
- **Sensitive mode** (on by default) keeps employer names, other people's
  names and salary figures out of the briefing files written for other agents.
- No telemetry. The only network calls are to public job-board APIs
  (application programming interfaces, the feeds job boards publish) in
  `fetch_roles.py`, the web pages you name in `claims_audit.py`, and the
  sources you approve for your agent to read.

Full details: [`method/PRIVACY.md`](method/PRIVACY.md).

## The honesty rules

Most career advice flatters. Climb is built to do the opposite.

- **Evidence or it scores zero.** Every point needs a source: a link, a file,
  an email, or your own answer to an interview question. A claim with no
  source counts as absent and becomes a "verify to unlock" question.
- **A verification ladder.** Evidence is graded `verified`, `corroborated`,
  `self_reported`, `unverified` or `contradicted`. A score can never be higher
  than its best evidence supports. An achievement only you have claimed
  supports at most 1 point out of 5.
- **A separate, sceptical reviewer.** A fresh agent, which never sees the
  campaign's scores or reasoning, scores every point above 2 for itself. The
  lower score stands. Until the review is done, the score counts as 2.
- **Helpers are checked, not trusted.** Helper agents return every finding
  with its source, tagged verified or unverified, and the lead agent opens the
  source of anything that matters before it counts.
- **The maths is a script, not a mood.** Judgements live in files. A
  deterministic script turns them into scores, so the same inputs always give
  the same result, and every change can be traced.
- **The default answer is "unlikely".** Competitive employers reject most
  applicants. The bands start from that fact.
- **No fabrication, no profiling.** It never invents experience, numbers,
  contacts or stories. It never infers or scores protected attributes such as
  age, gender, ethnicity, disability, religion or family status.
- **Nothing public without your yes.** Climb never applies for a job, sends a
  message, posts, accepts an invitation, changes an account or spends money
  on its own. It drafts, in `campaign/drafts/`, for you to read, edit and send
  yourself. If you ask it to make one specific change, such as a drafted
  LinkedIn headline fix, it does that one step only after you say yes to it.

## How a run works

A run has ten stages: intake, evidence, market, judge and audit, review,
score, SWOT and TOWS (strengths, weaknesses, opportunities and threats, and
the strategies that combine them), plan and fixes, report, and a short
message to you. An agent that can start helpers does the independent work in
parallel: one helper per evidence source, one per organisation, judges in
batches, the audits and the recruiter screen at once. Then it joins the
results and passes four gates: findings are checked, the reviewer and the
recruiter screen are independent, nothing is scored before review, and
nothing public happens without your yes.

Runs are daily for the first four weeks, then weekly once you agree. Each run
saves one dated run file, so your progress is a record, not a claim. Details:
[`docs/ORCHESTRATION.md`](docs/ORCHESTRATION.md).

## See it first: the demo

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
```

## By hand, in a terminal

```bash
python3 scripts/init.py --goal "Frontier AI labs"     # creates your private workspace
export CLIMB_HOME=~/climb-workspaces/frontier-ai-labs
python3 scripts/fetch_roles.py                        # open roles from public job boards
python3 scripts/network_map.py --csv ~/Downloads/Connections.csv
python3 scripts/claims_audit.py https://your-site.example/about
python3 scripts/score.py                              # deterministic scoring
python3 scripts/build_dashboard.py                    # report/index.html
python3 scripts/validate.py                           # checks every file
```

Between `network_map.py` and `score.py` there is judgement work: the
interview, recording evidence, the audits, and judging each role against the
rubric. The method files explain each step, and
[`method/RUNBOOK.md`](method/RUNBOOK.md) gives the full run order.

Every script takes `--workspace PATH`. Without it, scripts use
`$CLIMB_HOME`, or the only folder inside `~/climb-workspaces/`.

## The dashboard

`report/index.html` in your workspace: one self-contained page (no external
requests), light by default with a readable dark mode, that works on a phone.

- **The journey**: your best chance today, your level, and a flight-path
  chart. The black line is what was measured, one dot per scored day. From
  today it splits into three paths to the end date: *expected* if you follow
  the plan (each action weighted by its chance of working), *best case* if
  every action lands, and *do nothing*. Diamonds are plan actions on their
  target dates. The green dashed line at 70 is the offer zone.
- **Level up**: the actions that take you to the next level, and your level
  history (see [`docs/LEVELS.md`](docs/LEVELS.md)).
- **What if**: switch any plan action on or off and every number on the page
  updates.
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
never gains eligibility. See [`method/CAMPAIGN.md`](method/CAMPAIGN.md).

For your other agents: `report/for-agents/SUMMARY.md` (plain-text briefing)
and `report/for-agents/dashboard.json` (every number, in JSON, short for
JavaScript Object Notation, a plain-text data format).

## How scoring works, in one paragraph

Each open role is scored 0 to 5 on seven factors: requirements match, proof of
work, warm path (someone inside who vouches for you), organisation-specific
edge, public signal, eligibility and logistics, and application readiness.
Weighted together they give a fit score out of 100, which maps to a chance
band for an interview and for an offer (Very low, Low, Moderate, Good, Strong).
A referral moves the interview band up; a missing hard requirement moves both
down; a cold application caps the offer band at Low. The full rules are in
[`method/RUBRIC.md`](method/RUBRIC.md).

## Project layout

```
SKILL.md  AGENTS.md  README.md  LICENSE  CONTRIBUTING.md
.claude-plugin/  plugin.json and marketplace.json (Claude Code)
skills/     the /climb-interview, /climb-screen, /climb-audit, /climb-dashboard commands
agents/     subagent briefs: evidence-scout, market-scout, role-judge, reviewer, recruiter-screen
.cursor/rules/  Cursor rules
method/     the rules for each stage (rubric, interview, intake, audits, review, campaign, privacy, runbook)
schemas/    JSON Schema files (rules for every workspace file)
scripts/    init, fetch_roles, network_map, claims_audit, consistency_audit,
            score, build_dashboard, validate
templates/  the workspace skeleton that init.py copies, and agent prompts
docs/       INSTALL.md, ORCHESTRATION.md, LEVELS.md, DESIGN.md
examples/   demo-workspace/ (fictional) and build_demo.py
tests/      offline tests: python3 -m unittest discover -s tests
```

Your workspace (private, outside this repository) looks like this:

```
config.json                goal, targets, role types, locations, weights, privacy
intake/answers.md          your interview answers
intake/sources/            exports you supply (LinkedIn data, résumé)
profile/                   evidence.json, network.json, claims-audit.json
market/                    roles/latest.json, roles/snapshots/, orgs.json
eval/                      judgements, profile dimensions, SWOT, outlook, runs/
campaign/                  plan.json, inbox.md, drafts/, weekly/
report/                    index.html, for-agents/
```

## Not in version 0.1

Automatic LinkedIn scraping (it breaks LinkedIn's terms, so use the official
data export instead), automatic applying, salary negotiation, goals other than
jobs, and the Workable and SmartRecruiters job boards (enter those roles by
hand in `market/roles/manual.json`).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).
