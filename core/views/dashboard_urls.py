# core/views/dashboard_urls.py
from django.urls import path
from .dashboard import DashboardView

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
]
