# LVLme 0.7.0: goals and campaigns

5 November 2026. LVLme now works with goals and campaigns only. This page
covers the engine part of the release: steadier scoring (rules version 1.2)
and the end of LVLme quick. The lead adds the other parts when the work is
merged.

## Scoring rules 1.2

- **Judge twice and average.** Requirements match, proof of work and
  organisation edge are judged twice, by two helper agents or two passes that
  cannot see each other. Each judging is capped by its evidence on its own,
  then the two are averaged to a whole point. A half rounds down.
- **A fit range.** Every role carries `fit_low` and `fit_high` beside `fit`,
  so you see how far the two judgings disagreed instead of one number.
- Older judgement files with one score per factor still work.

## How steady is it? Measured, honestly

We ran the same decent CV and the same job three times with Codex through the
new instructions (a one-job campaign, each judged twice). The best fits were
26, 24 and 19, a spread of 7 points. The ranges the runs reported were 15 to
26, 24 to 26 and 19 to 26. The old quick path scored the same CV five times
at 20 to 22, but it checked fewer factors, so the two numbers are not directly
comparable. **This sample does not show that judging twice makes the score
steadier**; it shows the disagreement instead of hiding it. Three runs on one
CV is a small test, and we make no steadier claim.

## LVLme quick is gone as a product

LVLme works with a goal: the role you want, at which organisations, where,
and by when. Say "run LVLme" and tell it your goal.

Full changelog: [CHANGELOG.md](https://github.com/mark-hallam/lvlme/blob/v0.7.0/CHANGELOG.md)
