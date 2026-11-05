"""Employers' own published rules on candidates' use of AI, as the research pages show them.

Each entry was read on the employer's own page, at `source`, on `checked_on`.
Never add one from anywhere else, and never assume one employer's rules apply
to another (method/CAMPAIGN.md). A target's `ai_policy` in config.json overrides the entry, so the brief and
the research page say plainly what the employer asks.
"""

KNOWN = {
    # "Please create your first draft yourself, then use Claude to refine it." (page last updated 10 July 2025)
    "anthropic": {"name": "Anthropic", "first_draft_by_person": True,
                  "source": "https://www.anthropic.com/candidate-ai-guidance", "checked_on": "2026-11-03"},
}


def policy_for(org_id, org_name=None):
    """The ai_policy for an employer, matched on its board id or its name, or None."""
    for key, entry in KNOWN.items():
        if key == (org_id or "").lower() or entry["name"].lower() == (org_name or "").strip().lower():
            return {k: entry[k] for k in ("first_draft_by_person", "source", "checked_on")}
    return None


def first_draft_line(name, policy):
    """The plain sentence LVLme says before any application help, or None."""
    if not (policy or {}).get("first_draft_by_person"):
        return None
    return "%s asks for your own first draft. Write it, then I'll review it." % name
