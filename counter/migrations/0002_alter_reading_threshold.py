

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('counter', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reading',
            name='threshold',
            field=models.FloatField(default=0.35),
        ),
    ]
