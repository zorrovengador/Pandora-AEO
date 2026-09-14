import unittest
from unittest.mock import patch
from pandora_aeo.engine import (
    audit_page, audit_url, audit_agent_readiness,
    _parse_robots_txt, _cross_page_checks,
    _WELL_KNOWN_ENDPOINTS, _COMMERCE_ENDPOINTS,
    ENGINE_VERSION,
)


class EngineTests(unittest.TestCase):
    def test_engine_version(self):
        self.assertEqual(ENGINE_VERSION, "0.5.0")

    def test_audit_page_reports_8_categories(self):
        html = """<html lang="es-MX"><head><title>Example page</title>
        <meta name="description" content="A useful page">
        <meta property="og:image" content="https://example.com/og.png">
        <meta property="og:title" content="Example">
        <meta property="og:description" content="Desc">
        <link rel="canonical" href="https://example.com/">
        <script type="application/ld+json">{"@context":"https://schema.org"}</script>
        </head><body><h1>Hello</h1><h2>Section</h2><p>Words words words</p>
        <img src="x.jpg" alt="desc"><img src="y.jpg" alt="alt2">
        <link rel="alternate" hreflang="es-MX" href="https://example.com/">
        </body></html>"""
        result = audit_page("https://example.com/", html)
        cats = result["category_scores"]
        expected_cats = {"technicalSeo", "metadata", "htmlSemantics", "structuredData",
                         "llmContent", "i18n", "metaAdsReadiness", "performance"}
        self.assertTrue(expected_cats.issubset(set(cats.keys())))
        self.assertIn("score", result)
        self.assertTrue(0 <= result["score"] <= 100)

    def test_audit_page_detects_missing_h1(self):
        result = audit_page("https://example.com/", "<html><body><h2>Hi</h2></body></html>")
        checks = {c["id"]: c for c in result["checks"]}
        self.assertEqual(checks["H1_COUNT"]["status"], "warn")

    def test_audit_page_detects_heading_hierarchy_break(self):
        html = '<html><body><h2>Title</h2><h4>Skip</h4></body></html>'
        result = audit_page("https://example.com/", html)
        checks = {c["id"]: c for c in result["checks"]}
        self.assertEqual(checks["HEADING_HIERARCHY"]["status"], "warn")

    def test_audit_page_detects_thin_content(self):
        html = '<html><body><h1>Hi</h1><p>Short</p></body></html>'
        result = audit_page("https://example.com/", html)
        checks = {c["id"]: c for c in result["checks"]}
        self.assertEqual(checks["CONTENT_DEPTH"]["status"], "warn")

    def test_audit_page_detects_question_headings(self):
        html = '<html><body><h1>Page</h1><h2>What is AEO?</h2><p>Answer</p></body></html>'
        result = audit_page("https://example.com/", html)
        self.assertEqual(result["facts"]["question_headings"], 1)

    def test_audit_page_detects_og_tags(self):
        html = '<html><head><meta property="og:image" content="x.jpg">'
        html += '<meta property="og:title" content="T"><meta property="og:description" content="D">'
        html += '<title>T</title></head><body><h1>H</h1></body></html>'
        result = audit_page("https://example.com/", html)
        self.assertTrue(result["facts"]["og_image"])
        self.assertTrue(result["facts"]["og_title"])
        self.assertTrue(result["facts"]["og_description"])

    def test_audit_page_detects_hreflang(self):
        html = '<html lang="es-MX"><head><title>T</title>'
        html += '<link rel="alternate" hreflang="es-MX" href="https://example.mx/">'
        html += '</head><body><h1>H</h1></body></html>'
        result = audit_page("https://example.com/", html)
        self.assertEqual(len(result["facts"]["hreflang_tags"]), 1)
        self.assertEqual(result["facts"]["lang_attr"], "es-MX")

    def test_check_has_impact_and_effort(self):
        result = audit_page("https://example.com/", "<title>T</title><h1>H</h1>")
        for check in result["checks"]:
            self.assertIn("impact", check)
            self.assertIn("effort", check)
            self.assertTrue(1 <= check["impact"] <= 10)
            self.assertTrue(1 <= check["effort"] <= 10)

    def test_parse_robots_txt_detects_ai_bots(self):
        robots = "User-Agent: *\nAllow: /\n\nUser-Agent: GPTBot\nAllow: /\n\nSitemap: https://example.com/sitemap.xml"
        parsed = _parse_robots_txt(robots)
        self.assertIn("gptbot", parsed["ai_bots"])
        self.assertEqual(parsed["sitemaps"], ["https://example.com/sitemap.xml"])

    def test_parse_robots_txt_detects_content_signals(self):
        robots = "User-Agent: *\nAllow: /\nContent-Signal: ai-train=no, search=yes"
        parsed = _parse_robots_txt(robots)
        self.assertEqual(len(parsed["content_signals"]), 1)

    def test_cross_page_checks_detect_duplicates(self):
        pages = [
            {"title": "Same Title", "url": "https://example.com/", "word_count": 500},
            {"title": "Same Title", "url": "https://example.com/about", "word_count": 500},
        ]
        checks = _cross_page_checks(pages)
        ids = [c["id"] for c in checks]
        self.assertIn("DUPLICATE_TITLES", ids)

    def test_cross_page_checks_detect_thin_content(self):
        pages = [
            {"title": "A", "url": "https://example.com/", "word_count": 100},
            {"title": "B", "url": "https://example.com/about", "word_count": 200},
        ]
        checks = _cross_page_checks(pages)
        ids = [c["id"] for c in checks]
        self.assertIn("THIN_CONTENT", ids)

    def test_agent_readiness_endpoints_coverage(self):
        check_ids = [eid for eid, _, _, _, _ in _WELL_KNOWN_ENDPOINTS]
        self.assertGreaterEqual(len(check_ids), 8)
        for cid in ("API_CATALOG", "MCP_SERVER_CARD", "AGENT_SKILLS_INDEX"):
            self.assertIn(cid, check_ids)
        commerce_ids = [cid for cid, _, _, _, _ in _COMMERCE_ENDPOINTS]
        self.assertIn("OPENAPI_JSON", commerce_ids)

    @patch("pandora_aeo.engine.fetch_url")
    @patch("pandora_aeo.engine.audit_agent_readiness")
    def test_audit_url_returns_all_sections(self, mock_agent, fetch):
        fetch.return_value = (200, {"content-type": "text/html"}, "<title>Test</title><h1>H</h1>")
        mock_agent.return_value = {"checks": [], "facts": {}}
        result = audit_url("https://example.com/")
        self.assertEqual(result["url"], "https://example.com/")
        self.assertIn("scores", result)
        self.assertIn("category_scores", result["scores"])
        self.assertIn("run", result)
        self.assertIn("retrieval", result)

    def test_private_network_targets_are_rejected(self):
        with self.assertRaises(ValueError):
            audit_url("http://127.0.0.1/admin")


if __name__ == "__main__":
    unittest.main()
