# Copying sources for the consistency audit

Use this when building `profile/role-records.json` for
`scripts/consistency_audit.py` (see `method/CONSISTENCY.md`). It works for
you, for a helper agent, or for a person doing it by hand. Do one source at
a time. Replace `{{SOURCE_ID}}`, `{{SOURCE_LABEL}}` and `{{SOURCE_REF}}`
first.

---

You are copying one source of a person's work history into a JSON list, so a
script can compare it with their other sources. The source is
**{{SOURCE_LABEL}}** (`{{SOURCE_REF}}`). The source id is `{{SOURCE_ID}}`.

The whole point is to catch differences between sources, so **copy, do not
correct**.

## Rules

1. Copy each title **exactly as this source writes it**, even if you know
   it is wrong or another source says something else. "Quality Manager" stays
   "Quality Manager" here even if the CV says "Deputy Quality Manager".
2. Copy each date at the precision the source shows: `Oct 2007` stays
   `Oct 2007`, a year alone stays `2007`. A current role is `present`. If the
   source gives no date, leave the field out. Never fill a date from memory
   or from another source.
3. Copy the organisation name as written. Different spellings of the same
   employer are fine; the script matches them (add an alias if it does not).
4. Copy achievement lines for each role into `claims`, word for word, one
   line per claim. Skip duties with no claim in them.
5. One record per role. A promotion inside one employer is two records.
   Kinds: `role` (the default), `business` (the person's own company),
   `volunteer` and `education`.
6. If the source shows two roles at the same time on purpose (a part-time
   board seat, say), set `"concurrent": true` on the smaller one.
7. Do **not** copy: salary or pay, reasons for leaving, supervisor or
   referee contact details, government or tax numbers, addresses, or
   anything about health, family or legal matters. If a photo of a form
   shows these, copy only the role lines.
8. If a line is hard to read (a blurry photo, handwriting), copy what you
   can and add a `note` saying which part is uncertain. Never guess.

## Output

Only this JSON, ready to go under `sources` in `profile/role-records.json`:

```json
"{{SOURCE_ID}}": {
  "label": "{{SOURCE_LABEL}}",
  "ref": "{{SOURCE_REF}}",
  "captured_on": "YYYY-MM-DD",
  "records": [
    {"organisation": "", "title": "", "start": "", "end": "", "claims": []}
  ]
}
```

Add `"complete": false` if this source does not try to list every role (a
website "About" page usually does not), `"editable": false` if the person
cannot change it (a signed form, a referee's letter), and
`"covers": {"from": "", "to": ""}` if it only asks about a period (for
example "the last 10 years").
