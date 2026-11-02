"""The static summary: the dashboard's key numbers, rendered once in Python for readers without JavaScript.

build_dashboard.py puts it under the journey card. It shows what the latest run
and the plan say, with every open action at its plan setting (the same default
the live page and the agent briefing use): the best chance today with its bands,
the level and the points to the next one, the outlook, today's top actions (the
plan's highest priority open actions) and the best role at each organisation.

The page script hides it once it has drawn the live page, which shows the same
numbers and lets the what-if switches change them, so with JavaScript on nobody
reads them twice. Plain semantic HTML: headings, a list and tables with header
cells, so a screen reader or a text browser reads it in order.
"""
import html

import _levels as L
import _levels_html as LH

TOP_ACTIONS = 3


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def whole(v):
    return "%d" % int(v + 0.5)


def _key_numbers(page, nl):
    r = page["roles"][0]
    o = page["meta"]["outlook"]
    rows = [("Best chance today", "%s / 100 fit: %s, %s. Interview chance %s, offer chance %s." % (
        whole(r["fit"]), esc(r["on"]), esc(r["title"]), esc(r["ib"]), esc(r["ob"])))]
    if nl["top"]:
        rows.append(("Level", "Level %d, %s. Top level." % (nl["level"], esc(nl["band"]))))
    else:
        rows.append(("Level", "Level %d, %s. %s %s to Level %d, %s. %s" % (
            nl["level"], esc(nl["band"]), LH.fp(nl["points_to_next"]), "point" if nl["points_to_next"] == 1 else "points",
            nl["next_level"], esc(nl["next_band"]), esc(LH.nl_line(nl, page["meta"]["run_date"])))))
    rows.append(("Outlook", "%s within %d months. %s" % (esc(o["band"]), page["meta"]["horizon"], esc(o["text"]))))
    body = "".join('<tr><th scope="row">%s</th><td>%s</td></tr>' % (k, v) for k, v in rows)
    return '<table aria-label="Key numbers"><tbody>%s</tbody></table>' % body


def _actions(page, order):
    by_id = {a["id"]: a for a in page["actions"]}
    acts = [by_id[i] for i in order if i in by_id][:TOP_ACTIONS]
    if not acts:
        return '<p class="small sub">No open actions. The next run adds some from the biggest gaps.</p>'
    items = "".join('<li><b>%s</b> <span class="sub">(%s)</span><div class="small sub">%s%s · %s · %d%% chance it works. '
                    'Done when: %s</div></li>' % (
                        esc(a["title"]), esc(a["id"]), esc(a["owner"]), " · " + esc(a["effort"]) if a.get("effort") else "",
                        "target " + LH.long_date(a["date"]) if a.get("dated") else "no target date yet", L.pct(a["p"]),
                        esc(a.get("done_when"))) for a in acts)
    return "<ol>%s</ol>" % items


def _per_org(page, per_org):
    by_id = {r["id"]: r for r in page["roles"]}
    rows = []
    for oid, name in page["orgNames"].items():
        best = by_id.get((per_org.get(oid) or {}).get("role_id"))
        if best is None:
            rows.append('<tr><th scope="row">%s</th><td colspan="4" class="sub">No matching open role</td></tr>' % esc(name))
            continue
        rows.append('<tr><th scope="row">%s</th><td>%s</td><td class="num">%s</td><td>%s</td><td>%s</td></tr>' % (
            esc(name), esc(best["title"]), whole(best["fit"]), esc(best["ib"]), esc(best["ob"])))
    return ('<table aria-labelledby="staticOrgsH"><thead><tr><th scope="col">Organisation</th><th scope="col">Best role</th>'
            '<th scope="col">Fit</th><th scope="col">Interview chance</th><th scope="col">Offer chance</th></tr></thead>'
            '<tbody>%s</tbody></table>') % "".join(rows)


def render(page, per_org, action_order):
    """The inner HTML of <section id="staticSummary">.

    page: the page data build_dashboard.py renders from (already scrubbed of contact names);
    per_org: the latest run's per_org block; action_order: open action ids, highest priority first."""
    head = '<h2 id="staticSummaryH">Your numbers on %s</h2>' % LH.long_date(page["meta"]["run_date"])
    note = ('<p class="small sub">The key numbers as plain text, for reading without JavaScript. The interactive page '
            'shows the same numbers and adds the journey chart, the What if switches and the other views.</p>')
    if not page["roles"]:
        return head + note + '<p class="small">No open roles matched yet. Fetch roles and score a run, then build the dashboard again.</p>'
    r = page["roles"][0]
    nl = L.next_level(r, page["actions"], page["caps"], page["weights"], page["meta"]["run_date"])
    return (head + note + _key_numbers(page, nl)
            + '<h3>Today\'s actions</h3>' + _actions(page, action_order)
            + '<h3 id="staticOrgsH">Best role at each organisation</h3>' + _per_org(page, per_org))
