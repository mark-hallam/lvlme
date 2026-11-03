# LVLme 0.3.0: Climb is now LVLme

LVLme (said "level me") was called Climb until 3 November 2026. Same
engine, same method, same promise: **for the job you can't get yet.** It works
out honestly how far you are from a job, gives you the steps to climb there,
and re-measures as you go. The new name says what the dashboard already
shows: Level 1 to Level 5, and the actions that take you to the next one.

Nothing about scoring, evidence or privacy changed in this release.

## Changed

- **Name.** LVLme everywhere: the README, the docs, the method files, the
  skills, the helper agents, the Cursor rules, the dashboard and the quick
  result page.
- **Plugin and marketplace.** Both are named `lvlme` (were `climb`), and the
  plugin's display name is LVLme. Install:
  `/plugin install lvlme --marketplace mark-hallam/lvlme`.
- **Repository.** https://github.com/mark-hallam/lvlme. GitHub forwards the
  old climb address here.
- **Commands.** `/lvlme`, `/lvlme-quick`, `/lvlme-interview`, `/lvlme-screen`,
  `/lvlme-audit` and `/lvlme-dashboard` (were `/climb`, `/climb-quick` and so
  on). The words "run LVLme" and "run LVLme quick" start them in any agent.
- **Helper agents.** `lvlme:evidence-scout`, `lvlme:market-scout`,
  `lvlme:role-judge`, `lvlme:reviewer` and `lvlme:recruiter-screen`.
- **Codex and Cursor.** Type `$lvlme` in Codex. The Cursor rules are
  `lvlme-hard-rules.mdc` and `lvlme-run.mdc`.
- **Workspace.** The setting is `LVLME_HOME` and the default folder is
  `~/lvlme-workspaces/`, with quick results in `~/lvlme-workspaces/quick/`.
- **Small things.** Script messages start with `lvlme:`, the job-board
  requests say `lvlme/0.3`, and the dashboard saves its theme and its
  "Pending" ticks under `lvlme-` keys in your browser.

## Still works

| Old name | What happens now |
|---|---|
| `CLIMB_HOME` | Read when `LVLME_HOME` is not set. `LVLME_HOME` wins when both are set. |
| `~/climb-workspaces/` | Used when `~/lvlme-workspaces/` does not exist. The scripts say so once per command, on the error stream, so JSON output is untouched. |
| `~/climb-workspaces/quick/` | Quick results go there the same way while only the old folder exists. |
| The plugin name `climb` | The marketplace maps `climb` to `lvlme`, so an installed plugin moves to the new name. Update the marketplace, then run `/plugin install lvlme@climb` once. |
| "run Climb", "run Climb quick" | Still start a full run or a quick answer. |
| Dashboard theme and Pending ticks | Read from the old `climb-theme` and `climb-pending:` keys when the new ones are missing. |
| Workspace files | No file field or schema key carried the name, so workspaces and quick folders written by Climb 0.2.0 are read as they are. |

Step by step for an existing install:
[Coming from Climb](INSTALL.md#coming-from-climb).

## Not kept

- The old commands (`/climb`, `/climb-quick` and the rest), the old helper
  agent names (`climb:reviewer` and the rest) and `$climb` in Codex. Use the
  new names, or say "run Climb".
- A new install by the old plugin name (`/plugin install climb ...`) finds
  nothing. Use `lvlme`.

## Checked by

- `tests/test_old_names.py`: each fallback above, in temporary folders.
- `tests/test_packaging.py`: the `climb` to `lvlme` rename in the
  marketplace, and "run Climb" in the skill's trigger description.
