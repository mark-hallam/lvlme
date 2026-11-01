# The campaign engine

The campaign turns gaps into a short, prioritised, evolving list of actions.
Every action is a bet: it should raise a score or a north-star metric. Runs
check whether it did, so effort follows what actually moves the number.

Everything lives in `campaign/plan.json` (see `schemas/plan.schema.json`).

## Rules

1. **Drafts only.** The engine never applies, sends, posts or changes an
   account. Outreach, applications and posts are written as drafts in
   `campaign/drafts/` for the person to read, edit and send themselves.
2. **Attack the binding constraint first.** For most non-traditional
   candidates the order is: eligibility, a warm path, visible proof of work,
   then a tailored application.
3. **At most 8 active actions** (`max_active`, todo plus doing).
   `scripts/validate.py` warns above the cap. A short list gets done.
4. **Done needs evidence.** An action can be marked `done` only with
   `done_evidence`: a link, a file path or an email reference.
   `scripts/validate.py` reports an error otherwise.
5. **Never fabricate.** No invented experience, numbers, contacts or stories
   in any draft.

## Each action

| Field | What to put |
|---|---|
| `id` | `A01`, `A02` and so on. Never reuse an id. |
| `title`, `why` | What to do, and why it matters, in plain words. |
| `status` | `todo`, `doing`, `done` or `dropped`. |
| `owner` | `you`, `agent` or `both`. |
| `dimension` | The dimension it should raise. |
| `orgs`, `gap_id`, `strategy_ids`, `metric` | Optional links: the organisations, the gap in the leaderboard, the TOWS strategies, and the north-star metric id it should move. |
| `expected_points` | Fit points gained **per affected role** if it works. Work it out from the rubric: (new score minus current score) / 5 x weight. |
| `roles_affected` | How many of the top roles it would lift. The gap leaderboard gives this. |
| `chance` | Your honest chance it works, from 0 to 1. |
| `effort_hours` | Hours of the person's time. |
| `done_when` | The evidence that will prove it done. |
| `done_evidence` | Filled in when it is done. |
| `started_on`, `finished_on`, `draft`, `notes` | Optional. |

## Prioritisation

```
priority = expected_points x roles_affected x chance / effort_hours
```

The dashboard computes it and sorts the active list by it. The top 1 to 3 are
"today's actions".

**Worked example.** A role family is weighted D3 = 20 and D7 = 5.

- Warm introduction at one organisation: D3 from 2 to 3 is 1 / 5 x 20 = 4
  points per role, on 6 roles, with a 40% chance, for 3 hours:
  4 x 6 x 0.4 / 3 = **3.2**.
- Tailored résumé for the family: D7 from 1 to 3 is 2 / 5 x 5 = 2 points per
  role, on 12 roles, with a 90% chance, for 4 hours:
  2 x 12 x 0.9 / 4 = **5.4**.

The résumé goes first: smaller per role, but it touches more roles and is
nearly certain to work. Once it is done, the warm introduction leads.

Be honest with `chance`. An inflated chance is the easiest way to fool the
formula.

## Experiments: keep, rework or drop

Every `doing` action is an experiment. The dashboard flags one when at least
3 runs since its `started_on` show no change in both:

- its dimension: no role in the action's scope (its `orgs`, or every role)
  that was open in both the first and the latest of those runs changed its
  score on that dimension, and
- its linked north-star metric (`metric`), if it has one.

Roles that open or close in between do not count as movement, so a shifting
list of postings cannot hide a stalled action.

When an action is flagged, decide:

- **keep**: there is a clear reason it needs longer (say it);
- **rework**: change the approach and restart the clock (`started_on`);
- **drop**: set `status` to `dropped`.

Log every decision in `experiments_log`: `date`, `action_id`, `action`,
`result`, `decision` (`keep`, `rework`, `drop` or `done`) and `why`. Finished
actions get a `done` entry too, so the log shows what worked.

## North-star metrics

Track these in `north_star`, each with `id`, `name`, `current`, `target` and
the evidence ids that prove the current value. The template uses these ids.

| Id | Metric |
|---|---|
| `warm_intros` | Warm introductions to people at target organisations |
| `applications` | Applications to best-fit roles |
| `interviews` | Interviews |
| `offers` | Offers |
| `proof_pieces` | Public proof-of-work pieces |
| `credentials` | Credentials earned |

The dashboard records their values each run in
`campaign/metrics-history.json` and charts them in the Trends view.

## Cadence

- **Daily** during build-up: the first `cadence.build_up_weeks` weeks
  (default 4).
- **Weekly** after that.
- When daily runs stop producing score changes or new evidence (for example
  7 runs in a row), the agent suggests switching to weekly. The person
  decides. The agent never changes the schedule itself.

## Action library

Proven moves, by dimension and by TOWS type (the four strategy types in
`SWOT.md`). Effort is a typical range for
the person's own time. Adapt the wording; keep the done-when.

### By dimension

**D1 Requirements match**

| Move | Typical effort | Done when |
|---|---|---|
| Map each hard requirement in the top 5 postings to evidence, and list the gaps | 2 hours | A gap table saved in `campaign/drafts/` |
| Get a referee to confirm a key achievement in writing | 1 hour | An email or letter from the referee |
| Take a short course that closes a named requirement | 10 to 40 hours | Certificate address |
| Stop targeting a family whose hard requirements cannot be met in the horizon | 15 minutes | Family removed or deprioritised in `config.json` |

**D2 Proof of work**

| Move | Typical effort | Done when |
|---|---|---|
| Open-source a project you own, with a clear README and a release | 4 to 10 hours | Public repository with a tagged release |
| Write a verifiable case study of a past project (numbers a referee can confirm) | 4 to 8 hours | Published page address |
| Build a small, live demo that uses a target organisation's product | 8 to 20 hours | Live address and repository |
| Contribute a fix to an open-source project the target maintains or uses | 4 to 12 hours | Merged pull request address |

**D3 Warm path**

| Move | Typical effort | Done when |
|---|---|---|
| Map the network from the LinkedIn export | 30 minutes | `profile/network.json` updated |
| Ask a first-degree contact for an introduction (draft only) | 1 hour | Their reply, by email or message |
| Ask a second-degree path to open (draft only) | 1 hour | Their agreement, in writing |
| Contribute to a community or forum where target staff are active | 2 hours a week | Links to contributions; a named staff member who replied |
| Attend an event the target runs or speaks at | 3 to 8 hours | Calendar entry plus a follow-up email |
| Ask an insider who knows the work to refer (draft only) | 30 minutes | Their written agreement, then the referral confirmation |

**D4 Organisation-specific edge**

| Move | Typical effort | Done when |
|---|---|---|
| Use the target's product deeply and publish what you learned | 6 to 15 hours | Published write-up address |
| Earn a certification the target issues or values | 10 to 40 hours | Certificate address |
| Join the target's partner or community programme | 1 to 3 hours | Acceptance email |

**D5 Public signal**

| Move | Typical effort | Done when |
|---|---|---|
| Fix overstated or contradicted public claims (from the claims audit) | 1 to 2 hours | Updated page addresses; claims re-audited as supported |
| Publish one useful article about your work | 3 to 6 hours | Published address |
| Make the best repositories public and pin them | 1 hour | Profile address |
| Give a short talk at a meetup | 6 to 10 hours | Event page or recording |

**D6 Eligibility and logistics**

| Move | Typical effort | Done when |
|---|---|---|
| Confirm degree or equivalent, and which visa routes it opens | 1 to 2 hours | Degree certificate file or registrar email; route noted with its source |
| Confirm notice period, intellectual property terms and non-compete scope | 1 hour | Contract clause noted in `intake/answers.md` |
| Decide relocation and on-site limits, and record them | 30 minutes | `intake/answers.md` updated; D6 rules updated |

**D7 Application readiness**

| Move | Typical effort | Done when |
|---|---|---|
| Tailor a résumé per role family | 3 to 5 hours | Résumé file in `campaign/drafts/` |
| Write the two-sentence story and the answer to the strongest objection | 1 to 2 hours | Saved in `campaign/drafts/` |
| Draft a tailored application for a best-fit role, for the person to submit | 2 to 3 hours | The person's confirmation email from the job board |

### By TOWS type

| Type | Typical moves |
|---|---|
| SO (use a strength to seize an opportunity) | Lead with the strongest verified artefact in an application to an open best-fit role; pitch a strength to a newly opened team or office; use a strength in a partner programme application. |
| ST (use a strength to blunt a threat) | Turn a strength into a case study a referee can confirm so it stands out in a large applicant pool; use a strength to qualify for a role type that is less crowded. |
| WO (fix a weakness to unlock an opportunity) | Open a warm path before applying to a new team; publish proof of work in the area a new team is hiring for; confirm an eligibility route before a regional office's roles open. |
| WT (avoid the trap) | Do not apply cold to blocked or out-of-reach roles; do not publish claims you cannot back; wait for a referral before applying where the person would otherwise burn a single application chance. |

## After each run

1. Mark actions done only with evidence.
2. Decide keep, rework or drop for flagged actions, and log why.
3. Add actions from the top of the gap leaderboard and the new TOWS
   strategies, highest priority first, until the active list is full.
4. Update the north-star metric values, with evidence ids.
5. Write any outreach as drafts in `campaign/drafts/`.
