# core/admin/notification_admin.py
from django.contrib import admin
from core.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('titre', 'destinataire', 'type_notif', 'lue', 'created_at')
    list_per_page = 20
    list_filter = ('type_notif', 'lue', 'created_at', 'destinataire')
    search_fields = ('titre', 'message', 'destinataire__username')
    readonly_fields = ('created_at', 'destinataire')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Informations', {
            'fields': ('destinataire', 'type_notif', 'titre', 'message', 'lue')
        }),
        ('Lien vers objet', {
            'fields': ('app_label', 'model_name', 'object_id'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Notifications are created programmatically, not manually
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete notifications
        return request.user.is_superuser
