import json
import unittest
from pathlib import Path
from unittest.mock import patch

from pandora_aeo.engine import audit_html, audit_url


class EngineTests(unittest.TestCase):
    def test_audit_html_reports_deterministic_facts(self):
        html = """<html><head><title>Example page</title><meta name='description' content='A useful page'></head><body><h1>Hello</h1><img src='x.jpg'><script type='application/ld+json'>{\"@context\":\"https://schema.org\"}</script></body></html>"""
        result = audit_html('https://example.com/', html)
        checks = {item['id']: item for item in result['checks']}
        self.assertEqual(checks['TITLE_LENGTH']['value'], 12)
        self.assertEqual(checks['IMAGES_WITHOUT_ALT']['value'], 1)
        self.assertEqual(checks['JSON_LD']['status'], 'pass')
        self.assertIn('technical_aeo', result['scores'])

    def test_audit_html_marks_missing_title(self):
        result = audit_html('https://example.com/', '<html><body><h1>Hi</h1></body></html>')
        checks = {item['id']: item for item in result['checks']}
        self.assertEqual(checks['TITLE_PRESENT']['status'], 'fail')

    @patch('pandora_aeo.engine.fetch_url')
    def test_audit_url_returns_manifest_and_evidence(self, fetch):
        fetch.return_value = (200, {'content-type': 'text/html'}, '<title>Test</title>')
        result = audit_url('https://example.com/')
        self.assertEqual(result['target']['url'], 'https://example.com/')
        self.assertEqual(result['retrieval']['status_code'], 200)
        self.assertTrue(result['run']['engine_version'])
        json.dumps(result)

    def test_private_network_targets_are_rejected(self):
        with self.assertRaises(ValueError):
            audit_url('http://127.0.0.1/admin')


if __name__ == '__main__':
    unittest.main()
