"""scripts/checklist.py: extract, mark, confirm, status."""
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

import helpers as H
import checklist as CL
import score as S
import validate as V


def row(text, strength="must", kind="skill", inferred=False):
    return {"text": text, "strength": strength, "type": kind, "inferred": inferred, "applies": "everyone"}


def run(ws, *args):
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = CL.main(["--workspace", ws] + list(args))
    return code, out.getvalue(), err.getvalue()


def write_json(rows):
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"rows": rows}, fh)
    return path


class ChecklistCliTests(unittest.TestCase):
    def setUp(self):
        cfg = H.example_config()
        cfg["targets"] = [{"id": "acme", "name": "Acme", "ats": "manual"}]
        self.ws = H.new_workspace(self, cfg)
        self.rid = "acme:1"
        role = {
            "id": self.rid, "org": "acme", "title": "Nurse", "family": "tpm",
            "locations": ["Somewhere"], "location_classes": ["australia_nz"],
            "url": "https://example.com/1", "requires_heavy_coding": False, "eligibility_blockers": [],
            "description_text": "Ward nurse role.",
        }
        H.save(os.path.join(self.ws, "market", "roles", "latest.json"),
               {"schema_version": 1, "fetched_on": "2026-11-06", "summary": {"matched_total": 1}, "roles": [role]})
        H.save(os.path.join(self.ws, "eval", "judgements.json"),
               {"schema_version": 1, "roles": {self.rid: {
                   "D1": {"score": 3, "judged_on": "2026-11-06"},
                   "D2": {"score": 3, "judged_on": "2026-11-06"},
                   "D4": {"score": 3, "judged_on": "2026-11-06"},
               }}})
        H.save(os.path.join(self.ws, "eval", "profile-dimensions.json"), {"schema_version": 1})
        H.save(os.path.join(self.ws, "profile", "evidence.json"),
               {"schema_version": 1, "items": [{"id": "E01", "kind": "experience", "level": "corroborated",
                                                 "claim": "Two years on a ward"}]})
        H.save(os.path.join(self.ws, "eval", "gap-templates.json"), {"schema_version": 1, "gaps": []})

    def test_extract_merge_and_provisional(self):
        p1 = write_json([row("AHPRA registration", kind="licence"), row("Flu vaccination", kind="condition")])
        code, out, _ = run(self.ws, "extract", self.rid, "--read", p1)
        self.assertEqual(code, 0)
        self.assertIn("Provisional list", out)
        p2 = write_json([row("AHPRA registration", kind="licence"), row("Police check", kind="condition")])
        run(self.ws, "extract", self.rid, "--read", p2)
        p3 = write_json([row("AHPRA registration", kind="licence"), row("Flu vaccination", kind="condition")])
        code, out, _ = run(self.ws, "extract", self.rid, "--read", p3)
        doc = H.load(os.path.join(self.ws, "eval", "checklists.json"))
        texts = [r["text"] for r in doc["roles"][self.rid]["rows"]]
        self.assertEqual(texts, ["AHPRA registration", "Flu vaccination"])
        self.assertEqual(len(doc["roles"][self.rid]["reads"]), 3)
        self.assertNotIn("Provisional", out)

    def test_mark_three_passes_and_bad_verdict_refused(self):
        for path in (
            write_json([row("Cannulation"), row("Triage")]),
            write_json([row("Cannulation"), row("Triage")]),
        ):
            run(self.ws, "extract", self.rid, "--read", path)
        run(self.ws, "confirm", self.rid)
        mark = lambda verdict: write_json([{"row": "R1", "verdict": verdict, "evidence": ["E01"], "quote": "ward"}])
        for v in ("met", "met", "partly"):
            run(self.ws, "mark", self.rid, "--read", mark(v))
        doc = H.load(os.path.join(self.ws, "eval", "checklists.json"))
        self.assertEqual(doc["roles"][self.rid]["votes"]["R1"], ["met", "met", "partly"])
        before = json.dumps(doc, sort_keys=True)
        with self.assertRaises(SystemExit):
            run(self.ws, "mark", self.rid, "--read", mark("bogus"))
        after = H.load(os.path.join(self.ws, "eval", "checklists.json"))
        self.assertEqual(json.dumps(after, sort_keys=True), before)

    def test_confirm_rows_renumbers_and_drops_stale_votes(self):
        for path in (
            write_json([row("Cannulation"), row("Triage")]),
            write_json([row("Cannulation"), row("Triage")]),
        ):
            run(self.ws, "extract", self.rid, "--read", path)
        run(self.ws, "mark", self.rid, "--read",
            write_json([{"row": "R1", "verdict": "met", "evidence": ["E01"], "quote": "x"},
                        {"row": "R2", "verdict": "not_shown", "evidence": ["E01"], "quote": "y"}]))
        new_rows = write_json([row("Cannulation"), row("IV therapy")])
        _, out, _ = run(self.ws, "confirm", self.rid, "--rows", new_rows)
        doc = H.load(os.path.join(self.ws, "eval", "checklists.json"))
        self.assertEqual([r["id"] for r in doc["roles"][self.rid]["rows"]], ["R1", "R2"])
        self.assertEqual(doc["roles"][self.rid]["votes"].get("R2"), [])
        self.assertIn("still needing marks", out.lower())

    def test_status_validate_and_score(self):
        for path in (
            write_json([row("Cannulation")]),
            write_json([row("Cannulation")]),
        ):
            run(self.ws, "extract", self.rid, "--read", path)
        run(self.ws, "confirm", self.rid)
        run(self.ws, "mark", self.rid, "--read",
            write_json([{"row": "R1", "verdict": "met", "evidence": ["E01"], "quote": "ward"}]))
        _, out, _ = run(self.ws, "status")
        self.assertIn(self.rid, out)
        cl = H.load(os.path.join(self.ws, "eval", "checklists.json"))
        self.assertEqual(V.check(cl, H.schema("checklists.schema.json")), [])
        cfg = H.load(os.path.join(self.ws, "config.json"))
        built = S.build_run(self.ws, cfg, "2026-11-06")
        self.assertEqual(built["roles"][0]["checklist"]["verdict"], "strong match")


if __name__ == "__main__":
    unittest.main()
