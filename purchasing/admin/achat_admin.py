# purchasing/admin/achat_admin.py
from decimal import Decimal
from datetime import datetime

from django import forms
from django.apps import apps
from django.contrib import admin, messages
from django.db.models import Sum
from django.urls import resolve
from django.utils import timezone
from django.utils.html import format_html

from core.admin.mixins import AgentRestrictedMixin
from core.admin.detail_view_mixin import DetailViewMixin
from purchasing.models import Achat, LigneAchat
from core.utils.exercices import (
    filter_qs_by_exercices_dates,
    selection_is_closed_only,
    exercice_for_date,
)


# ──────────────────────────────────────────────────────────────
# Utilitaires
# ──────────────────────────────────────────────────────────────
def _aware_midnight(d):
    """Datetime tz-aware à minuit pour la date d'achat."""
    if not d:
        return timezone.now()
    return datetime.combine(d, datetime.min.time(), tzinfo=timezone.get_current_timezone())


# ──────────────────────────────────────────────────────────────
# Formulaire admin : dépôt obligatoire
# ──────────────────────────────────────────────────────────────
class _AchatAdminForm(forms.ModelForm):
    class Meta:
        model = Achat
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "depot" in self.fields:
            self.fields["depot"].required = True


# ──────────────────────────────────────────────────────────────
# Inline lignes d'achat
# ──────────────────────────────────────────────────────────────
class LigneAchatInline(admin.TabularInline):
    model = LigneAchat
    extra = 1
    fields = ("matiere", "quantite", "prix_unitaire", "total_ht_display", "appreciation")
    readonly_fields = ("total_ht_display",)

    def total_ht_display(self, obj):
        if obj and obj.pk:
            return f"{obj.total_ligne_ht:,.0f} FCFA"
        return "—"
    total_ht_display.short_description = "Total HT"


# ──────────────────────────────────────────────────────────────
# Admin Achat
# ──────────────────────────────────────────────────────────────
@admin.register(Achat)
class AchatAdmin(DetailViewMixin, AgentRestrictedMixin, admin.ModelAdmin):
    detail_print_url_name = "documents:achat_document"
    detail_print_buttons = [
        {
            "url_name":  "documents:achat_document",
            "label":     "PVR",
            "icon":      "🖨",
            "condition": lambda obj: (obj.total_ttc or 0) >= 300_000,
        },
        {"url_name": "documents:achat_bon_entree_modele1", "label": "BE", "icon": "📋"},
    ]
    detail_fields_sections = [
        {
            "titre": "Informations générales",
            "fields": [
                ("Code",        "code"),
                ("Fournisseur", "fournisseur"),
                ("Date d'achat", lambda o: o.date_achat.strftime("%d/%m/%Y") if o.date_achat else "—"),
                ("N° Facture",  "numero_facture"),
                ("Dépôt",       "depot"),
                ("TVA active",  lambda o: "✅ Oui" if o.tva_active else "❌ Non"),
            ],
        },
        {
            "titre": "Montants",
            "fields": [
                ("Total HT",  lambda o: f"{int(o.total_ht or 0):,} F CFA".replace(",", " "),  "montant"),
                ("Total TVA", lambda o: f"{int(o.total_tva or 0):,} F CFA".replace(",", " "), "montant"),
                ("Total TTC", lambda o: f"{int(o.total_ttc or 0):,} F CFA".replace(",", " "), "montant"),
            ],
        },
        {
            "titre": "Commentaire",
            "obs_field": "commentaire",
            "fields": [],
        },
    ]
    detail_inline_models = [
        {
            "titre": "Articles achetés",
            "qs": lambda obj: obj.lignes.select_related("matiere").all(),
            "colonnes": [
                {"label": "Désignation",   "accessor": lambda l: l.matiere,                                                        "css": "td-primary"},
                {"label": "Quantité",      "accessor": "quantite",                                                                       "css": "td-num center"},
                {"label": "Prix unitaire", "accessor": lambda l: f"{int(l.prix_unitaire or 0):,} F CFA".replace(',', ' '),           "css": "td-num right"},
                {"label": "Total HT",      "accessor": lambda l: f"{int(l.total_ligne_ht or 0):,} F CFA".replace(',', ' '),         "css": "td-num right"},
            ],
            "total_value_fn": lambda obj, items: f"{int(obj.total_ht or 0):,} F CFA".replace(',', ' '),
            "total_label": "TOTAL HT",
        }
    ]
    form = _AchatAdminForm
    inlines = [LigneAchatInline]

    list_display = (
        "code_or_temp", "fournisseur", "date_achat", "tva_active",
        "total_ht", "total_tva", "total_ttc",
        "numero_facture", "facture_link",
    )
    list_filter = ("tva_active", "date_achat", "fournisseur")
    search_fields = ("code", "numero_facture", "fournisseur__raison_sociale", "fournisseur__code_prefix")
    date_hierarchy = "date_achat"
    list_per_page = 20

    exclude = ("code", "total_ht", "total_tva", "total_ttc")
    fieldsets = (
        ("Informations", {"fields": ("fournisseur", "date_achat", "tva_active", "depot", "commentaire")}),
        ("Facture fournisseur", {"fields": ("numero_facture", "fichier_facture")}),
    )

    actions = ["regenerer_entrees_stock"]

    # ───── Helpers affichage ─────
    def code_or_temp(self, obj):
        return obj.code or "(en génération)"
    code_or_temp.short_description = "Code d'achat"

    def facture_link(self, obj):
        if obj.fichier_facture:
            return format_html('<a href="{}" target="_blank">Voir/Télécharger</a>', obj.fichier_facture.url)
        return "-"
    facture_link.short_description = "Facture"

    def _imprimer_link(self, obj):
        if obj.pk:
            from django.urls import reverse
            url = reverse("documents:achat_document", args=[obj.pk])
            return format_html(
                '<a href="{}" target="_blank" title="Imprimer le document" '
                'style="background:#1e3a5f;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;text-decoration:none;">🖨 Imprimer</a>',
                url
            )
        return "—"
    _imprimer_link.short_description = "Document"
    _imprimer_link.allow_tags = True

    # ──────────────────────────────────────────────────────────────
    # Gestion du contexte "clos"
    # ──────────────────────────────────────────────────────────────
    def _is_closed_context(self, request, obj=None) -> bool:
        """True si l'exercice de l'objet ou la sélection courante est CLOS uniquement."""
        if obj and getattr(obj, "date_achat", None):
            ex = exercice_for_date(obj.date_achat)
            return bool(ex and ex.statut == ex.Statut.CLOS)
        return selection_is_closed_only(request)

    # --- Permissions dynamiques ---
    def has_view_permission(self, request, obj=None):
        # Toujours autoriser la vue (liste + détail)
        return True

    def has_add_permission(self, request):
        # Interdire l'ajout si contexte clos
        if self._is_closed_context(request):
            return False
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        # Interdire la modification si contexte clos
        if self._is_closed_context(request, obj=obj):
            return False
        return super().has_change_permission(request, obj=obj)

    def has_delete_permission(self, request, obj=None):
        # Interdire suppression si contexte clos
        if self._is_closed_context(request, obj=obj):
            return False
        return super().has_delete_permission(request, obj=obj)

    def get_readonly_fields(self, request, obj=None):
        # Lecture seule complète en contexte clos
        if self._is_closed_context(request, obj=obj):
            return [f.name for f in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)

    def get_actions(self, request):
        # Supprime les actions si contexte clos
        if self._is_closed_context(request):
            return {}
        return super().get_actions(request)

    # ──────────────────────────────────────────────────────────────
    # Liste : filtrage par exercices sélectionnés
    # ──────────────────────────────────────────────────────────────
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("fournisseur")
        try:
            view_name = (resolve(request.path_info).url_name or "")
        except Exception:
            view_name = ""
        # Pas de filtre pour add/change/history
        if view_name.endswith("_add") or view_name.endswith("_change") or view_name.endswith("_history"):
            return qs
        return filter_qs_by_exercices_dates(qs, request, date_field="date_achat")

    # Totaux dynamiques
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)
        try:
            cl = response.context_data["cl"]
            qs = cl.queryset
            agg = qs.aggregate(
                total_ht_sum=Sum("total_ht"),
                total_tva_sum=Sum("total_tva"),
                total_ttc_sum=Sum("total_ttc"),
            )
            response.context_data["custom_totals"] = {
                "HT": agg["total_ht_sum"] or 0,
                "TVA": agg["total_tva_sum"] or 0,
                "TTC": agg["total_ttc_sum"] or 0,
            }
        except Exception:
            pass
        return response

    # ──────────────────────────────────────────────────────────────
    # Sauvegarde + génération mouvements
    # (inchangé mais inutilisable en clos, car has_change_permission=False)
    # ──────────────────────────────────────────────────────────────
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        achat: Achat = form.instance
        achat.recompute_totaux()
        achat.save(update_fields=["total_ht", "total_tva", "total_ttc"])
        ok, info = self._generate_movements_for_achat(achat)
        self._flash_generation_messages(request, ok, info)

    @admin.action(description="(Re)générer les mouvements d'entrée pour l'achat sélectionné")
    def regenerer_entrees_stock(self, request, queryset):
        total_ok, total_created, total_updated, total_deleted = 0, 0, 0, 0
        details_errors = []
        for achat in queryset:
            ok, info = self._generate_movements_for_achat(achat)
            if ok:
                total_ok += 1
                total_created += info.get("created", 0)
                total_updated += info.get("updated", 0)
                total_deleted += info.get("deleted", 0)
            else:
                details_errors.append(f"{achat} → {info.get('error')}")
        if total_ok:
            messages.success(
                request,
                f"{total_ok} achat(s) traités. Entrées créées: {total_created}, mises à jour: {total_updated}, supprimées: {total_deleted}.",
            )
        if details_errors:
            for line in details_errors:
                messages.warning(request, f"⚠️ {line}")

    def _generate_movements_for_achat(self, achat: Achat):
        MouvementStock = apps.get_model("inventory", "MouvementStock")
        LigneAchat = apps.get_model("purchasing", "LigneAchat")

        try:
            exo = exercice_for_date(achat.date_achat)
            depot = getattr(achat, "depot", None)
            if not depot:
                return False, {"error": "Dépôt manquant sur l'achat."}

            ref = achat.code or ""
            created, updated, deleted = 0, 0, 0
            wanted_dt = _aware_midnight(achat.date_achat)

            for ligne in LigneAchat.objects.filter(achat=achat):
                if not ligne.matiere_id or (ligne.quantite or 0) <= 0:
                    deleted += MouvementStock.objects.filter(
                        source_doc_type="purchasing.LigneAchat",
                        source_doc_id=ligne.id,
                    ).delete()[0]
                    continue

                mvt, was_created = MouvementStock.objects.get_or_create(
                    source_doc_type="purchasing.LigneAchat",
                    source_doc_id=ligne.id,
                    defaults=dict(
                        type="ENTREE",
                        date=wanted_dt,
                        exercice=exo,
                        matiere=ligne.matiere,
                        depot=depot,
                        quantite=ligne.quantite,
                        cout_unitaire=ligne.prix_unitaire or Decimal("0"),
                        reference=ref,
                        commentaire=f"Entrée de stock suite à l'achat {achat.code}",
                    ),
                )

                need = False
                if mvt.date != wanted_dt:
                    mvt.date = wanted_dt; need = True
                if mvt.exercice_id != (exo.id if exo else None):
                    mvt.exercice = exo; need = True
                if mvt.depot_id != depot.id:
                    mvt.depot = depot; need = True
                if mvt.matiere_id != ligne.matiere_id:
                    mvt.matiere = ligne.matiere; need = True
                if mvt.quantite != ligne.quantite:
                    mvt.quantite = ligne.quantite; need = True
                cu = ligne.prix_unitaire or Decimal("0")
                if mvt.cout_unitaire != cu:
                    mvt.cout_unitaire = cu; need = True
                if (mvt.reference or "") != ref:
                    mvt.reference = ref; need = True

                if need:
                    mvt.save()
                    if was_created:
                        created += 1
                    else:
                        updated += 1
                else:
                    if was_created:
                        created += 1

            return True, {"created": created, "updated": updated, "deleted": deleted}
        except Exception as e:
            return False, {"error": str(e)}

    def _flash_generation_messages(self, request, ok: bool, info: dict):
        if ok:
            c, u, d = info.get("created", 0), info.get("updated", 0), info.get("deleted", 0)
            if c or u or d:
                messages.success(request, f"Entrées de stock — créées: {c}, mises à jour: {u}, supprimées: {d}.")
            else:
                messages.info(request, "Aucune ligne exploitable → aucun mouvement créé.")
        else:
            messages.warning(request, f"⚠️ Mouvements non créés: {info.get('error')}")
