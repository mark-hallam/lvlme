# LVLme 0.6.0: from plan to people

LVLme is for the job you can't get yet. It works out honestly how far you are
from a job, gives you the steps to get there, and measures again as you go.

Most of those steps come down to people: meeting the ones who hire, showing
them your work, and being ready when the conversation comes. This release
helps with each of them. It finds the events and programmes where people from
your target organisations will be, gives you a one-page research pack before
you meet them, helps you show your work in public, keeps your best interview
stories ready, and helps you practise. And it checks itself: once you have
applied, it sets the odds it gave on the day you applied against what
happened.

How a score is worked out did not change, and none of the new features changes
one (a test proves it for each).

## Added

- **Doors.** Upcoming events, conferences, communities and programmes where
  people from your target organisations will be, each with its date, place
  and source, from public event calendars you name and from fellowship and
  residency postings. Each can become a plan step, and someone you met there
  goes into your contacts tracker. Meetup, Eventbrite and LinkedIn are never
  fetched. You register yourself.
- **How right has LVLme been?** The odds LVLme gave each application on the
  day you sent it, against what happened, beside public figures (Ashby's
  study of over 38 million applications, 16 May 2025: 3% of inbound and 40%
  of referred applications reached interview). Small numbers stay hidden
  until there are enough results to mean something.
- **Research packs.** One page per target organisation: what it is building,
  recent news, offices, the teams hiring, its events and programmes, and its
  rules on AI for candidates. Every line has its source and date, and a line
  nobody has checked yet says so.
- **Interview story bank.** Your best true stories, in your words, each
  linked to its evidence and the interview themes it answers. The card shows
  which themes have a story backed by evidence and which still need one.
- **Practise before an interview, debrief after.** `/lvlme-practice` builds
  questions from the posting and your stories and gives feedback on structure
  and evidence, never a script. `/lvlme-debrief` records what a real
  interview asked and how it went. Both refuse while an interview is
  happening.
- **Build in public.** `/lvlme-public` suggests what you finished that is
  worth sharing, drafts a post from your notes in your voice, and keeps a
  record of what you posted and what it led to. A post counts as proof once
  its link is checked. LVLme drafts; you post.
- **Offer help.** The pay range the posting advertised beside your offer, and
  what to ask the employer and a lawyer before you sign. A checklist, not
  advice.
- **Import from career-ops.** Already use
  [career-ops](https://github.com/career-ops-hq/career-ops)? LVLme reads its
  applications and their history, contacts at your targets and its interview
  stories, read only, so you can keep both. Tested against career-ops' own
  test files.

## Fixed

- The dashboard ranked a plan step whose roles all look suspicious as high as
  any other, while the scoring scripts put it last. Both now put it last.

The full list is in [CHANGELOG.md](https://github.com/mark-hallam/lvlme/blob/v0.6.0/CHANGELOG.md).

## Checked by

- 499 tests pass, including new ones for each feature above, and one per
  feature proving scores are the same with or without it.
- `claude plugin validate --strict` on the manifest.
- The fictional demo rebuilt with every new card, and checked on a phone.
