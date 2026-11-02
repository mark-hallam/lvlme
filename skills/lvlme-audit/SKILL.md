---
name: lvlme-audit
description: Run the LVLme consistency audit and public claims audit. Compares the CV, LinkedIn, website and any official forms for mismatched dates, titles and claims, and checks public claims against evidence.
argument-hint: "[consistency | claims | both]"
disable-model-invocation: true
---

# LVLme: the audits

The LVLme engine folder is `${CLAUDE_PLUGIN_ROOT}` (if that placeholder was not
filled in, it is the folder two levels above this file).

1. Read the engine's `SKILL.md` and follow its hard rules and its "Find or
   create the workspace" steps. Everything below is the **audit** entry
   point of that procedure. With no argument, run both audits, in parallel
   if you can start subagents.
2. **Consistency audit**: follow `method/CONSISTENCY.md` and run
   `scripts/consistency_audit.py` with the flags that file gives. It compares
   what the CV, LinkedIn, the website and any official form say about the
   same facts (dates, titles, employers, qualifications).
3. **Claims audit**: run `python3 scripts/claims_audit.py <their pages>` and
   judge each `pending` claim as `supported`, `overstated`, `unsupported` or
   `contradicted`, with evidence ids and suggested honest wording (see
   `method/INTAKE.md`).
4. Every mismatch, overstatement or contradiction becomes a top-priority
   plan action and a drafted correction (`method/PROFILE_FIXES.md`). Drafts
   only: you change an account only when the person says yes to that one
   specific fix.
5. Never mark a mismatch resolved on your own say-so. It is resolved when the
   source itself shows the fix.
6. Tell the person, in plain English, what does not match and which fix
   matters most.
