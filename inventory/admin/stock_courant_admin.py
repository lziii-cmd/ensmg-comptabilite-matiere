# inventory/admin/stock_courant_admin.py
from decimal import Decimal
from django.contrib import admin
from django.db.models import Sum, Min, DecimalField, OuterRef, Subquery, F, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.utils.html import format_html
from inventory.models import StockCourant
from core.admin.detail_view_mixin import DetailViewMixin


# ──────────────────────────────────────────────────────────────
# Vue détaillée par dépôt (existante)
# ──────────────────────────────────────────────────────────────
@admin.register(StockCourant)
class StockCourantAdmin(DetailViewMixin, admin.ModelAdmin):
    list_display = (
        "exercice", "matiere", "depot",
        "stock_initial_qte", "stock_initial_cu",
        "quantite", "cump", "valeur",
    )
    list_filter = ("exercice", "matiere", "depot")
    search_fields = ("matiere__code_court", "matiere__designation", "depot__nom")
    readonly_fields = (
        "stock_initial_qte", "stock_initial_cu",
        "quantite", "cump",
    )
    ordering = ("matiere", "depot")

    detail_fields_sections = [
        {
            "titre": "Stock courant",
            "fields": [
                ("Exercice",           "exercice"),
                ("Matière",            "matiere"),
                ("Dépôt",              "depot"),
                ("Qté stock initial",  lambda o: str(int(o.stock_initial_qte or 0))),
                ("Coût unitaire init.","stock_initial_cu"),
                ("Quantité actuelle",  lambda o: str(int(o.quantite or 0))),
                ("CUMP",               lambda o: f"{int(o.cump or 0):,} F CFA".replace(",", "\u202f") if o.cump else "—", "montant"),
                ("Valeur stock",       lambda o: f"{int(o.valeur or 0):,} F CFA".replace(",", "\u202f"), "montant"),
            ],
        },
    ]


# ──────────────────────────────────────────────────────────────
# Proxy pour la vue "Stock actuel agrégé" (tous dépôts)
# ──────────────────────────────────────────────────────────────
class StockCourantProxy(StockCourant):
    """Vue proxy sans table propre — utilisée pour l'agrégation."""
    class Meta:
        proxy = True
        verbose_name = "Stock actuel (tous dépôts)"
        verbose_name_plural = "Stock actuel (tous dépôts)"


@admin.register(StockCourantProxy)
class StockActuelAdmin(DetailViewMixin, admin.ModelAdmin):
    """
    Agrège le stock de toutes les dépôts par matière + exercice.
    Affiche : code_court | designation | type | quantité totale | valeur totale | seuil | alerte.
    """
    list_display = (
        "_detail_link",
        "code_court_display",
        "designation_display",
        "type_matiere_display",
        "exercice",
        "quantite_totale",
        "valeur_totale",
        "seuil_display",
        "alerte_display",
    )

    detail_fields_sections = [
        {
            "titre": "Matière",
            "fields": [
                ("Code",          lambda o: o.matiere.code_court),
                ("Désignation",   lambda o: o.matiere.designation),
                ("Type",          lambda o: (
                    "2e groupe — Consomptible (CONSOMMABLE)" if o.matiere.type_matiere == "consommable"
                    else "1er groupe — Durable (RÉUTILISABLE)" if o.matiere.type_matiere == "reutilisable"
                    else str(o.matiere.type_matiere or "—")
                )),
                ("Unité",         lambda o: o.matiere.unite or "—"),
                ("Seuil minimum", lambda o: str(int(o.matiere.seuil_min or 0))),
            ],
        },
        {
            "titre": "Stock agrégé (tous dépôts)",
            "fields": [
                ("Exercice",        "exercice"),
                ("Quantité totale", lambda o: str(int(o.total_qte or 0))),
                ("Valeur totale",   lambda o: f"{int(o.total_val or 0):,} F CFA".replace(",", "\u202f"), "montant"),
                ("Statut",          lambda o: (
                    "🔴 RUPTURE" if (o.total_qte or 0) <= 0
                    else "⚠️ ALERTE" if (o.total_qte or 0) <= (o.matiere.seuil_min or 0)
                    else "✅ OK"
                )),
            ],
        },
    ]
    list_filter = ("exercice", "matiere__type_matiere", "matiere__sous_categorie__categorie")
    search_fields = ("matiere__code_court", "matiere__designation")
    ordering = ("matiere__code_court",)

    def get_queryset_for_detail(self, request):
        """Le detail doit utiliser le queryset annoté (total_qte, total_val)."""
        return self.get_queryset(request)

    # Lecture seule — pas d'ajout/modification via cette vue agrégée
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        """
        Retourne UNE ligne par (exercice, matiere) avec la somme des stocks.
        Stratégie : on récupère 1 pk représentatif par groupe (exercice, matiere)
        via Min, puis on annote chaque ligne avec le total réel via Subquery.
        Cela retourne de vrais objets modèle (pas des dicts) compatibles avec
        le changelist Django admin.
        """
        base = super().get_queryset(request).select_related("matiere", "exercice", "depot")

        # 1) Un seul pk par (exercice_id, matiere_id)
        min_pks = (
            base
            .values("exercice_id", "matiere_id")
            .annotate(_min_pk=Min("pk"))
            .values_list("_min_pk", flat=True)
        )

        # 2) Sous-requêtes pour les totaux
        total_qte_sq = (
            StockCourant.objects
            .filter(exercice_id=OuterRef("exercice_id"), matiere_id=OuterRef("matiere_id"))
            .values("exercice_id", "matiere_id")
            .annotate(s=Sum("quantite"))
            .values("s")
        )
        total_val_sq = (
            StockCourant.objects
            .filter(exercice_id=OuterRef("exercice_id"), matiere_id=OuterRef("matiere_id"))
            .values("exercice_id", "matiere_id")
            .annotate(s=Sum(
                ExpressionWrapper(F("quantite") * F("cump"), output_field=DecimalField())
            ))
            .values("s")
        )

        return (
            base
            .filter(pk__in=min_pks)
            .annotate(
                total_qte=Coalesce(
                    Subquery(total_qte_sq, output_field=DecimalField()),
                    Decimal("0"), output_field=DecimalField(),
                ),
                total_val=Coalesce(
                    Subquery(total_val_sq, output_field=DecimalField()),
                    Decimal("0"), output_field=DecimalField(),
                ),
            )
            .order_by("matiere__code_court")
        )

    # ─── Colonnes calculées ───────────────────────────────────
    def code_court_display(self, obj):
        return obj.matiere.code_court
    code_court_display.short_description = "Code"

    def designation_display(self, obj):
        return obj.matiere.designation
    designation_display.short_description = "Désignation"

    def type_matiere_display(self, obj):
        val = obj.matiere.type_matiere
        colors = {"consommable": "#b45309", "reutilisable": "#1e6b3a"}
        labels = {"consommable": "Consommable", "reutilisable": "Réutilisable"}
        color = colors.get(val, "#6b7280")
        label = labels.get(val, val or "—")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, label
        )
    type_matiere_display.short_description = "Type"
    type_matiere_display.allow_tags = True

    def quantite_totale(self, obj):
        val = obj.total_qte or Decimal("0")
        return int(val) if val == int(val) else round(float(val), 2)
    quantite_totale.short_description = "Qté totale (tous dépôts)"

    def valeur_totale(self, obj):
        val = int(obj.total_val or 0)
        return f"{val:,} FCFA".replace(",", " ")
    valeur_totale.short_description = "Valeur totale"

    def seuil_display(self, obj):
        seuil = obj.matiere.seuil_min or Decimal("0")
        return int(seuil) if seuil == int(seuil) else round(float(seuil), 2)
    seuil_display.short_description = "Seuil min"

    def alerte_display(self, obj):
        qte   = obj.total_qte or Decimal("0")
        seuil = obj.matiere.seuil_min or Decimal("0")
        if qte <= 0:
            return format_html('<span style="color:#dc2626;font-weight:700;">🔴 RUPTURE</span>')
        if qte <= seuil:
            return format_html('<span style="color:#b45309;font-weight:700;">⚠️ ALERTE</span>')
        return format_html('<span style="color:#059669;font-weight:700;">✅ OK</span>')
    alerte_display.short_description = "Statut"
    alerte_display.allow_tags = True
