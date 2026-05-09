from django.urls import path

from . import views

app_name = 'users'

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────────────────
    path('api/auth/register/send-code/', views.send_verification_code, name='auth_register_send_code'),
    path('api/auth/register/', views.register, name='auth_register'),
    path('api/auth/login/', views.login, name='auth_login'),
    path('api/auth/google/', views.google_auth, name='auth_google'),
    path('api/auth/refresh/', views.token_refresh, name='auth_refresh'),
    path('api/auth/me/', views.me, name='auth_me'),
    path('api/auth/become_master/', views.become_master, name='auth_become_master'),
    path('api/auth/upload_avatar/', views.upload_avatar, name='upload_avatar'),

    # ── Users list ────────────────────────────────────────────────────────────
    path('api/users/', views.users_list, name='users_list'),

    # ── Clients ───────────────────────────────────────────────────────────────
    path('api/clients/', views.clients_list, name='clients_list'),
    path('api/clients/me/', views.my_client_profile, name='client_me'),
]
