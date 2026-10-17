# NZ Data Science + Analytics Forum

An owner-authorised static migration of [analytics.org.nz](https://analytics.org.nz/) for GitHub Pages.

Repository: <https://github.com/antonyede/analytics-org-nz>

Live preview: <https://antonyede.github.io/analytics-org-nz/>. GitHub Pages publishes `main:/docs` on the default GitHub domain. **The preview is deployed; production cutover is not recommended yet.** Contact delivery is disabled, signup delivery is unverified, and the audit identifies inherited validation and mobile/accessibility issues. See [production readiness](PRODUCTION_READINESS.md).

## What is included

- The five live pages: home, Events, About, Contact, and Privacy policy.
- All three published Events archive pages: 25 event records, with original query pagination URLs supported in the browser.
- The source's styled 404, captured from `/sitemap.xml` (which is already a 404 on the source).
- Original responsive layouts, typography, portraits, logos, navigation, hover states and page metadata.
- 47 referenced locally hosted assets, including original Webflow CSS/JavaScript, jQuery, HK Grotesk and Montserrat fonts. No new blanket licence is added; see [asset provenance](ASSET_RIGHTS.md).
- Original Mailchimp subscription actions and external event/profile/social links.
- Owner-requested edits: the TRA sponsor block is removed from all footers; Antony Ede's complete About profile is removed, with the other nine profiles preserved. Both removals are enforced by the builder.

Source HTML and asset bytes are retained under `source/`; publishable files are under `docs/`. GitHub Pages can serve `main:/docs` directly, with `.nojekyll` disabling Jekyll. There is no package install or build step at deployment time and no custom domain configuration.

## Review and verification

See [production readiness](PRODUCTION_READINESS.md), [the migration report](MIGRATION_REPORT.md), [deployed functional results](evidence/deployed-2026-10-17/functional.json), and [deployed screenshots](evidence/deployed-2026-10-17/README.md).

The original local migration had **66/66 identical comparisons** before the two requested content removals. The deployed matrix also passed **66/66 comparisons against the source with only those owner edits applied**, retaining the original source captures alongside the adjusted captures. It uses ordinary headless Chromium on Linux at desktop **1440 × 1000**, tablet **834 × 1112**, and mobile **390 × 844**, with device scale factor 1. Results describe the tested conditions only.

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

To repeat the deployed checks:

```sh
.venv/bin/python scripts/check.py \
  --target https://antonyede.github.io/analytics-org-nz \
  --output evidence/deployed/functional.json
.venv/bin/python scripts/visual_verify.py \
  --target https://antonyede.github.io/analytics-org-nz \
  --output evidence/deployed --owner-edits
.venv/bin/python scripts/audit_deployed.py \
  --revision <PUBLISHED_COMMIT> --output evidence/deployed/audit.json
.venv/bin/python scripts/make_evidence.py \
  --input evidence/deployed --output evidence/deployed/README.md
```

To intentionally refresh the snapshot from the live source, run `scripts/capture_source.py`, inspect its route inventory, rebuild, and repeat comparisons. The builder uses cached original asset bytes when present. Refreshing the archive is a deliberate content update; it is not part of GitHub Pages deployment.

## Known limitations requiring review

The Webflow contact backend and source analytics proxy do not move to static hosting. The contact form keeps its initial appearance and reports unavailable delivery on attempted submission, offering the help address already published in the source privacy statement. Mailchimp is retained but has not been submitted during tests. See the migration report for alternatives, inherited source issues, and URL/JavaScript differences.
