#!/usr/bin/env python3
"""Create a private workspace for one goal from the templates/ skeleton.

The workspace holds all personal data and lives outside the engine repo:
  --workspace PATH, else $LVLME_HOME, else ~/lvlme-workspaces/<goal-slug>
(the old names $CLIMB_HOME and ~/climb-workspaces still work: see _common.py)

The new config.json holds your goal and no target organisations or role
families: the interview sets those with you. --example starts from a config
in examples/configs/ instead (for example frontier-ai-labs).

Refuses a folder that already has files in it, a folder inside the engine
repo, or a folder inside a git repository that has a remote. The new folder
is readable by its owner only.

Usage
  python3 scripts/init.py --role "Climate tech product manager" --organisations "Octopus, Tesla" \\
                          --where Melbourne --by 2027-06-30
  python3 scripts/init.py --goal "Climate tech product roles"
  python3 scripts/init.py --goal "Climate tech product roles" --workspace ~/private/climate-search
  python3 scripts/init.py --goal "Frontier AI labs" --example frontier-ai-labs
"""
import argparse
import datetime as dt
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402
import _goal as G  # noqa: E402

SKIP = {".gitkeep", ".DS_Store", "__pycache__"}
EXAMPLE_DIR = os.path.join(C.ENGINE_ROOT, "examples", "configs")
NEXT_STEP = 'Next step: say to your agent "run the LVLme interview".'


def examples():
    return sorted(n[:-5] for n in os.listdir(EXAMPLE_DIR) if n.endswith(".json"))


def slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (slug[:40].strip("-") or "my-goal")


def local_timezone():
    """IANA name of the machine's time zone, if the system exposes it; else UTC."""
    try:
        real = os.path.realpath("/etc/localtime")
        if "zoneinfo/" in real:
            return real.split("zoneinfo/", 1)[1]
    except OSError:
        pass
    return os.environ.get("TZ") or "UTC"


def goal_fields(args, today):
    """The goal fields to store: the sentence in title, and role, organisations, where, by when they were given."""
    if not (args.role or "").strip():
        if not (args.goal or "").strip():
            raise ValueError("say the role you want with --role (and, if you can, --organisations, --where and --by), "
                             "or give a short --goal.")
        return {"title": args.goal.strip()}
    by = args.by
    if by:
        try:
            dt.date.fromisoformat(by)
        except ValueError:
            raise ValueError("--by must be a date like 2027-06-30.")
        if by <= today:
            raise ValueError("the date %s is already past. Choose a date after %s." % (by, today))
    orgs = [o.strip() for o in (args.organisations or "").split(",") if o.strip()]
    fields = {"role": args.role.strip(), "title": G.goal_sentence(args.role, orgs, args.where, by)}
    if orgs:
        fields["organisations"] = orgs
    if (args.where or "").strip():
        fields["where"] = args.where.strip()
    if by:
        fields["by"] = by
    return fields


def copy_skeleton(dest):
    for root, dirs, files in os.walk(C.TEMPLATE_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP]
        rel = os.path.relpath(root, C.TEMPLATE_DIR)
        target_dir = dest if rel == "." else os.path.join(dest, rel)
        os.makedirs(target_dir, exist_ok=True)
        for name in files:
            if name not in SKIP:
                shutil.copy2(os.path.join(root, name), os.path.join(target_dir, name))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Create a private LVLme workspace.")
    ap.add_argument("--role", help='the role you want, for example "Customer success"')
    ap.add_argument("--organisations", help='the organisations, separated by commas, for example "Anthropic, OpenAI"')
    ap.add_argument("--where", help="where you would work: a city, a country or remote")
    ap.add_argument("--by", help="the date you want to reach it by, YYYY-MM-DD")
    ap.add_argument("--goal", help='the goal in a few words instead, for example "Climate tech product roles"')
    ap.add_argument("--workspace", help="where to create it (default: $LVLME_HOME or "
                                        "~/lvlme-workspaces/<goal-slug>)")
    ap.add_argument("--example", choices=examples(),
                    help="start from this example config instead of an empty one")
    args = ap.parse_args(argv)
    today = C.today_in({"candidate": {"timezone": local_timezone()}})
    try:
        fields = goal_fields(args, today)
    except ValueError as exc:
        print("lvlme: %s" % exc, file=sys.stderr)
        return 1
    title = fields["title"]
    slug = slugify(" ".join([fields.get("role", title)] + fields.get("organisations", [])))
    env = C.home_env()
    dest = args.workspace or env or os.path.join(C.default_parent(), slug)
    dest = os.path.abspath(os.path.expanduser(dest))
    if os.path.exists(dest) and (not os.path.isdir(dest) or os.listdir(dest)):
        print("lvlme: %s already exists and is not empty. Choose another --workspace." % dest, file=sys.stderr)
        return 1
    problem = C.location_problem(dest, {})
    if problem:
        print("lvlme: refused. " + problem, file=sys.stderr)
        return 2
    copy_skeleton(dest)
    for root, dirs, _ in os.walk(dest):
        os.chmod(root, 0o700)
    cfg_path = C.wpath(dest, "config.json")
    source = os.path.join(EXAMPLE_DIR, args.example + ".json") if args.example else cfg_path
    config = C.load_json(source)
    config["goal"].update(slug=slug, description=title, started_on=today, **fields)
    config.setdefault("candidate", {})["timezone"] = local_timezone()
    C.write_json(cfg_path, config)
    print("Created your private workspace: %s" % dest)
    found = (os.path.dirname(dest) == C.default_parent(note=False)
             or bool(env) and os.path.abspath(os.path.expanduser(env)) == dest)
    print(NEXT_STEP if found else NEXT_STEP[:-1] + " and tell it the workspace is %s." % dest)
    return 0


if __name__ == "__main__":
    sys.exit(C.run_main(main, workspace_check=False))
