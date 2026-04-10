# purchasing/admin/dotation_admin.py
from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from core.admin.mixins import AgentRestrictedMixin
from core.admin.detail_view_mixin import DetailViewMixin
from purchasing.models.dotation import Dotation, LigneDotation


# ─────────────────────────────────────────────────────────────
# Inline des lignes
# ─────────────────────────────────────────────────────────────
class LigneDotationInline(admin.TabularInline):
    model               = LigneDotation
    extra               = 1
    readonly_fields     = ("total_ligne", "groupe_affiche")
    verbose_name        = "Article distribué"
    verbose_name_plural = "Articles distribués"

    @admin.display(description="Groupe")
    def groupe_affiche(self, obj):
        if not obj.pk or not obj.matiere_id:
            return "—"
        if obj.matiere.type_matiere == "reutilisable":
            return format_html('<span style="color:#1e3a5f;font-weight:600">1er groupe (immob.)</span>')
        return format_html('<span style="color:#b8962e;font-weight:600">2e groupe (consomm.)</span>')

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.statut == Dotation.Statut.VALIDE:
            # Dotation validée → tout en lecture seule
            return [f.name for f in LigneDotation._meta.fields] + ["groupe_affiche"]
        return self.readonly_fields

    def has_add_permission(self, request, obj=None):
        if obj and obj.statut == Dotation.Statut.VALIDE:
            return False
        return super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.statut == Dotation.Statut.VALIDE:
            return False
        return super().has_delete_permission(request, obj)


# ─────────────────────────────────────────────────────────────
# Admin Dotation
# ─────────────────────────────────────────────────────────────
@admin.register(Dotation)
class DotationAdmin(DetailViewMixin, AgentRestrictedMixin, admin.ModelAdmin):

    list_display   = ("code", "date", "statut_badge", "type_dotation", "beneficiaire", "depot", "total_value")
    list_filter    = ("statut", "depot")
    search_fields  = ("code", "beneficiaire", "document_number")
    date_hierarchy = "date"
    inlines        = [LigneDotationInline]
    readonly_fields = ("code", "total_value", "type_dotation", "statut")
    actions        = ["action_valider", "action_annuler"]

    fieldsets = (
        ("Informations générales", {
            "fields": ("statut", "date", "depot", "beneficiaire", "service"),
        }),
        ("Document de référence", {
            "fields": ("document_number", "comment"),
        }),
        ("Synthèse (calculée automatiquement)", {
            "fields": ("code", "type_dotation", "total_value"),
            "classes": ("collapse",),
        }),
    )

    # ── Badge statut ──────────────────────────────────────────
    @admin.display(description="Statut", ordering="statut")
    def statut_badge(self, obj):
        colours = {
            "BROUILLON": ("#6b7280", "#f3f4f6"),   # gris
            "VALIDE":    ("#166534", "#dcfce7"),   # vert
            "ANNULE":    ("#991b1b", "#fee2e2"),   # rouge
        }
        fg, bg = colours.get(obj.statut, ("#000", "#fff"))
        return format_html(
            '<span style="padding:2px 10px;border-radius:12px;font-size:11px;'
            'font-weight:600;color:{};background:{}">{}</span>',
            fg, bg, obj.get_statut_display(),
        )

    # ── Action : valider ──────────────────────────────────────
    @admin.action(description="✅  Valider les dotations sélectionnées (génère les documents)")
    def action_valider(self, request, queryset):
        ok, deja, erreurs = 0, 0, []
        for dotation in queryset:
            if dotation.statut == Dotation.Statut.VALIDE:
                deja += 1
                continue
            if dotation.statut == Dotation.Statut.ANNULE:
                erreurs.append(f"{dotation} : annulée, impossible de valider.")
                continue
            if not dotation.lignes.exists():
                erreurs.append(f"{dotation} : aucune ligne, impossible de valider.")
                continue
            dotation.statut = Dotation.Statut.VALIDE
            dotation.save(update_fields=["statut"])
            try:
                dotation.generer_documents()
                ok += 1
            except Exception as e:
                erreurs.append(f"{dotation} : {e}")

        if ok:
            self.message_user(request, f"{ok} dotation(s) validée(s) avec génération des documents.", messages.SUCCESS)
        if deja:
            self.message_user(request, f"{deja} dotation(s) déjà validée(s) (ignorée(s)).", messages.WARNING)
        for msg in erreurs:
            self.message_user(request, msg, messages.ERROR)

    # ── Action : annuler ──────────────────────────────────────
    @admin.action(description="🚫  Annuler les dotations sélectionnées (brouillons uniquement)")
    def action_annuler(self, request, queryset):
        nb = queryset.filter(statut=Dotation.Statut.BROUILLON).update(statut=Dotation.Statut.ANNULE)
        self.message_user(request, f"{nb} dotation(s) annulée(s).", messages.WARNING)

    # ── Lecture seule si validée ──────────────────────────────
    def get_readonly_fields(self, request, obj=None):
        base = list(self.readonly_fields)
        if obj and obj.statut == Dotation.Statut.VALIDE:
            # Tous les champs en lecture seule une fois validée
            all_fields = [f.name for f in Dotation._meta.fields if f.name != "id"]
            return all_fields
        return base

    def has_change_permission(self, request, obj=None):
        if obj and obj.statut == Dotation.Statut.VALIDE:
            # Autorise l'accès à la page mais en readonly
            return True
        return super().has_change_permission(request, obj)

    # ─────────────────────────────────────────────────────────
    # URL personnalisée : /admin/purchasing/dotation/<pk>/valider/
    # ─────────────────────────────────────────────────────────
    def get_urls(self):
        custom = [
            path(
                "<int:object_id>/valider/",
                self.admin_site.admin_view(self.valider_view),
                name="purchasing_dotation_valider",
            ),
        ]
        return custom + super().get_urls()

    def valider_view(self, request, object_id):
        """Valide une dotation en brouillon et génère les documents."""
        dotation = get_object_or_404(Dotation, pk=object_id)
        detail_url = reverse("admin:purchasing_dotation_detail", args=[object_id])

        if dotation.statut == Dotation.Statut.ANNULE:
            self.message_user(request, "Cette dotation est annulée, impossible de la valider.", messages.ERROR)
            return redirect(detail_url)

        if dotation.statut == Dotation.Statut.VALIDE:
            self.message_user(request, "Cette dotation est déjà validée.", messages.WARNING)
            return redirect(detail_url)

        if not dotation.lignes.exists():
            self.message_user(request, "Impossible de valider : la dotation ne contient aucun article.", messages.ERROR)
            return redirect(detail_url)

        dotation.statut = Dotation.Statut.VALIDE
        dotation.save(update_fields=["statut"])
        try:
            dotation.generer_documents()
            self.message_user(
                request,
                f"✅ Dotation {dotation.code} validée — mouvements de stock et fiches d'affectation générés.",
                messages.SUCCESS,
            )
        except Exception as e:
            self.message_user(request, f"Dotation validée mais erreur lors de la génération : {e}", messages.ERROR)

        return redirect(detail_url)

    # ── Passe l'URL de validation au contexte de la vue détail ───────────
    def detail_view(self, request, object_id):
        response = super().detail_view(request, object_id)
        try:
            dotation = Dotation.objects.get(pk=object_id)
            ctx = response.context_data
            if dotation.statut == Dotation.Statut.BROUILLON:
                ctx["valider_url"] = reverse("admin:purchasing_dotation_valider", args=[object_id])
                ctx["valider_has_lines"] = dotation.lignes.exists()
            else:
                ctx["valider_url"] = None
        except Exception:
            pass
        return response

    # ─────────────────────────────────────────────────────────
    # Vue détail (DetailViewMixin)
    # ─────────────────────────────────────────────────────────
    detail_print_buttons = [
        {
            "url_name":  "documents:dotation_bon_dotation",
            "label":     "Bon de dotation",
            "icon":      "🖨",
            "condition": lambda obj: obj.statut == "VALIDE",
        },
        {
            # Fiches d'affectation groupées : seulement si dotation 1er groupe ou mixte
            "url_name":  "documents:dotation_fiches_affectation",
            "label":     "Fiches d'affectation",
            "icon":      "📋",
            "condition": lambda obj: (
                obj.statut == "VALIDE"
                and obj.type_dotation in ("1ER_GROUPE", "MIXTE")
            ),
        },
    ]

    detail_fields_sections = [
        {
            "titre": "Bon de dotation",
            "fields": [
                ("Code",              "code"),
                ("Statut",            lambda o: o.get_statut_display()),
                ("Date",              lambda o: o.date.strftime("%d/%m/%Y") if o.date else "—"),
                ("Type",              lambda o: o.get_type_dotation_display() if o.type_dotation else "—"),
                ("Bénéficiaire",      "beneficiaire"),
                ("Service",           lambda o: str(o.service) if o.service else "—"),
                ("Dépôt source",      "depot"),
                ("N° document réf.",  "document_number"),
                ("Valeur totale",     lambda o: f"{int(o.total_value or 0):,} F CFA".replace(",", "\u202f"), "montant"),
            ],
        },
        {
            "titre": "Observations",
            "obs_field": "comment",
            "fields": [],
        },
    ]

    detail_inline_models = [
        {
            "titre": "Articles distribués",
            "qs": lambda obj: obj.lignes.select_related("matiere").all(),
            "colonnes": [
                {"label": "Désignation",  "accessor": lambda l: l.matiere,                                                   "css": "td-primary"},
                {"label": "Groupe",       "accessor": lambda l: "1er groupe" if l.matiere.type_matiere == "reutilisable" else "2e groupe",  "css": ""},
                {"label": "Quantité",     "accessor": "quantity",                                                            "css": "td-num center"},
                {"label": "Prix unit.",   "accessor": lambda l: f"{int(l.unit_price or 0):,} F CFA".replace(",", "\u202f"),  "css": "td-num right"},
                {"label": "Total",        "accessor": lambda l: f"{int(l.total_ligne or 0):,} F CFA".replace(",", "\u202f"), "css": "td-num right"},
                {"label": "Note",         "accessor": lambda l: l.note or "—",                                               "css": ""},
            ],
            "total_value_fn": lambda obj, items: f"{int(obj.total_value or 0):,} F CFA".replace(",", "\u202f"),
            "total_label": "TOTAL VALEUR",
        },
        {
            "titre": "Fiches d'affectation générées (1er groupe)",
            "qs": lambda obj: obj.fiches_affectation.select_related("matiere").all(),
            "colonnes": [
                # Retourner l'objet FicheAffectation → le mixin auto-lie vers sa page détail
                {"label": "Code FA",      "accessor": lambda fa: fa,                                                         "css": "td-primary"},
                {"label": "Matière",      "accessor": lambda fa: fa.matiere,                                                 "css": ""},
                {"label": "Qté",          "accessor": "quantite",                                                            "css": "td-num center"},
                {"label": "Bénéficiaire", "accessor": "beneficiaire",                                                        "css": ""},
                {"label": "Statut",       "accessor": lambda fa: fa.get_statut_display(),                                    "css": ""},
                {"label": "Date",         "accessor": lambda fa: fa.date_affectation.strftime("%d/%m/%Y"),                   "css": ""},
            ],
        },
    ]
