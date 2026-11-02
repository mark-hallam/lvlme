"""Every script stops with one plain line, never a Python traceback: no workspace, bad JSON, missing files.

Run as real subprocesses, so the scripts' own entry points (C.run_main) are what is tested.
"""
import glob
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import helpers as H
import _common as C

SCRIPTS = os.path.join(H.ENGINE, "scripts")
QUICK_DEMO = glob.glob(os.path.join(H.ENGINE, "examples", "quick-demo", "2026-*"))[0]
# Scripts that read a workspace, with the extra arguments each one needs to get that far.
WORKSPACE_SCRIPTS = {
    "validate.py": [],
    "fetch_roles.py": [],
    "score.py": [],
    "build_dashboard.py": [],
    "network_map.py": ["--csv", os.path.join(H.FIXTURES, "Connections.csv")],
    "claims_audit.py": ["notes.md"],
    "consistency_audit.py": [],
}


def tmpdir(test):
    d = tempfile.mkdtemp(prefix="lvlme-cli-test-")
    test.addCleanup(shutil.rmtree, d, True)
    return d


def lines(text):
    return [line for line in text.splitlines() if line.strip()]


class Script(unittest.TestCase):
    def setUp(self):
        self.home = tmpdir(self)  # an empty home folder: no real workspace can be found by accident

    def run_script(self, name, *args, env=None):
        full_env = {k: v for k, v in os.environ.items()
                    if k not in (C.HOME_ENV, C.LEGACY_HOME_ENV, C.DEBUG_ENV)}
        full_env["HOME"] = self.home
        full_env.update(env or {})
        res = subprocess.run([sys.executable, os.path.join(SCRIPTS, name)] + list(args), capture_output=True,
                             text=True, env=full_env, stdin=subprocess.DEVNULL, cwd=self.home, timeout=60)
        self.assertNotIn("Traceback", res.stdout + res.stderr, "%s printed a traceback" % name)
        return res

    def assert_one_line(self, res, pattern):
        self.assertNotEqual(res.returncode, 0)
        err = lines(res.stderr)
        self.assertEqual(len(err), 1, res.stderr)
        self.assertRegex(err[0], pattern)
        return err[0]

    def broken_workspace(self, rel="config.json", text='{ "targets": [ '):
        ws = H.copy_demo(self)
        with open(os.path.join(ws, rel), "w", encoding="utf-8") as fh:
            fh.write(text)
        return ws


class NoWorkspace(Script):
    def test_every_workspace_script_says_how_to_start(self):
        for name, extra in WORKSPACE_SCRIPTS.items():
            with self.subTest(script=name):
                res = self.run_script(name, *extra)
                self.assert_one_line(res, r"^lvlme: No workspace found\. Run scripts/init\.py first")

    def test_a_workspace_path_that_does_not_exist(self):
        missing = os.path.join(self.home, "nowhere")
        for name, extra in WORKSPACE_SCRIPTS.items():
            if name == "validate.py":
                continue  # validate reports the missing files as its own list (checked below)
            with self.subTest(script=name):
                res = self.run_script(name, "--workspace", missing, *extra)
                self.assert_one_line(res, r"^lvlme: no config\.json in .*nowhere\. Run scripts/init\.py first\.$")
        res = self.run_script("validate.py", "--workspace", missing)
        self.assertEqual(res.returncode, 1)
        self.assertIn("ERROR   config.json: missing", res.stdout)


class BadJson(Script):
    def test_a_broken_config_is_one_line_naming_the_file_and_the_spot(self):
        ws = self.broken_workspace()
        for name, extra in WORKSPACE_SCRIPTS.items():
            if name == "validate.py":
                continue
            with self.subTest(script=name):
                res = self.run_script(name, "--workspace", ws, *extra)
                line = self.assert_one_line(res, r"^lvlme: .*config\.json: not valid JSON \(line 1, column 16: "
                                                 r"Expecting value\)\. Fix that spot in the file, then run this again\.$")
                self.assertEqual(res.returncode, 1, line)

    def test_validate_lists_a_broken_config_without_the_noise_that_follows_from_it(self):
        ws = self.broken_workspace()
        res = self.run_script("validate.py", "--workspace", ws)
        self.assertEqual(res.returncode, 1)
        self.assertIn("ERROR   config.json: not valid JSON (line 1, column 16: Expecting value)", res.stdout)
        # the checks across files need the config, so they wait for it, and the one warning says so
        warned = [line for line in res.stdout.splitlines() if line.startswith("WARNING")]
        self.assertEqual(len(warned), 1, res.stdout)
        self.assertIn("did not run, because they need config.json", warned[0])
        res = self.run_script("validate.py", "--workspace", ws, "--json")
        report = json.loads(res.stdout)
        self.assertEqual(report["errors"], ["config.json: not valid JSON (line 1, column 16: Expecting value)"])
        self.assertEqual(len(report["warnings"]), 1)

    def test_a_broken_judgement_file_stops_scoring_plainly(self):
        ws = self.broken_workspace("eval/judgements.json", '{"roles": {,}}')
        res = self.run_script("score.py", "--workspace", ws)
        self.assert_one_line(res, r"^lvlme: .*eval/judgements\.json: not valid JSON \(line 1, column 12: "
                                  r"Expecting property name")

    def test_a_broken_run_stops_the_dashboard_plainly(self):
        ws = H.copy_demo(self)
        run = sorted(glob.glob(os.path.join(ws, "eval", "runs", "*.json")))[-1]
        with open(run, "w", encoding="utf-8") as fh:
            fh.write("{}{}")
        res = self.run_script("build_dashboard.py", "--workspace", ws)
        self.assert_one_line(res, r"^lvlme: .*eval/runs/%s: not valid JSON \(line 1, column 3: Extra data\)"
                             % re.escape(os.path.basename(run)))

    def test_a_file_that_is_not_utf8_text(self):
        ws = self.broken_workspace()
        with open(os.path.join(ws, "config.json"), "wb") as fh:
            fh.write(b"\xff\xfe{}")
        res = self.run_script("score.py", "--workspace", ws)
        self.assert_one_line(res, r"config\.json: not valid JSON \(it is not UTF-8 text\)")

    def test_a_broken_quick_file_stops_the_build_plainly(self):
        folder = os.path.join(tmpdir(self), "quick")
        shutil.copytree(QUICK_DEMO, folder)
        with open(os.path.join(folder, "eval", "quick.json"), "w", encoding="utf-8") as fh:
            fh.write('{"factors": ')
        for cmd in ("build", "review-items"):
            with self.subTest(cmd=cmd):
                res = self.run_script("quick.py", cmd, "--folder", folder)
                self.assert_one_line(res, r"^lvlme: .*eval/quick\.json: not valid JSON \(line 1, column 13")
        with open(os.path.join(folder, "config.json"), "w", encoding="utf-8") as fh:
            fh.write("{")
        res = self.run_script("quick.py", "build", "--folder", folder)
        self.assert_one_line(res, r"^lvlme: .*config\.json: not valid JSON")


class MissingFiles(Script):
    def test_posting_text_that_is_not_there(self):
        res = self.run_script("quick_posting.py", "--text", "missing.txt")
        self.assert_one_line(res, r"^lvlme: missing\.txt: no posting text file at this path\. "
                                  r"Check the path, then run this again\.$")

    def test_a_saved_response_that_is_not_there(self):
        res = self.run_script("quick_posting.py", "--saved", "missing.json", "https://boards.greenhouse.io/acme/jobs/1")
        self.assert_one_line(res, r"^lvlme: No saved response at missing\.json\.")

    def test_quick_checks_every_named_file_before_writing_a_folder(self):
        posting = os.path.join(self.home, "posting.txt")
        with open(posting, "w", encoding="utf-8") as fh:
            fh.write("Program Manager\n\nWe are hiring a program manager to run delivery for our agents team. " * 3)
        folder = os.path.join(self.home, "quick-folder")
        cases = [
            (["--posting-text", "missing.txt"], r"^lvlme: missing\.txt: no posting text file at this path\."),
            (["--posting-text", posting, "--cv", "missing-cv.pdf"], r"^lvlme: no CV file at missing-cv\.pdf\."),
            (["--posting-text", posting, "--cv-text", "missing-cv.txt"],
             r"^lvlme: missing-cv\.txt: no CV text file at this path\."),
            (["--posting-text", self.home], r"^lvlme: .*: this is a folder, not a posting text file\."),
        ]
        for extra, pattern in cases:
            with self.subTest(args=extra):
                res = self.run_script("quick.py", "new", "--title", "Program Manager", "--org", "Acme AI",
                                      "--folder", folder, *extra)
                self.assert_one_line(res, pattern)
                self.assertFalse(os.path.exists(folder), "nothing is written when an input is missing")

    def test_a_linkedin_export_that_is_not_there(self):
        ws = H.copy_demo(self)
        res = self.run_script("network_map.py", "--workspace", ws, "--csv", "missing.csv")
        self.assert_one_line(res, r"^lvlme: cannot read missing\.csv \(No such file or directory\)\. "
                                  r"Download your LinkedIn data export")


class NoTargetsYet(unittest.TestCase):
    """A new workspace hears the same one line from every script that needs targets."""

    def test_network_map_and_score_say_run_the_interview(self):
        import network_map as N
        import score as S
        ws = H.new_workspace(self)
        for mod, argv in ((N, ["--workspace", ws, "--csv", os.path.join(H.FIXTURES, "Connections.csv")]),
                          (S, ["--workspace", ws])):
            with self.subTest(script=mod.__name__):
                err = io.StringIO()
                with mock.patch("sys.stderr", err), mock.patch("sys.stdout", io.StringIO()):
                    self.assertEqual(mod.main(argv), 1)
                self.assertEqual(err.getvalue(), C.NO_TARGETS + "\n")
        self.assertFalse(os.path.exists(os.path.join(ws, "profile", "network.json")))


class Helpers(unittest.TestCase):
    def test_load_json_names_the_file_and_the_spot(self):
        path = os.path.join(tmpdir(self), "bad.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{\n  "a": 1,\n  "b": \n}')  # Python 3.13 words a trailing comma differently, so avoid one
        with self.assertRaises(C.FileProblem) as cm:
            C.load_json(path)
        self.assertIsInstance(cm.exception, ValueError)  # older callers that catch ValueError keep working
        self.assertEqual(cm.exception.detail, "not valid JSON (line 4, column 1: Expecting value)")
        self.assertTrue(str(cm.exception).startswith(C.show_path(path) + ": not valid JSON"))
        self.assertIsNone(C.load_json(path + ".missing"))  # a missing file is still the default

    def test_show_path_shortens_the_home_folder(self):
        home = os.path.expanduser("~")
        self.assertEqual(C.show_path(os.path.join(home, "lvlme-workspaces", "x")), "~/lvlme-workspaces/x")
        self.assertEqual(C.show_path(home + "-other/x"), home + "-other/x")
        self.assertEqual(C.show_path("relative.json"), "relative.json")

    def test_read_input(self):
        d = tmpdir(self)
        with self.assertRaisesRegex(C.FileProblem, r"no CV file at this path"):
            C.read_input(os.path.join(d, "cv.txt"), "CV file")
        with self.assertRaisesRegex(C.FileProblem, r"this is a folder, not a CV file"):
            C.read_input(d, "CV file")
        path = os.path.join(d, "cv.txt")
        with open(path, "wb") as fh:
            fh.write("Alex Example — PM\n".encode("utf-8") + b"\xff")
        self.assertEqual(C.read_input(path), "Alex Example — PM\n�")  # bad bytes never stop a read
        with mock.patch("sys.stdin", io.StringIO("pasted")):
            self.assertEqual(C.read_input("-"), "pasted")


def run_main(main, workspace_check=True):
    err = io.StringIO()
    with mock.patch("sys.stderr", err):
        code = C.run_main(main, [], workspace_check=workspace_check)
    return code, err.getvalue()


class RunMain(unittest.TestCase):
    def test_passes_the_exit_code_and_argv_through(self):
        self.assertEqual(C.run_main(lambda argv: 3 if argv == ["x"] else 0, ["x"]), 3)

    def test_a_file_problem_is_its_own_line(self):
        def main(argv):
            raise C.FileProblem("/x/plan.json", "not valid JSON (line 2, column 5: Expecting value)")
        self.assertEqual(run_main(main), (1, "lvlme: /x/plan.json: not valid JSON (line 2, column 5: Expecting "
                                             "value). Fix that spot in the file, then run this again.\n"))

    def test_an_os_error_on_a_file(self):
        def main(argv):
            raise PermissionError(13, "Permission denied", "/x/report/index.html")
        code, err = run_main(main)
        self.assertEqual(code, 1)
        self.assertEqual(err, "lvlme: could not open or save /x/report/index.html (Permission denied). Check the "
                              "file is there and you can open it, then run this again.\n")

    def test_anything_unexpected_is_one_line_with_what_to_do(self):
        def main(argv):
            return {}["ats"]
        code, err = run_main(main)
        self.assertEqual(code, 1)
        self.assertEqual(err, "lvlme: unexpected error (KeyError: 'ats'). Check the workspace with "
                              "scripts/validate.py. If it says Valid, rerun with LVLME_DEBUG=1 and report what it "
                              "shows.\n")
        code, err = run_main(lambda argv: int("two\nlines"), workspace_check=False)
        self.assertEqual(err, "lvlme: unexpected error (ValueError: invalid literal for int() with base 10: "
                              "'two\\nlines'). Rerun with LVLME_DEBUG=1 and report what it shows.\n")

    def test_names_the_engine_file_and_line(self):
        import fetch_roles as F
        ws = H.new_workspace(self, dict(H.example_config(), targets=[{"id": "acme", "name": "Acme AI"}]))
        code, err = run_main(lambda argv: F.main(["--workspace", ws]))
        self.assertEqual(code, 1)
        self.assertRegex(err, r"^lvlme: unexpected error \(KeyError: 'ats', in fetch_roles\.py line \d+\)\. ")

    def test_ctrl_c(self):
        def main(argv):
            raise KeyboardInterrupt
        self.assertEqual(run_main(main), (130, "lvlme: stopped.\n"))

    def test_debug_shows_the_full_details(self):
        def main(argv):
            raise KeyError("ats")
        with mock.patch.dict(os.environ, {C.DEBUG_ENV: "1"}), self.assertRaises(KeyError):
            C.run_main(main, [])

    def test_sys_exit_still_passes_through(self):
        def main(argv):
            sys.exit("lvlme: refused.")
        with self.assertRaises(SystemExit):
            C.run_main(main, [])

    def test_every_script_entry_point_uses_it(self):
        for path in sorted(glob.glob(os.path.join(SCRIPTS, "*.py"))):
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            if '__name__ == "__main__"' not in text:
                continue
            with self.subTest(script=os.path.basename(path)):
                self.assertRegex(text, r'if __name__ == "__main__":\n    sys\.exit\(C\.run_main\(main[,)]')


if __name__ == "__main__":
    unittest.main()
