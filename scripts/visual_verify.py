"""Matched Chromium source/target screenshots, including real UI states.

Usage: python scripts/visual_verify.py [--target https://antonyede.github.io/analytics-org-nz]
Only reads the live site. Blocks all non-GET/HEAD requests, including forms.
"""
import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from PIL import Image, ImageChops, ImageStat
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ROUTES = [
    ("home", "/"), ("events", "/events"),
    ("events-page-1", "/events?522c7db6_page=1"),
    ("events-page-2", "/events?522c7db6_page=2"),
    ("events-page-3", "/events?522c7db6_page=3"),
    ("about", "/about"), ("contact", "/contact"),
    ("privacy-policy", "/privacy-policy"), ("404", "/sitemap.xml"),
]
SIZES = {"desktop": (1440, 1000), "tablet": (834, 1112), "mobile": (390, 844)}


def compare(left, right, diff):
    a, b = Image.open(left).convert("RGB"), Image.open(right).convert("RGB")
    size_match = a.size == b.size
    width, height = max(a.width, b.width), max(a.height, b.height)
    def pad(im):
        result = Image.new("RGB", (width, height), "magenta")
        result.paste(im)
        return result
    delta = ImageChops.difference(pad(a), pad(b))
    channels = delta.split()
    mask = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2]).point(lambda n: 255 if n else 0)
    pixels = mask.histogram()[255]
    if pixels:
        delta.save(diff)
    return {"source_size": list(a.size), "target_size": list(b.size), "size_match": size_match,
            "different_pixels": pixels, "different_percent": round(pixels * 100 / (width * height), 6),
            "mean_channel_delta": round(sum(ImageStat.Stat(delta).mean) / 3, 6),
            "difference_bounds": delta.getbbox(), "exact_pixels": delta.getbbox() is None and size_match}


def ready(page):
    page.evaluate("document.fonts.ready")
    page.evaluate("""async () => {
      for (let y = 0; y < document.documentElement.scrollHeight; y += 700) {
        window.scrollTo(0, y); await new Promise(r => setTimeout(r, 70));
      }
      await Promise.all([...document.images].map(i => i.decode().catch(() => {})));
      window.scrollTo(0, 0);
    }""")
    page.wait_for_timeout(800)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="http://127.0.0.1:8000/analytics-org-nz")
    parser.add_argument("--output", default="evidence/local")
    parser.add_argument("--routes", nargs="*", help="Restrict to named routes after a failure")
    parser.add_argument("--owner-edits", action="store_true", help="Also compare against source DOM with the two requested removals")
    parser.add_argument("--cache-bust", help="Append this revision to target HTML requests")
    args = parser.parse_args()
    out = ROOT / args.output
    out.mkdir(parents=True, exist_ok=True)
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "source": "https://analytics.org.nz",
              "target": args.target, "platform": platform.platform(), "viewports": SIZES,
              "device_scale_factor": 1, "comparisons": [], "network_errors": [], "console_errors": []}
    report['expected_owner_edits'] = ['Remove TRA sponsor anchor from footer; preserve wrapper', 'Remove complete Antony Ede profile from About'] if args.owner_edits else []
    report['target_revision_query'] = args.cache_bust
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"])
        report["browser"] = browser.version
        for size, (width, height) in SIZES.items():
            for name, route in ROUTES:
                if args.routes and name not in args.routes:
                    continue
                states = ["default"]
                if name != "404":
                    states.append("menu-open")
                if name in ("events", "events-page-2", "events-page-3"):
                    states.append("event-hover")
                if name in ("home", "contact"):
                    states.append("form-focus")
                files = {}
                for side, origin in [("source", "https://analytics.org.nz"), ("target", args.target.rstrip("/"))]:
                    context = browser.new_context(ignore_https_errors=True, viewport={"width": width, "height": height}, device_scale_factor=1, locale="en-US", timezone_id="UTC", color_scheme="light")
                    def guard(request_route):
                        request = request_route.request
                        if request.method not in ("GET", "HEAD") or "/nvhc" in request.url or "google-analytics.com" in request.url:
                            request_route.abort()
                        else:
                            request_route.continue_()
                    context.route("**/*", guard)
                    page = context.new_page()
                    page.on("pageerror", lambda e: report["console_errors"].append({"side": side, "route": route, "viewport": size, "error": str(e)}))
                    page.on("response", lambda r: report["network_errors"].append({"side": side, "route": route, "viewport": size, "status": r.status, "url": r.url}) if r.status >= 400 and not (name == "404" and r.request.resource_type == "document") else None)
                    target_route = route
                    if side == "target" and name == "404" and origin.startswith("http://127."):
                        target_route = "/404.html"
                    if side == 'target' and args.cache_bust:
                        target_route += ('&' if '?' in target_route else '?') + 'migration_revision=' + args.cache_bust
                    response = page.goto(origin + target_route, wait_until="networkidle", timeout=60000)
                    ready(page)
                    for state in states:
                        if state == "menu-open":
                            page.locator(".menu-button").click()
                            page.wait_for_timeout(1500)
                        elif state in ("event-hover", "form-focus"):
                            if page.locator(".full-screen-menu").is_visible():
                                page.locator(".menu-button").click()
                                page.wait_for_timeout(1500)
                            if state == "event-hover":
                                page.locator(".collection-list-wrapper-2 .w-dyn-item").first.hover()
                            else:
                                page.locator("#mce-EMAIL").focus()
                            page.wait_for_timeout(500)
                        filename = f"{size}-{name}-{state}-{side}.png"
                        page.screenshot(path=str(out / filename), full_page=True, animations="disabled")
                        files[(side, state)] = filename
                        if side == 'source' and args.owner_edits:
                            page.evaluate(r'''() => {
                              const nodes = [...document.querySelectorAll('.section.footer a[href="https://tra.co.nz/"]')];
                              if (location.pathname.replace(/\/$/, '') === '/about') {
                                document.querySelectorAll('.w-dyn-item').forEach(x => {
                                  if (x.querySelector('h3.name')?.textContent.trim() === 'Antony Ede') nodes.push(x);
                                });
                              }
                              window.__qaOwnerRemovals = nodes.map(node => ({node, parent: node.parentNode, next: node.nextSibling}));
                              nodes.forEach(x => x.remove());
                            }''')
                            expected = f'{size}-{name}-{state}-source-with-owner-edits.png'
                            page.screenshot(path=str(out / expected), full_page=True, animations='disabled')
                            files[('expected', state)] = expected
                            page.evaluate('''() => {
                              window.__qaOwnerRemovals.forEach(x => x.parent.insertBefore(x.node, x.next));
                              delete window.__qaOwnerRemovals;
                            }''')
                    context.close()
                for state in states:
                    prefix = f"{size}-{name}-{state}"
                    reference = files[('expected', state)] if args.owner_edits else files[('source', state)]
                    result = compare(out / reference, out / files[("target", state)], out / (prefix + "-diff.png"))
                    if args.owner_edits:
                        result['expected_screenshot'] = reference
                        result['unmodified_source_difference'] = compare(out / files[('source', state)], out / files[('target', state)], out / (prefix + '-unmodified-source-diff.png'))
                    result.update({"route": route, "name": name, "viewport": size, "state": state,
                                   "source_screenshot": files[("source", state)], "target_screenshot": files[("target", state)]})
                    report["comparisons"].append(result)
                    print(prefix, "EXACT" if result["exact_pixels"] else str(result["different_percent"]) + "% differ", flush=True)
                (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
        browser.close()
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["summary"] = {"comparisons": len(report["comparisons"]), "exact": sum(r["exact_pixels"] for r in report["comparisons"]), "network_errors": len(report["network_errors"]), "console_errors": len(report["console_errors"])}
    (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["summary"]), flush=True)


if __name__ == "__main__":
    main()
