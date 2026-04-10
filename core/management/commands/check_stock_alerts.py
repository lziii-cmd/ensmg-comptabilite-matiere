# core/management/commands/check_stock_alerts.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db.models import F, Q
from django.apps import apps
from datetime import datetime


class Command(BaseCommand):
    help = 'Check stock levels and create notifications for low stock items and pending validations'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting stock alerts check...'))
        
        # Get all staff users (for stock alerts)
        staff_users = User.objects.filter(is_staff=True)
        
        if not staff_users.exists():
            self.stdout.write(self.style.WARNING('No staff users found'))
            return
        
        # Check for low stock items
        self._check_low_stock_alerts(staff_users)
        
        # Check for pending records (for chefs and admins)
        self._check_pending_validations()
        
        self.stdout.write(self.style.SUCCESS('Stock alerts check completed!'))
    
    def _check_low_stock_alerts(self, staff_users):
        """Create notifications for low stock items."""
        try:
            from inventory.models import StockCourant
            from core.models import Notification
            from core.utils.exercices import get_open_exercices
            
            # Get open exercices
            open_exercices = get_open_exercices()
            if not open_exercices:
                self.stdout.write(self.style.WARNING('No open exercices found'))
                return
            
            # Find low stock items
            low_stock = StockCourant.objects.select_related(
                'matiere', 'depot', 'exercice'
            ).filter(
                exercice__in=open_exercices,
                quantite__lte=F('matiere__seuil_min')
            )
            
            count = 0
            for stock in low_stock:
                # Create notification for each staff user
                for user in staff_users:
                    notification, created = Notification.create_or_get_today(
                        destinataire=user,
                        type_notif=Notification.Type.STOCK_BAS,
                        titre=f'Stock bas: {stock.matiere.code_court}',
                        message=f'{stock.matiere.designation} - Quantité: {stock.quantite} (Seuil: {stock.matiere.seuil_min}) - Dépôt: {stock.depot.nom}',
                        app_label='catalog',
                        model_name='matiere',
                        object_id=stock.matiere.id
                    )
                    if created:
                        count += 1
            
            self.stdout.write(self.style.SUCCESS(f'Created {count} stock alert notifications'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error checking stock alerts: {e}'))
    
    def _check_pending_validations(self):
        """Create notifications for pending validations."""
        try:
            from core.models import PendingRecord, Notification
            
            # Get admin and chef de service users
            try:
                admin_group = Group.objects.get(name='Administrateurs')
                chef_group = Group.objects.get(name='Chefs de Service')
                users = User.objects.filter(
                    Q(groups=admin_group) | Q(groups=chef_group) | Q(is_superuser=True)
                ).distinct()
            except Group.DoesNotExist:
                users = User.objects.filter(is_superuser=True)
            
            if not users.exists():
                self.stdout.write(self.style.WARNING('No admin/chef users found'))
                return
            
            # Find pending records
            pending = PendingRecord.objects.filter(status='pending')
            
            count = 0
            for pending_record in pending:
                # Create notification for each admin/chef user
                for user in users:
                    notification, created = Notification.create_or_get_today(
                        destinataire=user,
                        type_notif=Notification.Type.VALIDATION,
                        titre=f'Validation requise: {pending_record.verbose_name}',
                        message=f'Saisie soumise par {pending_record.submitted_by.get_full_name() or pending_record.submitted_by.username}',
                        app_label='core',
                        model_name='pendingrecord',
                        object_id=pending_record.id
                    )
                    if created:
                        count += 1
            
            if count > 0:
                self.stdout.write(self.style.SUCCESS(f'Created {count} validation notifications'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error checking pending validations: {e}'))
