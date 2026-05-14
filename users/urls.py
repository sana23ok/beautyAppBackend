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
    path('api/auth/favorite-masters/', views.favorite_masters_list, name='favorite_masters_list'),
    path('api/auth/favorite-masters/toggle/', views.favorite_masters_toggle, name='favorite_masters_toggle'),
    path(
        'api/auth/favorite-masters/<int:master_id>/',
        views.favorite_masters_delete,
        name='favorite_masters_delete',
    ),

    # ── Users list ────────────────────────────────────────────────────────────
    path('api/users/', views.users_list, name='users_list'),
    path('api/users/<int:user_id>/report/', views.report_user, name='report_user'),

    # ── Clients ───────────────────────────────────────────────────────────────
    path('api/clients/', views.clients_list, name='clients_list'),
    path('api/clients/me/', views.my_client_profile, name='client_me'),

    # ── Moderation (staff only) ───────────────────────────────────────────────
    path('api/moderation/users/', views.moderation_users, name='mod_users'),
    path('api/moderation/users/<int:user_id>/', views.moderation_user_delete, name='mod_user_delete'),
    path('api/moderation/reviews/', views.moderation_reviews, name='mod_reviews'),
    path('api/moderation/reviews/<int:review_id>/', views.moderation_review_delete, name='mod_review_delete'),
]
