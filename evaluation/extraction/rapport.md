# Évaluation de l'extraction (étape E4)

Rapport généré par `outils/evaluer_extraction.py` depuis `resultats.json`. Ne pas le modifier à la main : `--verifier` le recalcule et le compare.

- Dossiers : 34 ; verdict : **réussi** (seuils : 95% par champ, 95% de décisions identiques, aucune lecture impossible)
- date : 2026-10-08 10:22
- modele : gpt-5.4
- commit : c61bf34
- python : 3.11.15
- lectures_en_parallele : 6
- duree_totale_s : 25.1

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
| contrat | 34 | 1.77 | 2.35 | 2.81 |
| facture | 33 | 2.35 | 5.81 | 6.46 |

## Écarts

Aucun écart.
