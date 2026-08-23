from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from eba_trader.persistence import DEFAULT_DB_PATH, TradeLedger

HOST = os.getenv("EBA_RUNTIME_API_HOST", "127.0.0.1")
PORT = int(os.getenv("EBA_RUNTIME_API_PORT", "8765"))
DB_PATH = Path(os.getenv("EBA_LEDGER_DB", str(DEFAULT_DB_PATH)))


class RuntimeHandler(BaseHTTPRequestHandler):
    server_version = "EBA-Runtime/0.1"

    @property
    def ledger(self) -> TradeLedger:
        return self.server.ledger  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "service": "eba-runtime-api",
                    "database": str(DB_PATH),
                },
            )
            return

        if parsed.path == "/api/v1/positions":
            status = parse_qs(parsed.query).get("status", [None])[0]
            self._json(HTTPStatus.OK, {"positions": self.ledger.list_positions(status=status)})
            return

        if parsed.path.startswith("/api/v1/positions/"):
            position_id = parsed.path.rsplit("/", 1)[-1]
            position = self.ledger.get_position(position_id)
            if position is None:
                self._json(HTTPStatus.NOT_FOUND, {"error": "position_not_found"})
            else:
                self._json(HTTPStatus.OK, {"position": position})
            return

        if parsed.path == "/api/v1/events":
            raw_limit = parse_qs(parsed.query).get("limit", ["100"])[0]
            try:
                limit = int(raw_limit)
            except ValueError:
                limit = 100
            self._json(HTTPStatus.OK, {"events": self.ledger.list_events(limit=limit)})
            return

        self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def run_runtime_api() -> None:
    ledger = TradeLedger(DB_PATH)
    server = ThreadingHTTPServer((HOST, PORT), RuntimeHandler)
    server.ledger = ledger  # type: ignore[attr-defined]
    print(f"EBA runtime API listening on http://{HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    run_runtime_api()
