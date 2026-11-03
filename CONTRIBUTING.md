# Contributing

Thanks for helping. A few rules keep the engine honest, private and easy to
run.

## Ground rules

- **No personal data, ever.** Not yours, not anyone's. Test data and examples
  use fictional people and fictional organisations (the demo uses Alex
  Example, Acme AI, Globex Labs and Initech Robotics). Never write fictional
  facts about real companies.
- **Standard library only.** Python 3.9 or newer, no third-party packages, no
  telemetry. Network calls belong only in `fetch_roles.py`,
  `fetch_doors.py`, `claims_audit.py` and `quick_posting.py`. Board
  readers shared between them (`_boards.py`) and the calendar reader
  (`_doors.py`) parse answers and never fetch.
- **Drafts only.** No feature may apply, send, post or change an account.
- **Deterministic maths.** `score.py` must give the same output for the same
  inputs. Judgement belongs in workspace files, not in code.
- **One plain line when something goes wrong.** A new script ends with
  `sys.exit(C.run_main(main))`, reads JSON with `C.load_json` and files the
  person names with `C.read_input`. Then a missing file, bad JSON or a missing
  workspace prints one line that says what to do, not a traceback (a Python
  error listing). `LVLME_DEBUG=1` shows the full details.

## Before you open a pull request

1. Run the tests (all offline):

   ```bash
   python3 -m unittest discover -s tests
   ```

2. If you changed scoring, the dashboard or the demo inputs, rebuild the demo
   and commit the result:

   ```bash
   python3 examples/build_demo.py
   python3 examples/build_quick_demo.py
   python3 examples/build_demo_site.py
   ```

   The last one refreshes `docs/demo/`, the static demo folder.

3. If you changed a workspace file format, update the matching file in
   `schemas/` and the template in `templates/`.
4. If you changed the scoring rules, bump the rubric version in
   `method/RUBRIC.md` and in `scripts/score.py`, and say so in the pull
   request. Runs before and after are not directly comparable.
5. Add a line to the Unreleased section of [`CHANGELOG.md`](CHANGELOG.md)
   for anything a person using LVLme would notice: under Added, Changed or
   Fixed, in plain words.

## Writing style for docs

Plain English and short sentences, for readers who are not developers. Spell
out abbreviations the first time they appear in a file. Do not use em dashes
or en dashes; use commas, colons, full stops or brackets instead.

## Adding a job board

Add an adapter in `scripts/fetch_roles.py` that turns the board's public
response into the common role fields, add a small fictional fixture under
`tests/fixtures/`, and add an offline test. Never call the network in tests.
