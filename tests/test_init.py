"""init.py: creates a private workspace from templates/, and refuses unsafe places."""
import os
import shutil
import stat
import tempfile
import unittest
from unittest import mock

import helpers as H
import _common as C
import init as I
import validate as V


class InitTests(unittest.TestCase):
    def tmp(self):
        d = tempfile.mkdtemp(prefix="climb-init-")
        self.addCleanup(shutil.rmtree, d, True)
        return d

    def run_init(self, args):
        with mock.patch("sys.stdout") as out:
            code = I.main(args)
        return code, "".join(c.args[0] for c in out.write.call_args_list)

    def test_creates_valid_private_workspace(self):
        ws = os.path.join(self.tmp(), "climate")
        code, printed = self.run_init(["--goal", "Climate tech product roles!", "--workspace", ws])
        self.assertEqual(code, 0)
        cfg = H.load(os.path.join(ws, "config.json"))
        self.assertEqual(cfg["goal"]["slug"], "climate-tech-product-roles")
        self.assertEqual(cfg["goal"]["title"], "Climate tech product roles!")
        self.assertEqual(cfg["goal"]["description"], "Climate tech product roles!")
        self.assertEqual((cfg["targets"], cfg["families"], cfg["exclude_title_keywords"]), ([], [], []))
        steps = [line for line in printed.splitlines() if line.startswith("Next step")]
        self.assertEqual(len(steps), 1)
        self.assertIn('say to your agent "run the Climb interview"', steps[0])
        self.assertIn(ws, steps[0])                    # outside ~/climb-workspaces, so it names the folder
        self.assertNotIn("Next steps", printed)
        for rel in ("intake/answers.md", "profile/evidence.json", "eval/judgements.json", "campaign/plan.json",
                    "campaign/inbox.md", "market/roles/snapshots", "report/for-agents"):
            self.assertTrue(os.path.exists(os.path.join(ws, rel)), rel)
        self.assertFalse(os.path.exists(os.path.join(ws, "eval", "runs", ".gitkeep")))
        self.assertEqual(stat.S_IMODE(os.stat(ws).st_mode), 0o700)
        errors, _, _ = V.validate_workspace(ws)
        self.assertEqual(errors, [C.NO_TARGETS])

    def test_example_config(self):
        ws = os.path.join(self.tmp(), "labs")
        code, printed = self.run_init(["--goal", "Frontier AI labs", "--workspace", ws, "--example", "frontier-ai-labs"])
        self.assertEqual(code, 0)
        cfg = H.load(os.path.join(ws, "config.json"))
        self.assertEqual([t["id"] for t in cfg["targets"]], ["anthropic", "openai", "xai"])
        self.assertEqual(cfg["goal"]["description"], "Frontier AI labs")
        self.assertEqual(V.validate_workspace(ws)[0], [])

    def test_next_step_is_just_the_interview_in_the_default_place(self):
        parent = self.tmp()
        with mock.patch.object(C, "DEFAULT_PARENT", parent), mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLIMB_HOME", None)
            code, printed = self.run_init(["--goal", "Climate tech"])
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(os.path.join(parent, "climate-tech", "config.json")))
        self.assertEqual(printed.splitlines()[-1], 'Next step: say to your agent "run the Climb interview".')

    def test_env_default_and_refusals(self):
        parent = self.tmp()
        target = os.path.join(parent, "from-env")
        with mock.patch.dict(os.environ, {"CLIMB_HOME": target}), mock.patch("sys.stdout"):
            self.assertEqual(I.main(["--goal", "AI labs"]), 0)
        self.assertTrue(os.path.exists(os.path.join(target, "config.json")))
        with mock.patch("sys.stderr"):
            self.assertEqual(I.main(["--goal", "AI labs", "--workspace", target]), 1)  # not empty
            inside = os.path.join(H.ENGINE, ".init-guard-test")
            self.addCleanup(shutil.rmtree, inside, True)
            self.assertEqual(I.main(["--goal", "AI labs", "--workspace", inside]), 2)
        self.assertFalse(os.path.exists(inside))

    def test_slugify(self):
        self.assertEqual(I.slugify("Frontier AI labs"), "frontier-ai-labs")
        self.assertEqual(I.slugify("!!!"), "my-goal")


if __name__ == "__main__":
    unittest.main()
