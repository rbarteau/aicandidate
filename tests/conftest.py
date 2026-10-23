import json
from pathlib import Path

import httpx
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


# Fonction de chargement des fixtures
@pytest.fixture
def charger_fixture():  # aucun paramètre pour pytest
    def _charger(nom):  # la fonction que le test va appeler
        return json.loads((FIXTURES / nom).read_text(encoding="utf-8"))

    return _charger  # on renvoie la fonction, sans l'appeler


@pytest.fixture
def faux_client():
    """Construit un client httpx dont le faux serveur renvoie, pour chaque
    identifiant d'entreprise, la réponse prévue dans le dictionnaire `reponses`."""

    # la fixture ne peut pas prendre de paramètre, donc on renvoie une fonction qui prend le paramètre
    def _construire(reponse_par_entreprise):
        def faux_serveur(request):
            # greenhouse : "/v1/boards/stripe/jobs" -> ["", "v1", "boards", "stripe", "jobs"]
            # lever : "/v0/postings/blablacar" -> ["", "v0", "postings", "blablacar"]
            entreprise = request.url.path.split("/")[3]
            if entreprise not in reponse_par_entreprise:
                raise AssertionError(f"Requête inattendue : {request.url}")
            return reponse_par_entreprise[entreprise]

        return httpx.Client(transport=httpx.MockTransport(faux_serveur))

    return _construire
