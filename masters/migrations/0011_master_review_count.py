from django.db import migrations, models
from django.db.models import Avg, Count


def backfill_review_count_and_rating(apps, schema_editor):
    Master = apps.get_model('masters', 'Master')
    MasterReview = apps.get_model('masters', 'MasterReview')
    for m in Master.objects.all().only('id'):
        agg = MasterReview.objects.filter(master_id=m.pk).aggregate(cnt=Count('id'), avg=Avg('rating'))
        n = agg['cnt'] or 0
        raw = agg['avg']
        rating = float(raw) if raw is not None and n > 0 else 0.0
        Master.objects.filter(pk=m.pk).update(review_count=n, rating=rating)


class Migration(migrations.Migration):

    dependencies = [
        ('masters', '0010_masterreview'),
    ]

    operations = [
        migrations.AddField(
            model_name='master',
            name='review_count',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(backfill_review_count_and_rating, migrations.RunPython.noop),
    ]
