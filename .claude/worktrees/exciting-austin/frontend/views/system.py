# frontend/views/system.py
from .base import FrontendView


class ExercicesListView(FrontendView):
    template_name = 'v2/misc/exercices.html'
    active_page = 'exercices'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from core.models import Exercice
            ctx['exercices'] = Exercice.objects.order_by('-annee')
        except Exception:
            ctx['exercices'] = []
        return ctx


class LivreJournalView(FrontendView):
    template_name = 'v2/misc/livre_journal.html'
    active_page = 'livre_journal'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from inventory.models import MouvementStock
            from django.core.paginator import Paginator
            qs = MouvementStock.objects.select_related(
                'matiere', 'depot', 'exercice'
            ).order_by('-date', '-id')
            paginator = Paginator(qs, 30)
            page_obj = paginator.get_page(self.request.GET.get('page', 1))
            ctx['page_obj'] = page_obj
            ctx['mouvements'] = page_obj.object_list
        except Exception:
            ctx['mouvements'] = []
        return ctx


class NotificationsView(FrontendView):
    template_name = 'v2/misc/notifications.html'
    active_page = 'notifications'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        try:
            from core.models import Notification
            ctx['notifications'] = Notification.objects.order_by('-date_creation')[:50]
        except Exception:
            ctx['notifications'] = []
        return ctx


class ProfilView(FrontendView):
    template_name = 'v2/misc/profil.html'
    active_page = 'profil'


class SettingsView(FrontendView):
    template_name = 'v2/misc/settings.html'
    active_page = 'settings'
