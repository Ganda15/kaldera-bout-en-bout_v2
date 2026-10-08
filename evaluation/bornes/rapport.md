# Bornes tirées de la mesure

Rapport généré par `outils/mesurer_bornes.py` contre le partenaire simulé fourni. Ne pas modifier à la main.

- date : 2026-10-08 19:59 ; commit : 1e33ad5

| Mesure | Essais | Médiane (s) | Maximum (s) | Règle (src/kaldera/bornes.py) | Valeur tirée |
|---|---|---|---|---|---|
| Dépassement après l'échéance (partenaire seul, à trois, et chemin des pièces) | 70 | 0.006 | 0.038 | dix fois le maximum, arrondi au dixième supérieur, 0,1 s au moins | reserve_fiche_s = 0.4 |
| Durée d'un appel réussi au partenaire (seul et en lot de sept) | 65 | 0.09 | 0.1032 | le maximum, arrondi au vingtième supérieur, 0,05 s au moins | delai_partenaire_min_s = 0.15 |

Détail du dépassement : partenaire 0.038 s au plus, chemin des pièces 0.016 s au plus.

Limite : mesuré sur le partenaire simulé et sur cette machine. Contre le vrai partenaire (réponse garantie en 2 s), la durée d'un appel réussi sera plus longue : relancer la mesure et appliquer la même règle.
