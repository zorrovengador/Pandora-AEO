"""Deterministic, no-dependency AEO audit engine."""
from __future__ import annotations

import ipaddress
import json
import socket
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from typing import Any

ENGINE_VERSION = "0.1.0"


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self.description = ""
        self.h1_count = 0
        self.images_without_alt = 0
        self.canonical = False
        self.json_ld_blocks: list[str] = []
        self._in_json_ld = False
        self._json_ld_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta" and data.get("name", "").lower() == "description":
            self.description = data.get("content") or ""
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "img" and not (data.get("alt") or "").strip():
            self.images_without_alt += 1
        elif tag == "link" and data.get("rel", "").lower() == "canonical":
            self.canonical = bool(data.get("href"))
        elif tag == "script" and data.get("type", "").lower() == "application/ld+json":
            self._in_json_ld = True
            self._json_ld_buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_json_ld:
            self.json_ld_blocks.append("".join(self._json_ld_buf).strip())
            self._in_json_ld = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._in_json_ld:
            self._json_ld_buf.append(data)


def _check(check_id: str, value: Any, status: str, evidence: str, recommendation: str) -> dict[str, Any]:
    return {"id": check_id, "value": value, "status": status, "evidence": evidence, "recommendation": recommendation}


def audit_html(url: str, html: str) -> dict[str, Any]:
    parser = _Parser()
    parser.feed(html)
    title = " ".join(parser.title.split())
    description = " ".join(parser.description.split())
    valid_json_ld = 0
    for block in parser.json_ld_blocks:
        try:
            json.loads(block)
            valid_json_ld += 1
        except json.JSONDecodeError:
            pass
    checks = [
        _check("TITLE_PRESENT", bool(title), "pass" if title else "fail", title[:160], "Add one descriptive title."),
        _check("TITLE_LENGTH", len(title), "pass" if 10 <= len(title) <= 60 else "warn", title[:160], "Keep the title between 10 and 60 characters."),
        _check("META_DESCRIPTION", bool(description), "pass" if description else "fail", description[:200], "Add a concise meta description."),
        _check("H1_COUNT", parser.h1_count, "pass" if parser.h1_count == 1 else "warn", f"h1_count={parser.h1_count}", "Use exactly one primary H1."),
        _check("IMAGES_WITHOUT_ALT", parser.images_without_alt, "pass" if parser.images_without_alt == 0 else "warn", f"missing_alt={parser.images_without_alt}", "Add useful alt text to informative images."),
        _check("CANONICAL", parser.canonical, "pass" if parser.canonical else "warn", f"canonical={parser.canonical}", "Declare the preferred canonical URL."),
        _check("JSON_LD", valid_json_ld, "pass" if valid_json_ld else "warn", f"valid_blocks={valid_json_ld}; total_blocks={len(parser.json_ld_blocks)}", "Add valid JSON-LD structured data."),
    ]
    passed = sum(item["status"] == "pass" for item in checks)
    score = round(100 * passed / len(checks))
    return {"target": {"url": url}, "checks": checks, "scores": {"technical_aeo": score}, "facts": {"title": title, "description": description, "h1_count": parser.h1_count, "images_without_alt": parser.images_without_alt, "valid_json_ld_blocks": valid_json_ld}}


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


def fetch_url(url: str, timeout: int = 20) -> tuple[int, dict[str, str], str]:
    _validate_public_target(url)
    request = urllib.request.Request(url, headers={"User-Agent": "Pandora-AEO/0.1 (+https://github.com/zorrovengador/Pandora-AEO)"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        headers = {key.lower(): value for key, value in response.headers.items()}
        content_type = headers.get("content-type", "")
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            raise ValueError(f"Target did not return HTML: {content_type or 'unknown content type'}")
        body = response.read(2_000_000).decode(response.headers.get_content_charset() or "utf-8", errors="replace")
        return response.status, headers, body


def audit_url(url: str, timeout: int = 20) -> dict[str, Any]:
    measured_at = datetime.now(timezone.utc).isoformat()
    status_code, headers, html = fetch_url(url, timeout)
    result = audit_html(url, html)
    result["run"] = {"engine_version": ENGINE_VERSION, "measured_at": measured_at, "timeout_seconds": timeout}
    result["retrieval"] = {"status_code": status_code, "content_type": headers.get("content-type", ""), "bytes_read": len(html.encode("utf-8"))}
    return result
