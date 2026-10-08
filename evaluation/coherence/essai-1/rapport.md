# Évaluation de l'agent Documents et cohérence (spec § 5)

Rapport généré par `outils/evaluer_coherence.py` depuis `resultats.json`. Ne pas le modifier à la main : `--verifier` le recalcule et le compare.

- Dossiers : 42 ; verdict : **échoué**
- date : 2026-10-08 22:47
- modele : gpt-5.4
- commit : 22c2c5b
- python : 3.11.15
- dossiers_en_parallele : 3
- duree_totale_s : 151.1

## Portes (écrites avant la mesure)

| Porte | Mesure | Seuil |
|---|---|---|
| Contradictions envoyées à une personne | 6/6 | toutes |
| Fausses alertes (contradiction sur un dossier cohérent ou ambigu) | 0 | au plus 0 |
| Examens inutiles (insuffisant sur un dossier cohérent) | 17 | au plus 3 |
| Échecs techniques (non effectué) | 3 | au plus 0 |
| Dossiers au-delà de 10 s | 0 | au plus 0 |

## Verdicts de l'agent seul, par étiquette

| Étiquette | coherent | contradiction | insuffisant | non_effectue |
|---|---|---|---|---|
| coherent | 17 | 0 | 17 | 0 |
| non_coherent | 0 | 6 | 0 | 0 |
| ambigu | 0 | 0 | 2 | 0 |

Contradictions rendues « contradiction » (et non « insuffisant ») : 6/6. Verdicts différents entre l'agent seul et la chaîne complète (même dossier, deux appels) : 6 sur 34 dossiers où la chaîne atteint la cohérence.

## Chaîne complète

Fiches conformes à l'attendu : 26/42 (cohérent : la fiche du chemin JSON ; contradiction : un gestionnaire ; ambigu : l'un ou l'autre).

| Durée | Mesures | Moyenne (s) | p95 (s) | Max (s) |
|---|---|---|---|---|
| appel de cohérence (agent seul) | 42 | 4.01 | 5.97 | 8.23 |
| dossier complet | 42 | 6.58 | 9.6 | 9.62 |

Jetons de l'agent seul : 63823 en entrée, 7374 en sortie (1519 et 175 par dossier).

## Dossiers à regarder

- KAL-26-0101 (coherent) : agent **insuffisant**, chaîne insuffisant, fiche escalade gestionnaire ; piece-2-photo.png : Le visuel ne montre pas clairement de dommages identifiables ; seul le texte évoque un dégât des eaux.
- KAL-26-0104 (coherent) : agent **insuffisant**, chaîne non_atteint, fiche decision refusee ; piece-2-photo.png : Le visuel ne montre pas clairement des dommages identifiables ni le lieu ; seul le libellé évoque un dégât des eaux.
- KAL-26-0105 (coherent) : agent **insuffisant**, chaîne insuffisant, fiche escalade gestionnaire ; piece-2-photo.png : Le visuel ne montre pas clairement des dommages identifiables malgré le libellé mentionnant un dégât des eaux.
- KAL-26-0106 (coherent) : agent **coherent**, chaîne non_effectue, fiche escalade gestionnaire ; coherent
- KAL-26-0107 (coherent) : agent **insuffisant**, chaîne insuffisant, fiche escalade gestionnaire ; depots/1-photo.png : L'image porte la mention dégât des eaux mais ne montre pas clairement des dommages ou le lieu décrit dans la déclaration.
- KAL-26-0201 (coherent) : agent **insuffisant**, chaîne insuffisant, fiche escalade gestionnaire ; piece-2-photo.png : L'image comporte seulement une mention textuelle et un visuel schématique, sans dommage identifiable ni lieu vérifiable.
- KAL-26-0202 (coherent) : agent **insuffisant**, chaîne non_effectue, fiche escalade gestionnaire ; piece-2-photo.png : L'image est très schématique et ne montre pas clairement une cuisine ni les éléments déclarés ; seul le libellé évoque un incendie.
- KAL-26-0203 (coherent) : agent **insuffisant**, chaîne insuffisant, fiche escalade gestionnaire ; piece-2-photo.png : Le visuel est schématique et ne permet pas de vérifier clairement des dommages correspondant au sinistre déclaré.
- KAL-26-0204 (coherent) : agent **coherent**, chaîne non_effectue, fiche escalade gestionnaire ; coherent
- KAL-26-0205 (coherent) : agent **coherent**, chaîne insuffisant, fiche escalade gestionnaire ; coherent
- KAL-26-0301 (coherent) : agent **insuffisant**, chaîne insuffisant, fiche escalade gestionnaire ; piece-2-photo.png : L'image est très schématique et ne permet pas de vérifier le lieu ni les dommages décrits, malgré la mention de dégât des eaux.
- KAL-26-0302 (coherent) : agent **insuffisant**, chaîne insuffisant, fiche escalade gestionnaire ; piece-2-photo.png : L'image est très schématique et ne montre pas clairement une cuisine, un plan de travail ou une hotte endommagés.
- KAL-26-0304 (coherent) : agent **insuffisant**, chaîne coherent, fiche escalade cellule_fraude ; piece-2-photo.png : Le visuel est schématique et ne permet pas de relier clairement les dommages au couloir, au parquet ou à la salle de bains déclarés.
- KAL-26-0305 (coherent) : agent **insuffisant**, chaîne insuffisant, fiche escalade gestionnaire ; piece-2-photo.png : Le visuel ne montre pas clairement des dommages identifiables ni le lieu décrit, malgré le libellé indiquant un dégât des eaux.
- KAL-26-0402 (coherent) : agent **insuffisant**, chaîne non_atteint, fiche decision refusee ; piece-2-photo.png : Le document est présenté comme une photo de bris de glace, mais l'image fournie ne montre pas clairement une baie vitrée fissurée ni le lieu.
- KAL-26-0403 (coherent) : agent **insuffisant**, chaîne insuffisant, fiche escalade gestionnaire ; piece-2-photo.png : L'image est étiquetée 'incendie' mais ne montre pas clairement une cuisine, une hotte ou un plan de travail détruits.
- KAL-26-0404 (coherent) : agent **insuffisant**, chaîne coherent, fiche escalade cellule_fraude ; piece-2-photo.png : Le visuel est schématique et ne permet pas de vérifier clairement des dommages au parquet, aux plinthes ou à la salle de bains.
- KAL-26-0405 (coherent) : agent **insuffisant**, chaîne insuffisant, fiche escalade gestionnaire ; depots/1-photo.png : L’image est schématique et ne montre pas clairement une baie vitrée fissurée, malgré la mention de bris de glace.
- KAL-26-0502 (coherent) : agent **insuffisant**, chaîne insuffisant, fiche escalade gestionnaire ; piece-2-photo.png : L'image est schématique et ne montre pas clairement les dommages ni le lieu, malgré la mention de dégât des eaux.
- KAL-26-0503 (coherent) : agent **insuffisant**, chaîne insuffisant, fiche escalade gestionnaire ; piece-1-facture.png : Facture de travaux après sinistre, mais sans mention explicite d’un incendie ni de la cuisine.
- KAL-26-0701 (non_coherent) : agent **contradiction**, chaîne contradiction, fiche escalade gestionnaire ; piece-1-facture.png : évoque bris_de_glace, déclaré degat_des_eaux (Facture de dépose et pose de double vitrage) ; piece-1-facture.png : La facture concerne un vitrage endommagé, ce qui évoque un bris de glace et non un dégât des eaux sur parquet/plinthes.
- KAL-26-0702 (non_coherent) : agent **contradiction**, chaîne contradiction, fiche escalade gestionnaire ; piece-1-facture.png : facture du 2026-07-25, antérieure au sinistre du 2026-08-14
- KAL-26-0703 (non_coherent) : agent **contradiction**, chaîne contradiction, fiche escalade gestionnaire ; piece-2-photo.png : évoque incendie, déclaré degat_des_eaux (Photo présentée comme un sinistre incendie) ; piece-2-photo.png : L'image évoque explicitement un incendie, ce qui contredit la déclaration de dégât des eaux.
- KAL-26-0704 (non_coherent) : agent **contradiction**, chaîne contradiction, fiche escalade gestionnaire ; piece-1-facture.png : évoque degat_des_eaux, déclaré incendie (Facture de recherche et réparation de fuite et remplacement de parquet) ; piece-1-facture.png : La facture mentionne une fuite et un parquet remplacé, ce qui évoque un dégât des eaux et non un incendie de cuisine.
- KAL-26-0705 (non_coherent) : agent **contradiction**, chaîne contradiction, fiche escalade gestionnaire ; piece-2-depot_plainte.png : La plainte concerne un vol de véhicule sur la voie publique, pas un cambriolage d'habitation avec vol d'ordinateur et d'appareil photo.
- KAL-26-0706 (non_coherent) : agent **contradiction**, chaîne contradiction, fiche escalade gestionnaire ; piece-1-facture.png : évoque degat_des_eaux, déclaré bris_de_glace (Facture de recherche et réparation de fuite, remplacement de parquet) ; piece-1-facture.png : La facture mentionne une fuite et un parquet remplacé, ce qui évoque un dégât des eaux, pas un bris de glace.
- KAL-26-0707 (ambigu) : agent **insuffisant**, chaîne insuffisant, fiche escalade gestionnaire ; piece-1-facture.png : facture du 2026-03-06, antérieure au vol (achat, pas remplacement)
- KAL-26-0708 (ambigu) : agent **insuffisant**, chaîne insuffisant, fiche escalade gestionnaire ; piece-1-facture.png : Facture datée après le sinistre, mais libellé trop vague ('fournitures diverses') pour relier clairement au dégât des eaux déclaré. ; piece-2-photo.png : L'image porte la mention 'degat des eaux', compatible avec la déclaration, mais ne montre pas clairement les dommages décrits (parquet/plinthes/couloir).
