"""The page leads with job match while retaining fit for levels and bands."""
import json
import shutil
import subprocess
import unittest

import helpers as H  # noqa: F401
import _dashboard_assets as A

NODE = shutil.which("node")


def function(source, name):
    start = source.index("function " + name + "(")
    line = source[start:source.index("\n", start)]
    if line.endswith("}"):
        return line
    return source[start:source.index("\n}\n", start) + 3]


@unittest.skipUnless(NODE, "Node.js is not installed")
class HeadlineDisplayTests(unittest.TestCase):
    def run_js(self, body):
        helpers = "\n".join(function(A.JS_CORE, n) for n in ("matchLeads", "headlineValue", "allMatch"))
        result = subprocess.run([NODE, "-"], input=helpers + "\n" + body,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_tile_uses_best_job_match_only_when_all_judged_roles_in_focus_use_match(self):
        body = r'''
const nodes = {}, $ = id => nodes[id] || (nodes[id] = {querySelectorAll: () => []});
const state = {org: "best", sample: false};
const D = {meta: {baseline: "2026-11-01"}, orgs: {a: {name: "Acme"}, b: {name: "Globex"}}};
const a = {id: "a", g: "a", on: "Acme", title: "First", judged: true, fit: 50, h: {kind: "match", value: 70}};
const b = {id: "b", g: "b", on: "Globex", title: "Second", judged: true, fit: 40, h: {kind: "match", value: 90}};
const u = {id: "u", g: "a", judged: false, fit: 95, h: {kind: "fit", value: 95}};
let roles = [a, b, u];
const journeyRoles = () => state.org === "best" ? roles : roles.filter(r => r.g === state.org);
const headlineRole = () => a, jp = () => ({exp: {pts: []}}), TODAY = "2026-11-07", T0 = 0;
const tOf = () => 0, bandIdx = () => 0, THRESH = [0], BANDS = ["Very low"];
const fmtDate = x => x, esc = x => x, modeName = () => "today", fitM = r => r.fit;
const ibM = r => "fit " + r.fit, obM = ibM, pill = x => x;
const countTo = (node, n) => node.textContent = n;
const lv = () => ({nl: {fit: 50}}), levelCardHTML = nl => "level from fit " + nl.fit, enter = () => {};
'''
        body += function(A.JS_CORE, "renderTopline") + r'''
const capture = () => { renderTopline(); return [$("#bestLabel").textContent, $("#bestNum").textContent,
    $("#bestWhy").textContent, $("#bestRole").textContent, $("#level").innerHTML]; };
const results = [capture()];
b.h.kind = "fit"; results.push(capture());
state.org = "a"; results.push(capture());
state.org = "best"; roles = [u]; results.push(allMatch(roles));
roles = [a]; delete a.h; results.push(capture());
console.log(JSON.stringify(results));
'''
        all_match, mixed, focused, empty, legacy = self.run_js(body)
        self.assertEqual(all_match[:4], ["Best job match today", 90, "Fit waits for your answers about who you know.", "Globex: Second"])
        # Mixed and historical runs retain the existing fit display and projection behaviour.
        self.assertEqual(mixed[:3], ["Best match today", 95, ""])
        self.assertEqual(focused[:3], ["Best job match today", 70, "Fit waits for your answers about who you know."])
        self.assertFalse(empty)
        self.assertEqual(legacy[:3], ["Best match today", 50, ""])
        for result in (all_match, mixed, focused, legacy):
            self.assertEqual(result[4], "level from fit 50")

    def test_role_detail_and_list_lead_with_job_match_and_return_to_fit(self):
        body = r'''
const r = {id: "a", org: "a", g: "a", on: "Acme", title: "Role", family: "tpm", loc: [],
    judged: true, fit: 40, m: 80, s: [], n: [], awaiting: [], adj: [], hardReq: [],
    h: {kind: "match", value: 80, why: "Fit waits for your answer about who you know at Acme."}};
const roleById = {a: r}, P = {a: {exp: {end: 55}, best: {end: 70}}};
const D = {roles: [r], families: {}, dims: []}, DIMS = [], W = [];
const esc = x => x, pill = x => x, interviewBand = () => "Low", fitM = r => r.fit;
const roleFilter = {}, nodes = {}, $ = id => nodes[id] || (nodes[id] = {querySelectorAll: () => []});
const scoresM = r => r.s, plural = n => n + " roles", orgColour = () => "blue", bindTips = () => {};
'''
        body += function(A.JS_DETAIL, "detailRole") + "\n" + function(A.JS_VIEWS, "fillHeat") + r'''
fillHeat(); const match = detailRole("a"), matchList = $("#heatWrap").innerHTML;
r.h.kind = "fit"; fillHeat();
console.log(JSON.stringify([match, matchList, detailRole("a"), $("#heatWrap").innerHTML]));
'''
        match, match_list, fit, fit_list = self.run_js(body)
        self.assertLess(match.index("Job match"), match.index('<b>80</b>'))
        self.assertLess(match.index('<b>80</b>'), match.index('<span>Fit</span>'))
        self.assertIn("Fit waits for your answer about who you know at Acme.", match)
        self.assertIn('<th>Job match</th>', match_list)
        self.assertIn('>80</div>', match_list)
        self.assertIn('<b>40</b>', fit)
        self.assertNotIn("Fit waits", fit)
        self.assertIn('<th>Fit</th>', fit_list)
        self.assertIn('>40</div>', fit_list)
