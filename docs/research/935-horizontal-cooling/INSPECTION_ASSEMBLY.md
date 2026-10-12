# Assemblage PicoGK d'inspection — 12 octobre 2026

Cette étape assemble réellement dans PicoGK le **rotor candidat 935**, le
**scan complet de son entraînement/support**, le **scan de carter/cylindres disponible** et
un **carénage d'admission provisoire**. Les composants restent distincts dans
les exports GLB et OpenUSD. Aucun calcul de dynamique ni montage physique
n'est validé par cette scène.

Le carter moteur avec cylindres retrouvé est identifié dans son fichier source comme un
**917**, et non comme un 935. Il sert ici de contexte comparatif. Le scan
« 935 Xtreme Cyl head » contient une culasse ; il ne définit pas le moteur
complet ni ses fixations. La cible reste la réplique 935, puis son adaptation
993. Cette scène ne remplace pas la référence moteur 935 encore manquante.

## Ce qui a été construit

- Le [programme C#](../../../twins/935-horizontal-cooling-system-f0/source/picogk-inspection-assembly/Program.cs)
  importe et place les trois maillages existants avec `PicoGK.Mesh`. Il conserve
  l'ordre des triangles et utilise des transformations rigides réversibles,
  avec une échelle uniforme explicite. Les surfaces ouvertes restent ouvertes.
- Le carénage est généré avec deux sections de `PicoGK.Lattice`, puis une
  soustraction voxel pour garder l'admission ouverte. Le cylindre et la lèvre
  évasée se recouvrent à leur jonction pour éviter les faces non-manifold
  apparues dans la première tentative. Il ne représente pas le guide complet
  répartissant l'air sur les six cylindres d'un moteur 935.
- Le [contrôle et export](../../../twins/935-horizontal-cooling-system-f0/source/export_inspection_assembly.py)
  relit indépendamment les positions de **chaque triangle** transformé,
  contrôle les empreintes et la fermeture du carénage, puis vérifie les
  exports GLB et USD en mètres. La scène USD reste géométrique : aucune liaison
  ou masse physique n'est attribuée à une interface inconnue.
- Les [vues ombrées](../../../twins/935-horizontal-cooling-system-f0/source/render_inspection_assembly.py)
  réutilisent le runtime VTK déjà employé pour la 917 et conservent **tous les
  triangles**, sans simplification. Les couleurs distinguent les composants,
  sans désigner un alliage qualifié.

## Placement et limites

Les unités des scans ne sont toujours pas confirmées. Le facteur d'affichage
est **1 mm par unité source supposée**. Les matrices et leurs inverses
permettent de reprendre le montage après calibration.

La pose du moteur utilise sa PCA pour l'inspection, sans établir de datum.
L'entraînement utilise le repère provisoire d'une surface locale du support.
Son placement au-dessus de la boîte englobante du moteur assure une séparation
visuelle ; il ne crée pas de contact de fixation ni de chemin d'efforts.

Le premier placement du rotor intersectait une excroissance observée de
l'entraînement. Le second recentre le rotor sur un **centre cylindrique
estimé sur un arc partiel**, inférieur aux 330° exigés pour qualifier un axe
dans le coordinateur existant. Ce centre reste donc une hypothèse de pose.
La portée, les cannelures conjuguées, la retenue axiale et l'ajustement ne sont
pas définis par ce rapprochement visuel. Les tentatives rejetées sont conservées.

La revue visuelle montre aussi des extrémités et raccords de pales encore
irréguliers dans le candidat périodique hérité. Cet assemblage conserve cette
géométrie pour permettre son inspection ; il ne clôt pas sa reconstruction.

Le dégagement rotor/carénage est contrôlé pour toutes les positions angulaires
par une enveloppe radiale conservative des triangles, y compris leurs arêtes.
Les autres contrôles utilisent des enveloppes de triangles et les séparations
des boîtes englobantes. Une enveloppe qui se recoupe signale un contrôle à
approfondir ; elle ne prouve pas à elle seule une collision. Les intérieurs
absents des scans, les dilatations et les déformations restent exclus.

## Reproduction sans location de machine

Réutiliser une installation officielle PicoGK/.NET 9 locale compatible avec
le système et fournir un cas privé contenant : `classification`,
`scale_verified: false`, `engine_context_family`, `assumptions`, `voxel_mm`,
`imports` et `shroud`. Chaque import contient son `id`, son chemin privé,
son SHA-256, sa classification et `source_to_assembly_mm`, une matrice 4×4
appliquée à des **vecteurs colonnes**. Le C# la transpose pour l'API PicoGK.
Le cas réellement exécuté et ses paramètres restent dans l'archive privée.

```sh
dotnet build twins/935-horizontal-cooling-system-f0/source/picogk-inspection-assembly/InspectionAssembly.csproj \
  -c Release -p:PicoGKAssembly=/PRIVATE/PicoGK.dll
# Rendre la bibliothèque native officielle accessible au chargeur du système.
dotnet twins/935-horizontal-cooling-system-f0/source/picogk-inspection-assembly/bin/Release/net9.0/InspectionAssembly.dll \
  work/PRIVATE/case.json CASE_SHA256 work/PRIVATE/new-native-output
python twins/935-horizontal-cooling-system-f0/source/export_inspection_assembly.py \
  work/PRIVATE/new-native-output work/PRIVATE/new-exports
python twins/935-horizontal-cooling-system-f0/source/render_inspection_assembly.py \
  work/PRIVATE/new-native-output work/PRIVATE/new-exports work/PRIVATE/new-views
python -m unittest discover -s tests -p test_935_inspection_assembly.py -v
```

NumPy/trimesh et `usd-core` servent aux exports ; VTK sert aux vues.
Le programme refuse d'écraser une sortie et impose `work/` ignoré pour les
géométries. Le C# vérifie aussi les empreintes, les dimensions bornées et
l'absence de réflexion ou de déformation anisotrope.

## Prochaine étape de montage 935

Remplacer le contexte 917 par la géométrie du carter moteur 935/930 identifié,
puis établir ses faces et trous de fixation, l'axe de sortie du renvoi,
l'empilage moyeu/arbre et la définition du guide d'air. Le même assembleur
permettra de reprendre les poses et le carénage sans modifier les scans.
La validation des efforts, de la transmission et du refroidissement attend
ces interfaces ; les calculs antérieurs ne qualifient pas ce nouvel assemblage.

Les résultats détaillés et les tentatives rejetées sont privés. Le
[reçu d'exécution](inspection-assembly-20261012.json) conserve les contrôles,
empreintes et limites publiables. Aucune machine Vast n'a été louée.
