import logging

logger = logging.getLogger('apps')

_TOPIC_KEYWORDS = {
    'PRODUCTION': ['production', 'bopd', 'stb', 'huile', 'débit', 'debit',
                   'volume', 'mensuel', 'annuel', 'historique'],
    'BUDGET':     ['budget', 'coût', 'cout', 'cost', 'opex', 'capex',
                   'dépense', 'depense', 'usd', 'tnd', 'dollar'],
    'WORKOVER':   ['workover', 'intervention', 'perforation', 'acidizing',
                   'completion', 'tubing', 'esp', 'pompe', 'réparation'],
    'RESERVOIR':  ['réservoir', 'reservoir', 'bsw', 'gor', 'wct', 'water cut',
                   'pression', 'pressure', 'layer', 'formation'],
}


def _detect_topic(question):
    q = question.lower()
    for topic, keywords in _TOPIC_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return topic
    return 'GENERAL'


def get_user_memory(user):
    """Retourne les 10 dernières mémoires de l'utilisateur formatées en texte."""
    try:
        from .models import UserMemory
        memories = UserMemory.objects.filter(user=user).order_by('-updated_at')[:10]
        if not memories:
            return ""

        lines = ["=== MÉMOIRE SESSIONS PRÉCÉDENTES ==="]
        for m in memories:
            label = f"Puits {m.well_code}" if m.well_code else "Champ global"
            date_str = m.updated_at.strftime('%d/%m/%Y') if m.updated_at else '?'
            lines.append(f"- {label} [{m.topic}] (vu le {date_str}) : {m.summary}")
        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"get_user_memory erreur : {e}")
        return ""


def update_user_memory(user, question, answer, well=None):
    """Crée ou met à jour la mémoire pour ce (user, well_code, topic)."""
    try:
        from .models import UserMemory
        topic     = _detect_topic(question)
        well_code = well.wellcode if well else None
        summary   = answer[:200].replace('\n', ' ').strip()

        UserMemory.objects.update_or_create(
            user=user,
            well_code=well_code,
            topic=topic,
            defaults={'summary': summary},
        )
    except Exception as e:
        logger.warning(f"update_user_memory erreur : {e}")
