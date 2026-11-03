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
   `scripts/validate.py` warns above the cap. A short list gets done. Park
   the rest with status `later` instead of raising the cap: they stay in the
   plan with their effects and dates, ready to switch on.
4. **Done needs evidence.** An action can be marked `done` only with
   `done_evidence`: a link, a file path or an email reference.
   `scripts/validate.py` reports an error otherwise.
5. **Never fabricate.** No invented experience, numbers, contacts or stories
   in any draft.
6. **Follow each organisation's rules on AI use.** Where a target's
   `ai_policy.first_draft_by_person` is true, never write its application
   answers, cover letters or résumé text: write a brief and review the
   person's own draft (see "When an organisation asks for your own first
   draft" below).

## Each action

| Field | What to put |
|---|---|
| `id` | `A01`, `A02` and so on. Never reuse an id. |
| `title`, `why` | What to do, and why it matters, in plain words. |
| `status` | `todo`, `doing`, `later`, `done` or `dropped`. `todo` and `doing` are active. `later` is parked (see below). |
| `owner` | `you`, `agent` or `both`. |
| `dimension` | The dimension it should raise. |
| `orgs`, `gap_id`, `strategy_ids`, `metric` | Optional links: the organisations, the gap in the leaderboard, the TOWS strategies, and the north-star metric id it should move. |
| `expected_points` | Fit points gained **per affected role** if it works. Work it out from the rubric: (new score minus current score) / 5 x weight. |
| `roles_affected` | How many of the top roles it would lift. The gap leaderboard gives this. |
| `chance` | Your honest chance it works, from 0 to 1. |
| `effort_hours` | Hours of the person's time. |
| `done_when` | The evidence that will prove it done. |
| `done_evidence` | Filled in when it is done. |
| `target_date` | When it should land. The dashboard's projection applies it on this date. |
| `effects` | What it changes if it works (see "The projection" below). |
| `started_on`, `finished_on`, `draft`, `notes` | Optional. |

## Parked actions (`later`)

An action with status `later` is a real plan action that is not being worked
on yet, for example the next phase of a roadmap. It keeps its id, effects,
target date and chance, so nothing has to be written again when it starts.

- It does **not** count towards `max_active`.
- It is left out of the projection, the next-level sets, the quests and
  "today's actions", and starts switched off in the dashboard's What if rail.
  Switch it on there to see what it would add; it then counts like any open
  action, on that page only. The agent files (`report/for-agents/`) list it
  under "Parked for later".
- To start it, set `status` to `todo` (or `doing` with `started_on`), keeping
  the active list at or under the cap.
- Prefer `later` to the plain-text `backlog`: the backlog is for ideas that
  are not yet actions (no effects, no done-when).

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

## The projection

The dashboard draws three paths from today to the plan's end date: expected,
best case and do nothing. They come from each open action's `effects`:

```json
"effects": [
  {"dimension": "D3", "set_at_least": 2, "scope": {"orgs": ["initech"]}},
  {"dimension": "D7", "delta": 1, "scope": {"role_ids": ["initech:i-0001"]}}
]
```

- `delta` raises the factor by that much; `set_at_least` raises it to that
  level. `scope` can name `orgs`, `families`, `location_classes` and
  `role_ids`; a missing or empty list means every role.
- `"effects": []` says the action changes no score (for example fixing an
  overclaim, which protects credibility). With no `effects` field at all, the
  dashboard estimates one from `expected_points` on the action's `dimension`
  and `orgs`, and says so.
- Actions apply in `target_date` order. Open actions with no date count at the
  end date. Done and dropped actions are left out: a done action is already in
  today's scores. Parked (`later`) actions are left out too, unless switched
  on in the What if rail.
- **Expected** moves each factor by the action's `chance` times the rise.
  **Best case** assumes every action lands. **Do nothing** stays flat.
- **Caps keep it honest.** `projection_caps` sets the most the plan can add to
  each factor over today's score (defaults: D1 0, D2 1, D3 2, D4 1, D5 1, D6 1,
  D7 3), and no factor goes above 5. Years in a role don't change in a few
  months, so D1 stays put by default.
- **Blockers you can't clear stay blocked.** A role whose judgement sets
  `hard_eligibility_block: true`, or that is blocked by a type listed in
  `eligibility_blockers.hard_types` (default: export control, citizenship and
  security clearance), keeps D6 at 0 in every path.
- `baseline_date` (Day 1, default the first run) and `end_date` (default 90
  days after the latest run, later if an action's target date needs it) frame
  the chart.

## Path to the top band (optional)

`eval/ceilings.json` (see `schemas/ceilings.schema.json`) holds the agent's
view of how high the promising roles could go: today, likely in 12 months,
the ceiling on evidence the person can show, and the ceiling once unconfirmed
history is confirmed; what 5 out of 5 looks like per factor; a phased
roadmap; honest odds in words; and what each run should watch for. The
dashboard shows it as the "Path to the top band" view (aimed at 85, where
Strong starts, unless `target_fit` says otherwise) and hides that view when
the file is absent. Revisit it when a role's picture changes, not every run.

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
`campaign/metrics-history.json` and shows each one's change since Day 1 under
"Campaign progress".

## Warm paths: progress with each contact

Referrals are the biggest lever, and they are slow, so the person needs to see
them move before any score does. `campaign/warm-paths.json`
(`schemas/warm-paths.schema.json`) records, for each contact the person is
warming up at a target organisation, one stage on this ladder:

| Stage | Means |
|---|---|
| `followed` | You follow their work; they may not know you yet. A LinkedIn connection you have never spoken with is here too. |
| `talked` | A real exchange: a reply, a call, a chat at an event. |
| `connected` | A two-way line: they would recognise your name and reply. |
| `knows_your_work` | They have seen something you made or did. |
| `would_refer` | They have said they would refer you, or introduce you to the hiring manager. |

Each contact has an `id` (W01, W02 and so on), `org` (a target id), `person`,
`stage` and `updated_on`, and optionally `role` (their job title),
`next_step` (one small, honest step), `action` (the plan action it belongs
to), `evidence` and `history` (each stage with its date, oldest first).

- **It changes no score.** `score.py` never reads this file. The warm path
  factor (D3) is judged from evidence against the rubric's anchors
  (`method/RUBRIC.md`), so "would refer" lifts a score only once their own
  words (an email or a message) are recorded in `profile/evidence.json`.
  `validate.py` warns when a contact is at `would_refer` with no evidence.
- **The person's own account.** Record a stage when the person tells you,
  never from a guess, and never contact anyone to check it. When they say a
  contact has moved on, set `stage` and `updated_on` and add a `history`
  entry. Other agents only append the news to `campaign/inbox.md`.
- **One entry per person.** People found by the network map can be added as
  `followed`; people met elsewhere belong here too, even with no LinkedIn
  connection.
- **Names stay private.** The dashboard shows "a contact" and the agent files
  show "[contact]" unless the person opts in (`privacy` in `config.json`); in
  sensitive mode the agent files keep only the counts.

The dashboard shows one small strip per organisation under Do next (filled to
the furthest stage anyone there has reached, with the stage in words and the
count at each stage), and the contacts with their next steps in the
organisation's pane. The agent briefing lists the same.

## When an organisation asks for your own first draft

Some organisations publish rules on how candidates may use AI. Anthropic's
candidate AI guidance (https://www.anthropic.com/candidate-ai-guidance) says
"Please create your first draft yourself, then use Claude to refine it". It
does not allow AI-written answers to application questions, asks that
take-home tests and live interviews are done without AI unless it says
otherwise, and encourages using AI to research, practise and prepare.

Record such a rule on the target in `config.json`, only from the
organisation's own page, with its address:

```json
"ai_policy": {"first_draft_by_person": true, "source": "https://...", "checked_on": "2026-11-02"}
```

Before drafting application text for any target, check whether it publishes
guidance like this, and re-read the page before each application, since such
pages change. Never record a policy you have not read on the organisation's
own page, and never assume one organisation's rules apply to another.

For a target with `first_draft_by_person` true, say so plainly before any
application help: "Anthropic asks for your own first draft. Write it, then
I'll review it." (with the employer's name). Then:

1. **Never write** its application answers, cover letter or résumé text, in
   whole or in part.
2. **Write a brief instead**, `campaign/drafts/<org>-<role>-brief.md`: the
   role's requirements (from the posting), the evidence that meets each one
   (evidence ids) and the honest gaps, what to lead with and why, and the
   self-check list below. The plan action is the person's (`owner` `you`).
   Every draft for this employer starts with a line saying what it is, the
   policy's address and the date you last read it:

   ```
   LVLme brief. Policy: https://www.anthropic.com/candidate-ai-guidance, checked 2026-11-02.
   ```

   The kind is `brief`, `review` (of the person's own draft), `prep`
   (research, practice, questions to ask) or `outreach` (a message to a
   person, not part of an application). `scripts/validate.py` reports an
   error for any draft in `campaign/drafts/` whose path names the employer
   and that has no such line or another kind, and a warning when the policy
   was last checked more than 30 days ago: re-read the page, then update
   the date here and `checked_on` in `config.json`.
3. **Review the person's own draft** when they share it: what is unclear,
   what has no evidence behind it, what differs from the single source of
   truth in `profile/consistency.md`, and what from the brief is missing.
   Suggest changes to their sentences; keep their words and never replace the
   draft with new text.
4. **Take-home tests and live interviews are the person's alone** unless the
   organisation says AI is allowed. Help before, never during.
5. **Preparation is fine**: research the organisation, practise interview
   answers, build a study guide, prepare questions to ask.

The self-check list, for the person, before they submit:

- [ ] I wrote the first draft myself; any AI help only refined my own words.
- [ ] No answer to an application question was written by AI.
- [ ] Every claim has an evidence id in the brief and matches
      `profile/consistency.md`.
- [ ] Each hard requirement in the posting is met, or the gap is named
      honestly.
- [ ] It leads with the strongest verified evidence in the brief.
- [ ] I could defend every sentence in an interview.

## Cadence

- **Weekly**, plus a run whenever something changes: an action done, new
  evidence, a new export. Scores only move when evidence changes, and a full
  run can start about 40 helper agents (for around 300 open roles).
- The person decides the rhythm. The agent never changes the schedule
  itself.

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
| For an organisation that asks for your own first draft: a brief, then your draft, then a review of it | 3 to 5 hours | The brief in `campaign/drafts/`, then the person's confirmation email from the job board |

For an organisation with `ai_policy.first_draft_by_person` true, the résumé
and application moves above become a brief and a review of the person's own
draft, as described earlier.

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
   strategies, highest priority first, until the active list is full. Park
   anything beyond the cap as `later`; when an active action is done or
   dropped, start the highest priority parked one.
4. Update the north-star metric values, with evidence ids.
5. Write any outreach as drafts in `campaign/drafts/`.
