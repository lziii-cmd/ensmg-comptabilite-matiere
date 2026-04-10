"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to view. Home
    3. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

# Dashboard must come BEFORE the admin site so it takes precedence
from core.views.dashboard import DashboardView
from core.views.notifications import notifications_api
from catalog.views.admin_comptes_view import comptes_dashboard
from catalog.views.admin_categories_view import categories_dashboard, sous_categories_dashboard
from core.views.admin_referentiels_view import services_dashboard, depots_dashboard
from frontend.views.landing import LandingView

urlpatterns = [
    path('', LandingView.as_view(), name='landing'),
    path('admin/dashboard/', DashboardView.as_view(), name='dashboard'),
    path('admin/api/notifications/', notifications_api, name='api_notifications'),
    # Tableau de bord comptes d'imputation (3 niveaux)
    path('admin/comptes-imputation/', comptes_dashboard, name='admin_comptes_dashboard'),
    # Dashboards cards catégories
    path('admin/categories/', categories_dashboard, name='admin_categories_dashboard'),
    path('admin/sous-categories/', sous_categories_dashboard, name='admin_sous_categories_dashboard'),
    # Dashboards cards services et dépôts
    path('admin/services/', services_dashboard, name='admin_services_dashboard'),
    path('admin/depots/', depots_dashboard, name='admin_depots_dashboard'),
    path('admin/', admin.site.urls),
    path("core/", include(("core.urls", "core"), namespace="core")),
    path("documents/", include(("documents.urls", "documents"), namespace="documents")),
    # Frontend interface principale (v3)
    path("app/", include(("frontend.urls", "frontend"), namespace="frontend")),
]
