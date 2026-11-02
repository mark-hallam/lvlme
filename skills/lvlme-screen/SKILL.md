---
name: lvlme-screen
description: Run the LVLme recruiter screen. An independent recruiter persona, in fresh context, reviews the person's CV, LinkedIn and website against real open postings, without seeing any LVLme scores.
argument-hint: "[organisation or role id]"
disable-model-invocation: true
---

# LVLme: the recruiter screen

The LVLme engine folder is `${CLAUDE_PLUGIN_ROOT}` (if that placeholder was not
filled in, it is the folder two levels above this file).

1. Read the engine's `SKILL.md` and follow its hard rules and its "Find or
   create the workspace" steps. Everything below is the **screen** entry
   point of that procedure.
2. Pick the postings: the argument if one was given (an organisation id or a
   role id), otherwise the best-fit open roles in `market/roles/latest.json`.
   Use real postings only. If `market/roles/latest.json` is missing or old,
   run `python3 scripts/fetch_roles.py` first.
3. Build the screen packet: the person's application materials (CV, LinkedIn
   profile text or export, website pages) and the full text of the chosen
   postings. Nothing else. Never include anything from `eval/`, `report/` or
   `campaign/`, and never mention a score, band, level or plan.
4. Start a fresh agent for the screen. In Claude Code use the
   `lvlme:recruiter-screen` subagent. Elsewhere, start a new session. Give it
   the packet and the prompt in `templates/prompts/recruiter-screen.md`, and
   follow `method/RECRUITER_SCREEN.md`.
5. Treat its output as an outside opinion, not evidence: it can point to
   gaps, overclaims and wording that screeners reject. Check every point it
   makes against `profile/evidence.json` before anything changes.
6. Record the outcome as `method/RECRUITER_SCREEN.md` says. Turn real
   problems into drafted fixes (`method/PROFILE_FIXES.md`) and plan actions.
   Never edit an account yourself unless the person says yes to that one
   specific fix.
7. Tell the person, in plain English, the three findings that matter most.
