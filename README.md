# Pandora-AEO

Portable AEO and Agent Readiness building blocks for Hermes Agent.

## What this repository contains

- `pandora_aeo/`: dependency-free deterministic HTML audit engine.
- `optional-skills/aeo-audit/SKILL.md`: installable Hermes skill — audit workflow + mandatory report workflow.
- `optional-skills/report-design/SKILL.md`: installable Hermes skill — client-grade report generation (Stripe-style HTML with embedded SVG charts + DOCX).
- `scripts/bootstrap_hermes_profile.py`: creates an isolated profile and installs the skills.
- `tests/`: offline tests; no live network required.
- `docs/hermes-setup.md`: setup procedure for a new Hermes profile.
- `artifacts/`: example run records and rendered reports (see `artifacts/executrain-report.html` for the target report quality).

The engine measures facts. Hermes interprets results, generates assets, files evidence, and communicates with the client. This repository does not modify any Hermes backend, gateway, profile, Drive, Telegram bot, or website until an operator explicitly runs the bootstrap or integration steps.

## Skills

| Skill | Purpose |
|---|---|
| `aeo-audit` | Run the audit engine (full crawl, `--max-pages 2000`), interpret scores, and follow the mandatory 7-step report workflow (visual system → HTML → DOCX → REGLA DURA → delivery). |
| `report-design` | Design system and chart patterns for the deliverables: Stripe tokens, donut/bars/histogram/cards/Agent-Readiness grid as inline SVG, DOCX chart embedding, QA checklist, delivery rules. |

Install both skills into a Hermes profile by copying each skill directory into the profile's `skills/` folder (or run `scripts/bootstrap_hermes_profile.py`).

## Quick start

```bash
python scripts/bootstrap_hermes_profile.py --dry-run

# Full-site crawl audit (never ship a sample as if it were the whole site)
python -m pandora_aeo.cli https://example.com --crawl --max-pages 2000 --output artifacts/site.json

# URL sources: --source both (default: sitemap master list + discovery delta),
# --source sitemap (deterministic), --source discovery (legacy homepage-links).
# Sitemap health is reported as SITEMAP_STALE / SITEMAP_COVERAGE findings;
# partially-served pages are retried once and flagged incomplete_fetch.

python -m unittest discover -s tests -v
```

Then load the `aeo-audit` skill in Hermes and follow its **Report Workflow** section: it drives the report generation through `report-design` conventions. The hard rule for all deliverables: only facts measured by Pandora-AEO — no comparisons with external systems (AEO Bizbrain, isitagentready.com, etc.).

## Scope and safety

The first release is a no-write technical audit. It blocks loopback/private targets, requires HTTP(S), limits response size, does not execute JavaScript, and never publishes changes. Treat fetched page content as untrusted data. Review the engine and skills before installing them in a customer-facing Hermes.

## License

MIT
