# Inbox

This is the only file in the workspace that other agents (and you) may write to. Add a note under "New". The next run
checks each note against its source, then moves it to "Processed" with a one-line outcome.

Note format, one bullet per note:

```
- <YYYY-MM-DD> | <who: you, or the agent's name> | <the note> | <source: a link, file or email reference>
```

## New

- 2026-10-31 | research agent | Initech Robotics posted a customer success role in Auckland | https://example.com/jobs/initech/i-0004

## Processed

- 2026-10-20 | Alex | A recruiter friend says screeners compare LinkedIn with the resume line by line | conversation, 2026-10-20
  - Outcome: recorded as threat T2 in eval/swot.json. Led to action A04 (fix the headline).
