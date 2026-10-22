#!/usr/bin/env python3
import argparse
import os
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse


class VoiceClientHandler(BaseHTTPRequestHandler):
    websocket_url = None

    def log_message(self, format, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path in ("/", "/index.html"):
            self.serve_client_page()
        else:
            self.send_error(404, "Not found")

    def serve_client_page(self):
        try:
            html_path = os.path.join(os.path.dirname(__file__), "index.html")
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

            html_content = html_content.replace("{{WEBSOCKET_URL}}", self.websocket_url or "")

            content = html_content.encode()
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, "index.html not found")


def main():
    parser = argparse.ArgumentParser(description="Nova 2.5 Sonic Demo Client")
    parser.add_argument("--ws-url", default="ws://localhost:8083/ws", help="WebSocket server URL")
    parser.add_argument("--port", type=int, default=3002, help="HTTP server port (default: 3002)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")

    args = parser.parse_args()
    VoiceClientHandler.websocket_url = args.ws_url

    print("=" * 60)
    print("Nova 2.5 Sonic — Live Voice Agent Demo")
    print("=" * 60)
    print(f"WebSocket: {args.ws_url}")
    print(f"Server:    http://localhost:{args.port}")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    if not args.no_browser:
        webbrowser.open(f"http://localhost:{args.port}")

    httpd = HTTPServer(("", args.port), VoiceClientHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()
