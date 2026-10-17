"""Browser verification of the contact/email and event sync states; never submits."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from events_view import split_events

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--target',default='https://antonyede.github.io/analytics-org-nz')
    parser.add_argument('--output',default='evidence/event-sync/live')
    args=parser.parse_args()
    folder=ROOT/args.output;folder.mkdir(parents=True,exist_ok=True)
    data=json.loads((ROOT/'data/events.json').read_text()) if (ROOT/'data/events.json').exists() else None
    upcoming,past=split_events(data['events']) if data else ([],[None]*25)
    status=json.loads((ROOT/'data/event-sync-status.json').read_text())
    report={'target':args.target,'last_successful_sync':status.get('last_successful_sync'),'api_count':len(data['events']) if data else 0,
            'retained_archive_count':25 if not data else 0,'screenshots':[],'errors':[],'submissions':[]}
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for label,width,height in [('desktop',1440,1000),('tablet',834,1112),('mobile',390,844)]:
            context=browser.new_context(ignore_https_errors=True,viewport={'width':width,'height':height})
            def guard(route):
                if route.request.method not in ('GET','HEAD'):
                    report['submissions'].append(route.request.method);route.abort()
                else:route.continue_()
            context.route('**/*',guard)
            page=context.new_page()
            page.on('pageerror',lambda error:report['errors'].append(str(error)))
            for name,route in [('contact','/contact/'),('events','/events/'),('events-page-2','/events/?522c7db6_page=2'),('events-page-3','/events/?522c7db6_page=3'),('about','/about/')]:
                response=page.goto(args.target.rstrip('/')+route,wait_until='networkidle')
                assert response.status==200,(route,response.status)
                page.evaluate('document.fonts.ready')
                page.evaluate('''async () => {
                  for(let y=0;y<document.documentElement.scrollHeight;y+=700){scrollTo(0,y);await new Promise(r=>setTimeout(r,60));}
                  await Promise.all([...document.images].map(i=>i.decode().catch(()=>{})));scrollTo(0,0);
                }''')
                assert page.locator('.section.footer a[href="https://tra.co.nz/"]').count()==0
                if name=='contact':
                    assert page.locator('#email-form').count()==0
                    assert page.locator('a[href="mailto:hello@analytics.org.nz"]').is_visible()
                    assert page.locator('#mc-embedded-subscribe-form').count()==1
                elif name=='about':
                    assert 'Antony Ede' not in page.locator('main').inner_text()
                    assert page.locator('.w-dyn-item h3.name').count()==9
                else:
                    number=1 if name=='events' else int(name[-1])
                    page_count=max(1,(len(past)+9)//10)
                    actual=min(number,page_count)
                    expected=min(10,max(0,len(past)-(actual-1)*10))
                    assert page.locator('main .collection-list-wrapper-2 .w-dyn-item').count()==expected
                    assert page.locator('.event-sync-note').is_visible()
                    assert page.locator('.event-sync-note a').get_attribute('href').endswith('18441294721')
                    if not data:assert 'not connected' in page.locator('.event-sync-note').inner_text()
                broken=page.locator('img').evaluate_all('(xs)=>xs.filter(x=>x.getClientRects().length && (!x.complete || !x.naturalWidth)).map(x=>x.src)')
                assert not broken,broken
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),route
                filename=f'{label}-{name}.png'
                page.screenshot(path=str(folder/filename),full_page=True)
                report['screenshots'].append({'route':route,'viewport':[width,height],'file':filename})
            context.close()
        browser.close()
    assert not report['errors'] and not report['submissions'],report
    (folder/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'screenshots':len(report['screenshots']),'api_count':report['api_count'],'last_successful_sync':report['last_successful_sync'],'errors':report['errors'],'submissions':report['submissions']}))


if __name__=='__main__':main()
