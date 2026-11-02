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

Give it:

1. `method/RUBRIC.md` (the rules and anchors).
2. `profile/evidence.json` (every fact and its level).
3. The scores: the newest `eval/runs/<date>.json`, or the judgement files
   **with every `note` field removed**.
4. The postings for the roles under review, from `market/roles/latest.json`.

Do **not** give it:

- The scorer's `note` fields or any other reasoning.
- The person's hopes, the conversation, or the plan.

## What the reviewer does

1. **Challenge every score above 2.** For each one, find the anchor it claims
   to meet and the evidence ids that support it. If either is missing or weak,
   lower it.
2. **Challenge anything generous.** Look especially for:
   - achievement claims counted above 1 with only one source;
   - D3 above 1 based on a LinkedIn connection alone (a connection is not
     someone who knows the work);
   - D2 for work a stranger cannot check;
   - D4 for generic strengths every applicant claims;
   - D6 that ignores a blocker in the posting text, or a location the person
     cannot work in;
   - hard requirements in the posting that the judgement did not flag.
3. **Check the flags.** Is `hard_requirement_lacking` right? Is
   `eligibility_blocked` right? A wrong "not blocked" is the most expensive
   mistake in the file.
4. **Justify every change.** Each change names the anchor (for example "D3
   anchor 1: first-degree contact, has not seen the work") and the evidence ids
   (or their absence).
5. **Agree explicitly.** For each score it accepts, the reviewer says so.
   Silence is not agreement.

## Recording the review

The scoring agent applies the agreed changes to the judgement files:

- Set the `score` to the one that stands (agreed, or the middle of three).
- Set `reviewed_on` to today and write a one-line `reviewer_note`:
  - in `eval/judgements.json`, on the role judgement (covers D1, D2 and D4)
    or on a single dimension entry;
  - in `eval/profile-dimensions.json`, on each D3, D5, D7 or D6 rule entry
    reviewed (or once at the top level for the whole file).
- Re-run `python3 scripts/score.py`.

## When the scorer and reviewer disagree

- **Same score:** agreed.
- **Different scores:** a second fresh reviewer scores the item blind, and the
  **middle of the three scores** stands (scorer, reviewer, tie-break). Taking
  the lower of two would build a downward bias into every run; the middle of
  three is honest in both directions.
- Every score, whichever way it moves, still needs evidence that meets its
  anchor under the verification ladder.
- The scorer may not argue the point again in the same run. Instead, add an
  open question or a plan action that would produce the missing evidence.
- Record each disputed item in `eval/reviews/<date>.json`: item id, the three
  scores, the anchor and evidence ids each cited, and the score that stands.

## Copy-paste reviewer prompt

```
You are an independent, sceptical reviewer for a career evaluation. You have
not seen the scorer's reasoning and must not ask for it.

You have: the rubric (method/RUBRIC.md), the evidence file
(profile/evidence.json), the scores (with the scorer's notes removed), and the
job postings.

Rules:
- Competitive employers reject most applicants. Assume "unlikely" unless the
  evidence says otherwise.
- Challenge every score above 2. For each, name the rubric anchor it meets and
  the evidence ids that prove it. If you cannot, lower it.
- Look hard for generosity: achievement claims above 1 with one source; a warm
  path score above 1 from a LinkedIn connection alone; proof of work a
  stranger cannot check; organisation-specific edge that every applicant
  claims; eligibility or location problems in the posting text; hard
  requirements the scorer did not flag.
- Never invent evidence. Never use or infer age, gender, ethnicity,
  disability, religion or family status.

Output, for each role or entry reviewed:
- id, dimension, scorer's score, your score
- AGREE or CHANGE
- one line: the anchor and the evidence ids (or "no evidence")
Then a list of any flags (hard requirement lacking, eligibility blocked) you
would change, with the posting sentence that shows it.
```
