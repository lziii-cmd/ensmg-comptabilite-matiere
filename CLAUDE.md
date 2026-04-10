# Standards & Bonnes Pratiques — Projets Django

Ce fichier sert de référence pour tout développement sur ce projet. Il doit être lu et respecté par tout développeur ou assistant IA intervenant sur le code.

---

## 1. ARCHITECTURE

- Le projet est structuré en **applications Django séparées** par domaine métier (`core`, `catalog`, `purchasing`, `inventory`, `documents`, `frontend`). Ne jamais mélanger les responsabilités entre apps.
- Les **modèles** sont découpés en fichiers individuels dans un sous-dossier `models/` avec un `__init__.py` qui les réexporte tous.
- Les **admins** sont découpés de la même façon dans un sous-dossier `admin/`.
- Les **vues** sont regroupées par fonctionnalité dans un sous-dossier `views/`.
- La **logique métier** (calculs, validations complexes, algorithmes) doit vivre dans `services/`, jamais directement dans les vues ou les modèles.
- Les **signaux** sont dans `signals.py` (ou `signals/`) et ne doivent contenir que des déclenchements d'effets secondaires (mise à jour de champs dérivés, notifications, audit), pas de logique métier.

---

## 2. CONFIGURATION & SÉCURITÉ

### Settings
- Toujours utiliser **trois fichiers de settings** : `base.py`, `dev.py`, `prod.py`.
- `base.py` : ne jamais y mettre `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASES`.
- `dev.py` : `DEBUG = True`, SQLite acceptable, email backend = console.
- `prod.py` : appliquer **obligatoirement** toutes ces directives :
  ```python
  SECRET_KEY = os.environ['DJANGO_SECRET_KEY']  # Plante si absent — c'est voulu
  DEBUG = False
  SECURE_SSL_REDIRECT = True
  SESSION_COOKIE_SECURE = True
  CSRF_COOKIE_SECURE = True
  SECURE_HSTS_SECONDS = 31536000
  SECURE_HSTS_INCLUDE_SUBDOMAINS = True
  SECURE_HSTS_PRELOAD = True
  SECURE_CONTENT_TYPE_NOSNIFF = True
  X_FRAME_OPTIONS = 'DENY'
  CONN_MAX_AGE = 60
  ```

### Secrets
- Aucun secret (clé API, mot de passe, SECRET_KEY) ne doit être hardcodé dans le code.
- Toujours utiliser `os.environ` ou `python-decouple`.
- Un fichier `.env.example` doit lister toutes les variables requises (sans leurs valeurs).

### Authentification & Autorisations
- Toute vue frontend doit hériter de `LoginRequiredMixin`.
- Les vues de génération de documents utilisent `@staff_member_required`.
- Toute action sensible (validation, suppression) doit vérifier les permissions Django (`has_perm`).

---

## 3. MODÈLES & VALIDATION

### Règles générales
- Utiliser `BigAutoField` comme clé primaire par défaut (`DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'`).
- Toujours définir une méthode `__str__` lisible sur chaque modèle.
- Toujours définir `class Meta` avec au minimum `verbose_name` et `verbose_name_plural` en français.

### Validation
- La validation métier se place dans la méthode `clean()` du modèle. Elle doit lever `ValidationError` avec un message clair.
- **Règle critique** : avant toute sortie ou transfert de stock, valider que la quantité disponible est suffisante. Ne jamais laisser un stock devenir négatif :
  ```python
  def clean(self):
      if self.type == "SORTIE":
          courant = StockCourant.objects.filter(...).first()
          if courant is None or self.quantite > courant.quantite:
              raise ValidationError("Quantité insuffisante en stock.")
  ```

### Champs calculés et codes auto-générés
- Les totaux (HT, TVA, TTC) sont toujours recalculés via une méthode dédiée `recompute_totaux()` appelée dans `save()`.
- Les codes auto-générés (ex : `ACH-FOURNISSEUR-2025-00001`) utilisent le modèle `Sequence` ou `FournisseurSequence` pour garantir l'unicité même en cas de concurrence.
- Le pattern double-save (1er save pour obtenir le PK, 2e pour les champs dérivés) est accepté mais doit être documenté avec un commentaire.

### Indexes
- Tout champ utilisé fréquemment en filtre (`exercice`, `matiere`, `depot`, `fournisseur`) doit avoir un index déclaré dans `Meta.indexes`.
- Les combinaisons de champs uniques utilisent `UniqueConstraint` (pas `unique_together` déprécié).

---

## 4. SIGNAUX

- Les signaux ne doivent **jamais** utiliser `except: pass` silencieux. Toute exception doit être loggée :
  ```python
  import logging
  logger = logging.getLogger(__name__)

  try:
      # logique du signal
  except Exception:
      logger.error("Erreur dans le signal post_save de MouvementStock", exc_info=True)
  ```
- Les signaux de mise à jour de stock (`post_save`, `post_delete` sur `MouvementStock`) doivent capturer l'état **avant** modification via `pre_save` (stocker dans `instance._old_tuple`).
- Les signaux d'audit enregistrent : utilisateur, IP (proxy-aware via `HTTP_X_FORWARDED_FOR`), action, timestamp, valeurs avant/après.

---

## 5. SERVICES

- Toute opération qui modifie plusieurs tables à la fois doit être encapsulée dans `@transaction.atomic`.
- Les services retournent des objets métier ou lèvent des exceptions explicites (jamais de codes de retour entiers ou de booléens ambigus).
- Ne jamais laisser du code mort commenté dans les services. Si une logique est obsolète, la supprimer et committer avec un message explicatif.

---

## 6. TESTS

- Chaque modèle doit avoir des tests couvrant au minimum :
  - Création standard et vérification des champs auto-générés
  - Validations : champs obligatoires, contraintes d'unicité, règles métier (ex : quantité > 0)
  - La méthode `__str__`
- Chaque service métier doit avoir des tests de bout en bout (ex : séquence achat → lignes → calcul totaux → mise à jour stock).
- Les tests de concurrence (génération de codes sans collision) sont obligatoires pour tout modèle utilisant une séquence.
- Nommer les tests en français, de façon descriptive :
  ```python
  def test_quantite_nulle_leve_erreur(self):
  def test_stock_insuffisant_leve_erreur(self):
  def test_codes_sequentiels_sans_collision(self):
  ```

---

## 7. LOGGING

Configurer le logging dans `settings/base.py` de façon complète :

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 5 * 1024 * 1024,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

En développement, surcharger le niveau à `DEBUG`.
Ne jamais utiliser `print()` dans le code de production — toujours `logger.info()`, `logger.warning()`, `logger.error()`.

---

## 8. PERFORMANCE

- Toujours utiliser `select_related()` pour les ForeignKey et `prefetch_related()` pour les ManyToMany dans les vues qui affichent des listes.
- Toujours paginer les listes (minimum 50 résultats par page) :
  ```python
  from django.core.paginator import Paginator
  paginator = Paginator(queryset, 50)
  ```
- Utiliser `.only()` ou `.values()` pour les requêtes qui n'ont besoin que de certains champs (ex : context_processors, menus de navigation).
- Les requêtes fréquentes et coûteuses (ex : valeur totale du stock) doivent être mises en cache avec un TTL raisonnable dès que le volume de données dépasse 10 000 lignes.

---

## 9. INTERFACE ADMIN

- Chaque modèle métier **doit** être enregistré dans l'admin avec `@admin.register(MonModele)`.
- Chaque `ModelAdmin` doit définir au minimum : `list_display`, `list_filter`, `search_fields`.
- Les champs en lecture seule (totaux calculés, codes auto) sont déclarés dans `readonly_fields`.
- Les inlines (`TabularInline`) affichent les champs calculés via `readonly_fields` et non via le formulaire.
- Les actions de validation importantes (ex : valider un achat, clôturer un exercice) passent par une page de confirmation intermédiaire.

---

## 10. GÉNÉRATION DE DOCUMENTS

- Utiliser **WeasyPrint** pour la conversion HTML → PDF.
- Chaque document a son propre template dans `templates/documents/`.
- Le routeur de documents décide du type de document selon des règles métier explicites (ex : montant seuil pour PV vs bon d'entrée).
- Les templates de documents utilisent un template de base `_base.html` commun (en-tête institution, pied de page, logo).
- Les noms de fichiers PDF générés suivent le pattern : `{type_doc}_{code_objet}.pdf` (ex : `bon_entree_ACH-ELECTRO-2025-00001.pdf`).

---

## 11. DÉPENDANCES

- Ne pas inclure de bibliothèques dans `requirements.txt` si elles ne sont pas activement utilisées dans le code.
- Vérifier avant d'ajouter une dépendance si Django natif ne couvre pas déjà le besoin.
- Séparer `requirements.txt` (prod) et `requirements-dev.txt` (Faker, outils de test, debug toolbar).

---

## 12. CHECKLIST AVANT CHAQUE COMMIT

- [ ] Aucun `print()` dans le code (remplacer par `logger`)
- [ ] Aucun `except: pass` silencieux
- [ ] Aucun secret hardcodé
- [ ] Les nouvelles validations métier sont dans `clean()` et couvertes par un test
- [ ] Les nouveaux champs en base ont une migration générée et testée
- [ ] Les vues de liste ont une pagination
- [ ] Les nouvelles vues sont protégées par `LoginRequiredMixin` ou `@staff_member_required`
- [ ] Aucun code mort ou commenté laissé dans les services

---

## 13. CHECKLIST AVANT MISE EN PRODUCTION

- [ ] `DEBUG = False` confirmé
- [ ] `SECRET_KEY` via variable d'environnement
- [ ] Toutes les directives HTTPS/HSTS activées
- [ ] Base PostgreSQL configurée et migrée
- [ ] Logging avec rotation activé
- [ ] Fichier `.env.example` à jour
- [ ] Tous les tests passent (`python manage.py test`)
- [ ] `requirements.txt` ne contient que les dépendances réellement utilisées
