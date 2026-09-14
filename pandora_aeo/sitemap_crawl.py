# ── v0.5: sitemap-driven crawl (hybrid sitemap + discovery) ──────────────────
"""Sitemap parsing and URL-source resolution for site-wide audits.

Sources:
  - "sitemap":   all URLs declared in the site's sitemap (follows sitemap
                 indexes, any depth). Deterministic and complete per the
                 site's own declaration.
  - "discovery": links found on the homepage (legacy v0.4 behavior).
  - "both":      union of sitemap + discovery. Delta URLs found live but
                 missing from the sitemap are reported via the
                 SITEMAP_COVERAGE check.
"""
from __future__ import annotations

import re
import time
import urllib.parse
import urllib.request
from typing import Any

from . import ENGINE_VERSION

_LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
_SITEMAPINDEX_RE = re.compile(r"<sitemapindex", re.I)


def fetch_sitemap_urls(sitemap_url: str, timeout: int = 20, max_urls: int = 5000,
                       _depth: int = 0) -> tuple[list[str], list[str]]:
    """Fetch a sitemap (or sitemap index) and return (urls, errors).

    Follows <sitemapindex> entries recursively (max depth 3). Returns every
    <loc> URL found. Network/parse problems accumulate in `errors` instead of
    raising, so a partial sitemap still yields a partial crawl.
    """
    urls: list[str] = []
    errors: list[str] = []
    if _depth > 3:
        errors.append(f"sitemap-index nesting deeper than 3 at {sitemap_url}")
        return urls, errors
    try:
        req = urllib.request.Request(
            sitemap_url,
            headers={"User-Agent": f"Pandora-AEO/{ENGINE_VERSION} (+https://github.com/zorrovengador/Pandora-AEO)"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(2_000_000).decode(resp.headers.get_content_charset() or "utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001 — engine records, never raises
        errors.append(f"sitemap fetch failed {sitemap_url}: {exc}")
        return urls, errors

    if _SITEMAPINDEX_RE.search(body):
        children = _LOC_RE.findall(body)
        for child in children:
            sub_urls, sub_errors = fetch_sitemap_urls(child, timeout, max_urls - len(urls), _depth + 1)
            urls.extend(sub_urls)
            errors.extend(sub_errors)
            if len(urls) >= max_urls:
                break
        return urls, errors

    for loc in _LOC_RE.findall(body):
        if loc.startswith(("http://", "https://")):
            urls.append(loc)
            if len(urls) >= max_urls:
                errors.append(f"sitemap truncated at max_urls={max_urls}")
                break
    return urls, errors


def resolve_crawl_urls(base_url: str, source: str, timeout: int, max_pages: int,
                       homepage_html: str) -> tuple[list[str], dict[str, Any]]:
    """Build the ordered, deduplicated crawl list plus sitemap facts.

    Returns (urls, facts) where facts carries sitemap_url, sitemap_count,
    sitemap_errors and discovery_only_urls (for SITEMAP_COVERAGE).
    Order is deterministic: sorted within each source, sitemap first.
    """
    if source not in ("sitemap", "discovery", "both"):
        raise ValueError(f"invalid source: {source!r} (use sitemap | discovery | both)")
    parsed = urllib.parse.urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    facts: dict[str, Any] = {"sitemap_url": origin + "/sitemap.xml", "sitemap_count": 0,
                             "sitemap_errors": [], "discovery_only_urls": [], "source": source}

    def _same_origin(url: str) -> bool:
        p = urllib.parse.urlparse(url)
        return p.scheme in ("http", "https") and p.netloc == parsed.netloc

    def _normalize(url: str) -> str:
        p = urllib.parse.urlparse(url)
        clean = p.scheme + "://" + p.netloc + p.path
        return clean.rstrip("/") or clean

    sitemap_urls: list[str] = []
    discovery_urls: list[str] = []

    if source in ("sitemap", "both"):
        raw, errors = fetch_sitemap_urls(facts["sitemap_url"], timeout, max_pages)
        facts["sitemap_errors"] = errors
        seen: set[str] = set()
        for u in raw:
            if _same_origin(u):
                n = _normalize(u)
                if n not in seen and n != _normalize(base_url):
                    seen.add(n)
                    sitemap_urls.append(n)
        facts["sitemap_count"] = len(sitemap_urls)

    if source in ("discovery", "both"):
        from html.parser import HTMLParser as _HP

        class _LinkParser(_HP):
            def __init__(self) -> None:
                super().__init__()
                self.links: set[str] = set()

            def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
                if tag == "a":
                    href = dict(attrs).get("href", "")
                    if href and not href.startswith(("#", "mailto:", "tel:", "javascript:", "/cdn-cgi/")):
                        full = urllib.parse.urljoin(base_url, href)
                        p = urllib.parse.urlparse(full)
                        if p.scheme in ("http", "https") and p.netloc == parsed.netloc:
                            self.links.add(_normalize(full))

        lp = _LinkParser()
        lp.feed(homepage_html)
        discovery_urls = sorted(u for u in lp.links if u != _normalize(base_url))

    if source == "sitemap":
        urls = sorted(sitemap_urls)[: max_pages - 1]
    elif source == "discovery":
        urls = discovery_urls[: max_pages - 1]
    else:  # both: sitemap first (sorted), then discovery-only, capped
        smap = set(sitemap_urls)
        facts["discovery_only_urls"] = sorted(set(discovery_urls) - smap)
        merged = sorted(sitemap_urls) + facts["discovery_only_urls"]
        urls = merged[: max_pages - 1]
    return urls, facts


# ── Crawl helpers: politeness, suspicious-HTML retry, response metadata ──────

_REQUEST_PAUSE_SECONDS = 0.5
_SUSPICIOUS_TITLE_RE = re.compile(r"<title[^>]*>\s*</title>|<title[^>]*></title>", re.I)


def suspicious_vs_median(html: str, median_words: float) -> bool:
    """Thin-body check used for the final incomplete_fetch verdict (no title check: retry already covered it)."""
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S | re.I)
    words = len(re.findall(r"\w+", re.sub(r"<[^>]+>", " ", text)))
    return median_words > 0 and words < 0.6 * median_words


def _looks_suspicious(html: str, median_words: float) -> bool:
    """Heuristic for partially-served HTML: empty title or thin body vs site median."""
    if _SUSPICIOUS_TITLE_RE.search(html):
        return True
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S | re.I)
    words = len(re.findall(r"\w+", re.sub(r"<[^>]+>", " ", text)))
    return median_words > 0 and words < 0.6 * median_words


def fetch_page_for_crawl(url: str, timeout: int, session: dict[str, Any]) -> dict[str, Any]:
    """Fetch one page with single retry on suspicious HTML. Never raises.

    Returns {url, status, headers, html, bytes, attempts, incomplete_fetch, error}.
    """
    out: dict[str, Any] = {"url": url, "status": 0, "headers": {}, "html": "",
                           "bytes": 0, "attempts": 0, "incomplete_fetch": False, "error": None}
    for attempt in (1, 2):
        out["attempts"] = attempt
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": f"Pandora-AEO/{ENGINE_VERSION} (+https://github.com/zorrovengador/Pandora-AEO)"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                headers = {k.lower(): v for k, v in response.headers.items()}
                body = response.read(2_000_000)
                out.update(status=response.status, headers=headers, bytes=len(body),
                           html=body.decode(response.headers.get_content_charset() or "utf-8", errors="replace"),
                           error=None)
        except Exception as exc:  # noqa: BLE001
            out["error"] = str(exc)
            return out  # transport errors are terminal, not retried
        if attempt == 1 and _looks_suspicious(out["html"], session.get("median_words", 0)):
            time.sleep(_REQUEST_PAUSE_SECONDS)
            continue  # one retry before declaring it incomplete
        break
    else:
        pass
    if _looks_suspicious(out["html"], session.get("median_words", 0)) and out["attempts"] == 2:
        out["incomplete_fetch"] = True
    return out
