from django.contrib import admin
from core.admin.detail_view_mixin import DetailViewMixin
from core.models.service import Service
from core.utils.exercices import selection_is_closed_only


@admin.register(Service)
class ServiceAdmin(DetailViewMixin, admin.ModelAdmin):
    list_display = ("code", "libelle", "responsable", "actif")
    list_per_page = 20
    list_filter = ("actif",)
    search_fields = ("code", "libelle", "responsable")
    ordering = ("code",)

    fieldsets = (
        ("Service", {"fields": ("code", "libelle", "responsable", "actif")}),
    )

    def _is_closed_context(self, request) -> bool:
        return selection_is_closed_only(request)

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request):
        if self._is_closed_context(request):
            return False
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if self._is_closed_context(request):
            return False
        return super().has_change_permission(request, obj=obj)

    def has_delete_permission(self, request, obj=None):
        if self._is_closed_context(request):
            return False
        return super().has_delete_permission(request, obj=obj)

    def get_readonly_fields(self, request, obj=None):
        if self._is_closed_context(request):
            return [f.name for f in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)

    def get_actions(self, request):
        if self._is_closed_context(request):
            return {}
        return super().get_actions(request)
