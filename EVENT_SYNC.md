# Eventbrite sync

The contact page now uses a visible `mailto:hello@analytics.org.nz` link instead of the contact form. The separate Mailchimp newsletter embeds are unchanged. No emails or subscriptions were sent.

## Current feed status

**No authenticated Eventbrite sync has succeeded yet.** There are **0 API-synchronised events**, no last-success timestamp, and the original **25 archived events** remain available. The Events page explicitly labels that archive and links to the organiser for the latest events. The machine-readable [sync status](docs/event-sync-status.json) records the latest attempt and exact failure code; the public page never presents that failed attempt as a successful update.

The required access is an existing authorised Eventbrite API OAuth/private token, stored in this repository's Actions secret **`EVENTBRITE_TOKEN`**. It must belong to an account authorised to read the organisation owning organiser **`18441294721`**. Do not paste the token into an issue, source file or chat. An optional repository Actions variable **`EVENTBRITE_ORGANIZATION_ID`** limits discovery to the owning organisation; it is an organisation ID, not the organiser profile ID. Without that variable the sync uses the documented `GET /users/me/organizations/` endpoint and filters organisation event requests to the specified organiser.

No Eventbrite credential is available to this cloud session. Listing repository secret names was denied by GitHub with HTTP 403, so secret presence must be confirmed by an actual workflow run or the owner in Settings → Secrets and variables → Actions. No credentials, accounts, permissions or paid services were created.

## Source and supported access

The [requested public profile](https://www.eventbrite.co.nz/o/nz-data-science-analytics-forum-18441294721) identifies **NZ Data Science + Analytics Forum**, links to `analytics.org.nz`, reports 25 events, and exposes a successful empty upcoming list. This verifies identity; it is not a complete authenticated event export. Public past-event pagination and individual images have not been fetched as a feed.

Eventbrite's documented API supports paginated [organisation events](https://www.eventbrite.com/platform/new/api). Unauthenticated API requests return HTTP 401 `NO_AUTH`. The old organiser RSS path returned 404, and `/rss/` is disallowed in robots.txt. Eventbrite's [current terms, section 13](https://www.eventbrite.com/help/en-us/articles/251210/eventbrite-terms-of-service/) prohibit automated website extraction. The implementation therefore uses the official authenticated API, not a website scraper, browser-internal API, or a bypass of an access restriction.

## Prepared automation

The workflow is designed for **daily 06:17 UTC** execution and manual dispatch. Its installation and execution status are recorded in [verification evidence](evidence/event-sync). The schedule is not evidence that authenticated retrieval has succeeded.

- Uses only the documented organisation-list and organisation-events GET endpoints. It requests all non-draft statuses, filters by the exact organiser, follows every reported page, verifies counts, and rejects duplicate/mismatched records. Only explicitly public (`listed=true`) events are persisted; unlisted events and drafts are excluded before their details are saved.
- Includes upcoming/in-progress events until their UTC end time, with upcoming sorted oldest-first and past events newest-first. Display dates use each event's IANA timezone, including New Zealand daylight saving. Past events paginate ten per page with the original query parameter and direct no-JavaScript archive pages. Cancelled events are labelled.
- Preserves actual Eventbrite ticket links and downloads verified images from the Eventbrite CDN, without forwarding API authentication. Image files are content-addressed. Missing optional images are omitted; failed/invalid image downloads abort the new snapshot.
- Retries transient API/network failures with backoff, honours bounded `Retry-After`, and does not retry authentication denial. HTTP responses and credentials are never dumped into diagnostics.
- Validates the complete new snapshot before replacing data. Empty, partial, malformed, wrong-organiser or failed image fetches leave the previous dataset byte-for-byte intact. A decrease of more than half a substantial feed is rejected unless manually reviewed using the dispatch input. Empty feeds remain rejected even with that override.
- Writes public, sanitised freshness/failure diagnostics. When no API snapshot exists, the migration archive stays in place with an honest warning. Once a snapshot exists, a failure retains it and displays its last verified timestamp. Browser-side freshness text warns after 36 hours even if a workflow stops publishing.
- Grants the workflow only repository `contents:write` (generated data/status commits) and `pages:write` (explicit Pages rebuild). There is no push or pull-request trigger, so its commits cannot recursively invoke the sync. API credentials are exposed only to the fetch step. A non-force push is refused if another writer advanced `main` during the run.

The explicit Pages rebuild is necessary because commits made using `GITHUB_TOKEN` do not themselves trigger a legacy Pages build. This follows [GitHub's Pages publishing guidance](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site).

## Reproduce

```sh
python -m pip install -r requirements-sync.txt
python -m unittest discover -s tests -v
python scripts/sync_events.py
python scripts/build.py --events-only
```

Provide an existing authorised token through `EVENTBRITE_TOKEN`, not a command argument. If it is absent, the expected result is exit 2 and `credentials_missing`, with no new `data/events.json` and no loss of the migration archive. Tests use synthetic fixtures only inside temporary directories and never publish those events. They cover pagination completeness, privacy/scope filtering, empty/partial/image failure retention, retry behaviour, large count changes, timezones, rendering and escaping.

The source Webflow site, DNS, custom domains and previous TRA/Antony removals are unchanged. Real API event counts, images and a successful authenticated workflow cannot be verified until the required Eventbrite access is available.
