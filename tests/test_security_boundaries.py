"""Regression tests for cache paths, provider URLs, and table parsing."""
import sys
import io
import urllib.error
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.tools import jolpica_sync as J
from app.tools import openf1_sync as O

class SecurityBoundaryTests(unittest.TestCase):
    def test_upstream_error_streams_are_closed(self):
        url = 'https://api.jolpi.ca/ergast/f1/2026.json'
        for status in (429, 503):
            with self.subTest(status=status):
                stream = io.BytesIO(b'upstream error')
                error = urllib.error.HTTPError(url, status, 'unavailable', {}, stream)
                with patch.object(J._HTTP_OPENER, 'open', side_effect=error), patch.object(J.time, 'sleep'):
                    self.assertIsNone(J._http(url, retries=1))
                self.assertTrue(stream.closed)

    def test_cache_keys_cannot_escape_cache_directory(self):
        for name in ['../secret', '/tmp/secret', '2026_1/../../secret', 'bad\\name']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                J._path(name)
        self.assertEqual(Path(J._path('2026_1_results')).parent, Path(J.CACHE))

    def test_untrusted_urls_are_rejected_before_network_access(self):
        with patch.object(J._HTTP_OPENER, 'open') as request:
            for url in ['http://api.jolpi.ca/ergast/f1/2026.json',
                        'https://api.jolpi.ca.evil.test/ergast/f1/2026.json',
                        'https://api.jolpi.ca@localhost/ergast/f1/2026.json',
                        'https://localhost/ergast/f1/2026.json']:
                with self.subTest(url=url), self.assertRaises(ValueError):
                    J._http(url)
            request.assert_not_called()

    def test_provider_redirects_are_not_followed(self):
        self.assertIsNone(J._NoRedirect().redirect_request(None, None, 302, '', {},
                                                        'http://localhost/private'))

    def test_openf1_untrusted_urls_are_rejected_before_network_access(self):
        with patch.object(J._HTTP_OPENER, 'open') as request:
            for base in ['http://api.openf1.org/v1', 'https://api.openf1.org.evil.test/v1',
                         'https://api.openf1.org@localhost/v1', 'https://api.openf1.org/v2']:
                with self.subTest(base=base), patch.object(O, 'BASE', base), self.assertRaises(ValueError):
                    O._http('sessions?year=2026')
            request.assert_not_called()

if __name__ == '__main__':
    unittest.main()
