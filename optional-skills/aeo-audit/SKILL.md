---
name: aeo-audit
description: Audit websites for AEO facts and evidence.
version: 0.1.0
author: Manuel Hernández (zorrovengador), Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [AEO, SEO, Agent-Readiness, auditing]
    related_skills: []
---

# AEO Audit Skill

Run the bundled deterministic engine before interpreting a website. This skill measures reproducible HTML facts; it does not claim universal AI visibility rankings, publish website changes, or replace human review.

## When to Use

- Audit a public website for technical AEO and Agent Readiness signals.
- Produce structured facts that another Hermes workflow can interpret.
- Generate a reproducible JSON run record without making website changes.

Don't use for private-network targets, production changes, or unsupported claims about how an AI model will rank a site.

## Prerequisites

- Python 3.10 or newer.
- The repository directory available in the active workspace.
- No API keys are required for the deterministic audit.

## How to Run

Use the `terminal` tool from the repository root:

```bash
python -m pandora_aeo.cli https://example.com --output artifacts/example.json
```

If installed as a package:

```bash
pandora-aeo https://example.com --output artifacts/example.json
```

## Quick Reference

```text
python -m pandora_aeo.cli URL [--timeout SECONDS] [--output PATH]
```

## Procedure

1. Confirm the URL is an absolute HTTP(S) URL; completion means the target is explicit.
2. Run the deterministic CLI; completion means JSON contains `run`, `retrieval`, `checks`, and `scores`.
3. Inspect each check's `status`, `value`, and `evidence`; completion means every recommendation is tied to a measured fact.
4. Keep the JSON run record with the project artifacts; completion means the engine version and UTC measurement time are preserved.
5. Present measured facts separately from model interpretation; completion means no score is described as a universal ranking.

## Pitfalls

- A profile is not a complete filesystem sandbox; run untrusted crawling in a hardened container or restricted terminal backend.
- Redirects and DNS can change after initial validation; production deployments should add redirect revalidation and egress policy.
- HTML checks are not an AI visibility measurement. Query-set visibility requires a separate documented protocol.
- The engine reads up to 2 MB of HTML and does not execute JavaScript.

## Verification

Run the repository tests with the `terminal` tool:

```bash
python -m unittest discover -s tests -v
```

A valid run has passing tests, a parseable JSON result, and no writes to the audited website.
