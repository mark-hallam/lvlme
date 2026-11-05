# The independent sceptical review

Principle: honest by construction. The default answer is "unlikely", and a
separate, sceptical reviewer must agree with every score above 2 before it
stands. `scripts/score.py` enforces this: a score above
`scoring.review_required_above` (default 2) counts as 2 until it has a
`reviewed_on` date on or after its `judged_on` date.

## Why a separate reviewer

The scorer has spent the run looking for reasons to give points. That is a
bias, even for an honest agent. A fresh agent that has not seen the scorer's
reasoning reads the same evidence cold, the way a hiring manager would.

## Who reviews

- A **fresh agent session**, started for the review only. Not the agent that
  scored, and not a continuation of its conversation.
- It may be the same model. What matters is that it starts without the
  scorer's context.
- A person can review instead, following the same steps.

## What the reviewer gets

The review is **blind**: the reviewer scores each item itself and never sees
the score it is checking. A reviewer that can see the answer tends to agree
with it. `docs/ORCHESTRATION.md` (stage 5) and `agents/reviewer.md` run it
this way.

Give it only:

1. `method/RUBRIC.md` (the rules and anchors).
2. `profile/evidence.json` (every fact and its level).
3. The postings for the roles under review, from `market/roles/latest.json`
   (and `market/roles/manual.json`), plus `market/orgs.json` and
   `config.json`.
4. The list of items to review (role or organisation id and dimension). Mix
   in other new or changed items, so the list does not show which scores are
   high.

Do **not** give it:

- Any score, band, level or run file: nothing from `eval/`, `report/`,
  `campaign/` or `intake/`.
- The scorer's `note` fields or any other reasoning.
- The person's hopes, the conversation, or the plan.

## What the reviewer does

1. **Score every item itself.** For each one, find the highest anchor the
   evidence actually meets, and name the evidence ids that prove it.
2. **Look for generosity.** Look especially for:
   - achievement claims counted above 1 with only one source;
   - D3 above 1 based on a LinkedIn connection alone (a connection is not
     someone who knows the work);
   - D2 for work a stranger cannot check;
   - D4 for generic strengths every applicant claims;
   - D6 that ignores a blocker in the posting text, or a location the person
     cannot work in;
   - hard requirements in the posting.
3. **Set the flags.** Should `hard_requirement_lacking` be set? Should
   `eligibility_blocked`? A wrong "not blocked" is the most expensive mistake
   in the file.
4. **Justify every score.** Each score names the anchor (for example "D3
   anchor 1: first-degree contact, has not seen the work") and the evidence ids
   (or their absence).

The lead then compares the reviewer's score with the scorer's: the same score
is agreed, a different one goes to the tie-break below. Every score above 2
is challenged this way, because each one is scored again from scratch.

## Recording the review

The scoring agent applies the agreed changes to the judgement files:

- Set the `score` to the one that stands (agreed, or the middle of three). Where a factor was judged twice (`judgings`), the reviewer checks the averaged score; the `score` you write settles it and counts instead of the average, and the `judgings` stay so the range still shows.
- Set `reviewed_on` to today and write a one-line `reviewer_note`:
  - in `eval/judgements.json`, on the role judgement (covers D1, D2 and D4)
    or on a single dimension entry;
  - in `eval/profile-dimensions.json`, on each D3, D5, D7 or D6 rule entry
    reviewed (or once at the top level for the whole file).
- Re-run `python3 scripts/score.py`.

## When the scorer and reviewer disagree

- **Same score:** agreed.
- **One point apart:** the reviewer's score stands without a tie-break. Record
  the dispute with `decided_by` set to `reviewer_one_point` and no tie-break
  score. The score still cannot exceed the evidence cap or other caps.
- **Two or more points apart:** a second fresh reviewer scores the item blind,
  and the **middle of the three scores** stands (scorer, reviewer, tie-break).
  Until then it counts as 2 and is not marked reviewed.
- Every score, whichever way it moves, still needs evidence that meets its
  anchor under the verification ladder.
- The scorer may not argue the point again in the same run. Instead, add an
  open question or a plan action that would produce the missing evidence.
- Record each disputed item in `eval/reviews/<date>.json`: item id, the three
  scores, the anchor and evidence ids each cited, and the score that stands.
  The format is below; `scripts/validate.py` checks it.

## The dispute log: `eval/reviews/<date>.json`

One file per review date (`schemas/reviews.schema.json`). Only disputed
scores go in it; agreed scores are recorded as `reviewed_on` and
`reviewer_note` on the entry, as above.

```json
{
  "schema_version": 1,
  "date": "2026-10-26",
  "disputes": [
    {
      "item_id": "initech:i-0001/D2",
      "scorer":    {"score": 4, "anchor": "D2 anchor 4: better than most shortlisted applicants", "evidence": ["E04", "E15"], "by": "scorer"},
      "reviewer":  {"score": 3, "anchor": "D2 anchor 3: meets it, one case study", "evidence": ["E15"], "by": "reviewer"},
      "tie_break": {"score": 3, "anchor": "D2 anchor 3: comparable to a typical shortlisted applicant", "evidence": ["E04", "E15"], "by": "tie-break reviewer"},
      "stands": 3,
      "decided_by": "middle_of_three"
    }
  ]
}
```

- `item_id` names the judgement entry: `<role id>/D1` (or `D2`, `D4`) in
  `eval/judgements.json`; `D3/<organisation id>` (or `D5`, `D7`, with
  `default` allowed) or `D6/<location class>` in
  `eval/profile-dimensions.json`.
- Each score names the anchor it claims to meet and the evidence ids it
  cites (an empty list means "no evidence").
- `decided_by` is `reviewer_one_point` when the scores differ by exactly one
  and the reviewer score stands, with `tie_break` set to `{"absent": true,
  "why": "..."}`; `middle_of_three` once the tie-break has run;
  `awaiting_tie_break` while it has not (`tie_break` is then
  `{"absent": true, "why": "..."}`, and the entry gets no `reviewed_on`, so
  a score above 2 counts as 2); or `earlier_rule` for history decided under
  an older rule, such as one imported from another campaign, with a `note`
  saying how. Never write a tie-break score that did not happen.
- `validate.py` checks that the file date matches its name, that the middle
  of three is the score that stands, that every evidence id exists, and that
  the judgement file agrees (the same score, and `reviewed_on` set) unless the
  entry has been judged again since.

## Copy-paste reviewer prompt

```
You are an independent, sceptical reviewer for a career evaluation. You have
not seen the scorer's scores or reasoning and must not ask for them.

You have: the rubric (method/RUBRIC.md), the evidence file
(profile/evidence.json), the job postings, the organisation notes, and a list
of items to review (role or organisation id and dimension). If you are given
a score, a band, a level or the scorer's notes, say so and stop: the review
is no longer independent.

Rules:
- Competitive employers reject most applicants. Assume "unlikely" unless the
  evidence says otherwise.
- For each item, find the highest rubric anchor the evidence actually meets
  and give that score, with the evidence ids that prove it.
- Look hard for generosity: achievement claims above 1 with one source; a warm
  path score above 1 from a LinkedIn connection alone; proof of work a
  stranger cannot check; organisation-specific edge that every applicant
  claims; eligibility or location problems in the posting text; hard
  requirements in the posting.
- Never invent evidence. Never use or infer age, gender, ethnicity,
  disability, religion or family status.

Output, one line per item:
- id, dimension, your score, the anchor met, the evidence ids (or "no
  evidence")
Then any flags you would set (hard requirement lacking, eligibility blocked),
each with the posting sentence that shows it.
```
