"""Sync public organiser events through Eventbrite's documented authenticated API.

No website scraping, attendee endpoints, response dumps, or credentials in files.
Failed/partial/empty fetches never replace the last successful event dataset.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zoneinfo import ZoneInfo

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ORGANIZER_ID = '18441294721'
ORGANIZER_URL = 'https://www.eventbrite.co.nz/o/nz-data-science-analytics-forum-18441294721'
API_ROOT = 'https://www.eventbriteapi.com/v3'
PUBLIC_STATUSES = {'live', 'started', 'ended', 'completed', 'canceled'}
IMAGE_HOSTS = {'img.evbuc.com', 'cdn.evbuc.com'}
USER_AGENT = 'AnalyticsForumEventSync/1.0 (+https://github.com/antonyede/analytics-org-nz)'


class SyncError(Exception):
    def __init__(self, code, message, blocked=False):
        self.code, self.message, self.blocked = code, message, blocked
        super().__init__(message)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None  # Never forward an Authorization header to another origin.


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '.new')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


def load_json(path, default):
    return json.loads(path.read_text()) if path.exists() else default


class API:
    def __init__(self, token, sleep=time.sleep):
        self.token, self.sleep = token, sleep
        self.opener = build_opener(NoRedirect())
        self.retries = 0

    def get(self, path, parameters=None):
        if not re.fullmatch(r'/users/me/organizations/|/organizations/\d+/events/', path):
            raise SyncError('invalid_api_path', 'Refused an unsupported API path.')
        url = API_ROOT + path + ('?' + urlencode(parameters) if parameters else '')
        for attempt in range(3):
            try:
                request = Request(url, headers={'Authorization': 'Bearer ' + self.token,
                                               'User-Agent': USER_AGENT, 'Accept': 'application/json'})
                with self.opener.open(request, timeout=30) as response:
                    data = response.read(4_000_001)
                    if len(data) > 4_000_000:
                        raise SyncError('response_too_large', 'Eventbrite API response exceeded the safety limit.')
                    return json.loads(data)
            except HTTPError as error:
                status = error.code
                if status in (401, 403):
                    raise SyncError('api_http_' + str(status), 'Eventbrite API access was denied. Check the token and organisation access.', True) from None
                if status not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise SyncError('api_http_' + str(status), 'Eventbrite API returned HTTP ' + str(status) + '; previous events retained.') from None
                retry_after = error.headers.get('Retry-After', '')
                delay = min(60, max(2, int(retry_after))) if retry_after.isdigit() else (2, 8)[attempt]
            except (URLError, TimeoutError, OSError):
                if attempt == 2:
                    raise SyncError('api_network', 'Eventbrite API could not be reached; previous events retained.') from None
                delay = (2, 8)[attempt]
            except (ValueError, UnicodeDecodeError):
                raise SyncError('api_invalid_json', 'Eventbrite did not return valid JSON; previous events retained.') from None
            self.retries += 1
            self.sleep(delay)


def paginated(api, path, key, parameters=None):
    records, expected, seen = [], None, set()
    for page in range(1, 101):
        result = api.get(path, {**(parameters or {}), 'page': page, 'page_size': 50})
        pagination, items = result.get('pagination'), result.get(key)
        if not isinstance(pagination, dict) or not isinstance(items, list):
            raise SyncError('pagination_invalid', 'Eventbrite pagination metadata or records are missing.')
        total, number, count = pagination.get('object_count'), pagination.get('page_number'), pagination.get('page_count')
        if not all(isinstance(x, int) and not isinstance(x, bool) for x in (total, number, count)) or total < 0 or count < 0 or number != page:
            raise SyncError('pagination_invalid', 'Eventbrite pagination metadata is inconsistent.')
        if expected is None:
            expected = total
        if total != expected or count > 100 or not items and page < count:
            raise SyncError('pagination_changed', 'Eventbrite pagination changed or was incomplete; retry the full sync.')
        for item in items:
            if not isinstance(item, dict) or not re.fullmatch(r'\d+', str(item.get('id', ''))):
                raise SyncError('record_invalid', 'Eventbrite returned a record without a valid ID.')
            if str(item['id']) in seen:
                raise SyncError('pagination_duplicate', 'An Eventbrite record appeared on more than one page.')
            seen.add(str(item['id']))
            records.append(item)
        if page >= max(1, count):
            if len(records) != expected or pagination.get('has_more_items') is True:
                raise SyncError('pagination_incomplete', 'Eventbrite record count did not match its complete pagination.')
            return records
    raise SyncError('pagination_limit', 'Eventbrite exceeded the bounded pagination limit.')


def parse_utc(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is None:
            raise ValueError()
        return result.astimezone(timezone.utc)
    except (AttributeError, ValueError, TypeError):
        raise SyncError('invalid_datetime', 'A public event has an invalid timezone-aware timestamp.') from None


def normalize(event):
    name = event.get('name', {}).get('text') if isinstance(event.get('name'), dict) else None
    url = event.get('url', '')
    parts = urlsplit(url)
    if not isinstance(name, str) or not name.strip() or len(name) > 1000:
        raise SyncError('invalid_name', 'A public event has no valid title.')
    if parts.scheme != 'https' or parts.username or parts.password or parts.port not in (None,443) or parts.hostname not in {'www.eventbrite.com', 'www.eventbrite.co.nz', 'www.eventbrite.com.au'} or not parts.path.startswith('/e/'):
        raise SyncError('invalid_event_url', 'A public event has an unexpected ticket URL.')
    start, end = event.get('start', {}), event.get('end', {})
    first, last = parse_utc(start.get('utc')), parse_utc(end.get('utc'))
    try:
        zone = ZoneInfo(start['timezone'])
    except (KeyError, ValueError):
        raise SyncError('invalid_timezone', 'A public event has no recognised timezone.') from None
    if last < first or not isinstance(event.get('is_free'), bool) or not isinstance(event.get('online_event'), bool):
        raise SyncError('invalid_event_fields', 'A public event has inconsistent dates, pricing or online status.')
    venue = event.get('venue') or {}
    address = venue.get('address') or {}
    logo = event.get('logo') or {}
    image_url = (logo.get('original') or {}).get('url') or logo.get('url')
    if image_url:
        image = urlsplit(image_url)
        if image.scheme != 'https' or image.hostname not in IMAGE_HOSTS:
            raise SyncError('invalid_image_url', 'A public event has an image outside the supported Eventbrite CDN hosts.')
    return {'id': str(event['id']), 'organizer_id': ORGANIZER_ID, 'name': name.strip(), 'url': url,
            'start_utc': first.isoformat().replace('+00:00', 'Z'), 'end_utc': last.isoformat().replace('+00:00', 'Z'),
            'timezone': start['timezone'], 'start_local': first.astimezone(zone).isoformat(),
            'status': event['status'], 'is_free': event['is_free'], 'online_event': event['online_event'],
            'venue': str(venue.get('name') or '')[:500], 'city': str(address.get('city') or address.get('region') or '')[:300],
            'image_source_url': image_url, 'image_path': None}


def fetch_events(api, organization_id=None):
    if organization_id:
        if not re.fullmatch(r'\d+', organization_id):
            raise SyncError('invalid_organization_id', 'EVENTBRITE_ORGANIZATION_ID must be a numeric organisation ID.', True)
        organizations = [{'id': organization_id}]
    else:
        organizations = paginated(api, '/users/me/organizations/', 'organizations')
    if not organizations or len(organizations) > 30:
        raise SyncError('organization_access', 'Provide access to the owning Eventbrite organisation, or set EVENTBRITE_ORGANIZATION_ID.', True)
    events, ids, source_count = [], set(), 0
    for organization in organizations:
        records = paginated(api, '/organizations/' + str(organization['id']) + '/events/', 'events', {
            'organizer_filter': ORGANIZER_ID, 'status': 'live,started,ended,completed,canceled',
            'show_series_parent': 'false', 'order_by': 'start_asc', 'expand': 'venue,logo'})
        source_count += len(records)
        for event in records:
            if str(event.get('organizer_id')) != ORGANIZER_ID:
                raise SyncError('organizer_mismatch', 'Eventbrite ignored the organiser filter; no data was published.')
            if not isinstance(event.get('listed'), bool):
                raise SyncError('visibility_unknown', 'Eventbrite did not provide an explicit public-listing flag.')
            if not event['listed'] or event.get('status') not in PUBLIC_STATUSES:
                continue  # Never persist drafts or unlisted/private event content.
            record = normalize(event)
            if record['id'] in ids:
                raise SyncError('duplicate_event', 'The same public event appeared in multiple organisations.')
            ids.add(record['id'])
            events.append(record)
    if not events:
        raise SyncError('empty_public_feed', 'No verified public events were returned; existing events retained. Check organisation access and organiser scope.')
    return sorted(events, key=lambda item: (item['start_utc'], item['id'])), source_count


def download_image(record, previous, root, staging):
    url = record['image_source_url']
    if not url:
        return
    if previous and previous.get('image_source_url') == url and re.fullmatch(r'assets/eventbrite/\d+-[0-9a-f]{12}\.(jpg|png|webp|gif)', previous.get('image_path') or ''):
        cached = root / 'docs' / previous['image_path']
        if cached.is_file() and hashlib.sha256(cached.read_bytes()).hexdigest() == previous.get('image_sha256'):
            record.update({key: previous[key] for key in ('image_path', 'image_sha256')})
            return
    try:
        with build_opener(NoRedirect()).open(Request(url, headers={'User-Agent': USER_AGENT}), timeout=30) as response:
            data = response.read(5_000_001)
        if len(data) > 5_000_000:
            raise ValueError()
        with Image.open(BytesIO(data)) as image:
            image.verify()
            extension = {'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp', 'GIF': 'gif'}[image.format]
    except Exception:
        raise SyncError('image_fetch_failed', 'An event image could not be safely retrieved; previous event data and images retained.') from None
    digest = hashlib.sha256(data).hexdigest()
    path = 'assets/eventbrite/' + record['id'] + '-' + digest[:12] + '.' + extension
    (staging / Path(path).name).write_bytes(data)
    record.update({'image_path': path, 'image_sha256': digest})


def run(root=ROOT, token=None, organization_id=None, allow_large_decrease=False, api=None, image_loader=download_image):
    root = Path(root)
    dataset_path, status_path = root / 'data/events.json', root / 'data/event-sync-status.json'
    previous = load_json(dataset_path, {})
    attempted = utc_now()
    status = {'schema_version': 1, 'organizer_id': ORGANIZER_ID, 'organizer_url': ORGANIZER_URL,
              'last_attempt_at': attempted, 'last_successful_sync': previous.get('synced_at'),
              'retained_synced_event_count': len(previous.get('events', []))}
    try:
        if not token and api is None:
            raise SyncError('credentials_missing', 'Eventbrite API access is not configured. Add repository Actions secret EVENTBRITE_TOKEN for an authorised existing Eventbrite account.', True)
        api = api or API(token)
        events, source_count = fetch_events(api, organization_id)
        old = previous.get('events', [])
        if len(old) >= 10 and len(events) < len(old) / 2 and not allow_large_decrease:
            raise SyncError('large_count_decrease', 'Public event count dropped by more than half; retained previous data pending explicit review.')
        old_by_id = {item['id']: item for item in old}
        with tempfile.TemporaryDirectory(prefix='analytics-event-images-') as temporary:
            staging = Path(temporary)
            for record in events:
                image_loader(record, old_by_id.get(record['id']), root, staging)
            # Publish new immutable image files only after all data/images validate.
            for file in staging.iterdir():
                destination = root / 'docs/assets/eventbrite' / file.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(file.read_bytes())
        synced_at = utc_now()
        atomic_json(dataset_path, {'schema_version': 1, 'source': 'eventbrite_api', 'organizer_id': ORGANIZER_ID,
                                  'organizer_url': ORGANIZER_URL, 'synced_at': synced_at,
                                  'public_event_count': len(events), 'events': events})
        status.update({'result': 'success', 'code': 'ok', 'message': 'All pages of public organiser events were verified.',
                       'last_successful_sync': synced_at, 'retained_synced_event_count': len(events),
                       'api_records_examined': source_count, 'retries': getattr(api, 'retries', 0)})
        exit_code = 0
    except SyncError as error:
        status.update({'result': 'blocked' if error.blocked else 'error', 'code': error.code, 'message': error.message})
        exit_code = 2 if error.blocked else 1
    except Exception:
        status.update({'result': 'error', 'code': 'unexpected_error', 'message': 'Sync stopped unexpectedly; existing event data was not intentionally replaced.'})
        exit_code = 1
    atomic_json(status_path, status)
    return status, exit_code


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--allow-large-decrease', action='store_true')
    args = parser.parse_args()
    status, exit_code = run(token=os.environ.get('EVENTBRITE_TOKEN'), organization_id=os.environ.get('EVENTBRITE_ORGANIZATION_ID') or None,
                            allow_large_decrease=args.allow_large_decrease)
    print(json.dumps(status, indent=2))  # Whitelisted diagnostics only, never API response bodies.
    raise SystemExit(exit_code)


if __name__ == '__main__':
    main()
