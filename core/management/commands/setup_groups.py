# core/management/commands/setup_groups.py
"""
Crée les groupes de base : Administrateurs et Agents.
Usage : python manage.py setup_groups
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.apps import apps


class Command(BaseCommand):
    help = 'Crée les groupes Administrateurs et Agents avec leurs permissions'

    def handle(self, *args, **options):
        # Groupe Administrateurs — toutes les permissions
        admin_group, created = Group.objects.get_or_create(name='Administrateurs')
        all_perms = Permission.objects.all()
        admin_group.permissions.set(all_perms)
        self.stdout.write(self.style.SUCCESS(
            f'{"Créé" if created else "Mis à jour"} : groupe Administrateurs ({all_perms.count()} permissions)'
        ))

        # Groupe Agents — uniquement view + add (pas change, pas delete)
        agent_group, created = Group.objects.get_or_create(name='Agents')
        agent_perms = Permission.objects.filter(codename__startswith='view_') | \
                      Permission.objects.filter(codename__startswith='add_')
        agent_group.permissions.set(agent_perms)
        self.stdout.write(self.style.SUCCESS(
            f'{"Créé" if created else "Mis à jour"} : groupe Agents ({agent_perms.count()} permissions)'
        ))

        self.stdout.write(self.style.SUCCESS(
            '\nGroupes configurés. Assignez les utilisateurs à ces groupes dans l\'admin.'
        ))
