from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from functools import wraps


# ── Décorateurs de rôle ──────────────────────────────────────────

def role_required(*roles):
    """Décorateur générique — restreint l'accès selon le rôle."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.role in roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, "Accès non autorisé.")
            return redirect('dashboard:home')
        return wrapper
    return decorator

def admin_required(view_func):
    return role_required('admin')(view_func)

def ingenieur_required(view_func):
    return role_required('admin', 'ingenieur')(view_func)

def direction_required(view_func):
    return role_required('admin', 'direction')(view_func)


# ── Vues ─────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # Redirection selon le rôle
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard:home')
        else:
            messages.error(request, "Identifiant ou mot de passe incorrect.")

    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {'user': request.user})