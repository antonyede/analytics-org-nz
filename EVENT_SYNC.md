# Eventbrite sync

The contact page now uses a visible `mailto:hello@analytics.org.nz` link instead of the contact form. The separate Mailchimp newsletter embeds are unchanged. No emails or subscriptions were sent.

## Feed status at verification — 17 October 2026

**Authenticated sync is working.** [Run 39000586274](https://github.com/antonyede/analytics-org-nz/actions/runs/39000586274) successfully verified **23 public listed events** for organiser `18441294721` at **2026-10-17 03:55:13 UTC**: 0 upcoming and 23 past. **19 images** were retrieved and self-hosted; the other four events supplied no image. [Pages deployment 39000619137](https://github.com/antonyede/analytics-org-nz/actions/runs/39000619137) succeeded. The [live status](https://antonyede.github.io/analytics-org-nz/event-sync-status.json) is authoritative for later attempts and successes. The original manual archive is retained under `source/`, while the rendered Events page now uses the verified API dataset.

The required access is an existing authorised Eventbrite API OAuth/private token, stored in this repository's Actions secret **`EVENTBRITE_TOKEN`**. It must belong to an account authorised to read the organisation owning organiser **`18441294721`**. Do not paste the token into an issue, source file or chat. An optional repository Actions variable **`EVENTBRITE_ORGANIZATION_ID`** limits discovery to the owning organisation; it is an organisation ID, not the organiser profile ID. Without that variable the sync uses the documented `GET /users/me/organizations/` endpoint and filters organisation event requests to the specified organiser.

The user added the repository secret. It was used only inside the authorised GitHub Actions fetch step; its value was never retrieved by the assistant, printed, or committed. Automatic organisation discovery succeeded with `EVENTBRITE_ORGANIZATION_ID` empty. No replacement token, explicit organisation ID, new account or broader access was required.

## HTTP 400 diagnosis and fix

The first authenticated attempt failed on `GET /v3/users/me/organizations/?page=1&page_size=50`. Safe diagnostics from [run 39000484090](https://github.com/antonyede/analytics-org-nz/actions/runs/39000484090) identified `ARGUMENTS_ERROR`: `page_size - Unknown parameter`.

The shared pagination helper had added `page_size` to every endpoint. The official organisation-discovery endpoint does not accept it; the organisation-events endpoint explicitly documents it. Commit `d315824` moved the page-size parameter into event-list requests only. Discovery now sends `page` alone. Regression coverage simulates the real rejection if discovery receives `page_size` again and verifies that event-list requests still receive their supported page size.

The fix was rerun using the unchanged existing secret and succeeded. **20 unit tests pass**, including the pagination regression, credential-redacted error diagnostics, public filtering, complete pagination, failure retention, images, timezone handling and deletion protection. [Current live verification](evidence/event-sync/400-fix-live/README.md) checks every rendered event URL, UTC timestamp and image path across desktop/tablet/mobile, all 23 ticket-link responses, and all 19 hosted image hashes.

## Source and supported access

The [requested public profile](https://www.eventbrite.co.nz/o/nz-data-science-analytics-forum-18441294721) identifies **NZ Data Science + Analytics Forum** and links to `analytics.org.nz`. Its aggregate count was 25 during reconnaissance; that number is not substituted for the API's public-listed selection. The authenticated import verifies every API page and retains only explicitly listed, non-draft events from the exact organiser. The current 23-record feed is not padded with manual archive rows, unlisted events, or invented data.

Eventbrite's documented API supports paginated [organisation events](https://www.eventbrite.com/platform/new/api). Unauthenticated API requests return HTTP 401 `NO_AUTH`. The old organiser RSS path returned 404, and `/rss/` is disallowed in robots.txt. Eventbrite's [current terms, section 13](https://www.eventbrite.com/help/en-us/articles/251210/eventbrite-terms-of-service/) prohibit automated website extraction. The implementation therefore uses the official authenticated API, not a website scraper, browser-internal API, or a bypass of an access restriction.

## Prepared automation

The workflow is installed and active for **daily 06:17 UTC** execution and manual dispatch. Initial attempts safely retained the archive when the secret was absent and when request validation failed. After the endpoint-specific pagination fix, the real authenticated workflow completed successfully, committed the verified dataset and images in `b476b33`, and requested the successful Pages rebuild linked above.

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

The source Webflow site, DNS, custom domains and previous TRA/Antony removals are unchanged. Current live counts, links, dates, pagination and images have been verified; no emails, bookings, contact forms or subscriptions were sent.
