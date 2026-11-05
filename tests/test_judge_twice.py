"""Rubric 1.2: D1, D2 and D4 are judged twice, scoring averages them and records the range."""
import os
import unittest

import helpers as H
import score as S
import validate as V
from test_score import Base, e, TODAY


def two(a, b, ev=("E01",), **kw):
    out = {"judgings": [a, b], "evidence": list(ev), "note": ""}
    out.update(kw)
    return out


class AverageTests(Base):
    def test_average_rounds_halves_down_the_same_way_every_time(self):
        self.assertEqual([S.average_score(x) for x in ([3, 4], [4, 3], [2, 3], [0, 1], [4, 4], [5, 4], [1, 1, 2], [2, 3, 3])],
                         [3, 3, 2, 0, 4, 4, 1, 3])

    def test_two_judgings_average_and_are_recorded(self):
        self.judge("acme:1", two(3, 4), two(2, 2), e(2, ["E01"]))
        r = self.run_score()["roles"][0]
        self.assertEqual((r["scores"]["D1"]["score"], r["scores"]["D1"]["judgings"]), (3, [3, 4]))
        self.assertEqual(r["scores"]["D2"]["judgings"], [2, 2])
        self.assertNotIn("judgings", r["scores"]["D4"])      # judged once: no judgings key

    def test_fit_range_is_the_lowest_and_highest_judging(self):
        self.judge("acme:1", two(3, 4), two(2, 3), two(1, 3))
        r = self.run_score()["roles"][0]
        w = S.C.weights_of(self.cfg)
        total = float(sum(w.values()))

        def fit(d1, d2, d4):
            pts = {"D1": d1, "D2": d2, "D4": d4, "D3": 0, "D5": 0, "D7": 0, "D6": 5}
            return round(sum(pts[d] / 5.0 * w[d] for d in pts) * 100.0 / total, 1)
        self.assertEqual(r["fit"], fit(3, 2, 2))
        self.assertEqual(r["fit_low"], fit(3, 2, 1))
        self.assertEqual(r["fit_high"], fit(4, 3, 3))
        self.assertLess(r["fit_low"], r["fit"])
        self.assertLess(r["fit"], r["fit_high"])

    def test_one_score_per_factor_gives_a_range_of_one_fit(self):
        self.judge("acme:1", e(3, ["E02"]), e(2, ["E01"]), e(2, ["E01"]))
        r = self.run_score()["roles"][0]
        self.assertEqual((r["fit_low"], r["fit"], r["fit_high"]), (r["fit"], r["fit"], r["fit"]))
        self.assertNotIn("judgings", r["scores"]["D1"])

    def test_evidence_cap_applies_to_each_judging(self):
        self.judge("acme:1", two(4, 5, ["E03"]), e(0, []), e(0, []))     # self-reported job history supports 3
        r = self.run_score()["roles"][0]
        self.assertEqual(r["scores"]["D1"]["score"], 3)
        self.assertEqual(r["scores"]["D1"]["judgings"], [4, 5])           # the judgings stay as the judges gave them
        self.assertEqual(r["scores"]["D1"]["raw"], 4)
        self.assertEqual(r["fit_high"], r["fit"])                         # both judgings capped to 3: no spread left

    def test_review_cap_applies_and_awaits_review(self):
        self.judge("acme:1", two(2, 4, ["E01"], judged_on="2026-10-01"), e(0, []), e(0, []))
        del self.judgements["acme:1"]["reviewed_on"]
        r = self.run_score()["roles"][0]
        self.assertEqual(r["scores"]["D1"]["score"], 2)
        self.assertEqual(r["awaiting_review"], ["D1"])

    def test_a_settled_score_beats_the_judgings_and_the_range_still_shows_them(self):
        self.judge("acme:1", two(2, 4, score=3), e(0, []), e(0, []))
        r = self.run_score()["roles"][0]
        self.assertEqual(r["scores"]["D1"]["score"], 3)
        self.assertLess(r["fit_low"], r["fit"])
        self.assertGreater(r["fit_high"], r["fit"])

    def test_hard_requirement_lacking_caps_the_whole_range(self):
        self.judge("acme:1", two(4, 5, ["E01"]), e(0, []), e(0, []), hard_requirement_lacking=True)
        r = self.run_score()["roles"][0]
        self.assertEqual(r["scores"]["D1"]["score"], 1)
        self.assertEqual(r["fit_high"], r["fit"])

    def test_not_judged_role_has_a_zero_range(self):
        r = self.run_score()["roles"][0]
        self.assertEqual((r["fit_low"], r["fit_high"]), (r["fit"], r["fit"]))

    def test_the_same_inputs_give_the_same_run(self):
        self.judge("acme:1", two(3, 4), two(2, 3), two(1, 3))
        self.assertEqual(self.run_score(), self.run_score())

    def test_run_and_judgement_files_match_their_schemas(self):
        self.judge("acme:1", two(3, 4), two(2, 3), e(2, ["E01"]))
        run = self.run_score()
        self.assertEqual(V.check(run, H.schema("run.schema.json")), [])
        self.assertEqual(V.check(H.load(os.path.join(self.ws, "eval", "judgements.json")),
                                 H.schema("judgements.schema.json")), [])
        self.assertTrue(V.check({"schema_version": 1, "roles": {"x": {"D1": {"note": "n"}, "D2": e(1), "D4": e(1)}}},
                                H.schema("judgements.schema.json")))   # neither score nor judgings is refused

    def test_a_per_org_best_role_carries_the_range(self):
        self.judge("acme:1", two(3, 4), two(2, 3), two(1, 3))
        best = self.run_score()["per_org"]["acme"]
        self.assertLess(best["fit_low"], best["fit_high"])


class JudgeChangeWithJudgingsTests(Base):
    def go(self, date, agent, judgings):
        self.judged_by = {"agent": agent}
        self.judge("acme:1", e(2, ["E01"]), two(*judgings, ev=("E02",)), e(2, ["E01"]))
        run = self.run_score(date)
        H.save(os.path.join(self.ws, "eval", "runs", date + ".json"), run)
        return run["roles"][0]

    def test_b6_still_keeps_the_score_and_collapses_the_range(self):
        self.go("2026-11-01", "Claude Code", (2, 2))
        r = self.go("2026-11-02", "Codex", (1, 1))
        self.assertEqual(r["scores"]["D2"]["score"], 2)
        self.assertIn("judge_changed", r["scores"]["D2"])


class BlindReviewTests(unittest.TestCase):
    def test_averaged_score_is_compared_with_the_review(self):
        ws = H.new_workspace(self, H.example_config())
        H.save(os.path.join(ws, "eval", "judgements.json"), {"schema_version": 1, "roles": {"acme:1": {
            "D1": two(3, 4, judged_on="2026-10-01", reviewed_on="2026-10-02"), "D2": e(1, []), "D4": e(1, [])}}})
        H.save(os.path.join(ws, "eval", "reviews", "2026-10-02.json"), {"schema_version": 1, "date": "2026-10-02", "items": [
            {"item": "acme:1 D1", "scorer": {"score": 3}, "reviewer": {"score": 4}, "decided": "reviewer_one_point",
             "stands": 3}]})
        _, warnings, _ = V.validate_workspace(ws)
        self.assertFalse([w for w in warnings if "but the judgement file has" in w], warnings)


if __name__ == "__main__":
    unittest.main()
