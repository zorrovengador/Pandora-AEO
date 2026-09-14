"""CLI for Pandora AEO v0.5."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .engine import audit_url, audit_site


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pandora-aeo", description="Run a deterministic AEO audit.")
    parser.add_argument("url")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--output", type=Path, help="Write JSON to this path as well as stdout")
    parser.add_argument("--crawl", action="store_true", help="Crawl internal pages and audit each (site-wide audit)")
    parser.add_argument("--max-pages", type=int, default=50, help="Max pages to crawl (with --crawl)")
    parser.add_argument("--source", choices=("sitemap", "discovery", "both"), default="both",
                        help="Crawl URL source: sitemap (deterministic, follows sitemap indexes), "
                             "discovery (homepage links, legacy v0.4 behavior), or both (default: "
                             "sitemap master list + live-only URLs, reported via SITEMAP_COVERAGE)")
    parser.add_argument("--pause", type=float, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.pause is not None:
        from . import sitemap_crawl
        sitemap_crawl._REQUEST_PAUSE_SECONDS = args.pause

    if args.crawl:
        result = audit_site(args.url, timeout=args.timeout, max_pages=args.max_pages, source=args.source)
    else:
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
