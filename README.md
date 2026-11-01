# Climb

From a very low starting score to your dream job, one verified step at a time.

An honest, evidence-based way to answer one question: **how likely am I to land
this kind of role at these organisations, and what would raise my odds?**

Climb is a method plus a few small scripts. You, or a personal
artificial intelligence (AI) agent working for you, run it on your own computer. It:

1. **Estimates your chances** for every open role that fits your goal, from
   evidence, not vibes.
2. **Explains why**, factor by factor, with every point traced to a source.
3. **Turns the gaps into a campaign**: a short, prioritised list of actions,
   re-scored on a schedule, so your effort goes where it actually moves the
   number.

The first example goal is getting hired at a frontier AI lab. The engine does
not care what the goal is: the target organisations, role types and weights
are all settings in one file.

Author: Mark Hallam. Licence: MIT (see `LICENSE`).

## Why you can trust the numbers

Most career advice flatters. This is built to do the opposite.

- **Evidence or it scores zero.** Every point needs a source: a link, a file,
  an email, or your own answer to an interview question. A claim with no
  source counts as absent and becomes a "verify to unlock" question.
- **A verification ladder.** Evidence is graded `verified`, `corroborated`,
  `self_reported`, `unverified` or `contradicted`. A score can never be higher
  than its best evidence supports. For example, an achievement only you have
  claimed supports at most 1 point out of 5.
- **A separate, sceptical reviewer.** A fresh agent, which never sees the
  scorer's reasoning, must agree with every score above 2. Until it does, the
  score counts as 2.
- **The maths is a script, not a mood.** Judgements live in files. A
  deterministic script turns them into scores, so the same inputs always give
  the same result, and every change can be traced.
- **The default answer is "unlikely".** Competitive employers reject most
  applicants. The bands start from that fact.
- **No fabrication, no profiling.** It never invents experience, numbers,
  contacts or stories. It never infers or scores protected attributes such as
  age, gender, ethnicity, disability, religion or family status.

## What it will never do

- Apply for a job.
- Send an email or message, or post anything publicly.
- Change your LinkedIn, website, GitHub or any other account.

Outreach and applications are **drafts only**, saved in `campaign/drafts/` for
you to read, edit and send yourself. Other agents may write to exactly one file
in your workspace: `campaign/inbox.md`.

## Privacy

- **Your data never lives in this repository.** `init.py` creates a private
  workspace folder on your own machine, by default in
  `~/climb-workspaces/<goal>`. Only you can open it.
- The scripts refuse to work on a workspace inside this repository, or inside
  any git repository (a version-controlled folder) that has a remote, meaning
  a copy on a server such as GitHub.
- **Cloud agents see whatever they read.** If you point an online AI agent at
  your workspace, your evidence and contacts go to that service. Decide that
  on purpose.
- **Sensitive mode** (on by default) keeps employer names, other people's
  names and salary figures out of the briefing files written for other agents.
- No telemetry. The only network calls are to public job-board APIs
  (application programming interfaces, the feeds job boards publish) in
  `fetch_roles.py`, and to the web pages you name in `claims_audit.py`.

Full details: [`method/PRIVACY.md`](method/PRIVACY.md).

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

## Quick start

You need Python 3.9 or newer. Nothing else: the scripts use only Python's
standard library.

### Option 1: Claude Code, as a skill

1. Put this repository where Claude Code looks for skills:

   ```bash
   git clone <this repository's address> ~/.claude/skills/climb
   ```

2. Open Claude Code anywhere and say: **"run my career eval"**.

The skill (`SKILL.md`) tells Claude what to do: create your workspace,
interview you, gather evidence, fetch open roles, score, review, plan and build
the dashboard.

### Option 2: Codex, Cursor or another agent

Open this folder in your agent and ask it to follow `AGENTS.md`. It holds the
same procedure in a shorter form and points to the method files.

### Option 3: by hand, in a terminal

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

Between `network_map.py` and `score.py` there is judgement work: answering the
interview questions, recording evidence, and judging each role against the
rubric. The method files explain each step, and
[`method/RUNBOOK.md`](method/RUNBOOK.md) gives the full run order.

Every script takes `--workspace PATH`. Without it, scripts use
`$CLIMB_HOME`, or the only folder inside `~/climb-workspaces/`.

## What you get

`report/index.html` in your workspace: one self-contained page (no external
requests), light by default with a readable dark mode, that works on a phone.
It leads with the climb: your measured Day 1, every scored day since, and
where the plan is expected to take you.

![The demo dashboard on a desktop, light theme](docs/images/dashboard-desktop.png)

<img src="docs/images/dashboard-phone.png" alt="The demo dashboard on a phone, light theme" width="320">

*Screenshots of the fictional demo (Alex Example and three made-up
organisations).*

- **The journey**: your best chance today, a level badge, and a flight-path
  chart. The black line is what was measured, one dot per scored day. From
  today it splits into three paths to the end date: *expected* if you follow
  the plan (each action weighted by its chance of working), *best case* if
  every action lands, and *do nothing*. Diamonds are plan actions on their
  target dates. The green dashed line at 70 is the offer zone.
- **What if**: switch any plan action on or off and every number on the page
  updates. Each switch shows what it adds to your best role and how many roles
  it lifts.
- **Verifiable record**: one chip per scored day. If your workspace is its own
  git repository (a version history, with no remote), each chip also shows the
  saved version that first recorded that day.
- **Views**: Organisations; Path to the top band (if you add
  `eval/ceilings.json`); What moves you; Roles (every role by factor, as a heat
  map); SWOT and TOWS (strengths, weaknesses, opportunities and threats, and
  the strategies that combine them); Plan; Evidence (with your public claims,
  checked); Market.
- **Drill down**: tap any organisation, role, factor, action or piece of
  evidence to see why, in a side pane with breadcrumbs.

The projection is deliberately cautious: each factor can rise only by a capped
amount (`projection_caps` in `campaign/plan.json`), never above 5, and a role
with an eligibility blocker you can't clear never gains eligibility. See
[`method/CAMPAIGN.md`](method/CAMPAIGN.md).

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
method/     RUBRIC.md INTAKE.md SWOT.md CAMPAIGN.md REVIEW.md PRIVACY.md RUNBOOK.md
schemas/    JSON Schema files (rules for every workspace file)
scripts/    init.py fetch_roles.py network_map.py claims_audit.py
            score.py build_dashboard.py validate.py
templates/  the workspace skeleton that init.py copies
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

## Requirements

- Python 3.9 or newer, standard library only.
- No telemetry.
- Network access only in `fetch_roles.py` (public job-board APIs: Greenhouse,
  Ashby and Lever) and `claims_audit.py` (only the addresses you pass).

## Not in version 0.1

Automatic LinkedIn scraping (it breaks LinkedIn's terms, so use the official
data export instead), automatic applying, salary negotiation, goals other than
jobs, and the Workable and SmartRecruiters job boards (enter those roles by
hand in `market/roles/manual.json`).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).
