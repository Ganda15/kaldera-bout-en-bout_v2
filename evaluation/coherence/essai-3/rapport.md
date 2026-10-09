# Évaluation de l'agent Documents et cohérence (spec § 5)

Rapport généré par `outils/evaluer_coherence.py` depuis `resultats.json`. Ne pas le modifier à la main : `--verifier` le recalcule et le compare.

- Dossiers : 42 ; verdict : **réussi**
- date : 2026-10-08 22:57
- modele : gpt-5.4
- commit : 928e8df
- python : 3.11.15
- dossiers_en_parallele : 3
- duree_totale_s : 103.9

## Portes (écrites avant la mesure)

| Porte | Mesure | Seuil |
|---|---|---|
| Contradictions envoyées à une personne | 6/6 | toutes |
| Fausses alertes (contradiction sur un dossier cohérent ou ambigu) | 0 | au plus 0 |
| Examens inutiles (insuffisant sur un dossier cohérent) | 3 | au plus 3 |
| Échecs techniques (non effectué) | 0 | au plus 0 |
| Dossiers au-delà de 10 s | 0 | au plus 0 |

## Verdicts de l'agent seul, par étiquette

| Étiquette | coherent | contradiction | insuffisant | non_effectue |
|---|---|---|---|---|
| coherent | 31 | 0 | 3 | 0 |
| non_coherent | 0 | 6 | 0 | 0 |
| ambigu | 0 | 0 | 2 | 0 |

Contradictions rendues « contradiction » (et non « insuffisant ») : 6/6. Verdicts différents entre l'agent seul et la chaîne complète (même dossier, deux appels) : 3 sur 42 dossiers où la chaîne atteint la cohérence.

## Chaîne complète

Fiches conformes à l'attendu : 41/42 (cohérent : la fiche du chemin JSON ; contradiction : un gestionnaire ; ambigu : l'un ou l'autre).

| Durée | Mesures | Moyenne (s) | p95 (s) | Max (s) |
|---|---|---|---|---|
| appel de cohérence (agent seul) | 42 | 3.33 | 4.77 | 5.64 |
| dossier complet | 42 | 3.89 | 6.37 | 7.83 |

Jetons de l'agent seul : 66385 en entrée, 7323 en sortie (1580 et 174 par dossier).

## Dossiers à regarder

- KAL-26-0111 (coherent) : agent **insuffisant**, chaîne insuffisant, fiche decision refusee ; piece-1-facture.png : Facture de travaux après sinistre, mais le libellé ne mentionne pas explicitement un incendie ni la cuisine.
- KAL-26-0302 (coherent) : agent **coherent**, chaîne insuffisant, fiche escalade gestionnaire ; coherent
- KAL-26-0403 (coherent) : agent **insuffisant**, chaîne coherent, fiche decision acceptee ; piece-1-facture.png : Travaux de remise en état compatibles avec un incendie, mais le libellé ne mentionne pas explicitement un feu ni la cuisine, la hotte ou le plan de travail.
- KAL-26-0503 (coherent) : agent **insuffisant**, chaîne coherent, fiche escalade cellule_fraude ; piece-1-facture.png : Facture de travaux après sinistre, mais le libellé ne mentionne pas explicitement un incendie ni la cuisine, hotte ou plan de travail.
- KAL-26-0701 (non_coherent) : agent **contradiction**, chaîne contradiction, fiche escalade gestionnaire ; piece-1-facture.png : évoque bris_de_glace, déclaré degat_des_eaux (Facture de dépose et pose d'un double vitrage) ; piece-1-facture.png : La facture concerne un vitrage endommagé, ce qui évoque un bris de glace et non le dégât des eaux déclaré sur parquet et plinthes.
- KAL-26-0702 (non_coherent) : agent **contradiction**, chaîne contradiction, fiche escalade gestionnaire ; piece-1-facture.png : facture du 2026-07-25, antérieure au sinistre du 2026-08-14
- KAL-26-0703 (non_coherent) : agent **contradiction**, chaîne contradiction, fiche escalade gestionnaire ; piece-2-photo.png : évoque incendie, déclaré degat_des_eaux (Photo mentionnée comme sinistre incendie) ; piece-2-photo.png : L'image évoque clairement un incendie, ce qui contredit le dégât des eaux déclaré.
- KAL-26-0704 (non_coherent) : agent **contradiction**, chaîne contradiction, fiche escalade gestionnaire ; piece-1-facture.png : évoque degat_des_eaux, déclaré incendie (Facture de recherche et réparation de fuite et remplacement du parquet) ; piece-1-facture.png : La facture mentionne une fuite et un parquet à remplacer, ce qui évoque un dégât des eaux, pas l’incendie déclaré en cuisine.
- KAL-26-0705 (non_coherent) : agent **contradiction**, chaîne contradiction, fiche escalade gestionnaire ; piece-2-depot_plainte.png : La plainte concerne un vol de véhicule, différent du cambriolage du domicile avec vol d'ordinateur et d'appareil photo.
- KAL-26-0706 (non_coherent) : agent **contradiction**, chaîne contradiction, fiche escalade gestionnaire ; piece-1-facture.png : évoque degat_des_eaux, déclaré bris_de_glace (Facture de recherche et réparation de fuite et remplacement du parquet) ; piece-1-facture.png : La facture mentionne une fuite et un parquet remplacé, ce qui évoque un dégât des eaux et non un bris de glace.
- KAL-26-0707 (ambigu) : agent **insuffisant**, chaîne insuffisant, fiche escalade gestionnaire ; piece-1-facture.png : facture du 2026-03-06, antérieure au vol (achat, pas remplacement)
- KAL-26-0708 (ambigu) : agent **insuffisant**, chaîne insuffisant, fiche escalade gestionnaire ; piece-1-facture.png : Facture datée après le sinistre, mais libellé trop vague (« fournitures diverses ») pour la relier clairement au dégât des eaux déclaré.
