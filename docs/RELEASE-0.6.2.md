# LVLme 0.6.2: a first answer that agrees with itself

5 November 2026. A polish release for the first run. We ran the new-user test
again on 0.6.1, then had three AI reviewers from different makers (Claude,
Codex and Grok) judge the whole first-time journey blind, over five rounds, and
fixed what they and the test found. How a score is worked out did not change.

## Fixed

- **The blind review is always read.** If the second AI wrote a factor by its
  name ("Requirements match") instead of its code, the result said it was
  still waiting for the reviewer. Now either way is read, and a reply that
  cannot be read is said plainly.
- **A campaign made from a quick result keeps its job and its review.** For a
  job title with a comma in it, the first refresh of the job boards could drop
  the only role. It is found again now, and the reviewer's disagreement
  carries over instead of showing as "waiting".
- **The saved job ad keeps the visa and pay lines**, so your agent does not
  tell you the ad is silent on sponsorship when it is not.
- **Every suggested fix is accounted for.** The result page names each fix it
  left out, and why.

## Changed

- **Clearer result page**: why in short, what to do first and who judged, at
  the top; one plain status per factor ("First score 3, blind reviewer 2:
  counts as 2"); who did the blind review; how the points are worked out; what
  the fixes total and the "up to" range each mean; where the next band starts.
- **Honest about differences between runs**: another AI, or another run of
  the same one, can judge a factor differently, often by a few fit points.
- **Plainer dashboard**: "Altitude (fit)" and "Flight level (chance)",
  expected points explained with a worked example, one list of next steps
  ending with the career interview, and an Auto theme that follows your
  device.
- **Agents**: they never write the blind review themselves, they record who
  reviewed, and they paste the result as it is.
- **Docs**: LVLme quick asks at most two short questions; your first message
  can carry the job link and where your CV is; start a new Claude Code session
  if the command is not found right after installing; untested agents and
  systems are called untested.

The full list is in [CHANGELOG.md](https://github.com/mark-hallam/lvlme/blob/v0.6.2/CHANGELOG.md).
