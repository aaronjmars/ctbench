#!/usr/bin/env bash
# Run the full pipeline for one token, or all tokens in tokens.json.
# Usage: ./run.sh <slug>        # one token
#        ./run.sh               # every token, then serve the dashboard
set -euo pipefail
cd "$(dirname "$0")"

serve() {
  PORT=$((10000 + RANDOM % 50000))
  echo "dashboard: http://localhost:$PORT"
  # no-store so edits show on a normal refresh (no hard reload needed)
  exec python3 -c '
import http.server, sys
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()
http.server.test(HandlerClass=H, port=int(sys.argv[1]), bind="127.0.0.1")
' "$PORT"
}

# ./run.sh serve  -> just serve the existing dashboard, no collection
if [ "${1:-}" = "serve" ]; then
  serve
fi

one() {
  echo "== $1 =="
  python3 collect.py "$1"
  python3 build_batches.py "$1"
  python3 label.py "$1"
  python3 aggregate.py "$1"
}

if [ $# -ge 1 ]; then
  one "$1"
else
  for slug in $(python3 -c "import json;print(' '.join(t['slug'] for t in json.load(open('tokens.json'))['tokens']))"); do
    one "$slug"
  done
  serve
fi
