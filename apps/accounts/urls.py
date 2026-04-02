from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentification
    path('login/',   views.login_view,  name='login'),
    path('logout/',  views.logout_view, name='logout'),

    # Profil personnel
    path('profile/', views.profile_view, name='profile'),

    # Gestion des utilisateurs (admin)
    path('users/',                          views.user_list,   name='user_list'),
    path('users/create/',                   views.user_create, name='user_create'),
    path('users/<int:user_id>/edit/',       views.user_edit,   name='user_edit'),
    path('users/<int:user_id>/toggle/',     views.user_toggle, name='user_toggle'),
    path('users/<int:user_id>/delete/',     views.user_delete, name='user_delete'),
]
