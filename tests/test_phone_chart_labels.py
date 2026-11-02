"""On a phone the chart's three end labels never overlap, and the share card fits its row.

On every first run expected, best case and do nothing are equal, so the phone labels used to be
drawn at the same spot. The placement function runs in Node.js (a JavaScript runtime) and that
test is skipped when Node.js is not installed.
"""
import json
import shutil
import subprocess
import unittest

import helpers as H  # noqa: F401  (puts the engine scripts on the path)
import _dashboard_assets as A

NODE = shutil.which("node")


def placement_script():
    chart = A.JS_CHART
    start = chart.index("function phoneEndLabels(")
    return chart[start:chart.index("\n}\n", start) + 3]


class PhoneEndLabelTests(unittest.TestCase):
    @unittest.skipUnless(NODE, "Node.js is not installed")
    def test_labels_stay_apart_and_inside_the_plot(self):
        top, bottom = 22, 280
        cases = [
            [200, 200, 200],   # first run: all three equal
            [270, 270, 270],   # equal and near the bottom of the plot
            [15, 15, 15],      # equal and near the top
            [100, 180, 260],   # well apart: left where they are
            [190, 196, 200],   # close together
        ]
        names = ["Best case", "Expected", "Do nothing"]
        prog = placement_script() + "\nconsole.log(JSON.stringify(%s.map(c => phoneEndLabels(c.map((y, i) => [%s[i], y]), %d, %d))));" % (
            json.dumps(cases), json.dumps(names), top, bottom)
        res = subprocess.run([NODE, "-"], input=prog, capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr)
        for case, out in zip(cases, json.loads(res.stdout)):
            self.assertEqual([o[0] for o in out], names)
            ys = sorted(o[1] for o in out)
            for a, b in zip(ys, ys[1:]):
                self.assertGreaterEqual(b - a, 13, (case, out))
            for y in ys:
                self.assertGreaterEqual(y, top, (case, out))
                self.assertLessEqual(y, bottom, (case, out))
        # well apart, each label keeps its own place: above best case and do nothing, below expected
        self.assertEqual([o[1] for o in json.loads(res.stdout)[3]], [94, 194, 254])
        # equal values read top to bottom as best case, expected, do nothing
        first = json.loads(res.stdout)[0]
        self.assertLess(first[0][1], first[1][1])
        self.assertLess(first[1][1], first[2][1])

    def test_chart_uses_the_placement_on_a_phone(self):
        self.assertIn("phoneEndLabels(ends, PT + 12, PT + IH - 4)", A.JS_CHART)


class ShareRowFitTests(unittest.TestCase):
    def test_share_tiles_can_shrink_to_their_row(self):
        self.assertIn(".share-row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr))", A.CSS)
        self.assertIn("min-width:0}", A.CSS[A.CSS.index(".share-row div{"):])
        self.assertIn(".share-row .pill{white-space:normal", A.CSS)
        # tighter tiles on a phone, and one tile per row on the narrowest screens
        self.assertIn("@media (max-width:420px){.share-row div{padding:8px 7px}", A.CSS)
        self.assertIn("@media (max-width:359px){.share-row{grid-template-columns:minmax(0,1fr)}}", A.CSS)


if __name__ == "__main__":
    unittest.main()
