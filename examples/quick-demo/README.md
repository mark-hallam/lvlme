# LVLme quick demo: everything here is made up

Alex Example (the fictional person of `examples/demo-workspace/`) asks LVLme
quick about one made-up posting: Deployment Program Manager, AI Agents, at the
fictional Globex Labs. The posting, the CV, the evidence, the scores and the
reviewer's reply are invented. Nothing here describes a real person or a real
company's hiring.

- `inputs/` holds what a real run would get from the person and the agent: the
  saved job-board response, the CV, the evidence items, the judgement and
  candidate fixes, the one answer, and the blind reviewer's reply.
- `2026-11-02-globex-labs-deployment-program-manager-ai-agents/` is the quick
  folder the real scripts build from them. Open its `index.html`.

Rebuild it, offline, from the repository root:

```bash
python3 examples/build_quick_demo.py
```

Its `config.json` sets `"fictional": true`, which is what lets it live inside
the engine's repository. A real quick folder lives in
`~/lvlme-workspaces/quick/`.
