"""Validate generated routes/assets and exercise local UI without real submissions."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from events_view import split_events

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PREFIX = "/analytics-org-nz"
TARGET = "http://127.0.0.1:8000" + PREFIX


def main():
    global TARGET
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default=TARGET)
    parser.add_argument("--output", default="evidence/functional.json")
    args = parser.parse_args()
    TARGET = args.target.rstrip("/")
    parsed_target = urlsplit(TARGET)
    origin = parsed_target.scheme + "://" + parsed_target.netloc
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    feed_file = ROOT / 'data/events.json'
    past_events = split_events(json.loads(feed_file.read_text())['events'])[1] if feed_file.exists() else [None] * 25
    page_count = max(1, (len(past_events) + 9) // 10)
    def expected_count(number):
        return min(10, max(0, len(past_events) - (number - 1) * 10))
    missing, internal, placeholders, external = [], set(), [], set()
    for file in sorted(DOCS.rglob("*.html")):
        soup = BeautifulSoup(file.read_text(), "html.parser")
        for footer in soup.select('.section.footer'):
            assert not footer.select('.sponsored-by, a[href="https://tra.co.nz/"]'), str(file)
            assert not footer.select('img[src*="NZDatalogo-04"]'), str(file)
            assert len(footer.select('.footer-social-links-container a')) == 3, str(file)
        if file == DOCS / 'about/index.html':
            names = [x.get_text(strip=True) for x in soup.select('.w-dyn-item h3.name')]
            assert 'Antony Ede' not in names and len(names) == 9, names
            assert not soup.select('a[href="https://www.linkedin.com/in/antonyede/"]'), str(file)
        for tag in soup.select("[href], [src], [srcset]"):
            values = [tag[a] for a in ["href", "src"] if tag.get(a)]
            if tag.get("srcset"):
                values.extend(c.strip().split()[0] for c in tag["srcset"].split(","))
            for value in values:
                parts = urlsplit(value)
                if value == "#":
                    placeholders.append({"page": str(file.relative_to(ROOT)), "text": tag.get_text(" ", strip=True)})
                elif value.startswith(PREFIX + "/"):
                    path = DOCS / parts.path.removeprefix(PREFIX + "/")
                    if not (path.is_file() or (path / "index.html").is_file()):
                        missing.append({"page": str(file), "url": value})
                    internal.add(value)
                elif parts.scheme in ("http", "https"):
                    external.add(value)
    assets = json.loads((ROOT / "source" / "assets.json").read_text())
    for url, record in assets.items():
        if not (DOCS / record["path"]).is_file():
            missing.append({"asset_source": url, "path": record["path"]})
    assert not missing, missing
    metadata_routes = []
    for record in json.loads((ROOT / "source" / "routes.json").read_text())["routes"]:
        route = urlsplit(record["url"])
        if record["status"] != 200 or not record["title"] or route.query:
            continue
        original = BeautifulSoup((ROOT / "source" / record["file"]).read_text(), "html.parser")
        migrated = BeautifulSoup((DOCS / route.path.strip("/") / "index.html").read_text(), "html.parser")
        assert [str(x) for x in original.select("meta")] == [str(x) for x in migrated.select("meta")]
        assert original.title.text == migrated.title.text
        metadata_routes.append(record["url"])
    for route in sorted(internal):
        with urlopen(origin + route) as response:
            assert response.status == 200, route
    ui = []
    posts = []
    unexpected_external = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        page = browser.new_page(ignore_https_errors=True, viewport={"width": 390, "height": 844})
        def guard(route):
            if route.request.method not in ("GET", "HEAD"):
                posts.append(route.request.url)
                route.abort()
            else:
                if not route.request.url.startswith(origin + "/"):
                    unexpected_external.append(route.request.url)
                route.continue_()
        page.route("**/*", guard)
        page.goto(TARGET + "/", wait_until="networkidle")
        page.locator(".menu-button").click()
        page.wait_for_timeout(1500)
        assert page.locator(".full-screen-menu").is_visible()
        page.locator('.full-screen-menu a[href="' + PREFIX + '/events/"]').click()
        page.wait_for_load_state("networkidle")
        assert page.locator(".collection-list-wrapper-2 .w-dyn-item").count() == expected_count(1)
        ui.append("Mobile menu opens and Events navigation works")
        for number in range(2,min(3,page_count)+1):
            page.locator('a[aria-label="Next Page"]').click()
            page.wait_for_load_state("networkidle")
            assert f"522c7db6_page={number}" in page.url
            assert page.locator(".collection-list-wrapper-2 .w-dyn-item").count() == expected_count(number)
        last_page = min(3,page_count)
        page.reload(wait_until="networkidle")
        assert page.locator(".collection-list-wrapper-2 .w-dyn-item").count() == expected_count(last_page)
        if last_page > 1:
            page.locator('a[aria-label="Previous Page"]').click()
            page.wait_for_load_state("networkidle")
            assert f"522c7db6_page={last_page-1}" in page.url
            page.go_back(wait_until="networkidle")
            assert f"522c7db6_page={last_page}" in page.url
        ui.append("Pagination next, previous, reload and browser history preserve query URLs and records")
        page.goto(TARGET + "/contact/", wait_until="networkidle")
        assert page.locator('#email-form').count() == 0
        assert page.locator('a[href="mailto:hello@analytics.org.nz"]').is_visible()
        assert page.locator('#mc-embedded-subscribe-form').count() == 1
        assert not posts, posts
        page.screenshot(path=str(output.parent / "contact-email-mobile.png"), full_page=True)
        ui.append("Contact form replaced by visible mailto:hello@analytics.org.nz; newsletter remains separate; no email sent")
        for route in ("/", "/contact/"):
            page.goto(TARGET + route, wait_until="networkidle")
            form = page.locator("#mc-embedded-subscribe-form")
            assert form.get_attribute("action") == "https://analytics.us9.list-manage.com/subscribe/post?u=1a3a91f39ef59858d7c75f6ba&id=db8c88dafd"
            assert form.get_attribute("method") == "post"
            assert form.locator('[name="b_1a3a91f39ef59858d7c75f6ba_db8c88dafd"]').count() == 1
        ui.append("Both Mailchimp actions, field names, target and bot honeypot preserved; no real subscription submitted")
        nojs = browser.new_page(ignore_https_errors=True, java_script_enabled=False, viewport={"width": 390, "height": 844})
        nojs.route("**/*", guard)
        nojs.goto(TARGET + "/contact/", wait_until="networkidle")
        assert nojs.locator('#email-form').count() == 0
        assert nojs.locator('a[href="mailto:hello@analytics.org.nz"]').is_visible()
        assert not posts, posts
        nojs.goto(TARGET + "/events/", wait_until="networkidle")
        fallback = PREFIX + (f'/events/page/{last_page}/' if last_page > 1 else '/events/')
        nojs.locator('noscript a[href="' + fallback + '"]').click()
        nojs.wait_for_load_state("networkidle")
        assert nojs.locator(".collection-list-wrapper-2 .w-dyn-item").count() == expected_count(last_page)
        nojs.close()
        ui.append("Without JavaScript the contact email link is visible and direct archive fallback links work")
        assert not unexpected_external, unexpected_external
        browser.close()
    report = {"target": TARGET, "internal_urls_checked": len(internal), "self_hosted_assets_checked": len(assets), "metadata_routes_checked": metadata_routes, "missing_assets_or_pages": missing,
              "external_links_preserved": sorted(external), "inherited_placeholders": placeholders,
              "ui_checks": ui, "network_submissions": posts, "unexpected_external_resource_requests": unexpected_external}
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("external_links_preserved", "inherited_placeholders")}, indent=2))


if __name__ == "__main__":
    main()
