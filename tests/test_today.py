"""The Today screen: first on the page, plain words, one move, the next level, Mission control one tap away."""
import os
import re
import unittest

import helpers as H
import _today as T
import build_dashboard as B

FLIGHT_WORDS = ("altitude", "flight level", "flight path", "waypoint")


def build(test, tweak=None, today="2026-11-05"):
    ws = H.copy_demo(test)
    if tweak:
        tweak(ws)
    B.main(["--workspace", ws, "--today", today])
    page = open(os.path.join(ws, "report", "index.html"), encoding="utf-8").read()
    return ws, page


def today_part(page):
    start = page.index('<main class="td" id="today"')
    return page[start:page.index("</main>", start)]


def text_of(html_part):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html_part)).strip()


class TodayFirstTests(unittest.TestCase):
    def setUp(self):
        self.ws, self.page = build(self, lambda ws: None)
        self.today = today_part(self.page)
        self.body = self.page[self.page.index("<body>"):]

    def test_today_comes_before_mission_control_and_mission_control_is_one_tap_away(self):
        self.assertLess(self.body.index('id="today"'), self.body.index('<header class="top">'))
        self.assertIn('href="#mission-control"', self.today)
        self.assertIn("Open Mission control", self.today)
        self.assertIn('href="#today"', self.page)                 # and a way back
        self.assertIn("body.is-today .app", self.page)             # Today hides the full dashboard until the tap
        self.assertIn('"#mission-control"', self.page)             # the script that switches

    def test_without_javascript_both_screens_are_readable(self):
        # neither class is there until the script adds it, and the rules hide a screen only under a class
        self.assertNotIn("body.td", self.page)
        self.assertIn("body.is-mc #today{display:none}", self.page)
        self.assertNotIn('<body class="is-today"', self.page)

    def test_the_four_answers_are_on_the_screen_in_plain_words(self):
        words = text_of(self.today)
        self.assertIn("Level 3, Moderate", words)
        self.assertIn("You are at Level 3, Moderate. Your best match is", words)
        self.assertIn("Your one move today", words)
        self.assertIn("Next level", words)
        self.assertIn("Done? Tell your agent", words)
        for flight in FLIGHT_WORDS:
            self.assertNotIn(flight, words.lower())

    def test_one_h1_and_the_buttons_are_44_points_tall(self):
        self.assertEqual(len(re.findall(r"<h1[\s>]", self.today)), 1)
        self.assertIn("min-height:44px", T.CSS)

    def test_works_at_390_px(self):
        self.assertIn("@media (max-width:420px)", T.CSS)
        self.assertIn("max-width:600px", T.CSS)

    def test_dark_mode_is_built(self):
        # Today uses the page's own colour variables, which the dark theme redefines
        self.assertIn("var(--bg)", T.CSS)
        self.assertIn(":root[data-theme=dark]", self.page)

    def test_the_one_move_is_the_top_open_move_that_is_not_a_stale_posting(self):
        move = H.load(os.path.join(self.ws, "report", "for-agents", "dashboard.json"))["today"]["move"]
        self.assertTrue(move["title"])
        self.assertIn(move["id"], text_of(move["tell"]))
        self.assertNotIn("stale or reposted", move["why"])


class RangeTests(unittest.TestCase):
    def test_demo_best_role_judged_twice_shows_a_range(self):
        ws, page = build(self, lambda ws: None, today="2026-10-10")
        self.assertIn("fit about 57 to 61 out of 100", text_of(today_part(page)))
        self.assertNotIn("One judging so far", text_of(today_part(page)))

    def test_single_fit_when_the_run_file_has_no_range(self):
        def tweak(ws):
            path = os.path.join(ws, "eval", "runs", "2026-11-01.json")
            run = H.load(path)
            for r in run["roles"]:
                r.pop("fit_low", None)
                r.pop("fit_high", None)
            H.save(path, run)
        ws, page = build(self, tweak, today="2026-10-10")
        self.assertIn("fit 57 out of 100", text_of(today_part(page)))
        self.assertIn("One judging so far", text_of(today_part(page)))

    def test_range_shows_when_the_run_file_carries_fit_low_and_fit_high(self):
        def tweak(ws):
            path = os.path.join(ws, "eval", "runs", "2026-11-01.json")
            run = H.load(path)
            for r in run["roles"]:
                r["fit_low"], r["fit_high"] = r["fit"] - 3, r["fit"] + 4
            H.save(path, run)
        ws, page = build(self, tweak, today="2026-10-10")
        words = text_of(today_part(page))
        self.assertIn("fit about 54 to 61 out of 100", words)
        self.assertNotIn("One judging so far", words)
        dash = H.load(os.path.join(ws, "report", "for-agents", "dashboard.json"))
        self.assertEqual(dash["today"]["start_line"]["fit_low"], 54.0)


class StartingLineTests(unittest.TestCase):
    def test_starting_line_shows_for_the_first_two_weeks_only(self):
        _, early = build(self, lambda ws: None, today="2026-10-10")
        self.assertIn("Your starting line", text_of(today_part(early)))
        _, late = build(self, lambda ws: None, today="2026-11-05")
        self.assertNotIn("Your starting line", text_of(today_part(late)))

    def test_a_run_count_of_two_or_fewer_also_shows_it(self):
        def tweak(ws):
            for name in ("2026-10-11", "2026-10-18", "2026-10-25", "2026-11-01"):
                os.remove(os.path.join(ws, "eval", "runs", name + ".json"))
        _, page = build(self, tweak, today="2026-12-20")
        self.assertIn("Your starting line", text_of(today_part(page)))


class MomentTests(unittest.TestCase):
    def test_level_up_is_marked_with_a_share_card_that_has_no_names(self):
        _, page = build(self, lambda ws: None, today="2026-11-05")
        part = today_part(page)
        self.assertIn("Levelled up: Level 2, Low to Level 3, Moderate", text_of(part))
        card = re.search(r'data-head="([^"]*)" data-line="([^"]*)"', part)
        shown = card.group(1) + " " + card.group(2)
        for private in ("Acme", "Globex", "Initech", "Alex", "Sample", "Robot"):
            self.assertNotIn(private, shown)

    def test_no_marker_when_the_level_up_is_old(self):
        _, page = build(self, lambda ws: None, today="2026-12-30")
        self.assertNotIn("Levelled up", text_of(today_part(page)))

    def test_goal_reached_offers_the_next_goal(self):
        def tweak(ws):
            cfg = H.load(os.path.join(ws, "config.json"))
            cfg["goal"]["target_level"] = 3
            H.save(os.path.join(ws, "config.json"), cfg)
        _, page = build(self, tweak)
        words = text_of(today_part(page))
        self.assertIn("Goal reached: Level 3, Moderate", words)
        self.assertIn("You reached your goal.", words)
        self.assertIn("Set my next goal", words)


class CheckingAndStoneTests(unittest.TestCase):
    def test_what_is_still_being_checked_is_said(self):
        _, page = build(self, lambda ws: None)
        words = text_of(today_part(page))
        self.assertIn("Still being checked", words)
        self.assertIn("1 of 12 open roles is still being judged", words)
        self.assertIn("1 score is waiting for the blind review and counts as 2", words)

    def test_a_stepping_stone_is_a_choice_and_a_choice_is_remembered(self):
        def tweak(ws):
            cfg = H.load(os.path.join(ws, "config.json"))
            cfg["goal"].update(role="Applied AI", by="2027-01-31", target_level=5)
            H.save(os.path.join(ws, "config.json"), cfg)
        ws, page = build(self, tweak)
        words = text_of(today_part(page))
        self.assertIn("A stepping stone to consider", words)
        self.assertIn("Take the stepping stone", words)
        self.assertIn("Keep my goal", words)
        self.assertIn("Your goal stays as it is until you do", words)
        import goal as GL
        import io
        from contextlib import redirect_stdout
        with redirect_stdout(io.StringIO()):
            GL.main(["--workspace", ws, "check", "--date", "2026-11-05"])
            GL.main(["--workspace", ws, "stone", "decline", "--date", "2026-11-05"])
            B.main(["--workspace", ws, "--today", "2026-11-05"])
        again = text_of(today_part(open(os.path.join(ws, "report", "index.html"), encoding="utf-8").read()))
        self.assertNotIn("A stepping stone to consider", again)

    def test_the_waiting_state_when_nothing_is_judged(self):
        t = {"date": "2026-11-05", "goal": "Customer success", "state": "waiting", "stand": "Your first result is on its way.",
             "weeks_in_a_row": 0}
        self.assertIn("Your first result is on its way", T.render(t))


class WeekCardTests(unittest.TestCase):
    """The weekly rhythm is visible on Today: Monday's plan, Friday's review, and what counts as a week."""

    def write_notes(self, ws):
        import _autopilot as A
        import _weekly as WK
        cfg = H.load(os.path.join(ws, "config.json"))
        dash = H.load(os.path.join(ws, "report", "for-agents", "dashboard.json"))
        A.write_note(ws, cfg, "2026-11-02", "2026-11-02")
        WK.write_review(ws, cfg, "2026-10-30", "2026-11-05", dash)

    def test_this_week_card_shows_the_monday_plan_and_the_friday_review(self):
        ws, page = build(self, self.write_notes)
        import html
        words = html.unescape(text_of(today_part(page)))
        self.assertIn("This week", words)
        self.assertIn("Monday plan, 2 Nov", words)
        self.assertIn("Friday review, week of 26 Oct", words)
        self.assertIn("Done with evidence", words)
        self.assertIn("Next week's one move", words)
        dash = H.load(os.path.join(ws, "report", "for-agents", "dashboard.json"))
        self.assertEqual(dash["today"]["week"]["plan"]["date"], "2026-11-02")      # the newer note than the demo's own
        self.assertEqual(dash["today"]["week"]["review"]["week_of"], "2026-10-26")

    def test_with_no_notes_yet_it_says_what_will_appear_and_how_to_get_it(self):
        import glob
        ws, page = build(self, lambda ws: [os.remove(f) for f in glob.glob(os.path.join(ws, "campaign", "weekly", "*.json"))])
        words = text_of(today_part(page))
        self.assertIn("This week", words)
        self.assertIn("Your Monday plan and Friday review appear here", words)
        self.assertIn("Ask your agent", words)

    def test_next_level_says_what_a_point_is_and_where_the_next_level_starts(self):
        ws, page = build(self, lambda ws: None)
        words = text_of(today_part(page))
        self.assertIn("Fit is scored out of 100. Level 4, Good starts at 70.", words)
        self.assertIn("On expected odds your plan gets your best match to about 63, and 70 is needed.", words)

    def test_the_proof_profile_card_links_to_the_page_and_says_it_is_private(self):
        ws, page = build(self, lambda ws: None)
        today = today_part(page)
        self.assertIn('href="profile/index.html"', today)
        self.assertIn("It is private", text_of(today))
        self.assertIn("Publish it myself", text_of(today))

    def test_the_move_shows_the_sentence_the_button_copies(self):
        ws, page = build(self, lambda ws: None)
        words = text_of(today_part(page))
        self.assertIn("The button copies this for your agent:", words)

    def test_the_streak_says_what_counts_as_a_week(self):
        ws, page = build(self, lambda ws: None)
        self.assertIn("A week counts when a move is finished or evidence is checked", text_of(today_part(page)))


class DarkThemeAndPrivacyTests(unittest.TestCase):
    def test_today_data_reaches_the_agents_file(self):
        ws, _ = build(self, lambda ws: None)
        dash = H.load(os.path.join(ws, "report", "for-agents", "dashboard.json"))
        self.assertEqual(dash["today"]["level"], 3)
        self.assertIn("weeks_in_a_row", dash["today"])


if __name__ == "__main__":
    unittest.main()
