from datetime import datetime
from django import forms
from django.apps import apps
from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html
from core.admin.mixins import AgentRestrictedMixin
from core.admin.detail_view_mixin import DetailViewMixin
from purchasing.models import Pret, LignePret
from catalog.models import Matiere

def _exercice_for_date(d):
    try:
        from inventory.services.exercice import exercice_courant
        return exercice_courant(d)
    except Exception:
        Exercice = apps.get_model("core", "Exercice")
        if not d: return None
        return Exercice.objects.filter(date_debut__lte=d, date_fin__gte=d).order_by("-date_debut").first()

def _aware_midnight(d):
    if not d: return timezone.now()
    return datetime.combine(d, datetime.min.time(), tzinfo=timezone.get_current_timezone())

class _PretAdminForm(forms.ModelForm):
    class Meta:
        model = Pret
        fields = "__all__"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "depot" in self.fields:
            self.fields["depot"].required = True

class LignePretInline(admin.TabularInline):
    """
    Inline pour les lignes de prêt.
    Seules les matières du 1er groupe (réutilisables / immobilisations) sont proposées.
    """
    model = LignePret
    extra = 1
    fields = ("matiere", "quantite", "observation")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "matiere":
            # 1er groupe = matières réutilisables (immobilisations)
            kwargs["queryset"] = Matiere.objects.filter(
                type_matiere=Matiere.TypeMatiere.REUTILISABLE,
                actif=True,
            ).select_related("unite", "sous_compte").order_by("designation")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Pret)
class PretAdmin(DetailViewMixin, AgentRestrictedMixin, admin.ModelAdmin):
    detail_print_buttons = [
        {
            "url_name": "documents:pret_document",
            "label":    "Bon de prêt",
            "icon":     "🖨",
        },
    ]
    detail_fields_sections = [
        {
            "titre": "Informations du prêt",
            "fields": [
                ("Code",        "code"),
                ("Service",     "service"),
                ("Dépôt",       "depot"),
                ("Date du prêt",lambda o: o.date_pret.strftime("%d/%m/%Y") if o.date_pret else "—"),
                ("Statut",      lambda o: "✅ Clôturé" if o.est_clos else "🔄 En cours"),
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
            "titre": "Matières prêtées",
            "qs": lambda obj: obj.lignes.select_related("matiere").all(),
            "colonnes": [
                {"label": "Désignation", "accessor": lambda l: l.matiere, "css": "td-primary"},
                {"label": "Quantité",    "accessor": "quantite",                "css": "td-num center"},
                {"label": "Observation", "accessor": lambda l: getattr(l, "observation", "") or "—", "css": ""},
            ],
        },
        {
            "titre": "Retours / Factures",
            "qs": lambda obj: obj.retours.all(),
            "colonnes": [
                {"label": "Code retour",  "accessor": lambda r: r,                                           "css": "td-primary"},
                {"label": "Date retour",  "accessor": lambda r: r.date_retour.strftime("%d/%m/%Y"),          "css": "td-num center"},
                {"label": "Qté totale",   "accessor": "total_qte",                                           "css": "td-num center"},
                {"label": "N° pièce",     "accessor": lambda r: r.numero_piece or "—",                       "css": ""},
                {"label": "Commentaire",  "accessor": lambda r: r.commentaire or "—",                        "css": ""},
            ],
        },
    ]
    form = _PretAdminForm
    inlines = [LignePretInline]

    list_display = ("code_or_temp", "service", "date_pret", "depot", "est_clos")
    list_filter = ("date_pret", "service", "depot", "est_clos")
    search_fields = ("code", "service__libelle", "service__code")

    fieldsets = (("Prêt", {"fields": ("service", "date_pret", "depot", "commentaire", "est_clos")}),)
    actions = ["regenerer_sorties_stock"]

    def code_or_temp(self, obj): return obj.code or "(en génération)"
    code_or_temp.short_description = "Code du prêt"

    def _imprimer_link(self, obj):
        if obj.pk:
            from django.urls import reverse
            url = reverse("documents:pret_document", args=[obj.pk])
            return format_html(
                '<a href="{}" target="_blank" title="Imprimer le document" '
                'style="background:#1e3a5f;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;text-decoration:none;">🖨 Imprimer</a>',
                url
            )
        return "—"
    _imprimer_link.short_description = "Bon prêt"
    _imprimer_link.allow_tags = True

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        pret: Pret = form.instance
        ok, info = self._generate_movements_for_pret(pret)
        self._flash(request, ok, info, entree=False)
        try:
            pret.recompute_closure(); pret.save(update_fields=["est_clos"])
        except Exception: pass

    @admin.action(description="(Re)générer les sorties de stock pour le prêt sélectionné")
    def regenerer_sorties_stock(self, request, queryset):
        c=u=d=okn=0; errs=[]
        for pret in queryset:
            ok, info = self._generate_movements_for_pret(pret)
            if ok: okn+=1; c+=info.get("created",0); u+=info.get("updated",0); d+=info.get("deleted",0)
            else: errs.append(f"{pret} → {info.get('error')}")
        if okn: messages.success(request, f"{okn} prêt(s) traités. Sorties créées:{c}, MAJ:{u}, suppr:{d}.")
        for e in errs: messages.warning(request, f"⚠️ {e}")

    def _generate_movements_for_pret(self, pret: Pret):
        MouvementStock = apps.get_model("inventory", "MouvementStock")
        LignePret = apps.get_model("purchasing", "LignePret")
        try:
            exo = _exercice_for_date(pret.date_pret)
            depot = getattr(pret, "depot", None)
            if not depot: return False, {"error": "Dépôt manquant sur le prêt."}
            ref = pret.code or ""; created=updated=deleted=0; wanted_dt=_aware_midnight(pret.date_pret)
            for ligne in LignePret.objects.filter(pret=pret):
                if not ligne.matiere_id or (ligne.quantite or 0) <= 0:
                    deleted += MouvementStock.objects.filter(source_doc_type="purchasing.LignePret", source_doc_id=ligne.id).delete()[0]; continue
                mvt, was_created = MouvementStock.objects.get_or_create(
                    source_doc_type="purchasing.LignePret", source_doc_id=ligne.id,
                    defaults=dict(type="SORTIE", date=wanted_dt, exercice=exo, matiere=ligne.matiere, depot=depot,
                                  quantite=ligne.quantite, cout_unitaire=None, reference=ref,
                                  commentaire=f"Sortie suite au prêt {pret.code}"),
                )
                need=False
                if mvt.date!=wanted_dt: mvt.date=wanted_dt; need=True
                if mvt.exercice_id!=(exo.id if exo else None): mvt.exercice=exo; need=True
                if mvt.depot_id!=depot.id: mvt.depot=depot; need=True
                if mvt.matiere_id!=ligne.matiere_id: mvt.matiere=ligne.matiere; need=True
                if mvt.quantite!=ligne.quantite: mvt.quantite=ligne.quantite; need=True
                if (mvt.reference or "")!=ref: mvt.reference=ref; need=True
                if need: mvt.save(); (created:=created+1) if was_created else (updated:=updated+1)
                else:
                    if was_created: created+=1
            return True, {"created":created,"updated":updated,"deleted":deleted}
        except Exception as e:
            return False, {"error": str(e)}

    def _flash(self, request, ok: bool, info: dict, entree: bool):
        nature = "Entrées" if entree else "Sorties"
        if ok:
            c,u,d = info.get("created",0),info.get("updated",0),info.get("deleted",0)
            if c or u or d: messages.success(request, f"{nature} — créées:{c}, MAJ:{u}, suppr:{d}.")
            else: messages.info(request, "Aucune ligne exploitable.")
        else:
            messages.warning(request, f"⚠️ {nature} non créées: {info.get('error')}")
