from django.urls import path
from .views import client_analysis_view

app_name = 'appearance_test'

urlpatterns = [
    path('api/test_results/', client_analysis_view, name='test_results'),
]
