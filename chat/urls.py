from django.urls import path

from . import views

urlpatterns = [
    path('api/chat/conversations/', views.conversations_list, name='conversations_list'),
    path('api/chat/conversations/<int:pk>/', views.conversation_detail, name='conversation_detail'),
    path('api/chat/conversations/<int:pk>/messages/', views.conversation_messages, name='conversation_messages'),
    path('api/chat/conversations/<int:pk>/read/', views.mark_messages_read, name='mark_messages_read'),
]
