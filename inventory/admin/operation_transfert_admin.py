# inventory/admin/operation_transfert_admin.py
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
from inventory.models import OperationTransfert, LigneOperationTransfert
from core.utils.exercices import (
    filter_qs_by_exercices_dates,
    selection_is_closed_only,
    exercice_for_date,
)


def _aware_midnight(d):
    if not d:
        return timezone.now()
    return datetime.combine(d, datetime.min.time(), tzinfo=timezone.get_current_timezone())


def stock_disponible_depot(matiere_id, depot_id, date_operation):
    """
    Stock d'un dépôt à une date:
      + ENTREE (depot)
      + AJUSTEMENT (depot)  (considéré comme +)
      + TRANSFERT entrants (destination_depot)
      - SORTIE (depot)
      - TRANSFERT sortants (source_depot)

    NB: on suppose quantite toujours positive (comme tes validations).
    """
    MouvementStock = apps.get_model("inventory", "MouvementStock")
    dt = _aware_midnight(date_operation)

    base = MouvementStock.objects.filter(date__lte=dt, matiere_id=matiere_id)

    entrees = base.filter(type="ENTREE", depot_id=depot_id).aggregate(s=Sum("quantite"))["s"] or Decimal("0")
    ajust = base.filter(type="AJUSTEMENT", depot_id=depot_id).aggregate(s=Sum("quantite"))["s"] or Decimal("0")
    sorties = base.filter(type="SORTIE", depot_id=depot_id).aggregate(s=Sum("quantite"))["s"] or Decimal("0")

    tr_in = base.filter(type="TRANSFERT", destination_depot_id=depot_id).aggregate(s=Sum("quantite"))["s"] or Decimal("0")
    tr_out = base.filter(type="TRANSFERT", source_depot_id=depot_id).aggregate(s=Sum("quantite"))["s"] or Decimal("0")

    return (entrees + ajust + tr_in) - (sorties + tr_out)


class _OperationTransfertForm(forms.ModelForm):
    class Meta:
        model = OperationTransfert
        fields = "__all__"


class LigneOperationTransfertInline(admin.TabularInline):
    model = LigneOperationTransfert
    extra = 1
    fields = ("matiere", "quantite", "cout_unitaire", "commentaire")


@admin.register(OperationTransfert)
class OperationTransfertAdmin(DetailViewMixin, AgentRestrictedMixin, admin.ModelAdmin):
    form = _OperationTransfertForm
    detail_print_url_name = "documents:transfert_document"
    detail_print_buttons = [
        {"url_name": "documents:transfert_document", "label": "Bon de mutation", "icon": "🖨"},
        {"url_name": "documents:transfert_bon_entree", "label": "Bon d'entrée (Modèle 1)", "icon": "📋"},
    ]
    detail_fields_sections = [
        {
            "titre": "Informations du transfert",
            "fields": [
                ("Code",              "code"),
                ("Motif",             lambda o: o.get_motif_display()),
                ("Date opération", lambda o: o.date_operation.strftime("%d/%m/%Y") if o.date_operation else "—"),
                ("Dépôt source",    "depot_source"),
                ("Dépôt destination", "depot_destination"),
                ("Valeur totale",     lambda o: f"{int(o.total_valeur or 0):,} F CFA".replace(",", " "), "montant"),
            ],
        },
        {
            "titre": "Description",
            "obs_field": "description",
            "fields": [],
        },
    ]
    detail_inline_models = [
        {
            "titre": "Matières transférées",
            "qs": lambda obj: obj.lignes.select_related("matiere").all(),
            "colonnes": [
                {"label": "Désignation",   "accessor": lambda l: l.matiere,                                             "css": "td-primary"},
                {"label": "Quantité",      "accessor": "quantite",                                                            "css": "td-num center"},
                {"label": "Coût unitaire", "accessor": lambda l: f"{int(l.cout_unitaire or 0):,} F CFA".replace(",", " "), "css": "td-num right"},
                {"label": "Commentaire",   "accessor": lambda l: getattr(l, "commentaire", "") or "—",                   "css": ""},
            ],
            "total_value_fn": lambda obj, items: f"{int(obj.total_valeur or 0):,} F CFA".replace(",", " "),
            "total_label": "TOTAL VALEUR",
        }
    ]
    inlines = [LigneOperationTransfertInline]

    list_display = ("code_or_temp", "date_operation", "motif", "depot_source", "depot_destination", "total_valeur")
    list_filter = ("motif", "depot_source", "depot_destination", "date_operation")
    search_fields = ("code", "description")
    date_hierarchy = "date_operation"

    fieldsets = (
        ("Informations", {"fields": ("code", "date_operation", "motif", "depot_source", "depot_destination", "description")}),
        ("Valorisation", {"fields": ("total_valeur",)}),
    )
    readonly_fields = ("code", "total_valeur")

    actions = ["regenerer_mouvements_transfert"]

    def code_or_temp(self, obj):
        return obj.code or "(en génération)"
    code_or_temp.short_description = "Code"

    def _imprimer_link(self, obj):
        if obj.pk:
            from django.urls import reverse
            url = reverse("documents:transfert_document", args=[obj.pk])
            return format_html(
                '<a href="{}" target="_blank" title="Imprimer le document" '
                'style="background:#1e3a5f;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;text-decoration:none;">🖨 Imprimer</a>',
                url
            )
        return "—"
    _imprimer_link.short_description = "Bon mutation"
    _imprimer_link.allow_tags = True

    # ---------- Exercices clos ----------
    def _is_closed_context(self, request, obj=None) -> bool:
        if obj and getattr(obj, "date_operation", None):
            ex = exercice_for_date(obj.date_operation)
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

    def get_actions(self, request):
        if self._is_closed_context(request):
            return {}
        return super().get_actions(request)

    # ---------- Filtre par exercices ----------
    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related("depot_source", "depot_destination")
        try:
            view_name = (resolve(request.path_info).url_name or "")
        except Exception:
            view_name = ""
        if view_name.endswith("_add") or view_name.endswith("_change") or view_name.endswith("_history"):
            return qs
        return filter_qs_by_exercices_dates(qs, request, date_field="date_operation")

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)
        try:
            cl = response.context_data["cl"]
            agg = cl.queryset.aggregate(total=Sum("total_valeur"))
            response.context_data["custom_totals"] = {"VALEUR": agg["total"] or 0}
        except Exception:
            pass
        return response

    # ---------- Génération mouvements ----------
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        op: OperationTransfert = form.instance

        op.recompute_totaux()
        op.save(update_fields=["total_valeur"])

        ok, info = self._sync_mouvements(op)
        self._flash(request, ok, info)

    @admin.action(description="(Re)générer les mouvements TRANSFERT pour les opérations sélectionnées")
    def regenerer_mouvements_transfert(self, request, queryset):
        okn = c = u = d = 0
        errs = []
        for op in queryset:
            ok, info = self._sync_mouvements(op)
            if ok:
                okn += 1
                c += info.get("created", 0)
                u += info.get("updated", 0)
                d += info.get("deleted", 0)
            else:
                errs.append(f"{op} → {info.get('error')}")
        if okn:
            messages.success(request, f"{okn} opération(s) OK. Créés: {c}, MAJ: {u}, supprimés: {d}.")
        for e in errs:
            messages.warning(request, f"⚠️ {e}")

    def _sync_mouvements(self, op: OperationTransfert):
        MouvementStock = apps.get_model("inventory", "MouvementStock")
        Ligne = apps.get_model("inventory", "LigneOperationTransfert")

        try:
            exo = exercice_for_date(op.date_operation)
            dt = _aware_midnight(op.date_operation)
            ref = op.code or ""

            created = updated = deleted = 0

            # 1) contrôle stock par ligne au dépôt source
            for ligne in Ligne.objects.filter(operation=op):
                if not ligne.matiere_id or (ligne.quantite or 0) <= 0:
                    continue
                dispo = stock_disponible_depot(ligne.matiere_id, op.depot_source_id, op.date_operation)
                if dispo < (ligne.quantite or 0):
                    return False, {
                        "error": f"Stock insuffisant au dépôt source ({op.depot_source}) pour {ligne.matiere}. "
                                 f"Dispo={dispo} / Demandé={ligne.quantite}"
                    }

            # 2) sync 1 mouvement TRANSFERT par ligne
            for ligne in Ligne.objects.filter(operation=op):
                if not ligne.matiere_id or (ligne.quantite or 0) <= 0:
                    deleted += MouvementStock.objects.filter(
                        source_doc_type="inventory.LigneOperationTransfert",
                        source_doc_id=ligne.id,
                    ).delete()[0]
                    continue

                mvt, was_created = MouvementStock.objects.get_or_create(
                    source_doc_type="inventory.LigneOperationTransfert",
                    source_doc_id=ligne.id,
                    defaults=dict(
                        type="TRANSFERT",
                        date=dt,
                        exercice=exo,
                        matiere=ligne.matiere,
                        depot=None,  # doit être vide pour TRANSFERT (cf. clean)
                        source_depot=op.depot_source,
                        destination_depot=op.depot_destination,
                        quantite=ligne.quantite,
                        cout_unitaire=ligne.cout_unitaire or Decimal("0"),
                        reference=ref,
                        commentaire=f"Transfert {op.code} — {op.depot_source} → {op.depot_destination}",
                    ),
                )

                need = False
                if mvt.type != "TRANSFERT":
                    mvt.type = "TRANSFERT"; need = True
                if mvt.date != dt:
                    mvt.date = dt; need = True
                if mvt.exercice_id != (exo.id if exo else None):
                    mvt.exercice = exo; need = True
                if mvt.matiere_id != ligne.matiere_id:
                    mvt.matiere = ligne.matiere; need = True
                if mvt.depot_id is not None:
                    mvt.depot = None; need = True
                if mvt.source_depot_id != op.depot_source_id:
                    mvt.source_depot = op.depot_source; need = True
                if mvt.destination_depot_id != op.depot_destination_id:
                    mvt.destination_depot = op.depot_destination; need = True
                if mvt.quantite != ligne.quantite:
                    mvt.quantite = ligne.quantite; need = True
                cu = ligne.cout_unitaire or Decimal("0")
                if mvt.cout_unitaire != cu:
                    mvt.cout_unitaire = cu; need = True
                if (mvt.reference or "") != ref:
                    mvt.reference = ref; need = True

                if need:
                    mvt.save()
                    updated += 1
                if was_created:
                    created += 1

            return True, {"created": created, "updated": updated, "deleted": deleted}

        except Exception as e:
            return False, {"error": str(e)}

    def _flash(self, request, ok, info):
        if ok:
            messages.success(
                request,
                f"Mouvements TRANSFERT OK — créés: {info.get('created',0)}, MAJ: {info.get('updated',0)}, supprimés: {info.get('deleted',0)}."
            )
        else:
            messages.warning(request, f"⚠️ Mouvements non créés: {info.get('error')}")
