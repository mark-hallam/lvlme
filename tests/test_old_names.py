"""LVLme was called Climb until 3 November 2026: the old names keep working.

Pins each fallback: $CLIMB_HOME when $LVLME_HOME is not set, ~/climb-workspaces
when ~/lvlme-workspaces does not exist (said once),
the dashboard's saved browser settings, and workspaces written under the old
name. Every test uses temporary folders, never the real home folder.
"""
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

import helpers as H
import _common as C
import _dashboard_assets as A
import build_dashboard as B
import init as I
import validate as V

NODE = shutil.which("node")
NO_ENV = {"LVLME_HOME": "", "CLIMB_HOME": ""}


class Homes(unittest.TestCase):
    """A fake home: new and old parent folders that exist only when a test makes them."""

    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="lvlme-home-")
        self.addCleanup(shutil.rmtree, self.home, True)
        self.new = os.path.join(self.home, "lvlme-workspaces")
        self.old = os.path.join(self.home, "climb-workspaces")
        for patch in (mock.patch.object(C, "DEFAULT_PARENT", self.new), mock.patch.object(C, "LEGACY_PARENT", self.old),
                      mock.patch.object(C, "_legacy_noted", []), mock.patch.dict(os.environ, NO_ENV)):
            patch.start()
            self.addCleanup(patch.stop)

    def workspace(self, parent, name):
        ws = os.path.join(parent, name)
        os.makedirs(ws)
        H.save(os.path.join(ws, "config.json"), H.template_config())
        return ws

    def call(self, fn, *args):
        """Run fn, returning (result, what it printed on stderr)."""
        err = io.StringIO()
        with mock.patch("sys.stderr", err), mock.patch("sys.stdout", io.StringIO()):
            out = fn(*args)
        return out, err.getvalue()


class EnvTests(Homes):
    def test_lvlme_home_is_read(self):
        with mock.patch.dict(os.environ, {"LVLME_HOME": "/tmp/new-ws"}):
            self.assertEqual(C.resolve_workspace(None), "/tmp/new-ws")

    def test_climb_home_still_works_when_lvlme_home_is_not_set(self):
        with mock.patch.dict(os.environ, {"CLIMB_HOME": "/tmp/old-ws"}):
            self.assertEqual(C.home_env(), "/tmp/old-ws")
            self.assertEqual(C.resolve_workspace(None), "/tmp/old-ws")

    def test_lvlme_home_wins_over_climb_home(self):
        with mock.patch.dict(os.environ, {"LVLME_HOME": "/tmp/new-ws", "CLIMB_HOME": "/tmp/old-ws"}):
            self.assertEqual(C.resolve_workspace(None), "/tmp/new-ws")

    def test_workspace_flag_wins_over_both(self):
        with mock.patch.dict(os.environ, {"LVLME_HOME": "/tmp/new-ws", "CLIMB_HOME": "/tmp/old-ws"}):
            self.assertEqual(C.resolve_workspace("/tmp/flag-ws"), "/tmp/flag-ws")


class FolderTests(Homes):
    def test_new_folder_when_neither_exists(self):
        parent, err = self.call(C.default_parent)
        self.assertEqual((parent, err), (self.new, ""))

    def test_old_folder_when_only_it_exists_and_said_once(self):
        os.makedirs(self.old)
        err = io.StringIO()
        with mock.patch("sys.stderr", err):
            got = [C.default_parent(), C.default_parent(), C.default_parent(note=False)]
        self.assertEqual(got, [self.old] * 3)
        self.assertEqual(err.getvalue(), C.LEGACY_NOTE + "\n")
        self.assertIn("~/climb-workspaces", C.LEGACY_NOTE)
        self.assertNotIn(self.home, C.LEGACY_NOTE)     # never spells out the person's home folder

    def test_new_folder_wins_when_both_exist_and_says_so_once(self):
        os.makedirs(self.old)
        os.makedirs(self.new)
        err = io.StringIO()
        with mock.patch("sys.stderr", err):
            got = [C.default_parent(), C.default_parent(), C.default_parent(note=False)]
        self.assertEqual(got, [self.new] * 3)
        self.assertEqual(err.getvalue(), C.BOTH_NOTE + "\n")
        self.assertIn("using ~/lvlme-workspaces", C.BOTH_NOTE)    # names the one in use
        self.assertNotIn(self.home, C.BOTH_NOTE)

    def test_no_note_when_only_the_new_folder_exists(self):
        os.makedirs(self.new)
        parent, err = self.call(C.default_parent)
        self.assertEqual((parent, err), (self.new, ""))

    def test_scripts_find_a_workspace_in_the_old_folder(self):
        ws = self.workspace(self.old, "my-goal")
        found, err = self.call(C.resolve_workspace, None)
        self.assertEqual(found, ws)
        self.assertEqual(err.count("climb-workspaces"), 1)
        opened, _ = self.call(C.open_workspace, None)
        self.assertEqual(opened[0], ws)

    def test_init_uses_the_old_folder_while_only_it_exists(self):
        self.workspace(self.old, "first-goal")
        out = io.StringIO()
        with mock.patch("sys.stdout", out), mock.patch("sys.stderr", io.StringIO()):
            self.assertEqual(I.main(["--goal", "Second goal"]), 0)
        self.assertTrue(os.path.isfile(os.path.join(self.old, "second-goal", "config.json")))
        self.assertFalse(os.path.exists(self.new))
        self.assertEqual(out.getvalue().splitlines()[-1], I.NEXT_STEP)   # found without naming the folder

    def test_init_uses_the_new_folder_on_a_fresh_machine(self):
        with mock.patch("sys.stdout", io.StringIO()):
            self.assertEqual(I.main(["--goal", "First goal"]), 0)
        self.assertTrue(os.path.isfile(os.path.join(self.new, "first-goal", "config.json")))
        self.assertFalse(os.path.exists(self.old))

    def test_init_honours_climb_home(self):
        target = os.path.join(self.home, "elsewhere", "labs")
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"CLIMB_HOME": target}), mock.patch("sys.stdout", out):
            self.assertEqual(I.main(["--goal", "AI labs"]), 0)
        self.assertTrue(os.path.isfile(os.path.join(target, "config.json")))
        self.assertEqual(out.getvalue().splitlines()[-1], I.NEXT_STEP)


class OldWorkspaceTests(unittest.TestCase):
    def test_no_schema_field_carries_the_product_name(self):
        """The rename changed no workspace field, so files written by Climb need no alias to be read."""
        def keys(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    yield k
                    yield from keys(v)
            elif isinstance(node, list):
                for v in node:
                    yield from keys(v)
        for name in sorted(os.listdir(os.path.join(H.ENGINE, "schemas"))):
            for key in keys(H.schema(name)):
                self.assertNotRegex(key.lower(), "climb|lvlme", name)

    def test_a_workspace_written_by_climb_validates_and_builds(self):
        ws = H.copy_demo(self)
        agents = os.path.join(ws, "report", "for-agents", "dashboard.json")
        data = H.load(agents)
        data["generated_by"] = "climb scripts/build_dashboard.py"
        H.save(agents, data)
        self.assertEqual(V.validate_workspace(ws)[0], [])
        with mock.patch("sys.stdout", io.StringIO()):
            self.assertEqual(B.main(["--workspace", ws]), 0)
        self.assertEqual(H.load(agents)["generated_by"], "lvlme scripts/build_dashboard.py")


@unittest.skipUnless(NODE, "Node.js is not installed")
class DashboardStorageTests(unittest.TestCase):
    """The theme and the Pending ticks a browser saved under the old keys still load."""

    def run_js(self, store):
        js = A.JS_HOME + A.JS_VIEWS + A.JS_LEVELS + A.JS_DETAIL + A.JS_CORE + A.JS_CHART
        theme = next(l for l in js.splitlines() if 'localStorage.getItem("lvlme-theme")' in l)
        start = js.index("const PEND_KEY")
        pend = js[start:js.index("function savePending", start)]
        prog = ("const store = %s; globalThis.localStorage = {getItem: k => k in store ? store[k] : null};\n"
                "const D = {meta: {title: 'Demo'}, actions: [{id: 'A01'}, {id: 'A02'}]}; const live = a => true;\n"
                "let theme = 'auto';\n%s\n%s\nconsole.log(JSON.stringify({theme, pending: [...pending]}));"
                % (json.dumps(store), theme, pend))
        res = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr)
        return json.loads(res.stdout)

    def test_old_keys_are_read(self):
        got = self.run_js({"climb-theme": "dark", "climb-pending:Demo": json.dumps(["A02"])})
        self.assertEqual(got, {"theme": "dark", "pending": ["A02"]})

    def test_new_keys_win(self):
        got = self.run_js({"climb-theme": "dark", "lvlme-theme": "light",
                           "climb-pending:Demo": json.dumps(["A02"]), "lvlme-pending:Demo": json.dumps(["A01"])})
        self.assertEqual(got, {"theme": "light", "pending": ["A01"]})

    def test_auto_is_the_default_and_is_kept(self):
        self.assertEqual(self.run_js({})["theme"], "auto")
        self.assertEqual(self.run_js({"lvlme-theme": "auto"})["theme"], "auto")

    def test_new_keys_are_written(self):
        js = A.JS_CORE + A.JS_HOME + A.JS_VIEWS + A.JS_LEVELS + A.JS_DETAIL
        self.assertIn('localStorage.setItem("lvlme-theme", theme)', js)
        self.assertNotIn('setItem("climb-', js)


if __name__ == "__main__":
    unittest.main()
