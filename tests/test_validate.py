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

    def test_all_schemas_load_and_templates_validate(self):
        names = sorted(os.listdir(os.path.join(H.ENGINE, "schemas")))
        self.assertGreaterEqual(len(names), 10)
        ws = H.new_workspace(self)
        errors, warnings, checked = V.validate_workspace(ws)
        self.assertEqual(errors, [])
        self.assertIn("config.json", checked)


class WorkspaceTests(unittest.TestCase):
    def test_demo_in_place_is_valid(self):
        errors, _, checked = V.validate_workspace(H.DEMO)
        self.assertEqual(errors, [])
        self.assertIn("eval/swot.json", checked)
        self.assertIsNone(C.location_problem(H.DEMO))

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
        self.assertIn("more than the cap of 2", text)
        self.assertIn("names strategy SO9", text)
        self.assertIn("strategy SO1 is SO", text)
        self.assertIn("cites evidence E99", text)

    def test_main_exit_codes(self):
        with mock.patch("sys.stdout"):
            self.assertEqual(V.main(["--workspace", H.DEMO, "--json"]), 0)
        ws = H.copy_demo(self)
        os.remove(os.path.join(ws, "campaign", "plan.json"))
        with mock.patch("sys.stdout"):
            self.assertEqual(V.main(["--workspace", ws]), 1)


class LocationGuardTests(unittest.TestCase):
    def tmp(self):
        d = tempfile.mkdtemp(prefix="career-eval-guard-")
        self.addCleanup(shutil.rmtree, d, True)
        return d

    def test_inside_engine_repo_is_refused(self):
        inside = tempfile.mkdtemp(prefix=".guard-test-", dir=H.ENGINE)
        self.addCleanup(shutil.rmtree, inside, True)
        self.assertIn("inside the career-eval engine", C.location_problem(inside, {}))
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
