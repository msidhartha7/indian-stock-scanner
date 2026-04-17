---
name: publish-stock-dashboard
description: Use when the user wants to publish the Indian stock scanner dashboard or daily report from this repository to GitHub and GitHub Pages.
---

# Publish Stock Dashboard

Use this skill only inside the `indian-stock-scanner` repository.

## Trigger

Use this skill when the user asks to:

- publish the stock dashboard
- publish the latest report
- refresh GitHub Pages with a new scan
- run the stock-dashboard release flow

## Workflow

1. Check `git status --short` and note unrelated local changes.
2. Run the repo's official publish command:

```bash
PYTHONPATH=src python3 -m stock_scanner publish
```

3. If the user wants a demo-only publication, run:

```bash
PYTHONPATH=src python3 -m stock_scanner publish --demo
```

4. Report back:

- publish date
- created commit hash
- pushed branch
- expected GitHub Pages workflow result

## Constraints

- Do not invent alternate publish flows.
- Do not manually edit `web/public/data/` when the publish command can regenerate it.
- Do not revert unrelated working tree changes.
- If git push or GitHub setup fails, surface the exact command failure.
