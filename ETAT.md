# État du développement

## ▶️ Prochaine action

Étape 1.4 : les quatre agents complets (Pièces : demande de complément, NOM-07 et BCL-01), avec un test par cas cité.

## Mesures

| Date | Python | Commande | Résultat |
|---|---|---|---|
| 07/10/2026 | 3.14 (historique, hors version exigée) | `C:\Python314\python.exe -m pytest tests/acceptance -q` sur le code de départ | 11 passed, 45 failed (56 tests) |
| 07/10/2026 | 3.14 | `C:\Python314\python.exe -m ruff check .` | All checks passed! |
| 07/10/2026 | **3.11.15, référence** | `.venv\Scripts\python.exe -m pytest tests/acceptance -q` sur le code de départ | **11 passed, 45 failed (56 tests)** |
| 07/10/2026 | 3.11.15 | `.venv\Scripts\python.exe -m ruff check .` (ruff 0.9.10) | All checks passed! |
| 07/10/2026 | 3.11.15 | étape 1.1 : `.venv\Scripts\python.exe -m pytest tests/unit -q` | 4 passed (rouge vu avant : `module 'kaldera' has no attribute 'bornes'`) ; acceptance inchangée, 11/56 |
| 07/10/2026 | 3.11.15 | étape 1.2 : `.venv\Scripts\python.exe -m pytest tests/acceptance -q` | **38 passed, 18 failed** ; chantier 1 : 38/40 (restent NOM-07 et la borne BCL-01) ; NOM-02 en 2 étapes. Attention : les 28 contrôles « issue motivée » passent en partie parce que la règle 4 manque encore |
| 07/10/2026 | 3.11.15 | étape 1.3 : `.venv\Scripts\python.exe -m pytest tests/unit -q` | rouge d'abord : 6 failed, 13 passed ; puis **23 passed**. Défaut réel trouvé et corrigé : F4 déclenché à 20 % pile (1 234,50 / 1 481,40), calcul passé en centimes entiers (commit `1882c91`) ; acceptance inchangée, 38/56 |

`pyproject.toml` exige Python `>=3.11,<3.12` : seule une mesure sous 3.11 vaut preuve.

Installation (07/10) : le Python 3.11 installé est géré par `uv` et refuse `pip install --user` (PEP 668, « externally-managed-environment »). Procédure retenue : un environnement virtuel `.venv` (ignoré par Git), que Smart App Control laisse s'exécuter : `py -V:Astral/CPython3.11.15 -m venv .venv`, puis `.venv\Scripts\python.exe -m pip install --upgrade pip`, puis `.venv\Scripts\python.exe -m pip install -e . --group dev`.

## Ce que mesurent les tests d'acceptance

- **40 tests du chantier 1** (`test_equipe_orchestration.py`) : 11 issues nominales comparées à `attendu`, 28 contrôles « issue motivée » (un par scénario, **sans comparer le résultat métier**), 1 test de borne (BCL-01).
- **16 tests du chantier 2** (`test_collaboration_a2a.py`) : 7 anti-fraude, 7 réponses invalides, 2 pannes, contre le partenaire **simulé** que la suite démarre elle-même.
- Ce qu'ils ne prouvent pas, couvert par nos tests : le temps d'un lot (la suite tolère 10 s × nombre de demandes), l'absence de contenu rejeté **dans la trace**, la justesse des métriques (seul leur type est vérifié), l'impossibilité pour un agent de modifier l'état (seule l'attribution dans la trace est vérifiée).

40/40 puis 56/56 sont des jalons, pas la preuve de tout.

## Règles de chaque étape

1. Avant : ce qu'il faut lire, et pourquoi l'étape existe.
2. Test rouge d'abord : il aide à vérifier que le test détecte bien le défaut visé.
3. Code : mode A (Claude écrit, moins de 100 lignes) ou mode B (Claude explique, Era tape).
4. Vert : test qui passe, `ruff` propre, diff montré.
5. Explication à voix haute, par des questions concrètes, par exemple : pourquoi 950 € continuent-ils pendant une panne ? pourquoi 6 900 € partent-ils en escalade ? pourquoi une réponse tardive doit-elle être ignorée ? Sans réponse claire, on simplifie le code.
6. Un commit par étape, avec le décompte mesuré des tests et la version de Python.

## Plan

Échéances : chantier 1 jeudi 08/10 ; chantier 2 vendredi 09/10 matin ; livrables vendredi après-midi. Estimations : environ 6 h 45 pour le chantier 1 et 4 h 05 pour le chantier 2, **sans marge** pour le débrief et le débogage. Si le temps manque, la phase 3 tombe la première ; les délais, la validation et les preuves ne tombent jamais.

### Phase 0 : cadre (07/10)
- [x] 0.1 `CLAUDE.md` et `ETAT.md`
- [x] Dossier de conception en PDF : `livrable/dossier-de-conception.pdf`
- [ ] 0.2 Questions pour le débrief, validées par Era

### Phase 1 : chantier 1, l'équipe et son orchestration (jeudi 08/10)

| Étape | Quoi | Test rouge d'abord | Preuve | Mode |
|---|---|---|---|---|
| 1.0 ✅ | dépendances sous Python 3.11 ; point de départ mesuré sous 3.11 ; dossiers `agents/`, `a2a/`, `tests/unit/` (sans `conftest.py`) | aucun | 11/56 sous 3.11, `ruff` propre | A |
| 1.1 ✅ | `bornes()` : 8 étapes, 10 s, 2 compléments, 3 s, 1 s, réserve pour produire la fiche | clés présentes, `duree_max_s` ≤ 10 | unitaire vert | A |
| 1.2 ✅ | **une demande de bout en bout** (NOM-01) : agents minimaux, état, Coordination minimale, fiche § 11, trace | test d'acceptance NOM-01 | NOM-01 vert | B (squelettes de `etat.py` et `coordination.py`) |
| 1.3 ✅ | règles : constantes de `regles.py` vérifiées contre la spec § 4 à 10, ajout des 1 500 € ; **tests de frontière** : F1 4 999,99 / 5 000 ; F2 89 / 90 jours ; F3 2 / 3 sinistres ; F4 20 % pile / au-delà ; 1 500 / 1 500,01 ; 10 000 / 10 000,01 | un test par seuil | unitaires verts | A |
| 1.4 | les quatre agents complets : Éligibilité (NOM-02, 03, 04, 10, 11), Pièces et complément (NOM-07, BCL-01), Estimation et plafond (NOM-05), Anti-fraude (F1 à F4, AF-06) avec un partenaire bouchon « indisponible ». Calculs des indicateurs purs ; l'appel réseau sera isolé dans le client (chantier 2) | un test par cas cité | unitaires verts | A |
| 1.5 | mémoire `etat.py` : table des droits, `pieces` seule réécrite, résultats d'agents typés (Pydantic) | écriture hors section refusée ; ligne de trace `agent` + `ecrit` | unitaires verts | B |
| 1.6 | Coordination complète : Éligibilité **puis** Pièces avec court-circuit ; compléments ; même état vu deux fois ; dernière étape réservée à l'issue ; règles du § 10 **avec le mode dégradé du § 9** (sur l'« indisponible » du bouchon) ; **filet de sécurité** (exception imprévue donne `gestionnaire`, « erreur interne », trace partielle) ; **registre des références appelées, à l'échelle du processus, protégé par un verrou** | NOM-07, NOM-02 (2 étapes), NOM-05, BCL-01 ; exception forcée ; avis indisponible à 950 € et à 6 900 € ; avis `faible` au-delà de 10 000 € reste en escalade `gestionnaire` | nominaux 11/11, BCL-01 vert | B |
| 1.7 | `traiter_demande`, `traiter_lot` en concurrence, métriques calculées depuis la trace ; chaque demande tient son propre délai de l'intérieur (un fil d'exécution ne s'arrête pas seul) | une demande lente ne retarde pas les autres ; fiches dans l'ordre ; un résultat tardif ne modifie pas une issue ; latence moyenne et échecs calculés justes | **40/40** | A |
| 1.8 | suppression de `orchestrateur.py` et `agent_generaliste.py` ; **premier échange HTTP construit à la main** (message de 7 champs envoyé au partenaire simulé) | tout reste vert | 40/40, réponse reçue, commit | A |

Le débrief du formateur (jeudi fin de matinée) passe avant l'étape 1.6.

### Phase 2 : chantier 2, la liaison A2A et l'épreuve (vendredi 09/10 matin)

| Étape | Quoi | Test rouge d'abord | Preuve | Mode |
|---|---|---|---|---|
| 2.1 | filtre sortant : modèle Pydantic strict (`extra="forbid"`), 7 champs, objet construit à neuf | 7 clés ; aucune valeur personnelle ; département 69, 2A, 2B, 974 ; espion `httpx.MockTransport` | unitaires verts | B |
| 2.2 | client A2A asynchrone : `message/send`, Bearer, aucune relance ; **délai = min(3 s, temps restant − réserve de la fiche)**, horloge monotone. Formulation retenue : « une annulation asynchrone tient le délai visé, une réserve est gardée pour produire la fiche, et la durée réellement écoulée est vérifiée par des tests d'intégration » | partenaire lent ; réponse envoyée goutte à goutte ; nettoyage après annulation ; résultat tardif ignoré ; 503, 401 ; **HTTP 200 portant une `error` JSON-RPC donne « indisponible »** | unitaires verts, durées mesurées | A |
| 2.3 | validation à 5 niveaux, construite sur des réponses-types tirées du contrat ; réponse modélisée en Pydantic **`strict=True`, `FiniteFloat`, `ge=0, le=1`, `extra="forbid"`** | INV-01 à INV-07 ; tâche non terminée ; `score` valant `true`, `NaN`, `"0.5"`, `1.5` ; `error` dans un HTTP 200 | unitaires verts | B |
| 2.4 | branchement du vrai client à la place du bouchon ; **premier échange par notre filtre, notre client et notre validateur** | PAN-01 ; deux soumissions simultanées de la même référence donnent 1 appel ; avis indisponible au-delà de 10 000 € donne `cellule_fraude` (règle 4 avant règle 5) | AF, INV, PAN verts | B (Coordination) |
| 2.5 | **programme de rejeu** : pour chaque scénario, règle le partenaire, le réinitialise, exécute, compare à `attendu`, enregistre les écarts ; PAN rejoués 5 fois (la plus lente comparée à 10 s) ; totaux 16/7/4/6/1, 11 en mode dégradé, 18 appels ; aucun jeton ni contenu rejeté dans la trace ; appels externes égaux au journal du simulateur. **Relevé de résultats** : commit, version de Python, commande, attendu et obtenu, durées, limites | les totaux | **56/56** et relevé | A |
| 2.6 | démo : partenaire lancé comme service séparé (`docker compose up`), modes changés en direct par `scripts/partner_ctl.py` | aucun | démo répétée | A |

### Phase 3 : la touche personnelle, seulement à 56/56
- [ ] Agent « Lecteur de pièces » : facture PDF, photo JPG, contrat PDF en entrée ; JSON de la spec § 3 en sortie, validé par un schéma ; un LLM lit, il ne décide jamais. Sinon : choix justifié dans le dossier (section 6.2).

### Phase 4 : alignement et livrables (vendredi 09/10 après-midi)
- [x] PDF unique du dossier de conception (07/10), validation formelle du formateur à obtenir
- [ ] Alignement de la conception sur le code : schémas 0, 1, 2 et N1 régénérés (séquence au lieu du parallèle, scripts dans `kaldera_v2`) ; dossier 2.3 et 3.1 (séquence), 3.3 (reprise limitée au processus, journal n° 2) ; chantiers 1 et 2 (tests et pilote du partenaire désormais reçus) ; PDF régénéré. Phrase à garder partout : « contrôles en séquence dans une demande, demandes traitées en concurrence entre elles »
- [ ] Preuve des tests d'acceptance et relevé de résultats dans `livrable/`
- [ ] Journal des ajustements à jour : `conception/journal-ajustements.md`
- [ ] Oral (hors dépôt) : le besoin du client, nos choix, ce qu'on a retiré et pourquoi, démo en direct
- [ ] Journal Obsidian ; copie datée dans le dossier personnel, depuis un commit vérifié et cité

## Risques et replis

| Risque | Repli |
|---|---|
| Retard jeudi | 1.7 et 1.8 passent vendredi 8 h ; la cible 40/40 reste |
| Un test contredit la conception | le test et `interface.md` font foi ; écart consigné au journal |
| Durée de PAN-02 au-delà de 10 s | mesurer d'abord la concurrence du lot et le délai réel de l'appel ; ne pas se contenter de baisser une constante |
| Installation sous Python 3.11 refusée | Docker `python:3.11` (Smart App Control ne s'applique pas au conteneur) |
| Une brique qu'Era ne sait pas expliquer | on la simplifie avant de continuer |

## Questions pour le débrief

1. Le code de départ peut-il être supprimé, du moment que `interface.md` et les tests d'acceptance sont respectés ?
2. Les entrées peuvent être redéfinies (PDF, JPG) : peut-on garder le JSON de la spec § 3 comme format interne, avec un agent de lecture devant ?
3. Un LLM est-il attendu dans les agents, ou des agents en code déterministe suffisent-ils ?
4. Des identifiants Azure seront-ils fournis pour Kimi ?
5. Le code de départ contredit la spec (plafond refusé au lieu d'être appliqué, appel au partenaire sans délai ni filtre, issue `en_attente`) : pièges volontaires ?
6. Qu'est-ce qui est évalué vendredi : les tests verts, le code, l'oral ?
7. Le contrat impose un seul appel par dossier. Une protection valable pendant la vie du processus suffit-elle pour le prototype, ou attendez-vous une protection qui survive à un redémarrage ?

## Verrous

- Aucun pour l'instant.
