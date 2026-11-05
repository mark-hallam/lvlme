# LVLme 0.7.2: job match beside fit

6 November 2026. A clearer way to find jobs that suit your experience, and a
clearer question when LVLme has not asked who you know at an organisation.

- Each role now has a job match beside its fit. Job match uses requirements,
  proof of work, what the organisation values, and eligibility and location,
  with their weights rescaled to 0 to 100. It is shown in the role panel and
  in the file agents read.
- If LVLme has not asked whether you know anyone at an organisation, it says
  "not asked yet" and asks once per organisation. Missing evidence still
  counts as zero; it is no longer described as knowing nobody.

Fit, interview and offer bands, levels, and gaps are unchanged. Job match
helps compare jobs. It is not a probability of getting an interview or offer.
This release does not claim to make the agent's judgements more repeatable
or to broaden the job sources searched.

All 704 offline tests pass on macOS. Both plugin manifests pass strict
validation. Windows is not tested yet. See the
[changelog](https://github.com/mark-hallam/lvlme/blob/v0.7.2/CHANGELOG.md).
