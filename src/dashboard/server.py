"""Thin HTTP layer over dashboard.queries - see ADR-0008 (local web app, no
data leaves the machine). Binds to localhost only.
"""

import json
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from dashboard import queries


def build_server(store, host: str = "127.0.0.1", port: int = 0) -> HTTPServer:
    # Single-threaded: the sqlite connection on `store` is not safe for
    # concurrent access, and this is a single local user - one request at a
    # time is fine.
    return HTTPServer((host, port), _make_handler(store))


def _make_handler(store):
    class OverviewRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path != "/api/overview":
                self._send_json(404, {"error": "Not found"})
                return

            params = parse_qs(parsed.query)
            try:
                year = int(params["year"][0])
                month = int(params["month"][0])
            except (KeyError, ValueError, IndexError):
                self._send_json(400, {"error": "year and month query parameters are required integers"})
                return

            overview = queries.get_month_overview(store, year=year, month=month)
            self._send_json(200, asdict(overview))

        def log_message(self, format, *args):
            pass

        def _send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return OverviewRequestHandler
