"""The first run: one canonical list in SKILL.md, a short first message, and work rights questions only when needed.

Offline and standard library only. Pins three things:
- SKILL.md holds the one "First run" list, and every other file that
  describes a first run links to it instead of giving its own order;
- the interview's first message is about 120 words at most and asks only
  three things (three CV facts to confirm, which organisations, the LinkedIn
  data export);
- the US export control and security clearance questions are asked only when
  fetch_roles.py counts an open role that needs them (summary.blocker_counts).
"""
import os
import re
import unittest

import helpers as H
import _common as C

ROOT = H.ENGINE
LINKERS = ["README.md", "AGENTS.md", "docs/INSTALL.md", "docs/ORCHESTRATION.md", "method/RUNBOOK.md",
           "method/INTERVIEW.md", "method/INTAKE.md", "skills/lvlme-interview/SKILL.md"]
MD_LINK = re.compile(r"\]\(([^)\s]+)\)")
WORD_CAP = 120


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def section(text, heading):
    """The body under a '## heading' line, up to the next heading of level 1 or 2."""
    m = re.search(r"^## %s\n(.*?)(?=^#{1,2} |\Z)" % re.escape(heading), text, re.M | re.S)
    if not m:
        raise AssertionError("no '## %s' section" % heading)
    return m.group(1)


def first_message():
    """The example first message in INTERVIEW.md, as the person would read it."""
    body = section(read("method/INTERVIEW.md"), "The first message")
    lines = [l[1:].strip() for l in body.splitlines() if l.startswith(">")]
    return "\n".join(lines), body


def words(message):
    """Words a reader sees: list numbers at the start of a line are not words."""
    return [w for line in message.splitlines() for w in re.sub(r"^\d+\.\s+", "", line).split()]


class CanonicalListTests(unittest.TestCase):
    def test_skill_md_holds_the_one_first_run_list(self):
        text = read("SKILL.md")
        self.assertEqual(len(re.findall(r"^## First run$", text, re.M)), 1)
        steps = re.findall(r"^(\d+)\. \*\*", section(text, "First run"), re.M)
        self.assertGreaterEqual(len(steps), 5)
        self.assertEqual(steps, [str(i) for i in range(1, len(steps) + 1)], "numbered in order, no gaps")
        body = " ".join(section(text, "First run").split())
        for must in ("scripts/init.py", "The first message", "LinkedIn data export", "blocker_counts",
                     "candidate.eligibility_cleared", "stages 4 to 10"):
            self.assertIn(must, body)
        # init.py comes first and the first message comes before the config is filled in
        self.assertLess(body.index("init.py"), body.index("The first message"))
        self.assertLess(body.index("The first message"), body.index("fill in `config.json`"))

    def test_other_files_link_to_it(self):
        for rel in LINKERS:
            with self.subTest(doc=rel):
                targets = [t for t in MD_LINK.findall(read(rel)) if t.endswith("#first-run")]
                self.assertTrue(targets, "%s does not link to SKILL.md#first-run" % rel)
                for t in targets:
                    path = os.path.normpath(os.path.join(ROOT, os.path.dirname(rel), t.split("#")[0]))
                    self.assertEqual(path, os.path.join(ROOT, "SKILL.md"))

    def test_no_second_first_run_order(self):
        runbook = section(read("method/RUNBOOK.md"), "First run only")
        self.assertEqual(re.findall(r"^\s*\d+\. ", runbook, re.M), [], "RUNBOOK repeats the steps instead of linking")
        for rel in ("method/INTERVIEW.md", "skills/lvlme-interview/SKILL.md"):
            text = " ".join(read(rel).split())
            with self.subTest(doc=rel):
                self.assertNotIn("questions 1 and 5", text, "the old order: goals before the first message")
        self.assertNotIn("starts with the example's organisations", " ".join(read("docs/HOW-IT-WORKS.md").split()))


class FirstMessageTests(unittest.TestCase):
    def test_about_120_words_at_most(self):
        message, body = first_message()
        n = len(words(message))
        self.assertLessEqual(n, WORD_CAP)
        self.assertIn("about %d words at most" % WORD_CAP, " ".join(body.split()))
        stated = re.search(r"\((\d+) words\)", body)
        self.assertIsNotNone(stated, "the example says how long it is")
        self.assertEqual(int(stated.group(1)), n, "the stated length matches the example")

    def test_asks_only_the_three_things(self):
        message, _ = first_message()
        flat = " ".join(message.split())
        self.assertEqual(len(re.findall(r"^\d+\. ", message, re.M)), 3, "three CV facts to confirm")
        self.assertIn("Is each right?", flat)
        self.assertIn("which organisations", flat)
        self.assertIn("LinkedIn data export", flat)
        self.assertIn("Get a copy of your data", flat)
        for later in (r"export control", r"export-control", r"clearance", r"US person", r"\bpay\b", r"salary",
                      r"citizen", r"visa", r"sponsor"):
            self.assertIsNone(re.search(later, flat, re.I), "the first message asks about %s" % later)

    def test_example_is_fictional_and_plain(self):
        message, _ = first_message()
        self.assertIn("Alex", message)
        self.assertIsNone(re.search("[–—]", message))
        self.assertNotIn(" - ", message)
        self.assertIsNone(re.search(r"(?i)revolutioni[sz]e|transform|game-changer|next-generation|ai-powered", message))
        cv = read("examples/demo-workspace/intake/sources/cv-alex-example.md")
        for fact in ("Contoso Freight", "2021", "Bachelor of Business (Logistics)", "2015", "all 6 sites"):
            self.assertIn(fact, cv, "the example's facts come from the fictional demo CV")
            self.assertIn(fact, message)


class WorkRightsTests(unittest.TestCase):
    def test_only_when_an_open_role_needs_them(self):
        intake = section(read("method/INTAKE.md"), "The question bank")
        bank = intake.split("### 2. Constraints")[0]
        q4 = " ".join(re.search(r"^4\. (.*?)(?=^5\. )", bank, re.M | re.S).group(1).split())
        q5 = " ".join(re.search(r"^5\. (.*?)(?=^6\. )", bank, re.M | re.S).group(1).split())
        self.assertIn("export-control", q4)
        self.assertIn("clearance", q5)
        for q, kind in ((q4, "us_person_export_control"), (q5, "security_clearance")):
            with self.subTest(kind=kind):
                self.assertIn("Ask only when an open role needs it", q)
                self.assertIn(kind, q)
        interview = " ".join(section(read("method/INTERVIEW.md"), "The rounds").split())
        self.assertIn("summary.blocker_counts", interview)
        for kind in ("us_person_export_control", "security_clearance"):
            self.assertIn("`%s` is above 0" % kind, interview)
        self.assertIn("honest default", interview)

    def test_the_counts_named_exist(self):
        schema = H.schema("roles.schema.json")
        counts = schema["properties"]["summary"]["properties"]["blocker_counts"]["properties"]
        self.assertEqual(list(counts), C.BLOCKER_TYPES)

    def test_fictional_demo_counts_match_its_roles(self):
        latest = H.load(os.path.join(ROOT, "examples", "demo-workspace", "market", "roles", "latest.json"))
        counts = latest["summary"]["blocker_counts"]
        for kind in C.BLOCKER_TYPES:
            with self.subTest(kind=kind):
                self.assertEqual(counts[kind], sum(1 for r in latest["roles"]
                                                   if kind in {b["type"] for b in r["eligibility_blockers"]}))
        # The demo has a government role, so Alex was asked both questions, and answered them.
        self.assertGreater(counts["us_person_export_control"], 0)
        answers = read("examples/demo-workspace/intake/answers.md")
        self.assertIn("US person for export-control purposes: no.", answers)
        self.assertIn("Security clearance: none.", answers)


if __name__ == "__main__":
    unittest.main()
