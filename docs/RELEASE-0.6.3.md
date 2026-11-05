# LVLme 0.6.3: clearer, fairer scoring rules

5 November 2026. We tested LVLme end to end with real AI agents: a stranger
installing it from GitHub, three simulated weeks of a campaign, the desktop
features with a real AI, and the same CV scored again and again to see how
steady the score is. This release fixes what those tests found and brings in
the scoring rules version 1.1. **How a score is worked out changed**, so a
score from 0.6.2 and one from 0.6.3 are not directly comparable; the
dashboard says so when it compares runs made under different rules.

## Scoring rules 1.1

- **One point apart, the reviewer's score counts.** The old rule counted any
  disagreement as 2, lower than either scorer. Bigger differences still wait
  for a tie-break.
- **Eligibility anchors**, including "the employer says it sponsors visas":
  a possible route, never a confirmed one.
- **Only public links count as checked.** A page a stranger cannot open, such
  as a local test page or one behind a login, counts as self-reported.
  Documents, emails and references are judged as before.
- **Almost none**, a new lowest chance band, so a weak fit and an unrelated
  one read differently.
- **Show it or Build it** on every gap and fix: is the proof missing (days)
  or the skill (weeks or months)? This idea came from a reply to a post about
  LVLme.
- **A score holds when only the judging AI changed** and the evidence did
  not. In a test, switching AI agents moved a best fit from 25 to 19 with
  nothing new about the person. Now, when the judging agent is recorded and
  the evidence is unchanged, the earlier score stands.

## Fixed

- Saying "run LVLme quick" in Claude Code starts it; before, only the typed
  /lvlme-quick command did.
- The autopilot timer line can find Claude Code and runs the commands the
  morning needs.
- Offline mornings, progress made after the morning note, events, repeated
  job titles in different cities and the `--workspace` option all behave as
  you would expect.
- Small wording, naming and output fixes; the full list is in the
  [changelog](https://github.com/mark-hallam/lvlme/blob/v0.6.3/CHANGELOG.md).

## Measured after the change

We scored the same CV five times with Codex on 0.6.3: 18, 20, 20, 25 and 18.
On 0.6.2 the same test gave 20 to 22. The new visa rule worked (Codex and
Claude now read "we sponsor visas" the same way), but one judge still reads
requirements match as 2 one time and 3 the next, so the run-to-run wobble is
not smaller yet. Weak and unrelated candidates now read "Almost none" and a
decent one "Very low", where before all three read the same.

## Not in this release

- The desktop app's fixes for a real AI are in progress on their own branch.
- Judging twice and averaging, to cut the run-to-run wobble, is planned next.
- Whether the odds predict real hiring outcomes is not yet tested: that needs
  real outcomes over months.
