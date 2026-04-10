# core/admin/detail_view_mixin.py
"""
Mixin Django Admin qui ajoute une page de détail READ-ONLY accessible
depuis la liste (clic sur la ligne → détail → boutons Modifier / Supprimer).

Usage :
    class MonAdmin(DetailViewMixin, admin.ModelAdmin):
        detail_fields_sections = [...]   # optionnel – voir ci-dessous
        detail_inline_models   = [...]   # optionnel – tableaux de lignes liées
        detail_print_url_name  = None    # ex: "documents:achat_document"

Exemple detail_fields_sections :
    detail_fields_sections = [
        {
            "titre": "Informations générales",
            "obs_field": "commentaire",   # optionnel
            "fields": [
                ("Fournisseur", "fournisseur"),               # attr simple (FK → __str__)
                ("Date",        lambda obj: obj.date_achat),  # callable
                ("Montant",     "montant_total_ht", "montant"), # avec classe CSS
            ]
        },
    ]

Exemple detail_inline_models :
    detail_inline_models = [
        {
            "titre": "Articles achetés",
            "qs": lambda obj: obj.lignes.select_related("matiere").all(),
            "colonnes": [
                {"label": "Matière",        "accessor": lambda l: str(l.matiere), "css": "td-primary"},
                {"label": "Qté",            "accessor": "quantite",               "css": "td-num right"},
                {"label": "Prix unitaire",  "accessor": lambda l: _fmt_fcfa(l.prix_unitaire), "css": "td-num right"},
                {"label": "Total",          "accessor": lambda l: _fmt_fcfa(l.total_ligne_ht), "css": "td-num right"},
            ],
            "total_col": 3,   # index (0-based) de la colonne dont on somme les valeurs brutes
            "total_label": "TOTAL HT",
        }
    ]
"""
from decimal import Decimal

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db import models as django_models
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import SafeData


# ─────────────────────────────────────────────────────────────
# Helpers de formatage
# ─────────────────────────────────────────────────────────────

def _fmt_fcfa(val) -> str:
    """Formate un montant en F CFA avec séparateur de milliers."""
    try:
        v = Decimal(str(val or 0))
        # Arrondir à l'entier pour l'affichage
        vi = int(v)
        formatted = f"{vi:,}".replace(",", "\u202f")  # espace fine
        return f"{formatted} F CFA"
    except Exception:
        return str(val) if val is not None else "—"


def _fmt_bool(val) -> str:
    return "✅ Oui" if val else "❌ Non"


# ─────────────────────────────────────────────────────────────
# Mixin principal
# ─────────────────────────────────────────────────────────────

class DetailViewMixin:
    """
    Ajoute l'URL  /admin/<app>/<model>/<pk>/detail/  sur chaque ModelAdmin.
    Le lien dans la liste pointe vers cette URL au lieu de la page de modification.
    """

    # ── Pagination standard ENSMG ────────────────────────────────────────────
    list_per_page = 20

    # ── À surcharger dans chaque admin ──────────────────────────────────────
    detail_fields_sections = None   # Liste de sections de champs
    detail_inline_models   = None   # Liste de définitions de tableaux inline
    detail_print_url_name  = None   # URL nommée pour le bouton "Imprimer" (ancien, pour compat)
    detail_print_buttons   = None   # Liste de dicts {"url_name": "...", "label": "...", "icon": "..."}

    # ── Surcharge : le clic sur la liste pointe vers /detail/ ───────────────
    def get_list_display_links(self, request, list_display):
        """Retourne None pour déconnecter le lien par défaut (on ajoute le nôtre)."""
        return None

    def get_list_display(self, request):
        """Ajoute une colonne "lien vers détail" en première position."""
        original = list(super().get_list_display(request))
        if "_detail_link" not in original:
            original.insert(0, "_detail_link")
        return original

    def _detail_link(self, obj):
        from django.utils.html import format_html
        url = reverse(
            f"admin:{obj._meta.app_label}_{obj._meta.model_name}_detail",
            args=[obj.pk],
        )
        label = str(obj) or f"#{obj.pk}"
        return format_html(
            '<a href="{}" style="color:#1e6b3a;font-weight:600;">{}</a>', url, label
        )

    _detail_link.short_description = "Référence"
    _detail_link.allow_tags = True

    # ── URL supplémentaire ───────────────────────────────────────────────────
    def get_urls(self):
        urls = super().get_urls()
        model = self.model
        info = (model._meta.app_label, model._meta.model_name)
        custom = [
            path(
                "<path:object_id>/detail/",
                self.admin_site.admin_view(self.detail_view),
                name="%s_%s_detail" % info,
            ),
        ]
        return custom + urls

    def get_queryset_for_detail(self, request):
        """
        Queryset utilisé pour récupérer l'objet dans la vue détail.
        Par défaut : manager par défaut du modèle (sans filtrage d'exercice etc.)
        Surcharger dans les admins qui ont besoin d'annotations (ex: StockActuelAdmin).
        """
        return self.model._default_manager.all()

    # ── Vue détail ───────────────────────────────────────────────────────────
    def detail_view(self, request, object_id):
        model = self.model
        opts  = model._meta

        if not self.has_view_or_change_permission(request):
            raise PermissionDenied

        obj = get_object_or_404(self.get_queryset_for_detail(request), pk=object_id)

        sections = self._build_sections(request, obj)
        inlines  = self._build_inlines(obj)
        print_url = self._build_print_url(obj)
        print_buttons = self._build_print_buttons(obj)

        # Code affiché dans le badge (code, numero, etc.)
        object_code = (
            getattr(obj, "code", None)
            or getattr(obj, "numero_facture", None)
            or getattr(obj, "numero", None)
            or ""
        )

        ctx = {
            **self.admin_site.each_context(request),
            "opts":          opts,
            "object":        obj,
            "object_code":   object_code,
            "sections":      sections,
            "inlines":       inlines,
            "print_url":     print_url,
            "print_buttons": print_buttons,
            "can_change":    self.has_change_permission(request, obj),
            "can_delete":    self.has_delete_permission(request, obj),
            "title":         f"{opts.verbose_name} — {obj}",
        }
        return TemplateResponse(request, self._get_detail_template(obj), ctx)

    # ── Helpers ─────────────────────────────────────────────────────────────
    def _get_detail_template(self, obj):
        opts = obj._meta
        return [
            f"admin/{opts.app_label}/{opts.model_name}/detail.html",
            "admin/detail_view.html",
        ]

    def _build_print_url(self, obj):
        if not self.detail_print_url_name:
            return None
        try:
            return reverse(self.detail_print_url_name, args=[obj.pk])
        except Exception:
            return None

    def _build_print_buttons(self, obj):
        """Construit la liste des boutons document (URLs nommées).

        Chaque entrée peut contenir une clé optionnelle ``"condition"``,
        callable(obj) → bool.  Le bouton est masqué si la condition est False.
        """
        if not self.detail_print_buttons:
            return []

        buttons = []
        for btn_def in self.detail_print_buttons:
            url_name  = btn_def.get("url_name")
            label     = btn_def.get("label", "Document")
            icon      = btn_def.get("icon", "🖨")
            condition = btn_def.get("condition")

            if not url_name:
                continue

            # Évaluer la condition sur l'objet si elle est définie
            if callable(condition) and not condition(obj):
                continue

            try:
                url = reverse(url_name, args=[obj.pk])
                buttons.append({"url": url, "label": label, "icon": icon})
            except Exception:
                pass

        return buttons

    # ── Construction des sections de champs ─────────────────────────────────
    def _build_sections(self, request, obj):
        if self.detail_fields_sections is not None:
            return self._resolve_sections(obj, self.detail_fields_sections)
        return self._introspect_sections(obj)

    def _introspect_sections(self, obj):
        """Affiche automatiquement tous les champs simples du modèle."""
        fields = []
        for f in obj._meta.get_fields():
            if f.is_relation:
                continue
            if f.name in ("id",):
                continue
            label = getattr(f, "verbose_name", f.name)
            value = getattr(obj, f.name, None)
            if value is None or value == "":
                display = None
            elif isinstance(value, bool):
                display = _fmt_bool(value)
            else:
                display = str(value)
            fields.append({"label": str(label).capitalize(), "value": display, "css_class": ""})
        return [{"titre": "Informations", "fields": fields, "obs": None}]

    def _resolve_sections(self, obj, sections_def):
        """
        sections_def = [
            {
                "titre": "...",
                "obs_field": "commentaire",   # optionnel
                "fields": [
                    ("Label", "field_name"),               # attr simple
                    ("Label", lambda obj: ...),            # callable
                    ("Label", "field_name", "css_class"),  # avec classe CSS
                ]
            }
        ]
        """
        result = []
        for sec in sections_def:
            fields_out = []
            for entry in sec.get("fields", []):
                css   = entry[2] if len(entry) > 2 else ""
                label = entry[0]
                accessor = entry[1]
                if callable(accessor):
                    raw = accessor(obj)
                else:
                    raw = getattr(obj, accessor, None)

                # Gestion des FK cliquables : si c'est une instance de modèle, créer un lien
                if raw is not None and isinstance(raw, django_models.Model):
                    try:
                        # Essayer la vue détail en premier (si le modèle l'a)
                        try:
                            admin_url = reverse(
                                f"admin:{raw._meta.app_label}_{raw._meta.model_name}_detail",
                                args=[raw.pk]
                            )
                        except Exception:
                            admin_url = reverse(
                                f"admin:{raw._meta.app_label}_{raw._meta.model_name}_change",
                                args=[raw.pk]
                            )
                        raw = format_html('<a href="{}">{}</a>', admin_url, str(raw))
                    except Exception:
                        # Si reverse échoue (modèle non enregistré), afficher juste le texte
                        raw = str(raw)
                elif raw is not None and not isinstance(raw, (str, int, float, bool, Decimal)):
                    raw = str(raw)

                if isinstance(raw, SafeData):
                    pass  # HTML déjà marqué sûr (format_html / mark_safe) — ne pas re-échapper
                elif isinstance(raw, bool):
                    raw = _fmt_bool(raw)
                elif raw is None or raw == "":
                    raw = None
                else:
                    raw = str(raw)

                fields_out.append({
                    "label":     label,
                    "value":     raw,
                    "css_class": css,
                })

            obs_field = sec.get("obs_field")
            obs = getattr(obj, obs_field, None) if obs_field else None

            result.append({
                "titre":  sec.get("titre", ""),
                "fields": fields_out,
                "obs":    str(obs) if obs else None,
            })
        return result

    # ── Construction des tableaux inline ────────────────────────────────────
    def _build_inlines(self, obj):
        """
        Construit la liste des tableaux inline à partir de self.detail_inline_models.

        Chaque définition :
        {
            "titre":       "Articles achetés",
            "qs":          lambda obj: obj.lignes.all(),   # QuerySet ou liste
            "colonnes": [
                {"label": "Matière", "accessor": lambda l: str(l.matiere), "css": "td-primary"},
                {"label": "Qté",     "accessor": "quantite", "css": "td-num right"},
            ],
            "total_col":   3,          # index 0-based de la colonne à totaliser (optionnel)
            "total_label": "TOTAL HT", # libellé de la ligne de total (optionnel)
        }
        """
        if not self.detail_inline_models:
            return []

        result = []
        for inline_def in self.detail_inline_models:
            qs_getter = inline_def.get("qs")
            try:
                items = list(qs_getter(obj)) if callable(qs_getter) else []
            except Exception:
                items = []

            col_defs = inline_def.get("colonnes", [])

            # En-têtes
            colonnes = [
                {"label": c.get("label", ""), "css": c.get("css_header", "")}
                for c in col_defs
            ]

            # Lignes
            rows = []
            for item in items:
                cells = []
                for c in col_defs:
                    acc = c.get("accessor")
                    if callable(acc):
                        val = acc(item)
                    else:
                        val = getattr(item, acc, None)

                    # Auto-lier les instances de modèle Django (FK)
                    if val is not None and isinstance(val, django_models.Model):
                        try:
                            # Essayer la vue détail en premier (si le modèle l'a)
                            try:
                                admin_url = reverse(
                                    f"admin:{val._meta.app_label}_{val._meta.model_name}_detail",
                                    args=[val.pk]
                                )
                            except Exception:
                                admin_url = reverse(
                                    f"admin:{val._meta.app_label}_{val._meta.model_name}_change",
                                    args=[val.pk]
                                )
                            val = format_html('<a href="{}">{}</a>', admin_url, str(val))
                        except Exception:
                            val = str(val)
                    elif isinstance(val, SafeData):
                        pass  # Préserver le HTML sûr tel quel
                    elif val is not None and not isinstance(val, (str, int, float, bool, Decimal)):
                        val = str(val)

                    cells.append({
                        "value": val if isinstance(val, SafeData) else (str(val) if val is not None else "—"),
                        "css":   c.get("css", ""),
                    })
                rows.append(cells)

            # Ligne de total optionnelle
            totaux = self._build_inline_totaux(obj, inline_def, items, col_defs)

            result.append({
                "titre":    inline_def.get("titre", ""),
                "colonnes": colonnes,
                "rows":     rows,
                "totaux":   totaux,
            })
        return result

    def _build_inline_totaux(self, obj, inline_def, items, col_defs):
        """Construit la ligne de pied de tableau (totaux)."""
        # Support custom totaux_fn
        totaux_fn = inline_def.get("totaux_fn")
        if totaux_fn:
            try:
                return totaux_fn(obj, items)
            except Exception:
                return []

        total_col   = inline_def.get("total_col")
        total_label = inline_def.get("total_label", "TOTAL")
        total_value_fn = inline_def.get("total_value_fn")

        if total_col is None and total_value_fn is None:
            return []

        n = len(col_defs)
        totaux = []

        if total_value_fn:
            try:
                total_str = total_value_fn(obj, items)
            except Exception:
                total_str = "—"
        elif total_col is not None:
            # Calculer la somme depuis les lignes brutes
            total = Decimal(0)
            for item in items:
                acc = col_defs[total_col].get("accessor")
                try:
                    if callable(acc):
                        raw = acc(item)
                    else:
                        raw = getattr(item, acc, None)
                    # Tenter de nettoyer et convertir
                    if raw is not None:
                        raw_str = str(raw).replace("\u202f", "").replace(" ", "").replace("FCFA", "").replace(",", "")
                        total += Decimal(raw_str)
                except Exception:
                    pass
            total_str = _fmt_fcfa(total)
        else:
            total_str = "—"

        # Construire les cellules de la ligne de total
        for i in range(n):
            if i == 0:
                totaux.append({"value": total_label, "css": "right" if n > 1 else ""})
            elif i == (total_col if total_col is not None else n - 1):
                totaux.append({"value": total_str, "css": col_defs[i].get("css", "right")})
            else:
                totaux.append({"value": "", "css": ""})
        return totaux
