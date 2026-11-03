# Install LVLme

LVLme is one folder: a skill (`SKILL.md`), method files, small Python scripts
and a demo. The same folder installs as a Claude Code plugin, as a Claude
Code skill, as a Codex skill, and as Cursor rules. Pick the one that matches
the agent you use.

You need Python 3.9 or newer (the scripts use only its standard library) and
git (a tool that copies and updates the folder). Nothing else.

In the commands below, `mark-hallam/lvlme` is the repository on GitHub, and
`https://github.com/mark-hallam/lvlme` is its full address. You can also use a
local copy of the folder.

## Claude Code

### Option A: plugin, one step (recommended)

In a Claude Code session (version 2.1.275 or later):

```text
/plugin install lvlme --marketplace mark-hallam/lvlme
```

Claude Code adds the LVLme marketplace (a catalogue of plugins, here just
one), shows you what the plugin adds, and asks where to install it. Choose
"Install for you" so it works in every project.

The same thing from your terminal (version 2.1.292 or later):

```bash
claude plugin install lvlme --marketplace mark-hallam/lvlme
```

Or in two steps, on any recent version:

```text
/plugin marketplace add mark-hallam/lvlme
/plugin install lvlme@lvlme
```

### Option B: clone into your skills folder (the simple fallback)

```bash
git clone https://github.com/mark-hallam/lvlme ~/.claude/skills/lvlme
```

Start a new Claude Code session. Because the folder holds
`.claude-plugin/plugin.json`, Claude Code loads it as a skills folder plugin
named `lvlme@skills-dir`: `/lvlme` is the main skill and the other commands
carry the plugin prefix (for example `/lvlme:lvlme-interview`). If your
organisation's settings block skills folder plugins, `SKILL.md` still loads
as a plain skill, so `/lvlme` works and the other entry points work as words
after it (for example `/lvlme interview`).

To update: `git -C ~/.claude/skills/lvlme pull`.

### Option C: try it for one session

```bash
claude --plugin-dir /path/to/lvlme
```

### What you get

| Command | Does |
|---|---|
| `/lvlme` | Run LVLme, or resume today's run. Also `/lvlme status`. |
| `/lvlme-quick` | LVLme quick: honest odds for one posting, from a link and your CV, in a couple of minutes. |
| `/lvlme-interview` | The document-led career interview, first time or an update. |
| `/lvlme-screen` | The independent recruiter screen against real postings. |
| `/lvlme-audit` | The consistency audit (CV, LinkedIn, website, forms) and the public claims audit. |
| `/lvlme-dashboard` | Rebuild the dashboard and print the command to open it. |
| `/lvlme-autopilot` | Turn Autopilot on or off: a check-in that runs itself on your schedule, after asking for each permission. Needs a scheduler: the Claude desktop app's scheduled tasks, or your computer's own. |

Plugin commands also have a full name with the plugin prefix:
`/lvlme:lvlme`, `/lvlme:lvlme-interview` and so on. The short name works
unless another command already uses it.

The plugin also adds five subagents (helper agents with their own fresh
context) that `/lvlme` starts for the parallel run: `lvlme:evidence-scout`,
`lvlme:market-scout`, `lvlme:role-judge`, `lvlme:reviewer` and
`lvlme:recruiter-screen`. See [`ORCHESTRATION.md`](ORCHESTRATION.md).

You can also just say "run LVLme" or "how likely am I to get a job at X?",
and Claude loads the skill.

### Check it loaded

```bash
claude plugin details lvlme@lvlme
```

Use `lvlme@skills-dir` for option B. In a session, `/plugin` lists it on the
**Installed** tab, and the **Errors** tab says why if it did not load.

### Updates

Plugins from marketplaces other than Anthropic's own do not update on their
own by default. Turn on auto-update for the LVLme marketplace in `/plugin`
(**Marketplaces** tab), or update by hand:

```bash
claude plugin update lvlme@lvlme
```

## Claude chat (the Claude app and claude.ai)

Tried on 3 November 2026, on claude.ai with LVLme 0.4.0. The Claude desktop
app shows the same Customize page.

1. Open **Customize**, then **Plugins**.
2. Choose **Add**, then **Add marketplace**, then **Add from repository**.
   Type `mark-hallam/lvlme`, choose it, and press **Sync**. Anthropic's
   notice says to add only marketplaces you trust.
3. LVLme appears in the list. Press **Add**. It shows 6 skills: `/lvlme`,
   `/lvlme-quick`, `/lvlme-audit`, `/lvlme-dashboard`, `/lvlme-interview` and
   `/lvlme-screen`.
4. In a new chat, type `/lvlme-quick`, choose it, then paste the posting
   link and your CV text, and send.

Claude asks before each command it runs in its sandbox (choose **Allow
once**). A run took about three minutes, and the result page opened beside
the chat.

What to expect in chat:

- **LVLme quick works.** It reads the posting, scores it with the same maths
  and shares the result page.
- **The blind reviewer**, when a score is above 2, is a helper agent, and
  chat does not load helper agents. Start it in a new chat, as the quick
  steps say. Until it has run, those scores count as 2, so a missing review
  only ever lowers the odds.
- **The full campaign belongs in Claude Code.** Chat runs LVLme in Claude's
  sandbox, not on your computer, so there is no private workspace to come
  back to next week.
- A plugin added here is saved to your Claude account and also appears in
  Claude Code from its next session
  ([Anthropic's platform table](https://claude.com/docs/plugins/platform-support.md)).
  To turn it off: **Customize**, **Plugins**, LVLme, then its switch.

## Codex

Codex reads personal skills from `~/.agents/skills/`, and `AGENTS.md` from the
folder you work in.

- **As a skill:** `git clone https://github.com/mark-hallam/lvlme ~/.agents/skills/lvlme`,
  then in Codex type `$lvlme` (or pick it from `/skills`) and say "run
  LVLme quick" with a job link, or "run LVLme".
- **In the engine folder:** open Codex in the cloned folder. It reads
  `AGENTS.md`, which runs the same procedure.

If your Codex cannot start subagents, LVLme runs the same stages one after
another (see "Fallback" in [`ORCHESTRATION.md`](ORCHESTRATION.md)). For the
independent review and the recruiter screen, start a new Codex session and
give it only the packet the lead prepares.

## Cursor

Open the cloned folder in Cursor. The rules in `.cursor/rules/` load
automatically:

- `lvlme-hard-rules.mdc` applies to every chat in the folder.
- `lvlme-run.mdc` applies when you ask to run LVLme, or when you mention it
  with `@lvlme-run`.

Cursor also reads `AGENTS.md`. Say "run LVLme quick" with a job link, or
"run LVLme".

## Your first run

Say "run LVLme quick" with a job link for one honest answer, or "run LVLme"
for the full campaign. The full campaign's first message is short: it asks
you to confirm three facts from your CV, which organisations you want, and
for your LinkedIn data export. Every step of a first run, in order, is in
["First run"](../SKILL.md#first-run).

## Coming from Climb

LVLme was called Climb until 3 November 2026. What changed, and what still
works:

- **The plugin.** The marketplace now lists the plugin as `lvlme` and records
  that `climb` was renamed to it. On your machine the marketplace keeps the
  name you added it under, `climb`. Update it, then install the new name once:

  ```text
  /plugin marketplace update climb
  /plugin install lvlme@climb
  ```

  A new install by the old plugin name finds nothing: use `lvlme`, as in the
  commands at the top of this page.
- **The commands.** `/climb`, `/climb-quick` and the rest are now `/lvlme`,
  `/lvlme-quick` and so on, and the helper agents are `lvlme:reviewer` and so
  on. Saying "run Climb" or "run Climb quick" still starts the same thing.
- **A cloned folder.** The repository address has not changed, so
  `git -C ~/.claude/skills/climb pull` keeps updating it. The skill inside is
  now called `lvlme`. In Codex, type `$lvlme`.
- **Your workspace.** Nothing to do. When `LVLME_HOME` is not set, the scripts
  read `CLIMB_HOME`. When `~/lvlme-workspaces/` does not exist, they use
  `~/climb-workspaces/` and say so once. To move to the new names, rename the
  folder and change the setting at the same time.
- **The dashboard.** The theme and the "Pending" ticks your browser saved
  under the old name still load.

## By hand, in a terminal

See "By hand, in a terminal" in
[How LVLme works](HOW-IT-WORKS.md#by-hand-in-a-terminal). Every script takes
`--workspace PATH`.

## Where your data goes

- Installing copies only the engine (no personal data). A plugin install
  keeps its copy under `~/.claude/plugins/`.
- Your data lives in your private workspace, by default
  `~/lvlme-workspaces/<goal>`, created on the first run. The scripts refuse a
  workspace inside the engine folder, or inside any git repository that has a
  remote.
- An agent that runs in the cloud sees whatever it reads. Decide that on
  purpose. See [`method/PRIVACY.md`](../method/PRIVACY.md).

## For maintainers

- **Layout.** `.claude-plugin/plugin.json` is the plugin manifest.
  `.claude-plugin/marketplace.json` makes the repository its own marketplace
  (the plugin's source is `"./"`, the repository root). `SKILL.md` at the
  root is the main skill; the manifest's `"skills": ["./"]` keeps it loading
  next to the command skills in `skills/`. Subagents are in `agents/`.
- **Version.** `version` in `plugin.json` pins users to that version until it
  changes, so bump it with every release. Do not also set a version in the
  marketplace entry.
- **Changelog.** In the same change, turn the Unreleased section of
  [`CHANGELOG.md`](../CHANGELOG.md) into a heading for the new version, with
  its date and its test count, and tag the release commit (`v0.4.0` and so
  on). `tests/test_changelog.py` fails if the newest heading is not the
  version in `plugin.json`.
- **Validate** before every release:

  ```bash
  claude plugin validate --strict .claude-plugin/plugin.json
  claude plugin validate --strict .claude-plugin/marketplace.json
  python3 -m unittest discover -s tests
  ```

  `tests/test_packaging.py` checks offline that both manifests parse, that
  every skill and subagent file has valid frontmatter, and that every engine
  path the packaging docs name exists.

## Documentation this follows

Checked on 2 November 2026:

- Claude Code plugin manifest reference: https://code.claude.com/docs/en/plugins/manifest-reference
- Claude Code plugin components (skills, commands, subagents): https://code.claude.com/docs/en/plugins/components
- Claude Code marketplace reference: https://code.claude.com/docs/en/plugins/marketplace-reference
- Claude Code install and manage plugins: https://code.claude.com/docs/en/plugins/install
- Claude Code plugin loading (skills folder plugins, `--plugin-dir`): https://code.claude.com/docs/en/plugins/loading
- Claude Code create a plugin (root `SKILL.md` naming): https://code.claude.com/docs/en/plugins/create
- Claude Code skills (frontmatter, command names, size): https://code.claude.com/docs/en/skills
- Claude Code subagents (frontmatter, fresh context, parallel runs): https://code.claude.com/docs/en/sub-agents
- Codex skills (locations, `$skill` invocation): https://learn.chatgpt.com/docs/build-skills (the address https://developers.openai.com/codex/skills now redirects there)
- Codex `AGENTS.md` (discovery, 32 KiB limit): https://learn.chatgpt.com/docs/agent-configuration/agents-md (redirected from https://developers.openai.com/codex/guides/agents-md)
- Cursor rules (`.cursor/rules/*.mdc`, `AGENTS.md`): https://cursor.com/docs/context/rules
