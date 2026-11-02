"""consistency_audit.py: month parsing, each finding type, the suggested truth, the CLI and the schemas."""
import datetime as dt
import io
import os
import shutil
import tempfile
import unittest
from unittest import mock

import helpers as H
import consistency_audit as CA
import validate as V

TODAY = dt.date(2026, 11, 2)
EXAMPLE = os.path.join(H.ENGINE, "examples", "consistency")


def rec(org, title, start, end, **extra):
    r = {"organisation": org, "title": title, "start": start, "end": end}
    r.update(extra)
    return r


def doc(**sources):
    out = {"schema_version": 1, "sources": {}}
    for sid, value in sources.items():
        out["sources"][sid] = {"records": value} if isinstance(value, list) else value
    return out


def audit(d, **kw):
    return CA.run_audit(d, today=TODAY, **kw)


def of_type(report, kind):
    return [f for f in report["findings"] if f["type"] == kind]


def fixes_for(report, source):
    return [x for x in report["fixes"] if x["source"] == source]


class MonthParsingTests(unittest.TestCase):
    def test_formats(self):
        cases = {"Oct 2007": (2007, 10), "October 2007": (2007, 10), "oct. 2007": (2007, 10),
                 "Sept 2007": (2007, 9), "2007-10": (2007, 10), "2007-10-15": (2007, 10), "10/2007": (2007, 10),
                 "2007/10": (2007, 10), "2007": (2007, None), "15 Oct 2007": (2007, 10), "Oct 15, 2007": (2007, 10),
                 "Present": CA.ONGOING, "current": CA.ONGOING, "now": CA.ONGOING}
        for text, expected in cases.items():
            self.assertEqual(CA.parse_month(text), expected, text)
        self.assertIsNone(CA.parse_month(""))
        self.assertIsNone(CA.parse_month(None))

    def test_bad_dates(self):
        for text in ("13/2007", "2007-13", "Smarch 2007", "Octopus 2007", "07", "next year", "1850"):
            with self.assertRaises(ValueError, msg=text):
                CA.parse_month(text)

    def test_differences_respect_precision(self):
        self.assertEqual(CA.date_diff(CA.parse_month("Mar 2012"), CA.parse_month("May 2012")), 2)
        self.assertEqual(CA.date_diff(CA.parse_month("2012"), CA.parse_month("May 2012")), 0)
        self.assertEqual(CA.date_diff(CA.parse_month("2013"), CA.parse_month("Mar 2012")), 12)
        self.assertIsNone(CA.date_diff(CA.ONGOING, CA.parse_month("Mar 2012")))


class TitleTests(unittest.TestCase):
    def test_missing_deputy_is_likely_inflation(self):
        r = audit(doc(cv=[rec("Fabrikam Air", "Deputy Quality Manager", "Jul 2008", "Mar 2012")],
                      linkedin=[rec("Fabrikam Air", "Quality Manager", "Jul 2008", "Mar 2012")]))
        (f,) = of_type(r, "title_mismatch")
        self.assertTrue(f["likely_inflation"])
        self.assertEqual(f["severity"], "high")
        self.assertEqual(f["inflated"], ["Quality Manager"])
        self.assertIn('"Quality Manager" leaves out "Deputy"', f["reason"])
        self.assertEqual(r["roles"][0]["truth"]["title"], "Deputy Quality Manager")
        self.assertTrue(r["roles"][0]["truth"]["needs_confirmation"])
        (fix,) = fixes_for(r, "linkedin")
        self.assertEqual((fix["action"], fix["current"], fix["suggested"]),
                         ("change", "Quality Manager", "Deputy Quality Manager"))
        self.assertEqual(fixes_for(r, "cv"), [])

    def test_modest_title_wins_even_from_a_less_trusted_source(self):
        r = audit(doc(official_form=[rec("Fabrikam Air", "Quality Manager", "Jul 2008", "Mar 2012")],
                      cv=[rec("Fabrikam Air", "Acting Quality Manager", "Jul 2008", "Mar 2012")]))
        self.assertEqual(r["roles"][0]["truth"]["title"], "Acting Quality Manager")
        self.assertEqual(fixes_for(r, "official_form")[0]["action"], "explain")

    def test_confirmed_title_overrides(self):
        r = audit(doc(confirmed=[rec("Fabrikam Air", "Quality Manager", "Jul 2008", "Mar 2012")],
                      cv=[rec("Fabrikam Air", "Deputy Quality Manager", "Jul 2008", "Mar 2012")]))
        t = r["roles"][0]["truth"]
        self.assertEqual((t["title"], t["title_from"], t["needs_confirmation"]), ("Quality Manager", "confirmed", False))
        self.assertEqual(fixes_for(r, "cv")[0]["suggested"], "Quality Manager")

    def test_other_inflation_patterns(self):
        pairs = [("Operations Analyst", "Operations Lead"), ("Quality Manager", "Head of Quality"),
                 ("Engineer", "Senior Engineer"), ("Associate Director", "Director"), ("Co-founder", "Founder"),
                 ("Assistant Manager", "Manager"), ("Acting Head of Quality", "Head of Quality"),
                 ("Vice President, Sales", "President, Sales"), ("Pilot", "Senior Pilot")]
        for modest, raised in pairs:
            r = audit(doc(cv=[rec("Woodgrove Bank", modest, "2016", "2019")],
                          website=[rec("Woodgrove Bank", raised, "2016", "2019")]))
            (f,) = of_type(r, "title_mismatch")
            self.assertTrue(f["likely_inflation"], (modest, raised))
            self.assertEqual(f["inflated"], [raised])
            self.assertEqual(r["roles"][0]["truth"]["title"], modest)

    def test_plain_mismatch_and_same_title(self):
        r = audit(doc(cv=[rec("Fabrikam Air", "Quality Manager", "2008", "2012")],
                      linkedin=[rec("Fabrikam Air", "Safety Manager", "2008", "2012")]))
        (f,) = of_type(r, "title_mismatch")
        self.assertFalse(f["likely_inflation"])
        self.assertEqual(f["severity"], "medium")
        r = audit(doc(cv=[rec("Northwind", "Founder", "2013", "2015")],
                      linkedin=[rec("Northwind", "Founder and Principal Consultant", "2013", "2015")]))
        self.assertFalse(of_type(r, "title_mismatch")[0]["likely_inflation"])
        r = audit(doc(cv=[rec("Fabrikam Air", "Sr. Quality Mgr", "2008", "2012")],
                      linkedin=[rec("Fabrikam Air", "Senior Quality Manager", "2008", "2012")],
                      website=[rec("Fabrikam Air", "Quality Manager (Senior)", "2008", "2012")]))
        self.assertEqual(of_type(r, "title_mismatch"), [])


class DateTests(unittest.TestCase):
    def two(self, cv_end, li_end, **kw):
        return audit(doc(official_form=[rec("Fabrikam Air", "Deputy Quality Manager", "07/2008", "03/2012")],
                         cv=[rec("Fabrikam Air", "Deputy Quality Manager", "Jul 2008", cv_end)],
                         linkedin=[rec("Fabrikam Air", "Deputy Quality Manager", "Jul 2008", li_end)]), **kw)

    def test_end_dates_two_months_apart(self):
        r = self.two("Mar 2012", "May 2012")
        (f,) = of_type(r, "date_mismatch")
        self.assertEqual((f["field"], f["months"], f["severity"]), ("end", 2, "medium"))
        self.assertEqual(r["roles"][0]["truth"]["end"], "2012-03")
        self.assertEqual(r["roles"][0]["truth"]["end_from"], "official_form")
        (fix,) = fixes_for(r, "linkedin")
        self.assertEqual((fix["current"], fix["suggested"]), ("May 2012", "Mar 2012"))
        self.assertEqual(of_type(self.two("Mar 2012", "May 2012", tolerance=2), "date_mismatch"), [])
        self.assertEqual(len(of_type(self.two("Mar 2012", "Apr 2012", tolerance=0), "date_mismatch")), 1)

    def test_current_against_ended_and_large_differences(self):
        f = of_type(self.two("Mar 2012", "present"), "date_mismatch")[0]
        self.assertEqual(f["severity"], "high")
        self.assertNotIn("months", f)
        self.assertEqual(of_type(self.two("Mar 2012", "Oct 2012"), "date_mismatch")[0]["severity"], "high")

    def test_year_precision(self):
        self.assertEqual(of_type(self.two("2012", "Mar 2012"), "date_mismatch"), [])
        self.assertEqual(of_type(self.two("2013", "Mar 2012"), "date_mismatch")[0]["months"], 12)
        r = audit(doc(official_form=[rec("Fabrikam Air", "Deputy Quality Manager", "2008", "2012")],
                      cv=[rec("Fabrikam Air", "Deputy Quality Manager", "Jul 2008", "Mar 2012")]))
        t = r["roles"][0]["truth"]
        self.assertEqual((t["start"], t["start_from"]), ("2008-07", "cv"))


class MissingRoleTests(unittest.TestCase):
    def test_role_only_on_own_pages_is_high(self):
        r = audit(doc(confirmed=[rec("Woodgrove Bank", "Operations Analyst", "Jan 2016", "Aug 2019")],
                      cv=[rec("Woodgrove Bank", "Operations Analyst", "Jan 2016", "Aug 2019")],
                      linkedin=[rec("Woodgrove Bank", "Operations Analyst", "Jan 2016", "Aug 2019"),
                                rec("Adventure Works", "Advisory Board Member", "2018", "2019", concurrent=True)]))
        (f,) = of_type(r, "missing_role")
        self.assertEqual((f["severity"], f["present_in"], f["missing_from"]), ("high", ["linkedin"], ["confirmed", "cv"]))
        self.assertEqual(fixes_for(r, "linkedin")[0]["action"], "remove_or_prove")
        self.assertEqual(fixes_for(r, "confirmed")[0]["action"], "confirm")
        self.assertEqual(fixes_for(r, "cv"), [])  # never spread a role nobody trusted lists

    def test_omission_is_medium_and_covers_window(self):
        form = {"covers": {"from": "2009", "to": "Aug 2019"},
                "records": [rec("Woodgrove Bank", "Operations Analyst", "01/2016", "08/2019")]}
        r = audit(doc(official_form=form,
                      cv=[rec("Fabrikam Air", "Quality Officer", "Feb 2005", "Jun 2008"),
                          rec("Woodgrove Bank", "Operations Analyst", "Jan 2016", "Aug 2019")],
                      linkedin=[rec("Fabrikam Air", "Quality Officer", "Feb 2005", "Jun 2008")],
                      website={"records": []}))
        (f,) = of_type(r, "missing_role")  # Fabrikam is outside the form's period; the website is not complete
        self.assertEqual((f["severity"], f["missing_from"]), ("medium", ["linkedin"]))
        self.assertEqual(fixes_for(r, "linkedin")[0]["action"], "add")


class GapAndOverlapTests(unittest.TestCase):
    def test_gap_between_roles_and_explained_gap(self):
        records = [rec("Fabrikam Air", "Deputy Quality Manager", "Jul 2008", "Mar 2012"),
                   rec("Northwind Consulting", "Founder", "Jan 2013", "present", kind="business")]
        (f,) = of_type(audit(doc(cv=records)), "gap")
        self.assertEqual((f["months"], f["gap"]), (9, {"start": "2012-04", "end": "2012-12", "current": False}))
        self.assertEqual(f["roles"], ["R01", "R02"])
        explained = doc(cv=records)
        explained["explained_gaps"] = [{"start": "Apr 2012", "end": "Dec 2012", "reason": "Full-time study"}]
        self.assertEqual(of_type(audit(explained), "gap"), [])
        self.assertEqual(of_type(audit(doc(cv=records), gap_limit=9), "gap"), [])

    def test_current_gap_and_education_cover(self):
        r = audit(doc(cv=[rec("Fabrikam Air", "Quality Officer", "Feb 2005", "Mar 2025")]))
        (f,) = of_type(r, "gap")
        self.assertTrue(f["gap"]["current"])
        self.assertEqual(f["months"], 20)
        r = audit(doc(cv=[rec("Fabrikam Air", "Quality Officer", "Feb 2005", "Jun 2008"),
                          rec("Example University", "Master of Science", "2008", "2010", kind="education"),
                          rec("Woodgrove Bank", "Operations Analyst", "Jan 2011", "present")]))
        self.assertEqual(of_type(r, "gap"), [])

    def test_overlaps(self):
        base = [rec("Woodgrove Bank", "Operations Analyst", "Jan 2016", "Aug 2019"),
                rec("Tailspin Robotics", "Program Manager", "Feb 2019", "present")]
        (f,) = of_type(audit(doc(cv=base)), "overlap")
        self.assertEqual((f["months"], f["severity"], f["roles"]), (7, "medium", ["R01", "R02"]))
        base[1]["concurrent"] = True
        self.assertEqual(of_type(audit(doc(cv=base)), "overlap"), [])
        handover = [rec("Woodgrove Bank", "Operations Analyst", "Jan 2016", "Aug 2019"),
                    rec("Tailspin Robotics", "Program Manager", "Aug 2019", "present")]
        self.assertEqual(of_type(audit(doc(cv=handover)), "overlap"), [])
        years = [rec("Woodgrove Bank", "Operations Analyst", "2016", "2019"),
                 rec("Tailspin Robotics", "Program Manager", "2019", "present")]
        self.assertEqual(of_type(audit(doc(cv=years)), "overlap"), [])


class ClaimTests(unittest.TestCase):
    def test_single_source_mismatch_and_denied(self):
        r = audit(doc(
            confirmed=[rec("Tailspin Robotics", "Program Manager", "Sep 2019", "present",
                           claims=["Cut supplier defects by 30% in 2022", "Mentored two new analysts"],
                           denies=["Ran the external audit program"])],
            cv=[rec("Tailspin Robotics", "Program Manager", "Sep 2019", "present",
                    claims=["Cut supplier defects by 30% in 2022"])],
            linkedin=[rec("Tailspin Robotics", "Program Manager", "Sep 2019", "present",
                          claims=["Reduced supplier defects by 40 percent in 2022", "Managed a team of 12 engineers",
                                  "Ran the airline's external audit program"])]))
        (single,) = of_type(r, "single_source_claim")
        self.assertEqual((single["claim"], single["sources"], single["has_number"]),
                         ("Managed a team of 12 engineers", ["linkedin"], True))
        (mismatch,) = of_type(r, "claim_mismatch")
        self.assertEqual(mismatch["claim"], "Cut supplier defects by 30% in 2022")
        (denied,) = of_type(r, "denied_claim")
        self.assertEqual((denied["severity"], denied["claim"]), ("high", "Ran the airline's external audit program"))
        actions = sorted(x["action"] for x in fixes_for(r, "linkedin"))
        self.assertEqual(actions, ["change", "prove_or_remove", "remove"])
        self.assertEqual(fixes_for(r, "cv"), [])  # same wording and number as the confirmed claim


class MatchingAndInputTests(unittest.TestCase):
    def test_promotions_stay_separate_and_suffixes_match(self):
        r = audit(doc(official_form=[rec("Fabrikam Air Pty Ltd", "Deputy Quality Manager", "07/2008", "03/2012")],
                      cv=[rec("Fabrikam Air", "Quality Officer", "Feb 2005", "Jun 2008"),
                          rec("Fabrikam Air", "Deputy Quality Manager", "Jul 2008", "Mar 2012")],
                      linkedin=[rec("Fabrikam Air", "Quality Officer", "Feb 2005", "Jun 2008"),
                                rec("Fabrikam Air", "Quality Manager", "Jul 2008", "May 2012")]))
        self.assertEqual(len(r["roles"]), 2)
        self.assertEqual(sorted(r["roles"][1]["seen_in"]), ["cv", "linkedin", "official_form"])

    def test_aliases_and_keys(self):
        d = doc(cv=[rec("Contoso Freight", "Program Manager", "2021", "present", key="pm")],
                linkedin=[rec("Contoso Logistics", "Program Manager", "2019", "present", key="pm")])
        r = audit(d)
        self.assertEqual(len(r["roles"]), 1)
        d = doc(cv=[rec("Contoso Freight", "Program Manager", "2021", "present")],
                linkedin=[rec("Contoso Logistics", "Program Manager", "2021", "present")])
        self.assertEqual(len(audit(d)["roles"]), 2)
        d["organisation_aliases"] = {"Contoso Freight": ["Contoso Logistics"]}
        self.assertEqual(len(audit(d)["roles"]), 1)

    def test_bad_input(self):
        for bad in (doc(cv=[rec("X", "Y", "Smarch 2007", "2008")]), doc(cv=[rec("X", "Y", "2010", "Mar 2009")]),
                    doc(cv=[rec("X", "Y", "present", "2009")]), {"schema_version": 1, "sources": {"cv": {}}},
                    doc(cv=[rec("X", "Y", "2008", "2009", key="k"), rec("X", "Z", "2010", "2011", key="k")])):
            with self.assertRaises(CA.InputError):
                audit(bad)


class CommandLineTests(unittest.TestCase):
    def test_workspace_mode_writes_valid_report(self):
        ws = H.new_workspace(self)
        H.save(os.path.join(ws, "profile", "role-records.json"),
               H.load(os.path.join(EXAMPLE, "role-records.json")))
        with mock.patch("sys.stdout"):
            self.assertEqual(CA.main(["--workspace", ws, "--today", "2026-11-02"]), 0)
        report = H.load(os.path.join(ws, "profile", "consistency.json"))
        self.assertEqual(V.check(report, H.schema("consistency.schema.json")), [])
        self.assertEqual((report["counts"]["high"], report["input"]), (4, "profile/role-records.json"))
        with open(os.path.join(ws, "profile", "consistency.md")) as fh:
            self.assertIn("## Suggested single source of truth", fh.read())

    def test_standalone_prints_and_writes_nothing(self):
        before = sorted(os.listdir(EXAMPLE))
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            self.assertEqual(CA.main(["--input", os.path.join(EXAMPLE, "role-records.json"), "--today", "2026-11-02"]), 0)
        self.assertIn("# Consistency audit", out.getvalue())
        self.assertEqual(sorted(os.listdir(EXAMPLE)), before)

    def test_missing_input_and_bad_input(self):
        ws = H.new_workspace(self)
        with mock.patch("sys.stderr"):
            self.assertEqual(CA.main(["--workspace", ws]), 1)
        bad = os.path.join(ws, "profile", "role-records.json")
        H.save(bad, doc(cv=[rec("X", "Y", "Smarch 2007", "2008")]))
        err = io.StringIO()
        with mock.patch("sys.stderr", err):
            self.assertEqual(CA.main(["--workspace", ws]), 1)
        self.assertIn("cannot read the date", err.getvalue())

    def test_refuses_workspace_inside_engine(self):
        inside = tempfile.mkdtemp(prefix=".consistency-guard-", dir=H.ENGINE)
        self.addCleanup(shutil.rmtree, inside, True)
        H.save(os.path.join(inside, "config.json"), H.template_config())
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit) as ctx:
            CA.main(["--workspace", inside])
        self.assertEqual(ctx.exception.code, 2)

    def test_example_outputs_are_current(self):
        report = CA.run_audit(H.load(os.path.join(EXAMPLE, "role-records.json")), today=TODAY,
                              input_label="role-records.json")
        self.assertEqual(report, H.load(os.path.join(EXAMPLE, "consistency.json")))
        with open(os.path.join(EXAMPLE, "consistency.md"), encoding="utf-8") as fh:
            self.assertEqual(CA.to_markdown(report), fh.read())
        counts = report["counts"]["by_type"]
        for kind in CA.TYPES:
            self.assertIn(kind, counts, kind)  # the example shows every finding type


class SchemaTests(unittest.TestCase):
    def test_inputs_validate(self):
        self.assertEqual(V.check(H.load(os.path.join(EXAMPLE, "role-records.json")),
                                 H.schema("role-records.schema.json")), [])

    def test_recruiter_screen_schema_enforces_independence(self):
        screen = H.load(os.path.join(H.ENGINE, "examples", "recruiter-screen", "2026-11-02.json"))
        schema = H.schema("recruiter-screen.schema.json")
        self.assertEqual(V.check(screen, schema), [])
        peeked = H.deep(screen)
        peeked["independence"]["saw_campaign_scores"] = True
        self.assertTrue(V.check(peeked, schema))
        too_many = H.deep(screen)
        too_many["top_changes"] = [dict(screen["top_changes"][0], rank=min(i, 10)) for i in range(1, 12)]
        self.assertIn("at most 10", "\n".join(V.check(too_many, schema)))
        unquoted = H.deep(screen)
        unquoted["red_flags"][0]["quote"] = ""
        self.assertTrue(V.check(unquoted, schema))


class StyleTests(unittest.TestCase):
    FILES = ["method/INTERVIEW.md", "method/CONSISTENCY.md", "method/RECRUITER_SCREEN.md", "method/PROFILE_FIXES.md",
             "templates/prompts/recruiter-screen.md", "templates/prompts/consistency-sources.md",
             "examples/consistency/consistency.md"]

    def test_no_dashes_as_punctuation(self):
        for rel in self.FILES:
            with open(os.path.join(H.ENGINE, rel), encoding="utf-8") as fh:
                for n, line in enumerate(fh, 1):
                    body = line.strip()
                    if body.startswith("- "):
                        body = body[2:]
                    self.assertNotRegex(body, "[–—]|\\s-\\s|\\s--\\s", "%s:%d" % (rel, n))


if __name__ == "__main__":
    unittest.main()
