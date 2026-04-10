# documents/views/sortie_views.py
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404

from documents.utils import render_pdf
from inventory.models import OperationSortie


@staff_member_required
def bon_sortie(request, pk):
    op = get_object_or_404(
        OperationSortie.objects.prefetch_related("lignes__matiere__unite", "lignes__matiere__sous_compte"),
        pk=pk,
    )
    nb_lignes = op.lignes.count()
    context = {
        "op": op,
        "date_doc": op.date_sortie,
        "exercice_label": f"Exercice {op.date_sortie.year}",
        "empty_rows": range(max(0, 8 - nb_lignes)),
    }
    return render_pdf(
        request,
        "documents/bon_sortie.html",
        context,
        filename=f"bon_sortie_{op.code}.pdf",
    )
