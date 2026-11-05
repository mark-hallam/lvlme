# Scoring rubric (version 1.2)

## What changed in 1.2

- C1: requirements match (D1), proof of work (D2) and organisation edge (D4)
  are judged twice, independently: two helper agents, or two passes that
  cannot see each other or each other's scores. Both judgings are recorded as
  `judgings: [a, b]` in `eval/judgements.json`, with the evidence ids from
  both (their union) and one note.
- C2: scoring caps each judging on its own (the evidence cap, then the review
  cap), then averages the capped judgings. The average is a whole point and a
  half always rounds down, every time: 3 and 4 give 3, 2 and 3 give 2. A
  doubtful half point is not given. This replaces one judge's single score.
- C3: every role carries `fit_low` and `fit_high`, the fit with every factor at
  its lower judging and at its higher judging, beside `fit` (the average). A
  factor judged once has equal low and high, so an older judgement file with a
  single `score` per factor still works and has a range of one fit. The
  scores that count in the bands, levels and gaps are the averages.
- C4: a `score` written beside `judgings` is the settled score (for example
  after the blind review) and counts instead of the average; the range still
  shows the judgings.
- The blind review (`method/REVIEW.md`) and B6 work as before: the review
  challenges the averaged score, and B6 keeps a factor's previous score when
  only the judging agent changed and the evidence did not.

## What changed in 1.1

- B1: a one-point disagreement is decided by the reviewer's score; larger
  disagreements still need a tie-break reviewer.
- B2: D6 has fixed eligibility and location anchors, including the rules for
  locations with no rule.
- B3: a link counts as checked evidence only if a stranger can open it without
  signing in. Documents, emails, exports and references are not links and keep
  their level as before.
- B4: a new lowest chance band, Almost none, for an interview below 15 and an
  offer below 25, so a weak fit and an unrelated one no longer read the same.
  A missing hard requirement can move Very low down to Almost none. The five
  fit levels are unchanged. Applications already recorded keep the bands they
  were given on the day.
- B5: every gap and every quick fix says what kind it is: Show it (the proof
  is missing, usually days) or Build it (the skill is missing, usually weeks
  or months). A missing kind counts as Build it, with a warning. In LVLme
  quick, the shown fixes list Show it first; which fixes are shown, and the
  points, are worked out as before. The campaign shows the label next to each
  gap; its plan order is unchanged.
- B6: when a role's requirements match, proof of work or organisation edge is
  judged again by a different AI agent (from `judged_by`) and the evidence it
  cites is unchanged (same ids, levels and claims), the previous score stands,
  up or down, and the run says so. New evidence means the new score counts.
  Judgements with no recorded agent work as before.

Purpose: estimate, honestly, a person's chance of being hired into a specific
open role at a specific organisation, and show what would raise it. Every run
uses the same rubric, so a change in score reflects a change in evidence, not
a change in the scorer's mood.

The rules marked **(enforced)** are applied by `scripts/score.py`, so they hold
even if a judgement file says otherwise. Everything else is the judge's
responsibility, checked by the reviewer (see `REVIEW.md`).

## Ground rules

1. **Evidence or it scores zero (enforced).** Every point needs a cited
   evidence id from `profile/evidence.json`. A score with no evidence cited
   counts as 0. Claims with no source are listed as "verify to unlock"
   questions instead.
2. **No flattery.** Score against what the posting actually asks for and what
   a strong competing applicant would bring. Competitive employers reject the
   large majority of applicants. The default answer is "unlikely".
3. **Separate scorer and reviewer (enforced for scores above 2).** One pass
   scores. A second, sceptical pass challenges every score above 2 and must
   agree before the score stands.
4. **Same scale every run.** Changing this rubric bumps its version, and the
   report notes that runs before and after are not directly comparable.
5. **Never score protected attributes.** Age, gender, ethnicity, disability,
   religion and family status are never asked about, inferred or scored. Work
   rights are recorded only as the person states them, and only to match what
   a posting legally requires.

## The seven dimensions

Each role is scored 0 to 5 on each dimension. The weights below are the
defaults; change them per goal in `config.json` under `scoring.weights`.

| # | Dimension | Default weight | Judged | What it measures |
|---|---|---|---|---|
| D1 | Requirements match | 25 | per role | Hard requirements in the posting: years in a comparable role, domain, named skills, degree. |
| D2 | Proof of work | 20 | per role | Shipped, checkable work relevant to this role and this organisation's products. |
| D3 | Warm path | 20 | per organisation | People inside who know the person's work and would refer or vouch for them. |
| D4 | Organisation-specific edge | 10 | per role | Something this organisation values that most applicants lack. |
| D5 | Public signal | 10 | per organisation | What a hiring manager finds: writing, site, code, talks, posts, followers. |
| D6 | Eligibility and logistics | 10 | per location class | Work rights, visa route, location and relocation fit with where the role sits. |
| D7 | Application readiness | 5 | per organisation | A tailored résumé, portfolio and crisp story ready for this role. |

**Fit score** = the sum over all seven of (score / 5 x weight), giving 0 to
100, rounded to one decimal. If the weights do not add up to 100, the result
is rescaled to 100 (enforced).

Where they live:

- D1, D2 and D4: `eval/judgements.json`, one entry per role id.
- D3, D5 and D7: `eval/profile-dimensions.json`, one entry per target
  organisation id, with an optional `default` entry used for any organisation
  without its own.
- D6: `eval/profile-dimensions.json` under `D6_rules.classes`, one entry per
  location class (from `config.json`), plus a note for blocked roles under
  `D6_rules.blocked`.

### Anchors (all dimensions)

| Score | Meaning |
|---|---|
| 0 | Absent, or claimed with no evidence. |
| 1 | Weak or tangential. |
| 2 | Partial: meets some of it; a reviewer would see a clear gap. |
| 3 | Meets it: comparable to a typical shortlisted applicant. |
| 4 | Strong: better than most shortlisted applicants. |
| 5 | Exceptional: a reason to hire on its own. |

### Dimension notes

**D1 Requirements match.** Score against the posting's stated requirements,
not the title. If the posting states a hard requirement the person plainly
lacks (for example "computer science degree required" or "5 or more years as a
software engineer"), set `hard_requirement_lacking` to true with a short
`hard_requirement_note`. D1 is then capped at 1 (enforced).

**D2 Proof of work.** Count shipped things a stranger can check: a public
repository, a release history, a live product with users, a published case
study, a paper. Software built with AI agents counts when it is verifiable.
Volume without outcomes counts less than one shipped thing with users. Private
work counts only if a second source (a referee, a press article, an email from
the client) backs it up.

**D3 Warm path.** Use these anchors exactly:

| Score | Meaning |
|---|---|
| 0 | Nobody known at the organisation. |
| 1 | A first-degree contact in an unrelated team who has not seen the person's work. |
| 2 | A second-degree path that someone has agreed to open. |
| 3 | A named insider who knows the person's work. |
| 4 | That person has agreed to refer. |
| 5 | Referral submitted. |

`scripts/network_map.py` gives the first-degree contacts at each target. A
LinkedIn connection proves the connection exists, not that the person knows
your work: that needs their own words (an email, a message, a referee note).
The warm-path tracker (`campaign/warm-paths.json`, `method/CAMPAIGN.md`)
records how far each contact has come, but it is the person's account, not
evidence: judge D3 from `profile/evidence.json` only.

**D4 Organisation-specific edge.** Something this organisation values that
most applicants lack. Examples for an AI lab goal: deep daily use of that lab's
own products with published results, domain experience in a sector the lab is
selling into, or a contribution to a project the lab maintains. Generic
strengths that every applicant claims ("passionate about AI") score 0.

**D5 Public signal.** What a hiring manager would find in five minutes of
searching: writing, a personal site, public code, talks, podcasts, posts, and
how many people follow them. Score what exists and is findable, not what is
planned.

**D6 Eligibility and logistics.** Scored against where the role sits and the
person's stated work rights and willingness to move. Use these anchors:

| Score | Eligibility and location |
|---|---|
| 5 | The role is in the person's own city, or remote there, and they have full work rights. |
| 4 | They have full work rights in the role's country, must move, and are willing to move. |
| 3 | They need a visa or work right they do not hold, and have a confirmed route for this person: an existing right, a written sponsorship offer, or a listed eligibility clearance. |
| 2 | They need a visa, the posting says the employer sponsors visas, but no route is confirmed for this person. An employer saying "we sponsor" is a possible route, not a confirmed one. |
| 1 | They need a visa or work right they lack and the posting says nothing about sponsorship, or they are unsure about moving. |
| 0 | They cannot lawfully work there because of an uncleared eligibility blocker, the posting says it does not sponsor and they have no route, or they will not move for an on-site role. |

Set one entry per location class in `D6_rules.classes`. `scripts/score.py`
picks the best class among the role's locations (enforced). A judgement can
set `location_class` to override the automatic choice. In a full campaign, a
location class with no rule scores 0, and `scripts/validate.py` warns with the
class name. LVLme quick has no rules file, so its judge and reviewer score the
posting's location against what the person said using this table. A quick
reviewer must not score D6 as 0 only because no rules file exists.

## Links and checkable evidence

A link counts as checked at the `verified` or `corroborated` level only when a
stranger can open it from the public internet without signing in: a public
HTTPS (Hypertext Transfer Protocol Secure) address on a public host. This rule
is about links only. Documents, emails, exports and references are not links
and are judged by the evidence levels above. A page behind a login or
available only "on request" is not public evidence. `localhost`, `127.x`,
`::1`, private network addresses (`10.x`, `192.168.x`, and `172.16` to
`172.31`), names ending in `.local`, `.internal` or `.lan`, `file:` links and
other non-web links do not count as checked evidence. If every source of an
item is a link and none of them is public, it counts as self-reported.

**D7 Application readiness.** A tailored résumé, a portfolio and a crisp,
true story for this role. A generic résumé scores 1. A résumé tailored to this
family of roles, with a portfolio link, scores 3.

## The verification ladder (enforced)

Every evidence item has a level. A dimension score can be no higher than the
best evidence it cites supports.

| Level | Meaning | Highest score it supports |
|---|---|---|
| `verified` | Primary source checked (a repository, a certificate address, a live product, an email from the issuer). | 5 |
| `corroborated` | Two independent sources agree (for example LinkedIn plus a referee or a press article). | 4 |
| `partially_verified` | Some of the facts in the claim were checked against a source, some were not (for example the company register confirms the business exists, but not the revenue). | The higher of its kind's self-reported cap and 2, never above 4. See below. |
| `self_reported` | The person's own résumé, LinkedIn or answers. | Depends on the kind, see below. |
| `unverified` | A claim with no source. | 0 |
| `contradicted` | Evidence says otherwise. Also flagged in the claims audit. | 0 |

For `self_reported` evidence, the cap depends on the evidence kind, set in
`config.json` under `scoring.self_reported_caps`:

| Kind | Default cap | Why |
|---|---|---|
| `job_history` | 3 | Screening accepts a résumé's titles, employers and dates and verifies them later. |
| `education` | 3 | Same as job history. |
| `eligibility` | 5 | Work rights and where the person lives are taken on the applicant's word at screening too. |
| `preference` | 5 | Willingness to move or travel is only knowable from the person. |
| everything else | 1 | Specific achievements, credentials, artefacts and network claims need a second source. |

For `partially_verified` evidence the rule is: the checked part counts, the
unchecked part does not.

- It supports the higher of its kind's self-reported cap and
  `scoring.partially_verified_cap` (default 2): a partly checked achievement
  supports 2 where a self-reported one supports 1, and a partly checked job
  history supports 3, as a self-reported one does.
- It never supports more than 4, what corroborated evidence supports. A claim
  that is only partly checked can never outrank one that two independent
  sources agree on.
- For eligibility and preference, which the person's word already supports at
  5, that ceiling is lower than self-reported, so record those facts as
  `self_reported` (or `verified` once the rest is checked).
  `scripts/validate.py` warns about any partially verified item it would
  under-count.
- Say in the item's `notes` which part was checked and which was not. Checking
  the rest moves the item up the ladder.

Evidence ids are 1 to 3 capital letters, then digits. New items use `E`
(`E01`, `E02`); another prefix keeps a source's own numbering, for example
`G01` for findings from an email search. Never renumber an id.

Unknown evidence ids are reported as warnings and ignored.

## Employment history and achievement claims

- **Employment history works the way real screening does.** Job titles,
  employers and dates on the person's résumé or LinkedIn count as stated
  experience for D1 (up to 3), because recruiters accept them at screening and
  check them later.
- **Specific achievement claims** inside those roles (budgets, team sizes,
  outcomes, savings) count at most 1 point until a second source, a referee or
  a public artefact backs them up.

## Eligibility beats everything (enforced)

`scripts/fetch_roles.py` looks for four kinds of eligibility blocker in each
posting:

| Blocker type | What it catches |
|---|---|
| `us_person_export_control` | ITAR (the United States International Traffic in Arms Regulations), "US person", export control, US citizenship or permanent residency (green card). |
| `security_clearance` | An active or obtainable government security clearance. |
| `citizenship` | "Must be a citizen of" a named country. |
| `licence` | "Must hold" a named licence. |

A role is **blocked** if it has a blocker whose type is not listed in
`config.json` under `candidate.eligibility_cleared`. The judgement field
`eligibility_blocked` (true or false) overrides the automatic call, for example
when the detector misread the posting.

A blocked role scores D6 = 0 and counts as a lacking hard requirement, so D1
is capped at 1 and both bands move down one step.

Some blockers no plan can clear in time, such as a citizenship rule. Set
`hard_eligibility_block: true` in the role's judgement to say so (it also
marks the role blocked). The dashboard's projection then keeps D6 at 0 for
that role, whatever the plan does. Blocked roles whose blocker type is listed
in `campaign/plan.json` under `eligibility_blockers.hard_types` (by default
`us_person_export_control`, `citizenship` and `security_clearance`) are
treated the same way; a `licence` blocker can be cleared by a plan action.

## Review cap (enforced)

A dimension score above `scoring.review_required_above` (default 2) counts as
2 until the reviewer has agreed. Agreement is recorded as `reviewed_on`, dated
on or after `judged_on`:

- for D1, D2 and D4, on the role judgement (or on the single dimension entry);
- for D3, D5, D7 and D6 rules, on that entry (or on the file's top level).

Changing a judgement after review (a later `judged_on`) needs a fresh review.
The run lists these roles as awaiting review.

## Unjudged roles (enforced)

A role with no entry in `eval/judgements.json` scores 0 on D1, D2 and D4 and
is flagged "Not yet judged". If its posting expects production coding and
`candidate.writes_production_code` is false, it also counts as a lacking hard
requirement. Judge the best-looking roles first.

## From fit score to chances

Two estimates per role, shown as bands, not false-precision percentages:

| Fit score | Chance of an interview | Chance of an offer (if applied now) |
|---|---|---|
| 0 to 14 | Almost none | Almost none |
| 15 to 24 | Very low | Almost none |
| 25 to 39 | Very low | Very low |
| 40 to 54 | Low | Very low |
| 55 to 69 | Moderate | Low |
| 70 to 84 | Good | Moderate |
| 85 to 100 | Strong | Good |

Adjustments, applied after the table, in this order (enforced):

1. **Warm referral** (D3 at least 4): the interview band moves up one step.
2. **Hard requirement lacking** (or blocked): both bands move down one step.
3. **Cold application only** (D3 at most 1): the offer band is capped at Low.

These are judgement estimates, not statistics. The point is the direction and
the size of each gap, so effort goes where it moves the number most. The
dashboard checks them against what happened to the person's own applications
("How right has LVLme been", method/CAMPAIGN.md); that check never changes a
band. A change to this table is a new rubric version.

## Headline numbers in each report

1. **Best-fit roles**: the top roles by fit score, with bands.
2. **Per organisation**: the best role and its bands at each target (highest
   fit, ties broken by interview band, then role id).
3. **Gap leaderboard**: from `eval/gap-templates.json`. For each gap, over the
   top roles by fit (`scoring.top_n_for_gaps`, default 25) that match the
   gap's organisations, families, location classes and blocked filter: the
   sum of the fit points gained if that dimension rose to the gap's target
   score. A D1 target is capped at 1 on roles with a lacking hard requirement,
   and a D6 gap skips roles with an eligibility blocker (raising D6 there
   means clearing the blocker, which is its own gap). Each gap carries its
   `kind` (Show it or Build it); the order stays by points.
   By default there is one pool, the top roles overall, so a gap at an
   organisation with no role in that pool scores 0. With
   `scoring.gap_pool` set to `per_org`, each target organisation gets its own
   pool, its top `scoring.top_n_per_org_for_gaps` roles (default
   `top_n_for_gaps`), and each gap adds up over the pools it applies to. The
   run file then also shows each organisation's share (`by_org`). Use it when
   the targets differ a lot in how well they fit, so an organisation-specific
   warm introduction is not hidden behind the best organisation's roles.
4. **Outlook**: a plain-English estimate of the chance of reaching the goal
   within `goal.horizon_months` if the campaign is followed, with the main
   reasons. The agent writes it in `eval/outlook.json`. Without it the report
   says "Not yet judged".
5. **Verify to unlock**: open questions from `profile/evidence.json`, plus one
   question for each unverified evidence item.
6. **Trend**: the change since the last run, for each headline number.

## Repeatability

`scripts/score.py` is deterministic: the same input files give the same run
file, byte for byte. Each run file carries an `inputs_digest` (a fingerprint
of every input) and the weights used, so any two runs can be compared and any
change traced to the files that caused it.
