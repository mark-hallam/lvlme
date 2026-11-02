---
name: climb-interview
description: Run or update the Climb career interview. Reads the documents the person supplies first, then asks only what the documents cannot answer.
argument-hint: "[first | update]"
disable-model-invocation: true
---

# Climb: the interview

The Climb engine folder is `${CLAUDE_PLUGIN_ROOT}` (if that placeholder was not
filled in, it is the folder two levels above this file).

1. Read the engine's `SKILL.md` and follow its hard rules and its "Find or
   create the workspace" steps. Everything below is the **interview** entry
   point of that procedure.
2. If `config.json` has no target organisations or role families yet (a new
   workspace: `scripts/validate.py` says so), start there. Ask the "Goals and
   motivation" questions 1 and 5 in `method/INTAKE.md`, then fill in
   `config.json` with the person: targets, role families and keywords, any
   title exclusions, location classes and time zone. Run
   `scripts/validate.py` again.
3. Ask which documents and sources the person is happy for you to read (for
   example a CV, the LinkedIn data export, their website). Each one is opt in
   and read only. Save supplied files in `intake/sources/`.
4. Follow `method/INTERVIEW.md`: read the documents first, then ask only the
   gaps, a few questions at a time. Use the question bank in
   `method/INTAKE.md` as the checklist.
5. With the argument `update` (or when `intake/answers.md` already has
   answers), ask only about what changed since the last run and the open
   questions in `profile/evidence.json`.
6. Save the answers in `intake/answers.md`. Record each new fact in
   `profile/evidence.json` with its verification level. Something the person
   tells you is `self_reported`, never `verified`.
7. While the person answers, you may start the gather stage in the
   background for the sources they have approved (see
   `docs/ORCHESTRATION.md`).
8. Finish with a short plain English summary: what you learnt, what still
   needs an answer, and whether to run the full `/climb` next.
