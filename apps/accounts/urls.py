from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication (HTML)
    path('login/',   views.login_view,  name='login'),
    path('logout/',  views.logout_view, name='logout'),
    path('ping/',    views.session_ping, name='ping'),

    # Password management (HTML)
    path('change-password/',            views.change_password, name='change_password'),
    path('forgot-password/',            views.forgot_password, name='forgot_password'),
    path('reset-password/<str:token>/', views.reset_password,  name='reset_password'),

    # User profile (HTML)
    path('profile/', views.edit_profile, name='edit_profile'),

    # User management (admin, HTML)
    path('users/',                        views.user_list,   name='user_list'),
    path('users/create/',                 views.create_user, name='create_user'),
    path('users/<int:user_id>/edit/',     views.user_edit,   name='user_edit'),
    path('users/<int:user_id>/toggle/',   views.user_toggle, name='user_toggle'),
    path('users/<int:user_id>/delete/',   views.user_delete, name='user_delete'),

    # ── API JSON pour React frontend ──────────────────────────────
    path('me/',                    views.api_me,              name='api_me'),
    path('api-login/',             views.api_login,           name='api_login'),
    path('api-logout/',            views.api_logout,          name='api_logout'),
    path('api-change-password/',   views.api_change_password, name='api_change_password'),
    path('api-profile/',           views.api_update_profile,  name='api_update_profile'),
    path('users-api/',             views.api_users,           name='api_users'),
    path('users-api/<int:user_id>/toggle/',         views.api_user_toggle,         name='api_user_toggle'),
    path('users-api/<int:user_id>/delete/',         views.api_user_delete,         name='api_user_delete'),
    path('api-forgot-password/',                    views.api_forgot_password,     name='api_forgot_password'),
    path('api-reset-password/<str:token>/',         views.api_reset_password,      name='api_reset_password'),
    path('api-create-user/',                        views.api_create_user,         name='api_create_user'),
    path('users-api/<int:user_id>/detail/',         views.api_get_user,            name='api_get_user'),
    path('users-api/<int:user_id>/edit/',           views.api_edit_user,           name='api_edit_user'),
    path('users-api/<int:user_id>/reset-password/', views.api_admin_reset_password, name='api_admin_reset_password'),
]
