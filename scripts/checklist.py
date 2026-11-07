#!/usr/bin/env python3
"""Build and mark per-job requirement checklists beside today's fit.

The agent supplies extraction reads and evidence marks as JSON files; this
script stores them in eval/checklists.json, merges reads, and reports the
verdict from scripts/_checklist.py. See method/CHECKLIST.md.

Usage
  python3 scripts/checklist.py status [--json]
  python3 scripts/checklist.py posting ROLE_ID
  python3 scripts/checklist.py extract ROLE_ID --read FILE
  python3 scripts/checklist.py mark ROLE_ID --read FILE
  python3 scripts/checklist.py confirm ROLE_ID [--rows FILE]
  python3 scripts/checklist.py show ROLE_ID [--json]
  python3 scripts/checklist.py drop ROLE_ID
Every command takes --workspace PATH. FILE may be '-' for standard input.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402
import _checklist as K  # noqa: E402
import validate as V  # noqa: E402

REL = ("eval", "checklists.json")
VERDICTS = frozenset(("met", "partly", "not_shown", "unknown", "not_applicable"))
_SCHEMA = None


def _schema():
    global _SCHEMA
    if _SCHEMA is None:
        _SCHEMA = C.load_json(os.path.join(C.SCHEMA_DIR, "checklists.schema.json"))
    return _SCHEMA


def _norm(text):
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _load(ws):
    path = C.wpath(ws, *REL)
    doc = C.load_json(path, None)
    if doc is None:
        return path, {"schema_version": 1, "roles": {}}
    return path, doc


def _refuse(msg):
    print("lvlme: %s" % msg, file=sys.stderr)
    raise SystemExit(1)


def _check_doc(doc):
    errs = V.check(doc, _schema())
    if errs:
        _refuse("eval/checklists.json: %s" % errs[0])


def _save(path, doc):
    _check_doc(doc)
    C.write_json(path, doc)


def _role(ws, rid):
    roles_doc = C.load_json(C.wpath(ws, "market", "roles", "latest.json"), None) or {}
    found = next((r for r in roles_doc.get("roles", []) if r.get("id") == rid), None)
    if found is None:
        _refuse("no role %s in market/roles/latest.json." % rid)
    return found


def _entry(doc, rid, create=False):
    roles = doc.setdefault("roles", {})
    if rid not in roles:
        if not create:
            _refuse("no checklist for %s yet. Run extract first." % rid)
        roles[rid] = {"corrected": False, "rows": [], "votes": {}, "reads": [], "marks": []}
    entry = roles[rid]
    entry.setdefault("reads", [])
    entry.setdefault("marks", [])
    entry.setdefault("votes", {})
    entry.setdefault("rows", [])
    return entry


def posting_text(role):
    lines = ["%s (%s)" % (role.get("title") or "Untitled", role.get("org") or "?")]
    if role.get("description_text"):
        lines.append(role["description_text"])
    for label, key in (("Hard requirements", "hard_requirements"), ("Nice to haves", "nice_to_haves")):
        items = [x for x in (role.get(key) or []) if x]
        if items:
            lines.append(label + ":")
            lines.extend(items)
    return "\n\n".join(lines)


def _read_rows(path):
    try:
        raw = C.read_input(path, "read file")
        doc = json.loads(raw)
    except C.FileProblem as exc:
        _refuse(str(exc))
    except json.JSONDecodeError as exc:
        _refuse("read file is not valid JSON (%s)." % exc)
    rows = doc.get("rows")
    if not isinstance(rows, list):
        _refuse("read file needs a rows array.")
    return rows


def _strip_for_read(rows):
    out = []
    for row in rows:
        if not isinstance(row, dict) or not (row.get("text") or "").strip():
            continue
        item = {k: row[k] for k in ("text", "strength", "type", "inferred", "applies") if k in row}
        item.setdefault("strength", "should")
        item.setdefault("type", "skill")
        item.setdefault("inferred", False)
        item.setdefault("applies", "everyone")
        out.append(item)
    return out


def rebuild_votes(rows, marks):
    ids = [r["id"] for r in rows]
    votes = {rid: [] for rid in ids}
    for mark_pass in marks or []:
        for rid in ids:
            hit = mark_pass.get(rid)
            if hit and hit.get("verdict"):
                votes[rid].append(hit["verdict"])
    return votes


def _evidence_ids(ws):
    ev = C.load_json(C.wpath(ws, "profile", "evidence.json"), None) or {}
    return {e.get("id") for e in ev.get("items", []) if e.get("id")}


def _verdict_line(entry):
    result = K.score_checklist(entry.get("rows") or [], entry.get("votes") or {})
    shown = result["shown"]
    return shown["verdict"], shown


def cmd_status(ws, config, as_json):
    jud = C.load_json(C.wpath(ws, "eval", "judgements.json"), None) or {}
    judged = sorted((jud.get("roles") or {}).keys())
    _, doc = _load(ws)
    saved = doc.get("roles") or {}
    rows_out = []
    for rid in judged:
        entry = saved.get(rid)
        if not entry:
            rows_out.append({"role_id": rid, "reads": 0, "marks": 0, "corrected": False, "has_checklist": False})
            continue
        verdict = None
        if entry.get("marks"):
            verdict, _ = _verdict_line(entry)
        rows_out.append({
            "role_id": rid,
            "reads": len(entry.get("reads") or []),
            "marks": len(entry.get("marks") or []),
            "corrected": bool(entry.get("corrected")),
            "verdict": verdict,
            "has_checklist": True,
        })
    missing = [rid for rid in judged if rid not in saved]
    payload = {"judged": rows_out, "no_checklist": missing}
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    for row in rows_out:
        if not row["has_checklist"]:
            print("%s: no checklist yet" % row["role_id"])
            continue
        bits = ["reads %d/3" % row["reads"], "marks %d/3" % row["marks"],
                "corrected %s" % ("yes" if row["corrected"] else "no")]
        if row.get("verdict"):
            bits.append("verdict %s" % row["verdict"])
        print("%s: %s" % (row["role_id"], ", ".join(bits)))


def cmd_extract(ws, config, rid, read_path, today):
    path, doc = _load(ws)
    entry = _entry(doc, rid, create=True)
    rows_in = _strip_for_read(_read_rows(read_path))
    if not rows_in:
        _refuse("read file has no requirement rows.")
    reads = list(entry.get("reads") or [])
    reads.append(rows_in)
    if len(reads) > 3:
        reads = reads[-3:]
    entry["reads"] = reads
    entry["extracted_on"] = today
    if not entry.get("corrected"):
        merged = K.merge_extracts(reads)
        entry["rows"] = merged
        entry["votes"] = rebuild_votes(merged, entry.get("marks"))
    _save(path, doc)
    print(json.dumps(entry["rows"], indent=2, ensure_ascii=False))
    print("%d read(s) saved." % len(reads))
    if len(reads) == 1 and not entry.get("corrected"):
        print("Provisional list: add a second independent read before you treat this as the job list.")


def cmd_mark(ws, config, rid, read_path):
    path, doc = _load(ws)
    entry = _entry(doc, rid)
    rows = entry.get("rows") or []
    if not rows:
        _refuse("%s has no rows yet. Run extract first." % rid)
    row_ids = {r["id"] for r in rows}
    body = _read_rows(read_path)
    mark_pass = {}
    for item in body:
        if not isinstance(item, dict):
            _refuse("each mark row must be an object.")
        rid_row = item.get("row")
        verdict = item.get("verdict")
        if rid_row not in row_ids:
            _refuse("unknown row %s (rows: %s)." % (rid_row, ", ".join(sorted(row_ids))))
        if verdict not in VERDICTS:
            _refuse("bad verdict %r on %s (use met, partly, not_shown, unknown, not_applicable)."
                    % (verdict, rid_row))
        mark_pass[rid_row] = {
            "verdict": verdict,
            "evidence": list(item.get("evidence") or []),
            "quote": item.get("quote") or "",
        }
    known = _evidence_ids(ws)
    for rid_row, detail in mark_pass.items():
        for eid in detail["evidence"]:
            if eid not in known:
                print("lvlme: note: %s cites evidence %s, which is not in profile/evidence.json." % (rid_row, eid),
                      file=sys.stderr)
    marks = list(entry.get("marks") or [])
    marks.append(mark_pass)
    if len(marks) > 3:
        marks = marks[-3:]
    entry["marks"] = marks
    entry["votes"] = rebuild_votes(rows, marks)
    _save(path, doc)
    verdict, shown = _verdict_line(entry)
    print(json.dumps({k: shown[k] for k in ("verdict", "must_line", "moves", "questions", "todos") if k in shown},
                     indent=2, ensure_ascii=False))
    print("Verdict: %s" % verdict)


def cmd_confirm(ws, config, rid, rows_path, today):
    path, doc = _load(ws)
    entry = _entry(doc, rid)
    old_rows = list(entry.get("rows") or [])
    old_by_norm = {_norm(r.get("text")): r["id"] for r in old_rows}
    if rows_path:
        new_raw = _strip_for_read(_read_rows(rows_path))
        if not new_raw:
            _refuse("rows file has no requirements.")
        new_rows = []
        for i, row in enumerate(new_raw, 1):
            item = dict(row)
            item["id"] = "R%d" % i
            new_rows.append(item)
        new_by_norm = {_norm(r.get("text")): r["id"] for r in new_rows}
        keep_ids = set(new_by_norm.values())
        marks = []
        for mark_pass in entry.get("marks") or []:
            remapped = {}
            for old_id, detail in mark_pass.items():
                old_row = next((r for r in old_rows if r["id"] == old_id), None)
                if old_row is None:
                    continue
                new_id = new_by_norm.get(_norm(old_row.get("text")))
                if new_id:
                    remapped[new_id] = detail
            if remapped:
                marks.append(remapped)
        entry["rows"] = new_rows
        entry["marks"] = marks
        entry["votes"] = rebuild_votes(new_rows, marks)
        still = [r["id"] for r in new_rows if not (entry["votes"].get(r["id"]) or [])]
        entry["corrected"] = True
        _save(path, doc)
        if still:
            print("Confirmed. Rows still needing marks: %s" % ", ".join(still))
        else:
            print("Confirmed. Every row has at least one mark.")
        return
    entry["corrected"] = True
    _save(path, doc)
    print("Confirmed. The person agreed this is what the job asks for.")


def cmd_show(ws, config, rid, as_json):
    _, doc = _load(ws)
    entry = _entry(doc, rid)
    verdict, shown = _verdict_line(entry)
    payload = {
        "rows": entry.get("rows") or [],
        "votes": entry.get("votes") or {},
        "corrected": bool(entry.get("corrected")),
        "verdict": verdict,
        "shown": shown,
        "reads": len(entry.get("reads") or []),
        "marks": len(entry.get("marks") or []),
    }
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return
    for row in entry.get("rows") or []:
        print("%s  %s  %s  %s" % (row["id"], row.get("strength"), row.get("type"), row.get("text")))
    print("Votes: %s" % json.dumps(entry.get("votes") or {}, ensure_ascii=False))
    print("Verdict: %s" % verdict)
    print("Must-haves: %s" % shown.get("must_line"))
    for q in shown.get("questions") or []:
        print("Question: %s" % q)


def cmd_drop(ws, config, rid):
    path, doc = _load(ws)
    if rid not in (doc.get("roles") or {}):
        _refuse("no checklist for %s." % rid)
    del doc["roles"][rid]
    if doc["roles"]:
        _save(path, doc)
    elif os.path.exists(path):
        os.remove(path)
    print("Removed checklist for %s." % rid)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", help="workspace folder (default: $LVLME_HOME)")
    ap.add_argument("--json", action="store_true", help="machine-readable JSON on supported commands")
    sub = ap.add_subparsers(dest="command", required=True)

    sub.add_parser("status")
    for name in ("posting", "show", "drop"):
        p = sub.add_parser(name)
        p.add_argument("role_id")
    p = sub.add_parser("extract")
    p.add_argument("role_id")
    p.add_argument("--read", required=True, help="JSON with rows, or '-' for standard input")
    p = sub.add_parser("mark")
    p.add_argument("role_id")
    p.add_argument("--read", required=True)
    p = sub.add_parser("confirm")
    p.add_argument("role_id")
    p.add_argument("--rows", help="replace rows after the person's edits (renumbered)")
    args = ap.parse_args(argv)
    ws, config = C.open_workspace(args.workspace)
    today = C.today_in(config)
    if args.command == "status":
        cmd_status(ws, config, args.json)
    elif args.command == "posting":
        print(posting_text(_role(ws, args.role_id)))
    elif args.command == "extract":
        cmd_extract(ws, config, args.role_id, args.read, today)
    elif args.command == "mark":
        cmd_mark(ws, config, args.role_id, args.read)
    elif args.command == "confirm":
        cmd_confirm(ws, config, args.role_id, args.rows, today)
    elif args.command == "show":
        cmd_show(ws, config, args.role_id, args.json)
    else:
        cmd_drop(ws, config, args.role_id)
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main))
