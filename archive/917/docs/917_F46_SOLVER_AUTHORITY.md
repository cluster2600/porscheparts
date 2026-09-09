# F46 — autorité des solveurs moteur 2V/4V

Le terme demandé `ICEEngineFoam` ne désigne pas, dans les sources officielles
actuellement identifiées, un exécutable autonome reproductible. Il serait donc
incorrect de renommer un autre calcul et de le présenter comme une preuve
`ICEEngineFoam`.

La comparaison F46 emploie trois voies complémentaires, toutes verrouillées à
une version ou une révision précise :

- **AATE / OpenFOAM ICengines** à la révision
  `c0f75f953d67cd325d28d1300672d14288f22934`, pour le maillage mobile et la
  CFD moteur actuelle ;
- **OpenFOAM 3.0.x `engineFoam`** à la révision
  `221b8ab77307b0ea3831a055bedc2cd77c1417f9`, comme contre-calcul historique
  RANS combustion b-Xi ;
- **Cantera 3.2.0**, pour l'équilibre et la cinétique thermochimique 0D, sans le
  présenter comme une simulation 3D du cycle.

Les deux culasses utilisent la même enveloppe extérieure issue du scan et les
mêmes conditions de comparaison : alésage, course, compression, suralimentation,
carburant et limites. Chaque voie CFD doit terminer trois niveaux de maillage et
publier les historiques de résidus, bilans de masse et d'énergie, champs bruts,
hashes et versions.

Le contrat est vérifié par :

```sh
python3 twins/reference-917-engine/source/validate_engine_solver_authority_f46.py
python3 tests/test_917_engine_solver_authority_f46.py -v
```

Ce contrat choisit et fige les outils. Il ne prouve pas encore leur exécution,
la convergence, la tenue thermique, la résistance mécanique ou l'autorisation
d'impression.

La voie Cantera a depuis été exécutée dans le sous-lot
[`917_CANTERA_2V_4V_CRANK_CYCLE_F46.md`](917_CANTERA_2V_4V_CRANK_CYCLE_F46.md) :
36 cas 0D angle-vilebrequin 2V/4V avec un contre-modèle Wiebe, trois Cd et trois
pas angulaires. Cette exécution ferme une lacune numérique 0D, mais son écart
inter-modèle de pression demeure hors tolérance ; les gates CFD, corrélation et
fabrication restent fermés.
