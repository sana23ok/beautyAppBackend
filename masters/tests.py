"""Denormalized rating / review count on Master."""

from django.contrib.auth.models import User
from django.test import TestCase

from masters.models import Master, MasterReview


class MasterReviewAggregateTests(TestCase):
    def test_sync_with_no_reviews(self):
        u = User.objects.create_user(username='mu', email='mu@example.com', password='x')
        master = Master.objects.create(user=u, name='Ada')
        Master.sync_review_aggregates_for_master_id(master.pk)
        master.refresh_from_db()
        self.assertEqual(master.review_count, 0)
        self.assertEqual(master.rating, 0.0)

    def test_sync_average_and_count_two_reviews(self):
        mu = User.objects.create_user(username='ms', email='ms@example.com', password='x')
        ma = Master.objects.create(user=mu, name='Beth')
        clients = []
        for i in range(2):
            cu = User.objects.create_user(username=f'c{i}', email=f'c{i}@example.com', password='x')
            clients.append(cu)

        MasterReview.objects.create(master=ma, author=clients[0], rating=5, comment='nice')
        MasterReview.objects.create(master=ma, author=clients[1], rating=3, comment='ok')

        Master.sync_review_aggregates_for_master_id(ma.pk)
        ma.refresh_from_db()
        self.assertEqual(ma.review_count, 2)
        self.assertEqual(ma.rating, 4.0)
