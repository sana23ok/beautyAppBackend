from django.apps import AppConfig


class MastersConfig(AppConfig):
    name = 'masters'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        import masters.signals  # noqa: F401
