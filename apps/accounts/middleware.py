from urllib.parse import quote  #Sert à encoder une URL (ex: /dashboard/?id=1 devient sécurisé dans URL)

from django.contrib import auth, messages  #auth → login / logout utilisateur, messages → afficher des messages à l'utilisateur
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

EXEMPT_PATHS = {  #Liste des pages autorisées même si l'utilisateur doit changer password
    '/accounts/change-password/',
    '/accounts/logout/',
    '/accounts/login/',
}


class ForcePasswordChangeMiddleware:   #Middleware pour forcer changement mot de passe
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):#Cette fonction s'exécute à chaque requête
        if (
            request.user.is_authenticated  #Vérifie si utilisateur connecté
            and getattr(request.user, 'must_change_password', False)  #Vérifie champ must_change_password dans modèle User True → doit changer mot de passe
            and not any(request.path.startswith(p) for p in EXEMPT_PATHS) #Vérifie que la page demandée n'est PAS dans les pages autorisées
            and not request.path.startswith('/static/') #Ignore les fichiers CSS JS images
        ):
            return redirect('accounts:change_password')  

        return self.get_response(request) #Sinon continue normalement


class SessionTimeoutMiddleware: #Middleware pour expirer session après 30 minutes d'inactivité
    timeout_seconds = 1800
    session_key = "last_activity" #clé session pour stocker dernière activité

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now_ts = int(timezone.now().timestamp())
            last_activity = request.session.get(self.session_key) #récupère dernière activité depuis session

            if last_activity is not None:
                try:
                    inactivity_seconds = now_ts - int(last_activity)
                except (TypeError, ValueError): #sécurité si erreur conversion
                    inactivity_seconds = 0

                if inactivity_seconds > self.timeout_seconds:
                    user = request.user
                    username = user.get_username()

                    auth.logout(request)
                    messages.warning(
                        request,
                        "Session expired after 30 minutes of inactivity. Please sign in again.",
                    )
                    self._log_session_expired( #enregistre événement dans audit log
                        request=request,
                        user=user,
                        username=username,
                        inactivity_seconds=inactivity_seconds,
                    )

                    login_url = reverse("accounts:login") #récupère URL login
                    return redirect(f"{login_url}?next={quote(request.path)}")

            request.session[self.session_key] = now_ts #met à jour dernière activité     

        response = self.get_response(request)
        return response

    @staticmethod
    def _log_session_expired(*, request, user, username, inactivity_seconds):
        try:
            from apps.audit.models import AuditLog
        except Exception:
            return

        action = getattr(AuditLog.Action, "SESSION_EXPIRED", "SESSION_EXPIRED")
        AuditLog.log(
            action=action,
            user=user,
            request=request,
            details={
                "username": username,
                "path": request.path,
                "inactivity_seconds": inactivity_seconds,
            },
        )
