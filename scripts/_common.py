"""Shared helpers for the LVLme scripts. Standard library only.

Covers: finding the workspace, the workspace location guard, JSON input and
output, one-line error messages, keyword matching, dates, and constants shared
by several scripts.
"""
import datetime as dt
import json
import os
import re
import sys
import traceback

ENGINE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_DIR = os.path.join(ENGINE_ROOT, "schemas")
TEMPLATE_DIR = os.path.join(ENGINE_ROOT, "templates")
DEFAULT_PARENT = os.path.join(os.path.expanduser("~"), "lvlme-workspaces")
# LVLme was called Climb until 3 November 2026. The old names keep working:
# $CLIMB_HOME is read when $LVLME_HOME is not set, and ~/climb-workspaces is
# used when ~/lvlme-workspaces does not exist.
HOME_ENV = "LVLME_HOME"
LEGACY_HOME_ENV = "CLIMB_HOME"
LEGACY_PARENT = os.path.join(os.path.expanduser("~"), "climb-workspaces")
LEGACY_NOTE = ("lvlme: using ~/climb-workspaces, the folder's name from before Climb became LVLme. "
               "It keeps working. To move to the new name, rename the folder to ~/lvlme-workspaces.")

DIMENSIONS = ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]
DIMENSION_NAMES = {
    "D1": "Requirements match",
    "D2": "Proof of work",
    "D3": "Warm path",
    "D4": "Org-specific edge",
    "D5": "Public signal",
    "D6": "Eligibility and logistics",
    "D7": "Application readiness",
}
DEFAULT_WEIGHTS = {"D1": 25, "D2": 20, "D3": 20, "D4": 10, "D5": 10, "D6": 10, "D7": 5}
BANDS = ["Very low", "Low", "Moderate", "Good", "Strong"]
BLOCKER_TYPES = ["us_person_export_control", "security_clearance", "citizenship", "licence"]
# Evidence ids: 1 to 3 capital letters, then digits. E is the default for new items (E01, E02, ...);
# other prefixes keep a source's own numbering (for example G01 for email findings).
EVIDENCE_ID = r"^[A-Z]{1,3}[0-9]+$"
EVIDENCE_LEVELS = ["verified", "corroborated", "partially_verified", "self_reported", "unverified", "contradicted"]
# Plan action statuses. Active (counted against max_active, in the projection by default): todo and doing.
# later is parked: off the active cap and out of every projection until switched on in the what-if rail.
ACTIVE_STATUSES = ("todo", "doing")
EXTENSION_PREFIX = "x_"
BLOCKER_NAMES = {
    "us_person_export_control": "US person or export control (ITAR)",
    "security_clearance": "Security clearance",
    "citizenship": "Citizenship",
    "licence": "Licence",
}
# The one line a new workspace gets until the interview has set it up.
NO_TARGETS = "No target organisations yet. Say to your agent: run the LVLme interview."
NO_FAMILIES = "No role families yet. Say to your agent: run the LVLme interview."


# Set LVLME_DEBUG=1 to see the full Python details of a failure instead of the one plain line.
DEBUG_ENV = "LVLME_DEBUG"


class WorkspaceError(Exception):
    """Raised when a workspace cannot be found or is in an unsafe place."""


class FileProblem(ValueError):
    """A file cannot be used: not found, unreadable, or not valid JSON. Its text is one plain line.

    A ValueError, so code that already caught bad JSON as ValueError keeps working.

    >>> str(FileProblem("/x/config.json", "not valid JSON (line 1, column 2: Expecting value)"))
    '/x/config.json: not valid JSON (line 1, column 2: Expecting value). Fix that spot in the file, then run this again.'
    """

    def __init__(self, path, detail, hint="Fix that spot in the file, then run this again."):
        self.path, self.detail, self.hint = path, detail, hint
        super().__init__("%s: %s. %s" % (show_path(path), detail, hint))


def show_path(path):
    """A path for a message, with ~ for the home folder."""
    path = str(path)
    home = os.path.expanduser("~").rstrip(os.sep)
    if home and home != "~" and (path == home or path.startswith(home + os.sep)):
        return "~" + path[len(home):]
    return path


# ------------------------------------------------------------------ files


def load_json(path, default=None):
    """Read a JSON file; return default if it does not exist.

    Raises FileProblem (one plain line) if the file cannot be read or is not valid JSON.
    """
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise FileProblem(path, "not valid JSON (line %d, column %d: %s)" % (exc.lineno, exc.colno, exc.msg)) from None
    except UnicodeDecodeError:
        raise FileProblem(path, "not valid JSON (it is not UTF-8 text)") from None
    except OSError as exc:
        raise FileProblem(path, "cannot be read (%s)" % (exc.strerror or exc),
                          "Check the file is there and you can open it, then run this again.") from None


def read_input(path, what="file"):
    """Text of a file the person named ('-' reads standard input). Raises FileProblem if it cannot be read."""
    if path == "-":
        return sys.stdin.read()
    hint = "Check the path, then run this again."
    if not os.path.exists(path):
        raise FileProblem(path, "no %s at this path" % what, hint)
    if os.path.isdir(path):
        raise FileProblem(path, "this is a folder, not a %s" % what, hint)
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError as exc:
        raise FileProblem(path, "cannot be read (%s)" % (exc.strerror or exc), hint) from None


def dump_json(data):
    """Canonical JSON text used for every file the engine writes."""
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(dump_json(data))


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def wpath(workspace, *parts):
    return os.path.join(workspace, *parts)


# -------------------------------------------------------------- workspace


def home_env():
    """$LVLME_HOME, else the old $CLIMB_HOME, else None."""
    return os.environ.get(HOME_ENV) or os.environ.get(LEGACY_HOME_ENV) or None


_legacy_noted = []


def default_parent(note=True):
    """~/lvlme-workspaces, or the old ~/climb-workspaces when only that one exists (said once on stderr)."""
    if not os.path.isdir(DEFAULT_PARENT) and os.path.isdir(LEGACY_PARENT):
        if note and not _legacy_noted:
            _legacy_noted.append(LEGACY_PARENT)
            print(LEGACY_NOTE, file=sys.stderr)
        return LEGACY_PARENT
    return DEFAULT_PARENT


def resolve_workspace(arg):
    """--workspace, else $LVLME_HOME (or $CLIMB_HOME), else the only folder in ~/lvlme-workspaces."""
    if arg:
        return os.path.abspath(os.path.expanduser(arg))
    env = home_env()
    if env:
        return os.path.abspath(os.path.expanduser(env))
    parent = default_parent()
    if os.path.isdir(parent):
        subs = [d for d in sorted(os.listdir(parent))
                if os.path.isfile(os.path.join(parent, d, "config.json"))]
        if len(subs) == 1:
            return os.path.join(parent, subs[0])
        if len(subs) > 1:
            raise WorkspaceError("Several workspaces in %s (%s). Pass --workspace or set LVLME_HOME."
                                 % (parent, ", ".join(subs)))
    raise WorkspaceError("No workspace found. Run scripts/init.py first, or pass --workspace PATH, "
                         "or set LVLME_HOME.")


def _is_within(path, parent):
    path, parent = os.path.realpath(path), os.path.realpath(parent)
    return path == parent or path.startswith(parent.rstrip(os.sep) + os.sep)


def find_git_root(path):
    """Nearest folder at or above path that holds a .git entry, or None."""
    cur = os.path.realpath(path)
    while not os.path.exists(cur):
        cur = os.path.dirname(cur)
    while True:
        if os.path.exists(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def git_config_path(repo_root):
    """Path of the git config for a repo, following worktree and submodule .git files."""
    dotgit = os.path.join(repo_root, ".git")
    if os.path.isdir(dotgit):
        return os.path.join(dotgit, "config")
    try:
        with open(dotgit, encoding="utf-8") as fh:
            line = fh.read().strip()
    except OSError:
        return None
    if not line.startswith("gitdir:"):
        return None
    gitdir = line.split(":", 1)[1].strip()
    if not os.path.isabs(gitdir):
        gitdir = os.path.join(repo_root, gitdir)
    common = os.path.join(gitdir, "commondir")
    if os.path.exists(common):
        with open(common, encoding="utf-8") as fh:
            gitdir = os.path.normpath(os.path.join(gitdir, fh.read().strip()))
    return os.path.join(gitdir, "config")


def git_remotes(repo_root):
    """Remote names configured for the repo at repo_root (reads the config file, no git needed)."""
    cfg = git_config_path(repo_root)
    if not cfg or not os.path.exists(cfg):
        return []
    with open(cfg, encoding="utf-8", errors="replace") as fh:
        return re.findall(r'^\s*\[remote\s+"([^"]+)"\]', fh.read(), re.M)


def location_problem(workspace, config=None):
    """Return a reason string if the workspace is in an unsafe place, else None.

    Unsafe: inside the engine repo (except the fictional demo under examples/),
    or inside any git repository that has a remote configured.
    """
    if config is None:
        try:
            config = load_json(wpath(workspace, "config.json"), {}) or {}
        except FileProblem:
            config = {}  # an unreadable config never earns the demo's exception
    demo = bool(config.get("fictional")) and _is_within(workspace, os.path.join(ENGINE_ROOT, "examples"))
    if demo:
        return None
    if _is_within(workspace, ENGINE_ROOT):
        return ("The workspace %s is inside the LVLme engine folder. Personal data must live outside "
                "it. Use the default ~/lvlme-workspaces/<goal> or set LVLME_HOME." % workspace)
    root = find_git_root(workspace)
    if root:
        remotes = git_remotes(root)
        if remotes:
            return ("The workspace %s is inside the git repository %s, which has a remote (%s). A push could "
                    "publish personal data. Move the workspace outside it." % (workspace, root, ", ".join(remotes)))
    return None


def open_workspace(arg, need_config=True):
    """Resolve and guard a workspace. Returns (path, config). Exits with code 2 if unsafe."""
    try:
        ws = resolve_workspace(arg)
    except WorkspaceError as exc:
        sys.exit("lvlme: %s" % exc)
    cfg_path = wpath(ws, "config.json")
    if need_config and not os.path.exists(cfg_path):
        sys.exit("lvlme: no config.json in %s. Run scripts/init.py first." % ws)
    try:
        config = load_json(cfg_path, {}) or {}
    except FileProblem as exc:
        sys.exit("lvlme: %s" % exc)
    problem = location_problem(ws, config)
    if problem:
        print("lvlme: refused. " + problem, file=sys.stderr)
        sys.exit(2)
    return ws, config


# --------------------------------------------------------------- messages


def run_main(main, argv=None, workspace_check=True):
    """Run a script's main(argv) and return its exit code, with any failure as one plain line on stderr.

    A file problem (not found, unreadable, not valid JSON) says which file and what to do, and
    returns 1. Anything unexpected says what and where, and what to do next, also on one line.
    Ctrl-C returns 130 with "lvlme: stopped." Set LVLME_DEBUG=1 to see the full Python traceback.
    workspace_check: point the person at scripts/validate.py first (scripts that read a workspace).

    >>> run_main(lambda argv: 0)
    0
    """
    if os.environ.get(DEBUG_ENV):
        return main(argv)
    try:
        return main(argv)
    except KeyboardInterrupt:
        print("lvlme: stopped.", file=sys.stderr)
        return 130
    except FileProblem as exc:
        print("lvlme: %s" % exc, file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 (the point is that nothing reaches the person as a traceback)
        if isinstance(exc, OSError) and exc.filename:
            print("lvlme: could not open or save %s (%s). Check the file is there and you can open it, "
                  "then run this again." % (show_path(exc.filename), exc.strerror or exc), file=sys.stderr)
        else:
            print("lvlme: " + unexpected_line(exc, workspace_check), file=sys.stderr)
        return 1


def unexpected_line(exc, workspace_check=True):
    """One line for an error nobody planned for: what it was, where in the engine, what to do next."""
    scripts = os.path.join(ENGINE_ROOT, "scripts")
    frames = traceback.extract_tb(exc.__traceback__)
    frames = [f for f in frames if _is_within(f.filename, scripts) and f.name != "run_main"]
    where = ", in %s line %d" % (os.path.basename(frames[-1].filename), frames[-1].lineno) if frames else ""
    text = " ".join(str(exc).split())
    what = "%s: %s" % (type(exc).__name__, text[:160]) if text else type(exc).__name__
    then = ("Check the workspace with scripts/validate.py. If it says Valid, rerun with %s=1 and report what "
            "it shows." if workspace_check else "Rerun with %s=1 and report what it shows.") % DEBUG_ENV
    return "unexpected error (%s%s). %s" % (what, where, then)


# ------------------------------------------------------------------ dates


def today_in(config):
    """Today's date (ISO) in the candidate's time zone, falling back to UTC."""
    tz_name = ((config or {}).get("candidate") or {}).get("timezone") or "UTC"
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo(tz_name)).date().isoformat()
    except Exception:
        return dt.datetime.now(dt.timezone.utc).date().isoformat()


def check_date(value):
    try:
        dt.date.fromisoformat(value)
    except (TypeError, ValueError):
        raise SystemExit("lvlme: bad date %r, use YYYY-MM-DD" % (value,))
    return value


# --------------------------------------------------------------- keywords


def keyword_regex(keyword):
    """Compile one config keyword.

    Plain phrases match case-insensitively at the start of a word, so
    'program manag' matches 'Program Manager'. Keywords of three letters or
    fewer must match a whole word. 're:' starts a regular expression.
    """
    if keyword.startswith("re:"):
        return re.compile(keyword[3:], re.I)
    phrase = keyword.strip().lower()
    end = r"(?![a-z0-9])" if len(phrase) <= 3 else ""
    return re.compile(r"(?<![a-z0-9])" + re.escape(phrase) + end, re.I)


_KW_CACHE = {}


def matches_any(keywords, text):
    """True if any keyword matches text."""
    if not text:
        return False
    for kw in keywords or []:
        rx = _KW_CACHE.get(kw)
        if rx is None:
            rx = _KW_CACHE[kw] = keyword_regex(kw)
        if rx.search(text):
            return True
    return False


# ------------------------------------------------------------------ misc


def weights_of(config):
    w = ((config or {}).get("scoring") or {}).get("weights") or {}
    return {d: int(w.get(d, DEFAULT_WEIGHTS[d])) for d in DIMENSIONS}


def setup_problem(config):
    """NO_TARGETS or NO_FAMILIES while the config has none yet (targets first), else None."""
    if not (config or {}).get("targets"):
        return NO_TARGETS
    if not (config or {}).get("families"):
        return NO_FAMILIES
    return None


def target_ids(config):
    return [t["id"] for t in (config or {}).get("targets", [])]


def target_names(config):
    return {t["id"]: t.get("name", t["id"]) for t in (config or {}).get("targets", [])}


def family_names(config):
    return {f["id"]: f.get("name", f["id"]) for f in (config or {}).get("families", [])}
