from django.shortcuts import redirect
from django.views import View
from django.shortcuts import render


class LandingView(View):
    """Page d'accueil publique. Redirige vers le tableau de bord si déjà connecté."""

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('frontend:dashboard')
        return render(request, 'landing.html')
