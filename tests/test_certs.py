"""Website certificates: Python from python.org on a Mac has none until "Install Certificates" runs.

Every link is opened through _certs.open_checked: on a certificate failure it retries once with the
system's certificate file, and if that fails too it says, in one plain line, what to do. Offline: the
failures are mocked.
"""
import glob
import io
import os
import re
import ssl
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

import helpers as H
import _certs as CT
import _common as C
import claims_audit as CA
import fetch_doors as FD
import fetch_roles as FR
import quick as QK
import quick_posting as Q

GH = "https://job-boards.greenhouse.io/acmeai/jobs/4200001"
LINE = ("Your Python can't check website certificates. If you installed Python from python.org, run "
        "'Install Certificates.command' in its Applications folder, then try again. "
        "Or paste the job ad text instead.")


def cert_failure():
    return urllib.error.URLError(ssl.SSLCertVerificationError(
        1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate"))


class Response:
    def __init__(self, body=b"ok"):
        self.body = body
        self.headers = mock.Mock(get_content_charset=lambda: "utf-8")

    def read(self, n=-1):
        return self.body

    def geturl(self):
        return "https://example.com/final"

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class Opener:
    """A stand-in for urlopen: fails with a certificate error until it is given a context (or always)."""

    def __init__(self, always_fail=False, other=None):
        self.calls, self.always_fail, self.other = [], always_fail, other

    def __call__(self, req, timeout=None, context=None):
        self.calls.append(context)
        if self.other is not None:
            raise self.other
        if context is None or self.always_fail:
            raise cert_failure()
        return Response()


def a_ca_file(test):
    """A real certificate file for the retry context: this Python's own, or the system's."""
    paths = [ssl.get_default_verify_paths().cafile, ssl.get_default_verify_paths().openssl_cafile, "/etc/ssl/cert.pem"]
    path = next((p for p in paths if p and os.path.isfile(p)), None)
    if not path:
        test.skipTest("no certificate file on this machine")
    return path


class RetryTests(unittest.TestCase):
    def setUp(self):
        patch = mock.patch.object(CT, "SYSTEM_CA_FILES", (a_ca_file(self),))
        patch.start()
        self.addCleanup(patch.stop)

    def test_a_certificate_error_is_retried_once_with_the_system_certificates(self):
        opener = Opener()
        with CT.open_checked(opener, "req", 10) as resp:
            self.assertEqual(resp.read(), b"ok")
        self.assertEqual(len(opener.calls), 2)
        self.assertIsNone(opener.calls[0])
        ctx = opener.calls[1]
        self.assertIsInstance(ctx, ssl.SSLContext)
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)   # checking stays on
        self.assertTrue(ctx.check_hostname)

    def test_the_retry_uses_the_system_file(self):
        with mock.patch.object(CT.ssl, "create_default_context") as make:
            CT.retry_context()
        make.assert_called_once_with(cafile=CT.SYSTEM_CA_FILES[0])

    def test_a_second_failure_gives_the_one_plain_line(self):
        opener = Opener(always_fail=True)
        with self.assertRaises(CT.CertificateProblem) as ctx:
            CT.open_checked(opener, "req", 10, CT.PASTE_INSTEAD)
        self.assertEqual(len(opener.calls), 2)                  # retried once, never more
        self.assertEqual(str(ctx.exception), LINE)

    def test_other_errors_are_not_retried(self):
        opener = Opener(other=urllib.error.URLError("connection refused"))
        with self.assertRaises(urllib.error.URLError):
            CT.open_checked(opener, "req", 10)
        self.assertEqual(len(opener.calls), 1)


class NoCertificateFileTests(unittest.TestCase):
    def test_no_system_file_and_no_certifi_means_no_retry(self):
        missing = os.path.join(tempfile.mkdtemp(prefix="lvlme-ca-"), "none.pem")
        with mock.patch.object(CT, "SYSTEM_CA_FILES", (missing,)), mock.patch.dict(sys.modules, {"certifi": None}):
            self.assertIsNone(CT.ca_file())
            opener = Opener()
            with self.assertRaises(CT.CertificateProblem):
                CT.open_checked(opener, "req", 10)
        self.assertEqual(len(opener.calls), 1)

    def test_certifi_is_used_only_when_importable(self):
        missing = os.path.join(tempfile.mkdtemp(prefix="lvlme-ca-"), "none.pem")
        here = os.path.abspath(__file__)
        fake = mock.Mock(where=lambda: here)
        with mock.patch.object(CT, "SYSTEM_CA_FILES", (missing,)), mock.patch.dict(sys.modules, {"certifi": fake}):
            self.assertEqual(CT.ca_file(), here)

    def test_checking_is_never_turned_off(self):
        off = re.compile(r"CERT_NONE|check_hostname\s*=\s*False|_create_unverified_context|verify\s*=\s*False")
        for path in glob.glob(os.path.join(H.ENGINE, "scripts", "*.py")):
            with self.subTest(script=os.path.basename(path)):
                with open(path, encoding="utf-8") as fh:
                    self.assertIsNone(off.search(fh.read()))


class ScriptTests(unittest.TestCase):
    """Each script that opens links says the one plain line, not "could not open the link"."""

    def setUp(self):
        missing = os.path.join(tempfile.mkdtemp(prefix="lvlme-ca-"), "none.pem")
        for patch in (mock.patch.object(CT, "SYSTEM_CA_FILES", (missing,)),
                      mock.patch.dict(sys.modules, {"certifi": None}),
                      mock.patch("urllib.request.urlopen", Opener(always_fail=True))):
            patch.start()
            self.addCleanup(patch.stop)

    def test_quick_posting_prints_one_plain_line(self):
        err = io.StringIO()
        with mock.patch("sys.stderr", err), mock.patch("sys.stdout", io.StringIO()):
            code = C.run_main(Q.main, [GH], workspace_check=False)
        self.assertEqual(code, 1)
        self.assertEqual(err.getvalue(), "lvlme: " + LINE + "\n")

    def test_lvlme_quick_new_prints_one_plain_line_and_writes_nothing(self):
        parent = tempfile.mkdtemp(prefix="lvlme-quick-")
        self.addCleanup(__import__("shutil").rmtree, parent, True)
        err = io.StringIO()
        with mock.patch("sys.stderr", err), mock.patch("sys.stdout", io.StringIO()):
            code = C.run_main(QK.main, ["new", "--posting", GH, "--parent", parent, "--date", "2026-11-05"],
                              workspace_check=False)
        self.assertEqual(code, 1)
        self.assertEqual(err.getvalue(), "lvlme: " + LINE + "\n")
        self.assertEqual(os.listdir(parent), [])

    def test_job_boards_stop_with_the_line_instead_of_every_board_failed(self):
        with self.assertRaises(CT.CertificateProblem) as ctx:
            FR.fetch_json("https://boards-api.greenhouse.io/v1/boards/acme/jobs", tries=3)
        self.assertNotIn("paste", str(ctx.exception))
        cfg = H.example_config()
        cfg["targets"] = [{"id": "gh", "name": "Acme AI", "ats": "greenhouse", "slug": "acme"}]
        ws = H.new_workspace(self, cfg)
        err = io.StringIO()
        with mock.patch("sys.stderr", err), mock.patch("sys.stdout", io.StringIO()):
            code = C.run_main(FR.main, ["--workspace", ws, "--date", "2026-11-05"])
        self.assertEqual(code, 1)
        self.assertEqual(err.getvalue().splitlines(), ["lvlme: " + CT.HELP])

    def test_calendars_and_claims_audit_say_the_same(self):
        with self.assertRaises(CT.CertificateProblem):
            FD.fetch_text("https://example.com/calendar.ics")
        with self.assertRaises(CT.CertificateProblem):
            CA.read_source("https://example.com/about")


if __name__ == "__main__":
    unittest.main()
