"""Is this job still open, and a real opening? Age and repost labels (scripts/_posting_checks.py). No network.

A closed role (gone from a board that answered) and a failed board (never
called closed) are pinned in test_fetch_roles.py; this file pins the labels.
"""
import io
import os
import shutil
import unittest
from unittest import mock

import helpers as H
import _posting_checks as P
import build_dashboard as B
import fetch_roles as F
import validate as V

TODAY = "2026-11-03"


def role(rid="gh:1", title="Program Manager, Launches", published="2026-10-20", org="gh"):
    return {"id": rid, "org": org, "title": title, "published_at": published}


class LabelTests(unittest.TestCase):
    def label(self, r, history=(), ats=None):
        return P.check(r, P.repost_counts(list(history) + [(TODAY, {r["id"]: r})], TODAY), TODAY, ats)

    def test_a_recent_dated_posting_is_likely_real(self):
        self.assertEqual(self.label(role()), {"label": "likely_real", "note": "Open", "age_days": 14, "reposts": 0})

    def test_age_moves_it_to_check_first_then_suspicious(self):
        self.assertEqual(self.label(role(published="2026-07-01"))["note"], "Open, but posted 4 months ago")
        self.assertEqual(self.label(role(published="2026-07-01"))["label"], "check_first")
        old = self.label(role(published="2025-09-03T10:00:00Z"))
        self.assertEqual((old["label"], old["note"]), ("suspicious", "Open, but posted 14 months ago"))

    def test_no_date_is_check_first_never_suspicious(self):
        c = self.label(role(published=None))
        self.assertEqual((c["label"], c["note"], c["age_days"]), ("check_first", "Open, but the board gives no date", None))

    def test_an_ashby_date_reads_as_last_published(self):
        self.assertIn("last published 4 months ago", self.label(role(published="2026-07-01"), ats="ashby")["note"])

    def test_reposts_need_new_links_on_two_scan_dates_within_90_days(self):
        same = "program manager launches"
        self.assertEqual(P.title_key("gh", "Program Manager, Launches!"), ("gh", same))
        two_dates = [("2026-10-01", {"gh:0": role("gh:0")})]
        c = self.label(role(), two_dates)
        self.assertEqual((c["label"], c["reposts"], c["note"]), ("check_first", 1, "Open, but reposted 1 time in 90 days"))
        three = two_dates + [("2026-10-15", {"gh:00": role("gh:00")})]
        self.assertEqual((self.label(role(), three)["label"], self.label(role(), three)["reposts"]), ("suspicious", 2))
        one_date = {"gh:0": role("gh:0"), "gh:1": role()}   # two links on the same day is not a repost
        self.assertEqual(P.check(role(), P.repost_counts([(TODAY, one_date)], TODAY), TODAY)["reposts"], 0)
        too_old = [("2026-07-01", {"gh:0": role("gh:0")})]  # outside the 90 days
        self.assertEqual(self.label(role(), too_old)["reposts"], 0)
        other_org = [("2026-10-01", {"ab:0": role("ab:0", org="ab")})]
        self.assertEqual(self.label(role(), other_org)["reposts"], 0)

    def test_same_title_in_different_cities_is_not_a_repost(self):
        cities = {"id%d" % i: dict(role("id%d" % i), location=city)
                  for i, city in enumerate(("London", "Seoul", "Munich", "Tokyo"))}
        history = [("2026-11-01", {"id0": cities["id0"], "id1": cities["id1"]}),
                   ("2026-11-02", {"id2": cities["id2"], "id3": cities["id3"]})]
        seen = P.repost_counts(history, TODAY)
        self.assertEqual([P.check(r, seen, TODAY)["reposts"] for r in cities.values()], [0, 0, 0, 0])

    def test_same_title_and_location_relisted_after_closure_is_a_repost(self):
        old = role("gh:old")
        old["location"] = "London, United Kingdom"
        new = role("gh:new")
        new["location"] = " london, united kingdom "
        seen = P.repost_counts([("2026-10-20", {"gh:old": old}), (TODAY, {"gh:new": new})], TODAY)
        self.assertEqual(P.check(new, seen, TODAY)["reposts"], 1)

    def test_an_action_ranks_lower_only_when_every_role_it_names_is_suspicious(self):
        a = {"effects": [{"dimension": "D1", "scope": {"role_ids": ["gh:1", "gh:2"]}}]}
        self.assertTrue(P.only_suspicious(a, {"gh:1", "gh:2"}))
        self.assertFalse(P.only_suspicious(a, {"gh:1"}))
        self.assertFalse(P.only_suspicious({"effects": [{"dimension": "D3"}]}, {"gh:1"}))   # names no role

    def test_the_page_shows_a_note_only_when_there_is_something_to_check(self):
        self.assertEqual(B.posting_label({"posting_check": {"label": "likely_real", "note": "Open"}}), {})
        self.assertEqual(B.posting_label({"posting_check": {"label": "suspicious", "note": "Open, but posted 14 months ago"}}),
                         {"pc": "Open, but posted 14 months ago", "pcl": "suspicious"})


class FetchTests(unittest.TestCase):
    """The saved Greenhouse, Ashby and Lever feeds, run through fetch_roles.py on two dates."""
    def setUp(self):
        cfg = H.example_config()
        cfg["targets"] = [{"id": "gh", "name": "Acme AI", "ats": "greenhouse", "slug": "acme"},
                          {"id": "ab", "name": "Globex Labs", "ats": "ashby", "slug": "globex"},
                          {"id": "lv", "name": "Initech Robotics", "ats": "lever", "slug": "initech"}]
        self.ws = H.new_workspace(self, cfg)
        self.fx = os.path.join(os.path.dirname(self.ws), "fixtures")
        os.makedirs(self.fx)
        for src, dst in (("greenhouse", "gh"), ("ashby", "ab"), ("lever", "lv")):
            shutil.copy(os.path.join(H.FIXTURES, "ats", src + ".json"), os.path.join(self.fx, dst + ".json"))

    def run_main(self, date):
        with mock.patch("sys.stdout", io.StringIO()):
            self.assertEqual(F.main(["--workspace", self.ws, "--fixtures", self.fx, "--date", date]), 0)
        return H.load(os.path.join(self.ws, "market", "roles", "latest.json"))

    def test_every_role_gets_a_label_and_the_snapshot_keeps_links_and_dates(self):
        latest = self.run_main("2026-11-01")
        self.assertEqual(V.check(latest, H.schema("roles.schema.json")), [])
        checks = {r["id"]: r["posting_check"] for r in latest["roles"]}
        self.assertTrue(checks and all(c["label"] in P.LABELS for c in checks.values()))
        self.assertEqual(sum(latest["summary"]["posting_checks"].values()), len(latest["roles"]))
        gh = next(r for r in latest["roles"] if r["org"] == "gh")
        self.assertEqual(gh["posting_check"], {"label": "likely_real", "note": "Open", "age_days": 33, "reposts": 0})
        snap = H.load(os.path.join(self.ws, "market", "roles", "snapshots", "2026-11-01.json"))
        self.assertEqual(set(snap["roles"][gh["id"]]), {"org", "title", "family", "url", "published_at", "location"})

    def test_a_relisted_title_on_a_new_link_is_counted_as_a_repost(self):
        first = self.run_main("2026-11-01")
        gh = H.load(os.path.join(self.fx, "gh.json"))
        job = gh["jobs"][0]
        title = job["title"]
        job["id"] = 4199999                                  # the same title, back on a new link
        H.save(os.path.join(self.fx, "gh.json"), gh)
        latest = self.run_main("2026-11-02")
        relisted = next(r for r in latest["roles"] if r["id"] == "gh:4199999")
        self.assertEqual((relisted["title"], relisted["posting_check"]["reposts"]), (title, 1))
        self.assertEqual(relisted["posting_check"]["label"], "check_first")
        self.assertTrue(any(r["title"] == title for r in first["roles"]))

    def test_the_age_label_never_changes_the_inputs_fingerprint(self):
        """A posting gets a day older every day; that alone must not make a day count as changed (score.py)."""
        import score as S
        ws = H.copy_demo(self)
        config = H.load(os.path.join(ws, "config.json"))
        before = S.build_run(ws, config, "2026-11-03")["inputs_digest"]
        path = os.path.join(ws, "market", "roles", "latest.json")
        doc = H.load(path)
        for r in doc["roles"]:
            r["posting_check"] = {"label": "check_first", "note": "Open, but posted 4 months ago", "age_days": 120,
                                  "reposts": 0}
        H.save(path, doc)
        self.assertEqual(S.build_run(ws, config, "2026-11-03")["inputs_digest"], before)

if __name__ == "__main__":
    unittest.main()
