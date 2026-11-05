"""fetch_roles.py: adapters against saved job-board JSON, classification, flags, snapshots. No network."""
import json
import os
import shutil
import unittest
from unittest import mock

import helpers as H
import fetch_roles as F
import validate as V
from _common import matches_any

CFG = H.example_config()
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


def gh_job(jid, title, dept, body="<p>You will plan launches with research and product teams across the company.</p>"):
    import html as _html
    return {"id": jid, "title": title, "updated_at": "2026-10-20T10:00:00-04:00", "location": {"name": "Sydney, Australia"},
            "absolute_url": "https://example.com/jobs/acme/%s" % jid, "content": _html.escape(body),
            "departments": [{"id": 1, "name": dept}], "offices": [], "first_published": "2026-09-29T09:00:00-04:00",
            "company_name": "Acme AI"}


class EngineeringTitles(unittest.TestCase):
    """With the example config (writes_production_code false), engineering jobs and construction projects stay out."""

    def test_engineering_and_construction_titles_stay_out_of_the_market(self):
        jobs = [gh_job(1, "Android Engineer, Plugin Developer Platform", "Applied AI"),
                gh_job(2, "Full-Stack Engineer, ChatGPT Education & Learning", "Applied AI"),
                gh_job(3, "Machine Learning Engineer, Monetization AI/ML", "Applied AI"),
                gh_job(4, "ChatGPT Performance Engineer", "Applied AI"),
                gh_job(5, "Engineering Manager, Agent Platform", "Applied AI"),
                gh_job(6, "Sr. Construction Project Manager, Electrical Infrastructure - Memphis", "Data Centers"),
                gh_job(7, "Project Manager, Design and Construction, R&D/Lab Buildouts", "Workplace"),
                gh_job(8, "Deployment Engineer, Public Sector", "Applied AI"),
                gh_job(9, "Deployment Lead, Applied AI", "Applied AI"),
                gh_job(10, "Technical Program Manager, Model Launches", "Technical Program Management"),
                gh_job(11, "Technical Success Engineer", "Technical Success",
                       "<h3>Responsibilities</h3><ul><li>You will not write production code; you guide customers through launches.</li></ul>")]
        roles = built(F.greenhouse_postings({"jobs": jobs}))
        for title in [j["title"] for j in jobs[:8]]:
            role, why = roles[title]
            self.assertIsNone(role, title)
        self.assertIn("production coding", roles["Deployment Engineer, Public Sector"][1])  # dropped by its title
        for title in ("Deployment Lead, Applied AI", "Technical Program Manager, Model Launches"):
            self.assertFalse(roles[title][0]["requires_heavy_coding"], title)
        kept = roles["Technical Success Engineer"][0]                 # the posting says no production code
        self.assertFalse(kept["requires_heavy_coding"])
        coder = dict(CFG, candidate=dict(CFG["candidate"], writes_production_code=True))
        role, _ = F.build_role(TARGET, next(F.greenhouse_postings({"jobs": [jobs[7]]})), coder)
        self.assertIsNotNone(role)                                     # someone who codes keeps engineering roles
        self.assertFalse(role["requires_heavy_coding"])
        self.assertTrue(F.engineering_title("Software Engineer II"))
        self.assertFalse(F.engineering_title("Engineer Relations Lead"))
        self.assertFalse(F.engineering_title("Technical Program Manager, Engineering"))

    def test_non_software_engineer_and_developer_titles_are_not_coding_jobs(self):
        for title in ("Civil Engineer", "Civil Infrastructure Engineer", "Infrastructure Engineer",
                      "Site Engineer", "Maintenance Engineer", "Biomedical Engineer", "Property Developer",
                      "Engineering Manager, Facilities", "Senior Engineering Manager, Civil Works",
                      "Project Engineer", "Chemical Engineer"):
            with self.subTest(title=title):
                self.assertFalse(F.engineering_title(title))
        for title in ("Software Engineer", "Backend Developer", "Site Reliability Engineer",
                      "Software Quality Engineer"):
            with self.subTest(title=title):
                self.assertTrue(F.engineering_title(title))

    def test_posting_blurb_does_not_make_field_engineer_a_coding_title(self):
        blurb = (
            "plant performance targets, deployment of the programme, and batches of 50 ml samples."
        )
        for title in ("Project Engineer", "Chemical Engineer"):
            with self.subTest(title=title):
                self.assertFalse(F.engineering_title(title, blurb))

    def test_non_software_engineer_roles_are_not_heavy_coding_from_title(self):
        body = "<h3>Requirements</h3><ul><li>5+ years of field experience.</li></ul>"
        cfg = H.deep(CFG)
        cfg["families"].append({
            "id": "field_engineering",
            "name": "Field engineering",
            "title_keywords": [],
            "department_keywords": ["Operations"],
            "drop_if_heavy_coding": False,
        })
        for title in ("Civil Engineer", "Site Engineer", "Maintenance Engineer",
                      "Biomedical Engineer", "Property Developer"):
            with self.subTest(title=title):
                base = next(F.greenhouse_postings({"jobs": [gh_job(99, title, "Operations", body)]}))
                role, _ = F.build_role(TARGET, base, cfg)
                self.assertIsNotNone(role, title)
                self.assertFalse(role["requires_heavy_coding"], title)
                self.assertFalse(F.engineering_title(title, base["raw_html"]))


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

    def test_ashby_hybrid_with_is_remote_true_is_not_remote(self):
        # Ashby sends isRemote true with workplaceType Hybrid for office based roles (514 such jobs on
        # one live board). The workplace label wins, so a hybrid London role is never called remote.
        job = json.loads(json.dumps(AB["jobs"][1]))
        job.update({"id": "g-hyb", "location": "London, UK", "secondaryLocations": [],
                    "isRemote": True, "workplaceType": "Hybrid"})
        base = next(F.ashby_postings({"jobs": [job]}))
        role, _ = F.build_role(TARGET, base, CFG)
        self.assertIs(role["remote"], False)
        self.assertEqual(role["workplace"], "Hybrid")
        self.assertNotIn("remote", role["location_classes"])
        job.update({"workplaceType": "OnSite"})
        role, _ = F.build_role(TARGET, next(F.ashby_postings({"jobs": [job]})), CFG)
        self.assertEqual((role["remote"], role["workplace"]), (False, "Onsite"))
        job.update({"workplaceType": None})  # no label: the flag decides
        role, _ = F.build_role(TARGET, next(F.ashby_postings({"jobs": [job]})), CFG)
        self.assertEqual((role["remote"], role["workplace"]), (True, None))

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
        cfg = H.example_config()
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

    def test_total_failure_writes_status_and_keeps_latest_data_date(self):
        self.assertEqual(self.run_main("2026-11-01"), 0)
        with mock.patch.object(F, "collect", return_value=([], [], 0, {"gh": "offline", "ab": "offline", "lv": "offline"}, {}, [])):
            with mock.patch("sys.stderr"):
                self.assertEqual(F.main(["--workspace", self.ws, "--date", "2026-11-02"]), 1)
        status = H.load(os.path.join(self.ws, "market", "roles", "fetch-status.json"))
        self.assertEqual(status, {"date": "2026-11-02", "ok": False,
                                  "board_errors": {"gh": "offline", "ab": "offline", "lv": "offline"},
                                  "data_date": "2026-11-01"})

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

    def test_blocker_counts_say_which_eligibility_questions_matter(self):
        """The interview asks the export control and clearance questions only when an open role needs them."""
        with mock.patch("sys.stdout") as out:
            self.assertEqual(F.main(["--workspace", self.ws, "--fixtures", self.fx, "--date", "2026-11-01"]), 0)
        latest = H.load(os.path.join(self.ws, "market", "roles", "latest.json"))
        counts = latest["summary"]["blocker_counts"]
        self.assertEqual(list(counts), ["us_person_export_control", "security_clearance", "citizenship", "licence"])
        for kind, n in counts.items():
            with self.subTest(kind=kind):
                self.assertEqual(n, sum(1 for r in latest["roles"]
                                        if kind in {b["type"] for b in r["eligibility_blockers"]}))
        self.assertGreaterEqual(counts["us_person_export_control"], 1)   # the government partnerships role
        self.assertGreaterEqual(counts["security_clearance"], 1)
        printed = json.loads("".join(c.args[0] for c in out.write.call_args_list))
        self.assertEqual(printed["blocker_counts"], counts)
        self.assertEqual(V.check(latest, H.schema("roles.schema.json")), [])

    def test_blocker_counts_count_a_role_once_and_list_every_type(self):
        roles = [{"eligibility_blockers": [{"type": "security_clearance", "text": "a"},
                                           {"type": "security_clearance", "text": "b"}]},
                 {"eligibility_blockers": []}, {}]
        self.assertEqual(F.blocker_counts(roles), {"us_person_export_control": 0, "security_clearance": 1,
                                                   "citizenship": 0, "licence": 0})

    def test_no_targets_stops_with_one_line(self):
        cfg = H.load(os.path.join(self.ws, "config.json"))
        cfg["targets"] = []
        H.save(os.path.join(self.ws, "config.json"), cfg)
        with mock.patch("sys.stdout"), mock.patch("sys.stderr") as err:
            self.assertEqual(F.main(["--workspace", self.ws, "--fixtures", self.fx, "--date", "2026-11-01"]), 1)
        printed = "".join(c.args[0] for c in err.write.call_args_list)
        self.assertEqual(printed.strip(), "No target organisations yet. Say to your agent: run the LVLme interview.")
        self.assertFalse(os.path.exists(os.path.join(self.ws, "market", "roles", "latest.json")))

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
