# core/views/dashboard.py
from decimal import Decimal
from datetime import datetime, timedelta
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.views.generic import TemplateView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse
from django.db.models import F, Q, Sum, DecimalField
from django.db.models.functions import TruncDate
from django.apps import apps


def _test_staff_user(user):
    """Check if user is staff."""
    return user.is_staff


class DashboardView(UserPassesTestMixin, TemplateView):
    """
    Dashboard view with KPIs and charts.
    Requires staff login.
    """
    template_name = 'admin/dashboard.html'
    
    def test_func(self):
        return self.request.user.is_staff
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get open exercice if available
        try:
            from core.utils.exercices import get_selected_exercices
            selected_exercices = get_selected_exercices(self.request)
            open_exercices = selected_exercices.filter(statut='OUVERT') if selected_exercices else None
        except:
            open_exercices = None
        
        # 1. KPI: Valeur totale stock (F CFA)
        context['total_stock_value'] = self._get_total_stock_value(open_exercices)
        
        # 2. KPI: Mouvements du jour
        context['movements_today'] = self._get_movements_today(open_exercices)
        
        # 3. KPI: Alertes actives (stock bas)
        context['active_alerts'] = self._get_active_alerts(open_exercices)
        
        # 4. KPI: Entrées en attente validation
        context['pending_entries'] = self._get_pending_entries()
        
        # Chart data (JSON for Chart.js)
        context['stock_evolution_chart'] = self._get_stock_evolution_data(open_exercices)
        context['top_consumptions_chart'] = self._get_top_consumptions_data(open_exercices)
        context['stock_by_category_chart'] = self._get_stock_by_category_data(open_exercices)
        
        # Recent activity
        context['recent_movements'] = self._get_recent_movements(open_exercices)
        
        return context
    
    def _get_total_stock_value(self, exercices):
        """Calculate total stock value in FCFA."""
        try:
            StockCourant = apps.get_model('inventory', 'StockCourant')
            qs = StockCourant.objects.all()
            
            if exercices:
                qs = qs.filter(exercice__in=exercices)
            
            total_value = qs.aggregate(
                total=Sum(
                    F('quantite') * F('cump'),
                    output_field=DecimalField()
                )
            )['total'] or Decimal('0')
            
            return {
                'value': float(total_value),
                'formatted': f"{total_value:,.0f} FCFA"
            }
        except Exception:
            return {'value': 0, 'formatted': '0 FCFA'}
    
    def _get_movements_today(self, exercices):
        """Count movements for today."""
        try:
            MouvementStock = apps.get_model('inventory', 'MouvementStock')
            today = datetime.now().date()
            qs = MouvementStock.objects.filter(date__date=today)
            
            if exercices:
                qs = qs.filter(exercice__in=exercices)
            
            count = qs.count()
            return {'count': count}
        except Exception:
            return {'count': 0}
    
    def _get_active_alerts(self, exercices):
        """Count active stock alerts (quantite <= seuil_min)."""
        try:
            StockCourant = apps.get_model('inventory', 'StockCourant')
            qs = StockCourant.objects.select_related('matiere').filter(
                Q(quantite__lte=F('matiere__seuil_min')) | Q(quantite__lte=10)
            )
            
            if exercices:
                qs = qs.filter(exercice__in=exercices)
            
            count = qs.count()
            return {'count': count}
        except Exception:
            return {'count': 0}
    
    def _get_pending_entries(self):
        """Count pending validation entries."""
        try:
            PendingRecord = apps.get_model('core', 'PendingRecord')
            count = PendingRecord.objects.filter(status='pending').count()
            return {'count': count}
        except Exception:
            return {'count': 0}
    
    def _get_stock_evolution_data(self, exercices):
        """Get stock evolution for last 12 months (line chart)."""
        try:
            MouvementStock = apps.get_model('inventory', 'MouvementStock')
            
            # Get data for last 12 months
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            
            qs = MouvementStock.objects.filter(date__gte=start_date).annotate(
                date_day=TruncDate('date')
            ).values('date_day').annotate(
                total_qty=Sum('quantite')
            ).order_by('date_day')
            
            if exercices:
                qs = qs.filter(exercice__in=exercices)
            
            labels = []
            data = []
            cumulative = Decimal('0')
            
            for item in qs:
                labels.append(item['date_day'].strftime('%Y-%m-%d'))
                cumulative += item['total_qty'] or Decimal('0')
                data.append(float(cumulative))
            
            return {
                'labels': labels,
                'datasets': [{
                    'label': 'Évolution du stock (12 mois)',
                    'data': data,
                    'borderColor': '#1d4ed8',
                    'backgroundColor': 'rgba(29, 78, 216, 0.1)',
                    'tension': 0.4,
                    'fill': True
                }]
            }
        except Exception:
            return {'labels': [], 'datasets': []}
    
    def _get_top_consumptions_data(self, exercices):
        """Top 5 consumptions for current month (bar chart)."""
        try:
            MouvementStock = apps.get_model('inventory', 'MouvementStock')
            
            # Current month
            today = datetime.now()
            start_date = today.replace(day=1)
            
            qs = MouvementStock.objects.filter(
                type='SORTIE',
                date__gte=start_date
            ).values('matiere__code_court', 'matiere__designation').annotate(
                total_qty=Sum('quantite')
            ).order_by('-total_qty')[:5]
            
            if exercices:
                qs = qs.filter(exercice__in=exercices)
            
            labels = [f"{item['matiere__code_court']}" for item in qs]
            data = [float(item['total_qty'] or 0) for item in qs]
            
            return {
                'labels': labels,
                'datasets': [{
                    'label': 'Top 5 consommations (mois)',
                    'data': data,
                    'backgroundColor': [
                        '#1d4ed8', '#3b82f6', '#60a5fa', '#93c5fd', '#bfdbfe'
                    ]
                }]
            }
        except Exception:
            return {'labels': [], 'datasets': []}
    
    def _get_stock_by_category_data(self, exercices):
        """Stock distribution by category (doughnut chart)."""
        try:
            StockCourant = apps.get_model('inventory', 'StockCourant')
            
            qs = StockCourant.objects.select_related(
                'matiere__categorie'
            ).values('matiere__categorie__libelle').annotate(
                total_value=Sum(
                    F('quantite') * F('cump'),
                    output_field=DecimalField()
                )
            ).order_by('-total_value')

            if exercices:
                qs = qs.filter(exercice__in=exercices)

            labels = [item['matiere__categorie__libelle'] or 'Sans catégorie' for item in qs]
            data = [float(item['total_value'] or 0) for item in qs]
            
            colors = [
                '#1d4ed8', '#3b82f6', '#60a5fa', '#93c5fd', '#bfdbfe',
                '#dbeafe', '#eff6ff', '#2563eb', '#1e40af', '#1e3a8a'
            ]
            
            return {
                'labels': labels,
                'datasets': [{
                    'label': 'Répartition par catégorie',
                    'data': data,
                    'backgroundColor': colors[:len(data)]
                }]
            }
        except Exception:
            return {'labels': [], 'datasets': []}
    
    def _get_recent_movements(self, exercices, limit=10):
        """Get 10 most recent movements."""
        try:
            MouvementStock = apps.get_model('inventory', 'MouvementStock')
            
            qs = MouvementStock.objects.select_related(
                'matiere', 'depot', 'exercice'
            ).order_by('-date')[:limit]
            
            if exercices:
                qs = qs.filter(exercice__in=exercices)
            
            movements = []
            for mvt in qs:
                movements.append({
                    'id': mvt.id,
                    'type': mvt.get_type_display(),
                    'date': mvt.date.strftime('%Y-%m-%d %H:%M'),
                    'matiere': mvt.matiere.code_court,
                    'quantite': float(mvt.quantite),
                    'depot': mvt.depot.nom if mvt.depot else 'N/A',
                    'reference': mvt.reference or '-',
                })
            
            return movements
        except Exception:
            return []
