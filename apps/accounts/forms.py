from django import forms
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q
from .models import User


class UserCreateForm(forms.ModelForm):
    password         = forms.CharField(widget=forms.PasswordInput, label="Password")
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    class Meta:
        model  = User  #Le formulaire est basé sur le modèle User
        fields = ['username', 'first_name', 'last_name', 'email',
                  'role', 'department', 'phone', 'is_active']

    def clean(self):  #valider tout le formulaire
        cleaned = super().clean()  #Récupère les données nettoyées du formulaire
        p1, p2  = cleaned.get('password'), cleaned.get('password_confirm')  #Récupère password et password_confirm
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")  # raise : arrêter l'exécution et afficher un message d'erreur.
        if p1:
            validate_password(p1)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)  #Crée l'utilisateur sans l'enregistrer en base
        user.set_password(self.cleaned_data['password'])  #Hash le mot de passe avant de le sauvegarder
        if commit:
            user.save()  #Sauvegarde l'utilisateur dans la base
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
        current = cleaned.get('current_password')
        p1, p2  = cleaned.get('new_password'), cleaned.get('new_password_confirm')
        # verifier ancien mot de passe
        if current and not self.user.check_password(current):
            raise forms.ValidationError("Current password is incorrect")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("New passwords do not match.")
        if p1:
            validate_password(p1)
        return cleaned
