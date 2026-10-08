# Épreuve du réel : mesures

Rapport généré par `outils/mesurer_epreuve.py` contre le partenaire simulé fourni. Ne pas modifier à la main.

- date : 2026-10-08 19:20
- demandes conformes à `attendu` : 34/34 (28 scénarios)
- appels reçus par le partenaire : 18 ; doublons reçus : 0 ; au plus 1 appel par dossier
- trace la plus longue : 6 étapes

| Scénario | Partenaire | Conformes | Appels | Échecs | Raisons | Trace max | Durée du lot (s) |
|---|---|---|---|---|---|---|---|
| NOM-01 | normal | 1/1 | 0 | 0 | · | 5 | 0.0 |
| NOM-02 | normal | 1/1 | 0 | 0 | · | 2 | 0.0 |
| NOM-03 | normal | 1/1 | 0 | 0 | · | 2 | 0.0 |
| NOM-04 | normal | 1/1 | 0 | 0 | · | 2 | 0.0 |
| NOM-05 | normal | 1/1 | 0 | 0 | · | 5 | 0.0 |
| NOM-06 | normal | 1/1 | 0 | 0 | · | 4 | 0.0 |
| NOM-07 | normal | 1/1 | 0 | 0 | · | 6 | 0.001 |
| NOM-08 | normal | 1/1 | 0 | 0 | · | 5 | 0.0 |
| NOM-09 | normal | 1/1 | 0 | 0 | · | 4 | 0.0 |
| NOM-10 | normal | 1/1 | 0 | 0 | · | 2 | 0.0 |
| NOM-11 | normal | 1/1 | 0 | 0 | · | 2 | 0.001 |
| AF-01 | normal | 1/1 | 1 | 0 | · | 5 | 0.086 |
| AF-02 | normal | 1/1 | 1 | 0 | · | 5 | 0.092 |
| AF-03 | normal | 1/1 | 1 | 0 | · | 5 | 0.093 |
| AF-04 | normal | 1/1 | 1 | 0 | · | 5 | 0.1 |
| AF-05 | normal | 1/1 | 1 | 0 | · | 5 | 0.074 |
| AF-06 | normal | 1/1 | 1 | 0 | · | 5 | 0.091 |
| AF-07 | normal | 1/1 | 1 | 0 | · | 5 | 0.09 |
| INV-01 | invalide | 1/1 | 1 | 1 | schema | 5 | 0.075 |
| INV-02 | invalide | 1/1 | 1 | 1 | incoherence | 5 | 0.074 |
| INV-03 | invalide | 1/1 | 1 | 1 | schema | 5 | 0.074 |
| INV-04 | invalide | 1/1 | 1 | 1 | incoherence | 5 | 0.09 |
| INV-05 | invalide | 1/1 | 1 | 1 | schema | 5 | 0.072 |
| INV-06 | invalide | 1/1 | 1 | 1 | reponse_non_json | 5 | 0.077 |
| INV-07 | invalide | 1/1 | 1 | 1 | enveloppe_invalide | 5 | 0.075 |
| PAN-01 | panne | 5/5 | 2 | 2 | http_503, http_503 | 6 | 0.012 à 0.016 (5 rejeux) |
| PAN-02 | lent | 3/3 | 2 | 2 | delai_depasse, delai_depasse | 5 | 3.021 à 3.033 (5 rejeux) |
| BCL-01 | normal | 1/1 | 0 | 0 | · | 4 | 0.0 |
