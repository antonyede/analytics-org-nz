"""Render verified API data, or label the preserved migration archive honestly."""
import copy
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from sync_events import ORGANIZER_ID, ORGANIZER_URL, parse_utc

ROOT = Path(__file__).resolve().parents[1]
EVENTS_URL = 'https://analytics.org.nz/events'


def split_events(events, now=None):
    now = now or datetime.now(timezone.utc)
    upcoming = [e for e in events if parse_utc(e['end_utc']) > now]
    past = [e for e in events if parse_utc(e['end_utc']) <= now]
    return sorted(upcoming, key=lambda e:e['start_utc']), sorted(past, key=lambda e:e['start_utc'], reverse=True)


def note(soup, status, dataset, base):
    main = soup.select_one('main')
    current = main.select_one('.collection-list-wrapper')
    paragraph = soup.new_tag('p', attrs={'class':'event-sync-note', 'role':'status'})
    last = (dataset or {}).get('synced_at')
    paragraph['data-last-sync'] = last or ''
    paragraph['data-sync-result'] = status.get('result','blocked')
    if not last:
        message = 'Automatic event updates are not connected yet. Showing the preserved event archive. '
    elif status.get('result') != 'success':
        message = 'The latest event update failed. Showing events last verified on ' + last + '. '
    else:
        message = 'Events last verified on ' + last + '. Updated daily. '
    paragraph.append(message)
    link = soup.new_tag('a', href=ORGANIZER_URL, target='_blank', rel='noopener')
    link.string = 'View the latest on Eventbrite'
    paragraph.append(link)
    # Before the Current Events heading, inside its existing content column.
    heading = current.find_previous_sibling()
    (heading if heading else current).insert_before(paragraph)
    if not last:
        empty = current.select_one('.w-dyn-empty')
        if empty:
            empty.clear()
            link = soup.new_tag('a', href=ORGANIZER_URL, target='_blank', rel='noopener', attrs={'class':'text-block-19'})
            link.string = 'Check Eventbrite for upcoming events'
            empty.append(link)
    stylesheet = soup.new_tag('link', rel='stylesheet', href=base+'/events-sync.css')
    soup.head.append(stylesheet)
    soup.body.append(soup.new_tag('script', src=base+'/events-sync.js'))


def card(template, event, soup, base):
    row = copy.deepcopy(template)
    link = row.select_one('a')
    link['href'] = event['url']
    link['rel'] = 'noopener'
    for selector, value in [('.event-name',event['name']),('.event-price','Free' if event['is_free'] else 'See Eventbrite'),
                            ('.paragraph-7', 'Online' if event['online_event'] else event['city']),
                            ('.event-location','Online event' if event['online_event'] else event['venue'])]:
        node = row.select_one(selector)
        node.clear()
        node.append(value)
        classes = [x for x in node.get('class',[]) if x != 'w-dyn-bind-empty']
        if not value:
            classes.append('w-dyn-bind-empty')
        node['class'] = classes
    date = parse_utc(event['start_utc']).astimezone(ZoneInfo(event['timezone']))
    node = row.select_one('.event-date')
    node.clear()
    time = soup.new_tag('time', datetime=event['start_utc'], title=date.isoformat()+' ('+event['timezone']+')')
    time.string = date.strftime('%B') + ' ' + str(date.day) + ', ' + str(date.year)
    node.append(time)
    if event['status'] == 'canceled':
        label = soup.new_tag('span', attrs={'class':'event-cancelled'})
        label.string = ' — Cancelled'
        row.select_one('.event-name').append(label)
    if event.get('image_path'):
        wrapper = soup.new_tag('div', attrs={'class':'event-item-content'})
        image = soup.new_tag('img', src=base+'/'+event['image_path'], alt='', loading='lazy', attrs={'class':'event-thumbnail'})
        grid = row.select_one('.grid').extract()
        wrapper.append(image)
        wrapper.append(grid)
        link.append(wrapper)
    return row


def listing(container, events, template, soup, base, empty_text):
    container.clear()
    if not events:
        empty = soup.new_tag('div', attrs={'class':'empty-state w-dyn-empty'})
        text = soup.new_tag('div', attrs={'class':'text-block-19'})
        text.string = empty_text
        empty.append(text)
        container.append(empty)
    else:
        items = soup.new_tag('div', role='list', attrs={'class':'w-dyn-items'})
        for event in events:
            items.append(card(template,event,soup,base))
        container.append(items)
    pagination = soup.new_tag('div', role='navigation', attrs={'class':'w-pagination-wrapper','aria-label':'List'})
    container.append(pagination)
    return pagination


def prepare_event_pages(pages, base, root=ROOT):
    root = Path(root)
    status_file, dataset_file = root/'data/event-sync-status.json', root/'data/events.json'
    if not status_file.exists():
        return {n: pages[EVENTS_URL + (f'?522c7db6_page={n}' if n > 1 else '')] for n in (1,2,3)}
    status = json.loads(status_file.read_text())
    dataset = json.loads(dataset_file.read_text()) if dataset_file.exists() else None
    variants = {}
    if dataset:
        if dataset.get('source') != 'eventbrite_api' or dataset.get('organizer_id') != ORGANIZER_ID or not dataset.get('events') or dataset.get('public_event_count') != len(dataset['events']):
            raise ValueError('Refused inconsistent saved Eventbrite data')
        upcoming, past = split_events(dataset['events'])
        count = max(1, math.ceil(len(past)/10))
        template = pages[EVENTS_URL].select_one('main .collection-list-wrapper-2 .w-dyn-item')
        buttons = {css: pages[EVENTS_URL+'?522c7db6_page=2'].select_one('.w-pagination-'+css) for css in ('previous','next')}
        for number in range(1,max(3,count)+1):
            actual = min(number,count)
            soup = copy.deepcopy(pages[EVENTS_URL])
            main = soup.select_one('main')
            listing(main.select_one('.collection-list-wrapper'),upcoming,template,soup,base,'No events at present')
            pagination = listing(main.select_one('.collection-list-wrapper-2'),past[(actual-1)*10:actual*10],template,soup,base,'No past events at present')
            for label,target,css in [('Previous',actual-1,'previous'),('Next',actual+1,'next')]:
                if 1 <= target <= count:
                    anchor = copy.deepcopy(buttons[css])
                    anchor['href'] = base+f'/events/?522c7db6_page={target}'
                    pagination.append(anchor)
            variants[number] = soup
    else:
        variants = {n: pages[EVENTS_URL + (f'?522c7db6_page={n}' if n > 1 else '')] for n in (1,2,3)}
    for number,soup in variants.items():
        if dataset:
            fallback = soup.select_one('main noscript')
            if not fallback:
                fallback = soup.new_tag('noscript')
                soup.select_one('main').append(fallback)
            fallback.clear()
            for target in range(1,count+1):
                link = soup.new_tag('a',href=base+('/events/' if target == 1 else f'/events/page/{target}/'))
                link.string = f'Events page {target}'
                fallback.append(link)
                fallback.append(' ')
        note(soup,status,dataset,base)
        pages[EVENTS_URL + (f'?522c7db6_page={number}' if number > 1 else '')] = soup
    output = root/'docs/event-sync-status.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(status,indent=2)+'\n')
    return variants
