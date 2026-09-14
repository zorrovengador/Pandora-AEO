"""Deterministic, no-dependency AEO audit engine with Agent Readiness + LLM-friendly content checks.

v0.3 — adds 8-category scoring from the bizbrain AEO system:
  i18n, metadata, llmContent, performance, technicalSeo, htmlSemantics,
  structuredData, metaAdsReadiness.

Each check carries impact (1-10) and effort (1-10) scores.
Per-page scores plus cross-page duplicate-title detection.
"""
from __future__ import annotations

import ipaddress
import json
import re
import socket
import urllib.parse
import urllib.request
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any

from .sitemap_crawl import resolve_crawl_urls, suspicious_vs_median

from . import ENGINE_VERSION  # single source of truth (v0.5.0)

# ── AI bots for robots.txt detection ───────────────────────────────────────
_AI_BOTS = {
    "gptbot", "chatgpt-user", "google-extended", "anthropic-ai", "claude-web",
    "perplexitybot", "facebookbot", "meta-externalagent", "bingbot", "ccbot",
    "cohere-ai", "youbot", "amazonbot", "applebot", "bytespider",
}

# ── .well-known endpoints for Agent Readiness ───────────────────────────────
_WELL_KNOWN_ENDPOINTS = [
    ("API_CATALOG", "/.well-known/api-catalog", "Publish an API catalog (RFC 9727).", 6, 4),
    ("OAUTH_AUTH_SERVER", "/.well-known/oauth-authorization-server", "Publish OAuth authorization server metadata (RFC 8414).", 5, 5),
    ("OIDC_DISCOVERY", "/.well-known/openid-configuration", "Publish OpenID Connect discovery metadata.", 5, 5),
    ("OAUTH_PROTECTED_RESOURCE", "/.well-known/oauth-protected-resource", "Publish OAuth Protected Resource metadata (RFC 9728).", 5, 5),
    ("AUTH_MD", "/auth.md", "Publish auth.md for agent registration.", 6, 4),
    ("MCP_SERVER_CARD", "/.well-known/mcp/server-card.json", "Publish an MCP Server Card (SEP-1649).", 7, 5),
    ("MCP_JSON", "/.well-known/mcp.json", "Publish MCP server metadata.", 7, 5),
    ("AGENT_SKILLS_INDEX", "/.well-known/agent-skills/index.json", "Publish Agent Skills index (RFC v0.2.0).", 7, 4),
]

_COMMERCE_ENDPOINTS = [
    ("ARD_MANIFEST", "/.well-known/ai-catalog.json", "Publish an ARD manifest.", 6, 5),
    ("WEB_BOT_AUTH", "/.well-known/http-message-signatures-directory", "Publish JWKS for Web Bot Auth.", 4, 4),
    ("UCP_PROFILE", "/.well-known/ucp", "Publish UCP profile (ucp.dev).", 5, 5),
    ("ACP_DISCOVERY", "/.well-known/acp.json", "Publish ACP discovery (agenticcommerce.dev).", 5, 5),
    ("OPENAPI_JSON", "/openapi.json", "Publish an OpenAPI specification.", 5, 3),
]

# ── HTML Parser (expanded for v0.3) ─────────────────────────────────────────

class _PageParser(HTMLParser):
    """Parse a single HTML page for all SEO + AEO + LLM-friendly checks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self.description = ""
        self.h1_count = 0
        self.images_total = 0
        self.images_without_alt = 0
        self.canonical = False
        self.json_ld_blocks: list[str] = []
        self._in_json_ld = False
        self._json_ld_buf: list[str] = []
        # v0.3 additions
        self.og_image = False
        self.og_title = False
        self.og_description = False
        self.hreflang_tags: list[str] = []
        self.lang_attr = ""
        self.heading_sequence: list[int] = []  # e.g. [1, 2, 2, 3, 2, 4]
        self._current_tag = None
        self.word_count = 0
        self._text_buf: list[str] = []
        self.question_headings: list[str] = []
        self._in_h = False
        self._h_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        self._current_tag = tag
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = (data.get("name") or "").lower()
            prop = (data.get("property") or "").lower()
            if name == "description":
                self.description = data.get("content") or ""
            elif prop == "og:image":
                self.og_image = bool(data.get("content"))
            elif prop == "og:title":
                self.og_title = bool(data.get("content"))
            elif prop == "og:description":
                self.og_description = bool(data.get("content"))
        elif tag == "h1":
            self.h1_count += 1
            self._in_h = True
            self._h_buf = []
            self.heading_sequence.append(1)
        elif tag in ("h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            self.heading_sequence.append(level)
            self._in_h = True
            self._h_buf = []
        elif tag == "img":
            self.images_total += 1
            if not (data.get("alt") or "").strip():
                self.images_without_alt += 1
        elif tag == "link":
            rel = (data.get("rel") or "").lower()
            if rel == "canonical":
                self.canonical = bool(data.get("href"))
            elif rel == "alternate" and "hreflang" in data:
                self.hreflang_tags.append(data.get("hreflang") or "")
        elif tag == "html":
            self.lang_attr = data.get("lang") or ""
        elif tag == "script" and (data.get("type") or "").lower() == "application/ld+json":
            self._in_json_ld = True
            self._json_ld_buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_json_ld:
            self.json_ld_blocks.append("".join(self._json_ld_buf).strip())
            self._in_json_ld = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self._in_h:
            heading_text = " ".join("".join(self._h_buf).split())
            if heading_text:
                self.question_headings.append(heading_text)
            self._in_h = False
        self._current_tag = None

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_json_ld:
            self._json_ld_buf.append(data)
        if self._in_h:
            self._h_buf.append(data)
        # Collect visible text for word count (skip script/style)
        if self._current_tag and self._current_tag not in ("script", "style", "noscript"):
            self._text_buf.append(data)

    def finalize(self) -> None:
        """Compute word count from collected text."""
        text = " ".join(self._text_buf)
        self.word_count = len(text.split())


def _check(
    check_id: str,
    value: Any,
    status: str,
    evidence: str,
    recommendation: str,
    category: str = "seo_technical",
    impact: int = 5,
    effort: int = 5,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "value": value,
        "status": status,
        "evidence": evidence,
        "recommendation": recommendation,
        "category": category,
        "impact": impact,
        "effort": effort,
    }


# ── Per-page audit (8 categories, matching bizbrain AEO system) ─────────────

def audit_page(url: str, html: str) -> dict[str, Any]:
    """Audit a single page and return checks + per-category scores."""
    parser = _PageParser()
    parser.feed(html)
    parser.finalize()

    title = " ".join(parser.title.split())
    description = " ".join(parser.description.split())
    word_count = parser.word_count

    valid_json_ld = 0
    for block in parser.json_ld_blocks:
        try:
            json.loads(block)
            valid_json_ld += 1
        except json.JSONDecodeError:
            pass

    # Detect question headings (headings that end with ?)
    question_heading_count = sum(1 for h in parser.question_headings if h.endswith("?"))

    # Detect heading hierarchy jumps (e.g., h2 → h4 skipping h3)
    hierarchy_broken = False
    for i in range(1, len(parser.heading_sequence)):
        prev = parser.heading_sequence[i - 1]
        curr = parser.heading_sequence[i]
        if curr > prev + 1:
            hierarchy_broken = True
            break

    # ── Build checks for each category ───────────────────────────────────────
    checks: list[dict[str, Any]] = []

    # Category: SEO Técnico (97 in their system)
    checks.append(_check("TITLE_PRESENT", bool(title), "pass" if title else "fail",
        title[:160], "Add one descriptive title.", "technicalSeo", 8, 1))
    checks.append(_check("TITLE_LENGTH", len(title),
        "pass" if 30 <= len(title) <= 65 else "warn",
        f"len={len(title)}: {title[:80]}",
        "Keep the title between 30 and 65 characters.", "technicalSeo", 4, 1))
    checks.append(_check("META_DESCRIPTION", bool(description), "pass" if description else "fail",
        description[:200], "Add a concise meta description.", "technicalSeo", 7, 2))
    checks.append(_check("H1_COUNT", parser.h1_count,
        "pass" if parser.h1_count == 1 else "warn",
        f"h1_count={parser.h1_count}", "Use exactly one primary H1.", "technicalSeo", 8, 2))
    checks.append(_check("CANONICAL", parser.canonical, "pass" if parser.canonical else "warn",
        f"canonical={parser.canonical}", "Declare the preferred canonical URL.", "technicalSeo", 5, 1))
    checks.append(_check("IMAGES_WITHOUT_ALT", parser.images_without_alt,
        "pass" if parser.images_without_alt == 0 else "warn",
        f"missing_alt={parser.images_without_alt}/{parser.images_total}",
        "Add useful alt text to all images.", "technicalSeo", 5, 2))

    # Category: Metadatos y Etiquetas (91)
    checks.append(_check("OG_IMAGE", parser.og_image, "pass" if parser.og_image else "warn",
        f"og:image={'present' if parser.og_image else 'missing'}",
        "Add <meta property=\"og:image\"> with a 1200x630px image.", "metadata", 8, 2))
    checks.append(_check("OG_TITLE", parser.og_title, "pass" if parser.og_title else "warn",
        f"og:title={'present' if parser.og_title else 'missing'}",
        "Add <meta property=\"og:title\"> with a descriptive title.", "metadata", 5, 1))
    checks.append(_check("OG_DESCRIPTION", parser.og_description, "pass" if parser.og_description else "warn",
        f"og:description={'present' if parser.og_description else 'missing'}",
        "Add <meta property=\"og:description\"> with a page summary.", "metadata", 4, 1))

    # Category: Semántica HTML y Accesibilidad (93)
    checks.append(_check("HEADING_HIERARCHY", not hierarchy_broken,
        "pass" if not hierarchy_broken else "warn",
        f"hierarchy_{'ok' if not hierarchy_broken else 'broken'}: seq={parser.heading_sequence[:10]}",
        "Don't skip heading levels (e.g. h2 → h4). Keep sequential order.", "htmlSemantics", 3, 3))
    checks.append(_check("HEADING_COUNT", len(parser.heading_sequence),
        "pass" if len(parser.heading_sequence) >= 3 else "warn",
        f"headings={len(parser.heading_sequence)}",
        "Use enough headings (h2-h6) to structure content.", "htmlSemantics", 4, 3))

    # Category: Datos Estructurados (98)
    checks.append(_check("JSON_LD", valid_json_ld, "pass" if valid_json_ld else "warn",
        f"valid_blocks={valid_json_ld}; total={len(parser.json_ld_blocks)}",
        "Add valid JSON-LD structured data.", "structuredData", 7, 4))

    # Category: Contenido Amigable para LLM (75)
    checks.append(_check("CONTENT_DEPTH", word_count,
        "pass" if word_count >= 300 else "warn",
        f"word_count={word_count}",
        "Expand content to at least 300 words. AI engines rarely cite thin pages.", "llmContent", 8, 6))
    checks.append(_check("QUESTION_HEADINGS", question_heading_count,
        "pass" if question_heading_count >= 2 else "warn",
        f"question_headings={question_heading_count}/{len(parser.question_headings)}",
        "Convert headings to real questions followed by direct answers. AI engines extract and cite this format.", "llmContent", 6, 4))

    # Category: Internacionalización (71)
    checks.append(_check("HREFLANG", len(parser.hreflang_tags),
        "pass" if parser.hreflang_tags else "warn",
        f"hreflang_tags={len(parser.hreflang_tags)}; lang={parser.lang_attr}",
        "Add <link rel=\"alternate\" hreflang=\"es-MX\" ...> for regional targeting.", "i18n", 4, 3))
    checks.append(_check("LANG_ATTR", bool(parser.lang_attr),
        "pass" if parser.lang_attr else "warn",
        f"lang={parser.lang_attr or '(missing)'}",
        "Declare lang attribute on <html>.", "i18n", 3, 1))

    # Category: Preparación para Meta Ads (94)
    checks.append(_check("META_ADS_READY", parser.og_image and parser.og_title and parser.og_description,
        "pass" if (parser.og_image and parser.og_title and parser.og_description) else "warn",
        f"og:image={parser.og_image} og:title={parser.og_title} og:description={parser.og_description}",
        "Ensure all Open Graph tags (image, title, description) are present for ad sharing.", "metaAdsReadiness", 8, 2))

    # Category: Rendimiento y Seguridad (85) — basic checks
    checks.append(_check("HTML_SIZE", len(html),
        "pass" if len(html) < 500_000 else "warn",
        f"html_bytes={len(html)}",
        "Keep HTML under 500KB for fast rendering.", "performance", 4, 2))

    # ── Compute per-category scores ─────────────────────────────────────────
    categories = [
        "technicalSeo", "metadata", "htmlSemantics", "structuredData",
        "llmContent", "i18n", "metaAdsReadiness", "performance",
    ]
    category_scores: dict[str, dict[str, Any]] = {}
    for cat in categories:
        cat_checks = [c for c in checks if c["category"] == cat]
        cat_passed = sum(1 for c in cat_checks if c["status"] == "pass")
        cat_total = len(cat_checks)
        category_scores[cat] = {
            "score": round(100 * cat_passed / cat_total) if cat_total else 100,
            "passed": cat_passed,
            "total": cat_total,
        }

    # Global page score = average of category scores
    page_score = round(sum(cs["score"] for cs in category_scores.values()) / len(category_scores))

    return {
        "url": url,
        "title": title,
        "word_count": word_count,
        "score": page_score,
        "category_scores": category_scores,
        "checks": checks,
        "facts": {
            "title": title,
            "description": description,
            "word_count": word_count,
            "h1_count": parser.h1_count,
            "images_total": parser.images_total,
            "images_without_alt": parser.images_without_alt,
            "canonical": parser.canonical,
            "valid_json_ld_blocks": valid_json_ld,
            "og_image": parser.og_image,
            "og_title": parser.og_title,
            "og_description": parser.og_description,
            "hreflang_tags": parser.hreflang_tags,
            "lang_attr": parser.lang_attr,
            "heading_sequence": parser.heading_sequence,
            "question_headings": question_heading_count,
            "total_headings": len(parser.heading_sequence),
        },
    }


# ── Cross-page checks (duplicate titles, etc.) ───────────────────────────────

def _cross_page_checks(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect issues that span multiple pages (duplicates, etc.)."""
    checks: list[dict[str, Any]] = []

    # Duplicate titles
    title_urls: dict[str, list[str]] = {}
    for p in pages:
        t = p.get("title", "")
        if t:
            title_urls.setdefault(t, []).append(p["url"])
    duplicates = {t: urls for t, urls in title_urls.items() if len(urls) > 1}
    if duplicates:
        dup_count = len(duplicates)
        affected = sum(len(urls) for urls in duplicates.values())
        checks.append(_check(
            "DUPLICATE_TITLES", dup_count, "warn",
            f"{dup_count} duplicate title(s) across {affected} pages: {list(duplicates.keys())[:3]}",
            "Each page must have a unique and specific <title>.",
            "metadata", 6, 3,
        ))

    # Pages with low word count
    thin_pages = [p for p in pages if p.get("word_count", 0) < 300]
    if thin_pages:
        avg_words = round(sum(p["word_count"] for p in thin_pages) / len(thin_pages))
        checks.append(_check(
            "THIN_CONTENT", len(thin_pages), "warn",
            f"{len(thin_pages)}/{len(pages)} pages have <300 words (avg: {avg_words})",
            "Expand content with direct, detailed answers. AI engines rarely cite thin pages.",
            "llmContent", 8, 6,
        ))

    return checks


# ── Agent Readiness (from v0.2, unchanged) ──────────────────────────────────

def _parse_robots_txt(text: str) -> dict[str, Any]:
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
    sitemaps: list[str] = []
    content_signals: list[str] = []
    current_agents: list[str] = []

    for line in lines:
        if ":" not in line:
            continue
        field, _, value = line.partition(":")
        field = field.strip().lower()
        value = value.strip()
        if field == "user-agent":
            current_agents.append(value.lower())
        elif field == "sitemap":
            sitemaps.append(value)
        elif field == "content-signal":
            content_signals.append(value)

    ai_bots_found = [bot for bot in _AI_BOTS if any(bot in a for a in current_agents)]
    return {"sitemaps": sitemaps, "content_signals": content_signals, "ai_bots": ai_bots_found}


def _validate_public_target(url: str) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only absolute http(s) URLs are allowed")
    host = parsed.hostname
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise ValueError(f"Unable to resolve target host: {host}") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError("Private, loopback, link-local, reserved, or multicast targets are blocked")


def _fetch_simple(url: str, timeout: int, accept: str = "*/*") -> tuple[int, dict[str, str], bytes]:
    _validate_public_target(url)
    req = urllib.request.Request(url, headers={"User-Agent": f"Pandora-AEO/{ENGINE_VERSION}", "Accept": accept})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read(2_000_000)
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, b""


def audit_agent_readiness(url: str, timeout: int = 20) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    homepage_status, homepage_headers, _ = _fetch_simple(url, timeout)
    homepage_link = homepage_headers.get("link", "")

    md_status, md_headers, _ = _fetch_simple(url, timeout, accept="text/markdown")
    supports_markdown = "text/markdown" in md_headers.get("content-type", "")

    robots_status, robots_headers, robots_body = _fetch_simple(base_url + "/robots.txt", timeout)
    robots_text = robots_body.decode("utf-8", errors="replace")
    robots_ok = robots_status == 200 and "text/plain" in robots_headers.get("content-type", "")
    robots_parsed = _parse_robots_txt(robots_text) if robots_ok else {"sitemaps": [], "content_signals": [], "ai_bots": []}

    sitemap_status, sitemap_headers, _ = _fetch_simple(base_url + "/sitemap.xml", timeout)
    sitemap_ok = sitemap_status == 200 and "xml" in sitemap_headers.get("content-type", "").lower()

    dns_aid_found = False
    dns_aid_dnssec = False
    try:
        doh_url = f"https://1.1.1.1/dns-query?name=_index._agents.{parsed.hostname}&type=HTTPS"
        doh_req = urllib.request.Request(doh_url, headers={"Accept": "application/dns-json"})
        with urllib.request.urlopen(doh_req, timeout=timeout) as doh_resp:
            doh_data = json.loads(doh_resp.read().decode())
            if doh_data.get("Answer"):
                dns_aid_found = True
                if doh_data.get("AD"):
                    dns_aid_dnssec = True
    except Exception:
        pass

    agent_checks: list[dict[str, Any]] = []

    agent_checks.append(_check("ROBOTS_TXT", robots_ok, "pass" if robots_ok else "fail",
        f"HTTP {robots_status} /robots.txt", "Publish /robots.txt (RFC 9309).", "discoverability", 7, 2))
    agent_checks.append(_check("SITEMAP", sitemap_ok, "pass" if sitemap_ok else "fail",
        f"HTTP {sitemap_status} /sitemap.xml", "Publish a sitemap.", "discoverability", 6, 2))
    agent_checks.append(_check("LINK_HEADERS", bool(homepage_link), "pass" if homepage_link else "fail",
        f"Link: {homepage_link or '(none)'}", "Add Link headers for discovery (RFC 8288).", "discoverability", 5, 3))
    agent_checks.append(_check("DNS_AID", dns_aid_found,
        "pass" if (dns_aid_found and dns_aid_dnssec) else ("warn" if dns_aid_found else "fail"),
        f"found={dns_aid_found} dnssec={dns_aid_dnssec}", "Publish DNS-AID with DNSSEC (RFC 9460).", "discoverability", 4, 3))

    agent_checks.append(_check("MARKDOWN_NEGOTIATION", supports_markdown, "pass" if supports_markdown else "fail",
        f"Accept:text/markdown -> {md_headers.get('content-type', '')}", "Enable Markdown for Agents.", "content_accessibility", 7, 2))

    ai_bots = robots_parsed.get("ai_bots", [])
    agent_checks.append(_check("AI_BOT_RULES", len(ai_bots),
        "pass" if len(ai_bots) >= 3 else ("warn" if ai_bots else "fail"),
        f"{len(ai_bots)} AI bots configured", "Add AI bot rules to robots.txt.", "bot_access_control", 6, 1))
    content_signals = robots_parsed.get("content_signals", [])
    agent_checks.append(_check("CONTENT_SIGNALS", len(content_signals),
        "pass" if content_signals else "fail",
        f"content_signals={content_signals or '(none)'}", "Add Content-Signal directives.", "bot_access_control", 4, 1))

    for check_id, path, rec, impact, effort in _WELL_KNOWN_ENDPOINTS:
        status_code, _, _ = _fetch_simple(base_url + path, timeout)
        found = status_code == 200
        agent_checks.append(_check(check_id, found, "pass" if found else "fail",
            f"HTTP {status_code} {path}", rec, "api_auth_mcp", impact, effort))

    for check_id, path, rec, impact, effort in _COMMERCE_ENDPOINTS:
        status_code, _, _ = _fetch_simple(base_url + path, timeout)
        found = status_code == 200
        agent_checks.append(_check(check_id, found, "pass" if found else "fail",
            f"HTTP {status_code} {path}", rec, "commerce_info", impact, effort))

    return {"checks": agent_checks, "facts": {
        "robots_txt": {"exists": robots_ok, "ai_bots": ai_bots, "sitemaps": robots_parsed.get("sitemaps", [])},
        "markdown_negotiation": {"supported": supports_markdown},
        "link_headers": {"present": bool(homepage_link)},
        "dns_aid": {"found": dns_aid_found, "dnssec": dns_aid_dnssec},
    }}


# ── Network fetch for HTML pages ─────────────────────────────────────────────

def fetch_url(url: str, timeout: int = 20) -> tuple[int, dict[str, str], str]:
    _validate_public_target(url)
    request = urllib.request.Request(url, headers={"User-Agent": f"Pandora-AEO/{ENGINE_VERSION} (+https://github.com/zorrovengador/Pandora-AEO)"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        headers = {key.lower(): value for key, value in response.headers.items()}
        content_type = headers.get("content-type", "")
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            raise ValueError(f"Target did not return HTML: {content_type or 'unknown'}")
        body = response.read(2_000_000).decode(response.headers.get_content_charset() or "utf-8", errors="replace")
        return response.status, headers, body


# ── Full site audit ──────────────────────────────────────────────────────────

def audit_url(url: str, timeout: int = 20) -> dict[str, Any]:
    """Audit a single page: SEO + AEO + Agent Readiness + LLM-friendly content."""
    measured_at = datetime.now(timezone.utc).isoformat()
    status_code, headers, html = fetch_url(url, timeout)

    # Per-page audit (8 categories)
    page_result = audit_page(url, html)

    # Agent Readiness
    agent_result = audit_agent_readiness(url, timeout)

    # Merge
    all_checks = page_result["checks"] + agent_result["checks"]
    page_result["checks"] = all_checks
    page_result["scores"] = {
        "page_score": page_result["score"],
        "category_scores": page_result["category_scores"],
        "agent_readiness_checks": len([c for c in agent_result["checks"] if c["status"] == "pass"]),
        "agent_readiness_total": len(agent_result["checks"]),
    }
    page_result["facts"]["agent_readiness"] = agent_result["facts"]
    page_result["run"] = {"engine_version": ENGINE_VERSION, "measured_at": measured_at, "timeout_seconds": timeout}
    page_result["retrieval"] = {"status_code": status_code, "content_type": headers.get("content-type", ""), "bytes_read": len(html.encode("utf-8"))}
    return page_result


def audit_site(url: str, timeout: int = 20, max_pages: int = 50, source: str = "both") -> dict[str, Any]:
    """Crawl a site and audit all pages. source: "sitemap" | "discovery" | "both".

    "both" (default) uses the sitemap as the master URL list and discovery as a
    complement; URLs found live but absent from the sitemap are reported in
    agent_readiness facts and drive the SITEMAP_COVERAGE cross-check.
    """
    measured_at = datetime.now(timezone.utc).isoformat()
    if source not in ("sitemap", "discovery", "both"):
        raise ValueError(f"invalid source: {source!r} (use sitemap | discovery | both)")

    # Fetch homepage and discover internal links
    _, _, homepage_html = fetch_url(url, timeout)
    page_result = audit_page(url, homepage_html)
    pages = [page_result]

    crawl_urls, sitemap_facts = resolve_crawl_urls(url, source, timeout, max_pages, homepage_html)

    # Two-pass: first collect page word counts for the median used by the
    # suspicious-HTML heuristic, then audit each page with retry logic.
    from .sitemap_crawl import _REQUEST_PAUSE_SECONDS, fetch_page_for_crawl
    session: dict[str, Any] = {"median_words": 0}
    fetched: dict[str, dict[str, Any]] = {}
    for link in crawl_urls:
        fetched[link] = fetch_page_for_crawl(link, timeout, session)
        time.sleep(_REQUEST_PAUSE_SECONDS)
    import re as _re
    def _words(html: str) -> int:
        t = _re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=_re.S | _re.I)
        return len(_re.findall(r"\w+", _re.sub(r"<[^>]+>", " ", t)))
    words = sorted(_words(f["html"]) for f in fetched.values() if f["html"])
    if words:
        session["median_words"] = words[len(words) // 2]
    # Re-evaluate suspicion now that the median is known
    incomplete: list[str] = []
    for link, f in fetched.items():
        if f["html"] and not f["error"] and suspicious_vs_median(f["html"], session["median_words"]):
            incomplete.append(link)

    for link in crawl_urls:
        f = fetched[link]
        if f["error"] or not f["html"]:
            continue
        p_result = audit_page(link, f["html"])
        p_result["fetch"] = {"status": f["status"], "bytes": f["bytes"], "attempts": f["attempts"],
                             "incomplete_fetch": f["incomplete_fetch"] or link in incomplete}
        pages.append(p_result)

    # Cross-page checks
    cross_checks = _cross_page_checks(pages)

    # Sitemap health checks (v0.5)
    crawl_set = set(crawl_urls)
    stale = sorted(u for u in crawl_urls if u not in {p["url"] for p in pages})
    if source in ("sitemap", "both") and stale:
        cross_checks.append(_check("SITEMAP_STALE", len(stale), "fail",
                                   f"{len(stale)} sitemap URL(s) did not return usable HTML (first: {stale[0]})",
                                   "Remove stale URLs from the sitemap or fix the pages.", "discoverability", 5, 2))
    if source == "both" and sitemap_facts["discovery_only_urls"]:
        n = len(sitemap_facts["discovery_only_urls"])
        cross_checks.append(_check("SITEMAP_COVERAGE", n, "fail",
                                   f"{n} crawled URL(s) missing from sitemap (first: {sitemap_facts['discovery_only_urls'][0]})",
                                   "Add the missing URLs to the sitemap.xml.", "discoverability", 4, 2))

    # Aggregate scores
    category_scores: dict[str, float] = {}
    for cat in ("technicalSeo", "metadata", "htmlSemantics", "structuredData", "llmContent", "i18n", "metaAdsReadiness", "performance"):
        scores = [p["category_scores"].get(cat, {}).get("score", 0) for p in pages]
        category_scores[cat] = round(sum(scores) / len(scores)) if scores else 0

    global_score = round(sum(category_scores.values()) / len(category_scores))

    # Agent readiness
    agent_result = audit_agent_readiness(url, timeout)

    # Collect all checks from all pages + cross-page + agent readiness
    all_checks: list[dict[str, Any]] = []
    for p in pages:
        all_checks.extend(p["checks"])
    all_checks.extend(cross_checks)
    all_checks.extend(agent_result["checks"])

    # Build findings (issues only, sorted by impact)
    findings = sorted(
        [c for c in all_checks if c["status"] != "pass"],
        key=lambda c: c["impact"], reverse=True,
    )

    return {
        "run": {"engine_version": ENGINE_VERSION, "measured_at": measured_at, "timeout_seconds": timeout, "max_pages": max_pages},
        "target": {"url": url},
        "global_score": global_score,
        "category_scores": category_scores,
        "pages": [{"url": p["url"], "title": p["title"], "word_count": p["word_count"], "score": p["score"],
                   **({"fetch": p["fetch"]} if "fetch" in p else {})} for p in pages],
        "findings": findings,
        "findings_count": len(findings),
        "pages_analyzed": len(pages),
        "agent_readiness": {
            "checks": agent_result["checks"],
            "facts": agent_result["facts"],
        },
        "crawl": {"source": source, "sitemap_url": sitemap_facts["sitemap_url"],
                  "sitemap_count": sitemap_facts["sitemap_count"], "sitemap_errors": sitemap_facts["sitemap_errors"],
                  "discovery_only_count": len(sitemap_facts["discovery_only_urls"]),
                  "discovery_only_urls": sitemap_facts["discovery_only_urls"][:20],
                  "incomplete_fetches": sorted({p["url"] for p in pages if p.get("fetch", {}).get("incomplete_fetch")})},
    }
