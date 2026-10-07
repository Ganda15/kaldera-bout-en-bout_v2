# Journal des ajustements

Chaque ajustement de l'orchestration (borne, frontière ou routage) y est consigné, avec ce qui l'a provoqué et la preuve du rejeu. Procédure : un seul élément changé à la fois ; rejeu des 28 scénarios et des tests unitaires ; une ligne ici avec le commit.

| # | Date | Origine | Signal observé | Élément ajusté | Avant | Après | Résultat du rejeu | Commit |
|---|---|---|---|---|---|---|---|---|
| 1 | 07/10/2026 | revue de conception, avant tout code | Éligibilité et Pièces sont deux contrôles en code, sans réseau, dans le même processus : les lancer en parallèle ajoute des fils d'exécution pour un gain de temps attendu négligeable (durées mesurées à l'étape 1.2). Le parallélisme utile est entre les demandes d'un lot (§ 12), conservé | routage | Éligibilité et Pièces en parallèle | Éligibilité, puis Pièces, en séquence ; court-circuit : une demande non éligible est refusée sans contrôle des pièces | mesuré le 07/10 : NOM-02 en 2 étapes (eligibilite, coordination) au lieu de 3 ; chaque contrôle dure 0,00 à 0,01 ms (trace de NOM-01) ; acceptance 38/56, aucun test perdu | `ec158e3` |
| 2 | 07/10/2026 | revue de conception, avant tout code | Le dossier promettait qu'après un incident le partenaire ne serait jamais rappelé, grâce à un marqueur rangé dans l'état de la demande. Or cet état vit en mémoire : si le processus s'arrête, le marqueur disparaît. Le contrat impose un seul appel par `reference_dossier`, sans le limiter à une exécution | borne (appels au partenaire) | marqueur dans l'état de chaque demande ; reprise après incident annoncée sans rappel | registre des références appelées, partagé par tout le processus et protégé par un verrou : une demande, un lot ou des appels répétés pendant la vie du processus ne rappellent jamais le partenaire. Après un redémarrage, la protection n'est pas assurée : limite documentée, à confirmer avec le formateur (question 7 du débrief). Une protection durable demanderait un stockage persistant | à mesurer aux étapes 1.6 et 2.4 (deux soumissions simultanées de la même référence : 1 appel) | à venir |

## Effets sur le dossier de conception

Le dossier (`livrable/dossier-de-conception.pdf`) et les schémas reflètent la conception présentée ; ce journal fait foi pour les écarts décidés depuis. À aligner en phase 4 :

- entrée 1 : sections 2.3 et 3.1, schémas 0, 1, 2 et N1 (encore « en parallèle ») ;
- entrée 2 : section 3.3, paragraphe « Reprise après incident ».
