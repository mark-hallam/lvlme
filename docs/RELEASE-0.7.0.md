# LVLme 0.7.0: goals and campaigns

5 November 2026. LVLme now works with goals and campaigns only. This page
covers all three parts of the release: the engine (every factor judged twice,
a fit range, rules version 1.2, the end of LVLme quick), the journey (set a
goal, a starting line, a Today screen, a weekly rhythm, level-up events) and a
proof profile.

## The journey

- **Set a goal** (role, organisations, where, by when). LVLme tests it against
  your starting line and, if no plan reaches it in time, proposes a stepping
  stone with the reason. You choose.
- **The starting line.** Your level, your fit range ("fit about 57 to 61" when
  a role was judged twice) and the date the plan is expected to reach the next
  level, or a plain statement that no plan gets there yet. A first run judges
  only the best few roles so it comes in about 15 minutes; Today says what is
  still being checked.
- **Today first.** The dashboard opens on Today in plain words. Mission control,
  the full dashboard, is one tap away.
- **A weekly rhythm:** a Monday plan note, a Friday review and a count of weeks
  in a row with real evidence.
- **Level-up and goal-reached events**, marked on Today, with a share card that
  names no organisation or person.
- **Outcomes you can choose to share:** a numbers-only export after a plain
  consent screen. LVLme sends nothing anywhere.

## The proof profile

`scripts/proof_profile.py` builds a page of only the claims checked at verified
or corroborated level, each with its public source. It refuses to write if the
page would contain an email, a phone number, a folder path, a private link or
an unchecked claim. Private by default. See docs/PROOF-PROFILE.md.

## Known items for the reviewers

- The accent colour: Today is orange and Mission control is blue. Whether they
  should share one accent is still open.
- Mission control keeps its aviation labels for the chart; Today does not use
  them.

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
