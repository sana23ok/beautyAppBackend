from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Master, MasterReview


@receiver(post_save, sender=MasterReview)
@receiver(post_delete, sender=MasterReview)
def resync_master_review_aggregates(sender, instance, **kwargs):
    Master.sync_review_aggregates_for_master_id(instance.master_id)
