# NZ Data Science + Analytics Forum

An owner-authorised static migration of [analytics.org.nz](https://analytics.org.nz/) for GitHub Pages.

Repository: <https://github.com/antonyede/analytics-org-nz>

Intended preview: <https://antonyede.github.io/analytics-org-nz/> — **not deployed yet**. The existing GitHub integration returned HTTP 403, `Resource not accessible by integration`, when asked to enable Pages. An owner must select **Settings → Pages → Deploy from a branch → main → /docs → Save**. This uses GitHub's default domain; do not set a custom domain or change DNS. After activation, the published copy still needs the deployed browser checks below.

## What is included

- The five live pages: home, Events, About, Contact, and Privacy policy.
- All three published Events archive pages: 25 event records, with original query pagination URLs supported in the browser.
- The source's styled 404, captured from `/sitemap.xml` (which is already a 404 on the source).
- Original responsive layouts, typography, portraits, logos, navigation, hover states and page metadata.
- 49 locally hosted assets, including original Webflow CSS/JavaScript, jQuery, HK Grotesk and Montserrat fonts. No new blanket licence is added; see [asset provenance](ASSET_RIGHTS.md).
- Original Mailchimp subscription actions and external event/profile/social links.

Source HTML and asset bytes are retained under `source/`; publishable files are under `docs/`. GitHub Pages can serve `main:/docs` directly, with `.nojekyll` disabling Jekyll. There is no package install or build step at deployment time and no custom domain configuration.

## Review and verification

See [the migration report](MIGRATION_REPORT.md), [functional results](evidence/functional.json), and [matched source/target screenshots](evidence/visual-comparisons.md).

All **66/66 comparisons have identical pixels**. The screenshot matrix uses ordinary headless Chromium on Linux at desktop **1440 × 1000**, tablet **834 × 1112**, and mobile **390 × 844**, with device scale factor 1. Results describe those tested conditions only. Public deployment is blocked pending the Pages setting above; no deployed parity is claimed.

## Reproduce locally

Python 3.12+, Chromium, and the development dependencies are required. The migration itself is buildless; these dependencies support rebuilding and verification only.

```sh
python3 -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python scripts/build.py
.venv/bin/python scripts/serve.py
```

The local URL is `http://127.0.0.1:8000/analytics-org-nz/`. In another terminal:

```sh
.venv/bin/python scripts/check.py
.venv/bin/python scripts/visual_verify.py
.venv/bin/python scripts/make_evidence.py
```

Browser scripts use `/usr/bin/chromium`. TLS verification is relaxed only inside the screenshot browser context because this cloud environment's HTTPS inspection certificate is not trusted by Chromium. Normal downloads and Git operations retain their usual certificate checks. Browser verification blocks all non-GET/HEAD requests and source analytics calls, so it cannot send real form submissions.

To compare the deployed preview after an owner enables Pages:

```sh
.venv/bin/python scripts/check.py \
  --target https://antonyede.github.io/analytics-org-nz \
  --output evidence/deployed/functional.json
.venv/bin/python scripts/visual_verify.py \
  --target https://antonyede.github.io/analytics-org-nz \
  --output evidence/deployed
```

To intentionally refresh the snapshot from the live source, run `scripts/capture_source.py`, inspect its route inventory, rebuild, and repeat comparisons. The builder uses cached original asset bytes when present. Refreshing the archive is a deliberate content update; it is not part of GitHub Pages deployment.

## Known limitations requiring review

The Webflow contact backend and source analytics proxy do not move to static hosting. The contact form keeps its initial appearance and reports unavailable delivery on attempted submission, offering the help address already published in the source privacy statement. Mailchimp is retained but has not been submitted during tests. See the migration report for alternatives, inherited source issues, and URL/JavaScript differences.
