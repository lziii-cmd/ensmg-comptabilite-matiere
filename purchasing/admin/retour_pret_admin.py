from decimal import Decimal
from datetime import datetime
from django import forms
from django.apps import apps
from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html
from core.admin.mixins import AgentRestrictedMixin
from core.admin.detail_view_mixin import DetailViewMixin
from purchasing.models import RetourPret, LigneRetourPret

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

class _RetourPretAdminForm(forms.ModelForm):
    class Meta:
        model = RetourPret
        fields = "__all__"

class LigneRetourPretInline(admin.TabularInline):
    model = LigneRetourPret
    extra = 1
    fields = ("matiere", "quantite", "observation")

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "matiere":
            try:
                obj_id = request.resolver_match.kwargs.get("object_id")
                pret_id = None
                if obj_id:
                    rp = RetourPret.objects.select_related("pret").get(pk=obj_id)
                    pret_id = rp.pret_id
                else:
                    pret_id = request.GET.get("pret") or request.GET.get("pret__id__exact")
                if pret_id:
                    LignePret = apps.get_model("purchasing", "LignePret")
                    mat_ids = LignePret.objects.filter(pret_id=pret_id).values_list("matiere_id", flat=True)
                    formfield.queryset = formfield.queryset.model.objects.filter(id__in=list(mat_ids))
            except Exception:
                pass
        return formfield

@admin.register(RetourPret)
class RetourPretAdmin(DetailViewMixin, AgentRestrictedMixin, admin.ModelAdmin):
    detail_print_buttons = [
        {
            "url_name": "documents:retour_pret_document",
            "label":    "Bon de retour de prêt",
            "icon":     "🖨",
        },
    ]
    detail_fields_sections = [
        {
            "titre": "Informations du retour",
            "fields": [
                ("Code",          "code"),
                ("Prêt d'origine","pret"),
                ("Date du retour",lambda o: o.date_retour.strftime("%d/%m/%Y") if o.date_retour else "—"),
                ("N° pièce",      "numero_piece"),
                ("Qté totale",    "total_qte"),
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
            "titre": "Matières retournées",
            "qs": lambda obj: obj.lignes.select_related("matiere").all(),
            "colonnes": [
                {"label": "Désignation",  "accessor": lambda l: l.matiere, "css": "td-primary"},
                {"label": "Quantité",     "accessor": "quantite",                "css": "td-num center"},
                {"label": "Observation",  "accessor": lambda l: getattr(l, "observation", "") or "—", "css": ""},
            ],
        }
    ]
    form = _RetourPretAdminForm
    inlines = [LigneRetourPretInline]

    list_display = ("code_or_temp", "pret", "service_col", "depot_col", "date_retour", "total_qte", "numero_piece", "piece_link")
    list_filter = ("date_retour", "pret__service", "pret__depot")
    search_fields = ("code", "pret__service__libelle", "numero_piece")

    fieldsets = (
        ("Retour", {"fields": ("pret", "date_retour", "commentaire")}),
        ("Pièce justificative", {"fields": ("numero_piece", "fichier_piece")}),
    )

    actions = ["regenerer_entrees_stock"]

    def service_col(self, obj): return getattr(obj.pret.service, "libelle", "-")
    service_col.short_description = "Service"

    def depot_col(self, obj): return getattr(obj.pret.depot, "nom", "-")
    depot_col.short_description = "Dépôt"

    def code_or_temp(self, obj): return obj.code or "(en génération)"
    code_or_temp.short_description = "Code du retour"

    def piece_link(self, obj):
        if obj.fichier_piece:
            return format_html('<a href="{}" target="_blank">Voir/Télécharger</a>', obj.fichier_piece.url)
        return "-"
    piece_link.short_description = "Pièce"

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        retour: RetourPret = form.instance
        retour.recompute_total(); retour.save(update_fields=["total_qte"])
        ok, info = self._generate_movements_for_retour(retour)
        self._flash(request, ok, info)
        try:
            pret = retour.pret; pret.recompute_closure(); pret.save(update_fields=["est_clos"])
        except Exception: pass

    @admin.action(description="(Re)générer les entrées de stock pour le retour sélectionné")
    def regenerer_entrees_stock(self, request, queryset):
        c=u=d=okn=0; errs=[]
        for retour in queryset:
            ok, info = self._generate_movements_for_retour(retour)
            if ok: okn+=1; c+=info.get("created",0); u+=info.get("updated",0); d+=info.get("deleted",0)
            else: errs.append(f"{retour} → {info.get('error')}")
        if okn: messages.success(request, f"{okn} retour(s) traités. Entrées créées:{c}, MAJ:{u}, suppr:{d}.")
        for e in errs: messages.warning(request, f"⚠️ {e}")

    def _generate_movements_for_retour(self, retour: RetourPret):
        MouvementStock = apps.get_model("inventory", "MouvementStock")
        LigneRetourPret = apps.get_model("purchasing", "LigneRetourPret")
        StockCourant = apps.get_model("inventory", "StockCourant")
        try:
            exo = _exercice_for_date(retour.date_retour)
            depot = getattr(retour.pret, "depot", None)
            if not depot: return False, {"error": "Dépôt manquant (hérité du prêt)."}
            ref = retour.code or ""; created=updated=deleted=0; wanted_dt=_aware_midnight(retour.date_retour)
            for ligne in LigneRetourPret.objects.filter(retour=retour):
                if not ligne.matiere_id or (ligne.quantite or 0) <= 0:
                    deleted += MouvementStock.objects.filter(source_doc_type="purchasing.LigneRetourPret", source_doc_id=ligne.id).delete()[0]; continue
                cu = Decimal("0")
                if exo:
                    sc = StockCourant.objects.filter(exercice=exo, matiere_id=ligne.matiere_id, depot_id=depot.id).first()
                    if sc and sc.cump: cu = sc.cump
                mvt, was_created = MouvementStock.objects.get_or_create(
                    source_doc_type="purchasing.LigneRetourPret", source_doc_id=ligne.id,
                    defaults=dict(type="ENTREE", date=wanted_dt, exercice=exo, matiere=ligne.matiere, depot=depot,
                                  quantite=ligne.quantite, cout_unitaire=cu, reference=ref,
                                  commentaire=f"Entrée suite au retour {retour.code}"),
                )
                need=False
                if mvt.date!=wanted_dt: mvt.date=wanted_dt; need=True
                if mvt.exercice_id!=(exo.id if exo else None): mvt.exercice=exo; need=True
                if mvt.depot_id!=depot.id: mvt.depot=depot; need=True
                if mvt.matiere_id!=ligne.matiere_id: mvt.matiere=ligne.matiere; need=True
                if mvt.quantite!=ligne.quantite: mvt.quantite=ligne.quantite; need=True
                if mvt.cout_unitaire!=cu: mvt.cout_unitaire=cu; need=True
                if (mvt.reference or "")!=ref: mvt.reference=ref; need=True
                if need: mvt.save(); (created:=created+1) if was_created else (updated:=updated+1)
                else:
                    if was_created: created+=1
            return True, {"created":created,"updated":updated,"deleted":deleted}
        except Exception as e:
            return False, {"error": str(e)}

    def _flash(self, request, ok: bool, info: dict):
        if ok:
            c,u,d = info.get("created",0),info.get("updated",0),info.get("deleted",0)
            if c or u or d: messages.success(request, f"Entrées — créées:{c}, MAJ:{u}, suppr:{d}.")
            else: messages.info(request, "Aucune ligne exploitable.")
        else:
            messages.warning(request, f"⚠️ Entrées non créées: {info.get('error')}")
