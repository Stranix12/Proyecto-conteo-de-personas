import uuid
from django.db import models
class CountingSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.CharField(max_length=40, db_index=True)
    source = models.CharField(max_length=10, choices=[('camera', 'Cámara'), ('video', 'Video'), ('image', 'Imagen'), ('sample', 'Ejemplo')])
    capacity = models.PositiveSmallIntegerField(default=24)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ['-started_at']
class Reading(models.Model):
    session = models.ForeignKey(CountingSession, on_delete=models.CASCADE, related_name='readings')
    created_at = models.DateTimeField(auto_now_add=True)
    count = models.PositiveSmallIntegerField()
    processing_ms = models.FloatField()
    threshold = models.FloatField(default=0.35)
    class Meta:
        ordering = ['created_at']
