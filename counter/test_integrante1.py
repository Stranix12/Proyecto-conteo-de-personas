
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch
import cv2
import numpy as np
from django.test import SimpleTestCase, RequestFactory
from counter.detection import analyze, suppress, GRIDS
from counter.views import sessions


class Integrante1Tests(SimpleTestCase):
    def test_nms_elimina_duplicados(self):
        boxes = [[0, 0, 100, 200], [5, 5, 100, 200], [250, 0, 90, 200]]
        self.assertEqual(set(suppress(boxes, [.9, .8, .85])), {0, 2})

    def test_nms_vacio(self):
        self.assertEqual(suppress([], []), [])

    def test_umbral_filtra_puntuaciones(self):
        boxes = [[0, 0, 40, 80], [200, 0, 40, 80]]
        self.assertEqual(suppress(boxes, [.34, .80], .35), [1])
        self.assertEqual(suppress(boxes, [.34, .80], .90), [])

    def inferir(self, threshold):

        output = np.zeros((1, len(GRIDS), 85), np.float32)
        for index, score, category in [(0, .9, 0), (20, .6, 0), (40, .95, 2)]:
            output[0, index, :4] = [2, 2, 1, 1]
            output[0, index, 4] = 1
            output[0, index, 5 + category] = score
        net = Mock()
        net.forward.return_value = output
        ok, raw = cv2.imencode('.png', np.zeros((640, 640, 3), np.uint8))
        self.assertTrue(ok)
        with patch('counter.detection.detector', return_value=net):
            return analyze(raw.tobytes(), threshold)

    def test_cuenta_solo_personas(self):
        result = self.inferir(.35)
        self.assertEqual(result['count'], 2)
        self.assertEqual(len(result['boxes']), 2)
        self.assertTrue(result['jpeg'].startswith(b'\xff\xd8'))

    def test_subir_umbral_reduce_conteo(self):
        self.assertEqual(self.inferir(.75)['count'], 1)
        self.assertEqual(self.inferir(.95)['count'], 0)

    def test_imagen_invalida(self):
        with self.assertRaises(ValueError):
            analyze(b'archivo invalido')

    def solicitar(self, capacity):
        request = RequestFactory().post('/api/sessions/',
            json.dumps({'source': 'image', 'capacity': capacity}),
            content_type='application/json')
        with patch('counter.views.owner', return_value='prueba'), patch(
            'counter.views.CountingSession.objects.create',
            return_value=SimpleNamespace(id='prueba')) as create:
            response = sessions(request)
        return response, create

    def test_aforo_rechaza_valores_invalidos(self):
        for value in [0, -1, 1001, True, 2.5, '24', None]:
            with self.subTest(aforo=value):
                response, create = self.solicitar(value)
                self.assertEqual(response.status_code, 400)
                create.assert_not_called()

    def test_aforo_acepta_limites(self):
        for value in [1, 24, 1000]:
            with self.subTest(aforo=value):
                response, create = self.solicitar(value)
                self.assertEqual(response.status_code, 201)
                create.assert_called_once_with(owner='prueba', source='image', capacity=value)
