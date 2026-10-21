import json
from collections import Counter
from pathlib import Path

import httpx
import pytest

from aicandidate.providers.greenhouse import fetch_jobs

FIXTURES = Path(__file__).parent / "fixtures"


# Fonction de chargement des fixtures
def charger_fixture(nom):
    return json.loads((FIXTURES / nom).read_text(encoding="utf-8"))


# création des fixtures pour les tests
@pytest.fixture
def donnees_stripe():
    return charger_fixture("greenhouse_stripe.json")


@pytest.fixture
def donnees_doctolib():
    return charger_fixture("greenhouse_doctolib.json")


def faux_client(reponse_par_entreprise):
    """Construit un client httpx dont le faux serveur renvoie, pour chaque
    identifiant d'entreprise, la réponse prévue dans le dictionnaire `reponses`."""

    def faux_serveur(request):
        # "/v1/boards/stripe/jobs" -> ["", "v1", "boards", "stripe", "jobs"]
        board_token = request.url.path.split("/")[3]

        if board_token not in reponse_par_entreprise:
            raise AssertionError(f"Requête inattendue : {request.url}")

        return reponse_par_entreprise[board_token]

    return httpx.Client(transport=httpx.MockTransport(faux_serveur))


def test_renvoie_les_offres_d_une_entreprise(donnees_stripe):
    # Ce test créé un faux serveur qui renvoie une réponse connue (la fixture) et vérifie que la fonction fetch_jobs() renvoie bien les offres attendues.
    # Arrange : on prépare un faux serveur qui renvoie la fixture

    client = faux_client(
        {
            "stripe": httpx.Response(200, json=donnees_stripe),
        }
    )

    # Act : on appelle la fonction testée pour les différentes configurations
    offres = fetch_jobs(["stripe"], client=client)

    # Assert : on vérifie le résultat
    # 1 renvoie les offres d'une entreprise
    assert len(offres) == len(donnees_stripe["jobs"])


def test_renvoie_les_offres_de_plusieurs_entreprises(donnees_stripe, donnees_doctolib):
    # Ce test créé un faux serveur qui renvoie une réponse connue (la fixture) et vérifie que la fonction fetch_jobs() renvoie bien
    # les offres attendues pour plusieurs entreprises

    client = faux_client(
        {
            "stripe": httpx.Response(200, json=donnees_stripe),
            "doctolib": httpx.Response(200, json=donnees_doctolib),
        }
    )

    # Act : on appelle la fonction testée
    offres = fetch_jobs(["stripe", "doctolib"], client=client)

    # Assert : on vérifie le résultat
    assert len(offres) == len(donnees_stripe["jobs"]) + len(donnees_doctolib["jobs"])


def test_chaque_offre_indique_de_quelle_entreprise_elle_vient(donnees_stripe, donnees_doctolib):
    # Ce test créé un faux serveur qui renvoie une réponse connue (la fixture) et vérifie que la fonction fetch_jobs() renvoie bien
    # des offres qui précisent le nom de l'entreprise

    client = faux_client(
        {
            "stripe": httpx.Response(200, json=donnees_stripe),
            "doctolib": httpx.Response(200, json=donnees_doctolib),
        }
    )

    # Act : on appelle la fonction testée
    offres = fetch_jobs(["stripe", "doctolib"], client=client)

    # Assert : on vérifie que chaque offre contient le nom de l'entreprise
    for offre in offres:
        assert "board_token" in offre

    compte = Counter(offre["board_token"] for offre in offres)
    assert compte == {
        "stripe": len(donnees_stripe["jobs"]),
        "doctolib": len(donnees_doctolib["jobs"]),
    }


def test_une_entreprise_inexistante_est_ignoree(donnees_stripe, donnees_doctolib, caplog):
    # Ce test créé un faux serveur qui renvoie une réponse connue (la fixture) et vérifie que la fonction fetch_jobs() renvoie bien
    # ne prend pas en compte une entreprise qui renvoie une erreur 404, mais continue de traiter les autres entreprises
    # et renvoie un avertissement dans la log.

    # Arrange : on prépare un faux serveur qui renvoie la fixture pour stripe et doctolib, et une erreur 404 pour une entreprise inexistante
    client = faux_client(
        {
            "stripe": httpx.Response(200, json=donnees_stripe),
            "entreprise_inexistante": httpx.Response(404),
            "doctolib": httpx.Response(200, json=donnees_doctolib),
        }
    )

    # Act : on appelle la fonction testée
    offres = fetch_jobs(["stripe", "entreprise_inexistante", "doctolib"], client=client)

    # Assert : on vérifie le résultat
    assert len(offres) == len(donnees_stripe["jobs"]) + len(donnees_doctolib["jobs"])

    # Assert : un seul avertissement, qui mentionne l'entreprise fautive
    avertissements = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(avertissements) == 1
    assert "entreprise_inexistante" in avertissements[0].getMessage()


@pytest.mark.parametrize("code", [429, 500, 503])
def test_signale_les_erreurs_serveur(code):
    # Ce test créé 3 faux serveurs qui renvoient respectivement une erreur 429, 500 et 503
    # Il nous permet de vérifier que la fonction fetch_jobs est capable d'identifier et de signaler les erreurs de serveur de greenhouse.

    # Arrange : le faux serveur renvoie une erreur avec la valeur de code
    def faux_serveur(_request):
        return httpx.Response(code)

    client = httpx.Client(transport=httpx.MockTransport(faux_serveur))

    # Act + Assert: on appelle la fonction testée : on vérifie directement que python lève la bonne exception
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        fetch_jobs(["stripe"], client=client)

    assert exc_info.value.response.status_code == code
