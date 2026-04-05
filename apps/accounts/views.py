from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from functools import wraps
from apps.audit.models import AuditLog
from .models import User


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


# ── Authentification ─────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user     = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            AuditLog.log(
                action=AuditLog.Action.LOGIN,
                user=user,
                request=request,
                details={'path': request.path},
            )
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard:home')
        else:
            messages.error(request, "Identifiant ou mot de passe incorrect.")

    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    AuditLog.log(
        action=AuditLog.Action.LOGOUT,
        user=request.user,
        request=request,
        details={'path': request.path},
    )
    logout(request)
    return redirect('accounts:login')


@login_required
def session_ping(request):
    return JsonResponse({"status": "ok"})


# ── Profil utilisateur ───────────────────────────────────────────

@login_required
def profile_view(request):
    from .forms import ProfileForm, ChangePasswordForm

    profile_form = ProfileForm(instance=request.user)
    pwd_form     = ChangePasswordForm()

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = ProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Profil mis à jour avec succès.")
                return redirect('accounts:profile')

        elif 'change_password' in request.POST:
            pwd_form = ChangePasswordForm(request.POST)
            if pwd_form.is_valid():
                if not request.user.check_password(pwd_form.cleaned_data['current_password']):
                    pwd_form.add_error('current_password', "Mot de passe actuel incorrect.")
                else:
                    request.user.set_password(pwd_form.cleaned_data['new_password'])
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    messages.success(request, "Mot de passe modifié avec succès.")
                    return redirect('accounts:profile')

    return render(request, 'accounts/profile.html', {
        'profile_form': profile_form,
        'pwd_form':     pwd_form,
    })


# ── Gestion des utilisateurs (admin uniquement) ──────────────────

@admin_required
def user_list(request):
    qs = User.objects.all().order_by('username')

    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(
            Q(username__icontains=search)   |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)  |
            Q(email__icontains=search)      |
            Q(department__icontains=search)
        )

    role_filter = request.GET.get('role', '')
    if role_filter:
        qs = qs.filter(role=role_filter)

    active_filter = request.GET.get('active', '')
    if active_filter == '1':
        qs = qs.filter(is_active=True)
    elif active_filter == '0':
        qs = qs.filter(is_active=False)

    all_users  = User.objects.all()
    stats = {
        'total':     all_users.count(),
        'actifs':    all_users.filter(is_active=True).count(),
        'admins':    all_users.filter(role=User.Role.ADMIN).count(),
        'ingenieurs': all_users.filter(role=User.Role.INGENIEUR).count(),
        'directions': all_users.filter(role=User.Role.DIRECTION).count(),
    }

    return render(request, 'accounts/users_list.html', {
        'users':         qs,
        'search':        search,
        'role_filter':   role_filter,
        'active_filter': active_filter,
        'roles':         User.Role.choices,
        'stats':         stats,
    })


@admin_required
def user_create(request):
    from .forms import UserCreateForm
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Utilisateur « {user.username} » créé avec succès.")
            return redirect('accounts:user_list')
    else:
        form = UserCreateForm(initial={'is_active': True, 'role': User.Role.INGENIEUR})

    return render(request, 'accounts/user_form.html', {
        'form':   form,
        'action': 'create',
        'title':  'Créer un utilisateur',
    })


@admin_required
def user_edit(request, user_id):
    from .forms import UserEditForm, SetPasswordForm
    target = get_object_or_404(User, id=user_id)

    form     = UserEditForm(instance=target)
    pwd_form = SetPasswordForm()

    if request.method == 'POST':
        if 'change_password' in request.POST:
            pwd_form = SetPasswordForm(request.POST)
            if pwd_form.is_valid():
                target.set_password(pwd_form.cleaned_data['password'])
                target.save()
                messages.success(request, "Mot de passe réinitialisé.")
                return redirect('accounts:user_edit', user_id=user_id)

        else:
            form = UserEditForm(request.POST, instance=target)
            if form.is_valid():
                form.save()
                messages.success(request, "Utilisateur modifié avec succès.")
                return redirect('accounts:user_list')

    return render(request, 'accounts/user_form.html', {
        'form':        form,
        'pwd_form':    pwd_form,
        'action':      'edit',
        'title':       f"Modifier — {target.get_full_name() or target.username}",
        'target_user': target,
    })


@admin_required
def user_toggle(request, user_id):
    target = get_object_or_404(User, id=user_id)
    if target == request.user:
        messages.error(request, "Vous ne pouvez pas désactiver votre propre compte.")
    else:
        target.is_active = not target.is_active
        target.save(update_fields=['is_active'])
        etat = "activé" if target.is_active else "désactivé"
        messages.success(request, f"Compte de « {target.username} » {etat}.")
    return redirect('accounts:user_list')


@admin_required
def user_delete(request, user_id):
    target = get_object_or_404(User, id=user_id)
    if target == request.user:
        messages.error(request, "Vous ne pouvez pas supprimer votre propre compte.")
        return redirect('accounts:user_list')
    if request.method == 'POST':
        name = target.get_full_name() or target.username
        target.delete()
        messages.success(request, f"Utilisateur « {name} » supprimé.")
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_confirm_delete.html', {'target_user': target})
