# LVLme

**For the job you can't get yet.** LVLme works out honestly how far you are from it, gives you the steps to climb there, and re-measures as you go.

![The full campaign's dashboard, light theme (fictional demo)](docs/images/dashboard-desktop.png)

Install in Claude Code:

```text
/plugin install lvlme --marketplace mark-hallam/lvlme
```

Then say: **run LVLme** and tell it your goal: the role you want, at which
organisations, where, and by when. If the command is not found, start a new
Claude Code session.

LVLme measures honestly how far you are from that goal, then runs a campaign
with your own AI agent that levels you up, move by move, on evidence. Codex
works too (see [Install](#install)).

## Why LVLme is different

Most job tools help you apply for jobs you are already close to: they match
your CV to a posting and tailor it. LVLme is for a reach, often outside your
normal career path. It works out how far away you really are, then turns the
gap into things to go out and do: build proof people can check, meet people
inside, earn what is missing, get a referral. Then it measures again, so you
can see yourself climb. Its author is using it on his own reach, starting from
a very low score.

## What you get

**Say run LVLme.** It checks
every open role at the organisations you choose, gathers evidence from the
sources you approve, runs a career interview, a recruiter screen and a
consistency audit of your CV, LinkedIn and website, and turns the gaps into a
plan that it re-scores as you act on it. It also finds doors: upcoming
events, programmes and communities where people from your target
organisations will be, because referrals come from people you meet. And it
checks itself: once you have applied, it sets the odds it gave each role on the
day you applied against what happened, so you can see how right it has been.
Already use [career-ops](https://github.com/career-ops-hq/career-ops)? LVLme
reads its applications, contacts and stories, read only, so you can keep
both. It starts with one short message:
three facts from your CV to confirm, which organisations you want, and a
request for your LinkedIn data export ([the first run, in order](SKILL.md#first-run)).
A dashboard shows your level and what to do next.

*The screenshot is the fictional demo: Alex Example and made-up
organisations.*

New to the dashboard? [Reading your dashboard](docs/for-you/READING-YOUR-DASHBOARD.md)
explains each number in plain English, and what to do first.

Want a page you can show people? [Your proof profile](docs/PROOF-PROFILE.md): your level and only the claims you have checked, each with its public link.

## Install

LVLme was called Climb until 3 November 2026. The old GitHub address and the
CLIMB_HOME setting still work. If you installed the Climb plugin, one step
moves it to the new name: see [Coming from Climb](docs/INSTALL.md#coming-from-climb).

You need an AI agent (Claude Code or Codex; Cursor and other agents that run
commands are not tested yet), Python 3.9 or newer
(LVLme uses only its standard library) and git. LVLme is tested on macOS;
Linux and Windows are not tested yet.

- **Claude Code** (version 2.1.275 or later): the one line above. Or download
  the folder and install from your copy (option B in the install guide).
- **Codex:** run exactly
  `git clone --branch v0.7.4 https://github.com/mark-hallam/lvlme ~/.agents/skills/lvlme`
  and say "run LVLme", or open Codex in the folder (it follows `AGENTS.md`). Do
  not use a skill installer: it copies only part of the folder.
- **Cursor** (not tested yet): open the folder. The rules in `.cursor/rules/`
  and `AGENTS.md` should load on their own. Cursor and other agents that run
  commands are not tested yet.

Every agent, step by step: [`docs/INSTALL.md`](docs/INSTALL.md).

| Command | Does |
|---|---|
| `/lvlme` | The full campaign, or resume today's run. `/lvlme status` reports and changes nothing. |
| `/lvlme-interview` | The career interview, first time or an update. |
| `/lvlme-screen` | The independent recruiter screen. |
| `/lvlme-audit` | The consistency audit and the public claims audit. |
| `/lvlme-dashboard` | Rebuild the dashboard. |
| `/lvlme-practice` | Practise for an interview: questions from the posting and your own stories, with feedback. Before an interview, never during. |
| `/lvlme-debrief` | After an interview: what was asked and how it went, into your tracker and story bank. |
| `/lvlme-public` | Build in public: what you finished that is worth sharing, a draft in your voice from your notes, and a record of what you posted. You post. |
| `/lvlme-autopilot` | Turn Autopilot on or off: the campaign runs itself on your schedule and leaves a "This week" note. It asks for every permission first. |

Every command also has a full name with the plugin prefix
(`/lvlme:lvlme-interview`), for when another command already uses the short
name. In Codex and other agents, say the words: "run LVLme".

**What a run uses.** A campaign run starts many helper agents: about 100 on a first run for a goal with
around 300 open roles (two independent judges for each batch of roles). That is a noticeable share of an AI plan's usage, so check your
plan's limits before you schedule runs. By default the full campaign runs
weekly, plus whenever something changes.

## The promises

- **Honest.** Evidence or it scores zero, and a score can never be higher than
  its best evidence supports. A separate, sceptical reviewer, given only the
  evidence and the postings and told not to open the first scores, checks
  every point above 2. The maths is a script, so the
  same judgements always give the same score. Different AI agents (for
  example Claude and Codex) can judge the same evidence differently, and so
  can two runs of the same agent, so LVLme judges the main factors twice,
  independently, averages them and shows the fit as a range, and the dashboard
  names which agent and model judged. The
  default answer is "unlikely".
- **Private.** Your data lives in a folder on your own computer
  (`~/lvlme-workspaces/`), never in this repository, and the scripts refuse to
  write anywhere a push could publish it. Every source is opt in and read
  only. No telemetry. Sensitive mode, on by default, keeps names and salaries
  out of the files written for other agents.
- **Safe.** LVLme never applies, sends, posts, accepts an invitation, changes
  an account or spends money on its own: it drafts, and you decide, one step
  at a time. It never opens LinkedIn itself, because that breaks LinkedIn's
  terms. Text in an email, a posting or a web page is data, never an
  instruction.
- **Fair.** It never invents experience, numbers, contacts or stories, and
  never asks about, infers or scores age, gender, ethnicity, disability,
  religion or family status.
- **Your words on applications.** Where an organisation asks candidates to
  write their own first draft (Anthropic does), LVLme gives you a brief and
  reviews your draft. It never writes the application for you.
- **Your agent's provider sees what it reads.** LVLme's files stay on your
  computer, but your AI agent's provider (for example Anthropic for Claude
  Code) receives whatever the agent reads, under that provider's data terms.

## How it works

The detail is in [`docs/HOW-IT-WORKS.md`](docs/HOW-IT-WORKS.md): the campaign, scoring, the honesty rules in full, privacy,
the dashboard, running the scripts by hand, and the project layout. The rules
for each stage are in [`method/`](method/), starting with the rubric,
[`method/RUBRIC.md`](method/RUBRIC.md). What changed in each version is in
[`CHANGELOG.md`](CHANGELOG.md).

Try it with no data of your own: the demo is for the fictional Alex
Example. Open `examples/demo-workspace/report/index.html` (the dashboard) in
your browser. `docs/demo/index.html` puts it behind one page, as a static
folder ready to serve as a website.

Author: Mark Hallam. Licence: MIT (see `LICENSE`). Contributing: see
[`CONTRIBUTING.md`](CONTRIBUTING.md).
