"""Read-only deployment and form audit. Never requests a form action URL.

External destinations are GET-only reachability checks. A 403/429 is recorded as
inconclusive rather than described as a broken link. Form validation is inspected
in the DOM without clicking a signup button or invoking a submission method.
"""
import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
PREFIX = "/analytics-org-nz"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36"


def read_url(url):
    try:
        response = urlopen(Request(url, headers={"User-Agent": UA}), timeout=40)
    except HTTPError as error:
        response = error
    except Exception as error:
        return {"url": url, "error": type(error).__name__ + ": " + str(error)}
    with response:
        body = response.read()
        result = {"url": url, "status": response.status, "final_url": response.url,
                  "content_type": response.headers.get("Content-Type"),
                  "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
        if "text/html" in (result['content_type'] or ''):
            soup = BeautifulSoup(body.decode('utf-8', errors='replace'), 'html.parser')
            result['title'] = soup.title.get_text(' ', strip=True) if soup.title else None
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', default='https://antonyede.github.io/analytics-org-nz')
    parser.add_argument('--revision', default='2cf17cd')
    parser.add_argument('--output', default='evidence/deployed-2026-10-17/audit.json')
    args = parser.parse_args()
    target = args.target.rstrip('/')
    parts = urlsplit(target)
    origin = urlunsplit((parts.scheme, parts.netloc, '', '', ''))
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'target': target,
              'expected_revision': args.revision, 'form_actions_requested': [], 'post_requests': []}
    internal, external, placeholders = set(), set(), []
    for file in DOCS.rglob('*.html'):
        soup = BeautifulSoup(file.read_text(), 'html.parser')
        for link in soup.select('a[href]'):
            href = link['href']
            if href.startswith(PREFIX + '/'):
                internal.add(href)
            elif href.startswith(('https://', 'http://')):
                # Strip fragment only; retain event destination query parameters.
                p = urlsplit(href)
                external.add(urlunsplit((p.scheme,p.netloc,p.path,p.query,'')))
            elif href == '#':
                placeholders.append({'page': str(file.relative_to(DOCS)), 'text': link.get_text(' ',strip=True),
                                     'hidden_overlay': bool(link.find_parent(class_='overlay'))})
    revision_query = '?migration_revision=' + args.revision
    expected_files = []
    for file in DOCS.rglob('*'):
        if not file.is_file() or file.name == '.nojekyll':
            continue
        route = file.relative_to(DOCS).as_posix()
        if route.endswith('index.html'):
            route = route[:-10]
        expected_files.append((target + '/' + quote(route) + revision_query, file))
    with ThreadPoolExecutor(max_workers=6) as pool:
        files = list(pool.map(lambda pair: read_url(pair[0]), expected_files))
    for result, (_, file) in zip(files, expected_files):
        result['local_file'] = file.relative_to(ROOT).as_posix()
        result['matches_local_bytes'] = result.get('sha256') == hashlib.sha256(file.read_bytes()).hexdigest()
    report['deployed_files'] = files
    with ThreadPoolExecutor(max_workers=6) as pool:
        report['internal_links'] = list(pool.map(read_url, [origin + value for value in sorted(internal)]))
        report['external_links'] = list(pool.map(read_url, sorted(external)))
    report['inherited_placeholders'] = placeholders
    expected_404 = hashlib.sha256((DOCS / '404.html').read_bytes()).hexdigest()
    report['missing_routes'] = []
    for path in ['/sitemap.xml', '/missing-route-audit-' + args.revision, '/events/missing-record-audit-' + args.revision]:
        result = read_url(target + path + revision_query)
        result['custom_404_matches_local_bytes'] = result.get('sha256') == expected_404
        report['missing_routes'].append(result)
    report['forms'], report['responsive_dom'] = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        context = browser.new_context(ignore_https_errors=True)
        def guard(route):
            request = route.request
            if request.method not in ('GET', 'HEAD'):
                report['post_requests'].append({'method': request.method, 'url': request.url})
                route.abort()
            elif 'list-manage.com' in request.url:
                report['form_actions_requested'].append(request.url)
                route.abort()
            else:
                route.continue_()
        context.route('**/*', guard)
        page = context.new_page()
        for route in ['/', '/events/', '/events/?522c7db6_page=2', '/events/?522c7db6_page=3', '/about/', '/contact/', '/privacy-policy/']:
            page.goto(target + route + ('&' if '?' in route else '?') + 'migration_revision=' + args.revision, wait_until='networkidle')
            for form in page.locator('form').all():
                record = form.evaluate('''form => ({
                  id: form.id, visible: !!form.getClientRects().length,
                  action: form.action, method: form.method, target: form.target,
                  noValidate: form.noValidate, disabledForStaticHosting: form.hasAttribute('data-static-unavailable'),
                  insideWebflowFormWrapper: !!form.closest('.w-form'),
                  emptyFormNativeValidity: form.checkValidity(),
                  fields: [...form.querySelectorAll('input, textarea')].map(field => {
                    const old = field.value;
                    let emailChecks = null;
                    if (field.type === 'email') {
                      field.value = ''; const empty = field.checkValidity();
                      field.value = 'not-an-email'; const malformed = field.checkValidity();
                      field.value = 'audit@example.invalid'; const formatted = field.checkValidity();
                      field.value = old;
                      emailChecks = {empty, malformed, formatted};
                    }
                    return {name: field.name, type: field.type, required: field.required, className: field.className,
                      maxLength: field.maxLength, emailChecks};
                  }),
                  inlineSubmitHandler: form.getAttribute('onsubmit'),
                  mailchimpValidationGlobalPresent: typeof window.mc !== 'undefined' || typeof window.mcvalidate !== 'undefined'
                })''')
                record['route'] = route
                report['forms'].append(record)
        for viewport in [{'width':1440,'height':1000}, {'width':834,'height':1112}, {'width':390,'height':844}]:
            page.set_viewport_size(viewport)
            for route in ['/', '/about/']:
                page.goto(target + route + revision_query, wait_until='networkidle')
                page.evaluate('document.fonts.ready')
                metrics = page.evaluate('''() => {
                  const rect = x => x ? x.getBoundingClientRect().toJSON() : null;
                  const footer = document.querySelector('.section.footer');
                  const privacy = footer?.querySelector('.footer-link.email');
                  return {
                    sponsorLinks: footer?.querySelectorAll('a[href="https://tra.co.nz/"]').length || 0,
                    sponsorText: !!footer?.textContent.includes('Sponsored by'),
                    antonyProfileCount: [...document.querySelectorAll('.w-dyn-item h3.name')].filter(x => x.textContent.trim() === 'Antony Ede').length,
                    profileNames: [...document.querySelectorAll('.w-dyn-item h3.name')].map(x=>x.textContent.trim()),
                    horizontalOverflow: document.documentElement.scrollWidth > innerWidth,
                    footer: rect(footer), footerOverflow: footer ? getComputedStyle(footer).overflow : null,
                    socialLinks: rect(footer?.querySelector('.footer-social-links-container')),
                    privacyDisplay: privacy ? getComputedStyle(privacy).display : null,
                    menuTabIndex: document.querySelector('.menu-button')?.tabIndex,
                    menuRole: document.querySelector('.menu-button')?.getAttribute('role')
                  };
                }''')
                metrics.update({'route':route,'viewport':viewport})
                report['responsive_dom'].append(metrics)
        browser.close()
    report['summary'] = {
        'files_checked': len(files), 'file_status_or_byte_mismatches': sum(x.get('status') != 200 or not x['matches_local_bytes'] for x in files),
        'internal_links_checked': len(report['internal_links']),
        'internal_link_errors': sum(x.get('status') != 200 for x in report['internal_links']),
        'external_links_checked': len(report['external_links']),
        'external_restricted_or_unavailable': sum(x.get('status',0) >= 400 or 'error' in x for x in report['external_links']),
        'missing_routes_checked': len(report['missing_routes']),
        'custom_404_pass': all(x.get('status') == 404 and x['custom_404_matches_local_bytes'] for x in report['missing_routes']),
        'forms': len(report['forms']), 'visible_forms': sum(x['visible'] for x in report['forms']),
        'no_form_requests': not report['post_requests'] and not report['form_actions_requested']
    }
    report['finished_at'] = datetime.now(timezone.utc).isoformat()
    out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report['summary'], indent=2),flush=True)
    for link in report['external_links']:
        print('External:',link.get('status',link.get('error')),link['url'],flush=True)


if __name__ == '__main__':
    main()
