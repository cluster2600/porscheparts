# Nervures LatticeLibrary et échange VDB de la culasse

Le [runner C#](source/bionic/HeadBionicRunner.cs) construit les trois volumes
avec le générateur ShapeKernel de l'[étude architecturale](ORIGINAL_ARCHITECTURE.md),
puis ajoute des nervures extérieures ouvertes issues de LatticeLibrary.
Ce sont des renforts candidats ; leur placement ne découle pas d'un calcul
de charges ou de fatigue. Le [rapport](derived/bionic-report.json) conserve
leur inspection indépendante et la provenance de l'exécution native.

## LatticeLibrary réellement employée

`CuboidCell` dispose des cellules BCC ; `BodyCentreLattice` construit
leurs diagonales et `ConstantBeamThickness` fixe un diamètre hypothétique de
3,5 mm. Les cellules mesurent 12 × 14 × 14 mm, sans bruit aléatoire.
Les cellules complètes ont leur face interne noyée dans les deux flancs,
puis sont réunies au corps. Une première grille recoupée a été rejetée
pour fragments extérieurs détachés.
Il n'y a pas de treillis dans l'eau ni de suppression du noyau porteur.
Le [fichier de références](source/bionic/references.json) enregistre les
hypothèses et les empreintes des sources Apache-2.0 installées.

Ce changement ajoute de la matière. Il faut mesurer rigidité, contraintes,
fatigue, accès de fabrication et interactions thermiques avant de retenir
un renfort. Le caractère organique d'un rendu ne valide pas ces critères.

## Champs OpenVDB effectivement échangés

Le fichier local `work/962-head/bionic-native-002/head-fields.vdb` contient :

| Nom | Type | Interprétation |
| --- | --- | --- |
| `metal_domain` | Voxels | Corps avec les nervures candidates |
| `coolant_domain` | Voxels | Chemise d'eau conforme |
| `dry_domain` | Voxels | Réservations sèches, dont conduits, guides et poches |
| `coolant_native_signed_distance` | ScalarField | Distance géométrique native PicoGK |
| `coolant_native_gradient` | VectorField | Gradient géométrique natif PicoGK |

Les champs sont relus **par nom** : l'ordre des grilles VDB n'est pas garanti.
Les trois domaines passent `bIsEqual`. La traversée de toutes les valeurs
actives compare exactement les scalaires et vecteurs sauvegardés/rechargés,
dans les deux sens pour détecter aussi les valeurs ajoutées. Les compteurs
et le SHA-256 du VDB sont conservés dans le rapport. Ce fichier dérivé reste
local ; le code est la source éditable et partageable.

Aucune température, pression, vitesse d'eau ou contrainte n'est calculée.
Le champ scalaire garde les unités natives de grille. Dans l'API inspectée,
`ScalarField.fSignedDistance` multiplie sa valeur par `voxel_mm` pour obtenir
des millimètres ; un solveur en mètres demande encore une division par 1 000.
Le gradient conserve sa convention native et ne représente pas une vitesse. Un échange VDB réussi
ne prouve pas une simulation de refroidissement réussie.

## Reproduction

Les bibliothèques sont celles des références enregistrées. Compilation :

```sh
dotnet build twins/962-cylinder-head-f0/source/bionic/Engine.csproj \
  -p:PicoGKBinaryRoot=/chemin/vers/runtime-PicoGK-verifie \
  -p:ShapeKernelRoot=/chemin/vers/LEAP71_ShapeKernel \
  -p:LatticeLibraryRoot=/chemin/vers/LEAP71_LatticeLibrary \
  -o work/962-head/bionic-bin
```

Placer les dépendances natives vérifiées à côté du binaire et exécuter le
runner **sous le verrou partagé** de
[run_part.py](../../parts/picogk-catalog/tools/run_part.py). Il prend le dossier
`source/architecture/` et un dossier de sortie neuf. L'inspection emploie les
maillages de passages vérifiés de l'étape précédente :

```sh
python twins/962-cylinder-head-f0/source/bionic/inspect_and_render.py \
  work/962-head/bionic-native-002 work/962-head/bionic-bin \
  /chemin/vers/LEAP71_LatticeLibrary \
  work/962-head/architecture-final-inspected \
  work/962-head/bionic-inspected-new
```

Les [contrats d'interfaces](interface-contract.json) et les autorisations de
fabrication restent inchangés. Cette étape complète une étude logicielle et
géométrique, sans qualifier une culasse pour le kit de 1 000 ch moteur.
