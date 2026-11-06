# The document-led career interview

People misremember their own history. Titles drift upwards, end dates move
by a few months, and the best stories lose their numbers. The fastest way to
the truth is to ask for **documents the person already has**, read them
together, then corroborate what they say from independent sources.

This module is how to run the first intake interview (and any later one
about a gap in the record). It sits in front of the question bank in
`INTAKE.md`: the question bank says what to ask; this says how to ask it so
the answers can be trusted. Where the interview sits in a first run is in
["First run"](../SKILL.md#first-run).

## The rules

1. **Documents first, memory second.** Ask "do you have anything that shows
   this?" before "what do you remember?".
2. **Short rounds.** Ask 4 to 6 questions at a time, then stop, record, and
   look for corroboration before the next round.
3. **In time order.** Education, then each role from the earliest, then
   gaps, businesses, best stories, referees and motivation.
4. **The person's own words.** Record what they say, not your polished
   version. If you paraphrase, read it back and ask if it is right.
5. **Never invent.** No story, number, title or date the person did not give
   or a document does not show. "Not sure" is a valid answer; record it as an
   open question.
6. **Read only.** Every source (email, registers, the web) is opt in and
   read only. Never reply, send, label, delete or change anything.
7. **Keep it private.** Everything stays in the workspace. See "What never
   to record" below.

## The first message

Once the workspace exists (after the one sentence goal question, if LVLme
had to ask it), the first thing the person reads from LVLme is one short
message: about 120 words at most, three parts, in this order.

1. **Three facts from the CV, to confirm.** Pick facts the scores depend
   on: the latest title and employer with dates, the highest qualification,
   and the achievement the CV makes most of. Ask whether each is right: a
   yes or a correction is all you need.
2. **Which organisations.** Ask which organisations they want to work for,
   and the kind of role if the goal does not already say.
3. **The LinkedIn data export.** Say how to ask LinkedIn for it and which
   files you will read. It can take LinkedIn up to a day to send, so ask now:
   it arrives while the interview goes on.

Nothing else yet. Work rights, pay, other sources and the document rules
come in the rounds, once the targets are set. No CV yet? Ask for it (a file
or pasted text) instead of the three facts, and confirm them in the next
message.

An example, for the fictional Alex Example (112 words):

> Thanks, Alex. First, three facts from your CV. Is each right?
>
> 1. Program Manager at Contoso Freight since 2021, after five years there as
>    an Operations Analyst.
> 2. A Bachelor of Business (Logistics), finished in 2015.
> 3. You led the warehouse scheduling rollout across all 6 sites.
>
> Next, which organisations do you want to work for? Add the kind of role,
> if you know it.
>
> Last, your LinkedIn data export. On LinkedIn, open Settings, then Data
> privacy, then "Get a copy of your data". LinkedIn emails you a link,
> sometimes a day later. When it arrives, tell me where you saved the ZIP
> file. I read only your profile, positions, education, certifications,
> skills and connections.

## Before the first round

From the reply, set the targets and role families in `config.json` with the
person and run `scripts/validate.py` (["First run"](../SKILL.md#first-run),
step 3). Then tell the person, in plain words:

> I'll ask a few questions at a time, starting with your education and
> working forward. Wherever you can, show me a document instead of
> remembering: an old CV, a form you filled in for an employer, a
> certificate, a logbook, an offer letter. Photos are fine. I'll only copy
> titles, dates and achievements. I won't keep pay, passwords, ID numbers,
> or anything about health, family, loans or legal matters, even if they're
> in the photo.

Then ask which sources they are happy for you to check (see "Corroborating"
below). Note their answer in `intake/answers.md` under a "Permissions"
heading.

## Documents worth asking for

| Document | What to copy | Why it is good |
|---|---|---|
| A pre-employment or background check history form the person filled in | Each employer, title, start and end month | It was signed, and a future background check will compare against it. |
| The career section of an old CV (curriculum vitae) | Titles, dates and achievement lines, as written then | Shows what they claimed at the time, before memory drifted. |
| Offer letters and contracts | Title, start date, employer's legal name | Primary source for the title and start. Skip the pay. |
| Farewell or handover emails sent on the last day | The date, and who they worked with | The most reliable end date there is. |
| Certificates, licences, and a regulator's or issuer's register entry | Credential, number only if public, issue and expiry dates | Often checkable online, so it can reach `verified`. |
| Logbooks (flight hours, sea time, clinical or supervised hours) | Totals by type, from the page totals | Hard numbers a hiring manager can trust. |
| Reference letters, awards, performance summaries | The words used about the person, and who said them | A second source for achievement claims. |
| Employer or university news, videos, press articles that name the person | The address, the date, what it says they did | Independent and public. |

Save what the person shares in `intake/sources/` (photos are fine). If a
photo shows something on the "never record" list, ask the person to crop it,
or copy the role lines and do not keep the photo.

## The rounds

Each round is 4 to 6 questions. A good order:

### Round 1: education

Skip what the first message already confirmed.

1. What did you study, where, and when did it start and finish (month and
   year if you know)?
2. Do you have the certificate, a transcript, or a graduation email?
3. Anything else formal since: short courses, licences, certifications?
4. For each, is there a register or issuer page where it can be checked?

### Round 2 onwards: one role at a time, earliest first

1. What was the organisation called then, and what is it called now?
2. Your exact title, as it appeared on paper (an offer letter, a business
   card, an email signature)? Was it ever "acting", "deputy", "assistant",
   "associate" or "interim"? Did it change while you were there?
3. Start and end month. What document shows them (an offer letter, a
   farewell email, a form)?
4. What did you actually do, in a sentence or two?
5. What are you proudest of there, and is there a number attached? Who or
   what could confirm it?
6. Is there anything on your CV, LinkedIn or website about this role that
   you would not want to defend in an interview?

Question 6 matters. In practice it is where a raised title, or work the
person never did, comes to light.

### Work rights

Ask the "Eligibility and work rights" questions in `INTAKE.md`: where the
person can work without sponsorship, visa routes, the degree, licences, the
background check and conflicts of interest. Ask two of them only when an
open role needs them, which `fetch_roles.py` counts in
`market/roles/latest.json` under `summary.blocker_counts`:

- the US export control question (`INTAKE.md` 1.4), only when
  `us_person_export_control` is above 0;
- the security clearance question (1.5), only when `security_clearance` or
  `australian_security_clearance` is above 0.

Until the person says they meet a requirement, the roles that state it
count as blocked (D6 = 0), which is the honest default. If a later run's
count goes above 0 for a question not yet asked, ask it then. If the person
raises either one themselves, record what they say.

### Gaps

1. Between these roles there is a gap from (month) to (month). What were you
   doing? (Study, a business, caring, travel, looking for work, a break are
   all fine answers.)
2. Is there anything that shows it, if you want it on the record?

Do not push for detail about a gap the person does not want to explain.
Record "prefers not to say" and move on. Never ask about health or family.

### Businesses and side work

1. Have you run your own business or done contract work? Name, dates, what
   it did, customers or revenue only if you are happy to share.
2. Is it registered anywhere public (a business register, a website, an app
   store)?

### Best stories

1. Tell me about two or three pieces of work you are proudest of. What was
   the problem, what did you do, what changed?
2. For each, what document, link, email or person backs it up?

### Referees

1. Who could confirm your title, dates and the stories above? For which
   claims? Have they agreed to be asked?

Record referees by role and relationship. Keep their contact details out of
evidence files and briefings (see `PRIVACY.md`).

### Motivation

Use the "Goals and motivation" and "Story" groups in `INTAKE.md`.

## After each round

1. **Record the answers** in `intake/answers.md`, under a heading for the
   round, in the person's words.
2. **Add evidence items** to `profile/evidence.json`: one fact per item,
   level `self_reported`, a source of type `interview` pointing at the
   heading, and a note "confirmed by the person on <date>". A document the
   person showed you is a second source of type `document`.
3. **Add the role** to the `confirmed` source in
   `profile/role-records.json` (see `CONSISTENCY.md`): title, start and end
   exactly as the person confirmed them. If they told you a public line is
   not true, add it to that role's `denies` list.
4. **List open questions** under `open_questions` in
   `profile/evidence.json`, each with what would answer it. Start the next
   round by reading them back.
5. **Look for corroboration** (below), then lift each item up the ladder
   only for sources you actually checked.

## Corroborating

| Source (each opt in, read only) | What to look for | Ladder effect |
|---|---|---|
| The person's own email | Offer letters, farewell emails on the last day, certification and course emails, project threads that show the work, introductions from colleagues | An email from the issuer or employer can make an item `verified`; a thread that shows the work is a second source (`corroborated`). |
| Public registers | A regulator's or licensing body's register of certificate or licence holders, a business register | `verified` if the register names the person and the credential. |
| Employer or university news and videos | Pages or videos that name the person and their role | `corroborated` (a second, independent source). |
| Press articles | Articles that name the person, their title or their work | `corroborated`. |
| Referees | A written note from the referee | `corroborated` for the claims they confirm. |

Email searches that tend to work, within the dates of each role: the
employer's domain plus "offer", "welcome", "farewell", "last day", "thank
you"; the issuer's name plus "certificate", "congratulations", "results".
Read only the messages the search returns; do not browse the mailbox.

Record each check as a new `sources` entry on the evidence item, with
`checked_on`. If a source contradicts what the person said, do not argue:
show them, ask which is right, and record both (the wrong one as
`contradicted`, with a note).

## Counting from photos

When the person asks you to count something from photos (logbook hours,
sea days, supervised hours):

1. Use the page totals and "carried forward" lines where the document has
   them, not every line.
2. Write a small table: page or date range, each column's total.
3. Add the totals twice, in two different ways (by page, then by column).
   If they differ, find the reason before going on.
4. Mark any digit you cannot read as uncertain, and give a range rather
   than a guess.
5. Record the result as one evidence item with the photos as its source,
   the page range, and the date you counted. Never round up.

## What never to record

Even if you see it in a document or an email:

- pay, payslips, bank details, tax or pension numbers;
- passwords, security questions, one-time codes, account numbers;
- government identity numbers (passport, licence numbers that are not
  public, tax file numbers);
- loan, debt, legal, court or immigration papers;
- health, medical or disability information;
- family details, and anything about age, gender, ethnicity, religion or
  other protected attributes;
- other people's contact details or personal matters.

Do not copy it, quote it or summarise it. If it is in a photo you were
given, tell the person and ask them to delete or crop it. If you saw it by
accident, say so and move on.

## Closing the interview

Before you finish, tell the person:

- what is now on record, and at what level;
- which open questions remain, and what would answer each;
- that the next step is the consistency audit (`CONSISTENCY.md`), which
  compares their CV, LinkedIn, website and forms against what they just
  confirmed.
