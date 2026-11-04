# LVLme 0.6.1: fixes from a new-user test

5 November 2026. A small fix release. We installed LVLme the way a new person
would, followed only the public instructions, and fixed what got in the way.
How a score is worked out did not change.

## Fixed

- **Job links on Python from python.org.** That Python has no website
  certificates until its "Install Certificates" step is run, so every job
  link failed with a message that hid the cause. LVLme now tries once more
  with your Mac's own certificates. If that also fails, it says in one line
  what to run, or to paste the job ad text instead. It never turns
  certificate checking off.
- **Climb from here keeps your fixes.** When you turn a LVLme quick result
  into a full campaign, its suggested fixes now carry into the campaign plan
  as open actions, instead of an empty "No open actions yet".
- **Climb from here names the role.** Its message now says the role's title
  and organisation, not an internal code, and the goal is no longer repeated.
- **LVLme quick follows `LVLME_HOME`** (the setting for where your files
  live), as the rest of LVLme does. When both `~/lvlme-workspaces` and the
  older `~/climb-workspaces` exist, LVLme says once which one it is using.
- **Which AI judged.** Different AI agents can judge the same evidence
  differently, so the quick result and the dashboard now say which agent
  (for example Claude or Codex) and model did the judging, when known.
- **Install guide.** For Claude Code, the download option now installs from
  your own copy, so the main `/lvlme` command shows up. For Codex, run the
  exact `git clone` command: a skill installer copies only part of the
  folder. The Claude chat section lists all ten skills. Cursor is marked as
  not tested yet.
- **Agents ask first.** The instructions for AI agents now say, as their
  first rule, to stop and wait for your yes before each install or run, and
  to repair a partial copy of LVLme before starting.
- **Release notes** link the changelog by its full address, so the link
  works on the release page.

The full list is in [CHANGELOG.md](https://github.com/mark-hallam/lvlme/blob/v0.6.1/CHANGELOG.md).
