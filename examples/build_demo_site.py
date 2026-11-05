#!/usr/bin/env python3
"""Build docs/demo/: the fictional demos as one static folder, ready for a website.

Copies the page LVLme builds for the fictional Alex Example, unchanged,
and writes an index page that introduces it:

  docs/demo/index.html            the index page
  docs/demo/dashboard/index.html  the full campaign's dashboard (five weekly runs)
  docs/demo/dashboard/research/   its research pack for each fictional organisation

Every page is self-contained (inline styles, no fonts, images or scripts
loaded from anywhere), so the folder works opened from disk or served as
static files, for example by GitHub Pages. This script does not publish
anything or switch a website on.

It refuses to copy a page unless its workspace says "fictional": true, so a
real person's dashboard can never end up in the folder. It copies the
committed demo pages; rebuild those first if you changed the engine:

  python3 examples/build_demo.py
  python3 examples/build_demo_site.py

Usage: python3 examples/build_demo_site.py [--out FOLDER]
"""
import argparse
import html
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ENGINE, "scripts"))
import _page_html as PH  # noqa: E402

OUT = os.path.join(ENGINE, "docs", "demo")
DEMO = os.path.join(HERE, "demo-workspace")
REPO = "https://github.com/mark-hallam/lvlme"
# (folder the page is copied to, workspace it comes from, the page inside that workspace)
PAGES = [("dashboard", DEMO, os.path.join("report", "index.html"))]

CSS = PH.CSS + """
.lead{margin:0 0 4px}
ul.rows{list-style:none;margin:0;padding:0}
ul.rows li+li{border-top:1px solid var(--rule)}
ul.rows a{display:flex;align-items:center;gap:14px;padding:14px 0;color:var(--ink);text-decoration:none;min-height:44px}
ul.rows li:last-child a{padding-bottom:2px}
ul.rows p{margin:2px 0 0}
ul.rows a:hover h3,ul.rows a:focus-visible h3{color:var(--accent)}
ul.rows a:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:10px}
ul.rows .txt{flex:1;min-width:0}
ul.rows .chev{flex:none;width:9px;height:14px;color:var(--sub)}
ul.links{margin:8px 0 0;padding-left:20px}
ul.links li{padding:4px 0}
"""
CHEVRON = ('<svg class="chev" viewBox="0 0 9 14" aria-hidden="true"><path d="M1.5 1.5 L7 7 L1.5 12.5" fill="none" '
           'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def whole(v):
    return "%d" % int(v + 0.5)


def sources():
    """The workspace folder and page path for each demo page."""
    return [(name, ws, page) for name, ws, page in PAGES]


def goal_reached_page():
    """The dashboard of the same fictional person if her goal had been Level 3 (Moderate): the engine itself then records
    the goal as reached on 25 Oct, and Today shows the goal-reached moment, the share card and the next-goal offer."""
    import build_dashboard
    tmp = tempfile.mkdtemp(prefix="lvlme-goal-reached-")
    try:
        ws = os.path.join(tmp, "ws")
        shutil.copytree(DEMO, ws)
        cfg_path = os.path.join(ws, "config.json")
        cfg = load(cfg_path)
        cfg["goal"]["target_level"] = 3
        cfg["goal"]["role"] = "A program, applied AI or policy role (first target: Level 3, Moderate)"
        cfg["goal"]["by"] = "2026-12-31"
        with open(cfg_path, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2)
        levels = os.path.join(ws, "eval", "levels.json")
        if os.path.exists(levels):
            os.remove(levels)
        today = load(os.path.join(DEMO, "report", "for-agents", "dashboard.json"))["today"]["date"]
        build_dashboard.main(["--workspace", ws, "--today", today])
        with open(os.path.join(ws, "report", "index.html"), encoding="utf-8") as fh:
            return fh.read()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def check_fictional(workspace):
    """Stop unless the workspace's config.json says it is fictional."""
    path = os.path.join(workspace, "config.json")
    if not os.path.exists(path) or load(path).get("fictional") is not True:
        raise SystemExit('lvlme: %s is not marked "fictional": true, so it is not copied into the demo folder.'
                         % os.path.relpath(workspace, ENGINE))


def dashboard_line(dash):
    best = dash["levels"]["best_role"]
    org = (dash["per_org"].get(best["org"]) or {}).get("org_name", best["org"])
    return ("Latest run %s: best match %s at %s, fit %s of 100, Level %d, %s." % (
        esc(PH.long_date(dash["run_date"])), esc(best["title"]), esc(org), whole(best["fit"]),
        best["level"], esc(best["band"])))


def row(href, title, text):
    return ('<li><a href="%s"><div class="txt"><h3>%s</h3><p class="sub small">%s</p></div>%s</a></li>'
            % (href, title, text, CHEVRON))


def render(dash):
    rows = "".join([
        row("dashboard/index.html", "The full campaign dashboard",
            "Five weekly runs at three organisations: your level, the fit range for each role and what to do "
            "next. " + dashboard_line(dash)),
        row("goal-reached/index.html", "A goal reached",
            "The same made-up person if her goal had been Level 3, Moderate: the screen LVLme shows when a goal is "
            "reached, with the share card and the offer to set the next goal."),
        row("dashboard/profile/index.html", "The proof profile",
            "The page LVLme builds from checked evidence only, each claim with its source. Private until you choose "
            "to host it. The source links in this demo are made-up addresses."),
    ])
    body = (
        '<section class="card" aria-labelledby="introH"><p class="eyebrow">Demo</p>'
        '<h1 id="introH">See LVLme with made-up data</h1>'
        '<p class="lead">For the job you can\'t get yet. LVLme works out honestly how far you are from a job, '
        'turns the gap into real actions, and measures again as you go. This is the page it builds, '
        'for a fictional person.</p></section>'
        '<section class="card" aria-labelledby="pagesH"><h2 id="pagesH">Open a demo</h2>'
        '<ul class="rows">%s</ul></section>'
        '<section class="card" aria-labelledby="madeUpH"><h2 id="madeUpH">Everything here is made up</h2>'
        '<p>Alex Example, Acme AI, Globex Labs and Initech Robotics are fictional, and so are the job postings, '
        'the CV, the evidence and the scores. No real person\'s data is on these pages, and the odds say '
        'nothing about any real company\'s hiring.</p></section>'
        '<section class="card" aria-labelledby="getH"><h2 id="getH">Get LVLme</h2>'
        '<p>LVLme is free and open source. It runs in Claude Code or Codex on your own computer, keeps '
        'your files there, and drafts everything: it never applies, sends or posts for you.</p>'
        '<ul class="links"><li><a href="%s">LVLme on GitHub</a></li>'
        '<li><a href="%s/blob/HEAD/docs/INSTALL.md">How to install it</a></li>'
        '<li><a href="%s/blob/HEAD/docs/for-you/READING-YOUR-DASHBOARD.md">Reading your dashboard</a>, '
        'a one-page guide</li></ul></section>') % (rows, REPO, REPO, REPO)
    return ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<meta name=\"color-scheme\" content=\"light dark\">"
            "<meta name=\"description\" content=\"LVLme's demo page, for a fictional person.\">"
            "<title>LVLme demo</title><style>%s</style></head><body><div class=\"wrap\">"
            "<header class=\"top\"><span class=\"mark\">%s</span><b>LVLme</b>"
            "<span class=\"sub\"><span class=\"nw\">fictional demo</span></span></header><main>%s</main>"
            "<footer>Copies of the pages LVLme builds on your own computer. Rebuild this folder with "
            "python3 examples/build_demo_site.py.</footer></div></body></html>\n") % (CSS, PH.LOGO, body)


def build(out=OUT):
    """Write the demo folder at out (its pages; nothing else is touched). Returns the paths written."""
    for _name, workspace, _page in sources():
        check_fictional(workspace)
    written = []
    for name, workspace, page in sources():
        dest = os.path.join(out, name, "index.html")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(os.path.join(workspace, page), dest)
        written.append(dest)
    research = os.path.join(DEMO, "report", "research")     # the dashboard links to its research packs
    for name in sorted(os.listdir(research)) if os.path.isdir(research) else []:
        dest = os.path.join(out, "dashboard", "research", name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(os.path.join(research, name), dest)
        written.append(dest)
    reached = os.path.join(out, "goal-reached", "index.html")
    os.makedirs(os.path.dirname(reached), exist_ok=True)
    with open(reached, "w", encoding="utf-8") as fh:
        fh.write(goal_reached_page())
    written.append(reached)
    for name in sorted(os.listdir(research)) if os.path.isdir(research) else []:
        dest = os.path.join(out, "goal-reached", "research", name)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(os.path.join(research, name), dest)
        written.append(dest)
    for where in ("dashboard", "goal-reached"):       # Today links to profile/index.html next to itself
        profile = os.path.join(out, where, "profile", "index.html")
        os.makedirs(os.path.dirname(profile), exist_ok=True)
        shutil.copyfile(os.path.join(DEMO, "report", "profile", "index.html"), profile)
        written.append(profile)
    dash = load(os.path.join(DEMO, "report", "for-agents", "dashboard.json"))
    index = os.path.join(out, "index.html")
    with open(index, "w", encoding="utf-8") as fh:
        fh.write(render(dash))
    return [index] + written


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build docs/demo/ from the fictional demos.")
    ap.add_argument("--out", default=OUT, help="folder to write (default: docs/demo)")
    args = ap.parse_args(argv)
    for path in build(os.path.abspath(args.out)):
        print("wrote %s" % os.path.relpath(path))


if __name__ == "__main__":
    main()
