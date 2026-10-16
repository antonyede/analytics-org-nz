"""Read-only, bounded crawl of published source HTML and its pagination links."""
import hashlib
import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://analytics.org.nz"
OUT = ROOT / "source"


def fetch(url):
    request = Request(url, headers={"User-Agent": "AnalyticsMigration/1.0 (owner-authorised static archive)"})
    try:
        with urlopen(request, timeout=45) as response:
            return response.status, response.read(), dict(response.headers), response.url
    except HTTPError as error:
        return error.code, error.read(), dict(error.headers), error.url


def key(url):
    parts = urlsplit(url)
    return urlunsplit(("https", "analytics.org.nz", parts.path or "/", parts.query, ""))


def main():
    OUT.mkdir(exist_ok=True)
    queue = deque([SOURCE + "/", SOURCE + "/robots.txt", SOURCE + "/sitemap.xml"])
    seen, records = set(), []
    while queue:
        url = key(queue.popleft())
        if url in seen:
            continue
        seen.add(url)
        if len(seen) > 200:
            raise RuntimeError("Unexpected route count: inspect crawl scope")
        status, data, headers, final = fetch(url)
        filename = hashlib.sha256(url.encode()).hexdigest()[:16] + (".html" if b"<html" in data.lower() else ".txt")
        (OUT / filename).write_bytes(data)
        soup = BeautifulSoup(data.decode("utf-8"), "html.parser")
        links = sorted({urljoin(url, a["href"]) for a in soup.select("a[href]")})
        records.append({"url": url, "status": status, "final_url": final, "file": filename,
                        "title": soup.title.get_text() if soup.title else None,
                        "sha256": hashlib.sha256(data).hexdigest(), "links": links})
        print(status, url, len(data), flush=True)
        if status == 200 and filename.endswith(".html"):
            for link in links:
                p = urlsplit(link)
                if p.hostname in ("analytics.org.nz", "www.analytics.org.nz"):
                    queue.append(key(link))
    manifest = {"captured_at": datetime.now(timezone.utc).isoformat(), "source": SOURCE, "routes": records}
    (OUT / "routes.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
