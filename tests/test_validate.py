"""validate.py: the mini JSON Schema validator, cross-file checks and the workspace location guard."""
import os
import shutil
import tempfile
import unittest
from unittest import mock

import helpers as H
import _common as C
import validate as V


class CheckTests(unittest.TestCase):
    SCHEMA = {
        "type": "object", "required": ["a"], "additionalProperties": False,
        "properties": {
            "a": {"type": "integer", "minimum": 0, "maximum": 5},
            "b": {"enum": [True, "x"]},
            "c": {"type": "string", "pattern": "^E[0-9]+$", "minLength": 1},
            "d": {"type": "array", "items": {"$ref": "#/definitions/item"}, "minItems": 1},
            "e": {"anyOf": [{"const": "all"}, {"type": "array", "items": {"type": "string"}}]},
            "f": {"type": ["string", "null"]},
            "g": {"type": "number", "exclusiveMinimum": 0},
        },
        "definitions": {"item": {"type": "object", "required": ["id"], "properties": {"id": {"type": "string"}}}},
    }

    def test_valid(self):
        doc = {"a": 3, "b": True, "c": "E01", "d": [{"id": "x"}], "e": "all", "f": None, "g": 0.5}
        self.assertEqual(V.check(doc, self.SCHEMA), [])
        self.assertEqual(V.check({"a": 0, "e": ["x", "y"]}, self.SCHEMA), [])

    def test_errors(self):
        errs = V.check({"b": 1, "c": "X1", "d": [], "e": "some", "f": 3, "g": 0, "zz": 1}, self.SCHEMA)
        text = "\n".join(errs)
        for expected in ("missing required field 'a'", "$.b: 1 is not one of", "does not match the pattern",
                         "needs at least 1 items", "$.e: \"some\" does not match any", "$.f: expected string or null",
                         "must be more than 0", "unexpected field 'zz'"):
            self.assertIn(expected, text)
        self.assertIn("expected integer", "\n".join(V.check({"a": True}, self.SCHEMA)))  # booleans are not integers
        self.assertIn("above the maximum", "\n".join(V.check({"a": 6}, self.SCHEMA)))
        self.assertIn("$.d[0]: missing required field 'id'", "\n".join(V.check({"a": 1, "d": [{}]}, self.SCHEMA)))

    def test_pattern_properties(self):
        schema = {"type": "object", "additionalProperties": False, "properties": {"a": {"type": "integer"}},
                  "patternProperties": {"^x_": {}, "^n_": {"type": "number"}}}
        self.assertEqual(V.check({"a": 1, "x_anything": {"deep": [1, None]}, "n_ok": 2.5}, schema), [])
        text = "\n".join(V.check({"a": 1, "y_no": 1, "n_bad": "two", "X_case": 1}, schema))
        self.assertIn("unexpected field 'y_no'", text)
        self.assertIn("$.n_bad: expected number", text)
        self.assertIn("unexpected field 'X_case'", text)      # the prefix is lower case x_

    def test_all_schemas_load_and_templates_validate(self):
        names = sorted(os.listdir(os.path.join(H.ENGINE, "schemas")))
        self.assertGreaterEqual(len(names), 10)
        ws = H.new_workspace(self)
        errors, warnings, checked = V.validate_workspace(ws)
        self.assertEqual(errors, [C.NO_TARGETS])      # a new workspace waits for the interview
        self.assertIn("config.json", checked)
        ws = H.new_workspace(self, H.example_config())
        self.assertEqual(V.validate_workspace(ws)[0], [])


class WorkspaceTests(unittest.TestCase):
    def test_missing_location_rule_warns_with_class_name(self):
        ws = H.copy_demo(self)
        profile_path = os.path.join(ws, "eval", "profile-dimensions.json")
        profile = H.load(profile_path)
        classes = profile["D6_rules"]["classes"]
        removed = next(iter(classes))
        del classes[removed]
        H.save(profile_path, profile)
        _, warnings, _ = V.validate_workspace(ws)
        self.assertTrue(any("no D6 rule for location class '%s'" % removed in w for w in warnings))

    def test_one_point_reviewer_decision_validates_without_tie_break(self):
        ws = H.copy_demo(self)
        path = os.path.join(ws, "eval", "reviews", "2026-10-26.json")
        doc = H.load(path)
        dispute = doc["disputes"][0]
        dispute["reviewer"]["score"] = dispute["scorer"]["score"] - 1
        dispute["tie_break"] = {"absent": True, "why": "The reviewer differs by one point."}
        dispute["stands"] = dispute["reviewer"]["score"]
        dispute["decided_by"] = "reviewer_one_point"
        H.save(path, doc)
        jud = H.load(os.path.join(ws, "eval", "judgements.json"))
        rid, dim = dispute["item_id"].rsplit("/", 1)
        jud["roles"][rid][dim]["score"] = dispute["stands"]
        jud["roles"][rid]["reviewed_on"] = "2026-10-26"
        H.save(os.path.join(ws, "eval", "judgements.json"), jud)
        errors, _, _ = V.validate_workspace(ws)
        self.assertEqual(errors, [])

    def test_demo_in_place_is_valid(self):
        errors, _, checked = V.validate_workspace(H.DEMO)
        self.assertEqual(errors, [])
        self.assertIn("eval/swot.json", checked)
        self.assertIn("eval/reviews/2026-10-26.json", checked)     # the dispute log, middle of three
        self.assertIsNone(C.location_problem(H.DEMO))
        levels = {e["level"] for e in H.load(os.path.join(H.DEMO, "profile", "evidence.json"))["items"]}
        self.assertIn("partially_verified", levels)
        statuses = {a["status"] for a in H.load(os.path.join(H.DEMO, "campaign", "plan.json"))["actions"]}
        self.assertIn("later", statuses)

    def test_cross_file_errors(self):
        ws = H.copy_demo(self)
        plan = H.load(os.path.join(ws, "campaign", "plan.json"))
        plan["actions"][0]["done_evidence"] = ""                       # A01 is done
        plan["max_active"] = 2
        plan["actions"][1]["strategy_ids"] = ["SO9"]
        H.save(os.path.join(ws, "campaign", "plan.json"), plan)
        swot = H.load(os.path.join(ws, "eval", "swot.json"))
        swot["strategies"][0]["uses"] = ["S1", "T1"]                   # SO1 must use an S and an O
        swot["overall"]["strengths"][0]["evidence"] = ["E99"]
        H.save(os.path.join(ws, "eval", "swot.json"), swot)
        errors, _, _ = V.validate_workspace(ws)
        text = "\n".join(errors)
        self.assertIn("A01 is done but has no done_evidence", text)
        self.assertNotIn("more than the cap", text)                     # over the cap is a warning (method/CAMPAIGN.md)
        self.assertIn("names strategy SO9", text)
        self.assertIn("strategy SO1 is SO", text)
        self.assertIn("cites evidence E99", text)

    def test_active_cap_warns_and_later_is_off_the_cap(self):
        ws = H.copy_demo(self)
        plan = H.load(os.path.join(ws, "campaign", "plan.json"))
        active = [a for a in plan["actions"] if a["status"] in ("todo", "doing")]
        plan["max_active"] = len(active) - 1
        H.save(os.path.join(ws, "campaign", "plan.json"), plan)
        errors, warnings, _ = V.validate_workspace(ws)
        self.assertEqual(errors, [])
        self.assertTrue(any("more than the cap of %d" % (len(active) - 1) in w and "later" in w for w in warnings))
        next(a for a in plan["actions"] if a["status"] == "todo")["status"] = "later"   # park one
        H.save(os.path.join(ws, "campaign", "plan.json"), plan)
        errors, warnings, _ = V.validate_workspace(ws)
        self.assertEqual(errors, [])
        self.assertFalse(any("more than the cap" in w for w in warnings))
        plan["actions"][1]["status"] = "parked"
        H.save(os.path.join(ws, "campaign", "plan.json"), plan)
        self.assertTrue(any("is not one of" in x for x in V.validate_workspace(ws)[0]))

    def test_extension_fields_are_kept_and_validated(self):
        ws = H.copy_demo(self)
        edits = {
            "config.json": lambda d: (d.update(x_owner_note="mine"), d["candidate"].update(x_pronounce="AL-ex"),
                                      d["targets"][0].update(x_crm_id=42), d["families"][0].update(x_old_regex="re:x")),
            "profile/evidence.json": lambda d: (d.update(x_migrated_from="old tool"),
                                                d["items"][0].update(x_original_id="G01", x_detail={"a": [1]}),
                                                d["items"][0]["sources"][0].update(x_page=3),
                                                d["open_questions"][0].update(x_label="Notice")),
            "eval/judgements.json": lambda d: (d.update(x_batch="b1"), next(iter(d["roles"].values())).update(x_itar=False),
                                               next(iter(d["roles"].values()))["D1"].update(x_reason="kept")),
            "eval/profile-dimensions.json": lambda d: (d.update(x_file_note="n"), d["D3"]["acme"].update(x_why="w"),
                                                       d["D6_rules"].setdefault("blocked", {}).update(x_score=0)),
            "campaign/plan.json": lambda d: (d.update(x_mandate="m", x_story="s"), d["actions"][0].update(x_old_rank=3),
                                             d["north_star"][0].update(x_label="l")),
        }
        for rel, fn in edits.items():
            doc = H.load(os.path.join(ws, rel))
            fn(doc)
            H.save(os.path.join(ws, rel), doc)
        run_rel = os.path.join("eval", "runs", "2026-11-01.json")
        run = H.load(os.path.join(ws, run_rel))
        run["x_legacy_per_lab"] = {"acme": None}
        run["roles"][0]["x_note"] = "from the old run"
        H.save(os.path.join(ws, run_rel), run)
        errors, _, _ = V.validate_workspace(ws)
        self.assertEqual(errors, [])
        # an unknown field without the prefix is still an error, and so is x_ where the schema does not allow it
        doc = H.load(os.path.join(ws, "campaign", "plan.json"))
        doc["actions"][0]["mandate"] = "m"
        doc["actions"][0]["effects"] = [{"dimension": "D3", "delta": 1, "x_ok": True}]
        H.save(os.path.join(ws, "campaign", "plan.json"), doc)
        roles = H.load(os.path.join(ws, "market", "roles", "latest.json"))
        roles["x_not_here"] = 1
        H.save(os.path.join(ws, "market", "roles", "latest.json"), roles)
        text = "\n".join(V.validate_workspace(ws)[0])
        self.assertIn("unexpected field 'mandate'", text)
        self.assertNotIn("x_ok", text)
        self.assertIn("unexpected field 'x_not_here'", text)

    def test_no_targets_or_families_is_one_plain_error(self):
        cfg = H.template_config()
        cfg["targets"], cfg["families"] = [], []
        ws = H.new_workspace(self, cfg)
        self.assertEqual(V.validate_workspace(ws)[0], [C.NO_TARGETS])
        self.assertEqual(C.NO_TARGETS, "No target organisations yet. Say to your agent: run the LVLme interview.")
        cfg["targets"] = [{"id": "acme", "name": "Acme AI", "ats": "manual"}]
        H.save(os.path.join(ws, "config.json"), cfg)
        self.assertEqual(V.validate_workspace(ws)[0], [C.NO_FAMILIES])
        with mock.patch("sys.stdout"):
            self.assertEqual(V.main(["--workspace", ws]), 1)

    def test_ai_policy_field(self):
        cfg = H.example_config()
        policy = cfg["targets"][0]["ai_policy"]
        self.assertEqual(policy, {"first_draft_by_person": True, "checked_on": "2026-11-02",
                                  "source": "https://www.anthropic.com/candidate-ai-guidance"})
        self.assertEqual([t["id"] for t in cfg["targets"] if "ai_policy" in t], ["anthropic"])  # none invented
        schema = H.schema("config.schema.json")
        self.assertEqual(V.check(cfg, schema), [])
        for bad, expected in (({"first_draft_by_person": True}, "missing required field 'source'"),
                              ({"first_draft_by_person": "yes", "source": "https://example.com/ai"}, "expected boolean"),
                              ({"first_draft_by_person": True, "source": "their careers page"}, "does not match"),
                              ({"first_draft_by_person": True, "source": "https://example.com", "strict": 1},
                               "unexpected field 'strict'")):
            cfg["targets"][0]["ai_policy"] = bad
            self.assertIn(expected, "\n".join(V.check(cfg, schema)))

    def test_main_exit_codes(self):
        with mock.patch("sys.stdout"):
            self.assertEqual(V.main(["--workspace", H.DEMO, "--json"]), 0)
        ws = H.copy_demo(self)
        os.remove(os.path.join(ws, "campaign", "plan.json"))
        with mock.patch("sys.stdout"):
            self.assertEqual(V.main(["--workspace", ws]), 1)


class LocationGuardTests(unittest.TestCase):
    def tmp(self):
        d = tempfile.mkdtemp(prefix="lvlme-guard-")
        self.addCleanup(shutil.rmtree, d, True)
        return d

    def test_inside_engine_repo_is_refused(self):
        inside = tempfile.mkdtemp(prefix=".guard-test-", dir=H.ENGINE)
        self.addCleanup(shutil.rmtree, inside, True)
        self.assertIn("inside the LVLme engine", C.location_problem(inside, {}))
        # "fictional" only helps under examples/
        self.assertIsNotNone(C.location_problem(inside, {"fictional": True}))
        shutil.copy(os.path.join(H.ENGINE, "templates", "config.json"), os.path.join(inside, "config.json"))
        with mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            self.assertEqual(V.main(["--workspace", inside]), 2)

    def test_git_repo_with_remote_is_refused(self):
        repo = self.tmp()
        os.makedirs(os.path.join(repo, ".git"))
        ws = os.path.join(repo, "private", "ws")
        os.makedirs(ws)
        with open(os.path.join(repo, ".git", "config"), "w") as fh:
            fh.write("[core]\n\tbare = false\n")
        self.assertIsNone(C.location_problem(ws, {}))  # a local repo without a remote is fine
        with open(os.path.join(repo, ".git", "config"), "a") as fh:
            fh.write('[remote "origin"]\n\turl = https://example.com/repo.git\n')
        self.assertIn("has a remote (origin)", C.location_problem(ws, {}))

    def test_worktree_git_file_is_followed(self):
        main_repo, wt = self.tmp(), self.tmp()
        gitdir = os.path.join(main_repo, ".git", "worktrees", "wt")
        os.makedirs(gitdir)
        with open(os.path.join(gitdir, "commondir"), "w") as fh:
            fh.write("../..")
        with open(os.path.join(main_repo, ".git", "config"), "w") as fh:
            fh.write('[remote "upstream"]\n\turl = https://example.com/x.git\n')
        with open(os.path.join(wt, ".git"), "w") as fh:
            fh.write("gitdir: %s\n" % gitdir)
        self.assertIn("upstream", C.location_problem(wt, {}))


if __name__ == "__main__":
    unittest.main()
