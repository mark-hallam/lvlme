# LVLme 0.7.3: fairer job checks for Australia

7 November 2026. Roles outside software are judged by what the posting
asks for, Australian eligibility rules are caught, and a job from any site
can be added by link or pasted text.

- Whether a role needs heavy coding is judged from the posting itself (its
  duties, requirements and description), not from words in the title. A
  civil, site, maintenance or biomedical engineer, or a property developer,
  is no longer marked down for not writing production code. A software,
  backend or site reliability title still counts.
- Postings are checked for Australian eligibility rules: health
  practitioner registration (AHPRA), teacher registration, a Working With
  Children Check, a national police check, an Australian Government security
  clearance level, and a construction White Card. Each has its own interview
  question, asked only when an open role needs it. A police check, a Working
  With Children Check or a White Card can be cleared by a plan action;
  registration and clearance stay hard by default.
- `scripts/add_job.py` adds one job from a link or a text file (SEEK,
  Indeed, a hospital or government board, or any page you paste), saves it
  for a manual target, and `fetch_roles.py` scores it with the rest.
- Groundwork for a requirement checklist beside today's fit:
  `scripts/_checklist.py` scores a saved list in `eval/checklists.json`
  and shows the verdict on the role screen. Nothing writes that file yet,
  so no run shows a checklist until the extraction step is built. Today's
  fit is unchanged by it.

Fit, interview and offer bands, levels and gaps are worked out the same
way. One difference you may see: a role that was dropped or marked as heavy
coding because of its title alone can now be kept, or kept without that
mark, when its posting does not describe coding work.

All 742 offline tests pass on macOS. Windows is not tested yet. Built with
Cursor (Composer 2.5), reviewed by Grok, and checked by hand: tests rerun,
the full diff read, every review finding retested. See the
[changelog](https://github.com/mark-hallam/lvlme/blob/v0.7.3/CHANGELOG.md).
