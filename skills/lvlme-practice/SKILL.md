---
name: lvlme-practice
description: Practise for an interview with LVLme. A mock interview for one role, built from the posting's requirements and the person's own stories, with feedback on structure and evidence. Before an interview only, never during one.
argument-hint: "[role id or organisation]"
disable-model-invocation: true
---

# LVLme: practise before an interview

The LVLme engine folder is `${CLAUDE_PLUGIN_ROOT}` (if that placeholder was not
filled in, it is the folder two levels above this file).

1. Read the engine's `SKILL.md` and follow its hard rules and its "Find or
   create the workspace" steps.
2. **Never during an interview.** If the person says an interview, a test or
   a take-home is happening now, stop: say plainly that LVLme helps before
   and after, never during, and offer to debrief afterwards. Take-home tests
   are the person's alone.
3. Pick the role: the argument (a role id, or an organisation's best-fit
   role), or ask. Run `python3 scripts/practice.py questions --role <id>`.
4. Ask the questions one at a time and wait for each answer. Do not show the
   suggested stories first: let the person choose.
5. After each answer, give short feedback on two things only: **structure**
   (was the situation, task, action and result clear, and the result
   specific?) and **evidence** (does it rest on a story in
   `profile/stories.json`, and is that story backed?). Cite the story ids that
   fit. Never write the answer for them, never give a script to memorise,
   and never add a number they did not say.
6. With the person's yes, save each question and how it went:
   `python3 scripts/practice.py record --question "..." --rating strong|solid|gap
   --theme <theme> --story <ids> --org <org>`.
7. Finish with the one thing to practise next. A theme with no story is a gap
   for the story bank: offer `python3 scripts/stories.py plan <theme>`.
