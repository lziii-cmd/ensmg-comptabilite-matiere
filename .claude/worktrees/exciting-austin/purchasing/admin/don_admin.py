# purchasing/admin/don_admin.py
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
from purchasing.models import Don, LigneDon
from core.utils.exercices import (
    filter_qs_by_exercices_dates,
    selection_is_closed_only,
    exercice_for_date,
)


# ──────────────────────────────────────────────────────────────
# Utilitaires
# ──────────────────────────────────────────────────────────────
def _aware_midnight(d):
    """Datetime tz-aware à minuit pour la date du don."""
    if not d:
        return timezone.now()
    return datetime.combine(d, datetime.min.time(), tzinfo=timezone.get_current_timezone())


# ──────────────────────────────────────────────────────────────
# Formulaire admin : dépôt obligatoire
# ──────────────────────────────────────────────────────────────
class _DonAdminForm(forms.ModelForm):
    class Meta:
        model = Don
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "depot" in self.fields:
            self.fields["depot"].required = True


# ──────────────────────────────────────────────────────────────
# Inline lignes de don
# ──────────────────────────────────────────────────────────────
class LigneDonInline(admin.TabularInline):
    model = LigneDon
    extra = 1
    fields = ("matiere", "quantite", "prix_unitaire", "total_ligne_display", "observation")
    readonly_fields = ("total_ligne_display",)

    def total_ligne_display(self, obj):
        if obj and obj.pk:
            return f"{obj.total_ligne:,.0f} FCFA"
        return "—"
    total_ligne_display.short_description = "Total"


# ──────────────────────────────────────────────────────────────
# Admin Don
# ──────────────────────────────────────────────────────────────
@admin.register(Don)
class DonAdmin(DetailViewMixin, AgentRestrictedMixin, admin.ModelAdmin):
    detail_print_url_name = "documents:don_document"
    detail_print_buttons = [
        {"url_name": "documents:don_document",           "label": "PVR", "icon": "🖨"},
        {"url_name": "documents:don_bon_entree_modele1", "label": "BE",  "icon": "📋"},
    ]
    detail_fields_sections = [
        {
            "titre": "Informations générales",
            "fields": [
                ("Code",         "code"),
                ("Donateur",     "donateur"),
                ("Date du don",  lambda o: o.date_don.strftime("%d/%m/%Y") if o.date_don else "—"),
                ("Dépôt",        "depot"),
                ("N° pièce",     "numero_piece"),
                ("Valeur totale",lambda o: f"{int(o.total_valeur or 0):,} F CFA".replace(',', ' '), "montant"),
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
            "titre": "Articles reçus en don",
            "qs": lambda obj: obj.lignes.select_related("matiere").all(),
            "colonnes": [
                {"label": "Désignation",  "accessor": lambda l: l.matiere,                                                       "css": "td-primary"},
                {"label": "Quantité",     "accessor": "quantite",                                                                      "css": "td-num center"},
                {"label": "Valeur unit.", "accessor": lambda l: f"{int(l.prix_unitaire or 0):,} F CFA".replace(',', ' '),        "css": "td-num right"},
                {"label": "Total",        "accessor": lambda l: f"{int(l.total_ligne or 0):,} F CFA".replace(',', ' '),          "css": "td-num right"},
            ],
            "total_value_fn": lambda obj, items: f"{int(obj.total_valeur or 0):,} F CFA".replace(',', ' '),
            "total_label": "TOTAL VALEUR",
        }
    ]
    form = _DonAdminForm
    inlines = [LigneDonInline]

    # LISTE
    list_display = (
        "code_or_temp",
        "donateur",
        "date_don",
        "depot",
        "total_valeur",
        "numero_piece",
        "piece_link",
    )
    list_filter = ("date_don", "donateur", "depot")
    search_fields = ("code", "donateur__raison_sociale", "numero_piece")
    date_hierarchy = "date_don"

    # FORMULAIRE
    exclude = ("code", "total_valeur")
    fieldsets = (
        ("Information du don", {"fields": ("donateur", "date_don", "depot", "commentaire")}),
        ("Pièce justificative", {"fields": ("numero_piece", "fichier_piece")}),
    )

    actions = ["regenerer_entrees_stock"]

    # ───── Helpers affichage ─────
    def code_or_temp(self, obj):
        return obj.code or "(en génération)"
    code_or_temp.short_description = "Code du don"

    def piece_link(self, obj):
        if obj.fichier_piece:
            return format_html('<a href="{}" target="_blank">Voir/Télécharger</a>', obj.fichier_piece.url)
        return "-"
    piece_link.short_description = "Pièce"

    def _imprimer_link(self, obj):
        if obj.pk:
            from django.urls import reverse
            url = reverse("documents:don_document", args=[obj.pk])
            return format_html(
                '<a href="{}" target="_blank" title="Imprimer le document" '
                'style="background:#1e3a5f;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;text-decoration:none;">🖨 Imprimer</a>',
                url
            )
        return "—"
    _imprimer_link.short_description = "Bon don"
    _imprimer_link.allow_tags = True

    # ──────────────────────────────────────────────────────────────
    # Gestion du contexte "clos"
    # ──────────────────────────────────────────────────────────────
    def _is_closed_context(self, request, obj=None) -> bool:
        """
        True si :
        - le don (obj) appartient à un exercice CLOS, ou
        - la sélection d'exercices actuelle dans la liste est "clos uniquement".
        """
        if obj and getattr(obj, "date_don", None):
            ex = exercice_for_date(obj.date_don)
            return bool(ex and ex.statut == ex.Statut.CLOS)
        return selection_is_closed_only(request)

    # Permissions dynamiques
    def has_view_permission(self, request, obj=None):
        # On autorise toujours la vue (liste + détail)
        return True

    def has_add_permission(self, request):
        # Interdit l'ajout si on a sélectionné uniquement des exercices clos
        if self._is_closed_context(request):
            return False
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        # Interdit la modification si l'exercice du don est clos
        if self._is_closed_context(request, obj=obj):
            return False
        return super().has_change_permission(request, obj=obj)

    def has_delete_permission(self, request, obj=None):
        # Interdit la suppression si exercice clos
        if self._is_closed_context(request, obj=obj):
            return False
        return super().has_delete_permission(request, obj=obj)

    def get_readonly_fields(self, request, obj=None):
        # En contexte clos : tous les champs en lecture seule
        if self._is_closed_context(request, obj=obj):
            return [f.name for f in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)

    def get_actions(self, request):
        # Pas d'actions possibles en contexte clos
        if self._is_closed_context(request):
            return {}
        return super().get_actions(request)

    # ──────────────────────────────────────────────────────────────
    # Liste : filtrage par exercices sélectionnés
    # ──────────────────────────────────────────────────────────────
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("donateur", "depot")
        try:
            view_name = (resolve(request.path_info).url_name or "")
        except Exception:
            view_name = ""
        # Pas de filtre pour add/change/history
        if view_name.endswith("_add") or view_name.endswith("_change") or view_name.endswith("_history"):
            return qs
        return filter_qs_by_exercices_dates(qs, request, date_field="date_don")

    # Totaux dynamiques (optionnel – comme pour Achat)
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)
        try:
            cl = response.context_data["cl"]
            qs = cl.queryset
            agg = qs.aggregate(total_valeur_sum=Sum("total_valeur"))
            response.context_data["custom_totals"] = {
                "VALEUR": agg["total_valeur_sum"] or Decimal("0"),
            }
        except Exception:
            pass
        return response

    # ──────────────────────────────────────────────────────────────
    # Sauvegarde + génération mouvements
    # (non utilisée en contexte clos car has_change_permission=False)
    # ──────────────────────────────────────────────────────────────
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        don: Don = form.instance
        don.recompute_totaux()
        don.save(update_fields=["total_valeur"])
        ok, info = self._generate_movements_for_don(don)
        self._flash_generation_messages(request, ok, info)

    @admin.action(description="(Re)générer les entrées de stock pour le don sélectionné")
    def regenerer_entrees_stock(self, request, queryset):
        total_ok, total_created, total_updated, total_deleted = 0, 0, 0, 0
        details_errors = []
        for don in queryset:
            ok, info = self._generate_movements_for_don(don)
            if ok:
                total_ok += 1
                total_created += info.get("created", 0)
                total_updated += info.get("updated", 0)
                total_deleted += info.get("deleted", 0)
            else:
                details_errors.append(f"{don} → {info.get('error')}")
        if total_ok:
            messages.success(
                request,
                f"{total_ok} don(s) traités. Entrées créées: {total_created}, "
                f"mises à jour: {total_updated}, supprimées: {total_deleted}.",
            )
        for line in details_errors:
            messages.warning(request, f"⚠️ {line}")

    def _generate_movements_for_don(self, don: Don):
        MouvementStock = apps.get_model("inventory", "MouvementStock")
        LigneDon = apps.get_model("purchasing", "LigneDon")
        try:
            exo = exercice_for_date(don.date_don)
            depot = getattr(don, "depot", None)
            if not depot:
                return False, {"error": "Dépôt manquant sur le don."}

            ref = don.code or ""
            created = updated = deleted = 0
            wanted_dt = _aware_midnight(don.date_don)

            for ligne in LigneDon.objects.filter(don=don):
                if not ligne.matiere_id or (ligne.quantite or 0) <= 0:
                    deleted += MouvementStock.objects.filter(
                        source_doc_type="purchasing.LigneDon",
                        source_doc_id=ligne.id,
                    ).delete()[0]
                    continue

                mvt, was_created = MouvementStock.objects.get_or_create(
                    source_doc_type="purchasing.LigneDon",
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
                        commentaire=f"Entrée de stock suite au don {don.code}",
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
            messages.warning(request, f"⚠️ Entrées non créées: {info.get('error')}")
