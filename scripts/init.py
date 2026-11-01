#!/usr/bin/env python3
"""Create a private workspace for one goal from the templates/ skeleton.

The workspace holds all personal data and lives outside the engine repo:
  --workspace PATH, else $CLIMB_HOME, else ~/climb-workspaces/<goal-slug>

Refuses a folder that already has files in it, a folder inside the engine
repo, or a folder inside a git repository that has a remote. The new folder
is readable by its owner only.

Usage
  python3 scripts/init.py --goal "Frontier AI labs"
  python3 scripts/init.py --goal "Climate tech product roles" --workspace ~/private/climate-search
"""
import argparse
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

SKIP = {".gitkeep", ".DS_Store", "__pycache__"}


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
    ap = argparse.ArgumentParser(description="Create a private Climb workspace.")
    ap.add_argument("--goal", required=True, help='your goal in a few words, for example "Frontier AI labs"')
    ap.add_argument("--workspace", help="where to create it (default: $CLIMB_HOME or "
                                        "~/climb-workspaces/<goal-slug>)")
    args = ap.parse_args(argv)
    slug = slugify(args.goal)
    dest = args.workspace or os.environ.get("CLIMB_HOME") or os.path.join(C.DEFAULT_PARENT, slug)
    dest = os.path.abspath(os.path.expanduser(dest))
    if os.path.exists(dest) and (not os.path.isdir(dest) or os.listdir(dest)):
        print("climb: %s already exists and is not empty. Choose another --workspace." % dest, file=sys.stderr)
        return 1
    problem = C.location_problem(dest, {})
    if problem:
        print("climb: refused. " + problem, file=sys.stderr)
        return 2
    copy_skeleton(dest)
    for root, dirs, _ in os.walk(dest):
        os.chmod(root, 0o700)
    today = C.today_in({"candidate": {"timezone": local_timezone()}})
    cfg_path = C.wpath(dest, "config.json")
    config = C.load_json(cfg_path)
    config["goal"]["slug"] = slug
    config["goal"]["title"] = args.goal.strip()
    config["goal"]["started_on"] = today
    config.setdefault("candidate", {})["timezone"] = local_timezone()
    C.write_json(cfg_path, config)
    print("Created your private workspace: %s" % dest)
    print("Next steps:")
    print("  1. Edit config.json: target organisations, role families and keywords, location classes.")
    print("  2. Ask your agent to run the intake (method/INTAKE.md), or fill intake/answers.md yourself.")
    print("  3. Put exports such as LinkedIn's Connections.csv in intake/sources/.")
    print("  4. Run: python3 scripts/fetch_roles.py --workspace %s" % dest)
    print("Tip: set CLIMB_HOME=%s so you can leave out --workspace." % dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
