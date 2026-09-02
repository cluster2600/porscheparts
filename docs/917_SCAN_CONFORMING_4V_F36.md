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

La prochaine campagne compare deux méthodes indépendantes sur la même
géométrie et les mêmes conditions limites :

1. OpenFOAM, volumes finis RANS puis CHT conjuguée air/métal;
2. FluidX3D, Lattice Boltzmann pour la contre-vérification de l'air externe.

Les résultats F34 ne sont pas transférables : géométrie, surface d'échange,
répartition d'air et pertes de charge ont changé. Les deux nouvelles campagnes
restent fermées tant que la morphologie F36 n'est pas acceptée en revue.

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
```

Le dossier local produit trois STL, une planche PNG et
`geometry-report.json`. Aucun de ces dérivés n'est publié automatiquement.

## Portes fermées

L'échelle absolue, les interfaces 917, le porte-arbres, les lois de came, les
galeries d'huile, les inserts, les tolérances, la carte matériau à chaud issue
d'éprouvettes, la CHT, la fatigue thermomécanique, CT/CND, banc de flux,
spintron et banc moteur restent à fournir. L'impression métallique et le
démarrage moteur restent interdits.
