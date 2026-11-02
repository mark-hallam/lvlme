"""eval/reviews/<date>.json: the dispute log for the middle-of-three rule (method/REVIEW.md), schema and cross-file checks."""
import os
import unittest

import helpers as H
import validate as V

DATE = "2026-10-26"


def score(n, anchor="D2 anchor %d", evidence=("E04", "E15"), by="reviewer"):
    return {"score": n, "anchor": anchor % n if "%d" in anchor else anchor, "evidence": list(evidence), "by": by}


def dispute(**kw):
    d = {"item_id": "initech:i-0001/D2", "scorer": score(4, by="scorer"), "reviewer": score(3),
         "tie_break": score(3, by="tie-break reviewer"), "stands": 3, "decided_by": "middle_of_three"}
    d.update(kw)
    return d


class ReviewLogTests(unittest.TestCase):
    def setUp(self):
        self.ws = H.copy_demo(self)

    def write(self, disputes, date=DATE, name=DATE, **top):
        doc = {"schema_version": 1, "date": date, "rubric_version": "1.0", "disputes": disputes}
        doc.update(top)
        H.save(os.path.join(self.ws, "eval", "reviews", "%s.json" % name), doc)

    def result(self):
        errors, warnings, checked = V.validate_workspace(self.ws)
        return "\n".join(errors), "\n".join(warnings), checked

    def test_a_middle_of_three_dispute_validates(self):
        self.write([dispute()], x_reviewers=["fresh agent 1", "fresh agent 2"])
        errors, warnings, checked = self.result()
        self.assertEqual(errors, "")
        self.assertIn("eval/reviews/%s.json" % DATE, checked)
        self.assertNotIn("dispute", warnings)

    def test_the_middle_must_stand(self):
        self.write([dispute(stands=4)])
        self.assertIn("the middle of [4, 3, 3] is 3, but 4 stands", self.result()[0])
        self.write([dispute(scorer=score(1, by="scorer"), reviewer=score(4), tie_break=score(2), stands=2)])
        errors, warnings, _ = self.result()
        self.assertEqual(errors, "")                       # 1, 4, 2: the middle is 2, no built-in downward bias
        self.assertIn("2 stands, but the judgement file has 3", warnings)

    def test_tie_break_absent_is_recorded_not_invented(self):
        absent = {"absent": True, "why": "Decided before the middle-of-three rule; no second reviewer ran."}
        self.write([dispute(tie_break=absent, decided_by="middle_of_three")])
        self.assertIn("no tie-break score", self.result()[0])
        self.write([dispute(tie_break=absent, decided_by="earlier_rule", note="Lower of two stood.")])
        self.assertEqual(self.result()[0], "")
        self.write([dispute(tie_break=absent, decided_by="awaiting_tie_break", stands=3)])
        errors, warnings, _ = self.result()
        self.assertEqual(errors, "")
        self.assertIn("still awaiting a tie-break, but the judgement entry is marked reviewed", warnings)
        self.write([dispute(decided_by="awaiting_tie_break")])
        self.assertIn("awaiting a tie-break, but a tie-break score is recorded", self.result()[0])
        self.write([dispute(tie_break={"absent": True})])
        self.assertIn("does not match any of the allowed forms", self.result()[0])

    def test_file_date_evidence_and_item_ids(self):
        self.write([dispute()], date="2026-10-27")
        self.assertIn("date 2026-10-27 does not match the file name", self.result()[0])
        self.write([dispute(reviewer=score(3, evidence=["E99"]))])
        self.assertIn("the reviewer cites evidence E99", self.result()[0])
        self.write([dispute(item_id="initech:nope/D2"), dispute(item_id="D3/initech", scorer=score(1), reviewer=score(0),
                                                                  tie_break=score(0), stands=0)])
        errors, warnings, _ = self.result()
        self.assertEqual(errors, "")
        self.assertIn("(initech:nope/D2): no such judgement entry", warnings)
        self.assertNotIn("(D3/initech): no such", warnings)
        self.write([dispute(item_id="initech:i-0001/D3")])
        self.assertIn("does not match the pattern", self.result()[0])

    def test_anchors_and_agreement(self):
        self.write([dispute(reviewer={"score": 3, "evidence": []}), dispute(reviewer=score(4))])
        _, warnings, _ = self.result()
        self.assertIn("the reviewer's score names no rubric anchor", warnings)
        self.assertIn("the scorer and the reviewer agree, so it is not a dispute", warnings)

    def test_a_later_judgement_makes_the_dispute_history(self):
        self.write([dispute(stands=2, scorer=score(4), reviewer=score(2), tie_break=score(2))])
        self.assertIn("2 stands, but the judgement file has 3", self.result()[1])
        jud = H.load(os.path.join(self.ws, "eval", "judgements.json"))
        jud["roles"]["initech:i-0001"]["judged_on"] = "2026-10-30"   # re-judged on new evidence since
        H.save(os.path.join(self.ws, "eval", "judgements.json"), jud)
        self.assertNotIn("stands, but", self.result()[1])


if __name__ == "__main__":
    unittest.main()
