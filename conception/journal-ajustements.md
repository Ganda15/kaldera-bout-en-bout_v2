# Journal des ajustements

Chaque ajustement de l'orchestration (borne, frontière ou routage) y est consigné, avec ce qui l'a provoqué et la preuve du rejeu. Procédure : un seul élément changé à la fois ; rejeu des 28 scénarios et des tests unitaires ; une ligne ici avec le commit.

| # | Date | Origine | Signal observé | Élément ajusté | Avant | Après | Résultat du rejeu | Commit |
|---|---|---|---|---|---|---|---|---|
| 1 | 07/10/2026 | revue de conception, avant tout code | Éligibilité et Pièces sont deux contrôles en code, dans le même processus, d'environ une milliseconde chacun : les lancer en parallèle n'apporte aucun gain mesurable et ajoute des fils d'exécution. Le parallélisme utile est entre les demandes d'un lot (§ 12), conservé | routage | Éligibilité et Pièces en parallèle | Éligibilité, puis Pièces, en séquence ; court-circuit : une demande non éligible est refusée sans contrôle des pièces | à mesurer à l'étape 1.5 (NOM-02 : 2 étapes au lieu de 3) | à venir |

## Effets sur le dossier de conception

Le dossier (`livrable/dossier-de-conception.pdf`, sections 2.3 et 3.1) et les schémas 0, 1, 2 et N1 décrivent encore Éligibilité et Pièces en parallèle. Ils reflètent la conception présentée ; ce journal fait foi pour les écarts décidés depuis.
