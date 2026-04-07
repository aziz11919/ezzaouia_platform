from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from functools import wraps
from apps.audit.models import AuditLog
from .models import User
from .utils import (
    generate_random_password,
    generate_reset_token,
    send_welcome_email,
    send_password_reset_email,
    send_password_changed_email,
)


# ── Décorateurs de rôle ──────────────────────────────────────────

def role_required(*roles):
    """Décorateur générique — restreint l'accès selon le rôle."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.role in roles:
                return view_func(request, *args, **kwargs)
            messages.error(request, "Unauthorized access.")
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
            if user.must_change_password:
                request.session['force_change_password'] = True
                return redirect('accounts:change_password')
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard:home')
        else:
            messages.error(request, "Incorrect username or password.")

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
                messages.success(request, "Profile updated successfully.")
                return redirect('accounts:profile')

        elif 'change_password' in request.POST:
            pwd_form = ChangePasswordForm(request.POST)
            if pwd_form.is_valid():
                if not request.user.check_password(pwd_form.cleaned_data['current_password']):
                    pwd_form.add_error('current_password', "Current password is incorrect.")
                else:
                    request.user.set_password(pwd_form.cleaned_data['new_password'])
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    messages.success(request, "Password changed successfully.")
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
            messages.success(request, f"User '{user.username}' created successfully.")
            return redirect('accounts:user_list')
    else:
        form = UserCreateForm(initial={'is_active': True, 'role': User.Role.INGENIEUR})

    return render(request, 'accounts/user_form.html', {
        'form':   form,
        'action': 'create',
        'title':  'Create user',
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
                messages.success(request, "Password reset successfully.")
                return redirect('accounts:user_edit', user_id=user_id)

        else:
            form = UserEditForm(request.POST, instance=target)
            if form.is_valid():
                form.save()
                messages.success(request, "User updated successfully.")
                return redirect('accounts:user_list')

    return render(request, 'accounts/user_form.html', {
        'form':        form,
        'pwd_form':    pwd_form,
        'action':      'edit',
        'title':       f"Edit — {target.get_full_name() or target.username}",
        'target_user': target,
    })


@admin_required
def user_toggle(request, user_id):
    target = get_object_or_404(User, id=user_id)
    if target == request.user:
        messages.error(request, "You cannot deactivate your own account.")
    else:
        target.is_active = not target.is_active
        target.save(update_fields=['is_active'])
        state = "activated" if target.is_active else "deactivated"
        messages.success(request, f"Account '{target.username}' {state}.")
    return redirect('accounts:user_list')


@admin_required
def user_delete(request, user_id):
    target = get_object_or_404(User, id=user_id)
    if target == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('accounts:user_list')
    if request.method == 'POST':
        name = target.get_full_name() or target.username
        target.delete()
        messages.success(request, f"User '{name}' deleted.")
        return redirect('accounts:user_list')
    return render(request, 'accounts/user_confirm_delete.html', {'target_user': target})


# ── New user creation with email ─────────────────────────────────

@admin_required
def create_user(request):
    if request.method == 'POST':
        username   = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()
        email      = request.POST.get('email', '').strip()
        role       = request.POST.get('role', '')
        department = request.POST.get('department', '').strip()
        phone      = request.POST.get('phone', '').strip()

        errors = []
        if not username:
            errors.append("Username is required.")
        elif User.objects.filter(username=username).exists():
            errors.append("Username already exists.")
        if not email:
            errors.append("Email is required.")
        elif User.objects.filter(email=email).exists():
            errors.append("Email already in use.")
        elif not email.endswith('@maretap.tn'):
            errors.append("Email must be a MARETAP email (@maretap.tn).")
        if role not in [r[0] for r in User.Role.choices]:
            errors.append("Invalid role selected.")

        if errors:
            return render(request, 'accounts/create_user.html', {
                'errors':    errors,
                'form_data': request.POST,
                'roles':     User.Role.choices,
            })

        plain_password = generate_random_password()

        user = User.objects.create_user(
            username   = username,
            email      = email,
            password   = plain_password,
            first_name = first_name,
            last_name  = last_name,
        )
        user.role                 = role
        user.department           = department
        user.phone                = phone
        user.must_change_password = True
        user.save()

        try:
            send_welcome_email(user, plain_password)
            messages.success(
                request,
                f"User {username} created successfully. Password sent to {email}."
            )
        except Exception as e:
            messages.warning(
                request,
                f"User created but email failed: {e}. Temporary password: {plain_password}"
            )

        try:
            AuditLog.log(
                action='CREATE_USER',
                user=request.user,
                request=request,
                details={'created_user': username, 'role': role},
            )
        except Exception:
            pass

        return redirect('accounts:user_list')

    return render(request, 'accounts/create_user.html', {
        'roles': User.Role.choices,
    })


# ── Password change (forced + voluntary) ─────────────────────────

@login_required
def change_password(request):
    is_forced = request.session.get('force_change_password', False)

    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password     = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        errors = []

        if not is_forced:
            if not request.user.check_password(current_password):
                errors.append("Current password is incorrect.")

        if new_password != confirm_password:
            errors.append("Passwords do not match.")
        if len(new_password) < 8:
            errors.append("Password must be at least 8 characters.")
        if not any(c.isupper() for c in new_password):
            errors.append("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in new_password):
            errors.append("Password must contain at least one number.")

        if errors:
            return render(request, 'accounts/change_password.html', {
                'errors':    errors,
                'is_forced': is_forced,
            })

        request.user.set_password(new_password)
        request.user.must_change_password  = False
        request.user.last_password_change  = timezone.now()
        request.user.save()

        send_password_changed_email(request.user)

        if is_forced and 'force_change_password' in request.session:
            del request.session['force_change_password']

        update_session_auth_hash(request, request.user)
        messages.success(request, "Password changed successfully.")
        return redirect('dashboard:home')

    return render(request, 'accounts/change_password.html', {
        'is_forced': is_forced,
    })


# ── Forgot password ───────────────────────────────────────────────

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        success_message = (
            "If this email is registered, you will receive "
            "a password reset link shortly."
        )
        try:
            user    = User.objects.get(email=email)
            token   = generate_reset_token()
            expires = timezone.now() + timedelta(hours=1)
            user.password_reset_token   = token
            user.password_reset_expires = expires
            user.save(update_fields=['password_reset_token', 'password_reset_expires'])
            send_password_reset_email(user, token)
        except User.DoesNotExist:
            pass

        return render(request, 'accounts/forgot_password.html', {
            'success': success_message
        })

    return render(request, 'accounts/forgot_password.html')


# ── Reset password via token ──────────────────────────────────────

def reset_password(request, token):
    try:
        user = User.objects.get(
            password_reset_token=token,
            password_reset_expires__gt=timezone.now(),
        )
    except User.DoesNotExist:
        return render(request, 'accounts/reset_password.html', {
            'error': (
                "This reset link is invalid or has expired. "
                "Please request a new one."
            )
        })

    if request.method == 'POST':
        new_password     = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        errors = []
        if new_password != confirm_password:
            errors.append("Passwords do not match.")
        if len(new_password) < 8:
            errors.append("Password must be at least 8 characters.")
        if not any(c.isupper() for c in new_password):
            errors.append("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in new_password):
            errors.append("Password must contain at least one number.")

        if errors:
            return render(request, 'accounts/reset_password.html', {
                'errors': errors,
                'token':  token,
            })

        user.set_password(new_password)
        user.must_change_password   = False
        user.password_reset_token   = None
        user.password_reset_expires = None
        user.last_password_change   = timezone.now()
        user.save()

        send_password_changed_email(user)

        return render(request, 'accounts/reset_password.html', {
            'success': (
                "Your password has been reset successfully. "
                "You can now log in."
            )
        })

    return render(request, 'accounts/reset_password.html', {'token': token})


# ── Edit profile ──────────────────────────────────────────────────

@login_required
def edit_profile(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name',  '').strip()
        phone      = request.POST.get('phone',      '').strip()
        department = request.POST.get('department', '').strip()
        new_email  = request.POST.get('email',      '').strip()

        errors = []

        if new_email != request.user.email:
            if not new_email.endswith('@maretap.tn'):
                errors.append("Email must be a MARETAP email (@maretap.tn).")
            elif User.objects.filter(email=new_email).exclude(pk=request.user.pk).exists():
                errors.append("This email is already in use.")
            else:
                request.user.email = new_email

        if errors:
            return render(request, 'accounts/edit_profile.html', {
                'errors': errors,
            })

        request.user.first_name = first_name
        request.user.last_name  = last_name
        request.user.phone      = phone
        request.user.department = department
        request.user.save()

        messages.success(request, "Profile updated successfully.")
        return redirect('accounts:edit_profile')

    return render(request, 'accounts/edit_profile.html')
