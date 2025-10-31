from django.contrib.sessions.models import Session
from django.utils import timezone

def logout_other_sessions(user):
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    for session in sessions:
        data = session.get_decoded()
        if data.get('_auth_user_id') == str(user.id):
            session.delete()
