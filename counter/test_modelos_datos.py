"""Pruebas unitarias de modelos y datos.

Cubren los modelos CountingSession y Reading, el historial de sesiones
(resumen por sesión, límite de 30) y la exportación a CSV.
"""
import csv
import io
import json
import uuid
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from .models import CountingSession, Reading


def leer_csv(response):
    """Convierte la respuesta CSV en una lista de filas (quita el BOM)."""
    texto = response.content.decode('utf-8-sig')
    return list(csv.reader(io.StringIO(texto)))


class CountingSessionModelTests(TestCase):
    def test_valores_por_defecto(self):
        sesion = CountingSession.objects.create(owner='a', source='image')
        self.assertIsInstance(sesion.id, uuid.UUID)
        self.assertEqual(sesion.capacity, 24)
        self.assertIsNotNone(sesion.started_at)
        self.assertIsNone(sesion.ended_at)

    def test_etiquetas_de_fuente(self):
        esperado = {'camera': 'Cámara', 'video': 'Video', 'image': 'Imagen', 'sample': 'Ejemplo'}
        for codigo, etiqueta in esperado.items():
            with self.subTest(source=codigo):
                sesion = CountingSession.objects.create(owner='a', source=codigo)
                self.assertEqual(sesion.get_source_display(), etiqueta)

    def test_cerrar_sesion_guarda_ended_at(self):
        sesion = CountingSession.objects.create(owner='a', source='image')
        sesion.ended_at = timezone.now()
        sesion.save()
        sesion.refresh_from_db()
        self.assertIsNotNone(sesion.ended_at)

    def test_orden_mas_reciente_primero(self):
        ahora = timezone.now()
        vieja = CountingSession.objects.create(owner='a', source='image')
        nueva = CountingSession.objects.create(owner='a', source='image')
        CountingSession.objects.filter(pk=vieja.pk).update(started_at=ahora - timedelta(hours=2))
        CountingSession.objects.filter(pk=nueva.pk).update(started_at=ahora)
        self.assertEqual(list(CountingSession.objects.all()), [nueva, vieja])


class ReadingModelTests(TestCase):
    def setUp(self):
        self.sesion = CountingSession.objects.create(owner='a', source='image')

    def test_umbral_por_defecto(self):
        lectura = Reading.objects.create(session=self.sesion, count=3, processing_ms=10.0)
        self.assertEqual(lectura.threshold, 0.35)

    def test_lecturas_se_asocian_a_la_sesion(self):
        Reading.objects.create(session=self.sesion, count=1, processing_ms=5)
        Reading.objects.create(session=self.sesion, count=2, processing_ms=6)
        self.assertEqual(self.sesion.readings.count(), 2)

    def test_orden_por_fecha_de_creacion(self):
        primera = Reading.objects.create(session=self.sesion, count=1, processing_ms=5)
        segunda = Reading.objects.create(session=self.sesion, count=2, processing_ms=5)
        Reading.objects.filter(pk=primera.pk).update(created_at=timezone.now() + timedelta(hours=1))
        self.assertEqual(list(self.sesion.readings.all()), [segunda, primera])

    def test_eliminar_sesion_elimina_sus_lecturas(self):
        Reading.objects.create(session=self.sesion, count=1, processing_ms=5)
        self.sesion.delete()
        self.assertEqual(Reading.objects.count(), 0)

    def test_conteo_negativo_es_rechazado_por_la_base(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Reading.objects.create(session=self.sesion, count=-1, processing_ms=5)


class HistorialTests(TestCase):
    def setUp(self):
        self.client.get('/')
        self.owner = self.client.session.session_key

    def crear_sesion(self, **extra):
        datos = {'owner': self.owner, 'source': 'image'}
        datos.update(extra)
        return CountingSession.objects.create(**datos)

    def historial(self):
        return self.client.get('/api/sessions/').json()['sessions']

    def test_historial_limitado_a_30_sesiones(self):
        for _ in range(35):
            self.crear_sesion()
        self.assertEqual(len(self.historial()), 30)

    def test_sesion_sin_lecturas_tiene_resumen_en_cero(self):
        self.crear_sesion()
        resumen = self.historial()[0]
        self.assertEqual((resumen['samples'], resumen['peak'], resumen['mean']), (0, 0, 0))

    def test_resumen_con_maximo_promedio_y_muestras(self):
        sesion = self.crear_sesion()
        for conteo in (1, 2, 2):
            Reading.objects.create(session=sesion, count=conteo, processing_ms=5)
        resumen = self.historial()[0]
        self.assertEqual(resumen['samples'], 3)
        self.assertEqual(resumen['peak'], 2)
        self.assertEqual(resumen['mean'], 1.7)  # 5/3 redondeado a 1 decimal

    def test_historial_muestra_fuente_legible_aforo_y_estado(self):
        sesion = self.crear_sesion(source='camera', capacity=50)
        resumen = self.historial()[0]
        self.assertEqual(resumen['source'], 'Cámara')
        self.assertEqual(resumen['capacity'], 50)
        self.assertFalse(resumen['ended'])
        self.client.post(f'/api/sessions/{sesion.id}/stop/')
        self.assertTrue(self.historial()[0]['ended'])

    def test_fecha_de_inicio_en_hora_de_ecuador(self):
        self.crear_sesion()
        self.assertTrue(self.historial()[0]['started'].endswith('-05:00'))

    def test_creacion_por_api_guarda_fuente_y_aforo(self):
        respuesta = self.client.post(
            '/api/sessions/',
            json.dumps({'source': 'video', 'capacity': 1000}),
            content_type='application/json',
        )
        self.assertEqual(respuesta.status_code, 201)
        sesion = CountingSession.objects.get(id=respuesta.json()['id'])
        self.assertEqual((sesion.source, sesion.capacity, sesion.owner), ('video', 1000, self.owner))

    def test_aforo_en_los_limites_1_y_1000_es_valido(self):
        for aforo in (1, 1000):
            with self.subTest(aforo=aforo):
                respuesta = self.client.post(
                    '/api/sessions/',
                    json.dumps({'source': 'image', 'capacity': aforo}),
                    content_type='application/json',
                )
                self.assertEqual(respuesta.status_code, 201)


class ExportCsvTests(TestCase):
    def setUp(self):
        self.client.get('/')
        self.owner = self.client.session.session_key

    def test_csv_sin_lecturas_solo_tiene_encabezado(self):
        respuesta = self.client.get('/api/export.csv')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('lecturas_conteo.csv', respuesta['Content-Disposition'])
        self.assertTrue(respuesta.content.startswith(b'\xef\xbb\xbf'))  # BOM para Excel
        self.assertEqual(
            leer_csv(respuesta),
            [['sesion', 'fecha_ecuador', 'fuente', 'personas', 'aforo', 'procesamiento_ms', 'umbral_yolox']],
        )

    def test_csv_contiene_los_valores_guardados(self):
        sesion = CountingSession.objects.create(owner=self.owner, source='video', capacity=10)
        Reading.objects.create(session=sesion, count=7, processing_ms=12.5, threshold=0.5)
        fila = leer_csv(self.client.get('/api/export.csv'))[1]
        self.assertEqual(fila[0], str(sesion.id))
        self.assertEqual([fila[2], fila[3], fila[4], fila[5], fila[6]], ['video', '7', '10', '12.5', '0.5'])

    def test_csv_fecha_en_hora_de_ecuador(self):
        sesion = CountingSession.objects.create(owner=self.owner, source='image')
        Reading.objects.create(session=sesion, count=1, processing_ms=1)
        fila = leer_csv(self.client.get('/api/export.csv'))[1]
        self.assertTrue(fila[1].endswith('-05:00'))

    def test_csv_incluye_lecturas_de_todas_las_sesiones_propias(self):
        for lecturas in (2, 1):
            sesion = CountingSession.objects.create(owner=self.owner, source='image')
            for _ in range(lecturas):
                Reading.objects.create(session=sesion, count=1, processing_ms=1)
        filas = leer_csv(self.client.get('/api/export.csv'))
        self.assertEqual(len(filas) - 1, 3)

    def test_csv_solo_acepta_metodo_get(self):
        self.assertEqual(self.client.post('/api/export.csv').status_code, 405)
