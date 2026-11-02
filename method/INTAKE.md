# Intake: what we can learn, and how far to trust it

Intake is how evidence gets into the workspace. It has three parts:

1. **The interview**: questions only the person can answer (the question bank
   below). Answers go in `intake/answers.md`. Run it document-led, in short
   rounds, as `INTERVIEW.md` describes.
2. **Sources**: files and pages the person chooses to share, each opt in and
   read only.
3. **Recording**: every fact becomes one item in `profile/evidence.json`, with
   a verification level.

On the first run, work through the whole question bank. On later runs, ask
only about what has changed, and about the open questions in
`profile/evidence.json`.

## The verification ladder

Every evidence item has exactly one level. The level limits the score the item
can support (see `RUBRIC.md`).

| Level | Meaning | Highest score it supports |
|---|---|---|
| `verified` | Primary source checked: a repository, a certificate address, a live product, an email from the issuer. | 5 |
| `corroborated` | Two independent sources agree, for example LinkedIn plus a referee or a press article. | 4 |
| `partially_verified` | Some of the facts in the claim were checked against a source, some were not. Say which in `notes`. | The higher of the kind's self-reported cap and 2, never above 4 (see `RUBRIC.md`). Record eligibility and preference facts as `self_reported` instead. |
| `self_reported` | The person's own résumé, LinkedIn or interview answers. | 3 for job history and education; 5 for eligibility and preferences; 1 for specific achievement claims and everything else. |
| `unverified` | A claim with no source. | 0 |
| `contradicted` | Evidence says otherwise. | 0, and flagged in the claims audit. |

Move an item up the ladder only when you have actually checked the new
source. An agent's say-so (including a note in `campaign/inbox.md`) is not a
source.

Use `partially_verified` when you checked part of a claim and the rest is
still the person's word: for example the company register confirms that the
business exists and who its director is, but nothing confirms its revenue.
Better still, split the claim into two items, one `verified` and one
`self_reported`, when the two parts support different scores.

## The source catalogue

Every source is **opt in** (ask first) and **read only** (never change
anything). "Feeds" lists the dimensions the source usually informs.

| Source | How | Yields | Feeds |
|---|---|---|---|
| Interview questions | The question bank below | Eligibility, constraints, motivation, story, notice period, intellectual property and non-compete terms | D6, D7, SWOT |
| Résumé or CV (curriculum vitae) | A file the person supplies, saved in `intake/sources/` | Roles, dates, claims to verify | D1 |
| LinkedIn data export | The official "Get a copy of your data" ZIP file: `Positions.csv`, `Education.csv`, `Certifications.csv`, `Skills.csv`, `Connections.csv` | Job history, degree, certificates, and the network map | D1, D3, D6 |
| LinkedIn profile text | `Profile.csv` in the same export (headline, summary); the person types in their follower count and post reach | Headline, about, followers, posts | D5, claims audit |
| GitHub | The `gh` command or the public API (application programming interface) | Repositories, commits, merged pull requests, releases, licences, stars, followers, public or private | D2, D5 |
| Personal site, product sites, app stores | Fetch the page | Live products, claims, download counts | D2, D5, claims audit |
| Publications | Google Scholar, ORCID, arXiv, SSRN | Papers, citations | D2, D5 |
| Certifications | Credly, issuer addresses, issuer emails | Verified credentials | D2, D4 |
| Talks, podcasts, video | YouTube, podcast feeds | Speaking, reach | D5 |
| Web self-search | A search engine | What a recruiter finds, and what they do not | D5, claims audit |
| Email (read only) | A Gmail or Outlook connector the person approves | Recruiter contact, applications, introductions, issuer confirmations, events | D3, D7, evidence |
| Calendar (read only) | A connector the person approves | Meetups and conferences attended | D3 |
| References | A list from the person | Who can vouch, for which claim | Corroboration |

Never scrape LinkedIn automatically: it breaks LinkedIn's terms. Use the
official export.

### The network map

Run:

```bash
python3 scripts/network_map.py --csv intake/sources/Connections.csv
```

It reads the LinkedIn `Connections.csv`, skips the notes at the top, and
matches each contact's company to the target organisations and their aliases
in `config.json`. Matching ignores case, punctuation and legal suffixes such
as Inc, LLC, Ltd, Pty, PBC and Corp. It drops email addresses, works out how
many months each person has been connected, and writes
`profile/network.json`. It prints counts only, never names.

Second-degree paths come from the person. Ask: "who do you know who knows
someone at this organisation?" Record each path in `second_degree` with its
status (`idea`, `asked`, `agreed`, `opened`, `declined`). Re-running the script
keeps those paths and the per-contact `knows_my_work` and `note` fields.

For each person they are warming up at a target, record a stage in
`campaign/warm-paths.json`: followed, talked, connected, knows your work,
would refer ("Warm paths" in `method/CAMPAIGN.md`). It shows progress on the
dashboard and changes no score.

### The public claims audit

Run, with only the addresses the person gives you:

```bash
python3 scripts/claims_audit.py https://their-site.example/about intake/sources/resume.txt
```

It reads each page or file, picks out sentences that look like claims
(achievement verbs, numbers, percentages, money, years, titles, awards), and
adds new ones to `profile/claims-audit.json` as `pending`. Claims already
judged are never changed. For each pending claim, check it against the
evidence and set:

- `supported`: the evidence backs it as written.
- `overstated`: there is something real, but the wording claims more.
- `unsupported`: no evidence either way.
- `contradicted`: evidence says otherwise.

Add the evidence ids and a `suggested_wording` that is true. Overclaims hurt
credibility more than gaps, so every `overstated` or `contradicted` claim
becomes a top-priority plan action.

## Recording evidence

One fact per item in `profile/evidence.json` under `items`:

| Field | What to put |
|---|---|
| `id` | `E01`, `E02` and so on. Never reuse or renumber an id. An id is 1 to 3 capital letters and then digits, so items imported from a source with its own numbering can keep it (for example `G01` for email findings). Avoid `D`, `A` and `Q`, which LVLme uses for factors, actions and questions. |
| `claim` | The fact in one plain sentence. |
| `kind` | One of `job_history`, `education`, `credential`, `artefact`, `achievement`, `network`, `public_signal`, `eligibility`, `preference`, `other`. |
| `level` | One of the five ladder levels. |
| `dimensions` | The dimensions it can support, for example `["D1"]`. |
| `orgs` | Optional: the target organisation ids it relates to. |
| `sources` | Each with a `type` (for example `resume`, `github`, `email`, `interview`), a `ref` (an address, a workspace file path, or a pointer such as `intake/answers.md#work-rights`) and a `checked_on` date. |
| `added_on`, `notes` | Optional. |
| `x_...` | Optional extension fields: any key starting `x_` (for example `x_original_category`) holds data the engine never reads, such as a field from an older system. Allowed on evidence items, their sources and open questions, and on the main object of each judgement, plan, run and config file. |

Rules:

- Never delete an item. If it turns out to be wrong, set its level to
  `contradicted` and explain in `notes`.
- A fact with no source goes in as `unverified`. The scoring script turns
  each one into a "verify to unlock" question.
- Questions you still need answered go under `open_questions`, each with an
  `id` (`Q01` and so on), the `question`, `why` it matters, the `dimensions`
  it would change, and a `status` (`open`, `answered`, `dropped`).

## What we never ask

Never ask about, infer or record protected attributes: age, gender,
ethnicity, disability, religion, family status. Do not ask for a date of
birth, a photo, or graduation years beyond what a posting's stated
requirement needs. Work rights are asked as a yes or no fact about what the
person is legally allowed to do, never as a question about nationality or
origin. If the person volunteers something sensitive, do not record it.

## The question bank

Each question is tagged with the dimension or dimensions it feeds. Save
answers in `intake/answers.md` under the matching heading. Record each answer
that is a fact as an evidence item with a source of type `interview` and a
`ref` pointing to the heading.

### 1. Eligibility and work rights

1. In which countries are you legally allowed to work today, without
   sponsorship? [D6]
   Why we ask: this decides which location classes score well.
2. For each other country you would consider, is there a visa route you
   qualify for, and what does it need (a degree, an employer sponsor, a job
   offer first)? [D6]
   Why we ask: a confirmed route scores better than "would need sponsorship".
3. Do you hold a bachelor's degree or higher? If yes, in what field? If not,
   what do you hold instead? [D1, D6]
   Why we ask: many postings and some visa routes require a degree or
   equivalent experience.
4. Are you a "US person" for United States (US) export-control purposes (a US
   citizen, a US permanent resident, or a protected individual)? [D6]
   Why we ask: roles under ITAR (the US International Traffic in Arms
   Regulations) and other export controls are closed to everyone else.
5. Do you hold, or could you obtain, a government security clearance? Which
   country and level? [D6]
   Why we ask: clearance roles are closed without one.
6. Do you hold any professional licence a target role might require (for
   example a driving licence, an engineering registration, a financial
   services licence)? [D6, D1]
   Why we ask: licence requirements are hard blockers.
7. Is there anything that would stop you passing a standard background or
   reference check for this kind of role? You do not need to say what it is.
   [D6]
   Why we ask: better to plan for it than to be surprised late.
8. Are any of your past employers or clients likely to be seen as a conflict
   of interest by a target organisation? [D6, D4]
   Why we ask: some organisations screen out applicants from competitors or
   regulators.

### 2. Constraints

1. What is your notice period in your current role? [D6, D7]
   Why we ask: it sets how soon you can start and how to time applications.
2. Do you have an intellectual property (IP) agreement with your current or
   past employers that covers work you want to show as proof? [D2, D6]
   Why we ask: you can only publish work you own or are allowed to share.
3. Do you have a non-compete or non-solicitation clause? What does it cover,
   and until when? [D6]
   Why we ask: it may rule out some organisations or roles for a time.
4. Would you relocate? To where, and on what timeline? [D6]
   Why we ask: this sets the D6 score for each location class.
5. How many days a week could you work on site, and how much travel could
   you do? [D6]
   Why we ask: many roles are on site or hybrid.
6. What is the lowest total pay you would accept, and in which currency?
   [plan] (Kept in the workspace only; never shared with other agents in
   sensitive mode.)
   Why we ask: it filters roles that would never work for you.
7. How many hours a week can you give this campaign, for the next 4 weeks?
   [plan]
   Why we ask: the plan must fit the time you actually have.
8. Which time zones can you work in regularly? [D6]
   Why we ask: remote roles often need overlap with a team's hours.
9. Is there any organisation or kind of role you will not consider? [plan]
   Why we ask: so the campaign never pushes you towards it.

### 3. Goals and motivation

1. In one sentence, what role do you want, and at which organisations?
   [config]
   Why we ask: it sets the goal, targets and role families.
2. Why these organisations, specifically? What do you know about their work
   that most applicants would not? [D4, D7]
   Why we ask: a specific, true reason is part of the organisation-specific
   edge.
3. Which of their products have you used, how often, and what did you build
   or learn with them? [D4, D2]
   Why we ask: deep, demonstrable use of an organisation's own products is a
   strong edge.
4. What would a great first year in the role look like? [D7]
   Why we ask: it shapes the story and the tailored résumé.
5. Which role family is your first choice, and which are acceptable? [config]
   Why we ask: it sets the order of the families and where to focus.
6. What is your timeline: when do you want an offer by? [config, plan]
   Why we ask: it sets `goal.horizon_months` and the cadence.
7. What would make you turn an offer down? [plan]
   Why we ask: no point campaigning for a role you would refuse.
8. Have you applied to any target organisation before? When, for what, and
   what happened? [D3, D7]
   Why we ask: past applications and their outcomes are evidence, and some
   organisations ask you to wait before reapplying.

### 4. Proof of work

1. What have you shipped that a stranger can check today: a product, a
   repository, a publication, a case study? Give the links. [D2, D5]
   Why we ask: verifiable work is the strongest evidence there is.
2. Which of those have real users, customers or readers, and how do you know
   (analytics, downloads, emails)? [D2]
   Why we ask: one thing with users beats many things without.
3. What is your biggest achievement in your last two roles, and who could
   confirm it (a referee, a document, a press article)? [D1, D2]
   Why we ask: achievement claims count 1 point until a second source
   backs them.
4. Which certifications or credentials do you hold, and where can they be
   verified? [D2, D4]
   Why we ask: an issuer's address or email lifts a credential to verified.
5. What work do you have that is private but could be made public, with
   permission? [D2]
   Why we ask: publishing it may be the cheapest way to raise D2.
6. Have you built anything with AI agents or AI tools? What, and is it
   public? [D2, D4]
   Why we ask: verifiable agent-built software counts as proof of work.
7. Have you written, spoken or taught about your field? Where? [D5]
   Why we ask: it is public signal a hiring manager can find.
8. Which open-source projects or communities have you contributed to? [D2,
   D3, D5]
   Why we ask: contributions are checkable and often build a warm path.
9. Is any public claim about you (on your site, LinkedIn or elsewhere) out
   of date or stronger than you could prove? [claims audit]
   Why we ask: overclaims hurt more than gaps, so fix them first.

### 5. Network

1. Who do you know at each target organisation, even slightly? [D3]
   Why we ask: the LinkedIn export misses people you know outside LinkedIn.
2. Of those, who has seen your work, and what exactly have they seen? [D3]
   Why we ask: "knows my work" is the line between D3 = 1 and D3 = 3.
3. Who do you know who knows someone at each target organisation? [D3]
   Why we ask: second-degree paths are the most common route to a warm
   introduction.
4. Has anyone offered to introduce you or refer you? Who, to whom, and when?
   [D3]
   Why we ask: an agreed referral is D3 = 4.
5. Which past colleagues now work at, or near, a target organisation? [D3]
   Why we ask: former colleagues who know your work are the warmest path.
6. Which communities, meetups or events do people from the targets attend?
   Have you been? [D3, D5]
   Why we ask: showing up is how second-degree paths become first-degree.
7. Who would give you a strong reference for the kind of role you want? For
   which claims? [D1, D2]
   Why we ask: referees corroborate achievement claims.
8. Is there anyone you would rather we did not approach, or mention? [privacy]
   Why we ask: the campaign never drafts outreach you do not want.

### 6. Story

1. In two sentences, who are you professionally and why this role, now?
   [D7]
   Why we ask: a crisp, true story is part of application readiness.
2. What is the thread that connects your past roles to this one? [D7, D1]
   Why we ask: it turns an unusual background into a reason to hire.
3. What problem have you solved that is most like the work in the target
   role? [D1, D2, D7]
   Why we ask: it is the core of the tailored résumé.
4. What do people come to you for? [D7, D4]
   Why we ask: it often reveals the real strength.
5. What is the strongest objection a hiring manager would have to you, and
   your honest answer to it? [D7, SWOT]
   Why we ask: naming the weakness first is how to blunt it.
6. Do you have a current résumé tailored to this role family? A portfolio?
   [D7]
   Why we ask: D7 scores what exists today.
7. What is a mistake you made and what you changed afterwards? [D7]
   Why we ask: most interviews ask, and a true answer prepared in advance is
   stronger.
8. What do you want to be known for in two years? [D5, D7]
   Why we ask: it guides what to publish.

## After the interview

1. Save the answers in `intake/answers.md`.
2. Add evidence items for each fact, with the right level.
3. Add open questions for anything still unanswered.
4. Copy the work history from each source (what the person confirmed, any
   signed form, the CV, LinkedIn, the website) into
   `profile/role-records.json`, and run the consistency audit
   (`CONSISTENCY.md`).
5. Update `config.json` if the goal, targets, families, locations or
   `candidate.eligibility_cleared` changed.
6. Run `python3 scripts/validate.py`.
