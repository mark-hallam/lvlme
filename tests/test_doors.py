"""Doors (scripts/fetch_doors.py, scripts/doors.py, scripts/_doors.py). Fictional data, no network."""
import io
import os
import unittest
from contextlib import redirect_stdout
from unittest import mock

import helpers as H
import _autopilot as APL
import _doors as DR
import doors as CLI
import fetch_doors as FD
import score as S
import validate as V

TODAY = "2026-11-01"
CONFIG = {"candidate": {"home_region": "Brisbane, Australia", "timezone": "Australia/Brisbane"},
          "targets": [{"id": "acme", "name": "Acme AI", "aliases": ["Acme Artificial Intelligence"]},
                      {"id": "globex", "name": "Globex Labs"}]}
ICS = "\r\n".join([
    "BEGIN:VCALENDAR", "BEGIN:VEVENT", "UID:e1", "SUMMARY:Acme AI night\\, with demos",
    "DTSTART;TZID=Australia/Sydney:20261112T190000", "LOCATION:Sydney NSW", "DESCRIPTION:More at",
    " https://example.com/e1 for details", "END:VEVENT",
    "BEGIN:VEVENT", "UID:e2", "SUMMARY:Builders drinks", "DTSTART:20261113T080000Z", "LOCATION:Brisbane QLD",
    "URL:https://example.com/e2", "END:VEVENT",
    "BEGIN:VEVENT", "UID:e3", "SUMMARY:Perth data meetup", "DTSTART;VALUE=DATE:20261114", "LOCATION:Perth WA",
    "URL:https://example.com/e3", "END:VEVENT",
    "BEGIN:VEVENT", "UID:e4", "SUMMARY:Globex Labs summit", "DTSTART;VALUE=DATE:20270601", "LOCATION:Online",
    "URL:https://example.com/e4", "END:VEVENT",
    "BEGIN:VEVENT", "UID:e5", "SUMMARY:Acme AI last month", "DTSTART;VALUE=DATE:20261001", "LOCATION:Brisbane",
    "URL:https://example.com/e5", "END:VEVENT", "END:VCALENDAR", ""])
CAL = {"url": "https://api.lu.ma/ics/get?entity=calendar&id=cal-test", "name": "Test"}


def quiet(fn, *args):
    """(exit code, what it printed). A refusal (SystemExit with a message) counts as code 1."""
    with redirect_stdout(io.StringIO()) as out, mock.patch("sys.stderr", io.StringIO()):
        try:
            code = fn(list(args))
        except SystemExit as exc:
            code, msg = (1, str(exc.code)) if isinstance(exc.code, str) else (exc.code, "")
            print(msg)
    return code, out.getvalue()


class CalendarTests(unittest.TestCase):
    def test_reads_folded_lines_escapes_and_time_zones(self):
        e = {x["uid"]: x for x in DR.parse_ics(ICS, "Australia/Brisbane")}
        self.assertEqual(e["e1"]["title"], "Acme AI night, with demos")
        self.assertEqual((e["e1"]["starts_on"], e["e1"]["time"]), ("2026-11-12", "18:00"))   # Sydney 7pm is Brisbane 6pm
        self.assertEqual(e["e1"]["link"], "https://example.com/e1")                       # from the folded description
        self.assertEqual((e["e2"]["starts_on"], e["e2"]["time"]), ("2026-11-13", "18:00"))   # 08:00 UTC is 6pm
        self.assertEqual((e["e3"]["starts_on"], e["e3"].get("time")), ("2026-11-14", None))

    def test_keeps_targets_and_home_city_within_the_horizon(self):
        doors = DR.from_ical(DR.parse_ics(ICS, "Australia/Brisbane"), CAL, CONFIG, TODAY)
        got = {d["uid"]: d for d in doors}
        self.assertEqual(sorted(got), ["ical:e1", "ical:e2"])   # Perth: not near, no target; e4 too far; e5 past
        self.assertEqual(got["ical:e1"]["orgs"], ["acme"])
        self.assertEqual(got["ical:e2"]["orgs"], [])
        self.assertTrue(all(d["source"] == CAL["url"] and d["source_kind"] == "luma_ical" for d in doors))
        self.assertEqual(got["ical:e1"]["why"]["dimension"], "D3")
        far = DR.from_ical(DR.parse_ics(ICS, "Australia/Brisbane"), CAL, CONFIG, TODAY, horizon=365)
        self.assertIn("ical:e4", {d["uid"] for d in far})
        self.assertIn("online", next(d for d in far if d["uid"] == "ical:e4")["why"]["note"])

    def test_programmes_come_from_postings_already_fetched(self):
        roles = {"roles": [{"id": "acme:1", "org": "acme", "title": "Product Manager", "url": "https://example.com/1"}],
                 "excluded": [{"org": "acme", "title": "Acme AI Fellows Program", "url": "https://example.com/2"},
                              {"org": "globex", "title": "AI Residency, 2027", "url": "https://example.com/3"}]}
        doors = DR.from_roles(roles, CONFIG)
        self.assertEqual([d["title"] for d in doors], ["Acme AI Fellows Program", "AI Residency, 2027"])
        self.assertTrue(all(d["kind"] == "programme" and d["why"]["dimension"] == "D4" for d in doors))


class NeverFetchedTests(unittest.TestCase):
    """Meetup, Eventbrite and LinkedIn are never fetched, whatever the config says."""
    BAD = ["https://www.meetup.com/brisbane-ai/events/ical/", "https://www.eventbrite.com.au/o/acme-123",
           "https://eventbrite.com/e/1", "https://www.linkedin.com/events/123", "https://lnkd.in/abc",
           "https://evbuc.com/x", "https://meetu.ps/e/1"]

    def test_blocked_addresses(self):
        for url in self.BAD:
            self.assertTrue(DR.blocked(url), url)
        for url in ("https://api.lu.ma/ics/get?entity=calendar&id=cal-1", "https://example.com/meetup.com",
                    "https://notmeetup.com.example/x"):
            self.assertFalse(DR.blocked(url), url)

    def test_fetch_doors_never_requests_a_blocked_address(self):
        ws = H.new_workspace(self, dict(H.template_config(), **CONFIG, doors={
            "calendars": [{"url": u} for u in self.BAD] + [CAL, {"url": "http://example.com/plain.ics"}]}))
        asked = []

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake(req, timeout=None):
            asked.append(req.full_url)
            return Resp(ICS.encode("utf-8"))

        with mock.patch.object(FD.urllib.request, "urlopen", side_effect=fake):
            code, out = quiet(FD.main, "--workspace", ws, "--date", TODAY)
        self.assertEqual(code, 0)
        self.assertEqual(asked, [CAL["url"]])
        self.assertEqual(out.count("skipped: LVLme never fetches"), len(self.BAD))
        self.assertIn("only https://", out)
        self.assertEqual(len(H.load(os.path.join(ws, DR.REL))["doors"]), 2)


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)
        self.doc = H.load(os.path.join(self.ws, DR.REL))

    def test_the_demo_lists_five_dated_doors_with_sources(self):
        dated = [d for d in self.doc["doors"] if DR.date_of(d)]
        self.assertGreaterEqual(len(dated), 5)
        self.assertTrue(all(d["source"].startswith("https://") and d["link"] for d in self.doc["doors"]))

    def test_every_demo_door_becomes_a_plan_action(self):
        before = len(H.load(os.path.join(self.ws, "campaign", "plan.json"))["actions"])
        for d in self.doc["doors"]:
            self.assertEqual(quiet(CLI.main, "--workspace", self.ws, "plan", d["id"], "--date", TODAY)[0], 0)
        plan = H.load(os.path.join(self.ws, "campaign", "plan.json"))
        added = plan["actions"][before:]
        self.assertEqual(len(added), len(self.doc["doors"]))
        doors = {d["id"]: d for d in H.load(os.path.join(self.ws, DR.REL))["doors"]}
        for a in added:
            door = next(d for d in doors.values() if d.get("action") == a["id"])
            self.assertEqual(a["dimension"], door["why"]["dimension"])
            self.assertEqual(a.get("target_date"), DR.date_of(door) or None)
            self.assertTrue(a["done_when"] and a["effects"])
        self.assertEqual(quiet(V.main, "--workspace", self.ws)[0], 0)
        code, out = quiet(CLI.main, "--workspace", self.ws, "plan", "DR01", "--date", TODAY)
        self.assertEqual(code, 1)     # a door already in the plan is not added twice
        self.assertIn("already plan action", out)

    def test_doors_change_no_score(self):
        run = lambda: (quiet(S.main, "--workspace", self.ws, "--date", TODAY),
                       H.load(os.path.join(self.ws, "eval", "runs", TODAY + ".json")))[1]   # noqa: E731
        with_doors = run()
        os.remove(os.path.join(self.ws, DR.REL))
        without = run()
        self.assertEqual(with_doors["roles"], without["roles"])
        self.assertEqual(with_doors.get("inputs_digest"), without.get("inputs_digest"))

    def test_a_person_met_goes_into_warm_paths_by_name(self):
        code, out = quiet(CLI.main, "--workspace", self.ws, "met", "DR01", "--org", "acme", "--person", "Sam Lee",
                          "--date", "2026-11-12")
        self.assertEqual(code, 0, out)
        warm = H.load(os.path.join(self.ws, "campaign", "warm-paths.json"))
        sam = next(c for c in warm["contacts"] if c["person"] == "Sam Lee")
        self.assertEqual((sam["org"], sam["stage"], sam["updated_on"]), ("acme", "talked", "2026-11-12"))
        self.assertIn("DR01", sam["note"])
        self.assertEqual(next(d for d in H.load(os.path.join(self.ws, DR.REL))["doors"] if d["id"] == "DR01")["status"],
                         "went")
        self.assertEqual(quiet(CLI.main, "--workspace", self.ws, "met", "DR01", "--org", "acme", "--person", "sam lee")[0], 1)
        self.assertEqual(quiet(CLI.main, "--workspace", self.ws, "met", "DR01", "--org", "globex", "--person", "Jo")[0], 1)
        self.assertEqual(quiet(V.main, "--workspace", self.ws)[0], 0)

    def test_fetching_again_keeps_the_persons_marks(self):
        quiet(CLI.main, "--workspace", self.ws, "status", "DR02", "going", "--date", TODAY)
        ics = os.path.join(self.ws, "market", "fixtures", "doors.ics")
        code, out = quiet(FD.main, "--workspace", self.ws, "--ics", ics, "--date", TODAY)
        self.assertIn("0 new, 4 already known", out)
        doc = H.load(os.path.join(self.ws, DR.REL))
        self.assertEqual(len(doc["doors"]), len(self.doc["doors"]))
        self.assertEqual(next(d for d in doc["doors"] if d["id"] == "DR02")["status"], "going")

    def test_validate_catches_a_missing_plan_action(self):
        self.doc["doors"][0]["action"] = "A99"
        H.save(os.path.join(self.ws, DR.REL), self.doc)
        code, out = quiet(V.main, "--workspace", self.ws)
        self.assertEqual(code, 1)
        self.assertIn("action A99 is not in campaign/plan.json", out)

    def test_the_weekly_note_names_the_next_door(self):
        config = H.load(os.path.join(self.ws, "config.json"))
        note = APL.week_note(self.ws, config, TODAY)
        self.assertEqual(note["event"]["id"], "DR01")
        self.assertEqual(note["event"]["org"], "Acme AI")
        self.assertIn("Thu 12 Nov, 6pm", note["event"]["text"])

    def test_the_dashboard_shows_the_doors_card(self):
        with open(os.path.join(H.DEMO, "report", "index.html"), encoding="utf-8") as fh:
            page = fh.read()
        self.assertIn('id="doorsCard"', page)
        self.assertIn("Acme AI Builders Night", page)
        agents = H.load(os.path.join(H.DEMO, "report", "for-agents", "dashboard.json"))
        self.assertEqual(agents["doors"]["total"], len(self.doc["doors"]))

    def test_add_checks_its_inputs(self):
        bad = [["--kind", "event", "--title", "No date", "--link", "https://example.com/x"],
               ["--kind", "programme", "--title", "X", "--link", "https://example.com/y", "--org", "nobody"],
               ["--kind", "event", "--title", "Bad time", "--on", "2026-12-01", "--time", "6pm",
                "--link", "https://example.com/z"]]
        for args in bad:
            self.assertEqual(quiet(CLI.main, "--workspace", self.ws, "add", *args)[0], 1, args)
        code, out = quiet(CLI.main, "--workspace", self.ws, "add", "--kind", "event", "--title", "Acme talk",
                          "--on", "2026-12-01", "--link", "https://example.com/t", "--org", "acme", "--date", TODAY)
        self.assertEqual(code, 0, out)
        self.assertIn("Added DR07", out)


if __name__ == "__main__":
    unittest.main()
