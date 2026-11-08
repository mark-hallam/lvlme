# Profile fixes

The consistency audit (`CONSISTENCY.md`), the recruiter screen
(`RECRUITER_SCREEN.md`) and the claims audit (`INTAKE.md`) each say what is
wrong with the person's public profile. This module turns those findings
into **ready-to-paste drafts**: corrected LinkedIn entries, CV (curriculum
vitae) lines and website copy, each one tied to evidence.

## The rules

1. **Drafts only.** Neither the engine nor its agents edit the CV, LinkedIn,
   the website or any account. The person copies the drafts across.
2. **Every line is tied to evidence.** Each draft names the evidence ids
   (`profile/evidence.json`) and the finding it fixes. No evidence, no line.
3. **Never invent.** No new number, title, date, client or story. Fixing an
   overclaim means saying less, not saying something else, and never a
   confession (rule 8).
4. **The modest truth wins.** Use the suggested single source of truth from
   the consistency audit. Where a title is in doubt, use the more modest one
   until a document shows otherwise.
5. **The person's words.** Prefer how the person describes their own work,
   tidied, over agent prose. Keep their voice.
6. **One version of the truth.** The same title, organisation name and
   month dates on the CV, LinkedIn and website. Achievement lines may be
   shorter on one page than another, but never stronger.
7. **The organisation's AI rules come first.** A fix corrects the person's
   own existing text. Never write a résumé, cover letter or application
   answers for an organisation whose `ai_policy.first_draft_by_person` is
   true in `config.json` (for example Anthropic): give the person a brief and
   review their own draft instead, as `CAMPAIGN.md` describes.
8. **No negative status lines.** A draft for a public place (CV, LinkedIn,
   website, a post) never carries a line like "no users yet", "no paying
   customers", "did not finish", "not completed", "retired" or "I never
   switched it on". Readers and screening tools mark those down. Leave the
   fact unsaid; never claim the opposite. A hedge on the person's own count
   ("by my count") stays where a number appears. An interview answer or a
   case study the person writes in their own words is theirs to decide.


## The draft file

Write `campaign/drafts/profile-fixes-<YYYY-MM-DD>.md`, one block per change,
grouped by source:

```markdown
## LinkedIn

### Experience: Fabrikam Air, R03 (fixes F01, F02, F05)
Current title:   Quality Manager
New title:       Deputy Quality Manager
Current dates:   Jul 2008 to May 2012
New dates:       Jul 2008 to Mar 2012
Remove:          "Ran the airline's external audit program"
Evidence:        E04 (offer letter), E05 (farewell email, last day)
Status:          draft
```

For text blocks (a headline, an "About" section, a website paragraph), give
the full current text and the full new text, so the person can replace it
in one paste. Statuses: `draft`, `approved` (the person said yes),
`applied`, `verified` (the saved text was pasted back, or read from the person's own website, and matches).

Link the draft from the plan action it serves (`draft` in
`campaign/plan.json`).

## Applying the drafts (the person does this)

The person makes every edit themselves. Give them these tips with the drafts:

1. **Only approved drafts.** Change exactly what was approved, nothing else.
2. **One entry at a time.** Open one entry, paste, save, check, then move on.
3. **Turn off "notify network" first.** LinkedIn and similar sites offer to
   tell your network about profile changes. Switch that off before the first
   edit, so corrections do not go out as announcements.
4. **Skip every prompt to post, share or connect.** Close suggestions to
   announce a new role, add skills, follow people, or use a rewrite assistant.
5. **Check the saved text.** Some web editors drop or double characters.
   After saving, compare the saved text with the draft.
6. **Paste the saved text back** to the agent (or, for your own website, let
   it read the live page). The agent compares it with the approved draft and
   sets the block's status to `applied`, then `verified`, with the date.

If a field needs something the draft does not have (an employment type, a
location), the agent asks rather than guessing.

## After the edits

1. Copy the changed sources again into `profile/role-records.json` and run
   `python3 scripts/consistency_audit.py`.
2. Run `python3 scripts/claims_audit.py` on the changed pages and judge the
   new claims.
3. Mark the plan action done only with evidence: the new consistency report
   with no high findings, plus the page addresses and the date they were
   read back.
4. After a substantial change, run a fresh recruiter screen.

## Keeping every source identical

A checklist for the person, to run before every application and whenever
something changes:

- [ ] Each role's **title** is word for word the same on the CV, LinkedIn and
      website, and matches the offer letter or employer's records. "Acting",
      "Deputy", "Assistant" or "Associate" stays in if it was in the real
      title.
- [ ] Each role's **start and end month** is the same everywhere, and
      matches any form the person has signed. A role that has ended does not
      say "present".
- [ ] The **organisation name** is the same everywhere (the name it had then,
      with "now called" if it was renamed).
- [ ] **Every role** on LinkedIn is on the CV, and the reverse, unless one is
      left out on purpose for a reason the person can give.
- [ ] Every **gap** longer than a few months has a one-line explanation, or
      the person is ready to give one.
- [ ] Every **number** (team size, budget, percentage, users) is the same
      everywhere and has an evidence id behind it.
- [ ] Nothing on any page is something the person said is **not true**.
- [ ] Future **forms** (a new employer's history form, a visa or licence
      application) are filled from the single source of truth in
      `profile/consistency.md`, not from memory.
- [ ] A past signed form that turns out to be wrong is never altered. If it
      matters, the person tells the recruiter or employer the correct
      details before they find the difference themselves.
- [ ] The consistency audit has been re-run after the last change, with
      `--tolerance-months 0`, and shows no high findings.
