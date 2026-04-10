# frontend/urls.py
from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Exercices
    path('exercices/', views.ExercicesListView.as_view(), name='exercices'),

    # Catalogue
    path('categories/', views.CategoriesListView.as_view(), name='categories'),
    path('categories/<int:pk>/', views.CategorieDetailView.as_view(), name='categorie_detail'),
    path('matieres/', views.MatieresListView.as_view(), name='matieres'),
    path('matieres/<int:pk>/', views.MatiereDetailView.as_view(), name='matiere_detail'),
    path('comptes/', views.ComptesListView.as_view(), name='comptes'),

    # Achats
    path('achats/', views.AchatsListView.as_view(), name='achats'),
    path('achats/<int:pk>/', views.AchatDetailView.as_view(), name='achat_detail'),

    # Entrées
    path('dons/', views.DonsListView.as_view(), name='dons'),
    path('dons/<int:pk>/', views.DonDetailView.as_view(), name='don_detail'),
    path('legs/', views.LegsListView.as_view(), name='legs'),
    path('legs/<int:pk>/', views.LegsDetailView.as_view(), name='legs_detail'),
    path('dotations/', views.DotationsListView.as_view(), name='dotations'),

    # Prêts
    path('prets/', views.PretsListView.as_view(), name='prets'),
    path('prets/<int:pk>/', views.PretDetailView.as_view(), name='pret_detail'),
    path('prets/retours/<int:pk>/', views.RetourPretDetailView.as_view(), name='retour_pret_detail'),
    path('retours-fournisseurs/', views.RetoursFournisseursListView.as_view(), name='retours_fournisseurs'),

    # Stock
    path('mouvements/', views.MouvementsListView.as_view(), name='mouvements'),
    path('mouvements/<int:pk>/', views.MouvementDetailView.as_view(), name='mouvement_detail'),
    path('stock/courant/', views.StockCourantListView.as_view(), name='stock_courant'),
    path('stock/actuel/', views.StockActuelListView.as_view(), name='stock_actuel'),
    path('stock/sorties/', views.SortiesStockListView.as_view(), name='sorties_stock'),
    path('transferts/', views.TransfertsListView.as_view(), name='transferts'),
    path('sorties-definitives/', views.SortiesDefinitivesListView.as_view(), name='sorties_definitives'),
    path('reforme/', views.ReformeListView.as_view(), name='reforme'),

    # Référentiels
    path('fournisseurs/', views.FournisseursListView.as_view(), name='fournisseurs'),
    path('donateurs/', views.DonateursListView.as_view(), name='donateurs'),
    path('depots/', views.DepotsListView.as_view(), name='depots'),
    path('services/', views.ServicesListView.as_view(), name='services'),
    path('unites/', views.UnitesListView.as_view(), name='unites'),

    # Système
    path('livre-journal/', views.LivreJournalView.as_view(), name='livre_journal'),
    path('notifications/', views.NotificationsView.as_view(), name='notifications'),
    path('profil/', views.ProfilView.as_view(), name='profil'),
    path('parametres/', views.SettingsView.as_view(), name='settings'),
]
