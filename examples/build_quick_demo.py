#!/usr/bin/env python3
"""Rebuild the LVLme first pass demo: one fictional posting, one fictional CV.

Alex Example (the fictional person of examples/demo-workspace/) asks about one
made-up posting at Globex Labs. This runs the real steps, offline:

  1. scripts/quick.py new, reading the saved Ashby job-board response in
     quick-demo/inputs/globex-board.json instead of the network;
  2. copies in the agent's work, hand-written for the demo: the evidence
     items, the judgement and fixes, the one answer, and the blind reviewer's
     reply (quick-demo/inputs/);
  3. scripts/quick.py build, which writes result.json, index.html and
     message.md.

The quick folder's config.json sets "fictional": true, which is what lets it
live inside the engine's repository. A real quick folder lives in
~/lvlme-workspaces/quick/.

Usage: python3 examples/build_quick_demo.py
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ENGINE, "scripts"))
import quick  # noqa: E402

DATE = "2026-11-02"
INPUTS = os.path.join(HERE, "quick-demo", "inputs")
LINK = "https://jobs.ashbyhq.com/globex-labs-example/0b6f3c2e-1a2b-4c3d-8e9f-000000000001"
COPIES = [("evidence.json", "profile/evidence.json"), ("quick.json", "eval/quick.json"),
          ("review-reply.md", "eval/review-reply.md"), ("answers.md", "intake/answers.md")]


def folder_for(parent=None):
    name = quick.folder_name(DATE, "Globex Labs", "Deployment Program Manager, AI Agents")
    return os.path.join(parent or os.path.join(HERE, "quick-demo"), name)


def build(folder):
    """Build the demo quick folder at folder (replacing it). Returns the message text."""
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    code = quick.main(["new", "--posting", LINK, "--saved-response", os.path.join(INPUTS, "globex-board.json"),
                       "--org", "Globex Labs", "--cv", os.path.join(INPUTS, "cv-alex-example.md"),
                       "--date", DATE, "--folder", folder, "--fictional"])
    if code:
        raise SystemExit("quick.py new failed with exit code %d" % code)
    for src, dst in COPIES:
        shutil.copyfile(os.path.join(INPUTS, src), os.path.join(folder, dst))
    _, text = quick.build(folder)
    # the message names the folder; in the repository, name it from the repository root
    for root in (ENGINE, quick.display_path(ENGINE)):
        text = text.replace(root + os.sep, "")
    with open(os.path.join(folder, "message.md"), "w", encoding="utf-8") as fh:
        fh.write(text)
    return text


if __name__ == "__main__":
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        message = build(folder_for())
    print(message, end="")
