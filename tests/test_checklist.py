"""The checklist method sits beside today's fit and does not change it."""
import os
import unittest

import helpers as H
import _checklist as C
import build_dashboard as BD
import score as S
import validate as V


def row(rid, text, strength="must", kind="skill", inferred=False):
    return {"id": rid, "text": text, "strength": strength, "type": kind, "inferred": inferred, "applies": "everyone"}


class MergeTests(unittest.TestCase):
    def test_a_requirement_kept_only_when_two_reads_agree(self):
        kept = C.merge_extracts([
            [{"text": "AHPRA registration", "strength": "must", "type": "licence"},
             {"text": "Flu vaccination", "strength": "must", "type": "condition"}],
            [{"text": "AHPRA registration", "strength": "must", "type": "licence"},
             {"text": "Police check", "strength": "must", "type": "condition"}],
            [{"text": "AHPRA registration", "strength": "must", "type": "licence"},
             {"text": "Flu vaccination", "strength": "must", "type": "condition"}],
        ])
        texts = [r["text"] for r in kept]
        self.assertEqual(texts, ["AHPRA registration", "Flu vaccination"])
        self.assertEqual([r["id"] for r in kept], ["R1", "R2"])

    def test_one_corrected_read_is_kept_whole(self):
        kept = C.merge_extracts([[{"text": "A degree in nursing", "strength": "must", "type": "credential"}]])
        self.assertEqual(kept[0]["text"], "A degree in nursing")


class ScoreTests(unittest.TestCase):
    def test_a_check_anyone_can_get_is_a_todo_not_a_fail(self):
        rows = [row("R1", "Two years on a ward", "must", "experience"),
                row("R2", "Flu vaccination", "must", "condition")]
        got = C.score_checklist(rows, {"R1": ["met"], "R2": ["not_shown"]})
        self.assertEqual(got["shown"]["verdict"], "strong match")
        self.assertEqual(got["compare"]["points"], 100.0)
        self.assertEqual(got["shown"]["todos"], ["Flu vaccination"])

    def test_a_licence_fails_only_on_a_majority(self):
        rows = [row("R1", "AHPRA registration", "must", "licence"),
                row("R2", "Two years on a ward", "must", "experience")]
        fail = C.score_checklist(rows, {"R1": ["not_shown", "not_shown", "met"], "R2": ["met"]})
        self.assertEqual(fail["shown"]["verdict"], "not yet")
        self.assertEqual(fail["compare"]["points"], 0.0)
        split = C.score_checklist(rows, {"R1": ["not_shown", "met", "unknown"], "R2": ["met"]})
        self.assertNotEqual(split["shown"]["verdict"], "not yet")
        self.assertTrue(any("Split vote" in q for q in split["shown"]["questions"]))

    def test_a_soft_skill_counts_at_half_weight(self):
        skill = C.score_checklist(
            [row("R1", "Cannulation", "must", "skill"), row("R2", "A second skill", "must", "skill")],
            {"R1": ["met"], "R2": ["not_shown"]})
        soft = C.score_checklist(
            [row("R1", "Cannulation", "must", "skill"), row("R2", "Good communication", "must", "soft_skill")],
            {"R1": ["met"], "R2": ["not_shown"]})
        self.assertEqual(skill["compare"]["points"], 50.0)
        self.assertEqual(soft["compare"]["points"], 66.7)

    def test_unknown_widens_the_range_and_is_not_a_zero(self):
        rows = [row("R1", "Cannulation", "must", "skill"), row("R2", "Triage", "must", "skill")]
        got = C.score_checklist(rows, {"R1": ["met"], "R2": ["unknown"]})
        self.assertEqual(got["compare"]["points"], 100.0)
        self.assertEqual(got["compare"]["points_low"], 50.0)
        self.assertEqual(got["compare"]["points_high"], 100.0)
        self.assertTrue(any("unknowns could move" in q for q in got["shown"]["questions"]))

    def test_must_line_and_three_moves(self):
        rows = [row("R1", "One", "must"), row("R2", "Two", "must"), row("R3", "Three", "must"),
                row("R4", "Four", "should")]
        got = C.score_checklist(rows, {"R1": ["met"], "R2": ["partly"], "R3": ["not_shown"], "R4": ["not_shown"]})
        self.assertEqual(got["shown"]["must_line"], "1 of 3 must-haves met")
        self.assertEqual(got["shown"]["moves"], ["Add evidence for: Three", "Add evidence for: Two", "Add evidence for: Four"])

    def test_a_thin_posting_is_named(self):
        rows = [row("R1", "Work rights", "must", "eligibility"), row("R2", "A related degree", "should", "credential")]
        got = C.score_checklist(rows, {"R1": ["met"], "R2": ["met"]})
        self.assertTrue(got["shown"]["thin_posting"])
        self.assertEqual(got["shown"]["notice"], C.THIN_NOTICE)

    def test_a_rule_for_someone_else_is_skipped(self):
        rows = [row("R1", "Cannulation", "must", "skill"),
                {"id": "R2", "text": "If you hold another visa, name it", "strength": "must", "type": "eligibility",
                 "inferred": False, "applies": "only applicants on a temporary visa"}]
        got = C.score_checklist(rows, {"R1": ["met"], "R2": ["not_applicable"]})
        self.assertEqual(got["shown"]["verdict"], "strong match")
        self.assertEqual(got["shown"]["must_line"], "1 of 1 must-haves met")

    def test_the_shown_result_has_no_chance_percentage(self):
        got = C.score_checklist([row("R1", "Cannulation")], {"R1": ["met"]})
        text = str(got["shown"]).lower()
        self.assertNotIn("chance", text)
        self.assertNotIn("%", text)

    def test_beside_keeps_todays_fit(self):
        result = C.score_checklist([row("R1", "Cannulation")], {"R1": ["met"]})
        both = C.beside(41.0, result)
        self.assertEqual(both["today_fit"], 41.0)
        self.assertEqual(both["compare"]["today_fit"], 41.0)
        self.assertEqual(result["compare"].get("today_fit"), None)
        self.assertEqual(both["shown"]["verdict"], "strong match")


class BesideRunTests(unittest.TestCase):
    def test_a_saved_list_is_scored_beside_fit_and_shown_on_the_role(self):
        cfg = H.example_config()
        cfg["targets"] = [{"id": "acme", "name": "Acme", "ats": "manual"}]
        ws = H.new_workspace(self, cfg)
        role = {"id": "acme:1", "org": "acme", "title": "Nurse", "family": "tpm",
                "locations": ["Somewhere"], "location_classes": ["australia_nz"],
                "url": "https://example.com/1", "requires_heavy_coding": False, "eligibility_blockers": []}
        H.save(os.path.join(ws, "market", "roles", "latest.json"),
               {"schema_version": 1, "fetched_on": "2026-11-06", "summary": {"matched_total": 1}, "roles": [role]})
        H.save(os.path.join(ws, "eval", "judgements.json"), {"schema_version": 1, "roles": {}})
        H.save(os.path.join(ws, "eval", "profile-dimensions.json"), {"schema_version": 1})
        H.save(os.path.join(ws, "profile", "evidence.json"), {"schema_version": 1, "items": []})
        H.save(os.path.join(ws, "eval", "gap-templates.json"), {"schema_version": 1, "gaps": []})
        before = S.build_run(ws, cfg, "2026-11-06")
        fit = before["roles"][0]["fit"]
        self.assertNotIn("checklist", before["roles"][0])
        H.save(os.path.join(ws, "eval", "checklists.json"), {"schema_version": 1, "roles": {"acme:1": {
            "corrected": False,
            "rows": [row("R1", "Cannulation", "must", "skill")],
            "votes": {"R1": ["met"]},
        }}})
        after = S.build_run(ws, cfg, "2026-11-06")
        got = after["roles"][0]
        self.assertEqual(got["fit"], fit)
        self.assertEqual(got["checklist"]["today_fit"], fit)
        self.assertEqual(got["checklist"]["verdict"], "strong match")
        self.assertEqual(got["checklist"]["must_line"], "1 of 1 must-haves met")
        self.assertIn("Is this what the job asks for?", got["checklist"]["questions"])
        self.assertNotEqual(after["inputs_digest"], before["inputs_digest"])
        self.assertEqual(V.check(after, H.schema("run.schema.json")), [])
        view = BD._checklist_view(got["checklist"])
        self.assertEqual(view["ck"]["verdict"], "strong match")
        self.assertEqual(view["ck"]["rows"], ["Cannulation"])
        assets = open(os.path.join(os.path.dirname(BD.__file__), "_dashboard_assets.py"), encoding="utf-8").read()
        self.assertIn("Checklist", assets)
        self.assertIn("Today's fit is unchanged.", assets)


if __name__ == "__main__":
    unittest.main()
