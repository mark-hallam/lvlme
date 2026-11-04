"""Small A9 fixes: release pin, truthful install notes and campaign output."""
import io
import json
import os
import re
import unittest
from unittest import mock

import helpers as H
import autopilot
import applications
import build_dashboard
import run_plan
import _quick_html as QH

ROOT = H.ENGINE


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


class A9Docs(unittest.TestCase):
    def test_release_clone_commands_share_plugin_version(self):
        version = H.load(os.path.join(ROOT, ".claude-plugin", "plugin.json"))["version"]
        for rel in ("README.md", "docs/INSTALL.md", "agents.md"):
            with self.subTest(doc=rel):
                text = read(rel)
                for line in re.findall(r"git clone[^\n`]*https://github.com/mark-hallam/lvlme[^\n`]*", text):
                    self.assertIn("--branch v" + version, line)

    def test_plugin_and_marketplace_versions_match(self):
        plugin = H.load(os.path.join(ROOT, ".claude-plugin", "plugin.json"))
        market = H.load(os.path.join(ROOT, ".claude-plugin", "marketplace.json"))
        self.assertEqual(market.get("version"), plugin["version"])

    def test_install_docs_do_not_claim_plain_plugin_list_shows_path(self):
        for rel in ("README.md", "docs/INSTALL.md", "agents.md"):
            self.assertNotRegex(read(rel), r"claude plugin list.{0,120}Path")

    def test_quick_requirement_note_is_lowercase_and_has_no_period_inside_parentheses(self):
        text = QH.adjustments({"adjustments": ["Hard requirement lacking"],
                               "hard_requirement_note": "The posting asks for a quota-carrying sales."})[0]
        self.assertIn("missing (the posting asks for a quota-carrying sales),", text)


class A9Campaign(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)

    def test_week_rebuild_uses_requested_date(self):
        with mock.patch("sys.stdout", io.StringIO()), mock.patch("build_dashboard.main", wraps=build_dashboard.main) as builder:
            autopilot.main(["--workspace", self.ws, "week", "--date", "2026-11-03"])
        self.assertIn("--today", builder.call_args.args[0])
        self.assertEqual(builder.call_args.args[0][builder.call_args.args[0].index("--today") + 1], "2026-11-03")

    def test_applications_list_accepts_date_and_resolves_org_name(self):
        H.save(os.path.join(self.ws, "campaign", "applications.json"), {"applications": [
            {"id": "ap1", "org": "anthropic", "title": "Role", "stage": "applied", "last_step_on": "2026-11-01"}]})
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            applications.main(["--workspace", self.ws, "list", "--date", "2026-11-03"])
        self.assertIn("Anthropic", out.getvalue())

    def test_thank_you_draft_uses_thankyou_prefix(self):
        H.save(os.path.join(self.ws, "campaign", "applications.json"), {"applications": [
            {"id": "ap1", "org": "anthropic", "title": "Role", "stage": "interview", "last_step_on": "2026-11-01", "applied_on": "2026-10-01"}]})
        with mock.patch("sys.stdout", io.StringIO()):
            applications.main(["--workspace", self.ws, "draft", "ap1", "--date", "2026-11-03"])
        self.assertTrue(os.path.exists(os.path.join(self.ws, "campaign", "drafts", "thankyou-ap1-anthropic-2026-11-03.md")))

    def test_autopilot_and_door_status_accept_json(self):
        for call in (lambda: autopilot.main(["--workspace", self.ws, "status", "--json"]),
                     lambda: __import__("doors").main(["--workspace", self.ws, "status", "DR01", "going", "--json"])):
            with mock.patch("sys.stdout", io.StringIO()):
                self.assertEqual(call(), 0)

    def test_late_action_is_in_json_and_page_data(self):
        plan = H.load(os.path.join(self.ws, "campaign", "plan.json"))
        with mock.patch("sys.stdout", io.StringIO()):
            build_dashboard.main(["--workspace", self.ws, "--today", "2026-11-03"])
        before = H.load(os.path.join(self.ws, "report", "for-agents", "dashboard.json"))
        active_id = before["actions_active"][0]["id"]
        next(a for a in plan["actions"] if a["id"] == active_id)["target_date"] = "2026-10-30"
        H.save(os.path.join(self.ws, "campaign", "plan.json"), plan)
        with mock.patch("sys.stdout", io.StringIO()):
            build_dashboard.main(["--workspace", self.ws, "--today", "2026-11-03"])
        payload = H.load(os.path.join(self.ws, "report", "for-agents", "dashboard.json"))
        action = next(a for a in payload["actions_active"] if a["id"] == active_id)
        self.assertTrue(action["late"])
        with open(os.path.join(self.ws, "report", "index.html"), encoding="utf-8") as f:
            self.assertIn('a.late ? " · late"', f.read())

    def test_run_message_open_line_is_full_path(self):
        text = read("scripts/_autopilot.py")
        self.assertNotIn("open ~/", text)
        self.assertIn('os.path.join(ws, "report", "index.html")', text)

    def test_run_plan_shows_both_summaries(self):
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            run_plan.main(["--workspace", self.ws, "--top", "3"])
        self.assertIn("Full run:", out.getvalue())
        self.assertIn("Light run:", out.getvalue())


if __name__ == "__main__":
    unittest.main()
