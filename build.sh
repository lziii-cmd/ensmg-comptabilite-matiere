#!/usr/bin/env bash
# Script de build exécuté par Render avant de démarrer le serveur.
set -o errexit  # quitter immédiatement en cas d'erreur

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py seed_initial
