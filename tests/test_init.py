"""init.py: creates a private workspace from templates/, and refuses unsafe places."""
import os
import shutil
import stat
import tempfile
import unittest
from unittest import mock

import helpers as H
import init as I
import validate as V


class InitTests(unittest.TestCase):
    def tmp(self):
        d = tempfile.mkdtemp(prefix="climb-init-")
        self.addCleanup(shutil.rmtree, d, True)
        return d

    def test_creates_valid_private_workspace(self):
        ws = os.path.join(self.tmp(), "climate")
        with mock.patch("sys.stdout"):
            self.assertEqual(I.main(["--goal", "Climate tech product roles!", "--workspace", ws]), 0)
        cfg = H.load(os.path.join(ws, "config.json"))
        self.assertEqual(cfg["goal"]["slug"], "climate-tech-product-roles")
        self.assertEqual(cfg["goal"]["title"], "Climate tech product roles!")
        for rel in ("intake/answers.md", "profile/evidence.json", "eval/judgements.json", "campaign/plan.json",
                    "campaign/inbox.md", "market/roles/snapshots", "report/for-agents"):
            self.assertTrue(os.path.exists(os.path.join(ws, rel)), rel)
        self.assertFalse(os.path.exists(os.path.join(ws, "eval", "runs", ".gitkeep")))
        self.assertEqual(stat.S_IMODE(os.stat(ws).st_mode), 0o700)
        errors, _, _ = V.validate_workspace(ws)
        self.assertEqual(errors, [])

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
