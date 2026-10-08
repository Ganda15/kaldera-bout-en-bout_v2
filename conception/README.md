# Kaldera V2 : préparation de la conception

Préparation du dossier de conception du brief « Kaldera, développer une équipe d'agents de bout en bout » (Simplon × Wild Code School, formation Développeur IA, RNCP 37827).

Le dépôt rassemble les questions que le dossier de conception doit trancher, rangées par chantier, avec les points de vigilance repérés et les tableaux à remplir. Il ne contient pas encore les réponses : la plupart dépendent de `specs_metier.md`, de `eval/scenarios.jsonl` et des tests d'acceptance, qui n'ont pas encore été fournis.

> **Origine de ce dossier.** Copie du dépôt de conception `Ganda15/kaldera-v2-conception` (commit `85c61f7`, 07/10/2026), placée ici pour que la conception et le code vivent dans le même dépôt. Les documents du formateur cités (`docs/`, `eval/`, `external_agent/`) sont ceux de la racine de ce dépôt. Depuis cette copie, les tests d'acceptance (`tests/acceptance/`) et le pilote du partenaire simulé (`scripts/partner_ctl.py`) ont été publiés : ils sont à la racine. La ligne correspondante de la section « État », les questions 1 et 2 pour le formateur et les mentions « pas encore reçu » des deux chantiers sont donc dépassées. Les générateurs de schémas (`scripts/make_schemas_*.py`) sont restés dans le dépôt de conception.

## Démarche

Les questions de réflexion ont été discutées en groupe pendant la séance du 05/10/2026. Cette préparation et les réponses du dossier de conception sont individuelles.

## Organisation

| Fichier | Contenu |
|---|---|
| [chantier-1-equipe-orchestration.md](chantier-1-equipe-orchestration.md) | Chantier 1 : cadrage métier (existant, besoin, résultats attendus), choix du pattern par arbre de décision, carte des agents avec contrats et garde-fous, orchestration, mémoire partagée, observabilité et plan de preuve |
| [chantier-2-a2a-epreuve.md](chantier-2-a2a-epreuve.md) | Chantier 2 : cadrage métier de la collaboration avec le partenaire, choix de la liaison par arbre de décision, protocole et contrat A2A, filtre des données, validation des réponses, mode dégradé, observabilité et preuves, plan d'épreuve, journal des ajustements |
| [schemas/](schemas/) | Trois vues d'ensemble (N0 à N2), puis les schémas des chantiers 1 (A et 0 à 3) et 2 (4 à 6), et le schéma E (lecture des pièces), en `.drawio` (modifiable) et en `.png` |
| [scripts/](https://github.com/Ganda15/kaldera-v2-conception/tree/main/scripts) (dépôt de conception) | Générateurs des schémas (`make_schemas_vues.py`, `make_schemas_ch1.py`, `make_schemas_ch2.py`, `make_schema_lecture.py`), outils communs et légende en puces |

## Les six exigences de la direction des opérations

| | Exigence |
|---|---|
| E1 | Toute demande se termine par une décision ou une escalade humaine motivée, jamais par un blocage silencieux |
| E2 | Chaque agent a un rôle et une frontière définis ; aucun agent n'empiète sur le rôle d'un autre |
| E3 | Seules les données prévues au contrat partent chez le partenaire anti-fraude, rien d'autre |
| E4 | Une réponse du partenaire non conforme au contrat est rejetée, jamais propagée telle quelle |
| E5 | Partenaire indisponible : le mode dégradé défini par le métier s'applique (la demande continue ou est routée, selon `specs_metier.md`) |
| E6 | Aucune boucle infinie ; les métriques par agent (latence, échecs, recours à l'externe) sont visibles ; tout ajustement de l'orchestration provoqué par un scénario d'épreuve est consigné |

Les six sont des garanties absolues. Aucune ne peut reposer sur la seule bonne volonté d'un LLM : chacune doit être tenue par du code et prouvée par un test.

## Vues d'ensemble, en trois niveaux

Pour entrer dans le dossier avant les deux chantiers : le pourquoi, le système complet, puis l'épreuve.

| Niveau | Ce qu'il montre | Fichiers |
|---|---|---|
| N0 · Enjeux et exigences | le problème métier, le contrat durci du partenaire, les six exigences et ce qui tient chacune | [drawio](schemas/schema-N0-enjeux-exigences.drawio), [PNG](schemas/schema-N0-enjeux-exigences.png) |
| N1 · Système complet | l'équipe (chantier 1), la liaison A2A côté Kaldera (chantier 2) et le partenaire, sur une seule vue | [drawio](schemas/schema-N1-systeme-complet.drawio), [PNG](schemas/schema-N1-systeme-complet.png) |
| N2 · Épreuve du réel | la boucle rejouer, observer, comparer, ajuster, consigner ; le partenaire simulé ; les huit familles de tests et les chiffres attendus | [drawio](schemas/schema-N2-epreuve-du-reel.drawio), [PNG](schemas/schema-N2-epreuve-du-reel.png) |

![Niveau 0 · Enjeux et exigences](schemas/schema-N0-enjeux-exigences.png)

![Niveau 1 · Système complet](schemas/schema-N1-systeme-complet.png)

![Niveau 2 · Épreuve du réel](schemas/schema-N2-epreuve-du-reel.png)

## Lecture des pièces (phase E, ajoutée le 08/10/2026)

Le formateur a précisé le 08/10/2026 que les entrées réelles sont des pièces non structurées (contrat en PDF, factures en photo). Deux agents de lecture produisent le JSON de la spec § 3 avant la Coordination ; la chaîne de décision reste inchangée. Fichiers : [drawio](schemas/schema-E-lecture-des-pieces.drawio), [PNG](schemas/schema-E-lecture-des-pieces.png).

L'équipe compte sept rôles internes : deux agents de lecture qui utilisent un modèle (lecteur de contrat, lecteur de pièces), quatre contrôles déterministes (Éligibilité, Pièces, Estimation, Anti-fraude) et la Coordination, qui applique les règles et produit seule l'issue. Le partenaire anti-fraude est un agent externe : il appartient à une autre entreprise.

![Lecture des pièces](schemas/schema-E-lecture-des-pieces.png)

## Couverture des schémas attendus par le brief

| Schéma attendu | Où il se prépare |
|---|---|
| Cadrage métier (existant, besoin, résultats attendus) et choix du pattern | Chantier 1, sections 1 et 2 |
| Architecture générale : l'équipe, la mémoire, l'extérieur et les issues sur une seule vue | Chantier 1, schéma A et section 3 |
| Carte des agents : rôles, frontières (point ambigu tranché), règle métier ou jugement, dépendances, parallélisme | Chantier 1, section 3 |
| Schéma d'orchestration : délégations, conditions d'arrêt, bornes provisoires | Chantier 1, section 4 |
| Modèle de la mémoire partagée | Chantier 1, sections 5 et 6 |
| Cadrage métier du partenaire et choix de la liaison | Chantier 2, sections 1 et 2 |
| Schéma d'échange A2A : contrat, filtre de données, validation des réponses, chemin de mode dégradé | Chantier 2, sections 3 à 7 |
| Plan d'épreuve : scénarios d'intégration × signaux observés × ajustement possible du chantier 1 | Chantier 2, sections 8 à 10 |

## Mode d'emploi

- Écrire la réponse sous chaque question, puis cocher la case.
- `[E1]` à `[E6]` renvoient aux exigences ci-dessus.
- Une réponse qui dépend de `specs_metier.md` reste marquée « provisoire » tant que ce fichier n'a pas été lu.

## État

- [x] Documents du formateur reçus le 06/10/2026 : `docs/specs_metier.md`, `docs/interface.md`, `eval/scenarios.jsonl`, `external_agent/contrat.md`
- [ ] Tests d'acceptance (`tests/acceptance/`) et pilote du partenaire simulé (`scripts/partner_ctl.py`) : cités par `interface.md`, pas encore reçus
- [x] Réponses du chantier 1, fondées sur les documents reçus ; points ouverts listés en fin de chantier
- [x] Réponses du chantier 2, fondées sur le contrat du partenaire (version 2.0) et les 28 scénarios ; points ouverts listés en fin de chantier
- [x] Schémas du chantier 1 : architecture générale, arbre de décision, carte des agents, orchestration, mémoire partagée (fondés sur les documents reçus ; bornes provisoires)
- [x] Schémas du chantier 2 : arbre de décision de la liaison, échange A2A et mode dégradé, plan d'épreuve (fondés sur le contrat du partenaire)
- [x] 08/10/2026 : schéma E (lecture des pièces) ajouté ; schémas 1 et N1 alignés sur le code (contrôles dans l'ordre, avec court-circuit)
- [x] 08/10/2026 : texte des deux chantiers aligné sur le code (contrôles en séquence avec court-circuit, sept rôles, entrée, sortie, modèle et raison de chaque rôle)
- [ ] Schémas 0, 2 et A : décrivent encore Éligibilité et Pièces « en parallèle » ; l'écart est consigné (journal des ajustements, entrée 1), l'alignement est prévu
- [x] Trois vues d'ensemble (N0 enjeux et exigences, N1 système complet, N2 épreuve du réel), à jour de la conception au 07/10/2026
- [ ] Dossier validé par le formateur, avant tout code

## Questions pour le formateur

1. Quand recevrons-nous les tests d'acceptance (`tests/acceptance/`) ? `specs_metier.md` et `eval/scenarios.jsonl` ont été reçus le 06/10.
2. Le partenaire simulé et son pilote `scripts/partner_ctl.py`, cités par `interface.md`, seront-ils fournis ?
3. La pile technique est-elle libre ? Un composant à base de règles compte-t-il comme un agent ?
4. Les demandes déjà bloquées depuis des semaines font-elles partie du périmètre ?
5. Quelles sont les échéances du dossier de conception et du code ?

Questions résolues par les documents du 06/10 : la version du protocole (format 0.3.0, voir le chantier 2, section 3), le contrat réel du partenaire (`external_agent/contrat.md`, version 2.0) et les questions guides des deux chantiers.

## Sources

- Brief « Kaldera, développer une équipe d'agents de bout en bout », Simplonline (accès restreint)
- Spécification A2A, dernière version publiée (1.0.0) : [a2a-protocol.org/latest/specification](https://a2a-protocol.org/latest/specification/)
- Spécification A2A 0.3.0 : [a2a-protocol.org/v0.3.0/specification](https://a2a-protocol.org/v0.3.0/specification/)
- Schéma JSON officiel de la version 0.3.0 : [a2aproject/A2A, specification/json/a2a.json](https://github.com/a2aproject/A2A/blob/v0.3.0/specification/json/a2a.json)

## Lexique

- **A2A (Agent-to-Agent)** : protocole qui permet à deux agents de systèmes différents d'échanger selon un format commun.
- **Agent Card** : fiche publiée par un agent A2A ; elle décrit ses compétences, la version du protocole suivie et le mode d'authentification.
- **Bouchon (mock)** : faux partenaire réglable, utilisé pour simuler un partenaire lent, en panne ou menteur.
- **Borne** : limite dure (nombre d'étapes, d'appels, durée) qui arrête une boucle.
- **Contrat d'échange** : format exact et liste fermée des champs que les deux parties s'engagent à échanger.
- **Escalade motivée** : transfert d'une demande à un humain, avec le motif, l'étape atteinte, les données disponibles et les tentatives faites.
- **Mode dégradé** : chemin de repli défini par le métier quand le partenaire est indisponible.
- **Plan d'épreuve** : tableau qui associe à chaque scénario rejoué les signaux à observer et l'ajustement du chantier 1 qu'il peut provoquer.
