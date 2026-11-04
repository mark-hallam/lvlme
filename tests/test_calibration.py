"""How right has LVLme been (scripts/_calibration.py): its odds against what happened. Fictional data, no network."""
import io
import os
import unittest
from contextlib import redirect_stdout
from unittest import mock

import helpers as H
import _calibration as CAL
import applications as CLI
import score as S
import validate as V

TODAY = "2026-11-01"


def quiet(fn, *args):
    with redirect_stdout(io.StringIO()) as out, mock.patch("sys.stderr", io.StringIO()):
        try:
            code = fn(list(args))
        except SystemExit as exc:
            code = 1 if isinstance(exc.code, str) else exc.code
    return code, out.getvalue()


def row(band, got, kind="interview"):
    other = "offer" if kind == "interview" else "interview"
    return {"pred": {kind + "_band": band, other + "_band": "Very low"}, "out": {kind: got, other: None}}


class OutcomeTests(unittest.TestCase):
    def app(self, stage, applied="2026-09-01", last="2026-09-01"):
        return {"id": "ap1", "stage": stage, "applied_on": applied, "last_step_on": last}

    def test_an_interview_then_a_rejection_is_an_interview_but_no_offer(self):
        self.assertEqual(CAL.outcome(self.app("rejected"), {"applied", "interview", "rejected"}, TODAY),
                         {"interview": True, "offer": False})

    def test_a_rejection_before_any_interview_is_no_on_both(self):
        self.assertEqual(CAL.outcome(self.app("rejected"), {"applied"}, TODAY), {"interview": False, "offer": False})

    def test_silence_counts_as_no_interview_only_after_the_quiet_days(self):
        self.assertEqual(CAL.outcome(self.app("applied", last="2026-10-01"), set(), TODAY),
                         {"interview": None, "offer": None})                     # 31 days: still waiting
        self.assertEqual(CAL.outcome(self.app("applied", last="2026-09-01"), set(), TODAY),
                         {"interview": False, "offer": False})                   # 61 days: no interview

    def test_an_offer_counts_on_both(self):
        self.assertEqual(CAL.outcome(self.app("hired"), set(), TODAY), {"interview": True, "offer": True})

    def test_withdrawn_and_unsent_applications_are_left_out(self):
        self.assertIsNone(CAL.outcome(self.app("discarded"), {"applied"}, TODAY))
        self.assertIsNone(CAL.outcome({"id": "ap2", "stage": "evaluated", "last_step_on": TODAY}, set(), TODAY))

    def test_ranking_counts_pairs_and_ties_half(self):
        rows = [row("Low", True)] + [row("Very low", False)] * 8 + [row("Low", False)]
        self.assertEqual(CAL.ranking(rows, "interview"), {"results": 10, "share": 0.94})   # (8 + 0.5) / 9
        self.assertIsNone(CAL.ranking(rows[:9], "interview"))                             # under ten results
        self.assertIsNone(CAL.ranking([row("Low", False)] * 12, "interview"))             # nothing to compare

    def test_public_figures_match_their_source(self):
        self.assertEqual(CAL.BASE, {"cold": {"interview": 0.03, "offer_if_interview": 0.06},
                                    "referred": {"interview": 0.40, "offer_if_interview": 0.16}})
        self.assertEqual((CAL.SOURCE["date"], CAL.SOURCE["url"]),
                         ("16 May 2025", "https://www.ashbyhq.com/talent-trends-report/reports/referrals"))
        self.assertAlmostEqual(CAL.base_rate("offer", True), 0.064)


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)
        self.apps = H.load(os.path.join(self.ws, "campaign", "applications.json"))

    def test_the_panel_counts_and_hides_bands_under_five(self):
        # Two applications were sent under rubric 1.0, before "Almost none" existed: their recorded bands
        # stay as they were, and the panel still reads them.
        for app in self.apps["applications"]:
            if (app.get("predicted") or {}).get("interview_band") == "Almost none":
                app["predicted"].update(interview_band="Very low", offer_band="Very low")
        s = CAL.summary(self.ws, self.apps, TODAY)
        bands = {b["band"]: b for b in s["interview"]["bands"]}
        self.assertEqual((bands["Very low"]["sent"], bands["Very low"]["results"], bands["Very low"]["hits"]), (6, 5, 0))
        self.assertTrue(bands["Very low"]["shown"])
        self.assertEqual((bands["Low"]["results"], bands["Low"]["hits"], bands["Low"]["shown"]), (1, 1, False))
        self.assertNotIn("rate", bands["Low"])
        self.assertEqual((bands["Moderate"]["waiting"], bands["Moderate"]["shown"]), (1, False))
        self.assertAlmostEqual(bands["Very low"]["blended"], round(10 * 0.03 / 15, 3))
        self.assertIsNone(s["interview"]["ranking"])                                       # 7 results, under 10

    def test_almost_none_is_its_own_band(self):
        s = CAL.summary(self.ws, self.apps, TODAY)
        bands = {b["band"]: b for b in s["interview"]["bands"]}
        self.assertEqual((bands["Almost none"]["sent"], bands["Almost none"]["shown"]), (2, False))

    def test_scores_are_identical_with_or_without_outcomes(self):
        def run():
            quiet(S.main, "--workspace", self.ws, "--date", TODAY)
            return H.load(os.path.join(self.ws, "eval", "runs", TODAY + ".json"))
        with_outcomes = run()
        for name in ("applications.json", "applications-log.tsv"):
            os.remove(os.path.join(self.ws, "campaign", name))
        without = run()
        self.assertEqual(with_outcomes["roles"], without["roles"])
        self.assertEqual(with_outcomes.get("inputs_digest"), without.get("inputs_digest"))

    def test_the_prediction_is_frozen_on_the_day_it_was_sent(self):
        ap4 = next(a for a in self.apps["applications"] if a["id"] == "ap4")
        self.assertEqual(ap4["predicted"]["run_date"], "2026-10-11")
        self.assertEqual(ap4["predicted"]["interview_band"], "Low")
        code, _ = quiet(CLI.main, "--workspace", self.ws, "add", "--org", "acme", "--title", "Technical Program Manager, "
                        "Model Launches", "--role-id", "acme:4100001", "--date", "2026-10-30")
        self.assertEqual(code, 0)
        new = H.load(os.path.join(self.ws, "campaign", "applications.json"))["applications"][-1]
        self.assertEqual(new["predicted"]["run_date"], "2026-10-25")                      # the latest run on or before
        self.assertEqual(quiet(V.main, "--workspace", self.ws)[0], 0)

    def test_an_application_with_no_odds_on_the_day_is_counted_as_left_out(self):
        quiet(CLI.main, "--workspace", self.ws, "add", "--org", "acme", "--title", "A role found elsewhere",
              "--date", "2026-10-02")
        quiet(CLI.main, "--workspace", self.ws, "move", "ap9", "rejected", "--date", "2026-10-09")
        doc = H.load(os.path.join(self.ws, "campaign", "applications.json"))
        s = CAL.summary(self.ws, doc, TODAY)
        self.assertEqual((s["sent"], s["unmatched"]), (8, 1))
        self.assertIn("1 sent application had no LVLme odds", "\n".join(CAL.lines(s)))

    def test_the_dashboard_and_agent_files_carry_the_panel(self):
        with open(os.path.join(H.DEMO, "report", "index.html"), encoding="utf-8") as fh:
            page = fh.read()
        self.assertIn('id="calibCard"', page)
        agents = H.load(os.path.join(H.DEMO, "report", "for-agents", "dashboard.json"))
        self.assertEqual(agents["calibration"]["sent"], 8)
        with open(os.path.join(H.DEMO, "report", "for-agents", "SUMMARY.md"), encoding="utf-8") as fh:
            self.assertIn("## How right has LVLme been", fh.read())


if __name__ == "__main__":
    unittest.main()
