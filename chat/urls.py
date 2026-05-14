from django.urls import path

from . import views

urlpatterns = [
    path('api/chat/conversations/', views.conversations_list, name='conversations_list'),
    path('api/chat/unread_total/', views.unread_total, name='unread_total'),
    path('api/chat/conversations/<int:pk>/', views.conversation_detail, name='conversation_detail'),
    path('api/chat/conversations/<int:pk>/messages/', views.conversation_messages, name='conversation_messages'),
    path('api/chat/conversations/<int:pk>/delete/', views.conversation_delete_action, name='conversation_delete'),
    path('api/chat/conversations/<int:pk>/media/', views.conversation_upload_media, name='conversation_upload_media'),
    path('api/chat/conversations/<int:pk>/read/', views.mark_messages_read, name='mark_messages_read'),
]
