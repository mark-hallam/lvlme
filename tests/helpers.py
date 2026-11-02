"""Shared test helpers. Importing this module blocks all network access."""
import copy
import json
import os
import shutil
import sys
import tempfile
import urllib.request

TESTS = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(TESTS)
FIXTURES = os.path.join(TESTS, "fixtures")
DEMO = os.path.join(ENGINE, "examples", "demo-workspace")
sys.path.insert(0, os.path.join(ENGINE, "scripts"))


class NetworkBlocked(OSError):
    pass


def _blocked(*args, **kwargs):
    raise NetworkBlocked("network access is blocked in tests")


urllib.request.urlopen = _blocked

import _common as C  # noqa: E402,F401


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def template_config():
    """The empty config a new workspace starts with: no targets or role families yet."""
    return load(os.path.join(ENGINE, "templates", "config.json"))


def example_config():
    """The frontier AI labs example config: real targets, role families and keywords."""
    return load(os.path.join(ENGINE, "examples", "configs", "frontier-ai-labs.json"))


def new_workspace(test, config=None):
    """A fresh workspace from templates/ in a temp folder; removed after the test."""
    parent = tempfile.mkdtemp(prefix="climb-test-")
    test.addCleanup(shutil.rmtree, parent, True)
    ws = os.path.join(parent, "ws")
    shutil.copytree(os.path.join(ENGINE, "templates"), ws)
    if config is not None:
        save(os.path.join(ws, "config.json"), config)
    return ws


def copy_demo(test):
    parent = tempfile.mkdtemp(prefix="climb-demo-test-")
    test.addCleanup(shutil.rmtree, parent, True)
    ws = os.path.join(parent, "demo")
    shutil.copytree(DEMO, ws)
    return ws


def schema(name):
    return load(os.path.join(ENGINE, "schemas", name))


def deep(x):
    return copy.deepcopy(x)
