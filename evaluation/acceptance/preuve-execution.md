# Preuve d'exécution des tests d'acceptance

Fichier généré par `outils/preuve_acceptance.py`. Ne pas le modifier à la main. `python -m outils.preuve_acceptance --verifier` relance la suite et compare les noms et statuts des tests, puis contrôle la provenance (commit existant, code testé inchangé depuis, totaux) ; les durées ne sont pas comparées, elles varient d'une exécution à l'autre.

- date : 2026-10-08 21:04
- commit testé : `f45a9a8` ; arbre de travail : propre (le code testé est exactement celui du commit)
- Python 3.11.15 ; système : Windows 10.0.26300
- commande : `python -m pytest tests/acceptance -q -p no:cacheprovider --junitxml=<rapport.xml>` ; code de retour de pytest : 0
- durée de la suite : 10.4 s (les 56 tests ensemble ; ce n'est pas la durée d'une demande)
- intégration continue : exécution https://github.com/Ganda15/kaldera-bout-en-bout_v2/actions/runs/37828970183 sur le commit `f45a9a8`, conclusion success

**Verdict : tous les tests d'acceptance passent**

56 réussi(s), 0 échoué(s), 0 ignoré(s), sur 56 tests ; 56 test(s) exécuté(s) pour 56 collecté(s).

| Test | Statut | Durée (s) |
|---|---|---|
| test_collaboration_a2a::test_echange_antifraude_respecte_le_contrat_et_ne_transmet_que_les_donnees_autorisees[AF-01] | réussi | 0.362 |
| test_collaboration_a2a::test_echange_antifraude_respecte_le_contrat_et_ne_transmet_que_les_donnees_autorisees[AF-02] | réussi | 0.09 |
| test_collaboration_a2a::test_echange_antifraude_respecte_le_contrat_et_ne_transmet_que_les_donnees_autorisees[AF-03] | réussi | 0.092 |
| test_collaboration_a2a::test_echange_antifraude_respecte_le_contrat_et_ne_transmet_que_les_donnees_autorisees[AF-04] | réussi | 0.094 |
| test_collaboration_a2a::test_echange_antifraude_respecte_le_contrat_et_ne_transmet_que_les_donnees_autorisees[AF-05] | réussi | 0.077 |
| test_collaboration_a2a::test_echange_antifraude_respecte_le_contrat_et_ne_transmet_que_les_donnees_autorisees[AF-06] | réussi | 0.14 |
| test_collaboration_a2a::test_echange_antifraude_respecte_le_contrat_et_ne_transmet_que_les_donnees_autorisees[AF-07] | réussi | 0.091 |
| test_collaboration_a2a::test_reponse_invalide_du_partenaire_est_rejetee_et_non_propagee[INV-01] | réussi | 0.076 |
| test_collaboration_a2a::test_reponse_invalide_du_partenaire_est_rejetee_et_non_propagee[INV-02] | réussi | 0.106 |
| test_collaboration_a2a::test_reponse_invalide_du_partenaire_est_rejetee_et_non_propagee[INV-03] | réussi | 0.092 |
| test_collaboration_a2a::test_reponse_invalide_du_partenaire_est_rejetee_et_non_propagee[INV-04] | réussi | 0.081 |
| test_collaboration_a2a::test_reponse_invalide_du_partenaire_est_rejetee_et_non_propagee[INV-05] | réussi | 0.104 |
| test_collaboration_a2a::test_reponse_invalide_du_partenaire_est_rejetee_et_non_propagee[INV-06] | réussi | 0.097 |
| test_collaboration_a2a::test_reponse_invalide_du_partenaire_est_rejetee_et_non_propagee[INV-07] | réussi | 0.104 |
| test_collaboration_a2a::test_partenaire_en_panne_le_mode_degrade_s_applique_sans_bloquer_le_reste[PAN-01] | réussi | 0.035 |
| test_collaboration_a2a::test_partenaire_en_panne_le_mode_degrade_s_applique_sans_bloquer_le_reste[PAN-02] | réussi | 3.03 |
| test_equipe_orchestration::test_scenario_nominal_produit_la_decision_attendue[NOM-01] | réussi | 0.005 |
| test_equipe_orchestration::test_scenario_nominal_produit_la_decision_attendue[NOM-02] | réussi | 0.006 |
| test_equipe_orchestration::test_scenario_nominal_produit_la_decision_attendue[NOM-03] | réussi | 0.005 |
| test_equipe_orchestration::test_scenario_nominal_produit_la_decision_attendue[NOM-04] | réussi | 0.006 |
| test_equipe_orchestration::test_scenario_nominal_produit_la_decision_attendue[NOM-05] | réussi | 0.004 |
| test_equipe_orchestration::test_scenario_nominal_produit_la_decision_attendue[NOM-06] | réussi | 0.004 |
| test_equipe_orchestration::test_scenario_nominal_produit_la_decision_attendue[NOM-07] | réussi | 0.003 |
| test_equipe_orchestration::test_scenario_nominal_produit_la_decision_attendue[NOM-08] | réussi | 0.005 |
| test_equipe_orchestration::test_scenario_nominal_produit_la_decision_attendue[NOM-09] | réussi | 0.005 |
| test_equipe_orchestration::test_scenario_nominal_produit_la_decision_attendue[NOM-10] | réussi | 0.005 |
| test_equipe_orchestration::test_scenario_nominal_produit_la_decision_attendue[NOM-11] | réussi | 0.006 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[NOM-01] | réussi | 0.006 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[NOM-02] | réussi | 0.006 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[NOM-03] | réussi | 0.005 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[NOM-04] | réussi | 0.006 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[NOM-05] | réussi | 0.008 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[NOM-06] | réussi | 0.006 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[NOM-07] | réussi | 0.008 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[NOM-08] | réussi | 0.006 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[NOM-09] | réussi | 0.004 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[NOM-10] | réussi | 0.006 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[NOM-11] | réussi | 0.004 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[AF-01] | réussi | 0.059 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[AF-02] | réussi | 0.077 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[AF-03] | réussi | 0.107 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[AF-04] | réussi | 0.095 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[AF-05] | réussi | 0.09 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[AF-06] | réussi | 0.078 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[AF-07] | réussi | 0.099 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[INV-01] | réussi | 0.084 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[INV-02] | réussi | 0.11 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[INV-03] | réussi | 0.078 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[INV-04] | réussi | 0.077 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[INV-05] | réussi | 0.092 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[INV-06] | réussi | 0.092 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[INV-07] | réussi | 0.093 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[PAN-01] | réussi | 0.034 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[PAN-02] | réussi | 3.052 |
| test_equipe_orchestration::test_toute_demande_aboutit_a_une_decision_ou_une_escalade_motivee[BCL-01] | réussi | 0.005 |
| test_equipe_orchestration::test_scenario_piege_a_boucle_s_arrete_dans_les_bornes | réussi | 0.007 |
