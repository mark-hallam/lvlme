---
name: lvlme-debrief
description: Use when the person says "run LVLme debrief" or asks to review a completed interview. Records questions and answers and identifies story bank work. After an interview only, never during one.
argument-hint: "[application id]"
---

# LVLme: debrief after an interview

The LVLme engine folder is `${CLAUDE_PLUGIN_ROOT}` (if that placeholder was not
filled in, it is the folder two levels above this file).

1. Read the engine's `SKILL.md` and follow its hard rules and its "Find or
   create the workspace" steps.
2. **Only after it is over.** If the interview is still going, stop and say
   LVLme helps before and after, never during.
3. Find the application (the argument, or `python3 scripts/applications.py
   list`). If it is not tracked yet, add it first with the person's yes.
4. Ask what they were asked, one question at a time, and how each answer went
   in their own view: strong, solid or gap. Ask which story they used.
5. Save each with the person's yes: `python3 scripts/practice.py record --real
   --app <id> --question "..." --rating <rating> --theme <theme> --story <ids>`.
   The first one moves the application to Interview if it was earlier.
6. Then: offer the thank-you note (`python3 scripts/applications.py draft
   <id>`, for them to finish and send); for each gap, offer a story bank step
   (`python3 scripts/stories.py plan <theme>`, or add a story they now
   remember with `stories.py add`); and record any new evidence they mention
   in `profile/evidence.json` at the right level.
7. Rebuild the dashboard. Never contact the employer, and never guess an
   outcome: stages change only when the person says so.
