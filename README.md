# Pandora-AEO

Portable AEO and Agent Readiness building blocks for Hermes Agent.

## What this repository contains

- `pandora_aeo/`: dependency-free deterministic HTML audit engine.
- `optional-skills/aeo-audit/SKILL.md`: installable Hermes skill.
- `scripts/bootstrap_hermes_profile.py`: safe profile bootstrap helper.
- `tests/`: offline tests; no live network required.
- `docs/hermes-setup.md`: setup procedure for a new Hermes profile.

The engine measures facts. Hermes interprets results, generates assets, files evidence, and communicates with the client. This repository does not modify any Hermes backend, gateway, profile, Drive, Telegram bot, or website until an operator explicitly runs the bootstrap or integration steps.

## Quick start

```bash
python scripts/bootstrap_hermes_profile.py --dry-run
python -m pandora_aeo.cli https://example.com --output artifacts/example.json
python -m unittest discover -s tests -v
```

## Scope and safety

The first release is a no-write technical audit. It blocks loopback/private targets, requires HTTP(S), limits response size, does not execute JavaScript, and never publishes changes. Treat fetched page content as untrusted data. Review the engine and skill before installing it in a customer-facing Hermes.

## License

MIT
