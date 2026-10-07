# Kaldera V2 : équipe d'agents qui traite les demandes de remboursement habitation, et qui ne décide jamais par un LLM

> ## Début de session, dans cet ordre
>
> 1. Lire `ETAT.md` (racine du dépôt).
> 2. Vérifier le réel : `git log --oneline -5`, `git status`, la suite de tests.
> 3. Annoncer à Era en 3 lignes : où on s'est arrêté, la prochaine action, les verrous.
>
> ## Fin de session
>
> 1. `superpowers:verification-before-completion` avant tout « c'est fini » : commande lancée, sortie collée.
> 2. `ETAT.md` réécrit : prochaine action en tête, chiffres mesurés du jour, manques.
> 3. Journal Obsidian `Projets/Kaldera-v2/` quand une étape est terminée.

Les règles de travail et les pièges de la machine sont dans `C:\Users\kanda\.claude\CLAUDE.md`. Ce fichier ne contient que ce qui reste vrai pour ce dépôt ; l'état du jour vit dans `ETAT.md`.

## 1. Identité

- **Brief** : « Kaldera, développer une équipe d'agents de bout en bout » (Simplon × Wild Code School, RNCP 37827), individuel.
- **Dépôt** : `Ganda15/kaldera-bout-en-bout_v2` (fork public du dépôt du formateur), dossier local `C:\Users\kanda\Desktop\Kaldera\kaldera-bout-en-bout_v2`.
- **Remote `upstream`** : dépôt du formateur, en lecture seule (push désactivé). Ne jamais le modifier.
- **Conception** : `conception/` (copie du dépôt `Ganda15/kaldera-v2-conception`). Le code suit la conception ; un écart se consigne dans `conception/journal-ajustements.md`.
- **Documents qui font foi** : `docs/specs_metier.md`, `docs/interface.md`, `external_agent/contrat.md`, `eval/scenarios.jsonl`, `tests/acceptance/`.

## 2. Non-négociables (les six exigences du brief)

- **[N1]** Toute demande finit par une décision ou une escalade motivée. Vérifié par `test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee`.
- **[N2]** Une section métier n'est écrite que par un agent, et un agent n'écrit qu'une section. Vérifié par `verifier_roles` (tests nominal et antifraude).
- **[N3]** Seuls les 7 champs du contrat partent chez le partenaire. Vérifié par `test_echange_antifraude_respecte_le_contrat_et_ne_transmet_que_les_donnees_autorisees`.
- **[N4]** Une réponse non conforme du partenaire est écartée, jamais propagée. Vérifié par `test_reponse_invalide_du_partenaire_est_rejetee_et_non_propagee`.
- **[N5]** Partenaire indisponible : le mode dégradé du § 9 s'applique. Vérifié par `test_partenaire_en_panne_le_mode_degrade_s_applique_sans_bloquer_le_reste`.
- **[N6]** Aucune boucle infinie, métriques par agent visibles, chaque ajustement consigné. Vérifié par `test_scenario_piege_a_boucle_s_arrete_dans_les_bornes`, le test de panne et `conception/journal-ajustements.md`.

## 3. Ce qu'on ne fait jamais

- **Jamais** un LLM dans une décision : la Coordination et les quatre agents sont du code déterministe. Un LLM ne peut servir qu'à lire un document (phase 3), et sa sortie est validée par un schéma.
- **Jamais** LangGraph ni autre framework d'agents avant que les 56 tests soient verts (décision d'Era du 07/10/2026).
- **Jamais** modifier `tests/acceptance/`, `docs/`, `eval/`, `external_agent/` : ce sont les documents du formateur.
- **Jamais** un fichier ouvert sans `encoding="utf-8"` : sous Windows, les accents se corrompent.
- **Jamais** un test rouge supprimé ou affaibli pour obtenir du vert.
- **Jamais** de ligne « Co-Authored-By: Claude » dans un commit.
- **Jamais** de tiret cadratin ni de tournure qui « sonne IA » dans un fichier, une note ou un commit.

## 4. Mode de travail (choix d'Era du 07/10/2026)

- **Mode B, le code de la présentation et de la démo** : Claude donne le code dans le chat avec l'explication ligne par ligne ; **Era le tape lui-même**. Fichiers concernés : `src/kaldera/etat.py`, `src/kaldera/coordination.py`, `src/kaldera/a2a/filtre.py`, `src/kaldera/a2a/validation.py`.
- **Mode A, le reste** : Claude écrit par petites étapes (moins de 100 lignes), montre le diff, explique ligne par ligne ; Era répond à deux questions à voix haute avant l'étape suivante.
- Chaque étape : test rouge d'abord, puis le code, puis `ruff`, puis le diff montré.

## 5. Si ça ne marche pas

- **Un test échoue** : `superpowers:systematic-debugging`, enquêter avant de corriger.
- **Doute sur une règle métier** : citer la ligne de `docs/specs_metier.md` ; si elle ne tranche pas, `INCONNU` et une question à Era.
- **La conception et un test se contredisent** : le test et `interface.md` font foi ; consigner l'écart dans `conception/journal-ajustements.md`.
- **Un binaire refusé par Smart App Control** : Docker ou Python 3.11 (`py -V:Astral/CPython3.11.15`). Jamais toucher à un réglage de sécurité.

## 6. Stack et dossiers

- Python (tests lancés avec `C:\Python314\python.exe`, le projet vise 3.11), httpx, pydantic, FastAPI pour le partenaire simulé. Sans LangGraph.
- `src/kaldera/` : l'équipe (Coordination, agents, état de la demande, client A2A).
- `external_agent/` : partenaire anti-fraude simulé, fourni. `scripts/partner_ctl.py` : son pilote, fourni.
- `tests/acceptance/` : suite d'acceptance, fournie. `tests/unit/` : nos tests unitaires.
- `conception/` : dossier de conception et schémas.

## 7. Commandes (PowerShell 5.1 : le `cd` d'abord, un bloc par commande)

```powershell
cd C:\Users\kanda\Desktop\Kaldera\kaldera-bout-en-bout_v2
```
```powershell
C:\Python314\python.exe -m pytest -q
```
```powershell
C:\Python314\python.exe -m ruff check .
```
```powershell
C:\Python314\python.exe -m external_agent --port 8100
```

## 8. Skills de ce projet

| Moment | Skill |
|---|---|
| Chaque étape de code | `test-driven-development` |
| Bornes, garde-fous, évaluation des agents | `agent-standard` |
| Un bug | `superpowers:systematic-debugging` |
| Avant de dire « fait » | `superpowers:verification-before-completion` |
| Oral, présentation | `coach-soutenance` (oral hors du dépôt, dans `C:\Users\kanda\Desktop\Kaldera\kaldera_v2-oral\`) |
