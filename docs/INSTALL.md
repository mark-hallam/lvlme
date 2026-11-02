# Install Climb

Climb is one folder: a skill (`SKILL.md`), method files, small Python scripts
and a demo. The same folder installs as a Claude Code plugin, as a Claude
Code skill, as a Codex skill, and as Cursor rules. Pick the one that matches
the agent you use.

You need Python 3.9 or newer (the scripts use only its standard library) and
git (a tool that copies and updates the folder). Nothing else.

In the commands below, `mark-hallam/climb` is the repository on GitHub, and
`https://github.com/mark-hallam/climb` is its full address. You can also use a
local copy of the folder.

## Claude Code

### Option A: plugin, one step (recommended)

In a Claude Code session (version 2.1.275 or later):

```text
/plugin install climb --marketplace mark-hallam/climb
```

Claude Code adds the Climb marketplace (a catalogue of plugins, here just
one), shows you what the plugin adds, and asks where to install it. Choose
"Install for you" so it works in every project.

The same thing from your terminal (version 2.1.292 or later):

```bash
claude plugin install climb --marketplace mark-hallam/climb
```

Or in two steps, on any recent version:

```text
/plugin marketplace add mark-hallam/climb
/plugin install climb@climb
```

### Option B: clone into your skills folder (the simple fallback)

```bash
git clone https://github.com/mark-hallam/climb ~/.claude/skills/climb
```

Start a new Claude Code session. Because the folder holds
`.claude-plugin/plugin.json`, Claude Code loads it as a skills folder plugin
named `climb@skills-dir`: `/climb` is the main skill and the other commands
carry the plugin prefix (for example `/climb:climb-interview`). If your
organisation's settings block skills folder plugins, `SKILL.md` still loads
as a plain skill, so `/climb` works and the other entry points work as words
after it (for example `/climb interview`).

To update: `git -C ~/.claude/skills/climb pull`.

### Option C: try it for one session

```bash
claude --plugin-dir /path/to/climb
```

### What you get

| Command | Does |
|---|---|
| `/climb` | Run Climb, or resume today's run. Also `/climb status`. |
| `/climb-interview` | The document-led career interview, first time or an update. |
| `/climb-screen` | The independent recruiter screen against real postings. |
| `/climb-audit` | The consistency audit (CV, LinkedIn, website, forms) and the public claims audit. |
| `/climb-dashboard` | Rebuild the dashboard and print the command to open it. |

Plugin commands also have a full name with the plugin prefix:
`/climb:climb`, `/climb:climb-interview` and so on. The short name works
unless another command already uses it.

The plugin also adds five subagents (helper agents with their own fresh
context) that `/climb` starts for the parallel run: `climb:evidence-scout`,
`climb:market-scout`, `climb:role-judge`, `climb:reviewer` and
`climb:recruiter-screen`. See [`ORCHESTRATION.md`](ORCHESTRATION.md).

You can also just say "run Climb" or "how likely am I to get a job at X?",
and Claude loads the skill.

### Check it loaded

```bash
claude plugin details climb@climb
```

Use `climb@skills-dir` for option B. In a session, `/plugin` lists it on the
**Installed** tab, and the **Errors** tab says why if it did not load.

### Updates

Plugins from marketplaces other than Anthropic's own do not update on their
own by default. Turn on auto-update for the Climb marketplace in `/plugin`
(**Marketplaces** tab), or update by hand:

```bash
claude plugin update climb@climb
```

## Codex

Codex reads personal skills from `~/.agents/skills/`, and `AGENTS.md` from the
folder you work in.

- **As a skill:** `git clone https://github.com/mark-hallam/climb ~/.agents/skills/climb`,
  then in Codex type `$climb` (or pick it from `/skills`) and say "run
  Climb".
- **In the engine folder:** open Codex in the cloned folder. It reads
  `AGENTS.md`, which runs the same procedure.

If your Codex cannot start subagents, Climb runs the same stages one after
another (see "Fallback" in [`ORCHESTRATION.md`](ORCHESTRATION.md)). For the
independent review and the recruiter screen, start a new Codex session and
give it only the packet the lead prepares.

## Cursor

Open the cloned folder in Cursor. The rules in `.cursor/rules/` load
automatically:

- `climb-hard-rules.mdc` applies to every chat in the folder.
- `climb-run.mdc` applies when you ask to run Climb, or when you mention it
  with `@climb-run`.

Cursor also reads `AGENTS.md`. Say "run Climb".

## By hand, in a terminal

See "By hand, in a terminal" in the
[README](../README.md#by-hand-in-a-terminal). Every script takes
`--workspace PATH`.

## Where your data goes

- Installing copies only the engine (no personal data). A plugin install
  keeps its copy under `~/.claude/plugins/`.
- Your data lives in your private workspace, by default
  `~/climb-workspaces/<goal>`, created on the first run. The scripts refuse a
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
