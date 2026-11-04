---
name: lvlme-autopilot
description: "Turn LVLme Autopilot on or off. A check-in that runs itself on the person's schedule (weekly by default): it fetches roles, checks postings, judges what changed, scores, rebuilds the dashboard and leaves a This week note with the one thing to do. Asks for every permission first; never sends, applies or contacts anyone."
argument-hint: "[on | off | status]"
disable-model-invocation: true
---

# LVLme Autopilot: your campaign, running itself

Autopilot for the thinking, never for the doing. Once it is on, the person
does not have to remember to "run LVLme": each week (or day) the campaign
refreshes on its own and the dashboard opens on a "This week" card with the
one thing to do. LVLme never sends, applies, posts or contacts anyone, and a
run with nobody present asks nothing: questions wait in the note.

The LVLme engine folder is `${CLAUDE_PLUGIN_ROOT}` (if that placeholder was not
filled in, it is the folder two levels above this file). Run the commands
from that folder, with `--workspace <workspace>` found as the engine's
`SKILL.md` says.

## Turning it on

Needs a workspace with a scored run (a full `/lvlme` run, or LVLme quick
promoted to a campaign). If there is none, say so and offer to start one.

1. **Show what will run, in plain words** (one short message):
   - when: weekly on a day and time they choose (default Monday 7am, their
     time zone), or daily;
   - what each run does: new and closed roles at their targets, a check of
     each posting's age and reposts, judging only what changed, the blind
     review, scoring, the dashboard and a "This week" note;
   - the size: run `python3 scripts/run_plan.py` and quote its full and
     light lines, so they know how many helpers a run starts;
   - what it never does: send, apply, post, accept or change an account;
     drafts wait in `campaign/drafts/` for them.
2. **Ask for each permission once, as one short checklist**, and wait for
   their answers. Never assume a yes:
   - the rhythm, day and time;
   - a light run (their top 30 roles by fit, plus new ones; the default) or
     a full run;
   - which sources an unattended run may read, each read only: their public
     GitHub, their website, Gmail (read only, only if a connector exists), or
     none beyond the workspace;
   - whether unattended runs may start helper agents (the judges and the
     blind reviewer). Without them, new scores above 2 wait for review and
     count as 2.
3. **Record their answers** (only after their yes):

   ```bash
   python3 scripts/autopilot.py on --rhythm weekly --day mon --time 07:00 \
     --run light --sources github,website --helpers yes --scheduler desktop_task
   ```

   It writes `config.json` "autopilot" and the scheduled task's prompt to
   `campaign/autopilot-prompt.md`.
4. **Set up the schedule with the host's own scheduler**, and say which:
   - **Claude desktop app** (a scheduled-tasks tool is available): create a
     task named `lvlme-autopilot` with the prompt from
     `python3 scripts/autopilot.py prompt` and the schedule they chose, in
     their time zone. Show them the task, then confirm it is listed.
   - **Claude Code without the desktop app**: print the line from
     `python3 scripts/autopilot.py schedule-line` (a crontab entry that runs
      Claude Code on the schedule) and tell them how to add it
      (`crontab -e`, paste, save). They add it; never edit their crontab.
     The line grants these command permissions: `Bash(python3 *) Bash(ls *) Bash(cat *) Bash(test *) Bash(echo *) Bash(date *) Read Write Edit Glob Grep`.
   - **A cloud scheduler**: do not use one unless they choose to on purpose.
     It runs on someone else's computer and cannot see the workspace unless
     it is uploaded.
5. **Show progress straight away**: run `python3 scripts/autopilot.py week`
   and tell them to open the dashboard. Its first card is "This week", with
   the one thing to do and "Autopilot on, next run" with the date.

## Turning it off

1. `python3 scripts/autopilot.py off` (records the date).
2. Turn off or delete the scheduled task too: the desktop app task, or the
   crontab line (show them which line to remove). Confirm it is gone.

## Status

`python3 scripts/autopilot.py status`: on or off, the rhythm, the approved
sources and the next run. The latest note is `campaign/weekly/<date>.md`.

## Rules

- The person decides the rhythm and every source. Never change the schedule
  or the settings on your own, and never add a source they did not approve.
- A run with nobody present asks nothing and approves nothing new. Every
  question and every step that needs a yes goes in the note and the final
  message.
- Plain English, short, in the person's time zone.
