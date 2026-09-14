# F36 — reconstruction quatre soupapes contrainte par le scan

## Résultat de la correction

F36 retire F34 comme géométrie produit. La peau externe n'est plus un bloc
paramétrique : elle est reconstruite sur l'enveloppe du scan 935, avec ses
ailettes, bossages, admissions et sorties. L'ancien coeur deux soupapes est
rebouché numériquement puis remplacé par deux admissions, deux échappements,
quatre guides et sièges, et un double allumage latéral.

Le résultat local est un prototype d'architecture destiné à la revue humaine.
Il n'est ni une identité dimensionnelle Porsche 917, ni une CAO de définition,
ni une pièce autorisée à imprimer ou démarrer.

## Ce qui est calculé

Le script
[`build_scan_conforming_4v_f36.py`](../twins/reference-917-engine/source/build_scan_conforming_4v_f36.py)
refuse toute source dont le SHA-256 diffère du scan enregistré. Une
reconstruction Screened Poisson ferme la peau ouverte; la transformation dans
le repère chambre vient du rapport d'interface local. Le coeur fonctionnel est
ensuite remplacé par une opération voxel à pas de 0,75 unité OBJ.

| Contrôle F36 | Résultat local |
| --- | ---: |
| Échantillons peau du scan | 50 000 |
| Écart scan/reconstruction médian | 0,082 unité OBJ |
| Écart p95 | 0,439 unité OBJ |
| Écart p99 | 0,710 unité OBJ |
| Écart maximal | 2,938 unités OBJ |
| Corps final | 1, étanche, orientation cohérente |
| Échantillons paroi interne | 4 390 |
| Distance interne minimale échantillonnée | 6,379 unités OBJ |

Cette dernière valeur est une distance au stock rebouché, pas une carte CT
d'épaisseur. L'unité du fichier paraît être le millimètre mais n'est pas
confirmée; le rapport conserve donc les résultats en unités OBJ.

## Recalcul multi-solveur final du 3 septembre 2026

Le recalcul utilise la peau extérieure étanche F36 dérivée du scan. Il ne
réutilise pas le bloc F34. Toutes les valeurs dimensionnelles et mécaniques
restent conditionnelles à l'hypothèse `1 unité OBJ = 1 mm`.

### Air extérieur — deux méthodes réellement indépendantes

La campagne finale et ses fichiers de sortie traçables sont décrits dans
[`917_F36_FINAL_CFD_THERMAL.md`](917_F36_FINAL_CFD_THERMAL.md). Le cas OpenFOAM
de référence sans carénage compte 200 305 cellules : Δp = 684 Pa,
Q = 2,949 kW et erreur du bilan énergétique = 0,42 %. Les cas carénés RANS
retenus pour l'étude de sensibilité comptent 193 383 et 460 657 cellules;
leurs coefficients d'échange diffèrent de 16,26 % et leur fermeture
énergétique reste mauvaise. Ils sont donc rejetés comme validation thermique.

FluidX3D 3.7 utilise un LBM D3Q19 TRT avec un scalaire thermique D3Q7. La
condition isotherme est appliquée aux cellules fluides adjacentes à la peau;
les solides seuls restent adiabatiques dans cette formulation, conformément à
la [documentation FluidX3D](https://github.com/ProjectPhysX/FluidX3D/blob/master/DOCUMENTATION.md)
et à l'[explication du mainteneur](https://github.com/ProjectPhysX/FluidX3D/issues/347).

| FluidX3D | Grille | Pas | Chaleur | Δp par traînée | État |
| --- | ---: | ---: | ---: | ---: | --- |
| ultra ajusté | 384 × 213 × 160 | 0,9375 mm | 23,148 kW | 1 696 Pa | référence finale LBM |

La grille finale ne converge pas vers OpenFOAM et l'écart thermique croisé
reste largement supérieur au critère de 5 % : la validation croisée échoue.
De plus, la fermeture thermique LBM
emploie une diffusivité effective constante de 0,012686 m²/s, environ 443 fois
la diffusivité moléculaire entrée. Les sensibilités à 0,001 et 0,003 m²/s
deviennent numériquement instables lorsque la relaxation thermique approche sa
limite. FluidX3D ne confirme donc pas OpenFOAM; l'écart est enregistré comme
échec de validation croisée. Les valeurs intermédiaires antérieures ne sont
plus la référence de décision.

### Structure — convergence et point bloquant

CalculiX résout un écran élastique linéaire C3D8 sous 24,686 MPa, avec gradient
thermique prescrit de 260 à 120 °C. La carte candidate Aheadd HT1 utilise ici
`E = 66 GPa`, `ν = 0,33`, `α = 23 µm/m/K` et une limite chaude hypothétique de
216 MPa. Ces valeurs ne remplacent pas des éprouvettes du lot imprimé.

| Pas voxel | Éléments | Déplacement max | Von Mises p95 | Von Mises max |
| ---: | ---: | ---: | ---: | ---: |
| 4,0 | 25 629 | 0,926 mm | 33,54 MPa | 402,00 MPa |
| 3,0 | 57 016 | 0,903 mm | 34,82 MPa | 427,02 MPa |
| 2,5 | 94 805 | 0,899 mm | 36,32 MPa | 407,97 MPa |

Entre les deux maillages les plus fins, le p95 varie de 4,30 % et le
déplacement de 0,42 % : l'écran global converge à 5 %. En revanche, le maximum
reste entre 402 et 427 MPa, au bord d'un appui de goujon sur le deck. Il peut
contenir une singularité de liaison, mais dépasse la limite chaude candidate
sur les trois maillages. Tant qu'un modèle avec contact, précharge, congé réel
et carte non linéaire ne l'a pas résolu, cette zone reste rouge.

### Combustion et comparaison deux/quatre soupapes

La campagne Cantera/Wiebe F33 a été rejouée à l'identique : son rapport retrouve
11,885 MPa et 620,41 hp pour l'écran atmosphérique, puis 24,686 MPa et
1 601,20 hp pour l'écran turbo. Ce sont des charges thermodynamiques 0D non
corrélées, pas une prédiction moteur F36.

La campagne F33 deux/quatre soupapes a également été rejouée : le proxy quatre
soupapes donne +20,45 % de débit CFD sur les conduits équivalents fins,
+15,279 % au banc de flux virtuel et +4,268 % de puissance 0D à 9 000 tr/min.
Ces gains ne sont pas transférés à la pièce F36, car le scan ne fournit ni
domaines internes étanches 2V/4V, ni levée de soupape, ni loi de came.

## Architecture mécanique de revue

| Élément | Proposition F36 | État |
| --- | --- | --- |
| Admission | 2 × 31,5, tige 7, axe −18° | packaging passé, loi de levée absente |
| Échappement | 2 × 26, tige 7, axe +18° | packaging passé, loi de levée absente |
| Angle inclus | 36° | hypothèse d'architecture |
| Allumage | 2 pilotes latéraux inclinés, M10×1 candidat | filetage et insert non définis |
| Culasse | Aheadd HT1 candidat LPBF après traitement chaud | non libéré sans éprouvettes machine/lot |
| Soupapes admission | Ti-6Al-4V corroyé ou forgé | acheté, non imprimé |
| Soupapes échappement | INCONEL alloy 751 corroyé | acheté, non imprimé |
| Ressorts | double ressort Cr-Si acheté | raideur et charges non libérées |

Le choix de culasse reste Aheadd HT1 avec traitement haute température #2,
plutôt que CP1, parce que la priorité actuelle est la tenue vers 250 °C. La
[fiche Aheadd HT1](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/aheadd_ht1_fact_sheet_230620.ccac52e244fb.pdf)
annonce typiquement 216 MPa de limite à 0,2 %, 265 MPa de résistance ultime et
5 % d'allongement à 250 °C dans la direction verticale. Ce sont des valeurs
typiques fournisseur, pas des valeurs admissibles de calcul; la machine, le
lot de poudre, l'orientation, le HIP et le traitement doivent être qualifiés
sur éprouvettes.

Le Ti-6Al-4V d'admission reste une soupape corroyée/forgée achetée; la
[fiche TIMETAL 6-4](https://www.timet.com/documents/datasheets/alpha-and-beta-alloys/timetal-6-4.pdf)
documente les états forgés et les données de fatigue, mais ne constitue pas à
elle seule une qualification de soupape. Pour l'échappement, la
[fiche INCONEL 751 de Special Metals](https://www.specialmetals.com/documents/technical-bulletins/inconel/inconel-alloy-751.pdf)
identifie explicitement cet alliage comme matériau de soupape d'échappement de
moteur à combustion. Les deux soupapes restent des composants achetés, non
imprimés avec la culasse.

La poche de siège la plus proche garde 3,297 unités OBJ jusqu'au bord de
chambre; le pilote de bougie garde 3,895 unités OBJ jusqu'à la poche la plus
proche. Ces valeurs ne deviennent des millimètres qu'après confirmation de
l'échelle.

Le ressort ne peut pas être choisi honnêtement avant d'avoir la loi de came,
l'accélération, la hauteur installée, les masses mobiles, le régime maximal et
une corrélation spintron. F34 avait figé des forces sans ces entrées; F36 les
retire du statut de définition.

## Refroidissement à reconstruire sur la vraie forme

Le chemin thermique visé reste chambre et sièges → aluminium → pieds
d'ailettes → ailettes → air forcé caréné. F36 préserve la morphologie des
ailettes du scan afin que ce chemin puisse enfin être calculé sur la bonne
peau. Le modèle de carénage devra imposer l'air localement de `+Y` vers `−Y`
au travers des canaux, avec un débit par culasse issu d'un bilan énergétique et
d'une carte ventilateur, pas l'ancienne vitesse arbitraire de F34.

La campagne F36 compare maintenant deux méthodes indépendantes sur la même
géométrie et les mêmes conditions limites nominales :

1. OpenFOAM, volumes finis RANS à paroi imposée;
2. FluidX3D, Lattice Boltzmann pour la contre-vérification de l'air externe.

Les résultats F34 ne sont pas transférables : géométrie, surface d'échange,
répartition d'air et pertes de charge ont changé. La prochaine étape thermique
reste une CHT conjuguée air/métal, avec flux chambre/sièges, carte matériau
dépendante de la température et carénage de refroidissement mesuré.

## Reproduction locale

Les scans et tous les maillages dérivés restent hors Git. Dans l'environnement
local qui contient la source autorisée :

```bash
python twins/reference-917-engine/source/build_scan_conforming_4v_f36.py \
  --scan /chemin/local/935-xtreme-cylinder-head.obj \
  --envelope /chemin/local/head-envelope-uncapped.ply \
  --interfaces /chemin/local/interfaces.json \
  --output work/917-scan-conforming-f36/run

make 917-scan-conforming-4v-f36-check
make 917-scan-conforming-4v-f36-publish
make 917-scan-conforming-4v-f36-render
```

La variante de calcul retenue est `F36-013`: rayon de baie de distribution
`50,85` et plancher `49,15` unités OBJ. Si l'unité du scan est bien le
millimètre, son volume fermé est `1 059 854,924 mm³` et sa masse nue avec la
densité HT1 de `2 670 kg/m³` vaut `2,829813 kg`. Cette masse passe la cible
comparative de `2,83 kg`, sans confirmer l'échelle ni la compatibilité 917.
Ces deux paramètres ont été ajustés à la cible de masse : ils ne résultent pas
d'une optimisation DOE. Le contrôle d'épaisseur publié utilise le stock avant
ouverture de la baie et ne valide donc pas les ligaments locaux autour des
tours de guides; la porte `valvetrain_bay_local_ligament_validated` reste
explicitement fermée.

Le dossier local produit trois STL, une planche PNG et
`geometry-report.json`. Le rapport numérique JSON peut être versionné après
revue; les STL et la planche contenant la morphologie du scan restent locaux et
ne sont pas publiés automatiquement.

## Portes fermées

L'échelle absolue, les interfaces 917, le porte-arbres, les lois de came, les
galeries d'huile, les inserts, les tolérances, la carte matériau à chaud issue
d'éprouvettes, la CHT, la fatigue thermomécanique, CT/CND, banc de flux,
spintron et banc moteur restent à fournir. L'impression métallique et le
démarrage moteur restent interdits.
