# inventory/admin/stock_initial_admin.py
from decimal import Decimal
from django import forms
from django.contrib import admin, messages
from django.apps import apps

from inventory.models import StockInitial, MouvementStock
from inventory.services.exercice import exercice_courant, exercice_precedent
from inventory.services.import_initial import importer_stocks_initiaux_depuis_precedent
from inventory.services.stock import appliquer_mouvement_sur_courant


class StockInitialForm(forms.ModelForm):
    """
    Formulaire minimal pour la saisie des stocks initiaux.
    Champs visibles :
      - matière (filtrée sur est_stocke=False)
      - date (de mise en stock)
      - eststocke (info – non persisté)
      - dépôt (réception)
      - quantité

    À l’enregistrement :
      - l’exercice est déduit automatiquement depuis la date
      - on empêche les doublons (exercice, matière, dépôt)
    """
    eststocke = forms.BooleanField(
        required=False,
        label="Est stocké",
        help_text="Sera coché automatiquement après l'enregistrement (information).",
    )

    class Meta:
        model = StockInitial
        fields = ("matiere", "date", "eststocke", "depot", "quantite")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Matières non encore stockées uniquement
        Matiere = apps.get_model("catalog", "Matiere")
        self.fields["matiere"].queryset = (
            Matiere.objects.filter(est_stocke=False, actif=True).order_by("designation")
        )
        self.fields["eststocke"].initial = False

    def clean(self):
        cleaned = super().clean()
        matiere = cleaned.get("matiere")
        depot = cleaned.get("depot")
        date = cleaned.get("date")
        if not (matiere and depot and date):
            return cleaned

        # Résoudre l'exercice couvrant la date fournie
        Exercice = apps.get_model("core", "Exercice")
        exo = (
            Exercice.objects.filter(date_debut__lte=date, date_fin__gte=date)
            .order_by("-date_debut")
            .first()
        )
        if not exo:
            raise forms.ValidationError("Aucun exercice ne couvre la date sélectionnée.")
        cleaned["_exercice_resolu"] = exo

        # Interdire un second stock initial (exercice, matière, dépôt)
        exists = MouvementStock.objects.filter(
            type="ENTREE",
            is_stock_initial=True,
            exercice=exo,
            matiere=matiere,
            depot=depot,
        ).exists()
        if exists:
            raise forms.ValidationError(
                "Un stock initial existe déjà pour cette matière et ce dépôt sur l'exercice sélectionné."
            )

        return cleaned


@admin.register(StockInitial)
class StockInitialAdmin(admin.ModelAdmin):
    form = StockInitialForm

    # Liste
    list_display = (
        "date",
        "exercice",
        "matiere",
        "depot",
        "quantite",
        "cout_unitaire",
        "cout_total",
    )
    list_per_page = 20
    list_filter = ("exercice", "matiere", "depot")
    search_fields = ("matiere__designation", "depot__nom")
    readonly_fields = ("cout_total",)

    # Actions
    actions = ["action_importer_depuis_precedent", "reappliquer_sur_stock_courant"]

    # Form layout (champs visibles)
    def get_fields(self, request, obj=None):
        # On n'affiche pas 'exercice' ni 'is_stock_initial' : gérés automatiquement
        return ("matiere", "date", "eststocke", "depot", "quantite")

    def save_model(self, request, obj, form, change):
        """
        - Force ENTREE + is_stock_initial
        - Affecte l'exercice (depuis la date)
        - Déduit cout_unitaire du CUMP de l'exercice précédent si disponible, sinon 0
        - Marque la matière comme est_stocke=True
        """
        obj.type = "ENTREE"
        obj.is_stock_initial = True

        # Exercice résolu au clean()
        exo = form.cleaned_data.get("_exercice_resolu")
        if exo:
            obj.exercice = exo

        # Coût unitaire : reprendre le CUMP de l’exercice précédent si existant
        if obj.cout_unitaire is None:
            StockCourant = apps.get_model("inventory", "StockCourant")
            exo_prev = exercice_precedent(obj.exercice)
            cu_init = Decimal("0")
            if exo_prev:
                sc_prev = (
                    StockCourant.objects.filter(
                        exercice=exo_prev, matiere=obj.matiere, depot=obj.depot
                    ).first()
                )
                if sc_prev and sc_prev.cump:
                    cu_init = sc_prev.cump
            obj.cout_unitaire = cu_init

        # Enregistrer le mouvement
        super().save_model(request, obj, form, change)

        # Marquer la matière comme stockée
        matiere = obj.matiere
        if hasattr(matiere, "est_stocke") and not matiere.est_stocke:
            matiere.est_stocke = True
            matiere.save(update_fields=["est_stocke"])

        self.message_user(
            request,
            f"Stock initial enregistré pour {matiere.designation}. La matière est désormais marquée comme stockée.",
            level=messages.SUCCESS,
        )

    # ----- Actions -----

    @admin.action(description="Importer les stocks initiaux depuis l'exercice précédent")
    def action_importer_depuis_precedent(self, request, queryset):
        """
        Utilise l'exercice ciblé par le filtre (exercice__id__exact),
        sinon l'exercice courant. Crée des ENTREE is_stock_initial
        pour chaque (matière, dépôt) avec stock > 0 dans l'exercice précédent,
        si non déjà créé pour l'exercice cible.
        """
        # Déterminer l'exercice cible
        exo = None
        try:
            exo_id = request.GET.get("exercice__id__exact")
            if exo_id:
                Exercice = apps.get_model("core", "Exercice")
                exo = Exercice.objects.filter(id=exo_id).first()
        except Exception:
            exo = None
        if not exo:
            exo = exercice_courant()

        if not exo:
            self.message_user(
                request, "Aucun exercice sélectionné ou courant.", level=messages.WARNING
            )
            return

        n = importer_stocks_initiaux_depuis_precedent(exo)
        if n:
            self.message_user(
                request,
                f"{n} stock(s) initial(aux) importé(s) depuis l'exercice précédent.",
                level=messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                "Aucun stock à importer (déjà importé ou pas d'exercice précédent / quantités nulles).",
                level=messages.INFO,
            )

    @admin.action(description="Recalculer StockCourant pour les mouvements sélectionnés")
    def reappliquer_sur_stock_courant(self, request, queryset):
        """
        Réapplique l'impact de stock pour corriger/mettre à jour StockCourant
        (utile après un changement de règles ou de signaux).
        """
        n = 0
        for m in queryset:
            try:
                appliquer_mouvement_sur_courant(m)
                n += 1
            except Exception:
                pass
        self.message_user(request, f"{n} mouvement(s) réappliqué(s) au StockCourant.")
