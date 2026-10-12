# INC-001 : l'indicateur F4 se déclenche à 20 % pile

| | |
|---|---|
| Statut | résolu |
| Gravité | moyenne : un dossier honnête peut déclencher un appel inutile au partenaire, puis une escalade |
| Détecté le | 07/10/2026, étape 1.3, par un test de frontière (`tests/unit/test_regles.py`) |
| Corrigé par | commit `1882c91` (07/10/2026) |
| Documenté par | ce fichier, livré par pull request (07/10/2026, après la correction) |
| Exigence touchée | spécification § 7, indicateur F4 ; exigence [E3] (aucun appel au partenaire sans indicateur réel) |

## 1. Le symptôme

La spécification (§ 7) dit : F4 est présent quand le montant déclaré est « supérieur de **plus de 20 %** au montant justifié ». Un écart de 20 % exactement ne doit donc pas déclencher F4.

Pour un montant justifié de 1 234,50 € et un montant déclaré de 1 481,40 € (soit +20 % exactement), le code calculait F4 = vrai. Pour 1 250,00 € et 1 500,00 € (aussi +20 % exactement), il calculait F4 = faux. Le défaut dépendait donc des montants : il était **intermittent**.

**Conséquence si le défaut était resté** : un dossier sans autre indicateur aurait sollicité le partenaire anti-fraude sans raison (l'unique appel autorisé par dossier), et, en cas de panne au-delà de 1 500 €, aurait été escaladé vers la cellule anti-fraude.

## 2. Comment il a été détecté

Aucun des 28 scénarios du client ne se situe exactement sur le seuil de 20 % : les tests d'acceptance ne pouvaient pas le voir. Il a été trouvé par un **test de frontière**, écrit avant le code à l'étape 1.3 : chaque seuil est testé juste en dessous et juste au-dessus. Premier passage : 6 tests en échec, dont `test_f4_un_ecart_de_20_pour_cent_pile_ne_declenche_pas[1234.5-1481.4]`.

## 3. Reproduction en environnement de développement

Le code d'avant la correction (commit `1882c91~1`) a été extrait dans un dossier temporaire (`git worktree`), sans toucher au dossier de travail, puis exécuté sur les mêmes montants (Python 3.11.15, `.venv`).

| Justifié | Déclaré | Cas | Avant la correction | Après la correction |
|---|---|---|---|---|
| 1 234,50 | 1 481,40 | +20 % pile | **F4 = vrai** (faux positif) | F4 = faux |
| 1 250,00 | 1 500,00 | +20 % pile | F4 = faux | F4 = faux |
| 1 234,50 | 1 481,41 | un centime au-delà | F4 = vrai | F4 = vrai |

Pour reproduire depuis la racine du dépôt (PowerShell) :

```powershell
git worktree add ..\repro-inc001 1882c91~1
$env:PYTHONPATH = "..\repro-inc001\src"
.venv\Scripts\python.exe -c "from kaldera.agents.antifraude import evaluer_risque as e; print(e(reference='R', type_sinistre='incendie', date_survenance='2026-08-14', montant_declare=1481.40, date_souscription='2024-01-15', sinistres_12_mois=0, code_postal='69003', montant_justifie=1234.50).indicateurs)"
Remove-Item Env:PYTHONPATH
git worktree remove --force ..\repro-inc001
```

Résultat attendu sur l'ancien code : `['F4']`. Sur le code corrigé, la même commande sans `PYTHONPATH` donne `[]`.

## 4. La cause

L'ancien code comparait des nombres à virgule flottante :

```python
if montant_declare > montant_justifie * (1 + ECART_DECLARATION_MAX):
```

Un ordinateur stocke les décimaux de façon approchée, en binaire. Mesuré : `1234.5 * 1.2` vaut `1481.3999999999999`, un peu **moins** que 1 481,40. La comparaison « 1 481,40 > 1 481,3999999999999 » est donc vraie, alors que les deux montants sont égaux au centime. Pour 1 250 × 1,2, le produit tombe juste (1 500,0) : d'où le caractère intermittent.

## 5. La correction, étape par étape

1. **Test d'abord** : quatre cas « 20 % pile » qui ne doivent pas déclencher F4 et deux cas « un centime au-delà » qui doivent le déclencher (`tests/unit/test_regles.py`, `test_f4_*`). Ils échouaient sur un cas avant la correction.
2. **Calcul en centimes entiers** dans `src/kaldera/regles.py` : les montants sont convertis en centimes (`round(montant * 100)`), et « déclaré > justifié × 1,20 » devient « déclaré × 100 > justifié × 120 », en nombres entiers. Plus aucune approximation n'est possible.

   ```python
   def ecart_declaration_depasse(montant_declare: float, montant_justifie: float) -> bool:
       pourcentage = round(ECART_DECLARATION_MAX * 100)
       return _centimes(montant_declare) * 100 > _centimes(montant_justifie) * (100 + pourcentage)
   ```

3. **Branchement** : l'agent Anti-fraude (`src/kaldera/agents/antifraude.py`) appelle désormais `ecart_declaration_depasse` au lieu de comparer lui-même.
4. **Même méthode pour les autres seuils monétaires** de décision : `depasse_seuil_delegation` (strictement au-delà de 10 000 €) et `continue_en_mode_degrade` (1 500 € inclus) comparent aussi en centimes, avec leurs tests de frontière.
5. **Vérification** : 19 tests de règles verts, 23 tests unitaires au total à cette étape, tests d'acceptance inchangés (38/56 à cette étape), `ruff` propre. Aujourd'hui, la chaîne d'intégration continue rejoue ces tests à chaque push.

## 6. Ce qui empêche le retour du défaut

- Les tests de frontière F4 restent dans la suite et dans la chaîne d'intégration continue (`.github/workflows/tests.yml`) : toute régression fait échouer la chaîne.
- Règle retenue pour la suite du projet : **tout seuil monétaire se compare en centimes entiers**, dans `regles.py`, jamais directement en nombres à virgule dans un agent.

## 7. Ce qui n'a pas été fait selon la procédure

La correction a été poussée directement sur `main` (commit `1882c91`), avant la mise en place de l'outil de suivi : les tickets (issues) étaient désactivés sur le fork. La procédure de débogage est donc documentée **après coup**, ici et dans la pull request qui livre ce fichier. À partir de cet incident, toute correction passe par une branche, un ticket et une pull request.
