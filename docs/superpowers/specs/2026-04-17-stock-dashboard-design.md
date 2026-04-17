---
title: Indian Stock Scanner Dashboard And Publishing Design
date: 2026-04-17
status: approved
---

# Overview

This design adds a static React dashboard and a one-command publishing flow to the existing Indian stock scanner repository. The scanner remains the source of truth for daily dated report artifacts. The new frontend consumes those artifacts through a generated static data bundle and is deployed to GitHub Pages from the same repository.

The design goals are:

- keep the Python scanner as the only system that produces market-analysis artifacts
- visualize recommendations as a dashboard rather than a plain report viewer
- support history across older dated reports
- publish from a single local command
- let GitHub Actions handle site build and GitHub Pages deployment after each pushed report commit
- provide a local Codex skill that runs this exact flow when requested

# Current State

The repository already provides a Python CLI that:

- refreshes the NSE universe
- runs a scan for a date
- writes `data/reports/report-YYYY-MM-DD.json`
- writes `data/reports/report-YYYY-MM-DD.md`
- exposes `report` and `explain` commands

There is no web app, no frontend data export step, no Pages workflow, and no publish automation beyond the existing scanner commands.

# Recommended Approach

Use a separate Vite + React app inside the same repository and keep the report JSON files under version control as the canonical published artifacts.

Why this approach:

- it preserves the scanner/report contract that already exists
- it avoids moving live market-data fetching into CI
- it enables a stronger dashboard UI than a plain static HTML export
- it keeps the deployment path deterministic: local scan creates artifacts, GitHub Actions only builds and deploys

# Architecture

## Repository Layout

The implementation should add or extend the repository with these areas:

- `src/stock_scanner/`
  - existing scanner logic
  - new frontend-export helper
  - new publish orchestration command
- `data/reports/`
  - existing dated Markdown and JSON report artifacts
- `web/`
  - Vite + React dashboard app
- `web/public/data/`
  - generated static JSON files copied or derived from `data/reports/`
- `.github/workflows/deploy-pages.yml`
  - Pages build and deploy workflow
- `.codex/skills/publish-stock-dashboard/`
  - local skill that runs the repo’s publish flow when requested

## Data Ownership

The Python scanner owns report generation. The frontend must not recalculate recommendations or invent new domain logic. It only reads generated artifacts.

Source of truth:

- `data/reports/report-YYYY-MM-DD.json`
- `data/reports/report-YYYY-MM-DD.md`

Generated frontend bundle:

- a report index listing available dates and lightweight summary metadata
- one frontend-readable JSON file per dated report
- a latest-report pointer for quick initial load

## Publish Responsibility Split

Local machine responsibilities:

- fetch live data and run the scan
- update frontend data bundle
- build the app as a publish gate
- commit and push updated artifacts

GitHub Actions responsibilities:

- install frontend dependencies
- build the Vite app
- deploy built assets to GitHub Pages

GitHub Actions must not generate reports, mutate report JSON, or commit back to the repository.

# Dashboard Design

## Primary Experience

The site opens on the latest report and presents the results as a recommendation dashboard. It is not a Markdown document renderer.

The landing experience should include:

- a hero/header showing the active report date
- summary cards for report buckets and high-level counts
- a promoted recommendations area that highlights the strongest names
- a searchable/filterable recommendation table or list
- section views for all report categories
- a detail panel or drawer for the selected stock
- links to the raw Markdown and JSON artifacts for the selected date

## History

The dashboard must support browsing older scans. History should be visible rather than hidden.

Planned history behavior:

- load the latest report by default
- expose a date switcher or history rail for older dates
- switch all dashboard sections when the active date changes
- phase 1 does not require deep-linkable state; working history navigation in-app is required

## Recommendation Presentation

Each company view should show the data already present in the report JSON where available:

- ticker
- company name
- sector
- opportunity score
- action label
- time-window fit
- catalyst strength
- valuation stretch
- setup quality
- risk score
- positives
- risks
- summary
- invalidation reason
- latest financial snapshot
- recent news items

If `top_opportunities` is empty for a report date, the UI should still feel intentional. In that case it should clearly state that no names qualified for the top tier and promote the strongest watchlist names instead.

## Visual Direction

The dashboard should feel like an investment-monitoring surface, not a default admin template. The UI should use a deliberate visual system with:

- a strong dashboard layout
- clear score emphasis
- section color coding by recommendation bucket
- readable typography and mobile-safe layout

The design should preserve clarity and information density while staying usable on smaller screens.

# Frontend Data Model

## Required Export Shape

The frontend export step should generate a compact index that lets the app discover reports without scanning the filesystem at runtime.

The index should include at least:

- available report dates
- latest report date
- bucket counts by report
- top tickers or promoted tickers for summary display
- paths or identifiers for the corresponding per-date JSON assets

Per-date exported JSON should keep the report sections intact so the frontend can render them directly.

## Build-Time Strategy

The export should run before the frontend build and place the data under `web/public/data/` or an equivalent static asset directory used by Vite.

This allows GitHub Pages hosting with no server and no runtime dependency on repository browsing.

# CLI And Publish Flow

## New Command

Add a new CLI subcommand, `publish`, to orchestrate the full local flow.

Expected behavior:

1. Resolve the scan date, defaulting to the local current date.
2. Refresh the universe if needed and run the daily scan.
3. Write the dated Markdown and JSON report artifacts.
4. Regenerate frontend dashboard data from all available reports.
5. Build the Vite app as a validation gate.
6. Check whether tracked publish artifacts changed.
7. If changes exist, create a git commit and push to the tracked branch.
8. Print the pushed commit reference and relevant next-step information.

## Commit Behavior

The command should:

- avoid empty commits when nothing changed
- stage only the publish-related artifacts it owns
- fail clearly if the git working tree has conflicting changes in files it needs to stage
- avoid touching unrelated modified files

The default commit message can be date-based and deterministic, for example:

- `Publish stock scan for 2026-04-17`

## Failure Handling

The publish flow should fail fast if any of these steps fail:

- live scan generation
- frontend export generation
- frontend dependency install or build
- git staging or commit
- git push

It should surface which stage failed so the operator can recover without guessing.

# GitHub Pages Deployment

## Workflow

Add a GitHub Actions workflow that triggers on pushes to the publication branch, expected to be the repository default branch.

The workflow should:

- check out the repository
- install Node dependencies for `web/`
- build the Vite app
- upload the static build artifact
- deploy to GitHub Pages using the standard Pages actions

## Repository Settings Expectations

The repository must have:

- GitHub Pages enabled for Actions-based deployment
- workflow permissions set to allow Pages deployment

If needed, setup can also create or confirm these settings through `gh`.

# Local Skill Design

## Purpose

Create a repo-local skill that triggers when the user asks to publish the stock dashboard or daily report.

The skill should:

- be narrowly scoped to this repository
- direct Codex to use the repo’s official publish command
- avoid alternate ad hoc publish flows
- report back the commit and deployment status after the command runs

## Proposed Location

- `.codex/skills/publish-stock-dashboard/`

## Skill Content

The skill should include:

- clear trigger phrases
- the exact command pattern to use in this repo
- notes about expected prerequisites such as `gh`, `git`, Python environment, and frontend dependencies
- a reminder not to revert unrelated worktree changes

# Testing Strategy

## Python

Preserve existing tests and add targeted tests for:

- report index generation
- frontend export generation
- publish change-detection behavior where practical

## Frontend

At minimum, ensure:

- Vite production build passes
- the app renders latest-report and history-driven states correctly
- empty top-opportunity states do not break the UI

Full frontend testing is desirable but secondary to getting a reliable build and publish path in place.

# Risks And Mitigations

## Dirty Worktree Risk

The repository may contain unrelated local edits during publish. The publish command must avoid sweeping those changes into the report commit.

Mitigation:

- stage only owned files
- fail if owned files are already modified in incompatible ways

## Missing Frontend Data Contract

The raw report JSON is detailed but not optimized for fast frontend boot.

Mitigation:

- generate a compact report index as part of the publish/export flow

## CI Build Drift

The frontend may build locally but fail in CI if assumptions differ.

Mitigation:

- use the same build command locally in the publish gate and in GitHub Actions

## Empty Or Sparse Reports

Some dates may contain no top-tier recommendations.

Mitigation:

- explicitly design empty-state behavior that promotes watchlist names and explains the lack of top picks

# Success Criteria

The work is successful when all of the following are true:

- running one local publish command generates the daily report artifacts
- the command updates dashboard data and pushes a commit only when content changed
- GitHub Actions automatically rebuilds and deploys the site to GitHub Pages
- the dashboard loads the latest scan by default
- the dashboard supports browsing older report dates
- recommendations are shown as a dashboard with bucket summaries and stock details
- a local skill exists that runs this workflow when requested

# Out Of Scope

These are not part of this design:

- moving live stock/news data fetching into GitHub Actions
- creating a backend API or server-rendered app
- changing the stock scoring methodology
- automated trading or execution features
- adding portfolio tracking or user accounts
