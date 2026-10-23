# AICandidate

![CI](https://github.com/rbarteau/aicandidate/actions/workflows/ci.yml/badge.svg)

Outil d'aide à la recherche d'emploi pour les postes data (data scientist, data analyst, AI engineer) : il collecte les offres publiées par une liste d'entreprises cibles, les filtre, puis prépare les candidatures (choix du CV, lettre de motivation), avec une validation humaine avant tout envoi.

Projet construit comme un produit industrialisé : développement piloté par les tests (pytest), intégration continue (GitHub Actions), qualité de code (ruff), puis Docker, API FastAPI et couche agentique (MCP).

## Sources de données

- **Greenhouse** et **Lever** : API publiques des logiciels de recrutement, interrogées entreprise par entreprise.

## Installation

```bash
git clone https://github.com/rbarteau/aicandidate.git
cd aicandidate
pip install -e ".[dev]"
```

Python 3.13 ou supérieur requis.

## Tests et qualité

```bash
pytest          # tests
ruff check      # lint
ruff format     # formatage
```

## Structure
```bash
src/aicandidate/providers/ # un module par source d’offres 
tests/ # tests unitaires et fixtures JSON 
notebooks/ # exploration des API 
```