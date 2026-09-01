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

Le porteur du projet confirme que le fichier est sous licence ouverte et
réutilisable, mais l'identifiant standardisé de cette licence n'est pas encore
archivé. Indépendamment de ce droit, son instruction est de conserver le scan
et tous ses dérivés géométriques hors Git. Ni l'identification exacte ni
l'échelle en millimètres ne sont confirmées. Aucun artefact ne doit être présenté comme
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

Le brut est rangé sans modification sous
`raw-scans/917-engine/original/917-engine-case-with-cylinders.obj`. Une copie
USD sans instanciation, adaptée au rendu et aux étapes de simulation, est
produite hors Git sous `work/simready-results/917/`. La conversion contrôlée
contient un maillage de 7 397 573 points et 2 465 877 faces, en axe Z avec
`metersPerUnit = 0.001`; son enveloppe est de 1002,175 × 768,275 × 739,765
unités de scène. Ces métadonnées ne suffisent toujours pas à confirmer l'échelle
physique du scan.

Un rendu OVRTX 768 × 768 a été obtenu dans le conteneur SimReady. L'assignation
automatique de matière par le Material Agent reste bloquée par un refus 403 de
l'endpoint NVIDIA et ne doit pas être présentée comme validée. Le maillage brut,
les USD et les images restent hors Git en attendant la clarification des droits.

## Livrables visés

| Livrable | Usage | Limite |
|---|---|---|
| copie OBJ vérifiée | traçabilité | stockage local uniquement sur instruction du propriétaire |
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

## Assemblage fonctionnel complet F1

Une nomenclature paramétrique distincte du scan reconstruit les familles
fonctionnelles identifiables du moteur Type 912. Elle comprend 31 prototypes
STEP et STL d'inspection, instanciés 275 fois dans un stage OpenUSD : carters,
vilebrequin et huit paliers, pistons, axes, segments, bielles, cylindres,
culasses individuelles, soupapes et ressorts, quatre arbres à cames et leur
entraînement central, admission, double allumage, lubrification à carter sec,
refroidissement, échappement et accessoires. La variante `917_30_turbo` active
en plus deux turbocompresseurs et deux plénums ; la variante par défaut
`type_912_4_5_na` les masque.

```bash
make 917-complete-assembly
```

La chaîne utilise l'image immuable
`ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:41965aa48548481473a63f4d0277599b93cf4870d2e1f833099dd4e8e146d2f3`.
Elle exige d'abord un prévol SimReady vert, génère les géométries avec
Build123d, convertit chaque prototype STEP en USDC, compose le stage instancié,
puis contrôle les deux variantes. Les sorties restent localement sous
`work/917-complete-engine/`; aucun scan, STEP, STL ou USD n'est versionné.

Le résultat est un assemblage d'encombrement et de topologie, pas une CAO
constructeur. Les dimensions sourcées sont séparées des hypothèses de placement
(longueur de bielle, longueur des arbres, enveloppe des turbos, notamment).
L'affectation de matériaux, les joints physiques et PhysicsNeMo sont
intentionnellement absents tant que les interfaces, masses, alliages, profils de
came, jeux et cas de charge ne sont pas mesurés. Il est interdit d'utiliser ces
proxies pour fabriquer ou faire tourner un moteur.

Les principales sources de recoupement sont l'analyse moteur
[auto motor und sport](https://www.auto-motor-und-sport.de/oldtimer/porsche-917-motor-kraftwerk-ohne-gleichen/),
les [détails techniques Stuttcars](https://www.stuttcars.com/porsche-917-technical-details/),
la synthèse secondaire [kfz-tech](https://www.kfz-tech.de/Buchprojekte/Porsche/917Teil2.htm)
et la fiche officielle du
[Porsche 917/30 Spyder](https://newsroom.porsche.com/de/pressemappen/Porsche-Museum/Porsche-917-30-Spyder.html).

## Recoupement documentaire Stuttcars

La page [Porsche 917 Technical Details](https://www.stuttcars.com/porsche-917-technical-details/)
transmise par le porteur du projet confirme comme piste secondaire un flat-12
refroidi par air, deux arbres à cames par banc, une prise de puissance centrale,
un vilebrequin annoncé à 757 mm et des bielles forgées en titane. Elle distingue
notamment 85 × 66 mm pour la première définition et 86 × 70,2 mm pour la version
4 907 cm³. Ces données aident à nommer et paramétrer les futurs organes 917,
mais elles ne donnent ni contour de piston, ni entraxe de bielle, ni profil de
came, ni géométrie des deux turbos du 917/30. Elles ne calibrent donc pas à elles
seules le scan.

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
