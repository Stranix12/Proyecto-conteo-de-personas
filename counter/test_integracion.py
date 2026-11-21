"""Pruebas de integración: rutas principales y flujos completos de LabCount.

Validan que las vistas, los modelos, la base de datos y la exportación CSV
trabajen juntos. El detector se reemplaza por una versión simulada en los
flujos que no necesitan el modelo ONNX, para que sean rápidos y repetibles.
"""
import csv
import io
import json
import uuid
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from .models import CountingSession, Reading

SAMPLE = Path(__file__).parent / 'static/counter/sample.png'


def detector_simulado(conteo):
    """Devuelve una función que imita a analyze() con un conteo fijo."""
    def analyze(raw, threshold=0.35):
        return {
            'count': conteo,
            'processing_ms': 12.5,
            'boxes': [],
            'jpeg': b'\xff\xd8\xff\xd9',
        }
    return analyze


def leer_csv(response):
    texto = response.content.decode('utf-8-sig')
    return list(csv.reader(io.StringIO(texto)))


class BaseIntegracion(TestCase):
    def setUp(self):
        self.client.get('/')

    def crear_sesion(self, cliente=None, capacidad=24, fuente='image'):
        cliente = cliente or self.client
        respuesta = cliente.post(
            '/api/sessions/',
            json.dumps({'source': fuente, 'capacity': capacidad}),
            content_type='application/json',
        )
        self.assertEqual(respuesta.status_code, 201)
        return respuesta.json()['id']

    def enviar_cuadro(self, sid, cliente=None, umbral='0.35'):
        cliente = cliente or self.client
        archivo = SimpleUploadedFile('frame.jpg', b'imagen', content_type='image/jpeg')
        return cliente.post(f'/api/sessions/{sid}/frames/', {'frame': archivo, 'threshold': umbral})


class RutasPrincipalesTests(BaseIntegracion):
    def test_inicio_responde_200_con_la_plantilla_del_panel(self):
        respuesta = self.client.get('/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, 'counter/dashboard.html')

    def test_inicio_crea_la_cookie_de_sesion(self):
        respuesta = Client().get('/')
        self.assertIn('sessionid', respuesta.cookies)

    def test_inicio_solo_acepta_get(self):
        self.assertEqual(self.client.post('/').status_code, 405)

    def test_listado_de_sesiones_devuelve_json(self):
        respuesta = self.client.get('/api/sessions/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/json')
        self.assertEqual(respuesta.json(), {'sessions': []})

    def test_exportacion_csv_se_descarga_como_adjunto(self):
        respuesta = self.client.get('/api/export.csv')
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('attachment', respuesta['Content-Disposition'])

    def test_ruta_inexistente_devuelve_404(self):
        self.assertEqual(self.client.get('/api/no-existe/').status_code, 404)

    def test_detener_o_enviar_cuadro_a_una_sesion_inexistente_devuelve_404(self):
        falso = uuid.uuid4()
        self.assertEqual(self.client.post(f'/api/sessions/{falso}/stop/').status_code, 404)
        self.assertEqual(self.client.post(f'/api/sessions/{falso}/frames/').status_code, 404)


class FlujoCompletoTests(BaseIntegracion):
    def test_flujo_crear_detectar_detener_y_consultar_historial(self):
        sid = self.crear_sesion(capacidad=2)

        with patch('counter.views.analyze', side_effect=detector_simulado(3)):
            primero = self.enviar_cuadro(sid)
        self.assertEqual(primero.status_code, 200)
        self.assertEqual(primero.json()['count'], 3)
        self.assertTrue(primero.json()['over_capacity'])
        self.assertTrue(primero.json()['image'].startswith('data:image/jpeg;base64,'))

        with patch('counter.views.analyze', side_effect=detector_simulado(1)):
            segundo = self.enviar_cuadro(sid)
        self.assertEqual(segundo.status_code, 200)
        self.assertFalse(segundo.json()['over_capacity'])

        resumen = self.client.get('/api/sessions/').json()['sessions'][0]
        self.assertEqual((resumen['samples'], resumen['peak'], resumen['mean']), (2, 3, 2.0))
        self.assertFalse(resumen['ended'])

        self.assertEqual(self.client.post(f'/api/sessions/{sid}/stop/').json(), {'ok': True})
        self.assertTrue(self.client.get('/api/sessions/').json()['sessions'][0]['ended'])

        with patch('counter.views.analyze', side_effect=detector_simulado(1)):
            tarde = self.enviar_cuadro(sid)
        self.assertEqual(tarde.status_code, 409)

        filas = leer_csv(self.client.get('/api/export.csv'))
        self.assertEqual([fila[3] for fila in filas[1:]], ['3', '1'])

    def test_error_del_detector_no_guarda_y_la_sesion_sigue_abierta(self):
        sid = self.crear_sesion()
        with patch('counter.views.analyze', side_effect=RuntimeError('modelo no disponible')):
            fallido = self.enviar_cuadro(sid)
        self.assertEqual(fallido.status_code, 503)
        self.assertEqual(Reading.objects.count(), 0)

        with patch('counter.views.analyze', side_effect=detector_simulado(4)):
            correcto = self.enviar_cuadro(sid)
        self.assertEqual(correcto.status_code, 200)
        self.assertEqual(Reading.objects.filter(session_id=sid).count(), 1)

    def test_umbral_enviado_se_guarda_y_aparece_en_el_csv(self):
        sid = self.crear_sesion()
        with patch('counter.views.analyze', side_effect=detector_simulado(2)):
            self.assertEqual(self.enviar_cuadro(sid, umbral='0.5').status_code, 200)
        self.assertEqual(Reading.objects.get(session_id=sid).threshold, 0.5)
        fila = leer_csv(self.client.get('/api/export.csv'))[1]
        self.assertEqual(fila[6], '0.5')

    def test_varias_sesiones_aparecen_en_el_historial_y_en_el_csv(self):
        primera = self.crear_sesion(fuente='video')
        segunda = self.crear_sesion(fuente='camera')
        with patch('counter.views.analyze', side_effect=detector_simulado(1)):
            self.enviar_cuadro(primera)
            self.enviar_cuadro(primera)
            self.enviar_cuadro(segunda)
        historial = self.client.get('/api/sessions/').json()['sessions']
        self.assertEqual(sorted(s['samples'] for s in historial), [1, 2])
        fuentes = {fila[2] for fila in leer_csv(self.client.get('/api/export.csv'))[1:]}
        self.assertEqual(fuentes, {'video', 'camera'})

    def test_dos_navegadores_trabajan_sin_mezclar_sus_datos(self):
        otro = Client()
        otro.get('/')
        sid_a = self.crear_sesion()
        sid_b = self.crear_sesion(cliente=otro)
        with patch('counter.views.analyze', side_effect=detector_simulado(5)):
            self.enviar_cuadro(sid_a)
            self.enviar_cuadro(sid_b, cliente=otro)
        self.assertEqual([s['id'] for s in self.client.get('/api/sessions/').json()['sessions']], [sid_a])
        self.assertEqual([s['id'] for s in otro.get('/api/sessions/').json()['sessions']], [sid_b])
        self.assertEqual(len(leer_csv(otro.get('/api/export.csv'))) - 1, 1)

    @skipUnless(SAMPLE.exists(), 'No se encontró la imagen de ejemplo')
    def test_flujo_con_el_detector_real_sobre_la_imagen_de_ejemplo(self):
        sid = self.crear_sesion(capacidad=1, fuente='sample')
        archivo = SimpleUploadedFile('ejemplo.png', SAMPLE.read_bytes(), content_type='image/png')
        respuesta = self.client.post(f'/api/sessions/{sid}/frames/', {'frame': archivo, 'threshold': '0.35'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()['count'], 2)
        self.assertTrue(respuesta.json()['over_capacity'])
        self.assertEqual(self.client.post(f'/api/sessions/{sid}/stop/').status_code, 200)
        self.assertEqual(CountingSession.objects.get(id=sid).readings.count(), 1)
