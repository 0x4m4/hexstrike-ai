#!/usr/bin/env python3
"""Offline tests for the crt.sh subdomain enumeration tool.

Covers the pure ``parse_crtsh_certificates`` helper and the
``/api/tools/crtsh`` Flask route with the crt.sh HTTP call mocked, so no
network access and no crt.sh availability are required.

Run from the repository root:

    python3 -m unittest discover -s tests -v
"""

import json
import os
import sys
import unittest
from unittest.mock import patch

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hexstrike_server import app, parse_crtsh_certificates  # noqa: E402


# Fixture shaped like real crt.sh JSON: one object per certificate, with
# ``name_value`` holding one or more hostnames separated by newlines.
FIXTURE_ENTRIES = [
    {"name_value": "example.com"},
    {"name_value": "www.example.com\nmail.example.com"},
    {"name_value": "*.api.example.com"},
    {"name_value": "EXAMPLE.COM\nWWW.EXAMPLE.COM"},  # case + duplicates
    {"name_value": "other-domain.com"},  # out of scope (shared hosting)
    {"name_value": "notexample.com"},  # looks similar, still out of scope
    {"name_value": "deep.sub.example.com"},
    {"name_value": ""},
    {"name_value": "*.example.com"},
    {"issuer_name": "No name_value field here"},
    "not-a-dict",
    None,
]


class FakeResponse:
    """Minimal stub of ``requests.Response`` for the mocked crt.sh call."""

    def __init__(self, status_code=200, payload=None, bad_json=False):
        self.status_code = status_code
        self._payload = payload
        self._bad_json = bad_json

    def json(self):
        if self._bad_json:
            raise ValueError("No JSON object could be decoded")
        return self._payload


class TestParseCrtshCertificates(unittest.TestCase):
    def test_dedupes_and_sorts_in_scope_subdomains(self):
        self.assertEqual(
            parse_crtsh_certificates(FIXTURE_ENTRIES, "example.com"),
            [
                "api.example.com",
                "deep.sub.example.com",
                "example.com",
                "mail.example.com",
                "www.example.com",
            ],
        )

    def test_strips_wildcard_prefix(self):
        self.assertEqual(
            parse_crtsh_certificates([{"name_value": "*.api.example.com"}], "example.com"),
            ["api.example.com"],
        )

    def test_drops_out_of_scope_names(self):
        self.assertEqual(
            parse_crtsh_certificates(
                [{"name_value": "other.com\nsub.other.com"}, {"name_value": "evil-example.com"}],
                "example.com",
            ),
            [],
        )

    def test_empty_and_malformed_input(self):
        self.assertEqual(parse_crtsh_certificates([], "example.com"), [])
        self.assertEqual(parse_crtsh_certificates(None, "example.com"), [])
        self.assertEqual(parse_crtsh_certificates("not-a-list", "example.com"), [])
        self.assertEqual(parse_crtsh_certificates(FIXTURE_ENTRIES, ""), [])
        self.assertEqual(parse_crtsh_certificates(FIXTURE_ENTRIES, None), [])

    def test_domain_with_trailing_dot_and_case(self):
        self.assertEqual(
            parse_crtsh_certificates([{"name_value": "a.Example.COM"}], "EXAMPLE.com."),
            ["a.example.com"],
        )


class TestCrtshRoute(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_missing_domain_returns_400(self):
        response = self.client.post("/api/tools/crtsh", json={})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Domain parameter is required", response.get_json()["error"])

    @patch("hexstrike_server.requests.get")
    def test_success_returns_deduped_subdomains(self, mock_get):
        mock_get.return_value = FakeResponse(200, FIXTURE_ENTRIES)
        response = self.client.post("/api/tools/crtsh", json={"domain": "example.com"})
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["success"])
        self.assertEqual(body["tool"], "crtsh")
        self.assertEqual(body["domain"], "example.com")
        self.assertEqual(body["count"], 5)
        self.assertEqual(body["certificates_seen"], len(FIXTURE_ENTRIES))
        self.assertEqual(
            body["subdomains"],
            [
                "api.example.com",
                "deep.sub.example.com",
                "example.com",
                "mail.example.com",
                "www.example.com",
            ],
        )
        called_url = mock_get.call_args[0][0]
        self.assertIn("crt.sh", called_url)
        self.assertIn("output=json", called_url)
        self.assertIn("%25.example.com", called_url)

    @patch("hexstrike_server.requests.get")
    def test_exclude_expired_adds_query_param(self, mock_get):
        mock_get.return_value = FakeResponse(200, [])
        response = self.client.post(
            "/api/tools/crtsh", json={"domain": "example.com", "exclude_expired": True}
        )
        self.assertEqual(response.status_code, 200)
        called_url = mock_get.call_args[0][0]
        self.assertIn("exclude=expired", called_url)

    @patch("hexstrike_server.requests.get")
    def test_upstream_http_error_returns_502(self, mock_get):
        mock_get.return_value = FakeResponse(502, None)
        response = self.client.post("/api/tools/crtsh", json={"domain": "example.com"})
        self.assertEqual(response.status_code, 502)
        self.assertFalse(response.get_json()["success"])

    @patch("hexstrike_server.requests.get")
    def test_upstream_invalid_json_returns_502(self, mock_get):
        mock_get.return_value = FakeResponse(200, None, bad_json=True)
        response = self.client.post("/api/tools/crtsh", json={"domain": "example.com"})
        self.assertEqual(response.status_code, 502)
        self.assertFalse(response.get_json()["success"])

    @patch("hexstrike_server.requests.get")
    def test_upstream_request_failure_returns_502(self, mock_get):
        mock_get.side_effect = requests.RequestException("connection timed out")
        response = self.client.post("/api/tools/crtsh", json={"domain": "example.com"})
        self.assertEqual(response.status_code, 502)
        self.assertFalse(response.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
