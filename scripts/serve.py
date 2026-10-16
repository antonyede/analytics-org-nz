"""Preview the exact GitHub project Pages prefix without rewriting files."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1] / "docs"
PREFIX = "/analytics-org-nz"


class Handler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        route = urlsplit(path).path
        if route == PREFIX:
            route += "/"
        if route.startswith(PREFIX + "/"):
            route = route[len(PREFIX):]
        return super().translate_path(route)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)


if __name__ == "__main__":
    print("Preview: http://127.0.0.1:8000/analytics-org-nz/", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
