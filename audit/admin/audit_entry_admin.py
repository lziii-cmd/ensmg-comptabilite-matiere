# audit/admin/audit_entry_admin.py
"""
Interface d'administration du journal d'audit.

Fonctionnalités :
  - Liste paginée avec badges colorés par type d'action
  - Filtres avancés : action, app, modèle, utilisateur, plage de dates
  - Recherche texte : nom utilisateur, repr objet, IP, détails
  - Arborescence de dates (date_hierarchy)
  - Vue détail avec tableau de diff coloré (avant/après)
  - Lecture seule — pas de création ni modification manuelle
  - Suppression réservée aux superutilisateurs
"""
import json
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from audit.models import AuditEntry


# ── Couleurs par action ────────────────────────────────────────────────────
ACTION_STYLES = {
    AuditEntry.Action.CREATION:        ('#28a745', 'Création'),
    AuditEntry.Action.MODIFICATION:    ('#007bff', 'Modification'),
    AuditEntry.Action.SUPPRESSION:     ('#dc3545', 'Suppression'),
    AuditEntry.Action.VALIDATION:      ('#17a2b8', 'Validation'),
    AuditEntry.Action.CONNEXION:       ('#6c757d', 'Connexion'),
    AuditEntry.Action.DECONNEXION:     ('#adb5bd', 'Déconnexion'),
    AuditEntry.Action.ECHEC_CONNEXION: ('#fd7e14', 'Échec connexion'),
    AuditEntry.Action.EXPORT:          ('#6610f2', 'Export'),
    AuditEntry.Action.IMPRESSION:      ('#e83e8c', 'Impression'),
}


@admin.register(AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin):

    # ── Liste ──────────────────────────────────────────────────────────────
    list_display  = (
        'horodatage',
        'badge_action',
        'utilisateur',
        'module_modele',
        'objet_court',
        'adresse_ip',
        'a_des_changements',
    )
    list_filter   = (
        'action',
        'app_label',
        'model_name',
        ('user', admin.RelatedOnlyFieldListFilter),
        'timestamp',
    )
    search_fields = (
        'user_repr',
        'object_repr',
        'ip_address',
        'details',
        'object_id',
    )
    date_hierarchy = 'timestamp'
    ordering       = ('-timestamp',)
    list_per_page  = 50

    # ── Détail ─────────────────────────────────────────────────────────────
    readonly_fields = (
        'timestamp',
        'user',
        'user_repr',
        'ip_address',
        'session_key',
        'action',
        'app_label',
        'model_name',
        'object_id',
        'object_repr',
        'tableau_changements',
        'details',
    )

    fieldsets = (
        ('👤 Qui', {
            'fields': ('user', 'user_repr', 'ip_address', 'session_key'),
        }),
        ('📋 Quoi', {
            'fields': ('action', 'app_label', 'model_name', 'object_id', 'object_repr'),
        }),
        ('🔍 Changements', {
            'fields': ('tableau_changements', 'details'),
        }),
        ('🕐 Quand', {
            'fields': ('timestamp',),
        }),
    )

    # ── Permissions ────────────────────────────────────────────────────────
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        # Seuls les superutilisateurs peuvent supprimer des entrées d'audit
        return request.user.is_superuser

    # ── Colonnes personnalisées ────────────────────────────────────────────

    @admin.display(description='Horodatage', ordering='timestamp')
    def horodatage(self, obj):
        return format_html(
            '<span style="white-space:nowrap;font-family:monospace">{}</span>',
            obj.timestamp.strftime('%d/%m/%Y %H:%M:%S'),
        )

    @admin.display(description='Action')
    def badge_action(self, obj):
        color, label = ACTION_STYLES.get(obj.action, ('#6c757d', obj.action))
        return format_html(
            '<span style="'
            'background:{};color:#fff;padding:2px 10px;'
            'border-radius:12px;font-size:11px;font-weight:bold;'
            'white-space:nowrap'
            '">{}</span>',
            color, label,
        )

    @admin.display(description='Utilisateur', ordering='user_repr')
    def utilisateur(self, obj):
        if obj.user_repr:
            return obj.user_repr
        return format_html('<em style="color:#aaa">(système)</em>')

    @admin.display(description='Application / Modèle')
    def module_modele(self, obj):
        return format_html(
            '<span style="color:#888">{}</span> / <strong>{}</strong>',
            obj.app_label,
            obj.model_name,
        )

    @admin.display(description='Objet', ordering='object_repr')
    def objet_court(self, obj):
        text = obj.object_repr[:70]
        if len(obj.object_repr) > 70:
            text += '…'
        return text

    @admin.display(description='IP', ordering='ip_address')
    def adresse_ip(self, obj):
        if obj.ip_address:
            return format_html(
                '<span style="font-family:monospace;font-size:12px">{}</span>',
                obj.ip_address,
            )
        return '—'

    @admin.display(description='Diff', boolean=True)
    def a_des_changements(self, obj):
        return bool(obj.changes)

    # ── Tableau de diff ────────────────────────────────────────────────────

    @admin.display(description='Détail des changements')
    def tableau_changements(self, obj):
        if not obj.changes:
            return format_html('<em style="color:#aaa">Aucun champ modifié enregistré.</em>')

        try:
            lignes = []
            for champ, diff in obj.changes.items():
                avant = diff.get('avant', '—')
                apres = diff.get('apres', '—')

                # Formater les dicts (FK enrichies) en texte lisible
                def fmt(v):
                    if isinstance(v, dict) and 'id' in v:
                        return f"{v.get('repr', '')} (id={v.get('id')})"
                    if v is None:
                        return '<em style="color:#bbb">—</em>'
                    return str(v)

                lignes.append(
                    f'<tr>'
                    f'<td style="padding:5px 10px;font-weight:600;'
                    f'color:#495057;border-bottom:1px solid #dee2e6">{champ}</td>'
                    f'<td style="padding:5px 10px;color:#dc3545;'
                    f'border-bottom:1px solid #dee2e6">{fmt(avant)}</td>'
                    f'<td style="padding:5px 10px;color:#28a745;'
                    f'border-bottom:1px solid #dee2e6">{fmt(apres)}</td>'
                    f'</tr>'
                )

            html = (
                '<table style="border-collapse:collapse;font-size:13px;'
                'width:100%;max-width:800px">'
                '<thead>'
                '<tr style="background:#f8f9fa">'
                '<th style="padding:6px 10px;text-align:left;'
                'border-bottom:2px solid #dee2e6;color:#6c757d">Champ</th>'
                '<th style="padding:6px 10px;text-align:left;'
                'border-bottom:2px solid #dee2e6;color:#dc3545">Avant</th>'
                '<th style="padding:6px 10px;text-align:left;'
                'border-bottom:2px solid #dee2e6;color:#28a745">Après</th>'
                '</tr>'
                '</thead>'
                '<tbody>'
                + ''.join(lignes) +
                '</tbody></table>'
            )
            return mark_safe(html)

        except Exception:
            return format_html(
                '<pre style="font-size:11px">{}</pre>',
                json.dumps(obj.changes, ensure_ascii=False, indent=2),
            )
