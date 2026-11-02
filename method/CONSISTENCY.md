# The consistency audit

Recruiters, hiring managers and background checks compare the CV
(curriculum vitae), LinkedIn, the personal website and any official form the
person has signed. When they disagree, the reader does not assume a typo:

- a **raised title** (LinkedIn says "Quality Manager", the employer's
  records say "Deputy Quality Manager") reads as dishonesty;
- **dates that differ** by a few months read as careless, or as hiding a
  gap;
- a **role or claim on only one page**, especially one the person says they
  never did, is the thing a reference check finds.

These are cheap to fix and expensive to leave. Overclaims hurt more than
gaps (see `INTAKE.md`), so every high finding here becomes a top priority
plan action.

`scripts/consistency_audit.py` does the comparison. The agent's job is to
copy each source faithfully, run it, check the result with the person, and
draft the fixes (`PROFILE_FIXES.md`).

## 1. Build the input: `profile/role-records.json`

One entry per source under `sources`, each with a list of role `records`.
The shape is in `schemas/role-records.schema.json`; a fictional example is
`examples/consistency/role-records.json`.

| Source id | What it is | Default: lists every role? | Default: person can edit? |
|---|---|---|---|
| `confirmed` | What the person confirmed in the interview (`INTERVIEW.md`), ideally from a document | yes | no (it is the reference, not a page) |
| `official_form` | A form the person signed: a pre-employment or background check history form, a regulator's application | yes | no |
| `references` | What a referee's letter or note says | no | no |
| `cv` | The CV a recruiter would receive today | yes | yes |
| `linkedin` | The LinkedIn profile as it stands today | yes | yes |
| `website` | The person's own site | no | yes |

Any other id works too (for example `github` or `portfolio`); it is
treated as a page the person can edit that may not list every role.

**Copy, do not correct.** The audit only works if each source is copied
exactly as it reads today, wrong titles and all. Use
`templates/prompts/consistency-sources.md`, one source at a time. Dates can
be written as the source shows them: `Oct 2007`, `October 2007`, `2007-10`,
`10/2007`, or a year alone, `2007`. A current role is `present`.

Useful fields:

- `complete: false` for a source that does not try to list everything;
  `covers: {"from": "2009", "to": "Aug 2019"}` for a form that only asked
  about a period. Roles outside the period are not expected in it.
- `editable: false` for anything the person cannot change.
- `key`: give records in different sources the same key to force a match
  when the automatic one is wrong (see "How roles are matched").
- `concurrent: true` on a role that really ran alongside another.
- `claims`: achievement lines, copied word for word.
- `denies` (usually on `confirmed`): lines other sources say that the
  person says are not true.
- `organisation_aliases`: other names for a renamed employer.
- `explained_gaps`: periods the person has explained (study, a business,
  travel, caring, a career break), with a reason and evidence ids.
- `truth_order`: the order of trust, if the default does not suit.

## 2. Run it

```bash
python3 scripts/consistency_audit.py
```

It reads `profile/role-records.json` and writes `profile/consistency.json`
(the full report, `schemas/consistency.schema.json`) and
`profile/consistency.md` (the short summary for the person). Options:

- `--tolerance-months N`: date differences up to N months are ignored
  (default 1). Use 0 before publishing, so every date matches exactly.
- `--gap-months N`: report gaps longer than N months (default 3).
- `--input FILE` without `--workspace`: print the summary (or `--json`) for
  that file and write nothing. Useful for trying the fictional example:

```bash
python3 scripts/consistency_audit.py --input examples/consistency/role-records.json
```

## 3. What it checks

| Finding | When | Severity |
|---|---|---|
| `title_mismatch` | Two sources give the same role different titles. | High when it is likely inflation; medium otherwise. |
| `date_mismatch` | A start or end date differs by more than the tolerance, or one source says the role is current and another says it ended. | High for "current" against "ended" and for 6 months or more; medium otherwise. |
| `missing_role` | A role (or the person's own business) is missing from a source that should list it. | High when only the person's own pages list it and the confirmed history or an official form does not; medium otherwise. |
| `gap` | No role, study or explained break for longer than the gap limit, between roles or since the last one ended. | Low up to 6 months; medium above. |
| `overlap` | Two roles overlap by more than the tolerance and neither is marked concurrent. | Low up to 3 months; medium above. |
| `single_source_claim` | An achievement line appears on only one of the person's own pages. | Medium. |
| `claim_mismatch` | The same claim appears with different numbers ("30%" on the CV, "40%" on LinkedIn). | Medium. |
| `denied_claim` | A line on a page matches something the person says is not true. | High. |

A claim that appears on both the CV and LinkedIn is **consistent, not
corroborated**: both are the person's own words. Corroboration needs an
independent source (see the verification ladder in `INTAKE.md`).

### How it decides "likely inflation"

Titles are first normalised: lower case, punctuation dropped, common
abbreviations expanded ("Sr" to "Senior", "Mgr" to "Manager", "VP" to "Vice
President"), common British and American spellings matched ("Programme" and
"Program"), and word order ignored. So "Quality Manager (Deputy)" and "Deputy Quality Manager" are the
same title. Two different titles are then flagged as likely inflation when:

1. **A qualifier is missing.** One title is the other with a lowering word
   left out: Deputy, Assistant, Acting, Associate, Junior, Trainee,
   Graduate, Intern, Interim, Vice, Apprentice, Co (as in Co-founder) or Sub.
   "Quality Manager" against "Deputy Quality Manager" is the classic case.
2. **A seniority step.** The titles share the same subject words (for
   example "Operations") but one sits higher on the ladder: intern or
   trainee, then officer, analyst, engineer, specialist and similar, then
   supervisor or lead, then manager, head, director, vice president and
   chief. "Senior", "Principal", "General" and "Executive" add a step;
   "Junior" takes one away. So "Operations Lead" against "Operations
   Analyst", or "Head of Quality" against "Quality Manager". Both titles
   need a ladder word, or must differ only by words like "Senior", so
   "Founder" against "Founder and Principal Consultant" is not called
   inflation.

Titles about different subjects ("Quality Manager" against "Safety
Manager") are reported as a plain mismatch: check which one is right.

## 4. The suggested single source of truth

For each role, the report suggests one title, start and end, and says which
source each came from:

1. If the person confirmed the role (`confirmed`), their confirmed values
   win.
2. Otherwise each value comes from the most trusted source that has it
   (default order: confirmed, official form, references, CV, LinkedIn,
   website). A year alone is refined to a month from the next source that
   agrees on the year.
3. **Where titles disagree and nobody has confirmed one, the more modest
   title is suggested.** Understating a title costs little; overstating one
   can cost the offer. If the person can show the senior title on paper,
   add it to `confirmed` and run again.

Every line marked **confirm** needs the person's answer, against a document
if possible, before anything is changed.

## 5. The fixes

`profile/consistency.md` lists the exact fixes per source, for example:

> Change the title from "Quality Manager" to "Deputy Quality Manager".
> Change the end date from May 2012 to Mar 2012.

- Fixes to the CV, LinkedIn and website are **drafts**. Turn them into
  ready-to-paste text with `PROFILE_FIXES.md`. The engine never edits an
  account.
- A signed form cannot be changed. Its "fixes" say what the person should
  be ready to explain, and every editable source should match the truth.
- Fixes under `confirmed` are questions to ask the person.
- Gap and overlap fixes apply to all sources.

## 6. After the audit

1. Check every finding with the person. The script compares words; it does
   not know the truth.
2. Record what you learn in `profile/evidence.json`. A public title or date
   that turns out wrong is a claim to add to `profile/claims-audit.json` as
   `overstated` or `contradicted`, with the honest wording.
3. Add plan actions in `campaign/plan.json`: one per high finding (or one
   "make CV, LinkedIn and website match the source of truth" action for a
   batch), dimension D5 (public signal) or D7 (application readiness), with
   `"effects": []` because fixing an overclaim protects credibility rather
   than raising a score.
4. Once the person has made the changes, copy the changed sources again and
   re-run. Done means the audit shows no high findings, with the new report
   as the `done_evidence`.
5. Run it again whenever a source changes, and before every important
   application, with `--tolerance-months 0`.

## How roles are matched

Records are matched across sources by organisation (ignoring case,
punctuation and legal suffixes such as Pty Ltd, Inc or LLC, and using any
aliases), then by overlapping dates and similar titles. Two roles at one
employer (a promotion) stay separate when their dates are separate. If a
match is wrong, give the records the same `key`. Check the "Suggested
single source of truth" table: one line per real role is right.
