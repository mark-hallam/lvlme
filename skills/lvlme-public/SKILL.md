---
name: lvlme-public
description: Build in public with LVLme. Finds what the person finished that is worth sharing, drafts a post from their own notes in their voice, and keeps a record of what they posted and what it led to. LVLme drafts; the person posts, under their own name, every time.
argument-hint: "[idea ref, or: ideas | posted | checked]"
disable-model-invocation: true
---

# LVLme: build in public

The LVLme engine folder is `${CLAUDE_PLUGIN_ROOT}` (if that placeholder was not
filled in, it is the folder two levels above this file).

Showing your work in public is how people who could hire or refer you get to
know it. LVLme helps you do it steadily: what to share, a draft in your voice,
and a record. **It never posts, and never opens LinkedIn.** You post.

1. Read the engine's `SKILL.md` and follow its hard rules and its "Find or
   create the workspace" steps.
2. Run `python3 scripts/public.py ideas`. Show the person the ideas (things
   they finished that are worth sharing) and this week's count against their
   target (`config.json` `public.per_week`, default 1). Ask which one, or what
   else they want to share.
3. Run `python3 scripts/public.py draft <ref> --channel <x|linkedin|...>`. It
   writes a brief to `campaign/drafts/` with the facts the post may use and the
   person's voice rules (`config.json` `public.voice`; ask them to describe
   how they write the first time, and save it there with their yes).
4. Ask for their rough notes: what they want to say, in their own words. Write
   the draft from those notes into the brief's Draft section, in their voice.
   Offer two or three short options when they want choices. Never add a fact,
   a number or a claim beyond the brief's facts, never name a person without
   that person's yes, and never use words the person would not.
5. They edit it and post it themselves. When they give you the link, run
   `python3 scripts/public.py posted <id> --url <link>`. Open the link
   yourself; if it shows the post, run `python3 scripts/public.py checked <id>`:
   that makes it a verified public signal, which the next run can judge.
6. Later, ask what it led to (replies, a new contact, an invitation) and save
   it with `python3 scripts/public.py result <id> --note "..."`. A new contact
   goes into warm paths with the person's yes.
