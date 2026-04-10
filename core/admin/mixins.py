# core/admin/mixins.py
import json
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from core.utils.exercices import filter_qs_by_exercices


class FilterByExercicesAdminMixin:
    """
    Applique automatiquement le filtre par exercices selectionnes dans l'admin.
    Suppose que le modele a un champ FK 'exercice' (ou 'exercice_id').
    Surcharge 'exercise_field_name' si besoin.
    """
    exercise_field_name = "exercice_id"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return filter_qs_by_exercices(qs, request, field_name=self.exercise_field_name)


def _is_chef_service(user):
    """Retourne True si l'utilisateur est Chef de Service."""
    if user.is_superuser:
        return False
    return user.groups.filter(name="Chefs de Service").exists()


def _is_agent(user):
    """Retourne True si l'utilisateur est un agent simple."""
    if user.is_superuser or _is_chef_service(user):
        return False
    return user.groups.filter(name="Agents").exists()


class AgentRestrictedMixin:
    """
    Mixin a ajouter sur les ModelAdmin pour gerer les droits agents.
    - Agent : peut voir (list/detail), peut soumettre un ajout (-> PendingRecord)
    - Chef/Admin : tout faire
    """

    def has_change_permission(self, request, obj=None):
        if _is_agent(request.user):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if _is_agent(request.user):
            return False
        return super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        """
        Pour un agent : au lieu de sauvegarder directement, cree un PendingRecord.
        Pour un chef/admin : sauvegarde normale.
        """
        if _is_agent(request.user) and not change:
            try:
                from core.models.pending_record import PendingRecord
                # Serialiser les donnees du formulaire
                data = {}
                for field_name, value in form.cleaned_data.items():
                    if hasattr(value, "pk"):
                        data[field_name + "_id"] = value.pk
                    elif hasattr(value, "__iter__") and not isinstance(value, str):
                        data[field_name] = [v.pk if hasattr(v, "pk") else str(v) for v in value]
                    else:
                        try:
                            json.dumps(value)  # test serializabilite
                            data[field_name] = value
                        except TypeError:
                            data[field_name] = str(value)

                PendingRecord.objects.create(
                    submitted_by=request.user,
                    app_label=obj._meta.app_label,
                    model_name=obj._meta.model_name,
                    verbose_name=str(obj._meta.verbose_name),
                    data=data,
                )
                messages.warning(
                    request,
                    f'Votre ajout "{obj._meta.verbose_name}" a ete enregistre en attente de validation par un administrateur.'
                )
                return  # Ne pas sauvegarder directement
            except Exception as e:
                messages.error(request, f"Erreur lors de la soumission : {e}")
                return

        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        """Pour les agents, rediriger apres la soumission d'un ajout."""
        if _is_agent(request.user):
            self.message_user(
                request,
                f'Votre demande d\'ajout a ete transmise a l\'administrateur pour validation.',
                messages.WARNING
            )
            return HttpResponseRedirect(
                reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_changelist")
            )
        return super().response_add(request, obj, post_url_continue)


class ChefRestrictedMixin:
    """
    Mixin for Chef de Service role.
    - Chefs can: see and validate PendingRecords, create/edit operations directly (bypass tampon)
    - Chefs cannot: manage users
    """

    def has_add_permission(self, request):
        # Chefs can add
        if _is_chef_service(request.user):
            return True
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        # Chefs can edit
        if _is_chef_service(request.user):
            return True
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        # Chefs can delete
        if _is_chef_service(request.user):
            return True
        return super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        """
        Chefs bypass tampon system - save directly without creating PendingRecord.
        """
        # Chefs save directly without PendingRecord
        super().save_model(request, obj, form, change)
