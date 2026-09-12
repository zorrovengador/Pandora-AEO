"""Command-line interface for Pandora AEO."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .engine import audit_url


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pandora-aeo", description="Run a deterministic AEO audit.")
    parser.add_argument("url")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--output", type=Path, help="Write JSON to this path as well as stdout")
    args = parser.parse_args(argv)
    try:
        result = audit_url(args.url, args.timeout)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    print(payload, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
