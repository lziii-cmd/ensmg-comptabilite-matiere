# core/urls.py
from django.urls import path
from core.views.exercice_switch import switch_exercice
#from core import views
from core.views import set_exercices_selection
from core.views.notifications import notifications_api



app_name = "core"

urlpatterns = [
    path("switch-exercice/", switch_exercice, name="core_switch_exercice"),
    path("exercices/set-selection/", set_exercices_selection, name="set_exercices_selection"),
    path("notifications/", notifications_api, name="notifications"),
    path("api/notifications/", notifications_api, name="api_notifications"),
]
