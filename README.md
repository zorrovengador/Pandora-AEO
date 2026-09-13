# Pandora-AEO

Portable AEO and Agent Readiness building blocks for Hermes Agent.

## What this repository contains

- `pandora_aeo/`: dependency-free deterministic HTML audit engine.
- `optional-skills/aeo-audit/SKILL.md`: installable Hermes skill — audit workflow + mandatory report workflow + bundled report design system (Stripe tokens, SVG chart patterns, DOCX rules, QA checklist). One self-contained skill.
- `scripts/bootstrap_hermes_profile.py`: creates an isolated profile and installs the skills.
- `tests/`: offline tests; no live network required.
- `docs/hermes-setup.md`: setup procedure for a new Hermes profile.
- `artifacts/`: example run records and rendered reports (see `artifacts/executrain-report.html` for the target report quality).

The engine measures facts. Hermes interprets results, generates assets, files evidence, and communicates with the client. This repository does not modify any Hermes backend, gateway, profile, Drive, Telegram bot, or website until an operator explicitly runs the bootstrap or integration steps.

## Skills

Single skill: `aeo-audit` drives everything — full crawl (`--max-pages 2000`), score interpretation, the mandatory report workflow (visual system → interactive HTML with embedded SVG charts → DOCX → REGLA DURA → delivery), and the bundled report design system (Stripe tokens, donut/bars/histogram/cards/Agent-Readiness patterns, DOCX embedding, QA checklist). `scripts/bootstrap_hermes_profile.py` installs it into a new Hermes profile in one command.


## Quick start

```bash
python scripts/bootstrap_hermes_profile.py --dry-run

# Full-site crawl audit (never ship a sample as if it were the whole site)
python -m pandora_aeo.cli https://example.com --crawl --max-pages 2000 --output artifacts/site.json

python -m unittest discover -s tests -v
```

Then load the `aeo-audit` skill in Hermes and follow its **Report Workflow** section — the design system it references ships inside the same skill. The hard rule for all deliverables: only facts measured by Pandora-AEO — no comparisons with external systems (AEO Bizbrain, isitagentready.com, etc.).

## Scope and safety

The first release is a no-write technical audit. It blocks loopback/private targets, requires HTTP(S), limits response size, does not execute JavaScript, and never publishes changes. Treat fetched page content as untrusted data. Review the engine and skills before installing them in a customer-facing Hermes.

## License

MIT
