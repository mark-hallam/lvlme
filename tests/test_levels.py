"""_levels.py: levels, the next-level set (reachable, cannot reach, caps, chance), quests, level history, streak."""
import json
import os
import re
import unittest
from unittest import mock

import helpers as H
import _levels as L
import _levels_html as LH
import build_dashboard as B

WEIGHTS = [25, 20, 20, 10, 10, 10, 5]
CAPS = [0, 1, 3, 1, 1, 1, 3]
TODAY = "2026-11-01"


def role(s, org="acme", rid="acme:1", hard=False):
    return {"id": rid, "org": org, "family": "tpm", "lc": "australia_nz", "s": list(s), "hard": hard,
            "fit": L.fit_of(s, WEIGHTS)}


def act(aid, effects, p=1.0, date="2026-11-10", hours=1.0, status="todo", priority=0.0):
    return {"id": aid, "title": "Action " + aid, "status": status, "p": p, "effects": effects, "date": date,
            "dated": True, "hours": hours, "priority": priority, "done_when": "proof"}


def eff(dim, delta=None, at_least=None, **scope):
    e = {"dimension": dim, "scope": scope}
    if delta is not None:
        e["delta"] = delta
    if at_least is not None:
        e["set_at_least"] = at_least
    return e


def by_date(acts):
    return sorted(acts, key=lambda a: (a["date"], a["id"]))


class LevelBasics(unittest.TestCase):
    def test_bands_are_the_rubric_fit_table(self):
        self.assertEqual([L.band_index(v) for v in (0, 39.9, 40, 54.9, 55, 69.9, 70, 84.9, 85, 100)],
                         [0, 0, 1, 1, 2, 2, 3, 3, 4, 4])

    def test_top_level_has_no_next(self):
        nl = L.next_level(role([5, 5, 5, 4, 4, 5, 5]), [], CAPS, WEIGHTS, TODAY)
        self.assertTrue(nl["top"])
        self.assertEqual((nl["level"], nl["band"]), (5, "Strong"))
        self.assertNotIn("target", nl)


class NextLevelSet(unittest.TestCase):
    R = [2, 2, 1, 2, 2, 5, 1]       # fit 41: Level 2, Low; Level 3 starts at 55

    def test_fewest_actions_then_earliest_date(self):
        r = role(self.R)
        acts = by_date([act("A01", [eff("D3", at_least=4)], date="2026-11-10"),     # +12
                        act("A02", [eff("D2", 1)], date="2026-11-20"),              # +4
                        act("A03", [eff("D7", 3)], date="2026-11-05"),              # +3
                        act("A04", [eff("D4", 1)], date="2026-11-30")])             # +2
        nl = L.next_level(r, acts, CAPS, WEIGHTS, TODAY)
        self.assertEqual((nl["level"], nl["target"], nl["points_to_next"]), (2, 55, 14))
        self.assertTrue(nl["reachable"])
        self.assertEqual(nl["set"]["ids"], ["A03", "A01"])          # three pairs reach 55; this one lands first
        self.assertEqual(nl["set"]["date"], "2026-11-10")
        self.assertEqual(nl["set"]["fit"], 56)
        self.assertTrue(nl["set"]["exact"])
        self.assertAlmostEqual(nl["set"]["chance"], 1.0)

    def test_equal_dates_go_to_the_least_effort(self):
        r = role(self.R)
        acts = by_date([act("A01", [eff("D3", at_least=4)], date="2026-11-30", hours=2),
                        act("A02", [eff("D2", 1)], date="2026-11-10", hours=6),
                        act("A03", [eff("D7", 3)], date="2026-11-10", hours=1)])
        nl = L.next_level(r, acts, CAPS, WEIGHTS, TODAY)
        self.assertEqual(nl["set"]["ids"], ["A03", "A01"])          # same landing date as A02 + A01, an hour instead of six

    def test_chance_of_working_weights_the_effect(self):
        r = role([2, 2, 1, 2, 1, 5, 1])                            # fit 39, one point short of Level 2
        low = L.next_level(r, [act("A01", [eff("D5", 1)], p=0.4)], CAPS, WEIGHTS, TODAY)   # 0.4 x 2 points = 0.8
        self.assertFalse(low["reachable"])
        self.assertEqual(low["missing"]["points"], 0.2)
        self.assertEqual(low["best_case"]["ids"], ["A01"])
        self.assertAlmostEqual(low["best_case"]["chance"], 0.4)
        high = L.next_level(r, [act("A01", [eff("D5", 1)], p=0.6)], CAPS, WEIGHTS, TODAY)  # 1.2 points
        self.assertTrue(high["reachable"])
        self.assertAlmostEqual(high["set"]["chance"], 0.6)          # the level really arrives only if it works

    def test_caps_hold_and_cannot_reach_says_what_is_missing(self):
        r = role(self.R)
        acts = by_date([act("A01", [eff("D1", 3)]),                              # D1 cap 0: years don't change
                        act("A02", [eff("D3", at_least=5)], p=0.5),             # cap 3: 1 to 4 at most
                        act("A03", [eff("D2", 3)], p=1.0, date="2026-11-12")])  # cap 1
        nl = L.next_level(r, acts, CAPS, WEIGHTS, TODAY)
        self.assertEqual(nl["relevant"], ["A02", "A03"])            # A01 can't move this role at all
        self.assertFalse(nl["reachable"])
        self.assertEqual(nl["plan"]["fit_expected"], 51)            # 41 + 0.5 x 12 + 4
        self.assertEqual(nl["plan"]["fit_best"], 57)
        self.assertEqual(nl["missing"]["points"], 4)
        self.assertEqual(nl["best_case"]["ids"], ["A02", "A03"])
        self.assertAlmostEqual(nl["best_case"]["chance"], 0.5)
        room = {x["dimension"]: (x["points"], x["covered"]) for x in nl["missing"]["room"]}
        self.assertNotIn("D1", room)                                # no room: its cap is 0
        self.assertNotIn("D2", room)                                # A03 already takes it to its cap
        self.assertEqual(room["D3"], (6, True))                     # half of the 12 is still open, at low odds
        self.assertEqual(room["D7"], (3, False))                    # nothing in the plan raises it
        self.assertEqual(nl["missing"]["ceiling"], 64)                # 10 + 12 + 16 + 6 + 6 + 10 + 4

    def test_ceiling_below_the_next_level(self):
        caps = [0, 0, 0, 0, 0, 0, 1]
        nl = L.next_level(role(self.R), [act("A01", [eff("D7", 1)])], caps, WEIGHTS, TODAY)
        self.assertFalse(nl["reachable"])
        self.assertIsNone(nl["best_case"])
        self.assertLess(nl["missing"]["ceiling"], nl["target"])

    def test_hard_eligibility_block_never_counts(self):
        r = role([2, 2, 1, 2, 1, 0, 1], hard=True)                  # fit 34; eligibility can't be cleared
        nl = L.next_level(r, [act("A01", [eff("D6", at_least=5)])], [0, 1, 3, 1, 1, 5, 3], WEIGHTS, TODAY)
        self.assertEqual(nl["relevant"], [])
        self.assertFalse(nl["reachable"])
        self.assertNotIn("D6", [x["dimension"] for x in nl["missing"]["room"]])

    def test_out_of_scope_and_closed_actions_are_ignored(self):
        r = role([2, 2, 1, 2, 1, 5, 1])
        acts = [act("A01", [eff("D5", 1)], status="done"), act("A02", [eff("D5", 1, orgs=["globex"])]),
                act("A03", [eff("D5", 1)], status="dropped")]
        nl = L.next_level(r, acts, CAPS, WEIGHTS, TODAY)
        self.assertEqual(nl["relevant"], [])
        self.assertFalse(nl["reachable"])

    def test_overdue_action_lands_today(self):
        r = role([2, 2, 1, 2, 1, 5, 1])
        nl = L.next_level(r, [act("A01", [eff("D5", 1)], date="2026-10-20")], CAPS, WEIGHTS, TODAY)
        self.assertEqual(nl["set"]["date"], TODAY)

    def test_long_plans_use_a_flagged_greedy_search(self):
        r = role(self.R)
        acts = by_date([act("A0%d" % i, [eff(d, 1)], hours=h) for i, (d, h) in enumerate([("D2", 1), ("D4", 1), ("D5", 1), ("D7", 4)], 1)]
                       + [act("A05", [eff("D3", at_least=4)], hours=2)])
        with mock.patch.object(L, "MAX_EXACT", 2):
            nl = L.next_level(r, acts, CAPS, WEIGHTS, TODAY)
        self.assertTrue(nl["reachable"])
        self.assertFalse(nl["set"]["exact"])
        self.assertEqual(nl["set"]["ids"], ["A01", "A05"])          # best gain per hour first, then nothing it can drop
        self.assertEqual(nl["set"]["fit"], 57)


class Quests(unittest.TestCase):
    def test_sorted_by_points_per_hour_with_the_critical_path_marked(self):
        r = role(NextLevelSet.R)
        acts = by_date([act("A01", [eff("D3", at_least=4)], p=1.0, hours=4, date="2026-11-10"),   # 12 points, 3 an hour
                        act("A02", [eff("D2", 1)], p=0.5, hours=1, date="2026-11-20"),            # 2 points, 2 an hour
                        act("A03", [eff("D7", 3)], p=1.0, hours=0.5, date="2026-11-05"),          # 3 points, 6 an hour
                        act("A04", [], hours=0.5, date="2026-11-06", priority=9)])                # credibility only
        nl = L.next_level(r, acts, CAPS, WEIGHTS, TODAY)
        qs = L.quests(r, acts, CAPS, WEIGHTS, nl)
        self.assertEqual([q["a"]["id"] for q in qs], ["A03", "A01", "A02", "A04"])
        self.assertEqual({q["a"]["id"] for q in qs if q["crit"]}, set(nl["set"]["ids"]))
        a02 = next(q for q in qs if q["a"]["id"] == "A02")
        self.assertEqual((a02["exp"], a02["works"]), (2, 4))         # if it works, it adds its full 4 points
        lift = L.project(r, acts, CAPS, WEIGHTS)[0] - L.project(r, [a for a in acts if a["id"] != "A02"], CAPS, WEIGHTS)[0]
        self.assertAlmostEqual(a02["exp"], L.r1(lift))               # the same number as the what-if rail
        self.assertEqual(next(q for q in qs if q["a"]["id"] == "A04")["exp"], 0)

    def test_tell_agent_names_the_action_and_asks_for_evidence(self):
        text = L.tell_agent(act("A07", []))
        self.assertTrue(text.startswith("Mark action A07 done"))
        self.assertIn("Evidence: <paste a link, file path or email reference>", text)


class HistoryAndStreak(unittest.TestCase):
    def test_level_history_marks_ups_and_downs(self):
        runs = [{"date": "d1", "top": 39, "orgs": {"g": 30}}, {"date": "d2", "top": 42, "orgs": {}},
                {"date": "d3", "top": 41, "orgs": {"g": 41}}, {"date": "d4", "top": 38, "orgs": {"g": 38}}]
        hist = L.level_history(runs)
        self.assertEqual([h["change"] for h in hist], [None, "up", None, "down"])
        self.assertEqual([h["level"] for h in hist], [1, 2, 2, 1])
        self.assertEqual([h["date"] for h in L.level_history(runs, "g")], ["d1", "d3", "d4"])   # no role that day
        self.assertEqual(L.level_history(runs, "g")[1]["change"], "up")

    def test_progress_needs_real_movement(self):
        def run(date, fits):
            return {"run_date": date, "roles": [{"role_id": k, "fit": v} for k, v in fits.items()]}
        runs = [run("2026-10-04", {"a": 40, "b": 30}), run("2026-10-11", {"a": 42, "b": 30}),
                run("2026-10-18", {"a": 41, "c": 50}), run("2026-10-25", {"a": 41}), run("2026-11-01", {"a": 41})]
        evidence = [{"id": "E01", "level": "verified", "sources": [{"checked_on": "2026-10-20"}]},
                    {"id": "E02", "level": "self_reported", "sources": [{"checked_on": "2026-10-30"}]},
                    {"id": "E03", "level": "corroborated", "added_on": "2026-10-30", "sources": []}]
        plan = [{"id": "A01", "status": "done", "done_evidence": "link", "finished_on": "2026-10-15"},
                {"id": "A02", "status": "done", "finished_on": "2026-10-28"}]          # no evidence: doesn't count
        days, streak = L.progress_days(runs, evidence, plan)
        self.assertTrue(days[0]["start"])
        self.assertEqual([d["progress"] for d in days[1:]], [True, True, True, True])
        self.assertEqual(days[1]["roles_up"], 1)
        self.assertEqual((days[2]["roles_up"], days[2]["actions"]), (0, ["A01"]))      # a new role opening is not a rise
        self.assertEqual(days[3]["evidence"], ["E01"])
        self.assertEqual(days[4]["evidence"], ["E03"])                                  # self-reported doesn't count
        self.assertEqual(streak, 4)
        days, streak = L.progress_days(runs + [run("2026-11-08", {"a": 40})], evidence, plan)
        self.assertEqual(streak, 0)                                                     # a fall is not progress


class DemoLevels(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)
        with mock.patch("sys.stdout"):
            self.assertEqual(B.main(["--workspace", self.ws]), 0)

    def read(self, *parts):
        with open(os.path.join(self.ws, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_agent_files_carry_the_next_level(self):
        lv = H.load(os.path.join(self.ws, "report", "for-agents", "dashboard.json"))["levels"]
        best = lv["best_role"]
        self.assertEqual((best["role_id"], best["level"], best["points_to_next"]), ("initech:i-0001", 3, 13))
        self.assertFalse(best["reachable_on_expected_odds"])
        self.assertEqual(best["missing"]["points_short"], 7.2)
        self.assertEqual([a["id"] for a in best["best_case_set"]["actions"]], ["A06", "A11"])
        self.assertEqual(best["best_case_set"]["chance_it_happens"], 0.16)
        globex = lv["per_org"]["globex"]
        self.assertEqual([a["id"] for a in globex["smallest_set"]["actions"]], ["A02"])
        self.assertEqual(globex["smallest_set"]["level_reached_on"], "2026-11-15")
        self.assertEqual(lv["quests"][0]["id"], "A07")
        self.assertTrue(lv["quests"][0]["tell_your_agent"].startswith("Mark action A07 done"))
        self.assertEqual(lv["streak"], 4)
        self.assertEqual([h["change"] for h in lv["level_history"]], [None, None, None, "up", None])
        summary = self.read("report", "for-agents", "SUMMARY.md")
        self.assertIn("## Next level", summary)
        self.assertIn("## When the person says an action is done", summary)
        self.assertNotIn("Jordan", summary)

    def test_page_renders_the_level_view_without_javascript(self):
        page = self.read("report", "index.html")
        body = page.split('<script type="application/json"')[0]
        self.assertIn('id="v-level"', body)
        self.assertIn("Not reachable on the current plan", body)
        self.assertIn("Done? Tell your agent:", body)
        self.assertIn("scored days in a row with real progress", body)
        self.assertNotIn("__LEVEL", page)
        self.assertNotIn("Jordan", page)

    def test_static_copy_has_no_dashes_as_punctuation(self):
        page = self.read("report", "index.html")
        blob = re.search(r'<script type="application/json" id="data">(.*?)</script>', page, re.S).group(1)
        card, view = LH.render(json.loads(blob))
        text = re.sub(r"<[^>]+>", " ", card + view)
        self.assertNotRegex(text, "[–—]| - ")


if __name__ == "__main__":
    unittest.main()
