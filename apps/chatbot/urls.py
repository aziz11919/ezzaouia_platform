from django.urls import path
from . import stats_views, views

app_name = 'chatbot'

urlpatterns = [
    path('',                          views.chat_view,        name='chat'),
    path('session/<int:session_id>/', views.session_view,     name='session'),
    path('morning-suggestions/',      views.morning_suggestions_view, name='morning_suggestions'),
    path('new/',                      views.new_session,      name='new'),
    path('stats/',                    stats_views.chatbot_stats, name='stats'),
    path('ask/',                      views.ask_view,         name='ask'),
    path('rate/',                     views.rate_view,        name='rate'),
    path('upload/',                   views.upload_chat_file, name='upload'),
    path('session/<int:session_id>/delete/', views.delete_session, name='delete_session'),
    path('session/<int:session_id>/rename/', views.rename_session, name='rename_session'),
    path('stop/', views.stop_generation, name='stop'),
    path('add-comment/', views.add_comment, name='add_comment'),
    path('comments/<int:message_id>/', views.get_comments, name='get_comments'),
    path('share/<int:session_id>/', views.share_session, name='share_session'),
    path('shared/<str:token>/', views.shared_session_view, name='shared_session'),
    path('users/', views.list_users, name='list_users'),
    path('shared-with-me/', views.shared_with_me, name='shared_with_me'),
]
