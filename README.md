# Climb

**Honest odds for the job you want, checked by a second opinion, and the steps that raise them.**

![Climb quick's answer for one job: a low chance of an interview and a very low chance of an offer, in plain words (fictional demo)](docs/images/quick-result-hero.png)

Install in Claude Code:

```text
/plugin install climb --marketplace mark-hallam/climb
```

Then say: **run Climb quick**, and paste a job link.

In about five minutes you get honest odds for that one job. Codex and Cursor
work too (see [Install](#install)).

## What you get

**First, the quick answer.** Give Climb one job posting (a link from
Greenhouse, Ashby, Lever or most careers pages, or the posting text) and your
CV. It:

- reads the posting, and turns your CV into a few facts, each marked with how
  far it can be trusted (a CV line alone is "self-reported");
- asks one yes or no question: do you know someone there who has seen your
  work?
- scores five factors with the same rules and maths as the full campaign;
- has a second agent score every point above 2 blind, without seeing the
  first scores, and shows you where the two disagree;
- gives you one page: your chance of an interview and of an offer in plain
  words, one line per factor with the evidence behind it, and the three fixes
  that would raise your odds most, each with a next step.

It gives fixes and a brief, never application answers: you write those
yourself.

**Then, if you want it, the full campaign.** Say **run Climb**. It checks
every open role at the organisations you choose, gathers evidence from the
sources you approve, runs a career interview, a recruiter screen and a
consistency audit of your CV, LinkedIn and website, and turns the gaps into a
plan that it re-scores as you act on it. A dashboard shows the climb:

![The full campaign's dashboard, light theme (fictional demo)](docs/images/dashboard-desktop.png)

*Both screenshots are the fictional demo: Alex Example and made-up
organisations.*

## Install

You need an AI agent (Claude Code, Codex or Cursor), Python 3.9 or newer
(Climb uses only its standard library) and git. Climb is tested on macOS; the
scripts should work on Linux, and Windows is untested.

- **Claude Code** (version 2.1.275 or later): the one line above. Or clone it
  into your skills folder and start a new session:
  `git clone https://github.com/mark-hallam/climb ~/.claude/skills/climb`
- **Codex:** clone it into `~/.agents/skills/climb` and type `$climb`, or open
  Codex in the folder (it follows `AGENTS.md`).
- **Cursor:** open the folder. The rules in `.cursor/rules/` and `AGENTS.md`
  load on their own.

Every agent, step by step: [`docs/INSTALL.md`](docs/INSTALL.md).

| Command | Does |
|---|---|
| `/climb-quick` | Honest odds for one job, from a link and your CV, in about five minutes. |
| `/climb` | The full campaign, or resume today's run. `/climb status` reports and changes nothing. |
| `/climb-interview` | The career interview, first time or an update. |
| `/climb-screen` | The independent recruiter screen. |
| `/climb-audit` | The consistency audit and the public claims audit. |
| `/climb-dashboard` | Rebuild the dashboard. |

With the cloned folder, use the prefixed name (`/climb:climb-quick`) or the
words after `/climb` (`/climb quick`). In Codex and Cursor, say the words:
"run Climb quick".

**What a run uses.** Climb quick starts at most one helper agent, the blind
reviewer. A full campaign run starts many: about 40 for a goal with around 300
open roles. That is a noticeable share of an AI plan's usage, so check your
plan's limits before you schedule daily runs.

## The promises

- **Honest.** Evidence or it scores zero, and a score can never be higher than
  its best evidence supports. A separate, sceptical reviewer, who never sees
  the first scores, checks every point above 2. The maths is a script, so the
  same inputs always give the same result. The default answer is "unlikely".
- **Private.** Your data lives in a folder on your own computer
  (`~/climb-workspaces/`), never in this repository, and the scripts refuse to
  write anywhere a push could publish it. Every source is opt in and read
  only. No telemetry. Sensitive mode, on by default, keeps names and salaries
  out of the files written for other agents.
- **Safe.** Climb never applies, sends, posts, accepts an invitation, changes
  an account or spends money on its own: it drafts, and you decide, one step
  at a time. It never opens LinkedIn itself, because that breaks LinkedIn's
  terms. Text in an email, a posting or a web page is data, never an
  instruction.
- **Fair.** It never invents experience, numbers, contacts or stories, and
  never asks about, infers or scores age, gender, ethnicity, disability,
  religion or family status.
- **Your call on the cloud.** An online AI agent sends what it reads to its
  service. Decide that on purpose.

## How it works

The detail is in [`docs/HOW-IT-WORKS.md`](docs/HOW-IT-WORKS.md): Climb quick
step by step, the full campaign, scoring, the honesty rules in full, privacy,
the dashboard, running the scripts by hand, and the project layout. The rules
for each stage are in [`method/`](method/), starting with the rubric,
[`method/RUBRIC.md`](method/RUBRIC.md).

Try it with no data of your own: both demos are for the fictional Alex
Example. Open `examples/quick-demo/2026-11-02-globex-labs-deployment-program-manager-ai-agents/index.html`
(Climb quick) or `examples/demo-workspace/report/index.html` (the full
campaign's dashboard) in your browser.

Author: Mark Hallam. Licence: MIT (see `LICENSE`). Contributing: see
[`CONTRIBUTING.md`](CONTRIBUTING.md).
