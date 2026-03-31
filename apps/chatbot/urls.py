from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('',                          views.chatbot_view,     name='chat'),
    path('session/<int:session_id>/', views.chatbot_view,     name='session'),
    path('new/',                      views.new_session,      name='new'),
    path('ask/',                      views.ask_view,         name='ask'),
    path('upload/',                   views.upload_chat_file, name='upload'),
    path('session/<int:session_id>/delete/', views.delete_session, name='delete_session'),
]