import base64
import csv
import json
import math
import cv2
from django.db import transaction
from django.db.models import Avg, Count, Max
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .models import CountingSession, Reading
from .detection import analyze

def owner(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key

@ensure_csrf_cookie
@require_GET
def dashboard(request):
    owner(request)
    return render(request, 'counter/dashboard.html')

@require_http_methods(['GET', 'POST'])
def sessions(request):
    key = owner(request)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            source = data.get('source')
            capacity = data.get('capacity', 24)
            if source not in {'camera', 'video', 'image', 'sample'} or type(capacity) is not int or not 1 <= capacity <= 1000:
                raise ValueError
        except (ValueError, TypeError, AttributeError):
            return JsonResponse({'error': 'Fuente o aforo inválidos. Aforo permitido de 1 a 1000.'}, status=400)
        item = CountingSession.objects.create(owner=key, source=source, capacity=capacity)
        return JsonResponse({'id': str(item.id)}, status=201)
    items = CountingSession.objects.filter(owner=key).annotate(samples=Count('readings'), peak=Max('readings__count'), mean=Avg('readings__count')).order_by('-started_at')[:30]
    return JsonResponse({'sessions': [{'id': str(s.id), 'source': s.get_source_display(), 'started': timezone.localtime(s.started_at).isoformat(), 'ended': bool(s.ended_at), 'samples': s.samples, 'peak': s.peak or 0, 'mean': round(s.mean or 0, 1), 'capacity': s.capacity} for s in items]})

@require_POST
def stop(request, session_id):
    with transaction.atomic():
        item = get_object_or_404(CountingSession.objects.select_for_update(), id=session_id, owner=owner(request))
        if item.ended_at is None:
            item.ended_at = timezone.now()
            item.save(update_fields=['ended_at'])
    return JsonResponse({'ok': True})

@require_POST
def frame(request, session_id):
    item = get_object_or_404(CountingSession, id=session_id, owner=owner(request))
    if item.ended_at:
        return JsonResponse({'error': 'La sesión ya está cerrada.'}, status=409)
    uploaded = request.FILES.get('frame')
    try:
        threshold = float(request.POST.get('threshold', '0.35'))
        if not math.isfinite(threshold) or not 0.1 <= threshold <= 0.95:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Umbral inválido. Usa un valor de 0.1 a 0.95.'}, status=400)
    if not uploaded or uploaded.size > 3 * 1024 * 1024:
        return JsonResponse({'error': 'Envía una imagen de hasta 3 MB.'}, status=400)
    try:
        result = analyze(uploaded.read(), threshold)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except (RuntimeError, cv2.error):
        return JsonResponse({'error': 'No se pudo ejecutar YOLOX. Revisa el modelo ONNX y OpenCV.'}, status=503)
    with transaction.atomic():
        item = CountingSession.objects.select_for_update().get(id=item.id)
        if item.ended_at:
            return JsonResponse({'error': 'La sesión ya está cerrada.'}, status=409)
        Reading.objects.create(session=item, count=result['count'], processing_ms=result['processing_ms'], threshold=threshold)
    result['image'] = 'data:image/jpeg;base64,' + base64.b64encode(result.pop('jpeg')).decode('ascii')
    result['over_capacity'] = result['count'] > item.capacity
    return JsonResponse(result)

@require_GET
def export_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="lecturas_conteo.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['sesion', 'fecha_ecuador', 'fuente', 'personas', 'aforo', 'procesamiento_ms', 'umbral_yolox'])
    for r in Reading.objects.filter(session__owner=owner(request)).select_related('session').iterator():
        writer.writerow([str(r.session_id), timezone.localtime(r.created_at).isoformat(), r.session.source, r.count, r.session.capacity, r.processing_ms, r.threshold])
    return response
