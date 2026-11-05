"""Level events: recorded from the runs, only added, never across a rubric change, no names on the share card."""
import os
import unittest

import helpers as H
import _common as C
import _events as E


def run(date, fit, rid="acme:1", rubric="1.1"):
    return {"run_date": date, "rubric_version": rubric, "roles": [{"role_id": rid, "fit": fit, "judged": True}]}


def day(date, evidence=(), actions=()):
    return {"date": date, "progress": True, "evidence": list(evidence), "actions": list(actions)}


class DetectTests(unittest.TestCase):
    def test_a_rise_between_bands_is_a_level_up_with_its_evidence(self):
        runs = [run("2026-10-04", 44), run("2026-10-11", 47), run("2026-10-18", 58, "acme:2")]
        days = [day("2026-10-18", evidence=["E09"], actions=["A03"])]
        ev = E.detect(runs, days, {})
        self.assertEqual(ev, [{"date": "2026-10-18", "kind": "level_up", "from_level": 2, "to_level": 3,
                               "role_id": "acme:2", "evidence": ["A03", "E09"]}])

    def test_no_event_for_a_drop_or_a_change_of_rubric(self):
        runs = [run("2026-10-04", 60), run("2026-10-11", 50), run("2026-10-18", 72, rubric="1.2")]
        self.assertEqual([e for e in E.detect(runs, [], {}) if e["kind"] == "level_up"], [])

    def test_goal_reached_once_at_the_goal_level(self):
        runs = [run("2026-10-04", 60), run("2026-10-11", 72), run("2026-10-18", 80)]
        kinds = [(e["kind"], e["date"]) for e in E.detect(runs, [], {})]
        self.assertEqual(kinds, [("level_up", "2026-10-11"), ("goal_reached", "2026-10-11")])
        self.assertEqual([e["kind"] for e in E.detect(runs, [], {"target_level": 5})], ["level_up"])   # Level 4 is not Level 5

    def test_a_goal_already_met_on_day_one_is_reached_on_day_one(self):
        ev = E.detect([run("2026-10-04", 75)], [], {})
        self.assertEqual([(e["kind"], e["to_level"]) for e in ev], [("goal_reached", 4)])


class FileTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)

    def test_update_writes_events_and_only_ever_adds(self):
        runs = [run("2026-10-04", 44), run("2026-10-18", 58)]
        path = os.path.join(self.ws, "eval", "levels.json")
        if os.path.exists(path):
            os.remove(path)
        first = E.update(self.ws, runs, [], {})
        self.assertEqual(len(first), 1)
        self.assertEqual(E.update(self.ws, runs, [], {}), first)                       # again: no duplicate
        kept = E.update(self.ws, [run("2026-10-04", 44)], [], {})                      # the run file is gone: the event stays
        self.assertEqual(kept, first)
        self.assertEqual(H.load(path)["schema_version"], 1)

    def test_dashboard_build_records_the_demos_level_up(self):
        import build_dashboard as B
        os.remove(os.path.join(self.ws, "eval", "levels.json")) if os.path.exists(os.path.join(self.ws, "eval", "levels.json")) else None
        B.main(["--workspace", self.ws])
        events = H.load(os.path.join(self.ws, "eval", "levels.json"))["events"]
        self.assertTrue(any(e["kind"] == "level_up" for e in events))
        import validate as V
        self.assertEqual(V.validate_workspace(self.ws)[0], [])


class ShareCardTests(unittest.TestCase):
    def test_level_and_dates_only(self):
        ev = {"date": "2026-10-18", "kind": "level_up", "from_level": 2, "to_level": 3, "role_id": "acme:4100002",
              "evidence": ["E09"]}
        card = E.share_card(ev, "2026-10-04")
        self.assertEqual(card["head"], "Levelled up: Level 2, Low to Level 3, Moderate")
        self.assertEqual(card["line"], "Reached on 18 Oct 2026, 14 days after the first measurement on 4 Oct 2026.")
        text = " ".join(str(v) for v in card.values())
        for private in ("acme", "4100002", "E09"):
            self.assertNotIn(private, text)

    def test_goal_reached_card(self):
        ev = {"date": "2026-12-01", "kind": "goal_reached", "from_level": 3, "to_level": 4, "role_id": "x", "evidence": []}
        self.assertEqual(E.share_card(ev, "2026-10-04")["head"], "Goal reached: Level 4, Good")


class RecentTests(unittest.TestCase):
    def test_recent_window(self):
        ev = [{"date": "2026-10-18", "kind": "level_up", "from_level": 2, "to_level": 3}]
        self.assertIsNotNone(E.recent(ev, "2026-11-05", "level_up"))
        self.assertIsNone(E.recent(ev, "2026-12-05", "level_up"))
        self.assertIsNone(E.recent(ev, "2026-10-10", "level_up"))
        self.assertIsNone(E.recent(ev, "2026-11-05", "goal_reached"))


if __name__ == "__main__":
    unittest.main()
