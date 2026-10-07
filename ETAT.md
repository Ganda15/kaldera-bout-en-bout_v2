# État du développement

## ▶️ Prochaine action

Étape 1.1 : `bornes()` (8 étapes, 10 s, 2 demandes de complément), test rouge d'abord.

## Mesures

| Date | Commande | Résultat |
|---|---|---|
| 07/10/2026 | `C:\Python314\python.exe -m pytest tests/acceptance -q` sur le code de départ du formateur | 11 passed, 45 failed (56 tests) |
| 07/10/2026 | `C:\Python314\python.exe -m ruff check .` | All checks passed! |

## Plan

Échéances annoncées par le formateur : chantier 1 jeudi 08/10, chantier 2 vendredi 09/10 matin, livrables vendredi après-midi.

### Phase 0 : cadre (07/10)
- [x] 0.1 `CLAUDE.md` et `ETAT.md`
- [ ] 0.2 Questions pour le débrief

### Phase 1 : chantier 1, l'équipe et son orchestration (08/10)
Cible : `tests/acceptance/test_equipe_orchestration.py` à 40/40, `ruff` propre.
- [ ] 1.1 `bornes()` (mode A)
- [ ] 1.2 Règles : chaque constante de `regles.py` vérifiée contre la spec § 4 à 8 ; le plafond réduit le montant, il ne refuse pas (mode A)
- [ ] 1.3 Les quatre agents en fonctions pures : Éligibilité, Pièces, Estimation, Anti-fraude (indicateurs F1 à F4 ; appel au partenaire simulé par un bouchon « indisponible ») (mode A)
- [ ] 1.4 Mémoire partagée : `etat.py`, seule la Coordination écrit, trace au nom de l'agent avec `ecrit` (mode B)
- [ ] 1.5 Coordination : routage, bornes, état répété, décision § 10, escalade motivée, fiche § 11 (mode B)
- [ ] 1.6 `traiter_demande`, `traiter_lot` en concurrence, métriques calculées depuis la trace (mode A)

### Phase 2 : chantier 2, la liaison A2A et l'épreuve (09/10 matin)
Cible : 56/56.
- [ ] 2.1 Filtre sortant : exactement les 7 champs du contrat (mode B)
- [ ] 2.2 Client A2A : `message/send`, jeton Bearer, abandon à 3 s, aucune relance (mode A)
- [ ] 2.3 Validation de chaque réponse sur 5 niveaux (mode B)
- [ ] 2.4 Mode dégradé § 9 : 1 500 € ou moins, décision `mode_degrade: true` ; au-delà, `cellule_fraude` (mode B, dans la Coordination)
- [ ] 2.5 Rejeu des 28 scénarios ; chaque ajustement dans `conception/journal-ajustements.md`

### Phase 3 : la touche personnelle, seulement à 56/56
- [ ] Agent « Lecteur de pièces » : entrées définies (facture PDF, photo JPG, contrat PDF), sortie au format de la spec § 3, sortie validée par un schéma ; un LLM lit, il ne décide jamais. Sinon : écrit comme un choix justifié dans le dossier.

### Phase 4 : livrables (09/10 après-midi)
- [ ] PDF unique du dossier de conception, court : les trois vues d'ensemble et une page par décision
- [ ] Preuve des tests d'acceptance (sortie pytest collée)
- [ ] Oral : le besoin du client, nos choix, ce qu'on a retiré et pourquoi
- [ ] Journal Obsidian

## Questions pour le débrief

1. Le code de départ peut-il être supprimé, du moment que `interface.md` et les tests d'acceptance sont respectés ?
2. Les entrées peuvent être redéfinies (PDF, JPG) : peut-on garder le JSON de la spec § 3 comme format interne, avec un agent de lecture devant ?
3. Un LLM est-il attendu dans les agents, ou des agents en code déterministe suffisent-ils ?
4. Des identifiants Azure seront-ils fournis pour Kimi ?
5. Le code de départ contredit la spec (plafond refusé au lieu d'être appliqué, appel au partenaire sans délai ni filtre, issue `en_attente`) : pièges volontaires ?
6. Qu'est-ce qui est évalué vendredi : les tests verts, le code, l'oral ?

## Verrous

- Aucun pour l'instant. Les tests tournent avec `C:\Python314\python.exe` sans `uv`.
