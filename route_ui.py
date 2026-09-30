"""Local map UI for the generated marathon GeoJSON route."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).parent
GIS_TOOLS = (
    PROJECT_ROOT
    / "planner_agent"
    / "skills"
    / "gis-spatial-engineering"
    / "scripts"
    / "tools.py"
)
UI_ROOT = PROJECT_ROOT / "route_ui"


def _load_route_from_file(route_file: Path) -> dict | None:
    if not route_file.exists():
        return None
    with route_file.open(encoding="utf-8") as handle:
        route = json.load(handle)
    if route.get("type") != "FeatureCollection":
        raise ValueError(f"{route_file} is not a GeoJSON FeatureCollection")
    return route


def _generate_route(seed: int) -> dict:
    spec = importlib.util.spec_from_file_location("gis_tools_for_ui", GIS_TOOLS)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load GIS tools from {GIS_TOOLS}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = asyncio.run(module.plan_marathon_route(seed=seed, runner_count=10000))
    if result.get("status") != "success":
        raise RuntimeError(result.get("message", "Route generation failed"))
    return result["geojson"]


def make_handler(route_file: Path, seed: int):
    class RouteHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(UI_ROOT), **kwargs)

        def do_GET(self):  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/route":
                try:
                    route = _load_route_from_file(route_file)
                    source = str(route_file) if route is not None else "local GIS generator"
                    if route is None:
                        route = _generate_route(seed)
                    payload = {"source": source, "route": route}
                    body = json.dumps(payload).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except Exception as exc:  # noqa: BLE001
                    body = json.dumps({"error": str(exc)}).encode("utf-8")
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                return
            super().do_GET()

        def log_message(self, format, *args):  # noqa: A002
            print(f"[route-ui] {self.address_string()} - {format % args}")

    return RouteHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Display a marathon route on a local map")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--route-file", type=Path, default=Path("marathon_route.geojson"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), make_handler(args.route_file, args.seed))
    print(f"Route UI running at http://{args.host}:{args.port}")
    print(f"Route source: {args.route_file} if present, otherwise local GIS generator (seed={args.seed})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping route UI")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
