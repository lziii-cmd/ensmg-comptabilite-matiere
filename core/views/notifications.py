import json
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.apps import apps
from django.urls import reverse, NoReverseMatch
from django.utils import timezone
from datetime import timedelta


def format_time_ago(dt):
    """Format datetime as 'il y a X minutes/heures/jours'"""
    now = timezone.now()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "à l'instant"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"il y a {minutes} minute{'s' if minutes > 1 else ''}"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"il y a {hours} heure{'s' if hours > 1 else ''}"
    else:
        days = int(seconds / 86400)
        return f"il y a {days} jour{'s' if days > 1 else ''}"


@staff_member_required
def notifications_api(request):
    """
    API endpoint that returns unread notifications as JSON for the current user.
    Supports filtering and marking as read.
    
    GET: return {unread_count, notifications: [{id, type, titre, message, lue, created_at, detail_url}]}
    POST with {id: N}: mark notification N as read
    POST with {mark_all: true}: mark all as read
    """
    try:
        from core.models import Notification
        
        # Handle POST requests (mark as read)
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
            
            # Mark all as read
            if data.get('mark_all'):
                Notification.objects.filter(
                    destinataire=request.user,
                    lue=False
                ).update(lue=True)
                return JsonResponse({'success': True})
            
            # Mark specific notification as read
            notif_id = data.get('id')
            if notif_id:
                notification = Notification.objects.filter(
                    id=notif_id,
                    destinataire=request.user
                ).first()
                if notification:
                    notification.mark_as_read()
                    return JsonResponse({'success': True})
                return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)
            
            return JsonResponse({'success': False, 'error': 'Missing id or mark_all'}, status=400)
        
        # GET: Return all notifications for current user (read and unread)
        notifications = Notification.objects.filter(
            destinataire=request.user
        ).order_by('-created_at')[:20]
        
        data = []
        for notif in notifications:
            # Determine detail URL using stored app_label / model_name / object_id when available
            detail_url = None
            if notif.app_label and notif.model_name and notif.object_id:
                # Essayer la vue détail, puis change, puis changelist en fallback
                try:
                    detail_url = reverse(
                        f'admin:{notif.app_label}_{notif.model_name}_detail',
                        args=[notif.object_id]
                    )
                except NoReverseMatch:
                    try:
                        detail_url = reverse(
                            f'admin:{notif.app_label}_{notif.model_name}_change',
                            args=[notif.object_id]
                        )
                    except NoReverseMatch:
                        try:
                            detail_url = reverse(
                                f'admin:{notif.app_label}_{notif.model_name}_changelist'
                            )
                        except NoReverseMatch:
                            detail_url = None
            elif notif.type_notif == 'STOCK_BAS' and notif.object_id:
                # Fallback STOCK_BAS sans app_label stocké
                try:
                    detail_url = reverse('admin:catalog_matiere_detail', args=[notif.object_id])
                except NoReverseMatch:
                    detail_url = f'/admin/catalog/matiere/{notif.object_id}/change/'
            elif notif.type_notif == 'VALIDATION':
                # Fallback: list of pending records filtered by pending status
                detail_url = '/admin/core/pendingrecord/?status=pending'
            elif notif.type_notif in ('REJET', 'VALIDEE'):
                # Point to the list so the agent can see history
                detail_url = '/admin/core/pendingrecord/'
            else:
                detail_url = None
            
            item = {
                'id': notif.id,
                'type': notif.type_notif,
                'titre': notif.titre,
                'message': notif.message,
                'lue': notif.lue,
                'created_at': format_time_ago(notif.created_at),
                'detail_url': detail_url,
            }
            
            data.append(item)
        
        unread_count = Notification.objects.filter(
            destinataire=request.user,
            lue=False
        ).count()
        
        return JsonResponse({
            'notifications': data,
            'unread_count': unread_count,
        })
    
    except Exception as e:
        return JsonResponse({
            'error': str(e),
        }, status=400)


# LEGACY: Keep old endpoint for backwards compatibility
@staff_member_required
def notifications_api_legacy(request):
    notifications = []

    # 1. Stocks bas (quantite <= seuil_min ou <= 10)
    try:
        from django.db.models import F, Q
        StockCourant = apps.get_model('inventory', 'StockCourant')
        bas = StockCourant.objects.select_related('matiere', 'depot').filter(
            Q(quantite__lte=F('matiere__seuil_min')) | Q(quantite__lte=10)
        ).order_by('quantite')[:15]
        for sc in bas:
            notifications.append({
                'type': 'warning' if sc.quantite > 0 else 'danger',
                'icon': '⚠️' if sc.quantite > 0 else '🔴',
                'title': f'Stock bas : {sc.matiere.code_court}',
                'message': f'{sc.matiere.designation} — {sc.quantite} en stock ({sc.depot.nom})',
                'url': f'/admin/inventory/stockcourant/?q={sc.matiere.code_court}',
            })
    except Exception:
        pass

    # 2. Approbations en attente (si le modèle existe)
    try:
        PendingRecord = apps.get_model('core', 'PendingRecord')
        pending_count = PendingRecord.objects.filter(status='pending').count()
        if pending_count > 0 and request.user.is_superuser:
            notifications.insert(0, {
                'type': 'info',
                'icon': '📋',
                'title': f'{pending_count} ajout(s) en attente',
                'message': 'Des agents ont soumis des données à valider.',
                'url': '/admin/core/pendingrecord/',
            })
    except Exception:
        pass

    return JsonResponse({'notifications': notifications, 'count': len(notifications)})
