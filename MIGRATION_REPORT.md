# Migration review

**Current status, 17 October 2026:** [the GitHub Pages preview](https://antonyede.github.io/analytics-org-nz/) is deployed. The requested TRA sponsor footer and Antony Ede profile removals are live. See [the production-readiness audit](PRODUCTION_READINESS.md) for the deployed checks and unresolved launch issues. The source-capture/local-verification details below describe the original migration; the subsequent owner edits are explicit differences.

Subsequent requested updates: Contact now provides `mailto:hello@analytics.org.nz`, with its newsletter preserved. A daily/manual Eventbrite API workflow is installed and its failure-retention path is verified, but authenticated sync is blocked by missing `EVENTBRITE_TOKEN`. See [current implementation and status](EVENT_SYNC.md) and [new live checks](evidence/event-sync/README.md). The original archive is retained and clearly labelled; no successful API sync is claimed.

## Scope and source discovery

The source was reachable with HTTP 200 in this cloud environment. Ordinary Chromium screenshots worked using Playwright with the environment's certificate proxy accommodated in the browser context. The mounted repository was `antonyede/analytics-org-nz`, on local branch `work`, based on remote `main` commit `6b8b07fd390e8bbb9d1158f2d1e1a4ae34f8cb94`. It contained only `README.md`, no user modifications, and no applicable `AGENTS.md` files were found.

The read-only crawl followed every same-origin anchor, including every published Events pagination link. It found these live routes/states:

| Source | Static equivalent | Content |
| --- | --- | --- |
| `/` | `/analytics-org-nz/` | Homepage and mailing-list form |
| `/events` | `/analytics-org-nz/events/` | Current events empty; 10 past events |
| `/events?522c7db6_page=1` | `/analytics-org-nz/events/?522c7db6_page=1` | Explicit first-page alias |
| `/events?522c7db6_page=2` | `/analytics-org-nz/events/?522c7db6_page=2` | 10 past events |
| `/events?522c7db6_page=3` | `/analytics-org-nz/events/?522c7db6_page=3` | 5 past events |
| `/about` | `/analytics-org-nz/about/` | Source snapshot: 10 profiles; current copy: nine after the requested Antony Ede removal |
| `/contact` | `/analytics-org-nz/contact/` | Contact and Mailchimp forms |
| `/privacy-policy` | `/analytics-org-nz/privacy-policy/` | Original privacy statement |
| `/sitemap.xml` (404) | `docs/404.html`, Pages 404 handler | Source's styled not-found screen |

`/robots.txt` returns an empty 200 on the source and is preserved. `/sitemap.xml` returns a styled 404; it was not treated as a valid sitemap. Search-index reconnaissance returned the same five pages and Events pagination. All 25 event records were examined: 24 link to external event sites and one links to `#`. The 10 committee profiles link externally to LinkedIn. No internal CMS detail URL was exposed by those links, embedded page markup, or search results. Unlinked/unpublished Webflow records cannot be enumerated without an owner export; none are represented as discovered or migrated detail pages.

## Implementation

The builder preserves published markup, styling, images and runtime behaviour rather than recreating layouts by eye. Asset references are rewritten for the GitHub project path, with 47 public source resources referenced after the requested removals (49 in the initial snapshot). CSS font/image URLs and responsive image candidates are included. The original title, social-title metadata, viewport and favicon are retained. Tracking-specific source scripts are removed, and the external WebFont loader is replaced by a local Montserrat stylesheet using the same WOFF2 representation as the source browser. The builder removes only the requested footer sponsor anchor and Antony Ede profile, preserving other content and layout wrappers.

Events query pagination is implemented with the captured page variants embedded in inert templates and selected before Webflow initialises. The visible list, dates, record order, previous/next links and query strings are preserved. Static fallback pages also exist at `/events/page/2/` and `/events/page/3/` under the project prefix.

## Verification evidence

The [comparison index](evidence/visual-comparisons.md) links every actual full-page source and target screenshot and pixel result. Machine-readable results are in [evidence/local/results.json](evidence/local/results.json). Browser details, timestamps, viewport sizes, dimensions and differences are recorded there.

The matrix covers all nine route/state rows above at desktop 1440 × 1000, tablet 834 × 1112, and mobile 390 × 844. Each normal page also has a matched open-menu screenshot. Events pages 1–3 include hovered-event screenshots, and home/contact include focused subscription-field screenshots. The explicit page-1 alias is checked separately. The 404 has its default screen only.

**Initial local result: all 66 comparisons had identical pixels**, with matching full-page dimensions, zero recorded HTTP errors and zero browser JavaScript errors. Comparison uses every RGB channel with zero tolerance and no masks. Functional checks passed for 39 linked local URLs, all 49 original asset files, metadata on all five live pages, navigation, pagination/history, form interception and no-JavaScript fallbacks. A cached rebuild produced byte-for-byte identical publishable files. Current deployed evidence, including the two requested content differences, is indexed [here](evidence/deployed-2026-10-17/README.md).

Functional verification checks generated page and asset existence, GETs all linked local routes, opens the mobile menu, follows Events navigation, clicks next/previous through the archive, reloads a query page, and exercises browser history. It checks Mailchimp action/field/honeypot preservation and intercepts a contact submission locally. All browser tests block non-GET/HEAD requests. No real contact or subscription form was submitted. See [functional results](evidence/functional.json).

The first 66-comparison iteration had 63 exact matches. The remaining three states were the tablet last Events page: 57 different pixels (0.005011%) around two letters of “Previous.” Inspection established matching layout, dimensions and computed font settings, but Google Fonts had served TTF to the downloader and WOFF2 to Chromium. Matching the browser's WOFF2 assets addresses that difference. The complete first iteration, its diff images and asset manifest are retained at [evidence/iteration-1](evidence/iteration-1/results.json); the final matrix is recorded separately rather than silently replacing that evidence.

These results establish parity only in the recorded Chromium conditions. The deployed GitHub Pages origin has now been audited separately. Safari, Firefox, other screen sizes, real subscription delivery and animation timing between stable screenshots remain unverified.

## Differences and decisions

| Area | Status / difference | Supported next step |
| --- | --- | --- |
| Hosting origin and paths | Preview uses `antonyede.github.io/analytics-org-nz/`. Directory pages have trailing slashes; original route names and Events query parameter are retained beneath the prefix. | Review the default-domain preview. No DNS/custom-domain changes were made. |
| Contact delivery | The original Webflow form was initially disabled, then replaced at the owner's request with visible `mailto:hello@analytics.org.nz`. The newsletter remains separate. | Visitors use their own email application. Mailbox delivery was not tested and no email was sent. |
| Mailchimp | Existing HTTPS POST action, field names, new-tab target and bot honeypot retained on home/contact. Provider delivery remains an external dependency. | Owner can submit a controlled subscription after review; tests deliberately did not. |
| Analytics | Source first-party `/nvhc…` telemetry proxy is Webflow-hosted and cannot be served by Pages. Its scripts and tracking initialisation are omitted from the preview. | Decide whether and how to configure analytics for the new origin before a future production cutover. No tracking destination was invented. |
| CMS updates | Profiles remain static. Events have a prepared daily 06:17 UTC/manual API sync, blocked until the authorised Eventbrite token is configured. The original 25-event archive remains, with 0 API-synced events. | See the exact credential requirement and verified safe fallback in [Eventbrite setup](EVENT_SYNC.md). |
| JavaScript | Original navigation/animations already rely on JavaScript. Original query-based pagination now also needs JavaScript to select a static snapshot. Direct `/events/page/2/` and `/events/page/3/` pages, linked from a `noscript` notice, are available as fallbacks. | Keep scripting enabled for matched behaviour; use the direct archive links if needed. |
| Asset rights | Existing third-party material retained under the owner's migration authorisation; no blanket relicensing. | Review third-party font/image/logo/runtime terms for reuse outside this migration. See [provenance](ASSET_RIGHTS.md). |

Inherited source issues were preserved to honour the requested copy: the 2024 “Over Coming the Data Dilemma” event has a `#` destination; an unused hidden Events overlay contains placeholder `#` links and a template “Start A Project” mailto address; the privacy text still describes WordPress and plugins despite the current Webflow hosting. These are candidates for a separately approved content correction, not migration-induced visual differences. The help email used by the contact fallback comes from the live source privacy statement; inbox deliverability was not tested.

## Deployment history and current status

The initial attempt to enable Pages through the existing integration returned **HTTP 403**, **“Resource not accessible by integration.”** No credentials or broader permissions were created. At that initial handoff, the preview returned 404; that historical result is retained in [the initial blocker record](evidence/deployment-initial-blocker.json).

Pages is now enabled with `main:/docs`, HTTPS enforced and no custom domain. The original migration and both requested content changes have successful Pages builds. The [current deployment record](evidence/deployment.json) and [production audit](PRODUCTION_READINESS.md) supersede the initial setup blocker. Production readiness still depends on resolving the documented form, content and UX issues; deployment success does not prove message or subscription delivery.

The source Webflow site, its custom domain, and DNS have not been changed.
