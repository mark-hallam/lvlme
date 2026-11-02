"""score.py: fit maths, evidence and review caps, bands and adjustments, gaps, determinism."""
import json
import os
import unittest

import helpers as H
import score as S
import validate as V

TODAY = "2026-11-01"


def role(rid, org="acme", family="tpm", classes=("australia_nz",), blockers=(), heavy=False):
    return {"id": rid, "org": org, "title": "Role " + rid, "family": family, "locations": ["Somewhere"],
            "location_classes": list(classes), "url": "https://example.com/" + rid, "requires_heavy_coding": heavy,
            "eligibility_blockers": [{"type": b, "text": "posting text"} for b in blockers]}


def e(score, ev=("V",), **kw):
    out = {"score": score, "evidence": list(ev), "note": ""}
    out.update(kw)
    return out


EVIDENCE = {"schema_version": 1, "items": [
    {"id": "E01", "claim": "verified thing", "kind": "artefact", "level": "verified", "sources": []},
    {"id": "E02", "claim": "corroborated job", "kind": "job_history", "level": "corroborated", "sources": []},
    {"id": "E03", "claim": "self-reported job", "kind": "job_history", "level": "self_reported", "sources": []},
    {"id": "E04", "claim": "self-reported achievement", "kind": "achievement", "level": "self_reported", "sources": []},
    {"id": "E05", "claim": "unverified claim", "kind": "achievement", "level": "unverified", "sources": [],
     "dimensions": ["D2"]},
    {"id": "E06", "claim": "contradicted claim", "kind": "achievement", "level": "contradicted", "sources": []},
    {"id": "E07", "claim": "lives here", "kind": "eligibility", "level": "self_reported", "sources": []},
    {"id": "E08", "claim": "partly checked achievement", "kind": "achievement", "level": "partially_verified", "sources": []},
    {"id": "E09", "claim": "partly checked job", "kind": "job_history", "level": "partially_verified", "sources": []},
    {"id": "G01", "claim": "email finding, own numbering", "kind": "artefact", "level": "verified", "sources": []},
], "open_questions": [{"id": "Q01", "question": "Notice period?", "status": "open", "dimensions": ["D6"]},
                      {"id": "Q02", "question": "Done already?", "status": "answered"}]}


class Base(unittest.TestCase):
    def setUp(self):
        self.cfg = H.template_config()
        self.cfg["targets"] = [{"id": "acme", "name": "Acme", "ats": "manual"},
                               {"id": "globex", "name": "Globex", "ats": "manual"}]
        self.ws = H.new_workspace(self, self.cfg)
        self.roles = [role("acme:1")]
        self.judgements = {}
        self.profile = {"schema_version": 1, "judged_on": "2026-10-01", "reviewed_on": TODAY,
                        "D3": {"default": e(0, [])}, "D5": {"default": e(0, [])}, "D7": {"default": e(0, [])},
                        "D6_rules": {"classes": {"australia_nz": e(5, ["E07"]), "us": e(2, ["E07"])}}}
        self.gaps = []

    def run_score(self, date=TODAY):
        H.save(os.path.join(self.ws, "market", "roles", "latest.json"),
               {"schema_version": 1, "fetched_on": date, "summary": {"matched_total": len(self.roles)},
                "roles": self.roles})
        H.save(os.path.join(self.ws, "eval", "judgements.json"),
               {"schema_version": 1, "rubric_version": "1.0", "roles": self.judgements})
        H.save(os.path.join(self.ws, "eval", "profile-dimensions.json"), self.profile)
        H.save(os.path.join(self.ws, "profile", "evidence.json"), EVIDENCE)
        H.save(os.path.join(self.ws, "eval", "gap-templates.json"), {"schema_version": 1, "gaps": self.gaps})
        H.save(os.path.join(self.ws, "config.json"), self.cfg)
        return S.build_run(self.ws, self.cfg, date)

    def judge(self, rid, d1, d2, d4, **kw):
        j = {"D1": d1, "D2": d2, "D4": d4, "judged_on": "2026-10-01", "reviewed_on": TODAY}
        j.update(kw)
        self.judgements[rid] = j


class MathsTests(Base):
    def test_bands_table(self):
        self.assertEqual(S.band_for(S.INTERVIEW_TABLE, 39.9), "Very low")
        self.assertEqual(S.band_for(S.INTERVIEW_TABLE, 40), "Low")
        self.assertEqual(S.band_for(S.INTERVIEW_TABLE, 55), "Moderate")
        self.assertEqual(S.band_for(S.INTERVIEW_TABLE, 70), "Good")
        self.assertEqual(S.band_for(S.INTERVIEW_TABLE, 85), "Strong")
        self.assertEqual(S.band_for(S.OFFER_TABLE, 54.9), "Very low")
        self.assertEqual(S.band_for(S.OFFER_TABLE, 85), "Good")
        self.assertEqual(S.shift("Strong", 1), "Strong")
        self.assertEqual(S.shift("Very low", -1), "Very low")

    def test_fit_formula(self):
        self.judge("acme:1", e(3, ["E02"]), e(2, ["E01"]), e(2, ["E01"]))
        self.profile["D3"]["default"] = e(1, ["E01"])
        self.profile["D5"]["default"] = e(2, ["E01"])
        self.profile["D7"]["default"] = e(1, ["E01"])
        r = self.run_score()["roles"][0]
        # 3/5*25 + 2/5*20 + 1/5*20 + 2/5*10 + 2/5*10 + 5/5*10 + 1/5*5 = 15+8+4+4+4+10+1
        self.assertEqual(r["fit"], 46.0)
        self.assertEqual((r["interview_band"], r["offer_band"]), ("Low", "Very low"))

    def test_all_fives_is_100_and_cold_cap(self):
        self.judge("acme:1", e(5, ["E01"]), e(5, ["E01"]), e(5, ["E01"]))
        for d in ("D5", "D7"):
            self.profile[d]["default"] = e(5, ["E01"])
        self.profile["D3"]["default"] = e(1, ["E01"])
        r = self.run_score()["roles"][0]
        self.assertEqual(r["fit"], 84.0)
        self.assertEqual(r["interview_band"], "Good")
        self.assertEqual(r["offer_band"], "Low")  # cold application caps the offer at Low
        self.assertTrue(any("Cold application" in a for a in r["adjustments"]))
        self.profile["D3"]["default"] = e(5, ["E01"])
        r = self.run_score()["roles"][0]
        self.assertEqual(r["fit"], 100.0)
        self.assertEqual((r["interview_band"], r["offer_band"]), ("Strong", "Good"))

    def test_weights_rescaled(self):
        self.cfg["scoring"]["weights"] = {"D1": 50, "D2": 0, "D3": 0, "D4": 0, "D5": 0, "D6": 0, "D7": 0}
        self.judge("acme:1", e(5, ["E01"]), e(0, []), e(0, []))
        self.assertEqual(self.run_score()["roles"][0]["fit"], 100.0)

    def test_warm_referral_moves_interview_up(self):
        self.judge("acme:1", e(3, ["E02"]), e(3, ["E01"]), e(3, ["E01"]))
        self.profile["D3"]["default"] = e(4, ["E01"])
        r = self.run_score()["roles"][0]
        self.assertEqual(r["fit"], 15 + 12 + 16 + 6 + 0 + 10 + 0)  # 59: Moderate, moved up to Good
        self.assertEqual(r["interview_band"], "Good")
        self.assertTrue(any("Warm referral" in a for a in r["adjustments"]))


class CapTests(Base):
    def test_evidence_caps(self):
        self.judge("acme:1", e(5, ["E03"]), e(5, ["E04"]), e(5, []))
        r = self.run_score()["roles"][0]
        self.assertEqual(r["scores"]["D1"]["score"], 3)  # self-reported job history allows at most 3
        self.assertEqual(r["scores"]["D2"]["score"], 1)  # self-reported achievement allows 1
        self.assertEqual(r["scores"]["D4"]["score"], 0)  # no evidence, no points
        self.assertEqual(r["scores"]["D2"]["raw"], 5)
        self.assertIn("self-reported achievement", r["scores"]["D2"]["capped"])

    def test_corroborated_contradicted_unknown(self):
        self.judge("acme:1", e(5, ["E02"]), e(4, ["E06"]), e(3, ["E99"]))
        run = self.run_score()
        r = run["roles"][0]
        self.assertEqual(r["scores"]["D1"]["score"], 4)  # corroborated allows 4 (reviewed)
        self.assertEqual(r["scores"]["D2"]["score"], 0)  # contradicted supports nothing
        self.assertEqual(r["scores"]["D4"]["score"], 0)
        self.assertTrue(any("unknown evidence id E99" in w for w in run["warnings"]))

    def test_review_cap_and_stale_review(self):
        self.judge("acme:1", e(4, ["E01"]), e(4, ["E01"], reviewed_on="2026-09-01", judged_on="2026-10-01"),
                   e(3, ["E01"]), reviewed_on=None)
        del self.judgements["acme:1"]["reviewed_on"]
        r = self.run_score()["roles"][0]
        self.assertEqual(r["scores"]["D1"]["score"], 2)
        self.assertEqual(r["scores"]["D2"]["score"], 2)  # review older than the judgement does not count
        self.assertEqual(r["awaiting_review"], ["D1", "D2", "D4"])
        self.judgements["acme:1"]["reviewed_on"] = TODAY
        self.judgements["acme:1"]["D2"]["reviewed_on"] = TODAY
        r = self.run_score()["roles"][0]
        self.assertEqual((r["scores"]["D1"]["score"], r["scores"]["D2"]["score"]), (4, 4))
        self.assertEqual(r["awaiting_review"], [])

    def test_threshold_configurable(self):
        self.cfg["scoring"]["review_required_above"] = 5
        self.judge("acme:1", e(4, ["E01"]), e(0, []), e(0, []))
        del self.judgements["acme:1"]["reviewed_on"]
        self.assertEqual(self.run_score()["roles"][0]["scores"]["D1"]["score"], 4)


class RuleTests(Base):
    def test_hard_requirement_lacking(self):
        self.judge("acme:1", e(4, ["E02"]), e(5, ["E01"]), e(5, ["E01"]), hard_requirement_lacking=True,
                   hard_requirement_note="CS degree")
        self.profile["D3"]["default"] = e(4, ["E01"])
        r = self.run_score()["roles"][0]
        self.assertEqual(r["scores"]["D1"]["score"], 1)
        # fit = 5 + 20 + 16 + 10 + 0 + 10 + 0 = 61: Moderate/Low; referral up, lacking down -> Moderate/Very low
        self.assertEqual(r["fit"], 61.0)
        self.assertEqual((r["interview_band"], r["offer_band"]), ("Moderate", "Very low"))
        self.assertTrue(any("CS degree" in a for a in r["adjustments"]))

    def test_eligibility_blockers(self):
        self.roles = [role("acme:1", blockers=["us_person_export_control"]), role("acme:2", blockers=["licence"]),
                      role("acme:3", blockers=["security_clearance"])]
        self.cfg["candidate"]["eligibility_cleared"] = ["licence"]
        for rid in ("acme:1", "acme:2", "acme:3"):
            self.judge(rid, e(3, ["E02"]), e(0, []), e(0, []))
        self.judgements["acme:3"]["eligibility_blocked"] = False  # the scorer overrides a false positive
        by_id = {r["role_id"]: r for r in self.run_score()["roles"]}
        self.assertTrue(by_id["acme:1"]["eligibility_blocked"])
        self.assertEqual(by_id["acme:1"]["scores"]["D6"]["score"], 0)
        self.assertEqual(by_id["acme:1"]["scores"]["D1"]["score"], 1)
        self.assertTrue(by_id["acme:1"]["hard_requirement_lacking"])
        self.assertFalse(by_id["acme:2"]["eligibility_blocked"])
        self.assertEqual(by_id["acme:2"]["scores"]["D6"]["score"], 5)
        self.assertFalse(by_id["acme:3"]["eligibility_blocked"])

    def test_hard_eligibility_block_counts_as_blocked(self):
        self.judge("acme:1", e(3, ["E02"]), e(0, []), e(0, []), hard_eligibility_block=True)
        r = self.run_score()["roles"][0]
        self.assertTrue(r["eligibility_blocked"])
        self.assertEqual(r["scores"]["D6"]["score"], 0)

    def test_best_location_class_and_override(self):
        self.roles = [role("acme:1", classes=("us", "australia_nz")), role("acme:2", classes=("us", "australia_nz"))]
        self.judge("acme:1", e(0, []), e(0, []), e(0, []))
        self.judge("acme:2", e(0, []), e(0, []), e(0, []), location_class="us")
        by_id = {r["role_id"]: r for r in self.run_score()["roles"]}
        self.assertEqual((by_id["acme:1"]["location_class"], by_id["acme:1"]["scores"]["D6"]["score"]), ("australia_nz", 5))
        self.assertEqual((by_id["acme:2"]["location_class"], by_id["acme:2"]["scores"]["D6"]["score"]), ("us", 2))

    def test_unjudged_and_heavy_coding(self):
        self.roles = [role("acme:1"), role("acme:2", heavy=True)]
        by_id = {r["role_id"]: r for r in self.run_score()["roles"]}
        self.assertFalse(by_id["acme:1"]["judged"])
        self.assertEqual([by_id["acme:1"]["scores"][d]["score"] for d in ("D1", "D2", "D4")], [0, 0, 0])
        self.assertFalse(by_id["acme:1"]["hard_requirement_lacking"])
        self.assertTrue(by_id["acme:2"]["hard_requirement_lacking"])
        self.cfg["candidate"]["writes_production_code"] = True
        by_id = {r["role_id"]: r for r in self.run_score()["roles"]}
        self.assertFalse(by_id["acme:2"]["hard_requirement_lacking"])

    def test_per_org_gaps_and_questions(self):
        self.roles = [role("acme:1"), role("acme:2", family="product"), role("acme:3")]
        self.judge("acme:1", e(3, ["E02"]), e(2, ["E01"]), e(1, ["E01"]))
        self.judge("acme:2", e(1, ["E02"]), e(2, ["E01"]), e(1, ["E01"]), hard_requirement_lacking=True)
        self.judge("acme:3", e(2, ["E02"]), e(3, ["E01"]), e(1, ["E01"]))
        self.gaps = [{"id": "intro", "title": "Warm intro", "dimension": "D3", "target_score": 3},
                     {"id": "d1", "title": "Requirements", "dimension": "D1", "target_score": 3},
                     {"id": "tpm-only", "title": "TPM proof", "dimension": "D2", "target_score": 3, "families": ["tpm"]},
                     {"id": "globex", "title": "Globex only", "dimension": "D2", "target_score": 5, "orgs": ["globex"]}]
        run = self.run_score()
        self.assertEqual(run["per_org"]["acme"]["role_id"], "acme:1")
        self.assertIsNone(run["per_org"]["globex"])
        gaps = {g["id"]: g for g in run["gaps"]}
        self.assertEqual((gaps["intro"]["points_gain"], gaps["intro"]["roles_affected"]), (36.0, 3))
        self.assertEqual((gaps["d1"]["points_gain"], gaps["d1"]["roles_affected"]), (5.0, 1))  # lacking role capped at 1
        self.assertEqual((gaps["tpm-only"]["points_gain"], gaps["tpm-only"]["roles_affected"]), (4.0, 1))
        self.assertEqual(gaps["globex"]["points_gain"], 0.0)
        self.assertEqual(run["gaps"][0]["id"], "intro")
        qs = run["verify_to_unlock"]
        self.assertEqual([q["source"] for q in qs], ["open_question", "unverified_evidence"])
        self.assertEqual(qs[1]["id"], "E05")
        self.assertEqual(run["outlook"]["band"], "Not yet judged")

    def test_deterministic_and_valid(self):
        self.roles = [role("acme:1"), role("acme:2", classes=("us",))]
        self.judge("acme:1", e(3, ["E02"]), e(2, ["E01"]), e(1, ["E01"]))
        a = json.dumps(self.run_score(), indent=2)
        b = json.dumps(self.run_score(), indent=2)
        self.assertEqual(a, b)
        run = json.loads(a)
        self.assertEqual(V.check(run, H.schema("run.schema.json")), [])
        self.assertTrue(run["inputs_digest"].startswith("sha256:"))
        self.assertEqual(run["counts"]["not_judged"], 1)


class PartiallyVerifiedTests(Base):
    """Some facts in the claim checked, some not: between self-reported and corroborated, never above corroborated."""

    def test_caps_by_kind(self):
        self.judge("acme:1", e(4, ["E09"]), e(4, ["E08"]), e(4, ["E08", "E04"]))
        r = self.run_score()["roles"][0]
        self.assertEqual(r["scores"]["D1"]["score"], 3)  # job history: what self-reported supports (3)
        self.assertEqual(r["scores"]["D2"]["score"], 2)  # achievement: lifted from 1 to the partial cap, 2
        self.assertEqual(r["scores"]["D4"]["score"], 2)  # the best cited item counts
        self.assertIn("partially verified achievement, which supports at most 2", r["scores"]["D2"]["capped"])

    def test_cap_is_configurable_and_never_above_corroborated(self):
        self.cfg["scoring"]["partially_verified_cap"] = 1
        self.judge("acme:1", e(2, ["E02"]), e(4, ["E08"]), e(1, ["E01"]))
        self.assertEqual(self.run_score()["roles"][0]["scores"]["D2"]["score"], 1)
        kinds = ["job_history", "education", "eligibility", "preference", "achievement", "artefact", "other"]
        for self_cap in range(6):
            caps = {k: self_cap for k in kinds}
            caps["default"] = self_cap
            for partial in range(5):
                for kind in kinds:
                    got = S.level_cap("partially_verified", kind, caps, partial)
                    self.assertLessEqual(got, S.level_cap("corroborated", kind, caps, partial))
                    self.assertGreaterEqual(got, min(self_cap, 4))       # never below self-reported, unless that is above 4
                    self.assertGreaterEqual(got, min(partial, 4))

    def test_eligibility_partial_is_flagged(self):
        ev = H.deep(EVIDENCE)
        ev["items"].append({"id": "E30", "claim": "lives here, partly checked", "kind": "eligibility",
                            "level": "partially_verified", "sources": [{"type": "interview", "ref": "intake/answers.md"}]})
        H.save(os.path.join(self.ws, "profile", "evidence.json"), ev)
        errors, warnings, _ = V.validate_workspace(self.ws)
        self.assertEqual(errors, [])
        self.assertTrue(any("E30 is partially_verified, which supports at most 4" in w for w in warnings))


class EvidenceIdTests(Base):
    def test_source_prefixed_ids_score_and_validate(self):
        self.judge("acme:1", e(2, ["E02"]), e(4, ["G01"]), e(1, ["G01"]))
        run = self.run_score()
        self.assertEqual(run["roles"][0]["scores"]["D2"]["score"], 4)  # verified G01; review cap holds above 2
        self.assertFalse([w for w in run["warnings"] if "G01" in w])
        errors, _, _ = V.validate_workspace(self.ws)
        self.assertEqual(errors, [])

    def test_pattern(self):
        rx = H.C.EVIDENCE_ID
        for good in ("E01", "E1", "G01", "ABC123", "E901"):
            self.assertRegex(good, rx)
        for bad in ("e01", "ABCD1", "E", "E1a", "01", "E-01", "Q01x"):
            self.assertNotRegex(bad, rx)

    def test_every_schema_reference_uses_the_shared_pattern(self):
        found = []

        def walk(node, path):
            if isinstance(node, dict):
                pat = node.get("pattern")
                where = path.split(":", 1)[1]
                if pat and ("evidence" in where or (path.startswith("evidence.") and where.endswith("item.properties.id"))):
                    found.append((path, pat))
                for k, v in node.items():
                    walk(v, path + "." + k)
            elif isinstance(node, list):
                for v in node:
                    walk(v, path)
        for name in sorted(os.listdir(os.path.join(H.ENGINE, "schemas"))):
            text = json.dumps(H.schema(name))
            self.assertNotIn("^E[0-9]", text, name)
            walk(H.schema(name), name + ":")
        self.assertGreaterEqual(len(found), 10)
        for path, pat in found:
            self.assertEqual(pat, H.C.EVIDENCE_ID, path)

    def test_confusing_prefix_warns(self):
        ev = H.deep(EVIDENCE)
        ev["items"].append({"id": "D3", "claim": "looks like a factor code", "kind": "other", "level": "verified",
                            "sources": [{"type": "other", "ref": "x"}]})
        H.save(os.path.join(self.ws, "profile", "evidence.json"), ev)
        _, warnings, _ = V.validate_workspace(self.ws)
        self.assertTrue(any("evidence id D3 starts with D" in w for w in warnings))


class GapPoolTests(Base):
    def setUp(self):
        super().setUp()
        # Acme has the three best roles; Globex's only role is outside an overall top 2.
        self.roles = [role("acme:1"), role("acme:2"), role("acme:3"), role("globex:1", org="globex")]
        for rid in ("acme:1", "acme:2", "acme:3"):
            self.judge(rid, e(3, ["E02"]), e(2, ["E01"]), e(1, ["E01"]))
        self.judge("globex:1", e(1, ["E02"]), e(1, ["E01"]), e(1, ["E01"]))
        self.cfg["scoring"]["top_n_for_gaps"] = 2
        self.gaps = [{"id": "intro-globex", "title": "Warm intro at Globex", "dimension": "D3", "target_score": 3,
                      "orgs": ["globex"]},
                     {"id": "intro-all", "title": "Warm intro everywhere", "dimension": "D3", "target_score": 3}]

    def test_default_is_one_overall_pool(self):
        gaps = {g["id"]: g for g in self.run_score()["gaps"]}
        self.assertEqual((gaps["intro-globex"]["points_gain"], gaps["intro-globex"]["roles_affected"]), (0.0, 0))
        self.assertEqual((gaps["intro-all"]["points_gain"], gaps["intro-all"]["roles_affected"]), (24.0, 2))
        self.assertNotIn("pool", gaps["intro-all"])          # the run file is unchanged for existing workspaces
        self.assertNotIn("by_org", gaps["intro-all"])

    def test_per_org_pool_counts_every_organisation(self):
        self.cfg["scoring"]["gap_pool"] = "per_org"
        self.cfg["scoring"]["top_n_per_org_for_gaps"] = 2
        run = self.run_score()
        gaps = {g["id"]: g for g in run["gaps"]}
        self.assertEqual((gaps["intro-globex"]["points_gain"], gaps["intro-globex"]["roles_affected"]), (12.0, 1))
        self.assertEqual(gaps["intro-globex"]["by_org"], {"globex": {"points_gain": 12.0, "roles_affected": 1}})
        g = gaps["intro-all"]
        self.assertEqual((g["points_gain"], g["roles_affected"], g["pool"]), (36.0, 3, "per_org"))  # 2 at Acme, 1 at Globex
        self.assertEqual(g["by_org"], {"acme": {"points_gain": 24.0, "roles_affected": 2},
                                       "globex": {"points_gain": 12.0, "roles_affected": 1}})
        self.assertEqual(V.check(run, H.schema("run.schema.json")), [])

    def test_per_org_size_defaults_to_top_n(self):
        self.cfg["scoring"]["gap_pool"] = "per_org"
        self.cfg["scoring"]["top_n_for_gaps"] = 3
        gaps = {g["id"]: g for g in self.run_score()["gaps"]}
        self.assertEqual(gaps["intro-all"]["by_org"]["acme"]["roles_affected"], 3)
        errors, _, _ = V.validate_workspace(self.ws)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
