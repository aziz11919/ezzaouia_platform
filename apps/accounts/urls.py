from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/',   views.login_view,  name='login'),
    path('logout/',  views.logout_view, name='logout'),
    path('ping/',    views.session_ping, name='ping'),

    # Password management
    path('change-password/',            views.change_password, name='change_password'),
    path('forgot-password/',            views.forgot_password, name='forgot_password'),
    path('reset-password/<str:token>/', views.reset_password,  name='reset_password'),

    # User profile
    path('profile/', views.edit_profile, name='edit_profile'),

    # User management (admin)
    path('users/',                        views.user_list,   name='user_list'),
    path('users/create/',                 views.create_user, name='create_user'),
    path('users/<int:user_id>/edit/',     views.user_edit,   name='user_edit'),
    path('users/<int:user_id>/toggle/',   views.user_toggle, name='user_toggle'),
    path('users/<int:user_id>/delete/',   views.user_delete, name='user_delete'),
]
