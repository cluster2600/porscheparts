# Jumeau de référence du moteur Porsche 917

## Portée actuelle

Ce dossier transforme le scan local du carter avec cylindres en un jumeau
extérieur reproductible. Le fichier OBJ et tous les maillages dérivés restent
hors Git. Seuls le code, la méthode et les résultats textuels vérifiables sont
versionnés.

Deux familles de sortie sont prévues :

- un modèle `F1_exterior_reference` qui conserve les surfaces mesurables du
  scan et les interfaces répétées détectées ;
- un modèle `display_print` fermé et simplifié pour fabriquer une maquette
  non fonctionnelle.

Ni l'identification exacte, ni l'échelle en millimètres, ni la licence du
fichier ne sont encore confirmées. Aucun artefact ne doit être présenté comme
une pièce moteur fonctionnelle, compatible 993 ou prête pour un essai.

## Exécution

```bash
PYTHON=/chemin/vers/python \
  twins/reference-917-engine/run_pipeline.sh \
  raw-scans/917-engine/original/917-engine-case-with-cylinders.obj \
  work/917-engine/pipeline
```

La sortie lourde reste sous `work/`. Le pipeline refuse un fichier source dont
l'empreinte ne correspond pas au scan inspecté.

## Livrables visés

| Livrable | Usage | Limite |
|---|---|---|
| copie OBJ vérifiée | traçabilité | redistribution bloquée |
| maillages allégés | inspection et mesures | unité OBJ non confirmée |
| composants séparés | revue carter/cylindres/éléments isolés | classification à valider visuellement |
| rapport d'interfaces | axes, diamètre et pas des cylindres | dépend de la qualité des ouvertures visibles |
| proxy STEP | assemblage et encombrement | géométrie simplifiée |
| STL étanche | maquette d'exposition | interdit pour un usage moteur |
| domaines CFD locaux | développement de la chaîne numérique | pas de conditions moteur inventées |

## Résultats F1 actuels

Le maillage de travail à 600 000 triangles conserve le scan avec un écart p95
de 0,107 unité OBJ sur 50 000 points échantillonnés. La version à 250 000
triangles atteint 0,244 unité p95 et reste réservée à la visualisation.

La détection par projection, transformée de Hough et ajustement RANSAC retrouve
deux rangées de six ouvertures :

- diamètre visible moyen : 86,63 unités OBJ, plage 85,20 à 87,76 ;
- pas longitudinal régulier : 118,03 sur la rangée positive et 117,87 sur la
  rangée négative ;
- coupure centrale après le troisième cylindre : 172,84 et 173,89 ;
- décalage longitudinal médian entre rangées : 36,94.

Ces valeurs décrivent les ouvertures visibles du scan. Elles ne prouvent ni le
diamètre d'alésage, ni la variante du moteur, ni une unité millimétrique.

## Modèles d'impression

Les deux STL sont reconstruits directement à leur échelle cible avec un voxel
de 0,8 mm, puis nettoyés pour ne conserver qu'un volume principal. Sous
l'hypothèse encore non confirmée `1 unité OBJ = 1 mm` :

| Échelle | Enveloppe candidate | Triangles | Gates géométriques |
|---|---:|---:|---|
| 1:4 | 223,18 × 123,27 × 107,22 mm | 497 738 | étanche, manifold, un seul volume |
| 1:8 | 115,53 × 61,14 × 53,51 mm | 123 324 | étanche, manifold, un seul volume |

`Géométriquement imprimable` ne veut pas dire `prêt à lancer`. Les ailettes,
passages et détails fins exigent encore une revue dans le slicer, une stratégie
de supports et, en résine, un plan intentionnel d'évidement et de drainage.
Les fichiers restent des maquettes statiques non fonctionnelles.

## CFD externe

La peau externe fermée est alignée dans le repère moteur, convertie
provisoirement en mètres et allégée à 300 000 triangles. Le cas OpenFOAM
`snappyHexMesh` construit 130 208 cellules autour de cette peau, dont 118 304
hexaèdres. `checkMesh` bloque toutefois le solveur avec deux contrôles en échec :
21 faces dupliquées, 170 faces à sommets partagés non consécutifs, 76 faces très
asymétriques et 6 111 cellules concaves. Aucune solution d'écoulement n'est donc
produite ou revendiquée.

Le contrôle distant s'exécute séparément :

```bash
twins/reference-917-engine/source/check_external_cfd.sh \
  work/917-engine/pipeline/cfd/external-cooling

python twins/reference-917-engine/source/summarize_openfoam.py \
  work/917-engine/pipeline/cfd/external-cooling/checkMesh.log \
  work/917-engine/pipeline/cfd/external-cooling/cfd-validation.json
```

## Critères avant impression

1. confirmer une dimension physique et l'unité du scan ;
2. choisir une échelle d'impression explicite ;
3. vérifier l'épaisseur minimale, le drainage et le volume de matière ;
4. trancher le STL avec le profil réel de la machine et du matériau ;
5. conserver la mention `display-only` sur chaque export.

## Comparaison 993

Ce scan sert à éprouver les méthodes de gros assemblage, de répétition des
cylindres, de refroidissement externe et d'impression de maquette. Il ne fournit
aucune interface de montage 993. La comparaison dimensionnelle reste bloquée
jusqu'à disposer d'un moteur 993 nommé, de ses entraxes et registres mesurés,
ainsi que d'une échelle confirmée pour les deux jeux de données.
