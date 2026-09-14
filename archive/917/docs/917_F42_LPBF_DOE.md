# F42 — DOE LPBF BLT-S310 / AlSi10Mg pour AdditiveFOAM

## Verdict

F42 fournit une matrice de calcul exécutable, traçable et fail-closed. Elle ne
constitue ni une carte fournisseur qualifiée, ni un fichier machine, ni une
autorisation d'imprimer la culasse ou de démarrer un moteur.

![Matrice DOE F42](../twins/reference-917-engine/evidence/f42-lpbf-doe/917-head-lpbf-doe-f42.png)

La matrice contient les `27` combinaisons d'un plan factoriel complet :

| Paramètre | Niveaux |
| --- | --- |
| puissance | 360, 380, 400 W |
| vitesse | 1 200, 1 300, 1 500 mm/s |
| hatch | 0,13, 0,15, 0,16 mm |
| couche | 0,050 mm, fixe |

L'énergie volumique indicative `P/(v h t)` va de `30,000` à
`51,282 J/mm³`. Elle sert à ordonner le plan d'expériences, pas à prédire seule
la densité, la porosité ou la tenue à chaud.

## Machine et provenance du procédé

La machine de référence est une BLT-S310 monolaser : volume annoncé
`250 × 250 × 400 mm`, laser fibre `500 W`, couches `20–100 µm`, vitesse de
balayage maximale `7 m/s`, préchauffage annoncé de la température ambiante
jusqu'à `200 °C`, argon ou azote et oxygène au plus `100 ppm`.

La fenêtre AlSi10Mg provient d'une étude primaire sur BLT-S310. Un second essai
sur la même machine publie le témoin `380 W / 1 300 mm/s / 0,15 mm / 50 µm`,
rotation `67°`, puis détente `300 °C / 2 h` avant retrait des supports. Ces
publications portent sur leurs éprouvettes et blocs, pas sur notre culasse.

Le spot `80 µm` est une **hypothèse de modèle** issue d'une publication BLT-S310
distincte ; il n'est pas publié pour le témoin à `380 W`. La température
initiale `293,15 K` est également une hypothèse ambiante, car « sans
préchauffage » ne donne pas la température réelle de plaque. Absorptivité,
profil de faisceau, distribution granulométrique et convection gaz doivent
être mesurés ou fournis par BLT avant corrélation.

Sources primaires ou constructeur :

- [catalogue constructeur BLT](https://www.xa-blt.com/en/wp-content/uploads/2023/04/BLT-Engine-Solutions-2023.4.13.pdf) ;
- [fenêtre AlSi10Mg sur BLT-S310](https://nottingham-repository.worktribe.com/index.php/OutputFile/4698952) ;
- [témoin grand bloc 380 W sur BLT-S310](https://pmc.ncbi.nlm.nih.gov/articles/PMC10482850/) ;
- [étude distincte indiquant un spot de 80 µm](https://www.sciencedirect.com/science/article/pii/S0924013624001444) ;
- [code ORNL AdditiveFOAM](https://github.com/ORNL/AdditiveFOAM).

## Enveloppe, orientation, supports et tranchage

F42 reprend sans la surclasser la preuve géométrique F41. L'orientation
`scan_y_down` donne une enveloppe conditionnelle de
`119,112 × 82,000 × 206,089 mm`. Elle tient nominalement dans la BLT-S310 avec
des marges de `130,888 × 168,000 × 193,911 mm`, **avant** plaque, supports,
marges de bord, positionnement et contrôle de collision recoater.

À `50 µm`, `ceil(206,088844 / 0,05) = 4 122` couches. Ce calcul est vérifié par
test. L'aire descendante `7,35 %` et la projection de supports `11 947 mm²`
restent des proxys F41. Aucun support réel, parcours laser, projet slicer ou
fichier BLT n'est généré. Les portes correspondantes restent fermées jusqu'à
livraison des cinq preuves suivantes : projet du slicer fournisseur, géométrie
des supports, rapport de collision recoater, statistiques d'exposition par
couche et fichier machine signé par le fournisseur.

## Traitement honnête du plafond 3 300 K

`Tmax = 3300 K` est un limiteur implicite du tutoriel AdditiveFOAM. F42 vérifie
qu'il est toujours présent dans `system/fvSolution` et refuse de préparer un
cas où il diffère. Le relever ou le supprimer étendrait artificiellement la
carte thermophysique et ne résoudrait ni le bilan énergétique ni la
calibration du faisceau.

Une valeur `Tmax >= 3299 K` est donc classée **observation censurée à droite** :

- elle ne peut pas servir à classer les points DOE par température de pic ;
- elle invalide la comparaison de convergence correspondante ;
- elle ferme `temperature_cap_free` et `doe_response_ranking_permitted` ;
- elle déclenche une revue du pas de temps, du maillage, du spot, de
  l'absorptivité, de la température de plaque et des pertes de surface.

La fenêtre F42 réduit déjà nettement l'énergie volumique par rapport à F41. Si
elle atteint encore la borne, la bonne réponse est la calibration et l'étude
de résolution, pas la modification du solveur.

## Convergence numérique

Les 27 points sont préparés au niveau nominal. Trois extrêmes physiques sont
en plus générés sur trois maillages : `P360-V1500-H160`, le témoin
`P380-V1300-H150` et `P400-V1200-H130`.

| Niveau | cellules du bloc de base | cellules par couche |
| --- | ---: | ---: |
| grossier | 120 × 20 × 24 | 4 |
| nominal | 150 × 25 × 30 | 5 |
| fin | 180 × 30 × 36 | 6 |

Pour passer, les trois niveaux doivent exister, tous les champs doivent être
finis, chaque solveur doit terminer sans erreur, le nombre de Courant maximal
doit rester au plus `0,5` et aucune saturation à 3 300 K n'est admise. Entre
nominal et fin, l'écart relatif maximal est `5 %` sur longueur/largeur/profondeur
du bain et volume fondu, et `3 %` sur T P99. Même un écran numérique passant ne
qualifie pas la machine ou la pièce.

## Exécution

Préparer le CSV et le manifeste sans solveur :

```sh
python3 twins/reference-917-engine/source/prepare_additivefoam_f42_doe.py \
  --matrix-only \
  --output work/917-f42-lpbf/doe
```

Préparer les 27 cas nominaux et les six raffinements supplémentaires :

```sh
python3 twins/reference-917-engine/source/prepare_additivefoam_f42_doe.py \
  --additivefoam /opt/openfoam/AdditiveFOAM \
  --mode all \
  --output work/917-f42-lpbf/doe
```

Ajouter `--execute --openfoam /opt/openfoam/OpenFOAM-14 --jobs 2` pour lancer.
Les révisions Git exigées sont verrouillées dans la spécification. La faible
valeur de `--jobs` évite de multiplier sans contrôle les 16 rangs MPI de chaque
cas.

Après exécution, les VTK, CSV de bain et nombres de Courant sont extraits puis
évalués ainsi :

```sh
python3 twins/reference-917-engine/source/extract_additivefoam_f42_metrics.py \
  --jobs 12 \
  --run-manifest work/917-f42-lpbf/doe/917-head-lpbf-doe-f42-manifest.json \
  --output work/917-f42-lpbf/doe/measurements.json

python3 twins/reference-917-engine/source/evaluate_additivefoam_f42_doe.py \
  --measurements work/917-f42-lpbf/doe/measurements.json \
  --output work/917-f42-lpbf/doe/917-head-lpbf-doe-f42-results.json
```

Le schéma de chaque mesure exige : identifiant, résolution, état de fin,
finitude, températures maximale et P99, volume fondu, trois dimensions du bain
et nombre de Courant maximal. Une mesure manquante, dupliquée ou hors matrice
échoue explicitement.

L'extracteur lit uniquement les fichiers VTK volumiques `layer1_*.vtk` à la
racine de chaque export. Les fichiers `POLYDATA` des patches ne sont pas des
états volumiques et sont volontairement exclus. `--jobs` parallélise cette
lecture sans modifier les résultats.

## Exécution mesurée F42.2

Deux hôtes x86 indépendants ont exécuté la matrice complète : `33/33` calculs
terminés sur chacun, `0` saturation à `3 300 K`, `3/3` études de convergence
passées et `33/33` résultats reproduits dans les tolérances. La plage T99 des
27 cas nominaux vaut `329,300–392,168 K` sur les deux hôtes. L'écart absolu
inter-hôtes maximal sur T99 est `3,0517578125e-5 K`.

Les preuves, images et SHA-256 sont décrits dans
[le rapport F42.2 exécuté](917_F42_2_ADDITIVEFOAM_LIVE.md). Cette réussite ouvre
uniquement la gate de classement numérique du DOE ; les gates de support,
fichier machine, coupon, matériau, impression et démarrage restent fermées.

Le futur export de tranchage fournisseur peut être contrôlé séparément :

```sh
python3 twins/reference-917-engine/source/verify_f42_slicing.py \
  --supplier-slice-report work/917-f42-lpbf/slicer/supplier-slice-report.json \
  --output work/917-f42-lpbf/slicer/verified-slice-report.json
```

Le vérificateur relit exhaustivement les `4 122` lignes du CSV, contrôle les
indices contigus, le pas Z de `0,05 mm`, la finitude et la positivité des
expositions, l'existence et le SHA-256 des supports, du rapport recoater et du
fichier machine. Même si ces contrôles passent, les portes coupon, carte
fournisseur et autorisation d'impression restent fermées.
