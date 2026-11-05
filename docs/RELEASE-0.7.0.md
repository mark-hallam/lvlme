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

## LVLme quick is gone

LVLme works with a goal: the role you want, at which organisations, where,
and by when. Say "run LVLme" and tell it your goal.

Full changelog: [CHANGELOG.md](https://github.com/mark-hallam/lvlme/blob/v0.7.0/CHANGELOG.md)
