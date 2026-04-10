# core/forms/mixins.py
# (nouveau fichier ou remplace l'existant si tu en avais déjà un)
from django import forms
from django.core.exceptions import ValidationError
from core.utils.exercices import get_selected_exercice_ids
from core.models import Exercice

class CurrentExerciceSelectionMixin(forms.ModelForm):
    """
    - Si le form contient 'exercice' :
      * En création :
         - si exactement 1 exercice sélectionné en session => initial auto
         - si 0 ou plusieurs => laisse vide et force la saisie (required=True)
      * En édition : ne change rien si déjà défini
    - En clean() : si 1 seul sélectionné et champ vide, on injecte cet exercice.
    """
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        if "exercice" in self.fields:
            selected_ids = []
            if self.request:
                selected_ids = get_selected_exercice_ids(self.request)

            if not getattr(self.instance, "pk", None):
                # Création
                if len(selected_ids) == 1:
                    self.fields["exercice"].initial = Exercice.objects.filter(pk=selected_ids[0]).first()
                else:
                    self.fields["exercice"].required = True
                    self.fields["exercice"].help_text = (
                        "Sélectionnez l'exercice (plusieurs exercices actifs sont sélectionnés globalement)."
                    )

    def clean(self):
        cleaned = super().clean()
        if "exercice" in self.fields:
            if not cleaned.get("exercice") and self.request:
                selected_ids = get_selected_exercice_ids(self.request)
                if len(selected_ids) == 1:
                    cleaned["exercice"] = Exercice.objects.filter(pk=selected_ids[0]).first()
                elif len(selected_ids) == 0:
                    raise ValidationError("Aucun exercice actif/sélectionné. Veuillez créer/ouvrir un exercice.")
        return cleaned
