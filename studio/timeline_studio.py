#!/usr/bin/env python3
"""timeline_studio.py — local GUI server for film-universe-timelines.

Serves the editor (index.html) + a small JSON API around the REAL engine
(tools/universe_graph.py). The engine is the only renderer and the only
validator: every edit is validated server-side before it reaches the board,
so a lying chart is impossible by construction (repo principle #1).

API:
  GET  /api/graph?name=advanced-demo   -> {graph, errors, hitboxes_png_b64? no — see /api/render}
  POST /api/validate                   -> {errors}           (body: graph JSON)
  POST /api/render                     -> {png_b64, hitboxes, errors} (body: {graph, style, orientation})
  POST /api/save                       -> {ok, path}         (body: {name, graph})
  GET  /api/examples                   -> {examples: [names]}
Endpoints are stateless; the browser holds the working copy + undo stack.
"""
import base64, io, json, os, re, sys, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repo root
sys.path.insert(0, os.path.join(ROOT, "tools"))
import universe_graph as ug                                            # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES_DIR = os.path.join(ROOT, "examples")


def graph_path(name):
    name = os.path.basename(name)          # no traversal
    return os.path.join(EXAMPLES_DIR, name, f"{name}.universes.json")


def load_graph(name):
    p = graph_path(name)
    if not os.path.exists(p):
        return None, [f"unknown example: {name}"]
    with open(p) as f:
        return json.load(f), []


def validate_graph(g):
    if not isinstance(g, dict):
        return ["graph must be a JSON object"]
    try:
        return ug.validate(g) or []
    except Exception as e:                 # validator crash = report, don't 500
        return [f"validator exception: {e}"]


def render_graph(g, style, orientation):
    hb = []
    img = ug.build(g, style=style, orientation=orientation, hitboxes=hb)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue(), hb


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):             # quiet
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw or b"{}")
        except Exception:
            return None

    # ---------------- GET ----------------
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        if u.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        elif u.path == "/api/examples":
            names = sorted(d for d in os.listdir(EXAMPLES_DIR)
                           if os.path.isdir(os.path.join(EXAMPLES_DIR, d))
                           and os.path.exists(os.path.join(EXAMPLES_DIR, d, f"{d}.universes.json")))
            self._json({"examples": names})
        elif u.path == "/api/graph":
            q = urllib.parse.parse_qs(u.query)
            g, errs = load_graph((q.get("name") or ["demo-film"])[0])
            if g is None:
                self._json({"graph": None, "errors": errs}, 404)
            else:
                self._json({"graph": g, "errors": validate_graph(g)})
        elif u.path == "/api/health":
            self._json({"ok": True})
        else:
            self._json({"error": "not found"}, 404)

    # ---------------- POST ----------------
    def do_POST(self):
        if self.path == "/api/validate":
            g = self._body()
            if g is None:
                return self._json({"errors": ["body is not valid JSON"]}, 400)
            return self._json({"errors": validate_graph(g)})
        if self.path == "/api/render":
            b = self._body()
            if not isinstance(b, dict) or "graph" not in b:
                return self._json({"error": "need {graph, style?, orientation?}"}, 400)
            errs = validate_graph(b["graph"])
            if errs:
                return self._json({"errors": errs, "png_b64": None, "hitboxes": None})
            style = b.get("style") if b.get("style") in ("classic", "weight", "dash", "tape") else "classic"
            orient = b.get("orientation") if b.get("orientation") in ("vertical", "horizontal") else "vertical"
            try:
                png, hb = render_graph(b["graph"], style, orient)
            except Exception as e:
                return self._json({"errors": [f"render failed: {e}"], "png_b64": None, "hitboxes": None})
            return self._json({"errors": [], "png_b64": base64.b64encode(png).decode(), "hitboxes": hb})
        if self.path == "/api/save":
            b = self._body()
            if not isinstance(b, dict) or "name" not in b or "graph" not in b:
                return self._json({"error": "need {name, graph}"}, 400)
            name = re.sub(r"[^a-z0-9-]", "", str(b["name"]).lower()) or "untitled"
            d = os.path.join(EXAMPLES_DIR, name)
            os.makedirs(d, exist_ok=True)
            p = os.path.join(d, f"{name}.universes.json")
            errs = validate_graph(b["graph"])
            if errs:
                return self._json({"error": "refusing to save an invalid graph", "errors": errs}, 400)
            with open(p, "w") as f:
                json.dump(b["graph"], f, indent=2)
                f.write("\n")
            return self._json({"ok": True, "path": os.path.relpath(p, ROOT)})
        self._json({"error": "not found"}, 404)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8092
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"timeline-studio on http://127.0.0.1:{port} (repo: {ROOT})")
    srv.serve_forever()


if __name__ == "__main__":
    main()
