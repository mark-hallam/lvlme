"""fetch_roles.py: adapters against saved job-board JSON, classification, flags, snapshots. No network."""
import os
import shutil
import unittest
from unittest import mock

import helpers as H
import fetch_roles as F
import validate as V
from _common import matches_any

CFG = H.template_config()
GH = H.load(os.path.join(H.FIXTURES, "ats", "greenhouse.json"))
AB = H.load(os.path.join(H.FIXTURES, "ats", "ashby.json"))
LV = H.load(os.path.join(H.FIXTURES, "ats", "lever.json"))
TARGET = {"id": "t", "name": "Acme AI", "ats": "greenhouse"}


def built(postings):
    """{title: (role, exclusion reason)} for every posting."""
    out = {}
    for base in postings:
        out[base["title"]] = F.build_role(TARGET, base, CFG)
    return out


class KeywordTests(unittest.TestCase):
    def test_word_start_and_short_keywords(self):
        self.assertTrue(matches_any(["program manag"], "Senior Program Management Lead"))
        self.assertTrue(matches_any(["tpm"], "Senior TPM, Infrastructure"))
        self.assertFalse(matches_any(["tpm"], "Atpmx coordinator"))
        self.assertFalse(matches_any(["us"], "Business Operations"))
        self.assertTrue(matches_any(["us"], "Remote, US"))
        self.assertTrue(matches_any([r"re:,\s*(ca|ny)\b"], "San Mateo, CA"))
        self.assertFalse(matches_any(["policy"], ""))

    def test_classify_order_excludes_and_department_fallback(self):
        self.assertEqual(F.classify("Technical Program Manager, Launches", [], CFG)[0], "tpm")
        fam, note, reason = F.classify("Program Manager, Recruiting", [], CFG)
        self.assertIsNone(fam)
        self.assertIn("exclude", reason)  # global exclude wins, and is logged because a family matched
        self.assertEqual(F.classify("Recruiter", [], CFG), (None, None, None))
        fam, note, _ = F.classify("Member of Staff", ["Safeguards"], CFG)
        self.assertEqual(fam, "policy_safety")
        self.assertIn("department", note)
        self.assertIsNone(F.classify("Policy Engineer", [], CFG)[0])  # family exclude, no other family

    def test_negated_coding_does_not_count(self):
        heavy, signals = F.coding_check("Deployment Lead", "You will not write production code.")
        self.assertFalse(heavy)
        self.assertTrue(any(s.startswith("NOT required") for s in signals))
        self.assertTrue(F.coding_check("Lead", "You will write production code daily.")[0])


class AdapterTests(unittest.TestCase):
    def test_greenhouse(self):
        roles = built(F.greenhouse_postings(GH))
        tpm, _ = roles["Technical Program Manager, Model Launches"]
        self.assertEqual(tpm["family"], "tpm")
        self.assertEqual(tpm["locations"], ["San Francisco, CA", "Sydney, Australia"])
        self.assertEqual(tpm["location_classes"], ["australia_nz", "us"])
        self.assertEqual(tpm["compensation"], "$190,000 to $240,000 USD")
        self.assertEqual((tpm["years_experience"], tpm["years_experience_basis"]), (5, "required"))
        self.assertTrue(any("5+ years" in h for h in tpm["hard_requirements"]))
        self.assertEqual(tpm["eligibility_blockers"], [])
        self.assertIs(tpm["remote"], False)
        self.assertEqual(tpm["id"], "t:4100001")

        fde, why = roles["Forward Deployed Engineer"]
        self.assertIsNone(fde)
        self.assertIn("production coding", why)

        self.assertEqual(roles["Recruiter, Technical"], (None, None))

        gov, _ = roles["Program Manager, Government Partnerships"]
        self.assertEqual({b["type"] for b in gov["eligibility_blockers"]},
                         {"us_person_export_control", "security_clearance"})

        ts, _ = roles["Trust & Safety Specialist"]
        self.assertEqual(ts["family"], "policy_safety")
        self.assertEqual([b["type"] for b in ts["eligibility_blockers"]], ["citizenship"])
        self.assertIs(ts["remote"], True)
        self.assertEqual(ts["location_classes"], ["remote"])

    def test_ashby(self):
        postings = list(F.ashby_postings(AB))
        self.assertNotIn("Chief of Staff, Research", [p["title"] for p in postings])  # unlisted
        roles = built(postings)
        pm, _ = roles["Product Manager, Developer Platform"]
        self.assertEqual(pm["family"], "product")
        self.assertIs(pm["remote"], True)
        self.assertEqual(pm["compensation"], "$170K to $210K")
        self.assertEqual(pm["location_classes"], ["remote"])
        tpm, _ = roles["Technical Program Manager, Infrastructure"]
        self.assertEqual(tpm["locations"], ["Seattle, WA", "Toronto, Canada"])
        self.assertEqual(tpm["location_classes"], ["us", "canada"])
        self.assertFalse(tpm["requires_heavy_coding"])
        sa, why = roles["Solutions Architect"]
        self.assertIsNone(sa)
        self.assertIn("production coding", why)

    def test_lever(self):
        roles = built(F.lever_postings(LV))
        fleet, _ = roles["Program Manager, Robot Fleet Deployments"]
        self.assertEqual(fleet["family"], "tpm")
        self.assertEqual(fleet["compensation"], "AUD 150,000 to 180,000 per year salary")
        self.assertEqual(fleet["location_classes"], ["australia_nz"])
        self.assertEqual(fleet["years_experience"], 4)
        self.assertIs(fleet["remote"], False)
        self.assertTrue(fleet["published_at"].startswith("2025-") or fleet["published_at"].startswith("2026-"))
        auto, _ = roles["Product Manager, Warehouse Autonomy"]
        self.assertEqual([b["type"] for b in auto["eligibility_blockers"]], ["licence"])
        cs, _ = roles["Customer Success Manager, Fleet Operations"]
        self.assertEqual(cs["family"], "applied_ai")
        self.assertIs(cs["remote"], False)

    def test_location_classes_remote_rule(self):
        lc = F.location_classes
        self.assertEqual(lc(["Remote, US"], True, CFG), ["us"])
        self.assertEqual(lc(["Remote"], True, CFG), ["remote"])
        self.assertEqual(lc([], True, CFG), ["remote"])
        self.assertEqual(lc(["Mars Base One"], False, CFG), ["other"])
        self.assertEqual(lc(["London", "Sydney"], False, CFG), ["australia_nz", "uk_eu"])

    def test_endpoints(self):
        self.assertEqual(F.endpoint({"id": "x", "ats": "lever", "slug": "co", "region": "eu"}),
                         "https://api.eu.lever.co/v0/postings/co?mode=json")
        self.assertIn("boards-api.greenhouse.io/v1/boards/co/jobs", F.endpoint({"id": "x", "ats": "greenhouse", "slug": "co"}))
        self.assertIn("api.ashbyhq.com/posting-api/job-board/co", F.endpoint({"id": "x", "ats": "ashby", "slug": "co"}))
        self.assertIsNone(F.endpoint({"id": "x", "ats": "manual"}))


class MainTests(unittest.TestCase):
    def setUp(self):
        cfg = H.template_config()
        cfg["targets"] = [{"id": "gh", "name": "Acme AI", "ats": "greenhouse", "slug": "acme"},
                          {"id": "ab", "name": "Globex Labs", "ats": "ashby", "slug": "globex"},
                          {"id": "lv", "name": "Initech Robotics", "ats": "lever", "slug": "initech"},
                          {"id": "mn", "name": "Hand Entered Co", "ats": "manual"}]
        self.ws = H.new_workspace(self, cfg)
        self.fx = os.path.join(os.path.dirname(self.ws), "fixtures")
        os.makedirs(self.fx)
        for src, dst in (("greenhouse", "gh"), ("ashby", "ab"), ("lever", "lv")):
            shutil.copy(os.path.join(H.FIXTURES, "ats", src + ".json"), os.path.join(self.fx, dst + ".json"))
        H.save(os.path.join(self.ws, "market", "roles", "manual.json"), {"postings": [
            {"org": "mn", "id": "m1", "title": "Program Manager, Field Operations", "locations": ["Perth, Australia"],
             "url": "https://example.com/m1", "description": "Requirements\n3+ years of program management"}]})

    def run_main(self, date):
        with mock.patch("sys.stdout"):
            return F.main(["--workspace", self.ws, "--fixtures", self.fx, "--date", date])

    def test_offline_run_snapshots_and_velocity(self):
        self.assertEqual(self.run_main("2026-11-01"), 0)
        latest = H.load(os.path.join(self.ws, "market", "roles", "latest.json"))
        self.assertEqual(V.check(latest, H.schema("roles.schema.json")), [])
        ids = {r["id"] for r in latest["roles"]}
        self.assertIn("mn:m1", ids)
        self.assertIn("gh:4100001", ids)
        self.assertEqual(latest["summary"]["endpoint_errors"], {})
        self.assertEqual(latest["summary"]["previous_snapshot"], None)
        self.assertTrue(os.path.exists(os.path.join(self.ws, "market", "roles", "snapshots", "2026-11-01.json")))

        gh = H.load(os.path.join(self.fx, "gh.json"))
        gh["jobs"] = [j for j in gh["jobs"] if j["id"] != 4100001]
        H.save(os.path.join(self.fx, "gh.json"), gh)
        self.assertEqual(self.run_main("2026-11-02"), 0)
        latest = H.load(os.path.join(self.ws, "market", "roles", "latest.json"))
        self.assertEqual(latest["summary"]["previous_snapshot"], "2026-11-01")
        self.assertEqual(latest["summary"]["closed_role_ids"], ["gh:4100001"])
        self.assertEqual(latest["summary"]["new_role_ids"], [])
        self.assertTrue(all(r["first_seen"] == "2026-11-01" for r in latest["roles"]))

    def test_network_failure_keeps_previous_file(self):
        self.assertEqual(self.run_main("2026-11-01"), 0)
        before = H.load(os.path.join(self.ws, "market", "roles", "latest.json"))
        with mock.patch.object(F.time, "sleep"), mock.patch("sys.stdout"), mock.patch("sys.stderr"):
            code = F.main(["--workspace", self.ws, "--date", "2026-11-02"])  # live mode, network blocked
        latest = H.load(os.path.join(self.ws, "market", "roles", "latest.json"))
        # The manual target still works, so the run completes, keeping the last known roles for the failed boards.
        self.assertEqual(code, 0)
        self.assertEqual(set(latest["summary"]["endpoint_errors"]), {"gh", "ab", "lv"})
        self.assertEqual({r["id"] for r in latest["roles"]}, {r["id"] for r in before["roles"]})
        self.assertEqual(latest["summary"]["closed_role_ids"], [])


if __name__ == "__main__":
    unittest.main()
