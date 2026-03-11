from django.urls import path

from . import views

app_name = 'users'

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    path('api/auth/register/', views.register, name='auth_register'),
    path('api/auth/login/', views.login, name='auth_login'),
    path('api/auth/google/', views.google_auth, name='auth_google'),
    path('api/auth/refresh/', views.token_refresh, name='auth_refresh'),
    path('api/auth/me/', views.me, name='auth_me'),

    # ── Users list ────────────────────────────────────────────────────────────
    path('api/users/', views.users_list, name='users_list'),

    # ── Clients ───────────────────────────────────────────────────────────────
    path('api/clients/', views.clients_list, name='clients_list'),
    path('api/clients/me/', views.my_client_profile, name='client_me'),
]
