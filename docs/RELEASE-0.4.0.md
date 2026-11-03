# LVLme 0.4.0: warm paths, six job boards, and honest numbers

LVLme is for the job you can't get yet. It works out honestly how far you are
from a job, gives you the steps to get there, and measures again as you go.

This release adds a way to track the people who could open a door for you,
reads three more job boards, and fixes every place where a number on the page
said more than was true. It came from fourteen rounds of building and six
rounds of testing the public version end to end, as a new user would.

How a score is worked out did not change. One thing about which runs are
saved did: see "Scoring again" below.

## Added

- **Warm paths.** A new workspace file, `campaign/warm-paths.json`, records
  how far each contact at a target organisation has come: followed, talked,
  connected, knows your work, would refer. The dashboard shows it under Do
  next. An organisation where your LinkedIn connections include someone, but
  no warm path has started, says "1 connection, not asked yet". It is
  progress only: the score never reads it.
- **Reading your dashboard.** A
  [one-page plain-English guide](for-you/READING-YOUR-DASHBOARD.md) to each
  number on the dashboard, and what to do first.
- **Six job boards for LVLme quick.** Workday, SmartRecruiters and Workable
  links now read properly, as well as Greenhouse, Ashby and Lever: the
  requirements, nice to haves and duties come through, with the employer's
  name as people know it.
- **A demo folder.** `docs/demo/` holds both fictional demos behind one page
  that opens straight from your computer.
- **A changelog.** [CHANGELOG.md](../CHANGELOG.md) lists what changed in
  each version.

## Changed

- **LVLme quick says what it could not check.** Public signal and
  application readiness cannot be judged from one posting and a CV. Each is
  now marked "Not checked", and the fit is a range: "41 today, up to 56 if
  these turn out strong".
- **LVLme quick names a fix it leaves out, and why**, instead of quietly
  showing two fixes where three were promised.
- **Biggest unlocks reads as fit points on one role** ("+12 each, lifts 11
  roles") rather than totals such as "+144" beside scores out of 100.
- **Scoring again.** Running `scripts/score.py` on a later day with nothing
  changed (same inputs, no plan action finished) now saves no new day,
  because it would read as a day with no progress and break your streak.
  `--force` saves it anyway.
- **A shorter first run** and **plain errors**: one line that names the file
  and says what to do, never a Python traceback.

## Fixed

- A role nobody has judged is no longer shown as a measured weak fit.
- The share card no longer says "to an offer" when no offer has come.
- Hybrid roles are no longer called remote.
- One answer for "where will I be if I follow the plan", on every screen.
- The roles heat map reads the same in dark mode.
- Links to files in the repository open the right page.

The full list is in [CHANGELOG.md](../CHANGELOG.md).

## Checked by

- 374 tests pass, including new ones for each fix above.
- `claude plugin validate --strict` on the manifest.
