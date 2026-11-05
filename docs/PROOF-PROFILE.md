# The proof profile

A proof profile is one clean page that shows where you are against your goal and only the claims you have checked, each with the public link that backs it. It is built from your own evidence file, so nothing on it is a claim LVLme could not check.

## What it shows

- Your name, your goal, your current level (1 to 5) and the dated history of your levels.
- Claims at the `verified` or `corroborated` level that have at least one public https source. Each shows its level and its source link.
- Nothing else. Claims that are self reported, unverified, partly verified or contradicted are left out. So are claims whose only sources are documents, emails or private links, and anything about other people (your contacts), your work rights or your preferences. The page says how many checked claims it left out for want of a public link.
- Your target organisations are never shown.

## Private by default

LVLme writes the page to `report/profile/index.html` in your workspace, with the same facts in `report/profile/profile.json` for your agents. Nothing is sent anywhere. It stays on your computer until you choose to host it.

To build it, say to your agent "build my proof profile", or run:

```
python3 scripts/proof_profile.py --workspace ~/lvlme-workspaces/<your-goal>
```

## The leak check

Before it writes anything, LVLme checks the finished page. It refuses to write, and says why in plain words, if the page would contain an email address, a phone number, a folder path from your computer, a private-network, local or non-https link, anything that loads from outside the page, a claim below corroborated, or a name listed under `privacy.redact_terms` in your `config.json`. Fix the claim in `profile/evidence.json`, then run it again. An earlier page is left as it was.

The check cannot know everything. It cannot tell that a claim names a colleague or a client you did not mean to name, so read the page yourself before you share it.

## How to look at it

```bash
open ~/lvlme-workspaces/<your-goal>/report/profile/index.html
```

A fictional example, for Alex Example, is in `examples/demo-workspace/report/profile/index.html`.

## Host it yourself on GitHub Pages

This is your own step: LVLme never publishes for you. You need a free GitHub account.

1. Read the page once, start to finish, as a stranger would. Check every link opens.
2. On GitHub, create a new public repository. Name it `<your-username>.github.io` to get the address `https://<your-username>.github.io`, or any name for an address ending in that name.
3. Add one file to the repository called `index.html`, with the contents of `report/profile/index.html`. On the repository page choose Add file, then Upload files, drag the file in and commit it.
4. Open the repository's Settings, then Pages. Under Build and deployment choose Deploy from a branch, pick `main` and the `/ (root)` folder, and save.
5. After a minute or two the address shows at the top of that page. Open it and check it matches what you looked at.
6. To update it later, build the profile again and replace `index.html` in the repository.

Never put your workspace folder in a public repository. Upload only `index.html`.

## A hosted address (not built yet)

A hosted `username.lvlme.com` does not exist yet. It would need hosting that LVLme runs, an account system and Mark's decision to build it, so for now the way to have a public address is the GitHub Pages steps above.
