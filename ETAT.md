# État du développement

## ▶️ Prochaine action

Étape 1.0 : dossiers vides `src/kaldera/agents/`, `src/kaldera/a2a/`, `tests/unit/` ; `ruff` propre, toujours 11/56.

## Mesures

| Date | Commande | Résultat |
|---|---|---|
| 07/10/2026 | `C:\Python314\python.exe -m pytest tests/acceptance -q` sur le code de départ du formateur | 11 passed, 45 failed (56 tests) |
| 07/10/2026 | `C:\Python314\python.exe -m ruff check .` | All checks passed! |

## Règles de chaque étape

1. Avant : ce qu'il faut lire, et pourquoi l'étape existe.
2. Test rouge d'abord, vu en échec.
3. Code : mode A (Claude écrit, moins de 100 lignes) ou mode B (Claude explique, Era tape).
4. Vert : test qui passe, `ruff` propre, diff montré.
5. Explication à voix haute : deux questions, en ses propres mots ; sinon, on simplifie le code.
6. Un commit par étape, avec le décompte des tests.

Cibles : 40/40 sur `test_equipe_orchestration.py` jeudi 08/10 au soir ; 56/56 vendredi 09/10 à midi.

## Plan

### Phase 0 : cadre (07/10)
- [x] 0.1 `CLAUDE.md` et `ETAT.md`
- [x] Dossier de conception en PDF : `livrable/dossier-de-conception.pdf`
- [ ] 0.2 Questions pour le débrief, validées par Era

### Phase 1 : chantier 1, l'équipe et son orchestration (jeudi 08/10)

| Étape | Quoi | Test rouge d'abord | Preuve | Mode |
|---|---|---|---|---|
| 1.0 | dossiers vides `agents/`, `a2a/`, `tests/unit/` (sans `conftest.py`) | aucun | `ruff` propre, 11/56 | A |
| 1.1 | `bornes()` : 8 étapes, 10 s, 2 compléments, 3 s, 1 s | clés présentes, `duree_max_s` ≤ 10 | unitaire vert | A |
| 1.2 | constantes de `regles.py` vérifiées contre la spec § 4 à 9, ajout des 1 500 € | un test par chiffre | unitaires verts | A |
| 1.3a | agent Éligibilité, conditions E1 à E5 | NOM-02, 03, 04, 10, 11 | unitaires verts | A |
| 1.3b | agent Pièces et demande de complément | NOM-07, BCL-01 | unitaires verts | A |
| 1.3c | agent Estimation, franchise et plafond | NOM-05 : 4 200 − 300 = 3 900, plafonné à 3 000 | unitaires verts | A |
| 1.3d | agent Anti-fraude, F1 à F4, partenaire bouchon « indisponible » | un test par indicateur, AF-06 | unitaires verts | A |
| 1.4 | mémoire `etat.py` : sections, table des droits, trace ; résultats d'agents typés (Pydantic) | écriture refusée, `pieces` réécrite, ligne de trace | unitaires verts | B |
| 1.5 | Coordination : Éligibilité puis Pièces **en séquence, avec court-circuit** ; compléments ; règles du § 10 ; bornes ; **filet de sécurité** (toute exception imprévue donne une escalade `gestionnaire` « erreur interne » avec la trace partielle) | NOM-07, NOM-02, NOM-05, BCL-01 ; exception forcée | nominaux 11/11, BCL-01 vert | B |
| 1.6 | `traiter_demande`, `traiter_lot` en concurrence, métriques depuis la trace | lot de 3 | **40/40** | A |
| 1.7 | suppression de `orchestrateur.py` et `agent_generaliste.py`, journal | tout reste vert | 40/40, commit | A |

Le débrief du formateur (jeudi fin de matinée) passe avant l'étape 1.5.

### Phase 2 : chantier 2, la liaison A2A et l'épreuve (vendredi 09/10 matin)

| Étape | Quoi | Test rouge d'abord | Preuve | Mode |
|---|---|---|---|---|
| 2.1 | filtre sortant : modèle Pydantic `extra="forbid"`, 7 champs, construit à neuf | 7 clés, aucune valeur personnelle ; département 69, 2A, 2B, 974 ; espion `httpx.MockTransport` | unitaires verts | B |
| 2.2 | client A2A : `message/send`, Bearer, délai = min(3 s, temps restant), aucune relance | partenaire lent coupé à 3 s, 1 appel ; 503, 401 ; **HTTP 200 portant une `error` JSON-RPC donne « indisponible »** | unitaires verts | A |
| 2.3 | validation à 5 niveaux ; réponse modélisée en Pydantic `extra="forbid"` | INV-01 à INV-07 ; tâche non terminée ; `error` dans un HTTP 200 | unitaires verts | B |
| 2.4 | branchement du vrai client ; mode dégradé § 9 dans la Coordination | PAN-01 ; **avis indisponible et plus de 10 000 € donne `cellule_fraude` (règle 4 avant règle 5)** | AF, INV, PAN verts | B |
| 2.5 | rejeu des 28 scénarios, PAN rejoués 5 fois (la plus lente comparée à 10 s), totaux attendus, journal des ajustements | 16/7/4/6/1, 11 en mode dégradé, 18 appels | **56/56** et rapport | A |
| 2.6 | démo : partenaire lancé comme service séparé (`docker compose up`), modes changés en direct par `scripts/partner_ctl.py`, rejeu par `kaldera.cli` | aucun | démo répétée | A |

### Phase 3 : la touche personnelle, seulement à 56/56
- [ ] Agent « Lecteur de pièces » : facture PDF, photo JPG, contrat PDF en entrée ; JSON de la spec § 3 en sortie, validé par un schéma ; un LLM lit, il ne décide jamais. Sinon : choix justifié dans le dossier (section 6.2).

### Phase 4 : livrables (vendredi 09/10 après-midi)
- [x] PDF unique du dossier de conception (07/10) : `livrable/dossier-de-conception.pdf`, 20 pages, 6 schémas, table des matières vérifiée ; validation formelle du formateur à obtenir
- [ ] Preuve des tests d'acceptance (sortie pytest collée dans `livrable/`)
- [ ] Journal des ajustements : `conception/journal-ajustements.md`
- [ ] Oral (hors dépôt) : le besoin du client, nos choix, ce qu'on a retiré et pourquoi, démo en direct
- [ ] Journal Obsidian

## Risques et replis

| Risque | Repli |
|---|---|
| Retard jeudi | 1.6 et 1.7 passent vendredi 8 h ; la cible 40/40 reste |
| Un test contredit la conception | le test et `interface.md` font foi ; écart consigné au journal |
| PAN-02 au-delà de 10 s | vérifier d'abord la concurrence du lot, puis `duree_max_s` à 8 s (consigné) |
| Smart App Control | Docker, ou `py -V:Astral/CPython3.11.15` |
| Une brique qu'Era ne sait pas expliquer | on la simplifie avant de continuer |

## Questions pour le débrief

1. Le code de départ peut-il être supprimé, du moment que `interface.md` et les tests d'acceptance sont respectés ?
2. Les entrées peuvent être redéfinies (PDF, JPG) : peut-on garder le JSON de la spec § 3 comme format interne, avec un agent de lecture devant ?
3. Un LLM est-il attendu dans les agents, ou des agents en code déterministe suffisent-ils ?
4. Des identifiants Azure seront-ils fournis pour Kimi ?
5. Le code de départ contredit la spec (plafond refusé au lieu d'être appliqué, appel au partenaire sans délai ni filtre, issue `en_attente`) : pièges volontaires ?
6. Qu'est-ce qui est évalué vendredi : les tests verts, le code, l'oral ?

## Verrous

- Aucun pour l'instant. Les tests tournent avec `C:\Python314\python.exe` sans `uv`.
