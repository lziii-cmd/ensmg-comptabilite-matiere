# catalog/admin/matiere_admin.py
# ─────────────────────────────────────────────────────────────────────────────
# Admin 'Matière' avec verrouillage lecture seule si la sélection d'exercices
# est uniquement CLOS. Les matières n'ont pas de date → toujours visibles,
# mais pas d'ajout/modif/suppression ni d'actions quand clos.
# ─────────────────────────────────────────────────────────────────────────────
from django.contrib import admin, messages
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from core.admin.mixins import AgentRestrictedMixin
from core.admin.detail_view_mixin import DetailViewMixin
from catalog.models import Matiere, SousCompte
from core.utils.exercices import selection_is_closed_only


# ─── Helper statut prêt ───────────────────────────────────────────────────────
def _statut_pret_detail(matiere):
    """
    Retourne un tableau HTML listant tous les prêts (ouverts et clôturés)
    contenant cette matière, avec les colonnes :
    Dépôt/Bureau | Service | Bénéficiaire | Qté prêtée | Date prêt | Dernier retour | Statut
    Non applicable pour le 2e groupe (consommables).
    """
    if matiere.type_matiere != Matiere.TypeMatiere.REUTILISABLE:
        return "N/A (2e groupe — consommable)"
    try:
        from django.apps import apps
        from django.utils.safestring import mark_safe
        from django.db.models import Max
        LignePret = apps.get_model("purchasing", "LignePret")
        lignes = (
            LignePret.objects
            .filter(matiere=matiere)
            .select_related(
                "pret__service",
                "pret__depot",
            )
            .order_by("-pret__date_pret", "-pret__id")
        )
        if not lignes.exists():
            return mark_safe(
                '<span style="color:#166534;">✅ Jamais prêtée — en stock</span>'
            )

        # Récupérer la date du dernier retour pour chaque prêt
        RetourPret = apps.get_model("purchasing", "RetourPret")
        last_retour_map = {
            r["pret_id"]: r["last"]
            for r in RetourPret.objects.values("pret_id").annotate(last=Max("date_retour"))
        }

        rows = ""
        for ligne in lignes:
            pret = ligne.pret
            depot_nom    = pret.depot.nom if pret.depot else "—"
            service_lib  = pret.service.libelle if pret.service else "—"
            beneficiaire = (pret.service.responsable or "—") if pret.service else "—"
            qte          = int(ligne.quantite) if ligne.quantite == int(ligne.quantite) else round(float(ligne.quantite), 2)
            date_pret    = pret.date_pret.strftime("%d/%m/%Y") if pret.date_pret else "—"
            last_ret     = last_retour_map.get(pret.pk)
            date_retour  = last_ret.strftime("%d/%m/%Y") if last_ret else "—"
            if pret.est_clos:
                statut_html = '<span style="background:#dcfce7;color:#166534;padding:1px 6px;border-radius:8px;font-size:11px;font-weight:bold;">✅ Clôturé</span>'
            else:
                statut_html = '<span style="background:#fef3c7;color:#92400e;padding:1px 6px;border-radius:8px;font-size:11px;font-weight:bold;">🔄 En prêt</span>'
            rows += (
                f"<tr>"
                f"<td style='padding:3px 7px;border:1px solid #e5e7eb;'>{depot_nom}</td>"
                f"<td style='padding:3px 7px;border:1px solid #e5e7eb;'>{service_lib}</td>"
                f"<td style='padding:3px 7px;border:1px solid #e5e7eb;'>{beneficiaire}</td>"
                f"<td style='padding:3px 7px;border:1px solid #e5e7eb;text-align:right;'>{qte}</td>"
                f"<td style='padding:3px 7px;border:1px solid #e5e7eb;text-align:center;'>{date_pret}</td>"
                f"<td style='padding:3px 7px;border:1px solid #e5e7eb;text-align:center;'>{date_retour}</td>"
                f"<td style='padding:3px 7px;border:1px solid #e5e7eb;text-align:center;'>{statut_html}</td>"
                f"</tr>"
            )

        th = "<th style='padding:4px 7px;border:1px solid #d1d5db;text-align:left;background:#f3f4f6;font-size:11px;'>"
        thead = (
            "<thead><tr>"
            f"{th}Dépôt / Bureau</th>"
            f"{th}Service</th>"
            f"{th}Bénéficiaire</th>"
            f"<th style='padding:4px 7px;border:1px solid #d1d5db;background:#f3f4f6;font-size:11px;'>Qté prêtée</th>"
            f"<th style='padding:4px 7px;border:1px solid #d1d5db;background:#f3f4f6;font-size:11px;'>Date prêt</th>"
            f"<th style='padding:4px 7px;border:1px solid #d1d5db;background:#f3f4f6;font-size:11px;'>Dernier retour</th>"
            f"<th style='padding:4px 7px;border:1px solid #d1d5db;background:#f3f4f6;font-size:11px;'>Statut</th>"
            "</tr></thead>"
        )
        html = (
            "<table style='border-collapse:collapse;font-size:12px;width:100%;'>"
            + thead
            + "<tbody>" + rows + "</tbody>"
            + "</table>"
        )
        return mark_safe(html)
    except Exception as e:
        return f"Erreur: {e}"


# ─── Helpers stock pour la vue détail matière ─────────────────────────────────
def _get_stock_total(matiere):
    try:
        from django.apps import apps
        StockCourant = apps.get_model("inventory", "StockCourant")
        from django.db.models import Sum
        # Prendre l'exercice ouvert ou le plus récent
        Exercice = apps.get_model("core", "Exercice")
        ex = Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
        if not ex:
            ex = Exercice.objects.order_by("-annee").first()
        if not ex:
            return "—"
        total = StockCourant.objects.filter(
            matiere=matiere, exercice=ex
        ).aggregate(s=Sum("quantite"))["s"]
        if total is None:
            return "0"
        v = int(total) if total == int(total) else round(float(total), 2)
        return str(v)
    except Exception:
        return "—"

def _get_cump_moyen(matiere):
    try:
        from django.apps import apps
        StockCourant = apps.get_model("inventory", "StockCourant")
        from django.db.models import Avg
        Exercice = apps.get_model("core", "Exercice")
        ex = Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
        if not ex:
            ex = Exercice.objects.order_by("-annee").first()
        if not ex:
            return "—"
        avg = StockCourant.objects.filter(
            matiere=matiere, exercice=ex
        ).aggregate(a=Avg("cump"))["a"]
        if avg is None:
            return "—"
        v = int(avg) if avg == int(avg) else round(float(avg), 2)
        return f"{v:,} F CFA".replace(",", "\u202f")
    except Exception:
        return "—"

def _get_valeur_totale(matiere):
    try:
        from django.apps import apps
        from decimal import Decimal
        StockCourant = apps.get_model("inventory", "StockCourant")
        Exercice = apps.get_model("core", "Exercice")
        ex = Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
        if not ex:
            ex = Exercice.objects.order_by("-annee").first()
        if not ex:
            return "—"
        total = Decimal("0")
        for sc in StockCourant.objects.filter(matiere=matiere, exercice=ex).select_related():
            total += (sc.quantite or Decimal("0")) * (sc.cump or Decimal("0"))
        if total == 0:
            return "0 F CFA"
        return f"{int(total):,} F CFA".replace(",", "\u202f")
    except Exception as e:
        return f"— ({e})"

def _get_depots_stock(matiere):
    try:
        from django.apps import apps
        StockCourant = apps.get_model("inventory", "StockCourant")
        Exercice = apps.get_model("core", "Exercice")
        ex = Exercice.objects.filter(statut="OUVERT").order_by("-annee").first()
        if not ex:
            ex = Exercice.objects.order_by("-annee").first()
        if not ex:
            return "—"
        stocks = StockCourant.objects.filter(
            matiere=matiere, exercice=ex, quantite__gt=0
        ).select_related("depot").order_by("depot__nom")
        if not stocks.exists():
            return "Aucun stock (quantité > 0) enregistré pour cet exercice."
        rows = ""
        for s in stocks:
            qte = int(s.quantite) if s.quantite == int(s.quantite) else round(float(s.quantite), 2)
            cump = int(s.cump) if s.cump and s.cump == int(s.cump) else round(float(s.cump or 0), 2)
            val = int(s.quantite * s.cump) if s.quantite and s.cump else 0
            rows += f"<tr><td style='padding:3px 8px;border:1px solid #e5e7eb;'>{s.depot.nom}</td><td style='padding:3px 8px;border:1px solid #e5e7eb;text-align:right;'>{qte}</td><td style='padding:3px 8px;border:1px solid #e5e7eb;text-align:right;'>{cump:,}</td><td style='padding:3px 8px;border:1px solid #e5e7eb;text-align:right;'>{val:,}</td></tr>"
        from django.utils.safestring import mark_safe
        html = (
            "<table style='border-collapse:collapse;font-size:12px;width:100%;'>"
            "<thead><tr style='background:#f3f4f6;'>"
            "<th style='padding:3px 8px;border:1px solid #d1d5db;text-align:left;'>Dépôt</th>"
            "<th style='padding:3px 8px;border:1px solid #d1d5db;'>Quantité</th>"
            "<th style='padding:3px 8px;border:1px solid #d1d5db;'>CUMP (F CFA)</th>"
            "<th style='padding:3px 8px;border:1px solid #d1d5db;'>Valeur (F CFA)</th>"
            "</tr></thead><tbody>"
            + rows
            + "</tbody></table>"
        )
        return mark_safe(html)
    except Exception as e:
        return f"Erreur: {e}"


@admin.register(Matiere)
class MatiereAdmin(DetailViewMixin, AgentRestrictedMixin, admin.ModelAdmin):
    """
    Admin 'Matière'
    - Liste: code, désignation, type, catégorie, sous-catégorie, CP, CD, sous-compte, actif, est_stocke
    - Formulaire: catégorie en lecture seule (déduite), confirmation si on change le sous_compte
    - Verrou clos: lecture seule totale + pas d'ajout/suppression/actions
    """

    # ==== DÉTAIL READ-ONLY ====
    detail_fields_sections = [
        {
            "titre": "Identification",
            "fields": [
                ("Code court",   "code_court"),
                ("Désignation",  "designation"),
                ("Type matière", lambda o: (
                    "2e groupe — Consomptible (CONSOMMABLE)" if o.type_matiere == "CONSOMMABLE"
                    else "1er groupe — Durable (RÉUTILISABLE)" if o.type_matiere in ("REUTILISABLE", "IMMOBILISATION")
                    else str(o.type_matiere or "—")
                )),
                ("Groupe CDM",   lambda o: (
                    "Groupe 2 (Consomptibles)" if o.type_matiere == "CONSOMMABLE"
                    else "Groupe 1 (Durables)" if o.type_matiere in ("REUTILISABLE", "IMMOBILISATION")
                    else "—"
                )),
                ("Unité",        "unite"),
                ("Seuil minimum",lambda o: str(int(o.seuil_min or 0))),
                ("Actif",        lambda o: "✅ Oui" if o.actif else "❌ Non"),
                ("Stocké",       lambda o: "✅ Oui" if o.est_stocke else "❌ Non"),
            ],
        },
        {
            "titre": "Classification matière (Nomenclature)",
            "fields": [
                ("Catégorie",     "categorie"),
                ("Sous-catégorie","sous_categorie"),
            ],
        },
        {
            "titre": "Imputation comptable",
            "fields": [
                ("Compte principal (CP)",      lambda o: (
                    f"{o.sous_compte.compte_divisionnaire.compte_principal.code} — {o.sous_compte.compte_divisionnaire.compte_principal.libelle}"
                    if o.sous_compte and getattr(o.sous_compte, 'compte_divisionnaire', None)
                       and getattr(o.sous_compte.compte_divisionnaire, 'compte_principal', None) else "—"
                )),
                ("Compte divisionnaire (CD)",  lambda o: (
                    f"{o.sous_compte.compte_divisionnaire.code} — {o.sous_compte.compte_divisionnaire.libelle}"
                    if o.sous_compte and getattr(o.sous_compte, 'compte_divisionnaire', None) else "—"
                )),
                ("Sous-compte (SC)",           lambda o: (
                    f"{o.sous_compte.code} — {o.sous_compte.libelle}" if o.sous_compte else "—"
                )),
            ],
        },
        {
            "titre": "Stock & Valorisation (tous dépôts — exercice en cours)",
            "fields": [
                ("Stock actuel (total)", lambda o: _get_stock_total(o)),
                ("CUMP moyen",           lambda o: _get_cump_moyen(o)),
                ("Valeur totale stock",  lambda o: _get_valeur_totale(o), "montant"),
            ],
        },
        {
            "titre": "Stock par dépôt (exercice en cours)",
            "fields": [
                ("Dépôts", lambda o: _get_depots_stock(o), "full-width"),
            ],
        },
        {
            "titre": "Sorties provisoires / Prêts (1er groupe uniquement)",
            "fields": [
                ("Suivi prêts", lambda o: _statut_pret_detail(o), "full-width"),
            ],
        },
    ]

    # ==== LISTE (TABLEAU) ====
    list_display = (
        "code_court",
        "designation",
        "type_matiere",
        "categorie",
        "sous_categorie",
        "cp_code",
        "cd_code",
        "sous_compte",
        "actif",
        "est_stocke",
        "statut_pret_col",  # 🔄 En prêt / ✅ En stock pour le 1er groupe
    )
    list_filter = ("type_matiere", "categorie", "sous_categorie", "sous_compte", "actif", "est_stocke")
    search_fields = (
        "code_court",
        "designation",
        "sous_categorie__libelle",
        "categorie__libelle",
        "sous_compte__code",
        "sous_compte__libelle",
        "sous_compte__compte_divisionnaire__libelle",
        "sous_compte__compte_divisionnaire__compte_principal__libelle",
    )
    ordering = ("code_court",)
    list_select_related = (
        "categorie",
        "sous_categorie",
        "sous_compte",
        "sous_compte__compte_divisionnaire",
        "sous_compte__compte_divisionnaire__compte_principal",
    )

    # Colonnes CP / CD (codes)
    def cp_code(self, obj: Matiere):
        sc = obj.sous_compte
        if not sc:
            return "-"
        cp = getattr(sc.compte_divisionnaire, "compte_principal", None)
        return getattr(cp, "code", "-")
    cp_code.short_description = _("CP")

    def cd_code(self, obj: Matiere):
        sc = obj.sous_compte
        if not sc:
            return "-"
        cd = getattr(sc, "compte_divisionnaire", None)
        return getattr(cd, "code", "-")
    cd_code.short_description = _("CD")

    def statut_pret_col(self, obj: Matiere):
        """
        Indique si la matière a des unités actuellement en prêt (non clôturé).
        N'est pertinent que pour les matières du 1er groupe (réutilisable).
        """
        if obj.type_matiere != Matiere.TypeMatiere.REUTILISABLE:
            return "—"
        try:
            from django.apps import apps
            LignePret = apps.get_model("purchasing", "LignePret")
            nb_en_pret = LignePret.objects.filter(
                matiere=obj,
                pret__est_clos=False,
            ).count()
            if nb_en_pret:
                return format_html(
                    '<span style="background:#fef3c7;color:#92400e;padding:2px 7px;'
                    'border-radius:10px;font-size:11px;font-weight:bold;">🔄 En prêt</span>'
                )
            return format_html(
                '<span style="color:#166534;font-size:11px;">✅ En stock</span>'
            )
        except Exception:
            return "—"
    statut_pret_col.short_description = "Statut"

    # ==== FORMULAIRE ====
    fieldsets = (
        (_("Identification"), {
            "fields": ("code_court", "designation", "type_matiere", "actif")
        }),
        (_("Classification matière"), {
            "fields": ("sous_categorie", "categorie")
        }),
        (_("Imputation comptable"), {
            "fields": ("sous_compte",)
        }),
        (_("Stock (optionnel)"), {
            "classes": ("collapse",),
            "fields": ("unite", "seuil_min", "est_stocke"),  # affiché pour info
        }),
    )
    readonly_fields = ("categorie", "est_stocke")  # catégorie déduite + statut d'initialisation stock
    autocomplete_fields = ("sous_categorie", "sous_compte")

    # Confirmation lors du changement de sous_compte
    change_confirmation_template = "admin/catalog/matiere/confirm_sous_compte_change.html"

    # ─────────────────────────────────────────────────────────────
    # Verrouillage lecture seule si exercices clos
    # ─────────────────────────────────────────────────────────────
    def _is_closed_context(self, request) -> bool:
        """True si tous les exercices sélectionnés (barre de filtres) sont CLOS."""
        return selection_is_closed_only(request)

    def has_view_permission(self, request, obj=None):
        # Toujours consultable (liste + détail)
        return True

    def has_add_permission(self, request):
        # Interdit l'ajout si contexte clos
        if self._is_closed_context(request):
            return False
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        # Interdit la modification si contexte clos
        if self._is_closed_context(request):
            return False
        return super().has_change_permission(request, obj=obj)

    def has_delete_permission(self, request, obj=None):
        # Interdit la suppression si contexte clos
        if self._is_closed_context(request):
            return False
        return super().has_delete_permission(request, obj=obj)

    def get_readonly_fields(self, request, obj=None):
        # Lecture seule complète si clos (tous les champs)
        if self._is_closed_context(request):
            return [f.name for f in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)

    def get_actions(self, request):
        # Supprime les actions si clos
        if self._is_closed_context(request):
            return {}
        return super().get_actions(request)

    # ─────────────────────────────────────────────────────────────
    # Confirmation de changement du sous-compte (inactive quand clos,
    # car has_change_permission=False court-circuite le POST de modif)
    # ─────────────────────────────────────────────────────────────
    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        # Flag pour le template override (masquer boutons en clos)
        extra_context = extra_context or {}
        extra_context["closed_context"] = self._is_closed_context(request)

        # Si clos → laisser juste la vue (lecture seule), pas de confirmation
        if self._is_closed_context(request):
            return super().changeform_view(request, object_id, form_url, extra_context)

        # Conduite normale (avec confirmation sous-compte)
        if request.method == "POST" and object_id:
            try:
                original: Matiere = Matiere.objects.select_related("sous_compte").get(pk=object_id)
            except Matiere.DoesNotExist:
                return super().changeform_view(request, object_id, form_url, extra_context)

            new_sc_id = request.POST.get("sous_compte")
            if new_sc_id and str(original.sous_compte_id) != str(new_sc_id) and "_confirm_sous_compte" not in request.POST:
                new_sc = SousCompte.objects.filter(pk=new_sc_id).select_related(
                    "compte_divisionnaire__compte_principal"
                ).first()
                ctx = {
                    **extra_context,
                    **self.admin_site.each_context(request),
                    "opts": self.model._meta,
                    "original": original,
                    "old_sc": original.sous_compte,
                    "new_sc": new_sc,
                    "title": _("Confirmer le changement de sous-compte"),
                    "save_url": request.get_full_path(),
                }
                return TemplateResponse(request, self.change_confirmation_template, ctx)

        return super().changeform_view(request, object_id, form_url, extra_context)

    def response_change(self, request, obj):
        if "_confirm_sous_compte" in request.POST:
            messages.success(request, _("Sous-compte modifié avec succès."))
        return super().response_change(request, obj)
