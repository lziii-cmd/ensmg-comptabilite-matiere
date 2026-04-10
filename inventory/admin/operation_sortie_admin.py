# inventory/admin/operation_sortie_admin.py

from decimal import Decimal
from datetime import datetime

from django import forms
from django.apps import apps
from django.contrib import admin, messages
from django.db.models import Sum
from django.urls import resolve
from django.utils import timezone
        # NB: verification exercise logic etc. same as before
from django.utils.html import format_html

from core.admin.mixins import AgentRestrictedMixin
from core.admin.detail_view_mixin import DetailViewMixin
from inventory.models import OperationSortie, LigneOperationSortie
from core.utils.exercices import (
    filter_qs_by_exercices_dates,
    selection_is_closed_only,
    exercice_for_date,
)


# ----------------------------
# Utils
# ----------------------------
def _aware_midnight(d):
    if not d:
        return timezone.now()
    return datetime.combine(d, datetime.min.time(), tzinfo=timezone.get_current_timezone())


# ----------------------------
# Form
# ----------------------------
class _OperationSortieAdminForm(forms.ModelForm):
    class Meta:
        model = OperationSortie
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "depot" in self.fields:
            self.fields["depot"].required = True


# ----------------------------
# Inline
# ----------------------------
class LigneOperationSortieInline(admin.TabularInline):
    model = LigneOperationSortie
    extra = 1
    fields = ("matiere", "quantite", "prix_unitaire", "commentaire")


# ----------------------------
# Admin OperationSortie
# ----------------------------
@admin.register(OperationSortie)
class OperationSortieAdmin(DetailViewMixin, AgentRestrictedMixin, admin.ModelAdmin):
    detail_print_url_name = "documents:sortie_document"
    detail_print_buttons = [
        {"url_name": "documents:sortie_document", "label": "Bon de sortie", "icon": "🖨"},
    ]
    detail_fields_sections = [
        {
            "titre": "Informations de l'opération",
            "fields": [
                ("Code",         "code"),
                ("Type sortie",  lambda o: o.get_type_sortie_display()),
                ("Date sortie",  lambda o: o.date_sortie.strftime("%d/%m/%Y") if o.date_sortie else "—"),
                ("Dépôt",        "depot"),
                ("Motif",        "motif_principal"),
                ("N° document",  "numero_document"),
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
            "titre": "Articles sortis",
            "qs": lambda obj: obj.lignes.select_related("matiere").all(),
            "colonnes": [
                {"label": "Désignation",   "accessor": lambda l: l.matiere,                                                          "css": "td-primary"},
                {"label": "Quantité",      "accessor": "quantite",                                                                         "css": "td-num center"},
                {"label": "Prix unitaire", "accessor": lambda l: f"{int(l.prix_unitaire or 0):,} F CFA".replace(',', ' '),           "css": "td-num right"},
                {"label": "Total",         "accessor": lambda l: f"{int((l.prix_unitaire or 0) * l.quantite):,} F CFA".replace(',', ' '), "css": "td-num right"},
            ],
            "total_value_fn": lambda obj, items: f"{int(obj.total_valeur or 0):,} F CFA".replace(',', ' '),
            "total_label": "TOTAL VALEUR",
        }
    ]
    form = _OperationSortieAdminForm
    inlines = [LigneOperationSortieInline]

    list_display = (
        "code_or_temp",
        "date_sortie",
        "type_sortie",
        "depot",
        "total_valeur",
    )
    list_filter = ("type_sortie", "depot", "date_sortie")
    search_fields = ("code", "motif_principal", "commentaire", "numero_document")
    date_hierarchy = "date_sortie"

    fieldsets = (
        ("Informations générales", {
            "fields": (
                "code",
                "date_sortie",
                "type_sortie",
                "depot",
                "motif_principal",
                "commentaire",
            ),
        }),
        ("Justificatif", {
            "fields": ("numero_document", "fichier_document", "document_link"),
        }),
        ("Valorisation", {
            "fields": ("total_valeur",),
        }),
    )
    readonly_fields = ("code", "total_valeur", "document_link")

    actions = ["regenerer_operations_sortie"]

    # ------------- Affichage -------------
    def code_or_temp(self, obj):
        return obj.code or "(en génération)"
    code_or_temp.short_description = "Code sortie"

    def document_link(self, obj):
        if obj.fichier_document:
            return format_html('<a href="{}" target="_blank">Voir/Télécharger</a>', obj.fichier_document.url)
        return "-"
    document_link.short_description = "Pièce justificative"

    def _imprimer_link(self, obj):
        if obj.pk:
            from django.urls import reverse
            url = reverse("documents:sortie_document", args=[obj.pk])
            return format_html(
                '<a href="{}" target="_blank" title="Imprimer le bon de sortie" '
                'style="background:#1e3a5f;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;text-decoration:none;">🖨 Imprimer</a>',
                url
            )
        return "—"
    _imprimer_link.short_description = "Bon sortie"
    _imprimer_link.allow_tags = True

    # ------------- Contexte exercices / clos -------------

    def _is_closed_context(self, request, obj=None) -> bool:
        """
        True si :
        - l'exercice correspondant à la date de l'objet est clos, ou
        - la sélection d'exercices dans la barre "Exercices" ne contient QUE des exercices clos.
        """
        if obj and getattr(obj, "date_sortie", None):
            ex = exercice_for_date(obj.date_sortie)
            return bool(ex and ex.statut == ex.Statut.CLOS)
        return selection_is_closed_only(request)

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request):
        if self._is_closed_context(request):
            return False
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if self._is_closed_context(request, obj=obj):
            return False
        return super().has_change_permission(request, obj=obj)

    def has_delete_permission(self, request, obj=None):
        if self._is_closed_context(request, obj=obj):
            return False
        return super().has_delete_permission(request, obj=obj)

    def get_readonly_fields(self, request, obj=None):
        if self._is_closed_context(request, obj=obj):
            # tout en lecture seule en contexte clos
            return [f.name for f in self.model._meta.fields] + ["document_link"]
        return super().get_readonly_fields(request, obj)

    def get_actions(self, request):
        if self._is_closed_context(request):
            return {}
        return super().get_actions(request)

    # ------------- Filtrage par exercices -------------

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("depot")
        try:
            view_name = (resolve(request.path_info).url_name or "")
        except Exception:
            view_name = ""
        if view_name.endswith("_add") or view_name.endswith("_change") or view_name.endswith("_history"):
            return qs
        # Filtrage sur base de la date de sortie
        return filter_qs_by_exercices_dates(qs, request, date_field="date_sortie")

    # Totaux dynamiques en bas de liste
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)
        try:
            cl = response.context_data["cl"]
            qs = cl.queryset
            agg = qs.aggregate(
                total_valeur_sum=Sum("total_valeur"),
            )
            response.context_data["custom_totals"] = {
                "VALEUR": agg["total_valeur_sum"] or 0,
            }
        except Exception:
            pass
        return response

    # ------------- Génération mouvements de stock -------------

    def save_related(self, request, form, formsets, change):
        """
        Après sauvegarde des lignes :
        - recalcul des totaux
        - génération / mise à jour des MouvementStock de type SORTIE
        """
        super().save_related(request, form, formsets, change)

        operation: OperationSortie = form.instance
        operation.recompute_totaux()
        operation.save(update_fields=["total_valeur"])

        ok, info = self._generate_movements_for_operation(operation)
        self._flash_generation_messages(request, ok, info)

    @admin.action(description="(Re)générer les mouvements de sortie pour les opérations sélectionnées")
    def regenerer_operations_sortie(self, request, queryset):
        total_ok, total_created, total_updated, total_deleted = 0, 0, 0, 0
        errors = []
        for operation in queryset:
            ok, info = self._generate_movements_for_operation(operation)
            if ok:
                total_ok += 1
                total_created += info.get("created", 0)
                total_updated += info.get("updated", 0)
                total_deleted += info.get("deleted", 0)
            else:
                errors.append(f"{operation} → {info.get('error')}")
        if total_ok:
            messages.success(
                request,
                f"{total_ok} opération(s) traitée(s). "
                f"Sorties créées: {total_created}, mises à jour: {total_updated}, supprimées: {total_deleted}.",
            )
        for e in errors:
            messages.warning(request, f"⚠️ {e}")

    def _generate_movements_for_operation(self, operation: OperationSortie):
        """
        Crée / met à jour / supprime les mouvements de stock de type SORTIE
        liés aux lignes d'une opération de sortie.

        - type = "SORTIE"
        - date = date_sortie (tz-aware)
        - exercice = exercice couvrant la date
        - quantite = quantite de la ligne
        - référence = code d'opération

        ⚠️ Ici on NE FAIT PAS encore de contrôle fin de stock.
        On se contente de synchroniser les mouvements à partir des lignes.
        """
        MouvementStock = apps.get_model("inventory", "MouvementStock")
        LigneOperationSortie = apps.get_model("inventory", "LigneOperationSortie")

        try:
            exo = exercice_for_date(operation.date_sortie)
            depot = getattr(operation, "depot", None)
            if not depot:
                return False, {"error": "Dépôt manquant sur l'opération de sortie."}

            ref = operation.code or ""
            created = updated = deleted = 0
            wanted_dt = _aware_midnight(operation.date_sortie)

            for ligne in LigneOperationSortie.objects.filter(operation=operation):
                if not ligne.matiere_id or (ligne.quantite or 0) <= 0:
                    # Ligne non exploitable → suppression des mouvements existants
                    deleted += MouvementStock.objects.filter(
                        source_doc_type="inventory.LigneOperationSortie",
                        source_doc_id=ligne.id,
                    ).delete()[0]
                    continue

                mvt, was_created = MouvementStock.objects.get_or_create(
                    source_doc_type="inventory.LigneOperationSortie",
                    source_doc_id=ligne.id,
                    defaults=dict(
                        type="SORTIE",
                        date=wanted_dt,
                        exercice=exo,
                        matiere=ligne.matiere,
                        depot=depot,
                        quantite=ligne.quantite,
                        cout_unitaire=ligne.prix_unitaire or Decimal("0"),
                        reference=ref,
                        commentaire=(
                            f"Sortie stock {operation.code} "
                            f"({operation.get_type_sortie_display()})"
                        ),
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
                messages.success(
                    request,
                    f"Mouvements de sortie — créés: {c}, mis à jour: {u}, supprimés: {d}.",
                )
            else:
                messages.info(request, "Aucune ligne exploitable → aucun mouvement créé.")
        else:
            messages.warning(request, f"⚠️ Mouvements non créés: {info.get('error')}")
