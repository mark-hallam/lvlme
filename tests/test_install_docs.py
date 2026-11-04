"""The install guide, README and release notes say what is true today (fixes from the 5 November 2026 new-user test)."""
import glob
import os
import re
import unittest

import helpers as H

ROOT = H.ENGINE
UNTESTED = "Cursor and other agents that run commands are not tested yet"


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def flat(text):
    return re.sub(r"\s+", " ", text)


def skill_names():
    names = ["lvlme"] if os.path.isfile(os.path.join(ROOT, "SKILL.md")) else []
    return names + sorted(os.path.basename(os.path.dirname(p))
                          for p in glob.glob(os.path.join(ROOT, "skills", "*", "SKILL.md")))


class ClaudeCodeOptionB(unittest.TestCase):
    def test_option_b_installs_from_a_local_copy(self):
        text = flat(read("docs/INSTALL.md"))
        version = read(".claude-plugin/plugin.json")
        version = re.search(r'"version":\s*"([^\"]+)"', version).group(1)
        for line in ("git clone --branch v%s https://github.com/mark-hallam/lvlme ~/lvlme-engine" % version,
                     "claude plugin marketplace add ~/lvlme-engine", "claude plugin install lvlme@lvlme"):
            self.assertIn(line, text)
        # the skills folder clone hides the main /lvlme command: the guide must not offer it as an option
        self.assertNotIn("git clone https://github.com/mark-hallam/lvlme ~/.claude/skills/lvlme", text)
        self.assertNotIn("Use `lvlme@skills-dir` for option B", text)

    def test_readme_does_not_offer_the_skills_folder_clone(self):
        text = flat(read("README.md"))
        self.assertNotIn("~/.claude/skills/lvlme", text)
        self.assertNotIn("With the cloned folder, use the prefixed name", text)


class ClaudeChatSkillCount(unittest.TestCase):
    def test_the_count_and_list_match_the_plugin(self):
        text = flat(read("docs/INSTALL.md"))
        m = re.search(r"The plugin holds (\d+) skills: (.*?)\.\s", text)
        self.assertIsNotNone(m, "the Claude chat step must say how many skills the plugin holds")
        real = skill_names()
        self.assertEqual(int(m.group(1)), len(real))
        listed = re.findall(r"`/([a-z-]+)`", m.group(2))
        self.assertEqual(sorted(listed), sorted(real))
        self.assertNotIn("It shows 6 skills", text)


class CodexInstall(unittest.TestCase):
    def test_exact_clone_and_no_skill_installer(self):
        version = re.search(r'"version":\s*"([^\"]+)"', read(".claude-plugin/plugin.json")).group(1)
        for rel in ("docs/INSTALL.md", "README.md"):
            text = flat(read(rel))
            with self.subTest(doc=rel):
                self.assertIn("git clone --branch v%s https://github.com/mark-hallam/lvlme ~/.agents/skills/lvlme" % version, text)
                self.assertIn("skill installer", text)
                self.assertIn("only part of the folder", text)

    def test_agents_repair_a_partial_copy(self):
        for rel in ("SKILL.md", "AGENTS.md"):
            with self.subTest(doc=rel):
                self.assertIn("sparse-checkout disable", read(rel))


class AskFirst(unittest.TestCase):
    def test_agents_md_asks_before_each_install_or_run(self):
        rules = read("AGENTS.md").split("## Hard rules", 1)[1]
        first = rules.strip().split("\n- ", 1)[0]
        self.assertIn("Stop and wait for the person's yes before each install or run, even if they asked you to set "
                      "it up.", flat(first))

    def test_skill_md_asks_before_each_install(self):
        rules = flat(read("SKILL.md").split("## Hard rules", 1)[1])
        self.assertIn("stop and wait for the person's yes before each install", rules)


class AgentDependence(unittest.TestCase):
    def test_docs_say_agents_can_judge_differently(self):
        for rel in ("README.md", "docs/HOW-IT-WORKS.md"):
            text = flat(read(rel))
            with self.subTest(doc=rel):
                self.assertIn("same judgements always give the same score", text)
                self.assertIn("can judge the same evidence differently", text)
                self.assertNotIn("same inputs always give the same result", text)


class CursorUntested(unittest.TestCase):
    CLAIMS = re.compile(r"Codex (?:or|and) Cursor|Cursor / Grok|Claude Code, Codex,? (?:or|and) Cursor")

    def docs(self):
        """Every current doc: Markdown, Cursor rules and the demo page builder (history and the built demo excluded)."""
        out = []
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in (".git", "demo", "demo-workspace", "quick-demo", "tests")]
            for name in files:
                rel = os.path.relpath(os.path.join(base, name), ROOT)
                if rel in ("CHANGELOG.md", os.path.join("docs", "RELEASE-0.3.0.md")):
                    continue
                if name.endswith((".md", ".mdc")) or rel == os.path.join("examples", "build_demo_site.py"):
                    out.append(rel)
        return out

    def test_no_doc_claims_cursor_is_tested(self):
        for rel in self.docs():
            with self.subTest(doc=rel):
                self.assertIsNone(self.CLAIMS.search(flat(read(rel))))

    def test_front_doors_say_cursor_is_untested(self):
        for rel in ("README.md", "docs/INSTALL.md", "AGENTS.md"):
            with self.subTest(doc=rel):
                self.assertIn(UNTESTED, flat(read(rel)))


class ReleaseNotes(unittest.TestCase):
    def test_changelog_links_are_full_addresses_pinned_to_the_tag(self):
        notes = glob.glob(os.path.join(ROOT, "docs", "RELEASE-*.md"))
        self.assertTrue(notes)
        for path in notes:
            version = re.search(r"RELEASE-(\d+\.\d+\.\d+)\.md$", path).group(1)
            with open(path, encoding="utf-8") as fh:
                links = re.findall(r"\]\(([^)]*CHANGELOG[^)]*)\)", fh.read())
            with self.subTest(version=version):
                for link in links:
                    self.assertEqual(link, "https://github.com/mark-hallam/lvlme/blob/v%s/CHANGELOG.md" % version)

    def test_this_release_has_notes(self):
        with open(os.path.join(ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8") as fh:
            version = re.search(r'"version":\s*"([^"]+)"', fh.read()).group(1)
        path = os.path.join("docs", "RELEASE-%s.md" % version)
        self.assertTrue(os.path.isfile(os.path.join(ROOT, path)), path)
        self.assertIn("https://github.com/mark-hallam/lvlme/blob/v%s/CHANGELOG.md" % version, read(path))


if __name__ == "__main__":
    unittest.main()
