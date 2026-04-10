# core/admin/pending_record_admin.py
from django.contrib import admin, messages
from django.utils import timezone
from core.models.pending_record import PendingRecord


@admin.register(PendingRecord)
class PendingRecordAdmin(admin.ModelAdmin):
    list_display  = ['verbose_name', 'app_label', 'model_name', 'submitted_by', 'submitted_at', 'status_badge']
    list_per_page = 20
    list_filter   = ['status', 'app_label', 'submitted_at']
    search_fields = ['verbose_name', 'submitted_by__username', 'model_name']
    readonly_fields = ['submitted_by', 'submitted_at', 'app_label', 'model_name',
                       'verbose_name', 'data', 'reviewed_by', 'reviewed_at']
    actions       = ['approve_selected', 'reject_selected']
    ordering      = ['-submitted_at']

    fieldsets = (
        ('Soumission', {
            'fields': ('submitted_by', 'submitted_at', 'verbose_name', 'app_label', 'model_name', 'data')
        }),
        ('Décision admin', {
            'fields': ('status', 'admin_comment', 'reviewed_by', 'reviewed_at')
        }),
    )

    def status_badge(self, obj):
        colors = {'pending': '#b45309', 'approved': '#059669', 'rejected': '#dc2626'}
        labels = {'pending': '⏳ En attente', 'approved': '✅ Approuvé', 'rejected': '❌ Rejeté'}
        color = colors.get(obj.status, '#6b7280')
        label = labels.get(obj.status, obj.status)
        return f'<span style="color:{color};font-weight:600;">{label}</span>'
    status_badge.short_description = 'Statut'
    status_badge.allow_tags = True

    def approve_selected(self, request, queryset):
        count = 0
        for rec in queryset.filter(status='pending'):
            try:
                from django.apps import apps
                Model = apps.get_model(rec.app_label, rec.model_name)
                data = rec.data
                # Nettoyer les champs non-éditables habituels
                for f in ['id', 'pk', 'created_at', 'updated_at']:
                    data.pop(f, None)
                obj = Model(**data)
                obj.save()
                rec.status = 'approved'
                rec.reviewed_by = request.user
                rec.reviewed_at = timezone.now()
                rec.save()
                count += 1
            except Exception as e:
                self.message_user(request, f'Erreur pour {rec}: {e}', messages.ERROR)
        self.message_user(request, f'{count} enregistrement(s) approuvé(s).', messages.SUCCESS)
    approve_selected.short_description = '✅ Approuver la sélection'

    def reject_selected(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )
        self.message_user(request, f'{updated} enregistrement(s) rejeté(s).', messages.WARNING)
    reject_selected.short_description = '❌ Rejeter la sélection'

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None):
        # Superusers and chefs de service (staff) can view/validate pending records
        return request.user.is_staff
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
