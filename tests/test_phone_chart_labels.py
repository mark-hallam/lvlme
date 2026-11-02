"""On a phone the chart's three end labels sit on their own lines, never overlap, and the share card fits its row.

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
            [92.2, 110.0, 125.2],  # the demo on a phone: best 71, expected 63, do nothing 57
            [110.0, 110.0, 125.2],  # best case equal to expected, do nothing just below
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
        for case, out in zip(cases, json.loads(res.stdout)):
            # labels read in the same order as their lines, top to bottom
            self.assertEqual(sorted(range(3), key=lambda i: (out[i][1], i)), sorted(range(3), key=lambda i: (case[i], i)))
            # where the lines leave room (13px or more apart), each label is closer to its own line than to any
            # other (its middle sits 4px above its baseline); closer lines than that rely on the label's key
            if min(abs(case[i] - case[j]) for i in range(3) for j in range(i + 1, 3)) < 13:
                continue
            for i, o in enumerate(out):
                mine = abs(o[1] - 4 - case[i])
                for other in case:
                    if other != case[i]:
                        self.assertLess(mine, abs(o[1] - 4 - other), (names[i], case, out))
        # well apart, each label is centred on its own line
        self.assertEqual([o[1] for o in json.loads(res.stdout)[3]], [104, 184, 264])
        # close but clear of each other: nothing moves, so "63 Expected" is on the solid line, not the dotted one
        self.assertEqual([round(o[1], 1) for o in json.loads(res.stdout)[5]], [96.2, 114.0, 129.2])
        # equal values read top to bottom as best case, expected, do nothing
        first = json.loads(res.stdout)[0]
        self.assertLess(first[0][1], first[1][1])
        self.assertLess(first[1][1], first[2][1])

    def test_chart_uses_the_placement_on_a_phone(self):
        self.assertIn("phoneEndLabels(ends, PT + 12, PT + IH - 4)", A.JS_CHART)

    def test_each_phone_label_carries_a_key_drawn_like_its_line(self):
        """All three labels are the same grey, so a short key in the line's own colour and dash tells them apart."""
        self.assertIn('const keys = [[c, "7 5"], [c, "none"], ["var(--stop)", "2 4"]];', A.JS_CHART)
        # the keys match the lines: best case dashed 7 5, expected solid, do nothing dotted 2 4 in the stop grey
        self.assertIn('<path id="pNone" class="series" stroke="var(--stop)" stroke-dasharray="2 4"/>', A.JS_CHART)
        self.assertIn('<path id="pBest" class="series" stroke-dasharray="7 5"/>', A.JS_CHART)
        self.assertIn('"stroke-dasharray": keys[i][1]', A.JS_CHART)


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
