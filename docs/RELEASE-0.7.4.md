# LVLme 0.7.4: a checklist for each job, and job match first

7 November 2026. Each job can now be read as the list of things it asks for,
and checked against your evidence row by row, beside today's fit. And until
you have answered who you know at an organisation, the job itself leads.

- **A requirement checklist beside fit.** Your agent reads the posting three
  times in fresh context and keeps the requirements at least two reads agree
  on, matched by the words they share. You confirm the list ("Is this what the
  job asks for?"). Your agent then marks each row against your evidence three
  times: met, partly, not shown, unknown or not applicable. Code turns the
  votes into a verdict: strong match, worth applying, stretch or not yet, with
  the must-haves met, the three moves that would help most, and the checks
  anyone can get before starting as to-dos. A strong match needs most
  must-have rows fully met, not half met. A list nobody has marked yet says
  so. `python3 scripts/checklist.py` and `method/CHECKLIST.md`. Today's fit
  never changes because of it, and no chance percentage is shown.
- **Job match leads until you answer.** Fit adds who you know, how findable
  you are and a tailored CV to the job-side factors. Before you have answered
  who you know at an organisation, every role there now leads with job match
  on the role card, the dashboard tile, the Today screen and the briefing for
  agents, with one line saying why. Once answered, fit leads. Levels, bands
  and the maths are unchanged.
- **Role fetch:** a National Police Certificate, Queensland's Blue Card and a
  Positive Vetting clearance are detected as eligibility rules.

Tried on a real search before release: one person, six live Melbourne
postings across a known gradient, every AI step by a second maker's model in
fresh context. The ordering came out right in every method; the checklist
told the roles apart best; three marking passes agreed on 63 of 73 rows.

All 756 offline tests pass on macOS. Both plugin manifests pass validation.
Windows is not tested yet. See the
[changelog](https://github.com/mark-hallam/lvlme/blob/v0.7.4/CHANGELOG.md).
