# Évaluation de l'extraction (étape E4)

Rapport généré par `outils/evaluer_extraction.py` depuis `resultats.json`. Ne pas le modifier à la main : `--verifier` le recalcule et le compare.

- Dossiers : 34 ; verdict : **échoué** (seuils : 95% par champ, 95% de décisions identiques, aucune lecture impossible)
- date : 2026-10-08 23:03
- modele : gpt-5.4
- commit : 5cb2a4e
- python : 3.11.15
- lectures_en_parallele : 6
- duree_totale_s : 27.4

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

Décisions identiques au chemin JSON (issue, décision, montant, file, mode dégradé, arrêt) : 32/34. Lectures impossibles : 0.
- KAL-26-0204 : décision différente du chemin JSON ; cohérence des pièces : insuffisant
- KAL-26-0503 : décision différente du chemin JSON ; cohérence des pièces : insuffisant

## Appels au modèle

| Lecture | Appels | Moyenne (s) | p95 (s) | Max (s) |
|---|---|---|---|---|
| contrat | 34 | 1.69 | 2.68 | 3.49 |
| facture | 33 | 2.1 | 4.68 | 5.73 |
| coherence | 34 | 3.97 | 7.76 | 8.59 |

## Jetons consommés et métriques des agents de lecture

Jetons : 85719 en entrée, 8300 en sortie, pour 34 dossiers (2521 et 244 par dossier en moyenne). Coût = jetons d'entrée × prix d'entrée + jetons de sortie × prix de sortie, aux prix du déploiement (portail Azure).

| Agent | Lectures | Échecs | Latence moyenne (ms) | Appels au modèle | Jetons entrée | Jetons sortie |
|---|---|---|---|---|---|---|
| lecteur_contrat | 34 | 0 | 1693.38 | 34 | 10763 | 1653 |
| lecteur_pieces | 68 | 0 | 1025.48 | 33 | 21417 | 835 |
| coherence | 34 | 0 | 3976.27 | 34 | 53539 | 5812 |

## Écarts

Aucun écart.
