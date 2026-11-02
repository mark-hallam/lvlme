"""The dashboard's share card makes no claim the numbers do not support.

The share card and its saved image are the one surface built to travel, so the
headline states only what was measured: the flight level on day 1 and today,
counted in days like the Day number above the chart. It never says "to an offer". The headline function runs
in Node.js (a JavaScript runtime) and is skipped when Node.js is not installed.
"""
import json
import re
import shutil
import subprocess
import unittest

import helpers as H  # noqa: F401  (puts the engine scripts on the path)
import _dashboard_assets as A

NODE = shutil.which("node")


def headline_script():
    core = A.JS_CORE
    helpers = [l for l in core.splitlines() if re.match(r"const (BANDS|bandIdx) = ", l)]
    detail = A.JS_DETAIL
    start = detail.index("function shareHeadline(")
    return "\n".join(helpers) + "\n" + detail[start:detail.index("\n}\n", start) + 3]


class ShareCardTests(unittest.TestCase):
    def test_no_offer_claim_and_one_headline_for_card_and_image(self):
        self.assertNotIn("to an offer", A.JS_DETAIL)
        self.assertIn("${esc(s.head)}", A.JS_DETAIL)          # the dialog
        self.assertIn("x.fillText(s.head, 70, 170)", A.JS_DETAIL)  # the saved image

    @unittest.skipUnless(NODE, "Node.js is not installed")
    def test_headline_states_levels_and_days(self):
        cases = [[44, 57, 29], [57, 59, 15], [40, 40, 2], [62, 48, 8], [30, 30, 1], [12, 90, 101]]
        prog = headline_script() + "\nconsole.log(JSON.stringify(%s.map(c => shareHeadline(...c))));" % json.dumps(cases)
        res = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(json.loads(res.stdout), [
            "Level 2, Low to Level 3, Moderate by day 29",
            "Level 3, Moderate on day 1 and day 15",
            "Level 2, Low on day 1 and day 2",
            "Level 3, Moderate to Level 2, Low by day 8",
            "Level 1, Very low on day 1",
            "Level 1, Very low to Level 5, Strong by day 101",
        ])


if __name__ == "__main__":
    unittest.main()
