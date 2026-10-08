# Évaluation de l'extraction (étape E4)

Rapport généré par `outils/evaluer_extraction.py` depuis `resultats.json`. Ne pas le modifier à la main : `--verifier` le recalcule et le compare.

- Dossiers : 34 ; verdict : **réussi** (seuils : 95% par champ, 95% de décisions identiques, aucune lecture impossible)
- date : 2026-10-08 18:56
- modele : gpt-5.4
- commit : 0922f9b
- python : 3.11.15
- lectures_en_parallele : 6
- duree_totale_s : 21.7

## Exactitude par champ

| Champ | Justes | Taux |
|---|---|---|
| `contrat.cotisations_a_jour` | 34/34 | 100.00% |
| `contrat.date_souscription` | 34/34 | 100.00% |
| `contrat.formule` | 34/34 | 100.00% |
| `contrat.numero` | 34/34 | 100.00% |
| `contrat.statut` | 34/34 | 100.00% |
| `factures.montant` | 33/33 | 100.00% |
| `pieces.lisible` | 68/68 | 100.00% |

## Décisions

Décisions identiques au chemin JSON (issue, décision, montant, file, mode dégradé, arrêt) : 34/34. Lectures impossibles : 0.

## Appels au modèle

| Lecture | Appels | Moyenne (s) | p95 (s) | Max (s) |
|---|---|---|---|---|
| contrat | 34 | 1.81 | 2.93 | 6.98 |
| facture | 33 | 1.97 | 2.9 | 2.99 |

## Jetons consommés et métriques des agents de lecture

Jetons : 32180 en entrée, 2486 en sortie, pour 34 dossiers (946 et 73 par dossier en moyenne). Coût = jetons d'entrée × prix d'entrée + jetons de sortie × prix de sortie, aux prix du déploiement (portail Azure).

| Agent | Lectures | Échecs | Latence moyenne (ms) | Appels au modèle | Jetons entrée | Jetons sortie |
|---|---|---|---|---|---|---|
| lecteur_contrat | 34 | 0 | 1807.91 | 34 | 10763 | 1653 |
| lecteur_pieces | 68 | 0 | 959.68 | 33 | 21417 | 833 |

## Écarts

Aucun écart.
