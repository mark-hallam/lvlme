"""Packaging: plugin and marketplace manifests, skill, subagent and Cursor rule files, and doc paths.

Offline and standard library only. Some engine paths are added by other work
streams (the interview, consistency audit, recruiter screen, profile fixes and
levels modules). Until those are merged, test_after_merge_paths skips with the
list of what is still missing, instead of failing; every other path must exist.
"""
import glob
import json
import os
import re
import unittest

import helpers as H

ROOT = H.ENGINE
COMMANDS = {"lvlme", "lvlme-interview", "lvlme-screen", "lvlme-audit", "lvlme-dashboard",
            "lvlme-autopilot", "lvlme-practice", "lvlme-debrief",
            "lvlme-public"}
REMOVED = {"scripts/quick.py", "scripts/quick_posting.py", "scripts/_quick_html.py", "scripts/_promote.py",
           "skills/lvlme-quick/SKILL.md", "schemas/quick.schema.json", "examples/build_quick_demo.py"}
AGENTS = {"evidence-scout", "market-scout", "role-judge", "reviewer", "recruiter-screen"}
INDEPENDENT = {"reviewer", "recruiter-screen"}
AFTER_MERGE = {"method/INTERVIEW.md", "method/CONSISTENCY.md", "scripts/consistency_audit.py",
               "method/RECRUITER_SCREEN.md", "templates/prompts/recruiter-screen.md",
               "method/PROFILE_FIXES.md", "docs/LEVELS.md"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
PLUGIN_KEYS = {"$schema", "name", "displayName", "version", "description", "author", "homepage", "repository",
               "license", "keywords", "metadata", "icon", "documentationUrl", "supportUrl", "privacyPolicyUrl",
               "termsOfServiceUrl", "defaultEnabled", "dependencies", "settings", "userConfig", "types", "channels",
               "skills", "commands", "agents", "hooks", "mcpServers", "lspServers", "outputStyles", "workflows",
               "experimental"}
MARKET_KEYS = {"$schema", "name", "owner", "plugins", "description", "version", "metadata",
               "forceRemoveDeletedPlugins", "allowCrossMarketplaceDependenciesOn", "renames"}
ENTRY_KEYS = {"name", "source", "description", "version", "category", "tags", "strict", "displayName",
              "author", "homepage", "repository", "license", "keywords", "defaultEnabled", "metadata"}
RESERVED_MARKETS = {"claude-code-marketplace", "claude-code-plugins", "claude-plugins-official",
                    "anthropic-marketplace", "anthropic-plugins", "agent-skills", "inline", "builtin",
                    "skills-dir", "synced", "npm", "pip", "uv", "cargo", "github", "gh"}
SKILL_KEYS = {"name", "description", "argument-hint", "disable-model-invocation"}
AGENT_KEYS = {"name", "description", "model", "effort", "maxTurns", "autoCompactWindow", "tools",
              "disallowedTools", "skills", "memory", "background", "omitClaudeMd", "isolation", "color"}
RULE_KEYS = {"description", "globs", "alwaysApply"}
ENGINE_PATH = re.compile(r"(?<![\w./-])((?:\.claude-plugin|\.cursor|method|scripts|docs|templates|schemas|"
                         r"examples|skills|agents|tests)/[A-Za-z0-9_./-]*)")
ROOT_FILE = re.compile(r"(?<![\w./-])(SKILL\.md|AGENTS\.md|README\.md|CONTRIBUTING\.md|LICENSE)(?![\w.-])")
MD_LINK = re.compile(r"\]\(([^)\s]+)\)")


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def packaging_docs():
    docs = ["SKILL.md", "AGENTS.md", "README.md", "docs/INSTALL.md", "docs/ORCHESTRATION.md",
            "docs/for-you/READING-YOUR-DASHBOARD.md", "CHANGELOG.md"]
    for pattern in ("skills/*/SKILL.md", "agents/*.md", ".cursor/rules/*.mdc"):
        docs += sorted(os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(ROOT, pattern)))
    return docs


def frontmatter(rel):
    """Parse the one-line-scalar YAML subset the packaging files use; fail on anything a YAML parser may read differently."""
    text = read(rel)
    if not text.startswith("---\n") or "\n---\n" not in text[3:]:
        raise AssertionError("%s: no frontmatter block" % rel)
    head, body = text[4:].split("\n---\n", 1)
    data = {}
    for line in head.splitlines():
        m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*): (.+)$", line)
        if not m:
            raise AssertionError("%s: frontmatter line is not 'key: value': %r" % (rel, line))
        key, value = m.groups()
        if value.startswith('"'):
            if not (value.endswith('"') and '"' not in value[1:-1]):
                raise AssertionError("%s: bad quoted value for %s" % (rel, key))
            value = value[1:-1]
        elif value in ("true", "false"):
            value = value == "true"
        elif value[0] in "[]{}&*!|>'%@`,#?:-" or ": " in value or " #" in value or value.endswith(":"):
            raise AssertionError("%s: value for %s needs quoting in YAML" % (rel, key))
        data[key] = value
    return data, body


def slug(heading):
    return re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", heading.strip().lower()))


class ManifestTests(unittest.TestCase):
    def test_plugin_manifest(self):
        plugin = H.load(os.path.join(ROOT, ".claude-plugin", "plugin.json"))
        self.assertEqual((plugin["name"], plugin["displayName"]), ("lvlme", "LVLme"))
        self.assertTrue(NAME_RE.match(plugin["name"]))
        self.assertLessEqual(set(plugin), PLUGIN_KEYS)
        for key in ("version", "description", "license"):
            self.assertTrue(isinstance(plugin.get(key), str) and plugin[key], key)
        self.assertTrue(plugin["author"]["name"])
        self.assertEqual(plugin["skills"], ["./"], "the root SKILL.md loads next to skills/ only with this key")
        for path in plugin["skills"]:
            self.assertTrue(path.startswith("./") and ".." not in path, path)
            self.assertTrue(os.path.isfile(os.path.join(ROOT, path, "SKILL.md")), path)
        extra = set(os.listdir(os.path.join(ROOT, ".claude-plugin"))) - {"plugin.json", "marketplace.json"}
        self.assertEqual(extra, set(), "components inside .claude-plugin/ do not load")

    def test_marketplace_manifest(self):
        market = H.load(os.path.join(ROOT, ".claude-plugin", "marketplace.json"))
        plugin = H.load(os.path.join(ROOT, ".claude-plugin", "plugin.json"))
        self.assertLessEqual(set(market), MARKET_KEYS)
        self.assertTrue(NAME_RE.match(market["name"]))
        self.assertNotIn(market["name"], RESERVED_MARKETS)
        self.assertTrue(market["owner"]["name"])
        self.assertTrue(market.get("description"))
        self.assertEqual(len(market["plugins"]), 1)
        entry = market["plugins"][0]
        self.assertLessEqual(set(entry), ENTRY_KEYS)
        self.assertEqual(entry["name"], plugin["name"])
        self.assertEqual(market["version"], plugin["version"])
        self.assertNotIn("version", entry, "plugin.json carries the version; a second copy drifts")
        self.assertEqual(entry["source"], "./")
        self.assertTrue(os.path.isfile(os.path.join(ROOT, entry["source"], ".claude-plugin", "plugin.json")))

    def test_old_plugin_name_is_renamed_not_dropped(self):
        """Installs of the plugin under its old name, climb, migrate to lvlme instead of breaking."""
        market = H.load(os.path.join(ROOT, ".claude-plugin", "marketplace.json"))
        self.assertEqual(market["name"], "lvlme")
        self.assertEqual(market.get("renames"), {"climb": "lvlme"})
        names = {e["name"] for e in market["plugins"]}
        for old, new in market["renames"].items():
            self.assertNotIn(old, names, "a renamed name must not also be a live entry")
            self.assertIn(new, names)


class ComponentTests(unittest.TestCase):
    def test_root_skill_is_portable(self):
        data, body = frontmatter("SKILL.md")
        self.assertEqual(set(data), {"name", "description"}, "keep the root skill to the portable Agent Skills fields")
        self.assertEqual(data["name"], "lvlme")
        for phrase in ('"run LVLme"', '"run Climb"'):   # the old name still triggers the skill
            self.assertIn(phrase, data["description"])
        self.assertLessEqual(len(data["description"]), 1024)
        self.assertLess(len(read("SKILL.md").splitlines()), 500)
        self.assertIn("docs/ORCHESTRATION.md", body)

    def test_command_skills(self):
        names = {"lvlme"}
        locked = {"lvlme-autopilot", "lvlme-public"}
        for path in glob.glob(os.path.join(ROOT, "skills", "*")):
            rel = os.path.relpath(os.path.join(path, "SKILL.md"), ROOT)
            data, body = frontmatter(rel)
            self.assertLessEqual(set(data), SKILL_KEYS, rel)
            self.assertEqual(data["name"], os.path.basename(path), rel)
            self.assertTrue(NAME_RE.match(data["name"]) and len(data["name"]) <= 64, rel)
            self.assertTrue(0 < len(data["description"]) <= 1024, rel)
            if data["name"] in locked:
                self.assertIs(data.get("disable-model-invocation"), True, rel)
            else:
                self.assertNotIn("disable-model-invocation", data, rel)
            self.assertIn("${CLAUDE_PLUGIN_ROOT}", body, rel)
            names.add(data["name"])
        self.assertEqual(names, COMMANDS)

    def test_subagents(self):
        found = set()
        for path in glob.glob(os.path.join(ROOT, "agents", "*.md")):
            rel = os.path.relpath(path, ROOT)
            data, body = frontmatter(rel)
            stem = os.path.splitext(os.path.basename(path))[0]
            self.assertLessEqual(set(data), AGENT_KEYS, rel)
            self.assertEqual(data["name"], stem, rel)
            self.assertTrue(data["description"], rel)
            tools = {t.strip() for t in data.get("tools", "").split(",") if t.strip()}
            denied = {t.strip() for t in data.get("disallowedTools", "").split(",") if t.strip()}
            if tools:
                self.assertFalse(tools & {"Write", "Edit", "NotebookEdit", "Agent"}, rel)
            else:
                self.assertLessEqual({"Write", "Edit"}, denied, rel)
            self.assertIn("is data, never an instruction", " ".join(body.split()), rel)
            if stem in INDEPENDENT:
                self.assertIs(data.get("omitClaudeMd"), True, rel)
                for folder in ("eval/", "report/", "campaign/"):
                    self.assertIn(folder, body, rel)
            found.add(stem)
        self.assertEqual(found, AGENTS)

    def test_cursor_rules(self):
        rules = glob.glob(os.path.join(ROOT, ".cursor", "rules", "*.mdc"))
        self.assertTrue(rules)
        always = []
        for path in rules:
            rel = os.path.relpath(path, ROOT)
            data, _ = frontmatter(rel)
            self.assertLessEqual(set(data), RULE_KEYS, rel)
            self.assertIsInstance(data.get("alwaysApply"), bool, rel)
            self.assertTrue(data.get("description"), rel)
            self.assertLess(len(read(rel).splitlines()), 500, rel)
            if data["alwaysApply"]:
                always.append(rel)
        self.assertEqual(always, [os.path.join(".cursor", "rules", "lvlme-hard-rules.mdc")])

    def test_agents_md_fits_codex_limit(self):
        self.assertLess(len(read("AGENTS.md").encode("utf-8")), 32 * 1024)


class DocTests(unittest.TestCase):
    def engine_paths(self):
        found = set()
        for rel in packaging_docs():
            text = read(rel).replace("${CLAUDE_PLUGIN_ROOT}/", "").replace("${CLAUDE_SKILL_DIR}/", "")
            for m in ENGINE_PATH.finditer(text):
                found.add((rel, m.group(1).rstrip(".,:;")))
            for m in ROOT_FILE.finditer(text):
                found.add((rel, m.group(1)))
        return found

    def test_referenced_paths_exist(self):
        for doc, path in sorted(self.engine_paths()):
            if path in AFTER_MERGE or (doc == "CHANGELOG.md" and path in REMOVED):
                continue   # the history may name a file that a later version removed
            with self.subTest(doc=doc, path=path):
                self.assertTrue(os.path.exists(os.path.join(ROOT, path)), "%s names missing %s" % (doc, path))

    def test_after_merge_paths(self):
        named = {path for _, path in self.engine_paths()}
        missing = sorted(p for p in AFTER_MERGE & named if not os.path.exists(os.path.join(ROOT, p)))
        if missing:
            self.skipTest("added by other work streams, not merged yet: " + ", ".join(missing))

    def test_markdown_links_resolve(self):
        for rel in packaging_docs():
            for target in MD_LINK.findall(read(rel)):
                if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                    continue
                path, _, anchor = target.partition("#")
                full = os.path.normpath(os.path.join(ROOT, os.path.dirname(rel), path))
                if os.path.relpath(full, ROOT) in AFTER_MERGE and not os.path.exists(full):
                    continue  # reported by test_after_merge_paths
                with self.subTest(doc=rel, link=target):
                    self.assertTrue(full.startswith(ROOT) and os.path.exists(full))
                    if anchor and full.endswith(".md"):
                        with open(full, encoding="utf-8") as fh:
                            heads = {slug(l.lstrip("#")) for l in fh if l.startswith("#")}
                        self.assertIn(anchor, heads)

    def test_commands_and_agents_are_documented(self):
        for doc in ("README.md", "docs/INSTALL.md"):
            text = read(doc)
            for name in COMMANDS:
                self.assertIn("/" + name, text, doc)
        orchestration = read("docs/ORCHESTRATION.md")
        for name in AGENTS:
            self.assertIn("lvlme:" + name, orchestration)
        for rel in packaging_docs():
            text = read(rel)
            for ref in re.findall(r"`/?lvlme:([a-z-]+)`", text):
                self.assertIn(ref, AGENTS | COMMANDS, "%s names unknown lvlme:%s" % (rel, ref))
            self.assertEqual(re.findall(r"\bclimb:[a-z]", text), [], "%s still uses the old climb: prefix" % rel)

    def test_install_doc_cites_the_formats_followed(self):
        text = read("docs/INSTALL.md")
        for page in ("plugins/manifest-reference", "plugins/marketplace-reference", "/skills", "sub-agents"):
            self.assertIn("code.claude.com/docs/en/" + page.lstrip("/"), text)
        self.assertIn("cursor.com/docs", text)

    def test_default_cadence_is_weekly_plus_changes(self):
        """The docs state one default: weekly, plus a run when something changes. No daily build-up."""
        for rel in ("SKILL.md", "method/RUNBOOK.md", "docs/ORCHESTRATION.md", "method/CAMPAIGN.md"):
            text = " ".join(read(rel).split())
            with self.subTest(doc=rel):
                self.assertRegex(text, r"when(ever)? something changes")
                self.assertIn("Scores only move when evidence changes", text)
                self.assertNotIn("build_up_weeks", text)
                self.assertNotRegex(text, r"(?i)daily during build-up|build-up \(daily\)")
        for cfg in (H.template_config(), H.example_config()):
            self.assertEqual(cfg["cadence"], {"mode": "weekly", "run_time": "07:00"})

    def test_github_addresses_use_the_repository_that_exists(self):
        """Every GitHub address names the plugin's own repository, and file links follow its default branch.

        mark-hallam/lvlme is not a public repository, and the public default branch is not main,
        so /blob/HEAD/ is the only branch path that works before and after a rename to main. The one
        exception: docs/RELEASE-<version>.md may link its own tag, v<version>, which never moves.
        """
        with open(os.path.join(ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
            repo = json.load(fh)["repository"]
        self.assertEqual(repo, "https://github.com/mark-hallam/lvlme")
        own = re.compile(r"github\.com/mark-hallam/([A-Za-z0-9_.-]+)(/blob/([^/\s\"')]+)/)?")
        for dirpath, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if not d.startswith(".") or d in (".claude-plugin", ".cursor")]
            if os.path.relpath(dirpath, ROOT).split(os.sep)[0] == "tests":
                continue
            for name in files:
                if not name.endswith((".md", ".mdc", ".json", ".html", ".py", ".txt")):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, name), ROOT)
                for m in own.finditer(read(rel)):
                    with self.subTest(file=rel, address=m.group(0)):
                        self.assertEqual("https://github.com/mark-hallam/" + m.group(1).rstrip("."), repo)
                        if m.group(2):  # release notes may pin their own tag (a relative link 404s on the release page)
                            tag = re.match(r"RELEASE-(\d+\.\d+\.\d+)\.md$", name) if rel.startswith("docs" + os.sep) else None
                            self.assertIn(m.group(3), ["HEAD"] + (["v" + tag.group(1)] if tag else []))

    def test_plain_punctuation(self):
        """No em or en dashes, and no spaced hyphen used as a dash, outside code."""
        for rel in packaging_docs():
            in_code = False
            for n, line in enumerate(read(rel).splitlines(), 1):
                if line.lstrip().startswith("```"):
                    in_code = not in_code
                    continue
                prose = re.sub(r"`[^`]*`", "", line)
                with self.subTest(doc=rel, line=n):
                    self.assertIsNone(re.search("[–—]", line))
                    if not in_code:
                        self.assertNotIn(" - ", re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", prose))


class NetworkTests(unittest.TestCase):
    def test_only_three_scripts_can_reach_the_network(self):
        """AGENTS.md: network calls only in fetch_roles.py, fetch_doors.py and claims_audit.py."""
        net = re.compile(r"\b(urllib\.request|urlopen|http\.client|socket|ftplib|smtplib)\b")
        found = sorted(name for name in os.listdir(os.path.join(ROOT, "scripts"))
                       if name.endswith(".py") and net.search(read(os.path.join("scripts", name))))
        self.assertEqual(found, ["claims_audit.py", "fetch_doors.py", "fetch_roles.py"])


class QuickRetiredTests(unittest.TestCase):
    """LVLme quick was removed in 0.7.0: LVLme works with a goal. Nothing in the product may still offer it."""

    # The only places that may say the words: the history, and the lines that route "run LVLme quick" to a goal.
    ALLOWED = {"CHANGELOG.md", "SKILL.md", "AGENTS.md", os.path.join(".cursor", "rules", "lvlme-run.mdc")}

    def test_no_quick_skill_command_script_schema_or_demo_is_left(self):
        for rel in ("skills/lvlme-quick", "scripts/quick.py", "scripts/quick_posting.py", "scripts/_quick_html.py",
                    "schemas/quick.schema.json", "examples/quick-demo", "examples/build_quick_demo.py",
                    "docs/demo/quick", "tests/test_quick.py"):
            self.assertFalse(os.path.exists(os.path.join(ROOT, rel)), rel)

    def test_no_file_points_at_quick(self):
        word = re.compile(r"quick[-_ ](?:demo|posting|result|mode)|lvlme[- ]quick|/quick/|quick\.py", re.I)
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
            for name in files:
                rel = os.path.relpath(os.path.join(base, name), ROOT)
                if rel in self.ALLOWED or rel.startswith(os.path.join("docs", "RELEASE-")) or name == "test_packaging.py":
                    continue
                if not name.endswith((".md", ".py", ".json", ".mdc", ".html", ".txt")):
                    continue
                with open(os.path.join(base, name), encoding="utf-8", errors="ignore") as fh:
                    self.assertIsNone(word.search(fh.read()), rel)

    def test_the_words_run_lvlme_quick_route_to_setting_a_goal(self):
        for rel in ("SKILL.md", "AGENTS.md"):
            text = read(rel)
            self.assertRegex(text, r"(?i)no quick mode", rel)
            self.assertRegex(text, r"(?i)goal", rel)
        self.assertFalse(re.search(r"skills/lvlme-quick", read("SKILL.md") + read("AGENTS.md")))


if __name__ == "__main__":
    unittest.main()
