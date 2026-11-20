

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CountingSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('owner', models.CharField(db_index=True, max_length=40)),
                ('source', models.CharField(choices=[('camera', 'Cámara'), ('video', 'Video'), ('image', 'Imagen'), ('sample', 'Ejemplo')], max_length=10)),
                ('capacity', models.PositiveSmallIntegerField(default=24)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'ordering': ['-started_at'],
            },
        ),
        migrations.CreateModel(
            name='Reading',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('count', models.PositiveSmallIntegerField()),
                ('processing_ms', models.FloatField()),
                ('threshold', models.FloatField(default=0.5)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='readings', to='counter.countingsession')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
    ]
