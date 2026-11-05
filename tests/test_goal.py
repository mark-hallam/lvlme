"""The goal: its sentence, the honest test against the starting line, the stepping stone and the starting line."""
import os
import unittest

import helpers as H
import _common as C
import _goal as G
import build_dashboard as B

WEIGHTS = [25, 20, 20, 10, 10, 10, 5]
CAPS = [0, 1, 2, 1, 1, 1, 3]
TODAY = "2026-11-01"


def role(rid, s, **extra):
    r = {"id": rid, "org": "acme", "on": "Acme AI", "title": "Role " + rid, "loc": ["Melbourne"], "family": "tpm",
         "lc": "au", "s": list(s), "hard": False, "fit": B.fit_of(s, WEIGHTS), "judged": True, "ib": "Low"}
    r.update(extra)
    return r


def action(aid, dim, to, date, p=0.8, hours=4):
    return {"id": aid, "title": "Move " + aid, "status": "todo", "p": p, "date": date, "dated": True, "hours": hours,
            "effects": [{"dimension": dim, "set_at_least": to, "scope": {}}]}


def page(roles, actions):
    return {"roles": roles, "actions": actions, "caps": CAPS, "weights": WEIGHTS, "meta": {"run_date": TODAY}}


class SentenceTests(unittest.TestCase):
    def test_goal_sentence_names_role_orgs_place_and_date(self):
        self.assertEqual(G.goal_sentence("Customer success", ["Anthropic", "OpenAI"], "Melbourne", "2027-06-30"),
                         "Customer success at Anthropic or OpenAI, in Melbourne, by 30 Jun 2027")
        self.assertEqual(G.goal_sentence("Product manager", [], "", None), "Product manager")
        self.assertEqual(G.goal_sentence("PM", ["Acme"], "", "2027-01-05"), "PM at Acme, by 5 Jan 2027")

    def test_old_goals_without_the_new_fields_still_read(self):
        self.assertEqual(G.goal_line({"title": "Climate tech roles."}), "Climate tech roles")


class RangeTests(unittest.TestCase):
    def test_range_shows_when_the_run_file_has_it(self):
        r = role("a", [2, 2, 1, 2, 2, 5, 1], fit=21.5, lo=18.0, hi=25.0)
        self.assertEqual(G.fit_range(r), (18.0, 25.0))
        self.assertEqual(G.fit_text(r), "fit about 18 to 25")

    def test_single_fit_until_the_engine_writes_the_range(self):
        r = role("a", [2, 2, 1, 2, 2, 5, 1])          # no lo and hi: the engine has not written fit_low and fit_high
        self.assertEqual(G.fit_range(r), (r["fit"], r["fit"]))
        self.assertEqual(G.fit_text(r), "fit %g" % r["fit"])
        self.assertNotIn(" to ", G.fit_text(r))

    def test_a_range_that_rounds_to_one_number_is_one_number(self):
        r = role("a", [2, 2, 1, 2, 2, 5, 1], fit=21.3, lo=21.2, hi=21.4)
        self.assertNotIn(" to ", G.fit_text(r))


class CheckTests(unittest.TestCase):
    def test_on_track_when_expected_odds_reach_the_goal_level_before_the_date(self):
        pg = page([role("a", [4, 3, 3, 3, 3, 5, 4])], [action("A01", "D3", 5, "2026-12-01", p=1.0)])
        pg["roles"][0]["fit"] = 66.0
        out = G.check(pg, {"by": "2027-03-01"}, TODAY)
        self.assertEqual(out["verdict"], "on_track")
        self.assertIsNone(out["stepping_stone"])
        self.assertIn("Level 4 (Good)", out["text"])
        self.assertIn("1 Mar 2027", out["text"])

    def test_out_of_reach_proposes_a_stepping_stone_with_the_reason(self):
        pg = page([role("a", [1, 1, 0, 1, 1, 5, 0])], [action("A01", "D3", 2, "2026-12-01", p=1.0)])
        out = G.check(pg, {"by": "2027-01-31"}, TODAY)
        self.assertEqual(out["verdict"], "out_of_reach")
        self.assertIn("No plan reaches Level 4 (Good) by 31 Jan 2027", out["text"])
        stone = out["stepping_stone"]
        self.assertTrue(stone["why"])
        self.assertEqual(stone["role"], "Role a")
        self.assertEqual(stone["organisations"], ["Acme AI"])
        self.assertLess(stone["level"], 4)

    def test_actions_after_the_goal_date_do_not_count(self):
        late_moves = [action("A01", "D3", 3, "2027-09-01", p=1.0), action("A02", "D2", 4, "2027-09-01", p=1.0),
                      action("A03", "D5", 4, "2027-09-01", p=1.0), action("A04", "D7", 4, "2027-09-01", p=1.0)]
        pg = page([role("a", [3, 3, 1, 3, 3, 5, 3])], late_moves)
        late = G.check(pg, {"by": "2027-03-01"}, TODAY)
        early = G.check(pg, {"by": "2027-12-01"}, TODAY)
        self.assertNotEqual(late["verdict"], "on_track")
        self.assertEqual(early["verdict"], "on_track")

    def test_nothing_judged_is_said_plainly(self):
        pg = page([role("a", [0] * 7, judged=False)], [])
        out = G.check(pg, {"by": "2027-03-01"}, TODAY)
        self.assertEqual(out["verdict"], "unknown")
        self.assertIn("cannot be tested", out["text"])

    def test_already_there_is_reached(self):
        pg = page([role("a", [5, 4, 3, 4, 4, 5, 4])], [])
        self.assertEqual(G.check(pg, {"by": "2027-03-01"}, TODAY)["verdict"], "reached")


class StartingLineTests(unittest.TestCase):
    def test_expected_date_and_move_count(self):
        pg = page([role("a", [3, 2, 2, 2, 2, 5, 2])],
                  [action("A01", "D2", 3, "2026-12-01", p=1.0), action("A02", "D3", 4, "2026-12-20", p=1.0),
                   action("A03", "D5", 4, "2027-01-10", p=1.0)])
        pg["roles"][0]["fit"] = 50.0
        sl = G.starting_line(pg, TODAY)
        self.assertTrue(sl["reachable"])
        self.assertEqual(sl["next_level"], 3)
        self.assertRegex(sl["next"], r"^Level 3 expected by \d+ \w{3} with (this move|these \w+ moves)\.$")

    def test_no_plan_gets_there_says_so_and_what_is_missing(self):
        pg = page([role("a", [1, 1, 0, 1, 1, 5, 0])], [])
        sl = G.starting_line(pg, TODAY)
        self.assertFalse(sl["reachable"])
        self.assertTrue(sl["next"].startswith("No plan gets you to Level"))
        self.assertIn("What is missing", sl["next"])

    def test_range_in_the_starting_line_with_and_without_it(self):
        with_range = G.starting_line(page([role("a", [2, 2, 1, 2, 2, 5, 1], fit=21.5, lo=18.0, hi=25.0)], []), TODAY)
        self.assertTrue(with_range["has_range"])
        self.assertEqual(with_range["fit_text"], "fit about 18 to 25")
        without = G.starting_line(page([role("a", [2, 2, 1, 2, 2, 5, 1])], []), TODAY)
        self.assertFalse(without["has_range"])

    def test_demo_workspace_start_line_is_honest(self):
        cfg = C.load_json(os.path.join(H.DEMO, "config.json"))
        data = B.Data(H.DEMO, cfg, None)
        sl = G.starting_line(B.build_data(data), data.cur["run_date"])
        self.assertEqual(sl["level"], 3)
        self.assertIn("next", sl)


if __name__ == "__main__":
    unittest.main()
