# Design: Climb, the career eval and campaign engine

Status: draft v0.1 (2026-11-01). Name: Climb (chosen 2026-11-02). Folder, skill and command name: `climb`.

## 1. What it is

An open-source method plus small scripts that any person, or any personal AI
agent acting for them, can run to:

1. **Estimate honestly** how likely they are to land a specific kind of role at
   specific organisations, from evidence, not vibes.
2. **Explain why**, factor by factor, with every point traced to a source.
3. **Turn the gaps into a campaign**: a short, prioritised, evolving list of
   actions that raise the odds, re-scored on a schedule so effort follows
   what actually moves the number.

First use case: getting hired at frontier AI labs. The engine is goal-agnostic:
targets, role families and weights are configuration.

## 2. Principles

1. **Evidence or it scores zero.** Every point cites a source. Unsourced claims
   count as absent and become "verify to unlock" questions.
2. **Honest by construction.** Default answer is "unlikely". A separate,
   sceptical reviewer pass must agree with every score above 2.
3. **First principles about hiring.** For non-traditional candidates the
   binding constraints are, in order: eligibility (work rights, hard
   requirements), a warm path (someone inside who vouches), visible proof of
   work, and a tailored application. The rubric weights reflect that, and the
   campaign attacks the binding constraint first.
4. **Agent-agnostic.** Plain files in, plain files out. Works with Claude Code
   (as a skill), Codex, Cursor / Grok Bot, or a person with a terminal.
5. **Private by default.** The engine repo never holds personal data. A user's
   data lives in a separate workspace folder on their own machine.
6. **Drafts only.** The engine never applies, sends, posts, or changes the
   user's accounts. Outreach is drafted for the user to send.
7. **No fabrication, no flattery, no profiling.** Never invent experience,
   numbers, contacts or stories. Never infer or score protected attributes
   (age, gender, ethnicity, disability, religion, family status).

## 3. Architecture

```
climb/                        public engine (this repo, MIT)
  SKILL.md  AGENTS.md  README.md  LICENSE
  method/   RUBRIC.md INTAKE.md SWOT.md CAMPAIGN.md REVIEW.md PRIVACY.md RUNBOOK.md
  schemas/  JSON schemas for every workspace file
  scripts/  init.py fetch_roles.py network_map.py claims_audit.py
            score.py build_dashboard.py validate.py
  templates/ workspace skeleton copied by init.py
  examples/ demo-workspace/ (a fictional person, for demos and tests)
  tests/

<workspace>/                  private, per user, outside the repo
  config.json                 goal, targets, role families, locations, cadence
  intake/answers.md           interview answers (eligibility, constraints, story)
  intake/sources/             user-supplied exports (LinkedIn ZIP, résumé PDF)
  profile/evidence.json       evidence items with verification level
  profile/network.json        people at target orgs (from LinkedIn export)
  profile/claims-audit.json   public claims checked against evidence
  market/roles/latest.json    open roles + snapshots/
  market/orgs.json            org-level intelligence (offices, eligibility, signals)
  eval/judgements.json        per-role judgements (D1, D2, D4)
  eval/profile-dimensions.json  per-org D3, D5, D7 and D6 rules
  eval/swot.json              SWOT + TOWS strategies
  eval/runs/<date>.json       one scored run per date
  campaign/plan.json  campaign/inbox.md  campaign/drafts/  campaign/weekly/
  report/index.html  report/for-agents/SUMMARY.md  report/for-agents/dashboard.json
```

Workspace location: `$CLIMB_HOME`, else `~/climb-workspaces/<goal-slug>`.
`validate.py` refuses to run if the workspace is inside the engine repo or any
git repo with a public remote.

## 4. Pipeline (one run)

| Stage | Who | Output |
|---|---|---|
| 1. Intake (first run, then deltas) | agent + user | `intake/answers.md`, sources |
| 2. Evidence | agent + scripts | `profile/evidence.json`, `network.json`, `claims-audit.json` |
| 3. Market | `fetch_roles.py` + agent | `market/roles/latest.json`, `market/orgs.json` |
| 4. Judge | agent (scorer) | `eval/judgements.json`, `eval/profile-dimensions.json` |
| 5. Review | fresh agent (sceptic) | agreed changes applied to judgement files |
| 6. Score | `score.py` (deterministic) | `eval/runs/<date>.json` |
| 7. SWOT and TOWS | agent | `eval/swot.json` |
| 8. Plan | agent | `campaign/plan.json` |
| 9. Report | `build_dashboard.py` | dashboard + agent briefing |
| 10. Tell the user | agent | short message, today's 1 to 3 actions |

Judgement (stages 4, 5, 7, 8) lives in files so the maths (stage 6) is
repeatable and auditable; only changed or new items are re-judged each run.

## 5. Intake: what we can learn, and how far to trust it

### 5.1 Verification ladder (applies to every evidence item)

| Level | Meaning | Max score it can support |
|---|---|---|
| `verified` | primary source checked (repo, certificate URL, live product, email from the issuer) | 5 |
| `corroborated` | two independent sources agree (e.g. LinkedIn + a referee or press) | 4 |
| `partially_verified` | some facts in the claim checked, some not | the higher of the kind's self-reported cap and 2, never above 4 |
| `self_reported` | the user's own résumé / LinkedIn / answers | 3 for job history (screening accepts it); 1 for specific achievement claims |
| `unverified` | a claim with no source | 0 |
| `contradicted` | evidence says otherwise | 0, and flagged in the claims audit |

### 5.2 Source catalogue (each opt-in, read only)

| Source | How | Yields | Feeds |
|---|---|---|---|
| Interview questions | `method/INTAKE.md` question bank | eligibility, constraints, motivation, story, notice period, IP/non-compete | D6, D7, SWOT |
| Résumé / CV | user file | roles, dates, claims to verify | D1 |
| LinkedIn data export (official "Get a copy of your data" ZIP) | `Positions.csv`, `Education.csv`, `Certifications.csv`, `Skills.csv`, `Connections.csv` | job history, degree, certs, and **the network map** | D1, D6, D3 |
| LinkedIn profile text | `Profile.csv` in the export, plus follower count and post reach the person types in | headline, about, posts, followers | D5, claims audit |
| GitHub | `gh` / public API | repos, commits, merged PRs, releases, licences, stars, followers, public vs private | D2, D5 |
| Personal site, product sites, app stores | fetch | live products, claims, download counts | D2, D5, claims audit |
| Publications | Google Scholar, ORCID, arXiv, SSRN | papers, citations | D2, D5 |
| Certifications | Credly / issuer URLs / issuer emails | verified credentials | D2, D4 |
| Talks, podcasts, video | YouTube, podcast feeds | speaking, reach | D5 |
| Web self-search | search engine | what a recruiter finds (and doesn't) | D5, claims audit |
| Email (read only) | Gmail / Outlook connector | recruiter contact, applications, intros, issuer confirmations, events | D3, D7, evidence |
| Calendar (read only) | connector | meetups, conferences attended | D3 |
| References | user list | who can vouch, for which claim | corroboration |

### 5.3 Network map (`scripts/network_map.py`)

Parses LinkedIn `Connections.csv` (First Name, Last Name, URL, Email Address,
Company, Position, Connected On). Matches companies to target orgs (with
aliases, e.g. "xAI" ↔ "X.AI"), and lists first-degree contacts per target
org with position and how long connected. Second-degree paths are found by the
agent asking the user ("who do you know who knows someone at X?") and from
mutual-connection counts if the user supplies them. Output stays local; names
are never copied into the agent briefing unless the user opts in.

D3 anchors use it directly: 0 nobody; 1 a first-degree contact in an unrelated
team who hasn't seen the user's work; 2 a second-degree path someone has agreed
to open; 3 a named insider who knows the user's work; 4 that person has agreed
to refer; 5 referral submitted.

### 5.4 Public claims audit (`scripts/claims_audit.py` + agent)

Extracts claims from the user's public pages (site, LinkedIn, GitHub READMEs)
and checks each against evidence: `supported`, `overstated`, `unsupported`,
`contradicted`, with the suggested honest wording. Overclaims hurt credibility
more than gaps, so these become top-priority actions.

## 6. Market intelligence

`config.json` lists target orgs with their applicant-tracking system and slug
(Greenhouse, Ashby, Lever, Workable, SmartRecruiters, or `manual`). For each
open role, `fetch_roles.py` extracts: family (keyword taxonomy per goal),
locations and location class, remote flag, years required, degree requirement,
hard requirements, nice-to-haves, compensation, heavy-coding flag, and
**eligibility blockers** (US-person / ITAR / export control, security
clearance, citizenship, licence). Daily snapshots give hiring velocity (new and
closed roles). `market/orgs.json` holds org-level facts the agent researches:
offices in the user's region, teams growing, events, partner programmes.

## 7. Scoring

Seven dimensions, 0 to 5, weights configurable per goal (defaults below):
D1 requirements match 25 · D2 proof of work 20 · D3 warm path 20 · D4 org-specific
edge 10 · D5 public signal 10 · D6 eligibility and logistics 10 · D7 application
readiness 5. Fit = Σ score/5 × weight. Bands (Very low → Strong) for interview
and offer, with three adjustments (referral up, hard requirement lacking down,
cold-only caps offer at Low). Full rules: `method/RUBRIC.md`. Review protocol:
`method/REVIEW.md` (the reviewer gets the rubric, evidence and scores, but not
the scorer's reasoning, and must justify every change).

## 8. SWOT, then TOWS

`eval/swot.json` holds, overall and per target org:

- **Strengths / Weaknesses** (internal): evidence-cited, each tied to a
  dimension and the roles it moves.
- **Opportunities / Threats** (external): from market data (roles open in the
  user's region, new teams, partner programmes, events, competitor applicant
  pools, eligibility rules, hiring freezes).
- **TOWS strategies**, which turn the grid into moves:
  - SO: use a strength to seize an opportunity
  - ST: use a strength to blunt a threat
  - WO: fix a weakness to unlock an opportunity
  - WT: avoid the trap where a weakness meets a threat
  Each strategy names the actions it creates in the plan.

## 9. Campaign engine

- **Action library** (`method/CAMPAIGN.md`): proven moves per dimension and
  TOWS type (e.g. D3: map network, warm-intro ask, community contribution,
  event; D2: open-source a project, write a verifiable case study; D6: confirm
  degree / visa route; D7: tailored résumé per role).
- **Priority** = expected fit points gained × roles affected × chance it works
  ÷ effort hours. Cap 8 active actions (the validator warns above it); park
  the rest with status `later`, outside the projection until switched on.
- **Done needs evidence.** An action is done only with a link, file or email.
- **Experiments.** Every action is a bet. If it shows no score or metric
  movement for 3 runs, rework or drop it, and log why.
- **North-star metrics**: warm introductions, applications to best-fit roles,
  interviews, offers, public proof pieces, credentials.
- **Cadence**: daily during build-up (first ~4 weeks), then weekly. The agent
  suggests the switch; the user decides.

## 10. Outputs

- `report/index.html`: the "Mission control" dashboard (see `docs/LEVELS.md`).
  Self-contained, no external requests, light and dark mode, readable on a phone.
  The headline number reads "Best match 57 of 100": a fit score, not a probability.
  One yardstick for actions: Do next, the quests, the badges and the plan list share
  one order (the path to the next level first, then points per hour) and one points
  number per action (expected points toward the next level, counting its chance);
  only the What if rail shows what an action adds "with everything else on".
  Internal ids stay in the drill-in detail. The key numbers, the level card and the
  Level up view are also in the HTML itself, so they read without JavaScript.
- `eval/reviews/<date>.json`: the reviewer disputes and the score that stood.
- Every main workspace file accepts extension keys starting `x_` for data the
  engine never reads.
- `report/for-agents/SUMMARY.md` and `dashboard.json`: for the user's other
  agents. `campaign/inbox.md`: the only file agents may write to.

## 11. Packaging

- `SKILL.md` (Agent Skills format): Claude Code users drop the repo into
  `~/.claude/skills/climb/` or install it as a plugin.
- `AGENTS.md`: instructions for Codex, Cursor / Grok Bot and other agents.
- Scripts: Python 3.9+, standard library only, no network calls except public
  job-board APIs and connectors the user approves. No telemetry.

## 12. Safety and privacy

- Cloud agents see whatever they read: the README warns users before pointing
  one at their workspace, and `SUMMARY.md` has a "sensitive mode" that omits
  employer names, third-party names and salary.
- Third-party data (connections, email senders) stays in the workspace and is
  never copied into briefings or drafts without the user's opt-in.
- The engine never scores or infers protected attributes.

## 13. Not in v0.1

Automatic LinkedIn scraping (against LinkedIn's terms; use the official export),
auto-applying, salary negotiation, non-job goals (designed for, not built).

## 14. The story the product tells (owner's direction, 2026-11-01)

The headline feature is the climb: an honest, measured starting point (often
"Very low"), then every step to the goal, scored and dated. The dashboard leads
with the journey (baseline pinned on day one, actual progress, projected path
if the plan is followed, and a "do nothing" line), and each daily run is saved
with its date so the record of progress is verifiable rather than claimed.
