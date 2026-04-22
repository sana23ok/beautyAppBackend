from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Restores fields removed by the accidental 0009_remove_... migration, and adds
    MasterService.is_active so price-list updates no longer delete bookings.
    """

    dependencies = [
        ('masters', '0007_normalize_masterservice_schema'),
    ]

    operations = [
        # --- Master payment fields (were in 0008, then incorrectly removed) ---
        migrations.AddField(
            model_name='master',
            name='iban',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='master',
            name='payment_purpose',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        # --- MasterService prepayment + active flag ---
        migrations.AddField(
            model_name='masterservice',
            name='requires_prepayment',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='masterservice',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
