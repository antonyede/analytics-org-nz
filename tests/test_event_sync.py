import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from io import BytesIO

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from sync_events import API, ORGANIZER_ID, SyncError, download_image, fetch_events, paginated, run
from PIL import Image
from events_view import prepare_event_pages, split_events
from bs4 import BeautifulSoup


def event(identifier=1, **overrides):
    result = {'id':str(identifier),'organizer_id':ORGANIZER_ID,'listed':True,'status':'ended',
              'name':{'text':'Fixture event '+str(identifier)},'url':'https://www.eventbrite.co.nz/e/fixture-'+str(identifier),
              'start':{'utc':'2026-09-10T05:00:00Z','timezone':'Pacific/Auckland'},
              'end':{'utc':'2026-09-10T07:00:00Z','timezone':'Pacific/Auckland'},
              'is_free':True,'online_event':False,'venue':{'name':'Fixture venue','address':{'city':'Wellington'}},'logo':None}
    result.update(overrides)
    return result


class FakeAPI:
    retries = 0
    def __init__(self, rows, size=2, broken=False):
        self.rows,self.size,self.broken,self.calls=rows,size,broken,[]
    def get(self,path,parameters):
        self.calls.append((path,parameters))
        page=parameters['page']
        rows=self.rows[(page-1)*self.size:page*self.size]
        count=max(1,(len(self.rows)+self.size-1)//self.size)
        return {'pagination':{'object_count':len(self.rows)+(1 if self.broken else 0),'page_number':page,'page_count':count,'has_more_items':page<count},
                'events':copy.deepcopy(rows)}


class SyncTests(unittest.TestCase):
    def test_api_validation_diagnostic_identifies_request_without_secret(self):
        secret='fixture-sensitive-token-never-log'
        body=json.dumps({'error':'ARGUMENTS_ERROR','error_description':'Invalid page_size; Authorization Bearer '+secret+'; token='+secret}).encode()
        api=API(secret)
        api.opener.open=Mock(side_effect=HTTPError('https://www.eventbriteapi.com',400,'bad request',{},BytesIO(body)))
        with self.assertRaises(SyncError):api.get('/users/me/organizations/',{'page':1,'page_size':50,'token':secret})
        detail=api.last_error
        self.assertEqual(detail['path'],'/users/me/organizations/')
        self.assertEqual(detail['api_error'],'ARGUMENTS_ERROR')
        self.assertEqual(detail['parameters'],{'page':'1','page_size':'50'})
        self.assertNotIn(secret,json.dumps(detail))
        self.assertIn('[REDACTED]',detail['description'])

    def test_image_bytes_are_verified_and_auth_is_not_forwarded(self):
        body=BytesIO();Image.new('RGB',(8,8),'white').save(body,format='JPEG')
        record={'id':'1','image_source_url':'https://cdn.evbuc.com/fixture.jpg'}
        opener=Mock();opener.open.return_value=BytesIO(body.getvalue())
        with tempfile.TemporaryDirectory() as temporary,patch('sync_events.build_opener',return_value=opener):
            root=Path(temporary);staging=root/'staging';staging.mkdir()
            download_image(record,None,root,staging)
            self.assertEqual(len(list(staging.iterdir())),1)
            self.assertTrue(record['image_path'].endswith('.jpg'))
            self.assertIsNone(opener.open.call_args.args[0].get_header('Authorization'))

    def test_non_image_download_is_rejected(self):
        record={'id':'1','image_source_url':'https://cdn.evbuc.com/fixture.jpg'}
        opener=Mock();opener.open.return_value=BytesIO(b'<html>not an image</html>')
        with tempfile.TemporaryDirectory() as temporary,patch('sync_events.build_opener',return_value=opener):
            root=Path(temporary)
            with self.assertRaises(SyncError):download_image(record,None,root,root)
            self.assertEqual(list(root.iterdir()),[])

    def test_retries_back_off_and_do_not_retry_auth_errors(self):
        sleeps=[]
        api=API('fixture-not-a-real-token',sleep=sleeps.append)
        response=BytesIO(b'{"ok":true}')
        api.opener.open=Mock(side_effect=[HTTPError('https://www.eventbriteapi.com',503,'unavailable',{},None),HTTPError('https://www.eventbriteapi.com',429,'limited',{'Retry-After':'120'},None),response])
        self.assertTrue(api.get('/users/me/organizations/')['ok'])
        self.assertEqual(sleeps,[2,60])
        api=API('fixture-not-a-real-token',sleep=sleeps.append)
        api.opener.open=Mock(side_effect=HTTPError('https://www.eventbriteapi.com',401,'unauthorised',{},None))
        with self.assertRaises(SyncError) as error:api.get('/users/me/organizations/')
        self.assertTrue(error.exception.blocked)
        self.assertEqual(api.opener.open.call_count,1)
        self.assertNotIn('fixture-not-a-real-token',str(error.exception))

    def test_complete_pagination_and_scope(self):
        api=FakeAPI([event(n) for n in range(1,6)])
        rows,total=fetch_events(api,'123')
        self.assertEqual((len(rows),total),(5,5))
        self.assertEqual([c[1]['page'] for c in api.calls],[1,2,3])
        self.assertTrue(all(c[1]['organizer_filter']==ORGANIZER_ID for c in api.calls))
        self.assertTrue(all('past' not in c[1].get('time_filter','') for c in api.calls))

    def test_organization_discovery_uses_documented_me_endpoint(self):
        class Discovery(FakeAPI):
            def get(self,path,parameters):
                if path=='/users/me/organizations/':
                    if 'page_size' in parameters:
                        raise SyncError('api_http_400','page_size - Unknown parameter')
                    self.calls.append((path,parameters))
                    return {'pagination':{'object_count':1,'page_number':1,'page_count':1,'has_more_items':False},'organizations':[{'id':'123'}]}
                return super().get(path,parameters)
        api=Discovery([event()])
        rows,_=fetch_events(api)
        self.assertEqual(len(rows),1)
        self.assertEqual(api.calls[0][0],'/users/me/organizations/')
        self.assertEqual(api.calls[0][1],{'page':1})
        self.assertEqual(api.calls[1][0],'/organizations/123/events/')
        self.assertEqual(api.calls[1][1]['page_size'],50)

    def test_incomplete_pagination_is_rejected(self):
        with self.assertRaises(SyncError):
            fetch_events(FakeAPI([event()],broken=True),'123')

    def test_duplicate_page_records_are_rejected(self):
        with self.assertRaises(SyncError):
            fetch_events(FakeAPI([event(),event()]),'123')

    def test_wrong_organizer_is_rejected(self):
        with self.assertRaises(SyncError):
            fetch_events(FakeAPI([event(organizer_id='999')]),'123')

    def test_drafts_and_unlisted_never_persist(self):
        rows,_=fetch_events(FakeAPI([event(1),event(2,listed=False),event(3,status='draft')]),'123')
        self.assertEqual([r['id'] for r in rows],['1'])

    def test_empty_response_cannot_erase_data(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'data').mkdir();original=b'{"events":[{"id":"old"}],"synced_at":"2026-01-01T00:00:00Z"}\n'
            (root/'data/events.json').write_bytes(original)
            status,code=run(root,api=FakeAPI([]),organization_id='123')
            self.assertEqual(code,1)
            self.assertEqual((root/'data/events.json').read_bytes(),original)
            self.assertEqual(status['code'],'empty_public_feed')

    def test_missing_credentials_do_not_create_empty_dataset(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            status,code=run(root)
            self.assertEqual((code,status['result']),(2,'blocked'))
            self.assertFalse((root/'data/events.json').exists())
            self.assertIsNone(status['last_successful_sync'])

    def test_partial_fetch_preserves_exact_old_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'data').mkdir();original=b'{"events":[{"id":"old"}]}\n'
            (root/'data/events.json').write_bytes(original)
            _,code=run(root,api=FakeAPI([event()],broken=True),organization_id='123')
            self.assertEqual(code,1)
            self.assertEqual((root/'data/events.json').read_bytes(),original)

    def test_image_failure_preserves_old_dataset(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'data').mkdir();original=b'{"events":[{"id":"old"}]}\n'
            (root/'data/events.json').write_bytes(original)
            def fail(*args):raise SyncError('image_fetch_failed','Fixture failure')
            _,code=run(root,api=FakeAPI([event()]),organization_id='123',image_loader=fail)
            self.assertEqual(code,1)
            self.assertEqual((root/'data/events.json').read_bytes(),original)

    def test_large_decrease_requires_explicit_override(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'data').mkdir()
            (root/'data/events.json').write_text(json.dumps({'events':[{'id':str(n)} for n in range(20)]}))
            status,code=run(root,api=FakeAPI([event()]),organization_id='123')
            self.assertEqual((code,status['code']),(1,'large_count_decrease'))

    def test_success_stores_only_whitelisted_public_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            raw=event();raw['private_note']='MUST_NOT_PERSIST'
            status,code=run(root,api=FakeAPI([raw]),organization_id='123')
            self.assertEqual((code,status['result']),(0,'success'))
            text=(root/'data/events.json').read_text()
            self.assertNotIn('MUST_NOT_PERSIST',text)
            self.assertIn('2026-09-10T17:00:00+12:00',text)

    def test_new_zealand_daylight_saving_and_date_rollover(self):
        raw=event(start={'utc':'2026-10-17T12:00:00Z','timezone':'Pacific/Auckland'},end={'utc':'2026-10-17T14:00:00Z','timezone':'Pacific/Auckland'})
        rows,_=fetch_events(FakeAPI([raw]),'123')
        self.assertEqual(rows[0]['start_local'],'2026-10-18T01:00:00+13:00')

    def test_upcoming_boundary_and_sorting(self):
        rows,_=fetch_events(FakeAPI([event(1),event(2,end={'utc':'2026-09-11T07:00:00Z','timezone':'Pacific/Auckland'})]),'123')
        upcoming,past=split_events(rows,datetime(2026,9,10,7,tzinfo=timezone.utc))
        self.assertEqual([r['id'] for r in upcoming],['2'])
        self.assertEqual([r['id'] for r in past],['1'])

    def test_unsafe_url_and_invalid_dates_rejected(self):
        for raw in [event(url='https://example.invalid/e/1'),event(end={'utc':'2020-01-01T00:00:00Z'}),event(start={'utc':'not-a-date','timezone':'Pacific/Auckland'})]:
            with self.subTest(raw=raw['id']),self.assertRaises(SyncError):fetch_events(FakeAPI([raw]),'123')

    def test_renderer_pages_dates_images_and_html_escaping(self):
        manifest=json.loads((ROOT/'source/routes.json').read_text())
        pages={r['url']:BeautifulSoup((ROOT/'source'/r['file']).read_text(),'html.parser') for r in manifest['routes'] if r['title']}
        rows,_=fetch_events(FakeAPI([event(n) for n in range(1,36)]),'123')
        rows[0]['name']='<script>not executable</script>'
        rows[0]['image_path']='assets/eventbrite/fixture.jpg'
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);(root/'data').mkdir()
            (root/'data/event-sync-status.json').write_text(json.dumps({'result':'success'}))
            (root/'data/events.json').write_text(json.dumps({'source':'eventbrite_api','organizer_id':ORGANIZER_ID,'public_event_count':35,'synced_at':'2026-10-17T00:00:00Z','events':rows}))
            variants=prepare_event_pages(pages,'/analytics-org-nz',root)
            self.assertEqual([len(variants[n].select('.collection-list-wrapper-2 .w-dyn-item')) for n in (1,2,3,4)],[10,10,10,5])
            self.assertEqual(sum(len(v.select('.collection-list-wrapper-2 .w-dyn-item')) for v in variants.values()),35)
            self.assertIsNotNone(variants[1].select_one('noscript a[href="/analytics-org-nz/events/page/4/"]'))
            self.assertEqual(variants[1].select_one('.event-name').get_text(),'<script>not executable</script>')
            self.assertIsNone(variants[1].select_one('.event-name script'))
            self.assertEqual(len(variants[1].select('.event-thumbnail')),1)
            self.assertIn('September 10, 2026',variants[1].get_text())
            for variant in variants.values():
                self.assertIsNone(variant.select_one('.event-sync-note'))
                self.assertNotIn('View the latest on Eventbrite',variant.get_text())


if __name__ == '__main__':unittest.main()
