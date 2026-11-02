---
name: lvlme-dashboard
description: Rebuild the LVLme dashboard from the current workspace files, check it validates, and give the person the command to open it.
disable-model-invocation: true
---

# LVLme: the dashboard

The LVLme engine folder is `${CLAUDE_PLUGIN_ROOT}` (if that placeholder was not
filled in, it is the folder two levels above this file). Run the commands
from that folder.

1. Find the workspace as the engine's `SKILL.md` says (`$LVLME_HOME` or the
   older `$CLIMB_HOME`, or the one folder in `~/lvlme-workspaces/` or the older
   `~/climb-workspaces/`, or ask which goal).
2. Rebuild, then validate:

   ```bash
   python3 scripts/build_dashboard.py --workspace <workspace>
   python3 scripts/validate.py --workspace <workspace>
   ```

3. Do not rescore and do not change any judgement. This entry point only
   redraws what the files already say. If the newest run in `eval/runs/` is
   older than the plan or the evidence, say so and suggest a full `/lvlme`.
4. Tell the person, in under 80 words: the current level and best chance, the
   next-level actions the dashboard shows (see `docs/LEVELS.md`), and the
   command to open it:

   ```bash
   open <workspace>/report/index.html
   ```

5. If they ask what a number means, or this is their first dashboard, point
   them to the plain-English guide, `docs/for-you/READING-YOUR-DASHBOARD.md`
   in the engine folder (also at
   https://github.com/mark-hallam/lvlme/blob/main/docs/for-you/READING-YOUR-DASHBOARD.md).
