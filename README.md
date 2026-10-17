# NZ Data Science + Analytics Forum

An owner-authorised static migration of [analytics.org.nz](https://analytics.org.nz/) for GitHub Pages.

Repository: <https://github.com/antonyede/analytics-org-nz>

Live preview: <https://antonyede.github.io/analytics-org-nz/>. GitHub Pages publishes `main:/docs` on the default GitHub domain. Contact uses `hello@analytics.org.nz`; the [daily Eventbrite sync](EVENT_SYNC.md) is authenticated and working. Newsletter delivery and inherited validation/mobile/accessibility issues remain separate production-readiness items.

## What is included

- The five live pages: home, Events, About, Contact, and Privacy policy.
- Three Eventbrite archive pages containing 23 verified public events, with original query pagination URLs and direct no-JavaScript pages. The original 25-row manual snapshot remains under `source/` for provenance.
- The source's styled 404, captured from `/sitemap.xml` (which is already a 404 on the source).
- Original responsive layouts, typography, portraits, logos, navigation, hover states and page metadata.
- 47 referenced locally hosted source assets, plus 19 verified Eventbrite images. No new blanket licence is added.
- Original Mailchimp subscription actions and external event/profile/social links.
- Owner-requested edits: the TRA sponsor block is removed from all footers; Antony Ede's complete About profile is removed, with the other nine profiles preserved. Both removals are enforced by the builder.
- Contact form replaced by a visible email link; newsletter retained separately. Daily 06:17 UTC/manual Eventbrite workflow has validation, safe retention and freshness diagnostics. The authenticated run succeeded on 17 October 2026 at 03:55:13 UTC with 23 public events and 19 images. See [live sync status](https://antonyede.github.io/analytics-org-nz/event-sync-status.json) for later attempts.

Source HTML and asset bytes are retained under `source/`; publishable files are under `docs/`. GitHub Pages can serve `main:/docs` directly, with `.nojekyll` disabling Jekyll. There is no package install or build step at deployment time and no custom domain configuration.

## Review and verification

See [current sync verification](evidence/event-sync/400-fix-live/README.md), [production readiness](PRODUCTION_READINESS.md), and [earlier migration screenshots](evidence/deployed-2026-10-17/README.md).

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

The Contact page now provides `mailto:hello@analytics.org.nz`, which uses the visitor's email app; inbox delivery was not tested. Mailchimp is retained but has not been submitted. The source analytics proxy remains omitted. [Eventbrite sync setup](EVENT_SYNC.md) explains the required repository secret and why an unauthenticated scraper was not used. See the production report for remaining inherited issues.
