# LVLme 0.5.0: autopilot for your career

LVLme is for the job you can't get yet. It works out honestly how far you are
from a job, gives you the steps to get there, and measures again as you go.

This release makes the "measures again as you go" part run itself. You say
yes once to what may run and how often, and each week LVLme checks the job
boards, scores again, and leaves a short note: what changed, your level, and
the one thing to do next. It also tracks your applications, tells you when a
follow-up is due, and flags job ads that look old or keep being reposted.

How a score is worked out did not change.

## Added

- **Autopilot.** `/lvlme-autopilot` explains what will run, then asks for
  each permission once: how often, a light or full run, which read-only
  sources, and whether helper agents may run. It sets up the schedule with
  the Claude desktop app's scheduled tasks, or prints a line for your
  computer's own scheduler. Each run leaves a "This week" note, the
  dashboard's new first card. Off is one command. It never sends, applies or
  contacts anyone. Tried for real: a scheduled run on a fictional workspace
  finished on its own in about six minutes, with nobody at the keyboard.
- **Applications and follow-ups.** `scripts/applications.py` tracks each
  application through ten stages and keeps every change in an append-only
  log. Follow-ups are timed (7 days, then 7 more, at most 2; a thank-you
  note the day after an interview), shown on a new Applications card, and
  drafted for you to finish and send yourself.
- **Is this job still open?** Every role gets a quiet label from its age and
  reposts: likely real, check first, or suspicious ("Open, but posted 14
  months ago"). A plan action whose roles all look suspicious ranks lower.
  Scores never change, and LVLme never calls a posting fake.
- **Climb from here.** `python3 scripts/quick.py promote` turns a LVLme
  quick result into a full campaign with nothing redone: the same evidence,
  the posting as the first role, and the judgements carried across. The
  campaign's first score matches quick's.
- **Know the size of a run before it starts.** `scripts/run_plan.py` says
  how many roles need judging and about how many helper agents a full or a
  light run would start, so you choose. Unchanged roles keep their last
  judgement.
- **All six job boards in the full campaign.** Workday, SmartRecruiters and
  Workable join Greenhouse, Ashby and Lever. Large boards are paged through
  in full, and only postings whose title fits are read in detail.
- **The first-draft rule, checked in code.** For an employer that asks
  candidates to write their own first draft, `scripts/validate.py` flags any
  draft that is not a brief, a review of your draft, preparation or
  outreach. LVLme quick names the employer's AI guidance and links to it.
- **Install in Claude chat**, tried for real, with the steps in
  [INSTALL.md](INSTALL.md).

## Fixed

- Three method files told the agent to give the blind reviewer the scores.
  Every file now says the reviewer never sees them, and a test keeps it so.
- In Claude chat, LVLme quick shares the result page as a file rather than
  an open command, which cannot work there.

The full list is in [CHANGELOG.md](../CHANGELOG.md).

## Checked by

- 434 tests pass, including new ones for each feature above.
- `claude plugin validate --strict` on the manifest.
- One real unattended Autopilot run on a fictional workspace.
