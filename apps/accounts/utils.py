import secrets #Module pour générer mots de passe et tokens sécurisés
import string  #contient lettres, chiffres etc (ascii_letters, digits...)
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone


def generate_random_password(length=12):
    """
    Generate a secure random password.
    Format: at least 1 uppercase, 1 lowercase, 1 digit, 1 symbol.
    Example: Xk7#mP2qRt9!
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"  #caractères autorisés
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))  #génère mot de passe aléatoire
        has_upper  = any(c.isupper() for c in password) #vérifie présence majuscule
        has_lower  = any(c.islower() for c in password) #vérifie présence minuscule
        has_digit  = any(c.isdigit() for c in password)#vérifie présence chiffre
        has_symbol = any(c in "!@#$%^&*" for c in password)#vérifie présence symbole
        if has_upper and has_lower and has_digit and has_symbol:
            return password


def generate_reset_token():
    """Generate a secure token for password reset."""
    return secrets.token_urlsafe(32) #génère token sécurisé de 32 caractères (URL-safe)


def send_welcome_email(user, plain_password):
    """Send welcome email with temporary password."""
    subject = "Your EZZAOUIA Platform Account"

    message = f"""Dear {user.get_full_name() or user.username},

Your account has been created on the EZZAOUIA Production Platform (MARETAP S.A.).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ACCESS CREDENTIALS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Platform URL : http://{settings.PLATFORM_HOST}/
Username     : {user.username}
Password     : {plain_password}
Role         : {user.get_role_display()}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPORTANT — FIRST LOGIN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You will be required to change your password
immediately upon first login.

Please choose a strong password that you have
not used before.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECURITY NOTICE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This email contains confidential information.
Do not forward or share your credentials.
Access is restricted to MARETAP staff only.

If you did not request this account, please
contact your system administrator immediately.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MARETAP S.A. — EZZAOUIA Field
CPF Zarzis, Tunisia
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is an automated message. Do not reply.
"""

    send_mail(
        subject        = subject,
        message        = message,
        from_email     = settings.DEFAULT_FROM_EMAIL,
        recipient_list = [user.email],
        fail_silently  = False,
    )


def send_password_reset_email(user, token):
    """Send password reset email with secure link."""
    reset_url = f"http://{settings.PLATFORM_HOST}/accounts/reset-password/{token}/"

    subject = "EZZAOUIA Platform — Password Reset Request"

    message = f"""Dear {user.get_full_name() or user.username},

We received a request to reset your password for the
EZZAOUIA Production Platform.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESET YOUR PASSWORD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Click the link below to reset your password :

{reset_url}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPORTANT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- This link is valid for 1 hour only.
- If you did not request a password reset,
  please ignore this email.
- Your password will not change until you
  click the link and create a new one.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MARETAP S.A. — EZZAOUIA Field
CPF Zarzis, Tunisia
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is an automated message. Do not reply.
"""

    send_mail(
        subject        = subject,
        message        = message,
        from_email     = settings.DEFAULT_FROM_EMAIL,
        recipient_list = [user.email],
        fail_silently  = False,
    )


def send_password_changed_email(user):
    """Notify user that their password was changed."""
    subject = "EZZAOUIA Platform — Password Changed Successfully"

    message = f"""Dear {user.get_full_name() or user.username},

Your password has been changed successfully.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Change date : {timezone.now().strftime('%d/%m/%Y at %H:%M')}
Account     : {user.username}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If you did not make this change, please contact
your administrator immediately.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MARETAP S.A. — EZZAOUIA Field
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is an automated message. Do not reply.
"""

    send_mail(
        subject        = subject,
        message        = message,
        from_email     = settings.DEFAULT_FROM_EMAIL,
        recipient_list = [user.email],
        fail_silently  = True,
    )
