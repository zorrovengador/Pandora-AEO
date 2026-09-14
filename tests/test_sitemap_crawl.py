"""Offline tests for v0.5 sitemap-driven crawling (no network)."""
import unittest
from unittest import mock
from unittest.mock import patch

from pandora_aeo.sitemap_crawl import (
    _looks_suspicious,
    fetch_page_for_crawl,
    fetch_sitemap_urls,
    resolve_crawl_urls,
    suspicious_vs_median,
)

SITEMAP_INDEX = """<?xml version="1.0"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>https://x.com/sitemap-posts.xml</loc></sitemap>
<sitemap><loc>https://x.com/sitemap-pages.xml</loc></sitemap>
</sitemapindex>"""

SITEMAP_POSTS = """<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://x.com/a</loc></url>
<url><loc>https://x.com/b/</loc></url>
<url><loc>https://other.com/external</loc></url>
</urlset>"""

SITEMAP_PAGES = """<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://x.com/c</loc></url>
</urlset>"""

HOME = """<html><body>
<a href="/live-only">Live</a><a href="/a">A</a><a href="https://x.com/b">B</a>
<a href="mailto:x@y.z">m</a><a href="#frag">f</a><a href="https://evil.com">e</a>
</body></html>"""


class _Headers(dict):
    def __init__(self, charset="utf-8"):
        super().__init__({"Content-Type": "text/xml"})
        self._c = charset

    def get_content_charset(self):
        return self._c


class FakeResponse:
    def __init__(self, body, status=200):
        self._body = body.encode()
        self.status = status
        self.headers = _Headers()

    def read(self, n=-1):
        return self._body[:n] if n > 0 else self._body

    def get_content_charset(self):
        return "utf-8"

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeURLOpenMixin:
    def _fake_urlopen(self, bodies):
        def opener(req, timeout=20):
            url = req.full_url if hasattr(req, "full_url") else req
            for key, body in bodies.items():
                if url.endswith(key):
                    return FakeResponse(body)
            raise AssertionError(f"unexpected url {url}")
        return opener

    def test_index_followed(self):
        bodies = {"sitemap.xml": SITEMAP_INDEX, "sitemap-posts.xml": SITEMAP_POSTS, "sitemap-pages.xml": SITEMAP_PAGES}
        with patch("pandora_aeo.sitemap_crawl.urllib.request.urlopen", side_effect=self._fake_urlopen(bodies)):
            urls, errors = fetch_sitemap_urls("https://x.com/sitemap.xml")
        self.assertEqual(sorted(urls), ["https://other.com/external", "https://x.com/a", "https://x.com/b/", "https://x.com/c"])
        self.assertEqual(errors, [])

    def test_fetch_failure_recorded_not_raised(self):
        with patch("pandora_aeo.sitemap_crawl.urllib.request.urlopen", side_effect=OSError("boom")):
            urls, errors = fetch_sitemap_urls("https://x.com/sitemap.xml")
        self.assertEqual(urls, [])
        self.assertTrue(errors and "boom" in errors[0])

    def test_max_urls_truncates(self):
        with patch("pandora_aeo.sitemap_crawl.urllib.request.urlopen",
                   side_effect=self._fake_urlopen({"sitemap.xml": SITEMAP_POSTS})):
            urls, errors = fetch_sitemap_urls("https://x.com/sitemap.xml", max_urls=1)
        self.assertEqual(len(urls), 1)
        self.assertTrue(any("truncated" in e for e in errors))


class TestResolveCrawlUrls(_FakeURLOpenMixin, unittest.TestCase):
    def test_both_union_and_delta(self):
        bodies = {"sitemap.xml": SITEMAP_INDEX, "sitemap-posts.xml": SITEMAP_POSTS, "sitemap-pages.xml": SITEMAP_PAGES}
        with patch("pandora_aeo.sitemap_crawl.urllib.request.urlopen", side_effect=self._fake_urlopen(bodies)):
            urls, facts = resolve_crawl_urls("https://x.com/", "both", 20, 100, HOME)
        names = [u.rsplit("/", 1)[-1] for u in urls]
        self.assertIn("a", names)
        self.assertIn("live-only", names)  # discovered, not in sitemap
        self.assertNotIn("external", names)  # other origin excluded
        self.assertEqual(facts["discovery_only_urls"], ["https://x.com/live-only"])
        self.assertEqual(facts["sitemap_count"], 3)  # /a, /b, /c (dedup, origin-filtered)

    def test_discovery_only_is_legacy(self):
        urls, facts = resolve_crawl_urls("https://x.com/", "discovery", 20, 100, HOME)
        self.assertEqual(facts["discovery_only_urls"], [])
        self.assertIn("https://x.com/a", urls)  # linked on homepage; discovery-only delta is empty here

    def test_sitemap_only_deterministic_sorted(self):
        bodies = {"sitemap.xml": SITEMAP_INDEX, "sitemap-posts.xml": SITEMAP_POSTS, "sitemap-pages.xml": SITEMAP_PAGES}
        with patch("pandora_aeo.sitemap_crawl.urllib.request.urlopen", side_effect=self._fake_urlopen(bodies)):
            urls1, _ = resolve_crawl_urls("https://x.com/", "sitemap", 20, 100, HOME)
            urls2, _ = resolve_crawl_urls("https://x.com/", "sitemap", 20, 100, HOME)
        self.assertEqual(urls1, urls2)
        self.assertEqual(urls1, sorted(urls1))

    def test_invalid_source_rejected(self):
        with self.assertRaises(ValueError):
            resolve_crawl_urls("https://x.com/", "bogus", 20, 100, HOME)


class TestSuspiciousHTML(unittest.TestCase):
    def test_empty_title_suspicious(self):
        self.assertTrue(_looks_suspicious("<html><title></title><body>" + "word " * 500 + "</body></html>", 100))

    def test_thin_body_vs_median(self):
        full = "<html><title>t</title><body>" + "word " * 1000 + "</body></html>"
        thin = "<html><title>t</title><body>" + "word " * 100 + "</body></html>"
        self.assertFalse(_looks_suspicious(full, 900))
        self.assertTrue(_looks_suspicious(thin, 900))
        self.assertTrue(suspicious_vs_median(thin, 900))

    def test_healthy_page_not_suspicious(self):
        html = "<html><title>Curso</title><body>" + "palabra " * 900 + "</body></html>"
        self.assertFalse(_looks_suspicious(html, 900))


class TestFetchPageForCrawl(unittest.TestCase):
    def test_no_retry_on_healthy(self):
        html = "<html><title>t</title><body>" + "w " * 900 + "</body></html>"
        with patch("pandora_aeo.sitemap_crawl.urllib.request.urlopen", return_value=FakeResponse(html, 200)):
            r = fetch_page_for_crawl("https://x.com/ok", 20, {"median_words": 0})
        self.assertEqual(r["attempts"], 1)
        self.assertFalse(r["incomplete_fetch"])
        self.assertEqual(r["status"], 200)

    def test_retry_then_incomplete_flag(self):
        thin = "<html><title></title><body>thin</body></html>"
        with patch("pandora_aeo.sitemap_crawl.urllib.request.urlopen", return_value=FakeResponse(thin, 200)):
            r = fetch_page_for_crawl("https://x.com/bad", 20, {"median_words": 900})
        self.assertEqual(r["attempts"], 2)
        self.assertTrue(r["incomplete_fetch"])

    def test_transport_error_terminal(self):
        with patch("pandora_aeo.sitemap_crawl.urllib.request.urlopen", side_effect=OSError("refused")):
            r = fetch_page_for_crawl("https://x.com/dead", 20, {"median_words": 0})
        self.assertEqual(r["attempts"], 1)
        self.assertTrue(r["error"])
        self.assertEqual(r["status"], 0)


if __name__ == "__main__":
    unittest.main()
