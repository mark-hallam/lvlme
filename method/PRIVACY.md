# Privacy

career-eval handles some of the most personal data there is: your work
history, your contacts, your pay, your plans. It is built to keep that data on
your machine and out of anyone else's hands.

## Where your data lives

- **The engine repository holds no personal data.** It contains the method,
  the scripts, empty templates and a fictional demo. Nothing you enter goes
  into it.
- **Your workspace is a separate, private folder** on your own computer. By
  default it is `~/career-eval-workspaces/<goal>`, or wherever
  `$CAREER_EVAL_HOME` points. `init.py` makes it readable by your user account
  only.
- **The scripts refuse an unsafe workspace.** Every script checks the
  workspace location and refuses one inside the engine repository (except
  the fictional demo) or inside any git repository (a version-controlled
  folder) that has a remote, meaning a copy on a server such as GitHub. That
  stops your data being pushed somewhere by accident.

## What is stored, and where

| Data | File | Notes |
|---|---|---|
| Interview answers | `intake/answers.md` | Includes notice period, contract terms and minimum pay if you give them. |
| Exports you supply | `intake/sources/` | LinkedIn export, résumé. Delete them whenever you like. |
| Evidence | `profile/evidence.json` | Facts about you, each with its source. |
| Network | `profile/network.json` | Names, positions and companies of contacts at target organisations. Email addresses from the export are dropped. |
| Public claims | `profile/claims-audit.json` | Sentences from your public pages, and how well the evidence supports them. |
| Open roles | `market/` | Public job postings. |
| Scores, SWOT, plan | `eval/`, `campaign/` | Judgements and the campaign. |
| Report | `report/` | The dashboard and the agent briefing files. |

## Other people's data

Contacts, referees and email senders did not sign up for this. So:

- Their data stays in your workspace.
- It is never copied into the agent briefing (`report/for-agents/`) or into
  drafts unless you opt in.
- The dashboard shows contact names only if `privacy.show_contact_names_in_dashboard`
  is true. Otherwise it shows counts and positions, and replaces any contact
  name that appears in other text on the page (an evidence note, an action
  title) with `[contact]`.
- The engine can only hide names it knows: the people listed in
  `profile/network.json`. Keep other people's names (referees, email senders)
  out of evidence and plan text, or add them to `privacy.redact_terms`.
- `network_map.py` prints counts only, never names, and does not keep email
  addresses.

## Sensitive mode

`privacy.sensitive_mode` in `config.json` is **on by default**. It controls
the two files written for other agents, `report/for-agents/SUMMARY.md` and
`report/for-agents/dashboard.json`. In sensitive mode they:

- omit the text of evidence claims and of the claims audit;
- omit contact names and compensation figures;
- replace every word in `privacy.redact_terms` (put your employers' names
  there) with `[redacted]`;
- replace any contact name from `profile/network.json` with `[contact]`;
- replace money amounts with `[salary]`.

Contact names appear in the agent files only if
`privacy.share_contact_names_with_agents` is true **and** sensitive mode is
off.

## Cloud agents see whatever they read

An AI agent that runs in the cloud sends what it reads to its provider. If
you point one at your workspace, your evidence, contacts and plans go with it.
Before you do:

- keep sensitive mode on;
- point helper agents at `report/for-agents/` only;
- prefer an agent that runs on your own machine for the full run.

## Connectors

Email, calendar and browser access are **opt in and read only**. The agent
asks first, reads only what the run needs (for example, emails from the
target organisations' domains or from job boards since the last run), and
never sends, deletes, labels or changes anything.

## Protected attributes

The engine never asks about, infers, records or scores age, gender,
ethnicity, disability, religion or family status. It does not ask for a date
of birth or a photo. Work rights are recorded only as you state them, and used
only to match what a posting legally requires. If you volunteer something
sensitive, the agent does not record it.

## Network access and telemetry

- No telemetry. Nothing reports back to anyone.
- `fetch_roles.py` calls only the public job-board APIs (application
  programming interfaces) for the targets in your config.
- `claims_audit.py` fetches only the addresses you pass it.
- No other script uses the network.

## What the engine never does

- Apply for a job.
- Send an email or message, or post publicly.
- Accept an invitation, or change any account (LinkedIn, website, GitHub,
  email).
- Scrape LinkedIn (use the official data export instead).
- Copy your workspace anywhere.

## Deleting your data

Your data is just files in your workspace. To delete it all, delete the
workspace folder. To delete one kind of data, delete that file (for example
`profile/network.json` and `intake/sources/Connections.csv` for your
contacts). If you used a cloud agent, its provider may keep its own copy:
check that provider's settings.
