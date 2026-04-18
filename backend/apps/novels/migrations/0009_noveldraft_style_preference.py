from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('novels', '0008_draftsetting_source_novelsetting_source_storyline_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='noveldraft',
            name='style_preference',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='风格偏好'),
        ),
    ]
