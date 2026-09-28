# Jumeaux documentaires issus du catalogue

Ce lot initialise un jumeau distinct pour chaque composant qualifié et chaque
pièce ou produit muni d'un encombrement déclaré dans les registres du projet.
Une matière absente reste `unresolved` ; elle n'est pas inventée. Le lot est
généré par :

```bash
python3 scripts/generate_catalogue_part_twins.py --write
python3 scripts/generate_catalogue_part_twins.py --check
python3 parts/993-eng-carrier-0001/source/material_tradeoff.py --write
python3 parts/993-eng-carrier-0001/source/material_tradeoff.py --check
python3 scripts/generate_catalogue_part_engineering.py --write
python3 scripts/generate_catalogue_part_engineering.py --check
```

Les fichiers `usd/*.usda` sont des proxys OpenUSD `F1_envelope` en millimètres.
Chaque actif possède aussi un maître paramétrique `cad/*.scad`, limité au même
volume documentaire :

- les quatre roues Fuchs sont des anneaux d'interface construits à partir du
  diamètre nominal, de la largeur nominale et de l'alésage central ;
- le berceau moteur Turbo est un parallélépipède d'encombrement déclaré, pas la
  forme du berceau ;
- treize autres produits Turbo dimensionnés reçoivent le même type d'enveloppe
  de packaging, avec matière non résolue.

[`index.json`](index.json) relie chacun des 18 USD à sa fiche de composant ou de
référence, à sa masse, à son état matière et à ses limites. Le petit extrait
[`evidence/porschefanatics-993-oem-context.json`](evidence/porschefanatics-993-oem-context.json)
confirme l'identité PET du berceau sans copier d'illustration ni déduire de
géométrie depuis le catalogue PorscheFanatics.

Ces actifs ne contiennent volontairement ni collision, ni corps rigide, ni
densité de simulation. Ils ne sont pas SimReady et ne prouvent ni ajustement, ni
résistance, ni aptitude à la fabrication. Les roues et le berceau restent
bloqués pour toute libération fonctionnelle sans géométrie d'interface complète,
tolérances et revue d'ingénierie professionnelle.

[`engineering-f0.json`](engineering-f0.json) constitue la première passe
d'ingénierie exécutable. Pour chaque pièce, il conserve les entrées connues,
calcule seulement des grandeurs de présélection traçables, décrit les mesures à
acquérir, conserve des hypothèses de système matière non qualifiées, compare les
routes usinées/additives et route les domaines de calcul. Toutes les simulations
restent bloquées tant que la géométrie fonctionnelle, la matière, les charges et
les critères d'acceptation sont incomplets.

Le premier calcul mathématique reproductible est consigné dans
[`engine-carrier-material-screening-f1.json`](engine-carrier-material-screening-f1.json).
Il compare acier et Ti-6Al-4V sur un tube rectangulaire générique : à géométrie
identique, le titane est environ 44 % plus léger mais 1,84 fois plus souple ; à
raideur égale, la section doit croître d'environ 16,5 % et le gain de masse
théorique tombe à environ 23 %. Ce calcul dépriorise le titane pour le programme
conceptuel courant, mais ne sélectionne aucune nuance ou route fonctionnelle :
la géométrie réelle du berceau n'est pas utilisée et le crédit composant reste
explicitement nul.

PhysicsNeMo n'est pas le solveur de référence : ses modèles restent des
candidats futurs pour les maillages CAE non structurés, après production de cas
CalculiX convergés et corrélation à des essais physiques. Aucun entraînement
PhysicsNeMo n'est autorisé sur les proxys F1.

La découverte effectuée sur le dépôt NVIDIA vivant, puis revérifiée sur le tag
épinglé `v2.2.0`, est consignée dans
[`physicsnemo-structural-f0.json`](physicsnemo-structural-f0.json). Le menu reste
ouvert entre `GeoTransolver`, `MeshGraphNet`, `Transolver` et `FIGConvUNet`, et
sépare explicitement le modèle du datapipe. Le premier patron retenu pour le
berceau est `GeoTransolver` avec un fichier VTU par exécution CalculiX ; il reste
bloqué tant qu'aucun cas EF convergé et aucune corrélation physique n'existent.
