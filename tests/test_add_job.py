"""Add one manual job posting from a saved page or pasted text (no live network)."""
import io
import json
import os
import unittest
from unittest import mock

import helpers as H
import add_job as AJ
import fetch_roles as F
import quick_posting as Q

FX = os.path.join(H.FIXTURES, "boards")
PAGE = "https://careers.hooli.example/jobs/123"
GH = "https://job-boards.greenhouse.io/acmeai/jobs/4200001"


def config_with_manual(name="Hooli Analytics", mid="hooli"):
    cfg = H.example_config()
    cfg["targets"] = list(cfg["targets"]) + [{"id": mid, "name": name, "ats": "manual", "aliases": ["Hooli"]}]
    cfg["families"] = list(cfg["families"]) + [{
        "id": "ops_lead", "name": "Operations lead", "title_keywords": ["operations lead"],
    }]
    return cfg


def long_program_posting(title="Program Manager, Field Operations"):
    lines = [title, "Employer: Example Health"]
    lines += ["- Lead cross-site program delivery for clinical systems"] * 30
    lines += ["Requirements", "5+ years program management", "Must hold Australian work rights"]
    return "\n".join(lines)


def write_posting(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


class AddJobTests(unittest.TestCase):
    def setUp(self):
        self.cfg = config_with_manual()
        self.ws = H.new_workspace(self, self.cfg)

    def run_add(self, *args):
        err = io.StringIO()
        with mock.patch("sys.stdout", io.StringIO()) as out:
            with mock.patch("sys.stderr", err):
                code = AJ.main(["--workspace", self.ws] + list(args))
        return code, out.getvalue(), err.getvalue()

    def manual(self):
        return H.load(os.path.join(self.ws, "market", "roles", "manual.json"))

    def test_saved_page_matches_manual_target_by_name(self):
        code, out, _ = self.run_add("--url", PAGE, "--saved", os.path.join(FX, "page-jsonld.html"))
        self.assertEqual(code, 0)
        doc = json.loads(out)
        self.assertEqual(doc["org"], "hooli")
        self.assertTrue(doc["role_id"].startswith("hooli:"))
        self.assertEqual(doc["title"], "Senior Operations Lead")
        self.assertEqual(doc["requires_heavy_coding"], False)
        manual = self.manual()
        self.assertEqual(len(manual["postings"]), 1)
        self.assertEqual(manual["postings"][0]["org"], "hooli")
        self.assertIn("Brisbane", manual["postings"][0]["locations"][0])
        self.assertIn("<h3>Requirements</h3>", manual["postings"][0]["description"])

    def test_saved_description_matches_fetch_roles_scoring(self):
        code, out, _ = self.run_add("--url", PAGE, "--saved", os.path.join(FX, "page-jsonld.html"))
        self.assertEqual(code, 0)
        add_doc = json.loads(out)
        with mock.patch("sys.stdout"):
            self.assertEqual(F.main(["--workspace", self.ws, "--date", "2026-11-06"]), 0)
        latest = H.load(os.path.join(self.ws, "market", "roles", "latest.json"))
        role = next(r for r in latest["roles"] if r["id"] == add_doc["role_id"])
        self.assertEqual(role["requires_heavy_coding"], add_doc["requires_heavy_coding"])
        self.assertEqual(role.get("coding_signals") or [], add_doc.get("coding_signals") or [])

    def test_greenhouse_saved_response_uses_manual_org_and_blockers(self):
        self.cfg["targets"].append({"id": "acme_manual", "name": "Acme AI", "ats": "manual"})
        H.save(os.path.join(self.ws, "config.json"), self.cfg)
        code, out, _ = self.run_add("--url", GH, "--org", "acme_manual", "--saved",
                                     os.path.join(FX, "greenhouse-job.json"))
        doc = json.loads(out)
        self.assertEqual(doc["org"], "acme_manual")
        self.assertEqual([b["type"] for b in doc["eligibility_blockers"]], ["citizenship"])
        self.assertIn("compensation", self.manual()["postings"][0])

    def test_text_file_needs_org_when_employer_unknown(self):
        path = os.path.join(self.ws, "posting.txt")
        write_posting(path, long_program_posting())
        with self.assertRaises(SystemExit) as cm:
            AJ.main(["--workspace", self.ws, "--text-file", path])
        self.assertIn("--org", str(cm.exception))

    def test_text_file_resolves_employer_from_paste(self):
        self.cfg["targets"].append({"id": "seek", "name": "Example Health", "ats": "manual"})
        H.save(os.path.join(self.ws, "config.json"), self.cfg)
        path = os.path.join(self.ws, "posting.txt")
        write_posting(path, long_program_posting())
        code, out, _ = self.run_add("--text-file", path)
        self.assertEqual(code, 0)
        doc = json.loads(out)
        self.assertEqual(doc["org"], "seek")

    def test_text_file_with_org_is_in_manual_json(self):
        self.cfg["targets"].append({"id": "seek", "name": "Example Health", "ats": "manual"})
        H.save(os.path.join(self.ws, "config.json"), self.cfg)
        path = os.path.join(self.ws, "posting.txt")
        write_posting(path, long_program_posting())
        code, out, _ = self.run_add("--text-file", path, "--org", "seek")
        self.assertEqual(code, 0)
        doc = json.loads(out)
        self.assertEqual(doc["org"], "seek")
        self.assertIn("<h3>Requirements</h3>", doc["manual_posting"]["description"])
        self.assertIn("program management", doc["manual_posting"]["description"].lower())

    def test_unmatched_family_still_saves_manual_json(self):
        path = os.path.join(self.ws, "posting.txt")
        write_posting(path, long_program_posting("Staff Zookeeper"))
        code, out, err = self.run_add("--text-file", path, "--org", "hooli")
        self.assertEqual(code, 0)
        doc = json.loads(out)
        self.assertFalse(doc.get("kept_for_scoring", True))
        self.assertIn("exclusion_reason", doc)
        self.assertEqual(len(self.manual()["postings"]), 1)

    def test_short_paste_returns_exit_three(self):
        path = os.path.join(self.ws, "short.txt")
        write_posting(path, "One line title\nToo short.")
        code, _, err = self.run_add("--text-file", path, "--org", "hooli")
        self.assertEqual(code, 3)
        self.assertIn("Paste the posting text", err)
        self.assertEqual(self.manual()["postings"], [])

    def test_fetch_roles_picks_up_added_posting(self):
        cfg = config_with_manual()
        cfg["targets"] = [t for t in cfg["targets"] if t["id"] == "hooli"]
        ws = H.new_workspace(self, cfg)
        err = io.StringIO()
        with mock.patch("sys.stdout", io.StringIO()) as out:
            with mock.patch("sys.stderr", err):
                self.assertEqual(AJ.main(["--workspace", ws, "--url", PAGE, "--org", "hooli",
                                          "--saved", os.path.join(FX, "page-jsonld.html")]), 0)
        add_doc = json.loads(out.getvalue())
        with mock.patch("sys.stdout"):
            self.assertEqual(F.main(["--workspace", ws, "--date", "2026-11-06"]), 0)
        latest = H.load(os.path.join(ws, "market", "roles", "latest.json"))
        role = next(r for r in latest["roles"] if r["id"] == add_doc["role_id"])
        self.assertEqual(role["requires_heavy_coding"], add_doc["requires_heavy_coding"])

    def test_non_manual_target_refused(self):
        with self.assertRaises(SystemExit) as cm:
            AJ.main(["--workspace", self.ws, "--url", GH, "--org", "anthropic",
                     "--saved", os.path.join(FX, "greenhouse-job.json")])
        self.assertIn("not manual", str(cm.exception))


class FetchBaseTests(unittest.TestCase):
    def test_fetch_base_matches_fetch_role(self):
        base, source, link = Q.fetch_base(GH, saved=os.path.join(FX, "greenhouse-job.json"))
        role, _ = Q.fetch(GH, saved=os.path.join(FX, "greenhouse-job.json"))
        self.assertEqual(base["title"], role["title"])
        self.assertEqual(source["kind"], "greenhouse")
        self.assertEqual(link["ats"], "greenhouse")


if __name__ == "__main__":
    unittest.main()
