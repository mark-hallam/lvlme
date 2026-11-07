"""Job match (added to rubric 1.2 in LVLme 0.7.2): how well the person matches the job itself.

Fit adds up all seven factors, including three that are about the person's campaign rather than the job
(D3 warm path, D5 public signal, D7 application readiness). Job match uses only the factors judged against
the role (D1, D2, D4, D6), so a strong match is not hidden by having no contacts or no tailored CV yet.
Fit, the bands and the levels do not change.

A warm path the person was never asked about is not the same as knowing nobody: it still scores 0
(evidence or zero), but the run says it was not asked and asks the question.
"""
import unittest

import helpers as H
import score as S
import validate as V
from test_score import Base, e, role


def match_of(w, pts):
    keys = ("D1", "D2", "D4", "D6")
    total = float(sum(w[d] for d in keys))
    return round(sum(pts[d] / 5.0 * w[d] for d in keys) * 100.0 / total, 1)


class JobMatchTests(Base):
    def test_match_uses_only_the_factors_judged_against_the_role(self):
        self.judge("acme:1", e(3, ["E02"]), e(3, ["E01"]), e(1, ["E01"]))
        r = self.run_score()["roles"][0]
        w = S.C.weights_of(self.cfg)
        self.assertEqual(r["match"], match_of(w, {"D1": 3, "D2": 3, "D4": 1, "D6": 5}))
        self.assertGreater(r["match"], r["fit"])

    def test_campaign_factors_move_fit_but_not_match(self):
        self.judge("acme:1", e(3, ["E02"]), e(3, ["E01"]), e(2, ["E01"]))
        before = self.run_score()["roles"][0]
        self.profile["D5"] = {"default": e(2, ["E01"])}
        self.profile["D7"] = {"default": e(2, ["E01"])}
        after = self.run_score()["roles"][0]
        self.assertGreater(after["fit"], before["fit"])
        self.assertEqual(after["match"], before["match"])

    def test_fit_is_unchanged_by_this_release(self):
        self.judge("acme:1", e(3, ["E02"]), e(2, ["E01"]), e(1, ["E01"]))
        r = self.run_score()["roles"][0]
        w = S.C.weights_of(self.cfg)
        pts = {"D1": 3, "D2": 2, "D3": 0, "D4": 1, "D5": 0, "D6": 5, "D7": 0}
        self.assertEqual(r["fit"], round(sum(pts[d] / 5.0 * w[d] for d in pts) * 100.0 / sum(w.values()), 1))

    def test_match_follows_custom_weights(self):
        self.cfg.setdefault("scoring", {})["weights"] = {"D1": 40, "D2": 20, "D3": 10, "D4": 10, "D5": 5, "D6": 10, "D7": 5}
        self.judge("acme:1", e(2, ["E01"]), e(4, ["E01"]), e(0, []))
        r = self.run_score()["roles"][0]
        self.assertEqual(r["match"], match_of(S.C.weights_of(self.cfg), {"D1": 2, "D2": 4, "D4": 0, "D6": 5}))

    def test_match_keeps_the_hard_requirement_cap(self):
        self.judge("acme:1", e(4, ["E01"]), e(3, ["E01"]), e(1, ["E01"]), hard_requirement_lacking=True)
        r = self.run_score()["roles"][0]
        w = S.C.weights_of(self.cfg)
        self.assertEqual(r["match"], match_of(w, {"D1": 1, "D2": 3, "D4": 1, "D6": 5}))

    def test_match_range_follows_the_judgings(self):
        two = lambda a, b: {"judgings": [a, b], "evidence": ["E01"], "note": ""}
        self.judge("acme:1", two(3, 4), two(2, 3), two(1, 1))
        r = self.run_score()["roles"][0]
        w = S.C.weights_of(self.cfg)
        self.assertEqual(r["match_low"], match_of(w, {"D1": 3, "D2": 2, "D4": 1, "D6": 5}))
        self.assertEqual(r["match_high"], match_of(w, {"D1": 4, "D2": 3, "D4": 1, "D6": 5}))

    def test_unjudged_role_match_counts_only_location(self):
        r = self.run_score()["roles"][0]
        w = S.C.weights_of(self.cfg)
        self.assertEqual(r["match"], match_of(w, {"D1": 0, "D2": 0, "D4": 0, "D6": 5}))

    def test_per_org_and_schema_carry_match(self):
        self.judge("acme:1", e(3, ["E02"]), e(3, ["E01"]), e(1, ["E01"]))
        run = self.run_score()
        self.assertEqual(run["per_org"]["acme"]["match"], run["roles"][0]["match"])
        self.assertEqual(V.check(run, H.schema("run.schema.json")), [])

    def test_all_role_weights_zero_gives_zero_not_a_crash(self):
        self.cfg.setdefault("scoring", {})["weights"] = {"D1": 0, "D2": 0, "D3": 50, "D4": 0, "D5": 50, "D6": 0, "D7": 0}
        self.judge("acme:1", e(3, ["E02"]), e(3, ["E01"]), e(1, ["E01"]))
        self.assertEqual(self.run_score()["roles"][0]["match"], 0.0)


class WarmPathAskedTests(Base):
    def questions(self, run):
        return [q for q in run["verify_to_unlock"] if q["source"] == "warm_path_not_asked"]

    def test_default_entry_alone_means_not_asked_for_each_target(self):
        self.judge("acme:1", e(2, ["E01"]), e(2, ["E01"]), e(1, ["E01"]))
        run = self.run_score()
        r = run["roles"][0]
        self.assertFalse(r["warm_path_asked"])
        self.assertEqual(r["scores"]["D3"]["score"], 0)
        self.assertIn("not asked", r["scores"]["D3"]["note"].lower())
        qs = self.questions(run)
        self.assertEqual(len(qs), 2)                        # one per target organisation: Acme and Globex
        self.assertIn("Acme", qs[0]["question"])
        self.assertEqual(qs[0]["dimensions"], ["D3"])
        self.assertEqual(run["counts"]["warm_path_not_asked"], 2)
        self.assertEqual(V.check(run, H.schema("run.schema.json")), [])

    def test_default_marked_asked_means_the_person_answered_for_all(self):
        self.profile["D3"] = {"default": e(0, [], asked=True)}
        self.judge("acme:1", e(2, ["E01"]), e(2, ["E01"]), e(1, ["E01"]))
        run = self.run_score()
        self.assertTrue(run["roles"][0]["warm_path_asked"])
        self.assertEqual(self.questions(run), [])
        self.assertEqual(run["counts"]["warm_path_not_asked"], 0)

    def test_an_organisation_entry_counts_as_asked_for_that_organisation(self):
        self.profile["D3"] = {"default": e(0, []), "acme": e(0, [])}
        self.judge("acme:1", e(2, ["E01"]), e(2, ["E01"]), e(1, ["E01"]))
        run = self.run_score()
        self.assertTrue(run["roles"][0]["warm_path_asked"])
        qs = self.questions(run)
        self.assertEqual(len(qs), 1)
        self.assertIn("Globex", qs[0]["question"])

    def test_an_entry_can_say_it_was_not_asked(self):
        self.profile["D3"] = {"acme": e(0, [], asked=False)}
        self.judge("acme:1", e(2, ["E01"]), e(2, ["E01"]), e(1, ["E01"]))
        run = self.run_score()
        self.assertFalse(run["roles"][0]["warm_path_asked"])

    def test_profile_with_asked_still_validates(self):
        self.profile["D3"] = {"default": e(0, [], asked=True)}
        self.assertEqual(V.check(self.profile, H.schema("profile-dimensions.schema.json")), [])


class DemoTests(unittest.TestCase):
    def test_demo_for_agents_file_carries_job_match(self):
        import json, os
        with open(os.path.join(H.DEMO, "report", "for-agents", "dashboard.json"), encoding="utf-8") as fh:
            roles = json.load(fh)["roles"]
        self.assertTrue(roles)
        self.assertTrue(all("match" in r and r["match"] >= 0 for r in roles))


if __name__ == "__main__":
    unittest.main()


class HeadlineTests(Base):
    def test_headline_changes_after_the_answer_without_changing_the_maths(self):
        self.judge("acme:1", e(2, ["E01"]), e(2, ["E01"]), e(2, ["E01"]))
        runs = []
        for asked in (False, True):
            self.profile["D3"] = {"acme": e(0, [], asked=asked)}
            run = self.run_score()
            r = run["roles"][0]
            kind = "fit" if asked else "match"
            why = "" if asked else "Job match: the job itself. Fit waits for your answer about who you know at Acme."
            self.assertEqual(r["headline"], {"kind": kind, "value": r[kind],
                                           "low": r[kind + "_low"], "high": r[kind + "_high"], "why": why})
            self.assertEqual(V.check(run, H.schema("run.schema.json")), [])
            runs.append(r)
        for key in ("fit", "fit_low", "fit_high", "match", "match_low", "match_high", "interview_band", "offer_band"):
            self.assertEqual(runs[0][key], runs[1][key], key)

    def test_headline_does_not_change_run_sorting(self):
        self.roles = [role("acme:1"), role("globex:1", org="globex")]
        self.judge("acme:1", e(2, ["E01"]), e(2, ["E01"]), e(2, ["E01"]))
        self.judge("globex:1", e(1, ["E01"]), e(1, ["E01"]), e(1, ["E01"]))
        self.profile["D3"] = {"acme": e(0, [], asked=False), "globex": e(5, ["E01"], asked=True)}
        run = self.run_score()
        self.assertEqual([r["role_id"] for r in run["roles"]], ["globex:1", "acme:1"])
        self.assertGreater(run["roles"][1]["match"], run["roles"][0]["match"])
