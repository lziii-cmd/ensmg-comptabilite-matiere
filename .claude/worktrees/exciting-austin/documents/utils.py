# documents/utils.py
"""
Utilitaires de génération PDF pour les documents officiels ENSMG.

Utilise WeasyPrint si disponible (pip install weasyprint).
Sinon, retourne du HTML prêt à imprimer via le navigateur (Ctrl+P).
"""
from django.http import HttpResponse
from django.template.loader import render_to_string

try:
    from weasyprint import HTML as WeasyHTML
    WEASYPRINT_OK = True
except Exception:
    # WeasyPrint nécessite GTK/Pango sur Windows (libgobject-2.0-0).
    # Sans ces bibliothèques, on bascule automatiquement sur le mode
    # HTML + impression navigateur (Ctrl+P → Enregistrer en PDF).
    WEASYPRINT_OK = False


SEUIL_PV_RECEPTION = 300_000  # FCFA — ≤ 300 000 F : bon d'entrée simple ; > 300 000 F : PV de réception obligatoire (Art. 7 I. Gle n°04)


def render_pdf(request, template_name: str, context: dict, filename: str = "document.pdf"):
    """
    Génère un PDF à partir d'un template HTML.

    Si WeasyPrint est installé  → retourne un PDF téléchargeable.
    Sinon                       → retourne l'HTML avec CSS d'impression
                                  (le navigateur peut imprimer en PDF via Ctrl+P).
    """
    html_str = render_to_string(template_name, context, request=request)

    if WEASYPRINT_OK:
        pdf_bytes = WeasyHTML(
            string=html_str,
            base_url=request.build_absolute_uri("/"),
        ).write_pdf()
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response

    # Fallback : HTML pur — la barre d'impression dans _base.html
    # contient déjà un bouton "Imprimer" (window.print()). Pas besoin d'auto-trigger.
    return HttpResponse(html_str)


def fmt_montant(valeur) -> str:
    """Formate un montant en FCFA : 1 250 000 F CFA"""
    try:
        v = int(valeur)
        return f"{v:,} F CFA".replace(",", " ")
    except (TypeError, ValueError):
        return "— F CFA"


def fmt_qte(valeur) -> str:
    """Formate une quantité sans zéros inutiles : 5 / 2,5"""
    try:
        from decimal import Decimal
        d = Decimal(str(valeur))
        # Enlever les zéros trailing
        d = d.normalize()
        return str(d)
    except Exception:
        return str(valeur)
