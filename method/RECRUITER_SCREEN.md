# The recruiter screen

The scores say how strong the evidence is. They do not say how the person's
public profile **reads** to a stranger with six seconds and a pile of other
applicants. The recruiter screen does: an independent agent reads the
website, LinkedIn and CV (curriculum vitae) cold, as a recruiter and a
hiring manager at a target organisation would, against 3 to 5 real
postings, and says plainly whether it would advance the person to a phone
screen, and why not.

In practice it finds what the person and their campaign agent have stopped
seeing: a headline that undersells, an overclaim that a reference check
would catch, the one shipped project buried on page two.

## When to run it

- After the first round of profile fixes (`PROFILE_FIXES.md`).
- Whenever the website, LinkedIn or CV changes substantially.
- Before applying to a best-fit role.
- Otherwise about once a month during the campaign.

## The key rule: independence

The screen is only worth having if the reviewer starts cold and sceptical.

- Use a **fresh agent session** started for the screen only: not the agent
  running the campaign, and not a continuation of its conversation. It may
  be the same model. A person (a friend who hires, a mentor) can do it
  instead, with the same prompt.
- Give it **only what a recruiter would see**: the public website address,
  LinkedIn as it stands today (the person saves their profile as a PDF), the exact
  CV file a recruiter would receive, and the postings.
- **Never** give it the scores, the plan, the SWOT, the evidence file, the
  claims audit, earlier screens, or the person's hopes. A reviewer that knows
  the campaign's view anchors on it.
- Tell it to be sceptical: most applicants are rejected, and the default
  call is "no".
- A web search is allowed only if the person agrees. A real recruiter would
  search the name, so it is realistic; it also means the search sees
  whatever is public.

The output schema (`schemas/recruiter-screen.schema.json`) fixes
`fresh_context: true`, `saw_campaign_scores: false` and
`saw_campaign_plan: false`, so a screen that broke the rule does not
validate.

## Running it

1. Pick 3 to 5 real, open postings from `market/roles/latest.json`: the best
   fits, plus one stretch. Copy the full posting text, not just the title.
2. Save copies of what the reviewer will read in `intake/sources/` (for
   example the LinkedIn profile saved as a PDF, the CV file), so quotes can
   be checked later.
3. Fill in `templates/prompts/recruiter-screen.md` (a copy of it is in the
   workspace under `prompts/`). Replace every `{{PLACEHOLDER}}`.
4. Paste it into the fresh session. Do not add anything else.
5. Save the JSON it returns as `eval/recruiter-screens/<YYYY-MM-DD>.json`
   and the summary as `eval/recruiter-screens/<YYYY-MM-DD>.md`.

## What it returns

| Part | What it is |
|---|---|
| `six_second` | Who the person seems to be at first glance, and whether the reader keeps reading (`keep_reading`, `skim`, `move_on`). |
| `roles` | Per posting, after about two minutes: advance to a phone screen, `yes`, `maybe` or `no`, with the single biggest reason, the strongest match and the biggest gap. |
| `stop_and_look` | What made the reader slow down, quoted. |
| `red_flags` | Overclaiming, inconsistencies, vague or jargon lines, each with the **exact quote**, where it is, why it hurts and an honest fix. |
| `missing` | What the reader looked for and did not find. |
| `top_changes` | Up to 10 changes ranked by how much each would raise the chance of a "yes". |
| `remove` | Lines that hurt more than they help. |
| `design_notes` | How the site and CV read on a phone and a desktop: layout, contact path, broken links, whether a recruiting system can read the CV. |

## Checking the screen

The screen is a sceptical opinion. Check it before acting on it:

1. **Quotes.** Find every quote, word for word, in the saved materials. A
   quote that is not there is dropped (and suggests the reviewer
   paraphrased). Set `quotes_checked_on` once done.
2. **Facts.** Where the reviewer says something is missing, check the
   evidence file. Sometimes it is missing from the profile but the person
   has it (an easy win); sometimes it does not exist (a gap, not a wording
   problem).
3. **Changes that add claims.** A suggested change marked
   `needs_evidence: true` can only be made once the evidence exists. Never
   "fix" a missing item by writing a claim the person cannot back.

## Turning it into plan actions

The screen does not change any score by itself: it is not evidence about the
person. It feeds the campaign:

- every red flag of kind `overclaim` or `inconsistency` goes into the claims
  audit (`profile/claims-audit.json`) and, if it is about a title or date,
  into the consistency audit (`CONSISTENCY.md`);
- the top changes become plan actions in `campaign/plan.json`, mostly D5
  (public signal) and D7 (application readiness), with honest `chance` and
  `effort_hours`; write the action ids back into `action_id` and
  `actions_created`;
- a "no" whose biggest reason is a real gap (not wording) becomes, or
  strengthens, a gap in `eval/gap-templates.json`;
- the wording fixes are drafted with `PROFILE_FIXES.md`.

Compare screens over time (how many "yes" and "maybe" calls, whether the
six-second read matches the target), but always run each one fresh, without
the earlier ones.
