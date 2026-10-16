# Relecture parallèle des admissions exactes

`build_cached_v6.py` conserve le constructeur privé v5, les autorités déclarées
943/5047 et les six contrôles d’`admissions_v3.py`. Seules les relectures des
unités planaires passent dans un pool de quatre processus, avec huit futures
au maximum. Les résultats et refus sont restitués dans leur ordre d’origine.
Aucun générateur, recette ou ancien fichier de preuve n’est modifié.

Le parent capture son identité de runtime avant le pool ; chaque worker exige
la même identité à son initialisation. Après fermeture, le parent la recalcule.
Les deux empreintes doivent être identiques et sont exigées au réemploi du
dossier. Ce contrôle ne calcule aucun hash de runtime par unité. La fermeture
attend les tâches déjà lancées et annule les tâches encore en attente ; elle
ne promet pas d’interrompre immédiatement un calcul rationnel en cours.

## Trois résultats à distinguer

- Le benchmark historique avec la classe **814** a traité la peau de
  5 876 sommets en **324,729 s**. Son reçu reste historique.
- L’[essai isolé de réemploi des aires](combinatorial-evidence/ring-area-reuse-experiment-001.json)
  a mesuré **238,350 s**, avec WKB, reçu complet et statistiques identiques.
  La concurrence de la machine n’était pas contrôlée : ce rapport ne garantit
  aucun gain de durée. Sa mention `adopted=false` décrit l’état de cet essai.
- Les nouveaux workers v6 utilisent la copie éditable
  `incremental_combinatorial_interfaces_area.py`, SHA
  `2230847e5862b3d6668a900c2774ebb82cb3f12555486747fb06dfe8d5a90341`.
  Elle ne change qu’une expression de 814 : `ring_area=sum(areas)` réutilise
  les aires rationnelles déjà calculées avant le réordonnancement des cycles.
  Le hook et le reçu d’exécution déclarent cette implémentation séparément ;
  ils ne réétiquettent aucune autorité ni aucun résultat antérieur.

La réutilisation optionnelle est limitée aux **quatre résultats réels déjà
vérifiés des régions 003/009**, produits par 814. Leur reçu, plan, runtime,
checkpoints producteurs, données et résultats doivent correspondre exactement.
Un écart refuse le réemploi ; il ne déclenche pas une reconstruction silencieuse.
Il ne s’agit pas d’un cache général. Les tests vérifient ces quatre résultats
sans les soumettre à un worker.

## Commandes et preuves

La CLI conserve les arguments de v5 et ajoute seulement
`--proven-unit-replays CHEMIN_ASSESSMENT`. Ce chemin optionnel désigne le reçu
historique exact SHA `62082815b2e78ee66c11f91818f2f63c46b180f75664ede6f7ef602f9a57a432`,
accompagné de `frozen-plan.json` et `runtime-before.json`. Ces trois fichiers
bruts restent nécessaires pour utiliser ces quatre résultats historiques.
Sans cette option, les unités sont relues par les nouveaux workers.

Le nouveau dossier contient `exact-admission-replays.json`, lié aux six reçus
et au checkpoint. Le wrapper conserve et revérifie ce lien après la copie
effectuée par le CORE. `--reuse-support-stage` exige un dossier v6 complet ;
un ancien dossier v5 et une combinaison avec `--proven-unit-replays` sont refusés.

Depuis la racine du dépôt, les témoins logiciels ciblés se rejouent avec le
runtime PySLM épinglé :

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python -B -m unittest discover -s tests -p test_carrier_parallel_exact_admissions.py -v
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 work/part-workflow/runtimes/pyslm-coverage-011/env/bin/python -B -m unittest discover -s tests -p test_carrier_cached_build_v6.py -v
```

Le [reçu d’implémentation](combinatorial-evidence/parallel-admissions-implementation-002.json)
conserve les empreintes et les journaux : **7 tests du helper + 8 du driver
passent**, dont 21 petites unités réellement relues jusqu’aux six reçus d’un
témoin synthétique. La régression antérieure de 34 tests des drivers est
identifiée comme antérieure au garde runtime final. Les deux JSON associés
à cette notice sont des copies exactes des reçus conservés, sans réécriture.

Cette vérification concerne le logiciel. Aucune admission complète des vrais
supports, aucune nouvelle génération et aucun benchmark coûteux n’ont été
exécutés par le nouveau driver pour ce checkpoint.
