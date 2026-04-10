# frontend/views/base.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class FrontendView(LoginRequiredMixin, TemplateView):
    """Base view for all frontend pages. Adds active_page context."""
    active_page = 'dashboard'
    login_url = '/admin/login/'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['active_page'] = self.active_page
        ctx['notif_count'] = self._get_notif_count()
        return ctx

    def _get_notif_count(self):
        try:
            from core.models import Notification
            return Notification.objects.filter(
                lue=False
            ).count()
        except Exception:
            return 0
