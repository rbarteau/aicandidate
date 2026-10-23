BASE_URL = "https://api.lever.co/v0/postings"

import logging
import site

logger = logging.getLogger(__name__)


def fetch_jobs(board_tokens, client):
    offres = []

    # On parcourt les tokens des entreprises
    for board_token in board_tokens:
        # Créer l'url
        url = f"{BASE_URL}/{board_token}"
        # On fait la requête HTTP GET
        response = client.get(url, params={"mode": "json"})

        # Si le code de statut est 404, on affiche un avertissement dans la log et continue avec l'entreprise suivante
        if response.status_code == 404:
            logger.warning("Entreprise introuvable sur Greenhouse : %s", board_token)
            continue

        # On lève une exception pour tout code qui n'est pas un succès
        response.raise_for_status()

        data = response.json()
        
        # On ajoute le token de l'entreprise à chaque offre pour savoir de quelle entreprise elle vient
        for offre in data:
            offre["board_token"] = board_token

        # On ajoute les offres à la liste globale
        offres.extend(data)

    return offres
