# LVLme 0.7.5: relocation is part of the profile

7 November 2026. Whether you would move for a role, and on what terms, is now
recorded once and shown beside the pay of every role outside your home area.

- **Your answer, recorded once.** The intake asks where you would move, from
  when, and on what terms: the lowest yearly pay you would move for, whether
  the employer must pay the visa, and any organisation worth the move at any
  pay. The answer lives in your private config as `candidate.relocation`,
  with the evidence item behind it.
- **Shown beside pay on every role outside home.** The role card has a Pay row
  with the posting's pay, then one line: "A move. You said you would move for
  this: anywhere, from now, for USD 300,000 a year or more. The posting's pay
  meets your floor." When the posting's pay is below your floor, in another
  currency, unnamed or not stated, the line says so and asks you to check or
  to ask early. The roles list marks each one "a move" or "you would not
  move", the Today screen adds a sentence when your best role is a move, and
  the briefing for agents carries the same.
- **Shown, not scored.** The judged eligibility and location rule stays the
  only scoring input. `scripts/validate.py` checks the field against your
  location classes, targets and evidence, and warns when a rule contradicts a
  "no" or the question was never asked.
- **Checklist:** "worth applying" needs at least one must-have row fully met;
  otherwise the verdict is "stretch".

Upgrade: `git pull` in the engine folder, or `git clone --branch v0.7.5
https://github.com/mark-hallam/lvlme`. No workspace change is needed; add
`candidate.relocation` to your config when you answer the question.

All 781 offline tests pass on macOS. Both plugin manifests pass validation.
Windows is not tested yet. See the
[changelog](https://github.com/mark-hallam/lvlme/blob/v0.7.5/CHANGELOG.md).
