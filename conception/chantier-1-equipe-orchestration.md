# Chantier 1 : l'équipe et son orchestration

Ce que le brief attend pour ce chantier : l'architecture générale de l'équipe, la carte des agents (rôles, frontières dont le point ambigu tranché, dépendances, parallélisme), le schéma d'orchestration (délégations, conditions d'arrêt, bornes provisoires) et le modèle de la mémoire partagée.

Exigences concernées : E1, E2 et E6, plus E3 pour les champs sensibles de la mémoire. Le détail des exigences est dans le [README](README.md).

Sources : [`docs/specs_metier.md`](../docs/specs_metier.md) (version 3.2), [`docs/interface.md`](../docs/interface.md), [`eval/scenarios.jsonl`](../eval/scenarios.jsonl) (28 scénarios) et [`external_agent/contrat.md`](../external_agent/contrat.md) (version 2.0), reçus le 06/10/2026. Les renvois « § » désignent les sections de `specs_metier.md`.

> **Attention aux noms.** La spec nomme **E1 à E5** les cinq conditions d'éligibilité (§ 4). Dans ce dossier, **[E1] à [E6]** entre crochets désignent les exigences de la direction des opérations (README). Ce ne sont pas les mêmes.

Démarche : le cadrage métier (section 1) précède le choix du pattern (section 2) et la conception de l'équipe (sections 3 à 6). Une architecture définie avant le cadrage risque d'optimiser ce qui n'en a pas besoin.

## 1. Cadrage métier

Avant toute conception technique, un cadrage avec le métier établit les contraintes réelles du système, en trois volets : l'analyse de l'existant, l'expression du besoin et les résultats attendus. Les documents reçus répondent à une partie des questions ; les autres restent à poser au client.

### Analyse de l'existant

- [ ] Le système actuel a-t-il déjà donné satisfaction ? Si oui, depuis quand ses performances se dégradent-elles, et quels indicateurs ou quelles traces l'attestent ?
  **Ouvert.** Les documents ne donnent ni historique ni indicateur de l'agent actuel. *Impact : la situation de référence à laquelle comparer la nouvelle équipe.*
- [ ] De quels indicateurs et de quelles traces dispose-t-on aujourd'hui (journaux, tableaux de bord, suivi LLMOps ou MLOps) ?
  **Ouvert** pour l'existant. Pour la cible, `interface.md` impose une trace par étape et quatre métriques par agent (section 6). *Impact : les sources réutilisables pour l'observabilité.*
- [ ] Pour quelles raisons l'agent généraliste actuel a-t-il été conçu ainsi ?
  **Ouvert.** *Impact : les contraintes implicites à conserver ou à lever.*
- [ ] Quel est le volume de demandes (moyenne journalière, pics) ? Combien sont bloquées aujourd'hui, et à quelle étape ?
  **Ouvert.** Les scénarios traitent des lots de 3 et 5 demandes, et le traitement d'une demande ne doit jamais être retardé par celui d'une autre (§ 12). *Impact : le parallélisme entre demandes et les bornes.*
- [x] Quel est le parcours réel d'une demande, de sa réception au remboursement ?
  **Réponse (§ 2).** Éligibilité, pièces justificatives, estimation, contrôle anti-fraude (seulement si un indicateur de risque est présent), puis une issue : décision acceptée ou refusée, ou escalade vers une file humaine. Le seul temps d'attente prévu est la demande de complément de pièces à l'assuré (§ 5).

### Expression du besoin

- [x] Le recours à un système agentique est-il justifié, au regard d'un traitement humain ou d'un système déterministe plus simple ? Pour quelles étapes ?
  **Réponse (mise à jour le 08/10/2026).** Les règles de décision sont chiffrées (§ 4 à § 10) : elles s'écrivent en code et se testent ; l'avis anti-fraude vient du partenaire externe. Mais l'entrée réelle est un dossier de pièces non structurées (contrat en PDF, factures en photo), et les lire demande un modèle. **Choix : un modèle pour extraire l'information des documents (deux agents de lecture), du code pour les règles explicites et les calculs, aucun LLM dans la décision finale.** La cohérence des pièces avec la déclaration (§ 5) est un jugement : son périmètre est demandé au formateur avant tout ajout.
- [x] Le partenaire anti-fraude externe est-il indispensable, ou un contrôle interne pourrait-il le remplacer ?
  **Réponse (§ 2).** « L'avis de fraude est émis par le partenaire, jamais en interne. » Le partenaire est imposé ; son indisponibilité est traitée par le mode dégradé (§ 9, chantier 2).
- [x] Les règles métier (éligibilité, plafonds, pièces exigées) sont-elles formalisées ? Qui les fait évoluer, et à quelle fréquence ?
  **Réponse en partie.** Elles sont formalisées dans la spec, version 3.2. Qui les fait évoluer reste **ouvert**. **Choix :** les seuils (30 jours, 5 000 €, 90 jours, 20 %, 1 500 €, 10 000 €, franchises et plafonds) sont regroupés dans une configuration qui porte le numéro de version de la spec, pour qu'un changement de règle ne touche pas le code des agents.
- [x] Un refus peut-il être prononcé de façon entièrement automatisée, ou doit-il être validé par un gestionnaire de sinistres ?
  **Réponse (§ 10).** La spec prévoit des refus automatiques : demande non éligible (règle 1) et montant estimé nul (règle 3), avec un motif. **Point à faire valider** par le service juridique du client : l'article 22 du RGPD encadre les décisions fondées exclusivement sur un traitement automatisé.
- [ ] Quelle erreur coûte le plus au métier : indemniser une fraude, ou refuser à tort une demande légitime ?
  **Ouvert**, mais la spec donne un indice : en mode dégradé, une demande de 1 500 € ou moins continue sans avis anti-fraude (§ 9). Le métier accepte donc un risque de fraude limité pour ne pas bloquer les petites demandes.
- [ ] Quelle équipe traite les escalades, et quelle est sa capacité de traitement journalière ?
  **Réponse en partie.** Deux files humaines : `gestionnaire` et `cellule_fraude` (§ 8). Leur capacité reste **ouverte**. *Impact : le taux d'escalade acceptable.*

### Résultats attendus

- [x] Quel délai de décision vise-t-on pour une demande ?
  **Réponse (§ 12).** Une issue en 10 secondes au plus de traitement automatisé, y compris quand le partenaire est lent, indisponible ou répond de manière non conforme.
- [ ] Quels indicateurs mesureront le succès à trois mois ?
  **Ouvert** pour le métier. Côté équipe, les métriques par agent sont fixées par `interface.md` (section 6).
- [x] Quelles décisions et quelles traces doivent être conservées, et qui en assure l'audit ?
  **Réponse en partie.** Chaque demande produit une fiche de décision (§ 11) avec sa trace et, s'il y a lieu, l'identifiant d'évaluation du partenaire, « à conserver pour audit » (contrat § 3). La durée de conservation et le responsable de l'audit restent **ouverts**.

Encore à recevoir : les tests d'acceptance (`tests/acceptance/`) et le pilote du partenaire simulé (`scripts/partner_ctl.py`), cités par `interface.md` mais absents de l'archive.

## 2. Le choix du pattern : l'arbre de décision

Les questions se posent dans l'ordre, et chaque réponse élimine une option. Q0 est issue de l'expression du besoin (section 1) ; Q1 à Q5 portent sur l'architecture (voir le schéma 0).

| # | Question | Réponse | Ce qu'elle écarte ou ajoute |
|---|---|---|---|
| Q0 | Le recours à un système agentique est-il justifié, au regard d'un traitement humain ou de règles simples ? | En partie : les règles sont chiffrées (§ 4 à § 10), l'avis de fraude vient d'un agent externe ; les documents, eux, demandent un modèle pour être lus | Retient : deux agents de lecture (modèle). Écarte : confier une règle chiffrée à un LLM. Éligibilité, pièces, montant, indicateurs et décision restent en code |
| Q1 | Un seul agent avec 10 à 15 outils suffit-il ? | Non | Écarte : l'agent unique. `interface.md` exige qu'un agent n'écrive qu'une seule section métier ; c'est aussi le défaut de l'agent actuel |
| Q2 | Les étapes sont-elles connues d'avance, et dans quel ordre ? | Oui : éligibilité et pièces, estimation, anti-fraude, issue (§ 2) | Écarte : un planificateur LLM qui invente les étapes. Le parcours est fixé par la spec, testable et bornable |
| Q3 | Des sous-tâches peuvent-elles s'exécuter en parallèle ? | Dans une demande, non utile : chaque contrôle dure 0,01 ms (journal, entrée 1). Entre les demandes d'un lot, oui (§ 12) | Retient : contrôles en séquence dans l'ordre de la spec, arrêt dès qu'une règle conclut ; demandes d'un lot en parallèle |
| Q4 | Faut-il un contrôle central qui garantit une décision ou une escalade pour chaque demande ? | Oui | Écarte : des agents qui se passent la main sans contrôle central ; personne ne garantirait l'issue de chaque demande, ni les 10 secondes |
| Q5 | Quelles métriques par agent faut-il rendre visibles ? | Appels, échecs, latence, appels externes (`interface.md`) | Ajoute : une trace à chaque étape (agent, sections écrites), source des métriques |

Pattern retenu : une Coordination centrale écrite en code (pattern superviseur) qui délègue chaque contrôle et applique les règles de décision, et quatre contrôles déterministes, chacun maître d'une seule section, en séquence avec court-circuit ; deux agents de lecture en amont pour les documents (phase E) ; un seul appel au partenaire par demande ; une trace à chaque étape.

La tension à arbitrer : le code déterministe est prévisible mais peu flexible ; un système tout agentique est flexible mais difficile à garantir. Ici chaque règle est chiffrée et les engagements sont absolus (une issue pour chaque demande, 10 secondes, données limitées au contrat). D'où le choix : un squelette en code, l'avis externe venant du partenaire.

Questions associées :

- [x] Un seul spécialiste suffit-il pour chaque demande, ou faut-il en combiner plusieurs ?
  **Réponse.** Chaque demande passe par plusieurs contrôles, dans l'ordre de la spec ; le contrôle anti-fraude n'appelle le partenaire que si un indicateur est présent.
- [x] Qui décide de la suite : le code, une boucle, un superviseur, ou les agents se vérifient-ils eux-mêmes ? [E1] [E6]
  **Réponse.** La Coordination, en code. Les agents ne s'appellent jamais entre eux et ne choisissent pas l'étape suivante.

## 3. La carte des agents [E2]

### Rôles et frontières

- [x] Quels sont exactement les agents ?
  **Réponse.** Cinq, un par section métier de `interface.md` : **Éligibilité** (`eligibilite`), **Pièces justificatives** (`pieces`), **Estimation** (`estimation`), **Anti-fraude**, liaison avec le partenaire (`avis_fraude`), et la **Coordination** (`issue`). « Une section métier n'est écrite que par un seul agent, et un agent n'écrit qu'une seule section métier. » Chaque section est remplie par le résultat d'un seul agent ; c'est la Coordination, seule à lire et à écrire l'état, qui l'y range (section 5).
  Le brief cite quatre agents (éligibilité, pièces, estimation, coordination). `interface.md` en impose un cinquième : il y a cinq sections métier, un agent par section, et la Coordination écrit déjà `issue`. La section `avis_fraude` revient donc à un agent de liaison avec le partenaire. Cet agent n'émet aucun avis : il calcule les indicateurs, appelle le partenaire et contrôle sa réponse.
- [x] Sous quel nom chaque agent apparaît-il dans la trace ?
  **Réponse.** Un nom fixe par agent, utilisé dans le champ `agent` de la trace et comme clé des métriques de `traiter_lot` (`interface.md`) : `coordination`, `eligibilite`, `pieces`, `estimation`, `antifraude`. Changer un nom casserait la lecture des métriques.
- [x] Pour chaque agent : que peut-il faire, et que ne doit-il surtout pas faire ?
  **Réponse :** voir la carte des agents en fin de section et le schéma 1. Les frontières viennent du § 2 : l'éligibilité ne chiffre pas, l'estimation ne se prononce pas sur la fraude, l'avis de fraude vient du partenaire, seule la décision conclut.
- [x] Les outils sont-ils partagés entre agents, ou chacun a-t-il les siens ?
  **Réponse.** Chacun les siens. Seul l'agent Anti-fraude dispose du client du partenaire et du jeton d'accès (`PARTENAIRE_JETON`) ; seul l'agent Pièces peut adresser une demande de complément à l'espace assuré.
- [x] Qui rend la décision finale, et qui rédige le motif ?
  **Réponse.** La Coordination, qui écrit la section `issue` en appliquant les règles du § 10 dans l'ordre, et rédige le motif destiné à l'assuré ou au gestionnaire (§ 11).
- [x] Comment prouver par un test qu'un agent ne sort pas de son rôle ?
  **Réponse.** Deux preuves. La trace : pour chaque étape, `agent` nomme l'agent dont le résultat a été rangé et `ecrit` la section remplie ; un test vérifie, sur les 28 scénarios, que chaque section n'est remplie que par son agent. Et deux tests unitaires : la Coordination refuse de ranger le résultat d'un agent dans une autre section (erreur de droits), et aucun agent ne reçoit l'état complet.

### Le contrat de chaque agent

Il s'agit du contrat interne entre agents, distinct d'un contrat d'API : l'entrée, la sortie, les erreurs possibles et une docstring qui dit en une phrase le rôle et la frontière de l'agent.

Exemple, pour l'agent Éligibilité :

```python
def verifier_eligibilite(demande: Demande) -> ResultatEligibilite:
    """Dit si le contrat couvre le sinistre (conditions E1 à E5 de la spec, § 4).

    Ne calcule aucun montant, n'applique pas le plafond, ne juge ni les pièces ni la fraude.
    Erreurs : DonneesIncompletes.
    """
```

| Agent | Entrée | Sortie | Erreurs possibles | Docstring (une phrase) |
|---|---|---|---|---|
| Éligibilité | contrat et sinistre, passés par la Coordination | éligible oui ou non ; conditions non remplies | données incomplètes | Dit si le contrat couvre le sinistre, sans chiffrer |
| Pièces justificatives | pièces, type de sinistre, dépôts de l'espace assuré, passés par la Coordination | complet, ou pièces manquantes ou illisibles ; factures lisibles ; compléments demandés | données incomplètes | Dit si les pièces exigées sont présentes, lisibles et du type attendu, et demande les compléments quand la Coordination le lui confie, sans conclure la demande |
| Estimation | montant déclaré, formule, factures lisibles, passés par la Coordination | montant justifié, montant retenu, montant estimé | données incomplètes | Calcule le montant remboursable, franchise et plafond compris, sans juger la fraude |
| Anti-fraude | huit données passées par la Coordination, dont le montant justifié | non requis ; ou avis (niveau, score, indicateurs, `evaluation_id`) ; ou indisponible avec la raison | délai dépassé, erreur du service, réponse non conforme : toutes rendent « indisponible », jamais une exception | Calcule les indicateurs F1 à F4 et, si l'un est présent, obtient l'avis du partenaire en un seul appel, sans jamais émettre d'avis lui-même |
| Coordination | l'état de la demande, qu'elle est seule à lire | section `issue`, rangement des résultats ; fiche de décision | borne atteinte, agent en échec : toutes deux mènent à une escalade motivée | Délègue chaque contrôle, applique les règles de décision dans l'ordre et conclut, sans refaire aucun contrôle |

### Les entrées passées par la Coordination

La Coordination est la seule à lire l'état de la demande. Elle déclenche chaque agent par un appel direct et lui passe seulement les données dont il a besoin ; l'agent renvoie son résultat, que la Coordination range dans la section de cet agent (section 5).

| Agent | Données passées par la Coordination | Ce que l'agent ne reçoit jamais |
|---|---|---|
| Éligibilité | statut du contrat, cotisations, formule, date de souscription ; type de sinistre, date de survenance, date de déclaration | identité, IBAN, description, pièces |
| Pièces justificatives | type de sinistre, pièces, dépôts de l'espace assuré | identité, IBAN, description, montants estimés |
| Estimation | montant déclaré, formule, factures lisibles (résultat de Pièces) | identité, IBAN, description |
| Anti-fraude | référence, type de sinistre, date de survenance, montant déclaré, date de souscription, sinistres sur 12 mois, code postal, montant justifié (résultat de l'Estimation) | identité, IBAN, description, pièces |

- [x] Le type de sinistre est-il saisi en texte libre ?
  **Réponse.** Non (§ 3) : `sinistre.type` est un champ structuré à quatre valeurs, et la description libre n'entre dans aucune règle. Si le type devait un jour être déduit du texte libre, ce serait un jugement : une étape de qualification en amont, candidate à un LLM avec un contrôle contre les quatre valeurs, et non une règle de l'Éligibilité.

### Garde-fous et métriques de bon fonctionnement, par agent

| Agent | Garde-fou | Métrique de bon fonctionnement |
|---|---|---|
| Éligibilité | le motif cite chaque condition non remplie ; aucun accès au montant | échecs ; refus par condition (NOM-02, NOM-03, NOM-04, NOM-10, NOM-11 en couvrent chacune une) |
| Pièces justificatives | demandes de complément bornées (2 au plus) ; une demande de complément n'est faite que sur délégation de la Coordination, après le résultat de l'Éligibilité | part des demandes avec complément ; échecs |
| Estimation | le montant n'est jamais négatif, jamais supérieur au plafond de la formule, arrondi au centime (NOM-05 le vérifie) | échecs ; latence |
| Anti-fraude | filtre sortant en liste blanche ; un seul appel par dossier (registre des appels, portée : une exécution) ; au plus 3 s, dans le temps restant de la demande ; réponse contrôlée avant usage (chantier 2) | appels externes, réponses écartées, part des demandes en mode dégradé |
| Coordination | bornes vérifiées avant chaque délégation ; seule à lire et à écrire l'état ; range chaque résultat dans la seule section de son agent | étapes consommées par demande, bornes atteintes (`arret`), part d'escalades |

### Le point ambigu

Le brief demande de le trancher, et il sera questionné à la validation du dossier.

- [x] Quel est le point ambigu entre deux agents, et qui en est le seul responsable ?
  **Réponse : le plafond de garantie.** La spec le range dans la section éligibilité (§ 4), mais « le contrôle d'éligibilité ne chiffre pas la demande » (§ 2), et la section estimation (§ 6) ne le cite pas. **Choix : l'Estimation l'applique**, parce que le plafond est un calcul de montant. Le scénario NOM-05 le confirme : 4 200 € déclarés, moins 300 € de franchise, soit 3 900 €, plafonnés à 3 000 € remboursés.
- [x] Qui déclenche le contrôle anti-fraude qui mène à l'appel du partenaire ?
  **Réponse (§ 7).** Il n'y a pas de « suspicion » à juger : le contrôle est requis dès qu'un des quatre indicateurs F1 à F4 est présent. L'agent Anti-fraude les calcule, après l'Estimation, car F4 compare le montant déclaré au montant justifié.

Autres frontières tranchées :

| Responsabilité | Agents qui pourraient la revendiquer | Choix et raison |
|---|---|---|
| Appliquer le plafond | Éligibilité, Estimation | Estimation (point ambigu ci-dessus) |
| Escalader pour pièces manquantes | Pièces, Coordination | Pièces le constate ; la Coordination escalade (règle 2), car « seule la décision conclut la demande » (§ 2) |
| Calculer le montant justifié | Pièces, Estimation | Estimation (§ 6), à partir des factures lisibles fournies par Pièces |
| Un montant déclaré supérieur aux factures | Pièces (« cohérence avec la déclaration », § 5), Anti-fraude (F4, § 7) | Anti-fraude, par l'indicateur F4 ; ce n'est pas un motif de demande de complément. Le scénario AF-06 le confirme : 2 000 € déclarés, 1 500 € justifiés, demande acceptée avec un avis faible |
| La « cohérence avec la déclaration » (§ 5) | Pièces, Anti-fraude | Pièces vérifie que les pièces sont du type exigé pour le type de sinistre déclaré (une photo pour un dégât des eaux, un dépôt de plainte pour un vol). Une pièce ne porte que `type`, `lisible` et `montant` (§ 3) ; l'écart de montant relève de F4 |
| Décider d'une demande de complément | Pièces, Coordination | La Coordination, après le résultat de l'Éligibilité ; Pièces l'adresse à l'assuré. Pièces ne lit pas `eligibilite` |

### Dépendances et parallélisme

- [x] Quelles étapes dépendent les unes des autres, et lesquelles peuvent s'exécuter en parallèle ?
  **Réponse (mise à jour le 08/10/2026).** Éligibilité, puis vérification des pièces, en séquence : les lancer en parallèle n'apportait rien (0,01 ms par contrôle, journal entrée 1), et une demande non éligible est refusée sans contrôle des pièces. La demande de complément, elle, attend l'Éligibilité : la Coordination ne la confie à Pièces que si la demande est éligible. L'Estimation attend les factures lisibles de Pièces. L'Anti-fraude attend l'Estimation (F4). La Coordination conclut en dernier. L'appel au partenaire n'est jamais lancé plus tôt : appeler pour une demande qui sera refusée gaspillerait l'unique appel autorisé et enverrait des données sans nécessité.
- [x] Quand deux résultats se contredisent (par exemple : éligible, mais pièces incomplètes), quelle règle l'emporte ?
  **Réponse.** L'ordre des règles du § 10 : la première qui s'applique fixe l'issue. Une demande non éligible est refusée quel que soit l'état de ses pièces (règle 1), et la demande de complément n'est alors jamais adressée à l'assuré.


### Règle métier ou jugement : ce que fait chaque rôle (mis à jour le 08/10/2026)

Vocabulaire de ce dossier, aligné sur celui du formateur : un **agent LLM** est un modèle qui lit ou juge, avec des
outils et une sortie vérifiée par le code ; un **contrôle déterministe** est du code, exact et testable ; la
**Coordination** est du code, seule à lire et écrire la mémoire et seule à conclure. Chaque rôle a un contrat (entrée,
sortie, erreurs) et un nom fixe dans la trace et les métriques, exigé par `interface.md`.

| Rôle | Nature | Entrée | Sortie | Modèle | Pourquoi ce choix | J'aurais pu… |
|---|---|---|---|---|---|---|
| Lecteur de contrat | agent LLM | le texte du contrat PDF (extrait en code par PyMuPDF) | numéro, formule, date de souscription, statut, cotisations à jour (schéma strict `ContratLu`) | gpt-5.4 (Azure AI Foundry, API Responses) | comprendre un document fait pour un humain, aux mises en page variées ; mesuré : 34/34 contrats lus juste | utiliser des règles après un OCR ; écarté : fragile dès que la mise en page change |
| Lecteur de pièces | agent LLM (vision) pour les factures nettes ; code pour le reste | une image et son type (créneau choisi par l'assuré) | lisible ou non ; montant TTC pour une facture (schéma strict `FactureLue`) | gpt-5.4, vision | une image floue, une photo, un dépôt de plainte ne partent jamais au modèle (netteté mesurée en code) ; dans le doute : illisible ; mesuré : 33/33 montants, 68/68 lisibilités | envoyer toutes les images au modèle ; écarté : 35 documents sur 102 n'en ont pas besoin (coût, délai, données envoyées) |
| Éligibilité | contrôle déterministe | le contrat et le sinistre | éligible ou non, conditions non remplies | aucun | E1 à E5 : des dates, des statuts, une liste, écrits dans la spec ; la réponse doit être exacte à la frontière (conseil du formateur du 07/10 : un outil) | un agent LLM avec les règles dans son prompt ; écarté : moins sûr aux seuils, un appel de modèle en plus |
| Pièces justificatives | contrôle déterministe | type de sinistre, pièces lues, dépôts | complet ou non, pièces manquantes, montants lisibles ; demande de complément groupée | aucun | présence, lisibilité, type attendu : des règles ; toutes les pièces manquantes sont demandées en une fois | un agent LLM ; à reconsidérer pour la **cohérence avec la déclaration** (§ 5), question posée au formateur le 08/10 |
| Estimation | contrôle déterministe | montant déclaré, formule, factures lisibles | montant justifié, retenu, estimé | aucun | un calcul : franchise et plafond ; un montant calculé par un LLM serait un risque | un agent LLM qui expliquerait le calcul ; écarté : aucun besoin du parcours |
| Anti-fraude | contrôle déterministe et client de l'agent externe | 8 données, jamais l'identité ni l'IBAN | indicateurs F1 à F4 ; avis du partenaire, non requis ou indisponible | aucun en interne | l'avis est « émis par le partenaire, jamais en interne » (§ 2) | un LLM interne ; interdit par la spec |
| Coordination | code (workflow déterministe) | la demande complète | la fiche de décision (§ 11) | aucun | l'ordre des règles est fixé par le § 10 ; elle centralise la mémoire et conclut seule | un superviseur LLM ; écarté : coût, délai, imprévisibilité pour un parcours écrit dans la spec |
| Partenaire anti-fraude | agent externe (A2A) | 7 champs du contrat d'échange | un avis : faible, modéré, élevé | le sien | une autre entreprise ; chantier 2 | aucun choix de notre côté |

**Parcours utilisateur retenu** (il décide de la place d'un modèle) : l'assuré dépose ses pièces dans son espace en
ligne (§ 3, `espace_assure`) ; la fiche porte un motif « rédigé pour l'assuré ou le gestionnaire » (§ 11) ; les
escalades vont à des files humaines. Un courrier rédigé par un modèle n'est donc pas nécessaire.

**Chaque exigence, et ce qui la garantit dans le code :**

| Exigence | Élément du code | Preuve |
|---|---|---|
| [E1] toute demande a une issue motivée | `coordination.traiter` : bornes, puis filet de sécurité ; `escalade_directe` pour une lecture impossible | test `test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee` |
| [E2] une section, un écrivain | `etat.ranger` : table `SECTION_DE`, type contrôlé, section écrite une fois (sauf `pieces`) | `verifier_roles` (tests du formateur) |
| [E3] seules les données prévues sortent | l'Anti-fraude ne reçoit que 8 données ; filtre de 7 champs (chantier 2) | test de frontière des paramètres ; tests A2A (chantier 2) |
| [E4] une réponse non conforme est écartée | validation de la réponse du partenaire (chantier 2) | tests A2A (chantier 2) |
| [E5] partenaire indisponible : mode dégradé | `continue_en_mode_degrade` (1 500 €) | tests unitaires de la Coordination |
| [E6] aucune boucle, métriques visibles, ajustements consignés | bornes (étapes, durée, « même état vu deux fois ») ; `metriques.py` ; `journal-ajustements.md` | `test_scenario_piege_a_boucle_s_arrete_dans_les_bornes` ; métriques des 7 rôles |

**Patterns écartés, une raison chacun :** un agent unique avec 10 à 15 outils (une section, un écrivain) ; un
superviseur LLM (le chemin est écrit dans la spec) ; un planificateur qui invente les étapes (étapes connues) ; une
machine à états avec table de transitions (une séquence de règles suffit, plus simple à tester) ; des agents qui se
passent la main (personne ne garantirait l'issue) ; des contrôles en parallèle dans une demande (0,01 ms par contrôle,
journal entrée 1).

**Honnêteté de conception :** les documents de l'évaluation sont synthétiques et propres, 100 % ici n'est pas 100 % sur
de vrais scans ; un montant plausible mais faux passe le schéma (c'est ce que l'évaluation mesure) ; le contenu des
photos n'est pas vérifié ; le statut et les cotisations devraient venir des fichiers de l'assureur, pas du contrat
signé ; la phrase de garde contre l'injection est une précaution, pas une preuve.

**Pourquoi des rôles séparés, même quand c'est du code ?**

1. Chaque agent rend un service sans montrer ses règles. La Coordination demande « cette demande est-elle éligible ? » et reçoit oui ou non avec les conditions non remplies, sans connaître les seuils. Si le métier passe la carence de 30 à 45 jours, seul l'agent Éligibilité change. Le partenaire anti-fraude fonctionne déjà ainsi : il rend un avis sans révéler son modèle.
2. La frontière se prouve : une section, un propriétaire, vérifié dans la trace sur les 28 scénarios [E2].
3. Le contrat ne change pas si la réalisation change. L'agent Pièces peut passer au LLM sans toucher la Coordination ni la mémoire. Trois choses changent alors : un budget de tokens (mesuré pour les agents de lecture depuis l'étape E5, section 4), une validation de sa sortie, et la règle « pas de relance », qui suppose un code déterministe.
4. Les métriques se lisent par agent (appels, échecs, latence), sous un nom fixe (`interface.md`).
5. Agent LLM ou contrôle déterministe, l'architecture est la même : la Coordination appelle et reçoit un résultat. Les deux agents de lecture ont été ajoutés le 08/10 sans changer la chaîne de décision (34 décisions sur 34 identiques).

**Comment les agents communiquent.** Aucun agent ne lit la mémoire : la Coordination lui passe ses entrées et range son résultat. Ici, les agents internes sont des fonctions appelées par la Coordination, dans le même processus : une seule équipe les maintient, et c'est le plus sûr pour tenir 10 s. Si un contrôle appartenait à un autre service de l'entreprise, il serait exposé par une API ou une interface d'agent, comme le partenaire en A2A. Ce choix dépend de l'organisation, pas des règles de décision.

Le schéma A montre cette architecture générale sur une seule vue.

### La carte des agents

| Agent | Rôle | Reçoit | Renvoie | Ne fait jamais | Code ou LLM |
|---|---|---|---|---|---|
| Coordination | délègue, vérifie les bornes, range les résultats, applique les règles du § 10, conclut | l'état complet, qu'elle est seule à lire | `issue`, fiche de décision | refaire un contrôle | code |
| Éligibilité | conditions E1 à E5 de la spec | contrat, sinistre (passés par la Coordination) | éligible, conditions non remplies | chiffrer, appliquer le plafond, juger les pièces ou la fraude | code |
| Pièces justificatives | présence, lisibilité, type attendu des pièces ; demandes de complément confiées par la Coordination | pièces, dépôts de l'espace assuré (passés par la Coordination) | complet ou manquantes, factures lisibles | conclure ou escalader, chiffrer, juger la fraude, décider seul d'une demande de complément | code |
| Estimation | montant justifié, retenu, estimé ; franchise et plafond | montant déclaré, formule, factures lisibles (passés par la Coordination) | montants | juger la fraude, revenir sur l'éligibilité | code |
| Anti-fraude | indicateurs F1 à F4 ; un appel au partenaire ; contrôle de la réponse | huit données passées par la Coordination | non requis, avis ou indisponible | émettre un avis en interne, envoyer une donnée hors contrat, relancer un appel | code |

## 4. L'orchestration et la terminaison garantie [E1] [E6]

- [x] Quel schéma d'orchestration : superviseur qui délègue, chaîne séquentielle, mixte ?
  **Réponse : superviseur, en séquence.** La Coordination délègue chaque contrôle dans l'ordre de la spec et s'arrête dès qu'une règle conclut. Les agents ne s'appellent jamais entre eux.
- [x] Qui déclenche chaque agent, l'Éligibilité par exemple ?
  **Réponse.** La Coordination, par un appel direct, avec les données dont l'agent a besoin. Aucun agent ne surveille la mémoire pour y trouver du travail : il attend d'être appelé, renvoie son résultat, et la Coordination le range avant de décider de l'appel suivant.
- [x] Qui décide qu'une demande est terminée ?
  **Réponse.** La Coordination seule, en écrivant la section `issue` (« seule la décision conclut la demande », § 2). Elle applique les règles du § 10 dans l'ordre ; la première qui s'applique fixe l'issue.
- [x] Quels sont les états finaux possibles ?
  **Réponse (§ 2, § 11).** Deux issues seulement : une **décision** (acceptée ou refusée) ou une **escalade** vers `gestionnaire` ou `cellule_fraude`, avec un motif lisible. Il n'existe pas d'état « en attente » sans qu'un humain en ait été saisi. Le schéma 2 montre que chaque chemin mène à l'une de ces issues.
- [x] Comment borne-t-on les boucles ?
  **Réponse.** Une seule boucle existe dans le parcours : la demande de complément de pièces, qui reprend le contrôle après chaque dépôt de l'assuré (§ 5). Elle est bornée par le nombre de compléments, par la détection d'un état déjà vu et par les bornes globales (étapes et durée).
- [x] Qu'est-ce qu'une étape ?
  **Réponse.** Une délégation de la Coordination à un agent : l'appel avec ses entrées, le résultat renvoyé et son rangement dans la section de l'agent, soit une ligne de trace. Une demande de complément, avec la lecture du dépôt de l'assuré et le nouveau contrôle des pièces, compte pour une étape. L'écriture de l'issue par la Coordination est la dernière étape.
- [x] Quelles bornes au départ, et sur quelle base les choisit-on ?
  **Réponse :** voir le tableau ci-dessous. La durée vient de l'engagement de service ; le nombre d'étapes vient du chemin le plus long prévu par la spec et les scénarios ; le délai du partenaire vient de son contrat.
- [x] Que se passe-t-il quand une borne est atteinte ?
  **Réponse.** Jamais un arrêt silencieux. La demande reçoit une issue, une escalade vers `gestionnaire`, et sa fiche le signale dans `arret` avec le nom de la borne (`interface.md`). La file de destination n'est pas fixée par la spec, et le scénario BCL-01 ne vérifie que l'escalade et l'arrêt signalé : **choix à confirmer** avec le client.
  Pour que la trace ne dépasse jamais `etapes_max` (`interface.md`), la Coordination ne délègue plus aucun contrôle dès que la trace atteint `etapes_max` moins une étape : la dernière est réservée à l'écriture de l'issue. De même, elle arrête de déléguer avant la fin des 10 s, en gardant le temps de produire la fiche.
- [x] Comment un lot de demandes est-il traité ?
  **Réponse (§ 12).** « Le traitement d'une demande n'est jamais retardé par celui d'une autre. » `traiter_lot` traite donc les demandes du lot **en concurrence**, chacune avec son propre état et sa propre durée de 10 s ; les fiches sont rendues dans l'ordre des demandes (`interface.md`). Traitées l'une après l'autre, trois demandes qui attendent chacune le partenaire jusqu'à 3 s (scénario PAN-02) retarderaient la troisième d'environ 6 s. Le plan d'épreuve mesure ce point sur PAN-01 et PAN-02.
- [x] Qu'est-ce qu'une escalade « motivée » ?
  **Réponse (§ 8).** Elle précise la file destinataire et un motif lisible par le gestionnaire qui reprend le dossier : la règle ou la borne en cause, et l'étape atteinte. La trace complète accompagne la fiche.
- [x] Que se passe-t-il quand un agent interne plante, renvoie un format invalide ou dépasse son délai ?
  **Réponse.** Les agents internes sont du code déterministe : relancer avec la même entrée redonnerait la même erreur. Pas de relance : escalade immédiate vers `gestionnaire`, motif « erreur interne » avec le nom de l'agent, et l'échec compte dans les métriques. L'appel au partenaire suit une autre règle, celle de son contrat : jamais de relance, et toute défaillance rend l'avis « indisponible » (chantier 2).
- [x] Quelle gestion d'erreur observable met-on en place dans le workflow ?
  **Réponse.** Chaque étape écrit une ligne de trace avec son statut ; chaque échec compte dans `echecs` ; chaque arrêt par une borne est signalé dans `arret`.

### Les bornes provisoires

Les valeurs fixées par la spec ou le contrat ne sont pas provisoires. Les autres sont des valeurs de départ : le plan d'épreuve du chantier 2 les confirme ou les ajuste, et chaque ajustement entre dans le journal (voir [chantier 2, section 10](chantier-2-a2a-epreuve.md)).

| Borne | Valeur de départ | Justification | Scénario d'épreuve qui la teste |
|---|---|---|---|
| Durée par demande (`duree_max_s`) | 10 s | engagement de service (§ 12), maximum autorisé par `interface.md`. Décision du 08/10 : le budget commence à l'arrivée du dossier et couvre la lecture des pièces ; chaque appel au modèle reçoit le temps restant, et la Coordination continue la même limite. Mesure réelle du 08/10 : lecture la plus longue 8,94 s sur 34 dossiers, pour une limite de 9,5 s (marge faible, à surveiller). Si la mesure montre qu'une demande arrêtée à 10 s dépasse l'engagement le temps de produire sa fiche, la borne descendra à 8 s | PAN-02 (partenaire lent) |
| Étapes par demande (`etapes_max`) | 8 | chemin nominal : 5 étapes (éligibilité, pièces, estimation, anti-fraude, issue) ; plus 2 demandes de complément, soit 7 pour le chemin le plus long ; plus 1 de marge. La dernière étape est toujours réservée à l'issue | BCL-01 (piège à boucle) |
| Demandes de complément par demande | 2 | NOM-07 et PAN-01 en demandent une ; aucun scénario n'en justifie davantage | BCL-01 |
| Même état vu deux fois | arrêt immédiat | une pièce toujours illisible après un nouveau dépôt ne fait pas avancer la demande | BCL-01 |
| Appels au partenaire par dossier | 1 exactement | contrat, § 6 : un seul appel, aucune relance, tout doublon est refusé et signalé | PAN-01, PAN-02, scénarios `invalide` |
| Délai d'un appel au partenaire | 3 s | contrat, § 5 : le client abandonne au plus tard 3 s après l'envoi | PAN-02 |
| Délai par contrôle interne | objectif 1 s, non imposé | contrôles en code, sans réseau, mesurés à 0,01 ms ; Python ne peut pas interrompre une fonction de l'extérieur, la limite de 10 s est vérifiée avant chaque étape | cas nominal |
| Budget de tokens ou de coût | mesuré, hors décision | les deux agents de lecture consomment des jetons (32 180 en entrée, 2 480 en sortie pour 34 dossiers, étape E5) ; aucun LLM dans le chemin de décision | évaluation E4 |

Lecture du scénario BCL-01 : la facture est illisible, et le seul dépôt de l'assuré est une facture tout aussi illisible. Ce n'est pas « aucun dépôt du type demandé » (§ 5), donc la spec demanderait un nouveau complément, sans fin. Le scénario attend une escalade avec `arret` : c'est la borne « même état vu deux fois » qui l'arrête, à la quatrième étape (éligibilité, pièces, demande de complément qui retrouve le même état, issue). Cette lecture sera vérifiée contre les tests d'acceptance quand ils seront fournis.

Les dépôts de l'espace assuré se lisent dans l'ordre : le premier dépôt répond à la première demande de complément, le deuxième à la deuxième (§ 3).

## 5. La mémoire partagée

Le brief demande une mémoire partagée de la demande, avec un état commun et un accès maîtrisé.

- [x] Que contient l'état partagé de la demande ?
  **Réponse.** La demande reçue (§ 3), en lecture seule ; les cinq sections métier (`eligibilite`, `pieces`, `estimation`, `avis_fraude`, `issue`) ; la trace, en ajout seul. Hors de l'état : l'échéance de la demande et le registre des appels (une exécution) ; `arret` est écrit dans la fiche.
- [x] Sous quelle forme, et où vit-elle ?
  **Réponse.** En mémoire, un objet par demande, créé au début de `traiter_demande` et jamais partagé entre deux demandes : le traitement d'une demande n'en retarde pas une autre (§ 12). À la fin, la fiche de décision est construite depuis `issue`, `avis_fraude`, la trace et `arret`.
- [x] Accès maîtrisé : qui lit et qui écrit quels champs ?
  **Réponse.** La Coordination est la seule à lire et à écrire l'état de la demande. Elle appelle chaque agent directement, en lui passant seulement les données dont il a besoin (section 3) ; l'agent ne voit pas l'état, il renvoie son résultat ; la Coordination range ce résultat dans la section de cet agent, puis décide de l'appel suivant. Voir le tableau ci-dessous.
- [x] Comment un agent évite-t-il d'écraser le travail d'un autre ?
  **Réponse.** Un agent ne peut rien écraser : il n'a aucun accès à l'état. Une table fixe associe chaque agent à sa section ; la Coordination range le résultat d'un agent dans cette seule section et refuse tout autre rangement (erreur de droits). `pieces` est remplie à nouveau après chaque dépôt de l'assuré ; les autres sections métier ne le sont qu'une fois. Les contrôles tournent en séquence et un seul composant écrit : aucun conflit possible. Chaque section métier reste alimentée par un seul agent, comme l'exige `interface.md` : la ligne de trace de l'étape porte le nom de l'agent (`agent`) et la section remplie par son résultat (`ecrit`).
- [x] Peut-on reprendre une demande après un crash, sans la bloquer de nouveau ?
  **Réponse (mise à jour le 08/10/2026).** Une demande se traite en 10 s au plus : en cas de crash, elle est reprise depuis le début, les contrôles en code donnant le même résultat. **Une exception, imposée par le contrat du partenaire** : un seul appel par dossier, et un doublon est signalé comme manquement. La Coordination réserve donc la référence dans le registre des appels avant l'envoi : dans une même exécution (une demande ou un lot), un second appel est bloqué et l'avis est « indisponible ». **Limite écrite** (journal, entrées 2 et 3) : après un redémarrage, le registre est vide et la protection n'est pas assurée ; si le partenaire a déjà évalué le dossier, il répond -32029, traité comme une erreur (avis indisponible, mode dégradé). Une protection durable demanderait un stockage persistant.
- [x] Quels champs de la mémoire ne doivent jamais partir chez le partenaire ? [E3]
  **Réponse (contrat, § 2).** L'identité et les coordonnées de l'assuré (nom, prénom, e-mail, téléphone, adresse, code postal complet), l'IBAN, l'identifiant client et le numéro de contrat, la description libre du sinistre, les pièces et leur contenu. Seuls sept champs partent, construits par l'agent Anti-fraude (chantier 2), qui ne reçoit lui-même que huit données de la Coordination.
- [x] Où range-t-on l'identifiant de l'évaluation du partenaire ?
  **Réponse.** Dans la section `avis_fraude` : niveau, score, indicateurs, `evaluation_id` (à conserver pour audit, contrat § 3) et version du modèle. Le contrat ne prévoit qu'un appel `message/send` qui renvoie une tâche terminée : pas d'identifiant de tâche à suivre ni à annuler.

### Les droits sur la mémoire

**Mémoire de session et informations exposées : deux niveaux distincts.** L'état de la demande est une mémoire de session : il vit le temps du traitement, dans la plateforme, et n'est jamais exposé. Sa gestion est un choix interne : seule la Coordination le lit et l'écrit. `interface.md` fixe autre chose : ce que la plateforme expose au système d'information et à la suite d'acceptance (fiche de décision, trace, métriques). La trace y dit, pour chaque étape, quel agent a produit la section remplie (`agent`, `ecrit`). Le partenaire, lui, ne voit que les sept champs de son contrat (A2A) : la mémoire d'un agent n'est jamais exposée par A2A.

Seule la Coordination lit et écrit l'état. Le tableau dit, pour chaque section, quel agent fournit le résultat et à qui la Coordination en passe ensuite le contenu.

| Section de l'état | Remplie par le résultat de | Rangée par | Contenu passé ensuite à |
|---|---|---|---|
| `demande` (données reçues) | à la création, puis lecture seule | Coordination | chaque agent reçoit seulement ses entrées (section 3) |
| `eligibilite` | Éligibilité | Coordination | la Coordination (règle 1) |
| `pieces` | Pièces (après chaque dépôt) | Coordination | l'Estimation (factures lisibles), la Coordination (règle 2) |
| `estimation` | Estimation | Coordination | l'Anti-fraude (montant justifié), la Coordination (règles 3 et 5) |
| `avis_fraude` | Anti-fraude | Coordination | la Coordination (règle 4) |
| `issue` | Coordination | Coordination | la fiche de décision |
| hors de l'état (mis à jour le 08/10) : l'échéance de la demande et le registre des appels (une exécution) ; `arret` est écrit dans la fiche | Coordination | Coordination | la Coordination |
| `trace` : une ligne par étape, ajout seul | chaque étape, au nom de l'agent dont le résultat est rangé | Coordination | métriques, fiche de décision |

L'agent Anti-fraude ne reçoit ni l'identité de l'assuré, ni son IBAN, ni la description, ni les pièces : il ne peut pas envoyer ce qu'il ne reçoit pas. [E3] est ainsi tenu deux fois, à l'entrée de l'agent et à la sortie du filtre (chantier 2).

## 6. L'observabilité et le plan de preuve [E6]

Le partenaire peut être lent, en panne ou répondre de manière non conforme : chaque affirmation sur le comportement de l'équipe doit se prouver par une trace ou par un test.

- [x] Quel événement enregistre-t-on à chaque étape ?
  **Réponse (`interface.md`).** Une ligne de `trace` par étape : l'agent, les sections écrites (`ecrit`), puis l'action, la durée et le statut.
- [x] Quelles métriques par agent en découlent ?
  **Réponse (`interface.md`).** Pour chaque agent : `appels` (étapes réalisées), `echecs` (erreur, délai dépassé, réponse écartée), `latence_ms` (durée moyenne d'une étape), `appels_externes`. Elles sont renvoyées par `traiter_lot`.
- [x] Quels éléments observe-t-on au niveau de l'équipe et de son orchestration ?
  **Réponse.** Les étapes consommées par demande, les bornes atteintes (`arret`), la part d'escalades par file, la part des demandes traitées en mode dégradé.
- [x] Comment montrer qu'une demande a suivi le bon chemin ?
  **Réponse.** Par sa trace : la suite des agents et des sections remplies se compare au chemin attendu par les règles du § 10.
- [x] Comment prouver [E1] sur tous les scénarios ?
  **Réponse.** Un test rejoue les 28 scénarios de `eval/scenarios.jsonl` et vérifie que chaque fiche porte une issue (`decision` ou `escalade`), conforme au champ `attendu`, en 10 s au plus.
- [x] Comment prouver [E2] ?
  **Réponse.** Sur les mêmes rejeux, un test vérifie dans la trace que chaque section métier n'est remplie que par le résultat de son agent. Deux tests unitaires : la Coordination refuse de ranger le résultat d'un agent dans une autre section (erreur de droits), et aucun agent ne reçoit l'état complet.

Le filtre des données sortantes, la validation des réponses du partenaire et le mode dégradé sont traités au [chantier 2](chantier-2-a2a-epreuve.md).

## 7. Cas d'usage : quatre demandes suivies de bout en bout

Chaque cas est un scénario de `eval/scenarios.jsonl`. Une étape est une délégation de la Coordination, soit une ligne de trace.

### Cas 1 : une pièce manquante, puis déposée (NOM-07, KAL-26-0107)

Situation : formule premium, dégât des eaux du 2 août 2026 déclaré le lendemain, 2 300 € déclarés ; facture lisible, photo absente ; l'assuré dépose une photo lisible après la demande de complément.

| Étape | Agent | Section remplie | Résultat |
|---|---|---|---|
| 1 | eligibilite | eligibilite | éligible : les cinq conditions sont remplies |
| 2 | pieces | pieces | photo manquante |
| 3 | pieces, sur délégation de la Coordination | pieces (remplie à nouveau) | complément adressé, photo déposée, pièces complètes |
| 4 | estimation | estimation | justifié 2 300 €, franchise 0 €, estimé 2 300 € |
| 5 | antifraude | avis_fraude | aucun indicateur F1 à F4 : avis non requis, aucun appel |
| 6 | coordination | issue | règles 1 à 5 non applicables, règle 6 : acceptée |

Issue : décision acceptée, 2 300 € remboursés, sans avis ni mode dégradé. Ce que le cas montre : la boucle de complément, `pieces` remplie à nouveau par le seul résultat de Pièces, la décision du complément par la Coordination après l'éligibilité.

### Cas 2 : un contrat résilié (NOM-02, KAL-26-0102)

Situation : formule essentiel, contrat au statut `resilie`, incendie de 2 400 € avec facture et photo.

| Étape | Agent | Section remplie | Résultat |
|---|---|---|---|
| 1 | eligibilite | eligibilite | non éligible : condition E1 (contrat actif) non remplie |
| 2 | coordination | issue | règle 1 : refusée ; les pièces ne sont pas contrôlées (court-circuit) |

Issue : décision refusée, 0 €, le motif cite la condition E1. Ce que le cas montre : l'arrêt anticipé ; ni estimation, ni appel au partenaire, ni sollicitation de l'assuré.

### Cas 3 : le point ambigu, le plafond (NOM-05, KAL-26-0105)

Situation : formule essentiel (franchise 300 €, plafond 3 000 €), dégât des eaux de 4 200 € avec facture et photo.

| Étape | Agent | Section remplie | Résultat |
|---|---|---|---|
| 1 | eligibilite | eligibilite | éligible |
| 2 | pieces | pieces | pièces complètes |
| 3 | estimation | estimation | retenu 4 200 €, moins 300 € = 3 900 €, plafonné à 3 000 € |
| 4 | antifraude | avis_fraude | aucun indicateur (4 200 € < 5 000 €) : avis non requis |
| 5 | coordination | issue | règle 6 : acceptée |

Issue : décision acceptée, 3 000 € remboursés. Ce que le cas montre : le plafond appliqué par l'Estimation, jamais par l'Éligibilité.

### Cas 4 : le piège à boucle (BCL-01, KAL-26-0601)

Situation : formule confort, dégât des eaux de 1 400 € ; la facture est illisible, et le seul dépôt de l'assuré est une facture tout aussi illisible.

| Étape | Agent | Section remplie | Résultat |
|---|---|---|---|
| 1 | eligibilite | eligibilite | éligible |
| 2 | pieces | pieces | facture illisible |
| 3 | pieces, sur délégation de la Coordination | pieces (remplie à nouveau) | complément adressé, nouveau dépôt illisible : même état qu'à l'étape 2 |
| 4 | coordination | issue | borne « même état vu deux fois » : escalade gestionnaire |

Issue : escalade, `arret` renseigné avec le nom de la borne, trace de 4 étapes. Ce que le cas montre : la boucle arrêtée par une borne, jamais un blocage silencieux.

Les cas d'usage de la liaison avec le partenaire (avis faible, avis modéré, réponse écartée, partenaire lent) sont au [chantier 2, section 10](chantier-2-a2a-epreuve.md).

## Points ouverts

| Point | Pourquoi il reste ouvert | Qui tranche |
|---|---|---|
| File de l'escalade quand une borne est atteinte | la spec ne la fixe pas ; choix actuel : `gestionnaire` | le client |
| Refus automatiques (règles 1 et 3) | article 22 du RGPD | le service juridique du client |
| Lecture du scénario BCL-01 | dépôt illisible : la spec ne dit pas s'il compte comme un dépôt | les tests d'acceptance, absents de l'archive |
| Durée de 10 s ou 8 s | dépend du temps mesuré pour produire la fiche | le plan d'épreuve du chantier 2 |
| Attente réelle de l'assuré après une demande de complément | les 10 s portent sur le traitement automatisé (§ 12) ; dans les scénarios, les dépôts sont déjà dans `espace_assure`. En production, l'attente d'un dépôt qui peut prendre des jours n'est pas décrite | le client |

## Schémas

Fondés sur `specs_metier.md` (version 3.2) et `interface.md`. Restent provisoires : les valeurs des bornes, à éprouver au chantier 2, et la file de l'escalade sur borne atteinte. Chaque schéma existe en `.drawio`, modifiable sur [app.diagrams.net](https://app.diagrams.net/), et en `.png`. Ils se régénèrent avec `scripts/make_schemas_ch1.py`.

### A. L'architecture générale

Une seule vue : l'entrée `traiter_lot`, la Coordination (seule à lire et à écrire la mémoire, elle appelle chaque agent et reçoit son résultat), les quatre agents de contrôle et la section que remplit le résultat de chacun, la mémoire partagée de la demande, le mode dégradé, l'espace assuré, le partenaire, les métriques et les deux issues possibles. Les deux encadrés de gauche résument pourquoi les contrôles restent des agents et comment ils communiquent (section 3). Fichiers : [schema-A-architecture-generale.drawio](schemas/schema-A-architecture-generale.drawio), [PNG](schemas/schema-A-architecture-generale.png).

![Architecture générale](schemas/schema-A-architecture-generale.png)

### 0. Le choix du pattern : l'arbre de décision

Une question métier (Q0), puis cinq questions d'architecture posées dans l'ordre ; chaque réponse élimine une option, jusqu'au pattern retenu. Fichiers : [schema-0-arbre-de-decision.drawio](schemas/schema-0-arbre-de-decision.drawio), [PNG](schemas/schema-0-arbre-de-decision.png).

![Arbre de décision du pattern](schemas/schema-0-arbre-de-decision.png)

### 1. La carte des agents

Les cinq agents, la section que remplit le résultat de chacun, ses interdits, le point ambigu tranché (le plafond) et les dépendances. Fichiers : [schema-1-carte-des-agents.drawio](schemas/schema-1-carte-des-agents.drawio), [PNG](schemas/schema-1-carte-des-agents.png).

![Carte des agents](schemas/schema-1-carte-des-agents.png)

### 2. L'orchestration et la terminaison garantie

Les règles de décision du § 10 dans l'ordre, la boucle de la demande de complément, le mode dégradé, les bornes ; chaque chemin finit par une décision ou une escalade motivée. Fichiers : [schema-2-orchestration.drawio](schemas/schema-2-orchestration.drawio), [PNG](schemas/schema-2-orchestration.png).

![Orchestration et terminaison garantie](schemas/schema-2-orchestration.png)

### 3. La mémoire partagée de la demande

Les sections, l'agent dont le résultat remplit chacune, la Coordination seule à lire et à écrire l'état, la règle de rangement et le lieu de vie de l'état. Fichiers : [schema-3-memoire-partagee.drawio](schemas/schema-3-memoire-partagee.drawio), [PNG](schemas/schema-3-memoire-partagee.png).

![Mémoire partagée de la demande](schemas/schema-3-memoire-partagee.png)
