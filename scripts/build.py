"""Build the Pages directory from the owner-authorised published snapshot.

Only GETs public assets. Never connects to a form submission endpoint.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlsplit
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
OUT = ROOT / "docs"
BASE = "/analytics-org-nz"
ASSETS = {}
# Match the WOFF2 representation served to the browser used for source QA.
# A generic/legacy UA receives different TTF outlines from Google Fonts.
DOWNLOAD_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/154.0.0.0 Safari/537.36"


def asset(url):
    if url.startswith("//"):
        url = "https:" + url
    if not url.startswith(("https://", "http://")):
        return url
    if url in ASSETS:
        return BASE + "/" + ASSETS[url]["path"]
    part = urlsplit(url)
    name = re.sub(r"[^a-zA-Z0-9_.-]", "_", unquote(part.path.rsplit("/", 1)[-1])) or "asset"
    if part.netloc == "fonts.googleapis.com":
        name = "montserrat.css"
    relative = "assets/" + hashlib.sha256(url.encode()).hexdigest()[:12] + "-" + name
    path = OUT / relative
    ASSETS[url] = {"path": relative}
    cache = ROOT / "source" / "assets" / path.name
    cache.parent.mkdir(exist_ok=True)
    if cache.exists():
        data = cache.read_bytes()
    else:
        with urlopen(Request(url, headers={"User-Agent": DOWNLOAD_UA}), timeout=60) as response:
            data = response.read()
        cache.write_bytes(data)
    ASSETS[url]["sha256"] = hashlib.sha256(data).hexdigest()
    ASSETS[url]["bytes"] = len(data)
    if name.endswith(".css"):
        text = data.decode("utf-8")
        def replace(match):
            target = match[1].strip("\"' ")
            if target.startswith("data:"):
                return match[0]
            return 'url("' + asset(urljoin(url, target)) + '")'
        data = re.sub(r"url\(([^)]+)\)", replace, text).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return BASE + "/" + relative


def transform(record):
    soup = BeautifulSoup((SOURCE / record["file"]).read_text(), "html.parser")
    for script in list(soup.select("script")):
        src = script.get("src", "")
        code = script.get_text()
        if src.startswith("/nvhc") or "google_tags_first_party" in code or "gtag(" in code:
            script.decompose()
        elif "webfont" in src:
            script.decompose()
        elif "WebFont.load" in code:
            link = soup.new_tag("link", rel="stylesheet", href=asset("https://fonts.googleapis.com/css?family=Montserrat:100,100italic,200,200italic,300,300italic,400,400italic,500,500italic,600,600italic,700,700italic,800,800italic,900,900italic"))
            script.replace_with(link)
    for link in list(soup.select('link[rel="preconnect"]')):
        link.decompose()
    for tag in soup.find_all(True):
        for attr in ["src", "href", "poster"]:
            value = tag.get(attr)
            if not value:
                continue
            if attr == "href" and tag.name == "a":
                absolute = urljoin(record["url"], value)
                parts = urlsplit(absolute)
                if value.startswith("#"):
                    continue
                if parts.hostname in ("analytics.org.nz", "www.analytics.org.nz"):
                    route = parts.path.rstrip("/")
                    tag[attr] = BASE + (route + "/" if route else "/") + ("?" + parts.query if parts.query else "") + ("#" + parts.fragment if parts.fragment else "")
            elif value.startswith(("https://", "http://", "//")):
                tag[attr] = asset(value)
                tag.attrs.pop("integrity", None)
                tag.attrs.pop("crossorigin", None)
        if tag.has_attr("srcset"):
            candidates = []
            for candidate in tag["srcset"].split(","):
                pieces = candidate.strip().split()
                if pieces:
                    candidates.append(" ".join([asset(pieces[0]), *pieces[1:]]))
            tag["srcset"] = ", ".join(candidates)
        if tag.get("style") and "url(" in tag["style"]:
            tag["style"] = re.sub(r"url\([\"']?(https?://[^)'\"]+)[\"']?\)", lambda m: 'url("' + asset(m[1]) + '")', tag["style"])
    # Webflow's form delivery belongs to the source hosting account. Do not let
    # the static preview post there or claim a successful delivery.
    for form in soup.select(".w-form form:not([action])"):
        form["data-static-unavailable"] = "true"
        form["action"] = "#"
        # Outside a dialog, this method never submits data to a server. The
        # normal JS path supplies the explanatory message; noscript stays safe.
        form["method"] = "dialog"
        fallback = soup.new_tag("noscript")
        fallback.string = "Contact form delivery is unavailable. Please email help@analytics.org.nz to get in touch."
        form.append(fallback)
    if urlsplit(record["url"]).path == "/events":
        fallback = soup.new_tag("noscript")
        for label, path in [("Events page 1", "/events/"), ("Events page 2", "/events/page/2/"), ("Events page 3", "/events/page/3/")]:
            link = soup.new_tag("a", href=BASE + path)
            link.string = label
            fallback.append(link)
            fallback.append(" ")
        soup.select_one("main").append(fallback)
    if soup.body:
        runtime = soup.new_tag("script", src=BASE + "/migration.js")
        soup.body.append(runtime)
    return soup


def main():
    global BASE
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-path", default=BASE)
    args = parser.parse_args()
    BASE = args.base_path.rstrip("/")
    OUT.mkdir(exist_ok=True)
    records = json.loads((SOURCE / "routes.json").read_text())["routes"]
    pages = {r["url"]: transform(r) for r in records if r["title"]}
    event = pages["https://analytics.org.nz/events"]
    for number in (2, 3):
        variant = pages[f"https://analytics.org.nz/events?522c7db6_page={number}"]
        template = event.new_tag("template", id=f"events-page-{number}")
        template.append(BeautifulSoup(str(variant.select_one("main")), "html.parser"))
        event.body.insert(4, template)
        # A directly addressable fallback also makes each archived page useful
        # with scripting disabled; normal navigation retains Webflow's query URL.
        path = OUT / "events" / "page" / str(number) / "index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(variant) + "\n")
    selector = event.new_tag("script")
    selector.string = """(() => {
  const number = new URLSearchParams(location.search).get('522c7db6_page');
  const page = document.getElementById('events-page-' + number);
  if (page) document.querySelector('main').replaceWith(page.content.cloneNode(true));
})();"""
    # Run after the main/templates have parsed, before Webflow initialises.
    first_script = event.body.find("script", recursive=False)
    first_script.insert_before(selector)
    for record in records:
        if not record["title"]:
            continue
        route = urlsplit(record["url"])
        if route.query:
            continue
        if record["status"] == 404:
            path = OUT / "404.html"
        else:
            path = OUT / route.path.strip("/") / "index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(pages[record["url"]]) + "\n")
    (OUT / ".nojekyll").touch()
    (OUT / "robots.txt").write_text("")
    (ROOT / "source" / "assets.json").write_text(json.dumps(ASSETS, indent=2) + "\n")
    print(f"Built {len(pages)} captured states; self-hosted {len(ASSETS)} assets in docs/")


if __name__ == "__main__":
    main()
