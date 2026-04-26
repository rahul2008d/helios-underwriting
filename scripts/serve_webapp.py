"""Tiny static file server for the underwriting workbench UI.

Run with: uv run python -m scripts.serve_webapp
Then open http://localhost:3000 in your browser.

We use a real HTTP server rather than file:// so that fetch() calls to
the backend services work without CORS issues. The backend services have
already been configured with permissive CORS.
"""

from __future__ import annotations

import http.server
import socketserver
from pathlib import Path
from typing import Any

PORT = 3000
WEBAPP_DIR = Path(__file__).parent.parent / "webapp"


class _Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(WEBAPP_DIR), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        # Quieter logging
        if args and isinstance(args[0], str) and "GET / " in args[0]:
            super().log_message(format, *args)


def main() -> None:
    """Serve the webapp on localhost:3000."""
    if not WEBAPP_DIR.exists():
        raise SystemExit(f"webapp directory not found: {WEBAPP_DIR}")

    print(f"Serving Helios workbench from {WEBAPP_DIR}")
    print(f"Open http://localhost:{PORT} in your browser")
    print("Ctrl+C to stop.")

    with socketserver.TCPServer(("", PORT), _Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down.")


if __name__ == "__main__":
    main()
