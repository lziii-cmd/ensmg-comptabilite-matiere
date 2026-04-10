from .dashboard import DashboardView
from .achats import AchatsListView, AchatDetailView
from .catalog import (
    CategoriesListView, CategorieDetailView,
    MatieresListView, MatiereDetailView,
    ComptesListView,
)
from .entrees import (
    DonsListView, DonDetailView,
    LegsListView, LegsDetailView,
    DotationsListView,
)
from .prets import (
    PretsListView, PretDetailView,
    RetourPretDetailView,
    RetoursFournisseursListView,
)
from .stock import (
    MouvementsListView, MouvementDetailView,
    StockCourantListView,
    StockActuelListView,
    SortiesStockListView,
    TransfertsListView,
    SortiesDefinitivesListView,
    ReformeListView,
)
from .referentiels import (
    FournisseursListView,
    DonateursListView,
    DepotsListView,
    ServicesListView,
    UnitesListView,
)
from .system import (
    ExercicesListView,
    LivreJournalView,
    NotificationsView,
    ProfilView,
    SettingsView,
)
