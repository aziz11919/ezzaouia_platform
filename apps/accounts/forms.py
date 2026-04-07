from django import forms
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from .models import User


class UserCreateForm(forms.ModelForm):
    password         = forms.CharField(widget=forms.PasswordInput, label="Password")
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    class Meta:
        model  = User
        fields = ['username', 'first_name', 'last_name', 'email',
                  'role', 'department', 'phone', 'is_active']

    def clean(self):
        cleaned = super().clean()
        p1, p2  = cleaned.get('password'), cleaned.get('password_confirm')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        if p1:
            validate_password(p1)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ['username', 'first_name', 'last_name', 'email',
                  'role', 'department', 'phone', 'is_active']


class ProfileForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email', 'department', 'phone']


class SetPasswordForm(forms.Form):
    """Réinitialisation mot de passe par l'admin."""
    password         = forms.CharField(widget=forms.PasswordInput, label="New password")
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirm")

    def clean(self):
        cleaned = super().clean()
        p1, p2  = cleaned.get('password'), cleaned.get('password_confirm')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        if p1:
            validate_password(p1)
        return cleaned


class ChangePasswordForm(forms.Form):
    """Changement de mot de passe par l'utilisateur lui-même."""
    current_password     = forms.CharField(widget=forms.PasswordInput, label="Current password")
    new_password         = forms.CharField(widget=forms.PasswordInput, label="New password")
    new_password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirm new password")

    def clean(self):
        cleaned = super().clean()
        p1, p2  = cleaned.get('new_password'), cleaned.get('new_password_confirm')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("New passwords do not match.")
        if p1:
            validate_password(p1)
        return cleaned
