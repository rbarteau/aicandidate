from collections import Counter

import httpx
import pytest

from aicandidate.providers.lever import fetch_jobs


# création des fixtures pour les tests
@pytest.fixture
def donnees_blablacar(charger_fixture):
    return charger_fixture("lever_blablacar.json")


@pytest.fixture
def donnees_qonto(charger_fixture):
    return charger_fixture("lever_qonto.json")


def test_renvoie_les_offres_d_une_entreprise(donnees_blablacar, faux_client):

    client = faux_client(
        {
            "blablacar": httpx.Response(200, json=donnees_blablacar),
        }
    )

    # Act : on appelle la fonction testée pour les différentes configurations
    offres = fetch_jobs(["blablacar"], client=client)

    # Assert : on vérifie le résultat
    # 1 renvoie les offres d'une entreprise
    assert len(offres) == len(donnees_blablacar)


def test_renvoie_les_offres_de_plusieurs_entreprises(donnees_blablacar, donnees_qonto, faux_client):
    # Ce test créé un faux serveur qui renvoie une réponse connue (la fixture) et vérifie que la fonction fetch_jobs() renvoie bien
    # les offres attendues pour plusieurs entreprises

    client = faux_client(
        {
            "blablacar": httpx.Response(200, json=donnees_blablacar),
            "qonto": httpx.Response(200, json=donnees_qonto),
        }
    )

    # Act : on appelle la fonction testée
    offres = fetch_jobs(["blablacar", "qonto"], client=client)

    # Assert : on vérifie le résultat
    assert len(offres) == len(donnees_blablacar) + len(donnees_qonto)


def test_chaque_offre_indique_de_quelle_entreprise_elle_vient(
    donnees_blablacar, donnees_qonto, faux_client
):
    # Ce test créé un faux serveur qui renvoie une réponse connue (la fixture) et vérifie que la fonction fetch_jobs() renvoie bien
    # des offres qui précisent le nom de l'entreprise

    client = faux_client(
        {
            "blablacar": httpx.Response(200, json=donnees_blablacar),
            "qonto": httpx.Response(200, json=donnees_qonto),
        }
    )

    # Act : on appelle la fonction testée
    offres = fetch_jobs(["blablacar", "qonto"], client=client)

    # Assert : on vérifie que chaque offre contient le nom de l'entreprise
    for offre in offres:
        assert "board_token" in offre

    compte = Counter(offre["board_token"] for offre in offres)
    assert compte == {
        "blablacar": len(donnees_blablacar),
        "qonto": len(donnees_qonto),
    }


def test_une_entreprise_inexistante_est_ignoree(
    donnees_blablacar, donnees_qonto, caplog, faux_client
):
    # Ce test créé un faux serveur qui renvoie une réponse connue (la fixture) et vérifie que la fonction fetch_jobs() renvoie bien
    # ne prend pas en compte une entreprise qui renvoie une erreur 404, mais continue de traiter les autres entreprises
    # et renvoie un avertissement dans la log.

    # Arrange : on prépare un faux serveur qui renvoie la fixture pour stripe et doctolib, et une erreur 404 pour une entreprise inexistante
    client = faux_client(
        {
            "blablacar": httpx.Response(200, json=donnees_blablacar),
            "entreprise_inexistante": httpx.Response(404),
            "qonto": httpx.Response(200, json=donnees_qonto),
        }
    )

    # Act : on appelle la fonction testée
    offres = fetch_jobs(["blablacar", "entreprise_inexistante", "qonto"], client=client)

    # Assert : on vérifie le résultat
    assert len(offres) == len(donnees_blablacar) + len(donnees_qonto)

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
        fetch_jobs(["blablacar"], client=client)

    assert exc_info.value.response.status_code == code

def test_demande_les_offres_au_format_json():
    requetes_recues = []

    def faux_serveur(request):
        requetes_recues.append(request)
        return httpx.Response(200, json=[])

    client = httpx.Client(transport=httpx.MockTransport(faux_serveur))

    fetch_jobs(["blablacar"], client=client)

    assert len(requetes_recues) == 1
    assert requetes_recues[0].url.params["mode"] == "json"

def test_une_entreprise_sans_offre_est_un_cas_normal(donnees_blablacar, donnees_qonto, caplog, faux_client):
    # Une entreprise présente sur Lever mais sans offre publiée renvoie un 200
    # avec une liste vide (cas observé avec Mistral). C'est un cas normal :
    # la collecte continue, sans avertissement.

    # Arrange : l'entreprise sans offre est placée au milieu de la liste
    client = faux_client(
        {
            "blablacar": httpx.Response(200, json=donnees_blablacar),
            "mistral": httpx.Response(200, json=[]),
            "qonto": httpx.Response(200, json=donnees_qonto),
        }
    )

    # Act
    offres = fetch_jobs(["blablacar", "mistral", "qonto"], client=client)

    # Assert : les offres des autres entreprises sont bien récupérées
    assert len(offres) == len(donnees_blablacar) + len(donnees_qonto)

    # Assert : aucun avertissement, puisque ce n'est pas une erreur
    avertissements = [r for r in caplog.records if r.levelname == "WARNING"]
    assert avertissements == []
