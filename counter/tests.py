"""Pruebas de la API con PostgreSQL y pruebas reales del detector ONNX."""
import csv
import io
import json
from pathlib import Path
from unittest.mock import patch
import cv2
import numpy as np
from django.test import TestCase, SimpleTestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import CountingSession, Reading
from .detection import analyze, suppress

SAMPLE = Path(__file__).parent / 'static/counter/sample.png'

class DetectorTests(SimpleTestCase):
    def test_sample_has_two_people(self):
        result = analyze(SAMPLE.read_bytes())
        self.assertEqual(result['count'], 2)
        self.assertEqual(len(result['boxes']), 2)
        self.assertTrue(result['jpeg'].startswith(b'\xff\xd8'))

    def test_blank_has_zero_people(self):
        ok, raw = cv2.imencode('.jpg', np.zeros((480,640,3), np.uint8))
        self.assertTrue(ok)
        self.assertEqual(analyze(raw.tobytes())['count'], 0)

    def test_invalid_image(self):
        with self.assertRaises(ValueError):
            analyze(b'not-an-image')

    def test_tiny_image_rejected(self):
        _, raw = cv2.imencode('.png', np.zeros((20,20,3), np.uint8))
        with self.assertRaises(ValueError):
            analyze(raw.tobytes())

    def test_suppression_removes_overlapping_boxes(self):
        kept = suppress([[0,0,100,200],[5,5,100,200],[250,0,90,200]], [.9,.8,.85])
        self.assertEqual(set(kept), {0,2})

    def test_empty_suppression(self):
        self.assertEqual(suppress([], []), [])

class ApiTests(TestCase):
    def setUp(self):
        self.client.get('/')

    def create_session(self, capacity=24):
        response = self.client.post('/api/sessions/', json.dumps({'source':'image','capacity':capacity}), content_type='application/json')
        self.assertEqual(response.status_code,201)
        return response.json()['id']

    def upload(self, sid, raw=b'test', threshold='0.35'):
        return self.client.post(f'/api/sessions/{sid}/frames/', {'frame':SimpleUploadedFile('frame.jpg',raw,content_type='image/jpeg'),'threshold':threshold})

    def test_home_and_csrf_cookie(self):
        response = self.client.get('/')
        self.assertContains(response,'LabCount')
        self.assertIn('csrftoken', response.cookies)

    def test_create_and_list(self):
        sid = self.create_session()
        self.assertEqual(self.client.get('/api/sessions/').json()['sessions'][0]['id'],sid)

    def test_history_is_newest_first(self):
        first=self.create_session()
        newest=self.create_session()
        items=self.client.get('/api/sessions/').json()['sessions']
        self.assertEqual([s['id'] for s in items],[newest,first])

    def test_bad_source_and_capacity(self):
        for data in [{'source':'other','capacity':24},{'source':'image','capacity':0},{'source':'image','capacity':True},{'source':'image','capacity':1001}]:
            with self.subTest(data=data):
                self.assertEqual(self.client.post('/api/sessions/',json.dumps(data),content_type='application/json').status_code,400)

    def test_invalid_json(self):
        for raw in ['{','[]','null']:
            with self.subTest(raw=raw):
                self.assertEqual(self.client.post('/api/sessions/',raw,content_type='application/json').status_code,400)

    def test_session_isolation(self):
        sid = self.create_session()
        other=Client()
        self.assertEqual(other.get('/api/sessions/').json()['sessions'],[])
        self.assertEqual(other.post(f'/api/sessions/{sid}/stop/').status_code,404)
        self.assertEqual(other.post(f'/api/sessions/{sid}/frames/').status_code,404)

    def test_missing_frame(self):
        sid=self.create_session()
        self.assertEqual(self.client.post(f'/api/sessions/{sid}/frames/').status_code,400)

    def test_invalid_thresholds(self):
        sid=self.create_session()
        for value in ['nan','inf','-1','0','1.1','hello']:
            with self.subTest(value=value):
                self.assertEqual(self.upload(sid,threshold=value).status_code,400)

    def test_corrupt_image(self):
        self.assertEqual(self.upload(self.create_session()).status_code,400)
        self.assertEqual(Reading.objects.count(),0)

    def test_large_upload(self):
        self.assertEqual(self.upload(self.create_session(),b'x'*(3*1024*1024+1)).status_code,400)

    def test_real_detection_saved_and_exported(self):
        sid=self.create_session(capacity=1)
        response=self.upload(sid,SAMPLE.read_bytes())
        self.assertEqual(response.status_code,200)
        data=response.json()
        self.assertEqual(data['count'],2)
        self.assertTrue(data['over_capacity'])
        self.assertTrue(data['image'].startswith('data:image/jpeg;base64,'))
        reading=Reading.objects.get(session_id=sid)
        self.assertEqual(reading.count,2)
        self.assertGreater(reading.processing_ms,0)
        summary=self.client.get('/api/sessions/').json()['sessions'][0]
        self.assertEqual((summary['samples'],summary['peak'],summary['mean']),(1,2,2.0))
        rows=list(csv.reader(io.StringIO(self.client.get('/api/export.csv').content.decode('utf-8-sig'))))
        self.assertEqual(rows[1][0],sid)
        self.assertEqual(rows[1][3],'2')

    def test_stop_idempotent_and_reject_late_frames(self):
        sid=self.create_session()
        url=f'/api/sessions/{sid}/stop/'
        self.assertEqual(self.client.post(url).status_code,200)
        ended=CountingSession.objects.get(id=sid).ended_at
        self.assertEqual(self.client.post(url).status_code,200)
        self.assertEqual(CountingSession.objects.get(id=sid).ended_at,ended)
        self.assertEqual(self.upload(sid,SAMPLE.read_bytes()).status_code,409)
        self.assertEqual(Reading.objects.count(),0)

    def test_csv_has_only_owned_readings(self):
        self.create_session()
        foreign=CountingSession.objects.create(owner='other',source='image')
        Reading.objects.create(session=foreign,count=99,processing_ms=1)
        self.assertNotIn(b'99', self.client.get('/api/export.csv').content)

    def test_csrf_is_enforced(self):
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/api/sessions/',json.dumps({'source':'image','capacity':24}),content_type='application/json').status_code,403)

    def test_wrong_method(self):
        sid=self.create_session()
        self.assertEqual(self.client.get(f'/api/sessions/{sid}/stop/').status_code,405)
        self.assertEqual(self.client.get(f'/api/sessions/{sid}/frames/').status_code,405)

    @patch('counter.views.analyze', side_effect=RuntimeError('model missing'))
    def test_model_error_does_not_save(self, mocked):
        self.assertEqual(self.upload(self.create_session(),SAMPLE.read_bytes()).status_code,503)
        self.assertEqual(Reading.objects.count(),0)
