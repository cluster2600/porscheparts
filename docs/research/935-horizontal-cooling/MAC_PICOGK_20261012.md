# 935 — bibliothèques PicoGK et calculs sur le Mac

La chaîne utilise maintenant les bibliothèques LEAP71 sur le Mac pour étudier
les pieds du rotor, sonder les épaisseurs et échanger géométrie et champs de
simulation en VDB. **Cinq calculs centrifuges et un point CFD concernent le
nouveau rotor à neuf pales individuelles.** Leurs contrôles révèlent encore
une convergence insuffisante ; ils ne valident pas un montage fabricable.

Le [reçu d'exécution](mac-picogk-20261012.json) donne les empreintes, versions,
résultats et rejets. Les scans, géométries, champs, cas et fichiers solveur
restent dans l'[archive privée](https://github.com/cluster2600/porscheparts-935-private/releases/tag/mac-picogk-20261012).
Le programme reste celui de la 935 historique, avec son moteur six cylindres
et ses interfaces encore à mesurer. Aucune machine Vast n'est utilisée.

## Bibliothèques qualifiées

PicoGK 2.3/Core 26.2.0 et .NET 9.0.318 tournent nativement en `osx-arm64`.
Les quatre dépôts suivants sont figés dans le
[verrou des bibliothèques](../../../twins/935-horizontal-cooling-system-f0/source/picogk-mac-study/libraries.lock.json).
Leurs sources sont compilées avec le noyau déjà installé, sans modifier les
anciens programmes ni leurs preuves. Compilation : zéro erreur et 98
avertissements d'API obsolètes dans les bibliothèques amont.

| Bibliothèque | Utilisation effective | Vérification |
|---|---|---|
| [ShapeKernel](https://github.com/leap71/LEAP71_ShapeKernel) | Repères, cylindres, tubes, masque annulaire des pieds et domaine fluide | Volume d'un tube analytique : erreur 0,049 % ; rayons donnant 9,6 mm pour une paroi de 10 mm sur une grille de 0,6 mm |
| [LatticeLibrary](https://github.com/leap71/LEAP71_LatticeLibrary) | Témoin de treillis BCC borné à un tube | Volume positif inférieur au solide enveloppe ; aucune insertion dans la réplique historique |
| [QuasiCrystals](https://github.com/leap71/LEAP71_QuasiCrystals) | Sources compilées avec les autres bibliothèques | Compilation seulement ; aucune géométrie 935 ne justifie son usage actuellement |
| [SimulationExample](https://github.com/leap71/PicoGK_SimulationExample) | Lecteur officiel du protocole fluide à cinq champs VDB | Lecture réelle et contrôle des champs par nom ; géométrie, densité, viscosité et vitesse initiale |

ShapeKernel, LatticeLibrary et QuasiCrystals sont sous Apache-2.0. Le fichier
`src/SimpleFluidSimulationInput.cs` porte SPDX CC0-1.0 ; aucune licence globale
n'est supposée pour les autres fichiers du dépôt SimulationExample.
Les nouveaux types contractuels PicoGK.Geometry demandent .NET 10/C# 14 et ne
sont pas nécessaires à cette chaîne .NET 9. Les exemples HeatX/RoverWheel ne
définissent pas une 935. Les vis génériques du projet tiers PicoGK-Fasteners
ne remplacent pas la mesure des fixations du spécimen.

## Géométrie conservée et raccords proposés

Le [programme C#](../../../twins/935-horizontal-cooling-system-f0/source/picogk-mac-study/Program.cs)
charge le rotor natif de la campagne précédente et le revoxelise à 0,6 mm
supposé. Ce passage constitue une nouvelle référence numérique ; il ne
garantit pas l'égalité avec les triangles d'origine ou le scan.

Trois fermetures morphologiques sont examinées : 0, 0,6 et 1,2 mm. Le programme
retient uniquement leurs **ajouts** dans l'anneau r = 25…95 mm, z = −30…40 mm.
Les premières sections acquises se trouvent à une station de 98 unités source
ou plus, mesurée sur l'axe radial de chaque pale. La garde ne repose pas sur
une PCA. Le programme vérifie une provenance acquise pour chacune des neuf
pales, l'absence de suppression de matière, l'absence d'ajout dans l'alésage
et l'absence de changement hors du masque.

Un contrôle indépendant compare exactement les triangles à r ≥ 98 mm entre
chaque variante et la référence revoxelisée : ils sont identiques. Les trois
maillages ont chacun une composante, sont fermés, orientés de façon cohérente
et possèdent uniquement des faces d'aire positive. Cela ne constitue pas une
preuve générale d'absence d'auto-intersections.
Ces ajouts restent des hypothèses de réparation des pieds absents ; aucun
rayon de congé historique ou d'usinage n'est déclaré mesuré. La référence
historique n'est pas remplacée par la variante de 1,2 mm.

L'inspection visuelle superpose les points du scan au rotor et montre les
variantes ainsi que les contraintes discrètes. Elle conserve l'asymétrie des
pales. Le moyeu, le dos et les raccords hypothétiques restent visibles comme
tels ; la superposition du scan entier ne qualifie pas le dos mal aligné.

## Épaisseurs et champs VDB

Les rayons sondent trois sections réellement acquises de chaque pale, avec
une garde aux extrémités de l'intervalle disponible, à 16 positions du contour.
Sur **432 sondes**, 426 produisent une longueur et six restent non résolues.
Les longueurs normales mesurées sur cette grille vont de 0,6 à 18,49 mm, avec
une médiane de 5,40 mm. Le minimum atteint la résolution du voxel : **ce n'est
pas une épaisseur minimale globale ni une cote de fabrication**. Un rayon
normal n'est pas une mesure exhaustive de la distance entre faces opposées.
Toutes les sondes et tous les échecs sont conservés dans le VDB et son reçu.

Trois types de VDB sont produits avec `PicoGK.OpenVdbFile` :

- inspection : rotor et longueurs normales échantillonnées ;
- entrée fluide : domaines solide/air, densité, viscosité cinématique et vitesse
  axiale initiale ; le lecteur officiel accepte les cinq champs par nom ;
- résultat mécanique : rotor, maxima des huit points de Gauss de chaque C3D8
  aux centres des éléments et déplacements aux nœuds.

Le domaine d'entrée fluide est un cylindre d'essai de rayon 180 mm, haut de
240 mm, rasterisé à 2 mm supposés. Il reste distinct du conduit carré du
pilote OpenFOAM. Il n'exporte pas encore la condition de paroi tournante.
L'export VDB est un protocole de données, pas un solveur CFD ni une validation
SimReady complète. Les coordonnées géométriques restent en mm supposés ;
densité, viscosité et vitesse portent explicitement leurs unités SI. Une
conversion géométrique vers le mètre est nécessaire avant un calcul SI.
Les résultats mécaniques restent **ponctuels et non interpolés** : un voxel
sans valeur n'est pas une zone à contrainte nulle.

## Calcul mécanique sur les neuf pales

PicoGK fournit les grilles de cellules dont le centre est dans le solide.
Gmsh 4.12.1 prépare les C3D8 dans le conteneur local amd64 existant ; CalculiX
2.21 résout nativement en Linux ARM64 dans Docker sur le Mac. Les solveurs
physiques complètent le noyau géométrique PicoGK.

Hypothèses communes : 1 mm/unité source, 6 000 tr/min, matériau homogène,
élasticité linéaire, coefficient de Poisson 0,33 et alésage immobilisé en
translation. La largeur de sélection des nœuds de l'alésage suit le pas de la
grille. Cette discrétisation de l'appui évolue donc avec le maillage ; son
effet n'est pas séparé de celui des cellules. Ni pression d'air, ni température,
ni contacts d'arbre, ni précontrainte réelle de serrage ne sont appliqués.

| Matériau, grille 1,5 mm | Masse conditionnelle de la CAO revoxelisée | Pic de von Mises | Déplacement maximal |
|---|---:|---:|---:|
| AlSi10Mg | 1,158 kg | 176,9 MPa | 0,816 mm |
| WE43 | 0,794 kg | 121,2 MPa | 0,887 mm |
| Ti‑6Al‑4V | 1,909 kg | 291,5 MPa | 0,855 mm |

Les masses de CAO utilisent l'intégration indépendante des triangles et les
densités des cartes existantes. La grille FEA de 1,5 mm représente un volume
2,69 % supérieur à cette géométrie et possède donc une masse distincte dans
son reçu. Les cartes ne qualifient ni le procédé d'impression ni les limites
de fatigue du spécimen. Les pics peuvent inclure des concentrations liées
aux appuis et aux marches des voxels. Ces trois lignes ne déterminent pas
un matériau vainqueur ou une vitesse admissible.

Pour l'aluminium, les grilles 1,5 → 1,35 → 1,2 mm donnent respectivement
**0,816 → 0,941 → 1,160 mm** de déplacement maximal et
**176,9 → 202,5 → 199,7 MPa** de contrainte maximale. Entre les deux grilles
fines, le percentile 95 des maxima par élément hors r < 25 mm change de
3,55 %, mais le déplacement change encore de **23,31 %**. La convergence
mécanique exigée n'est donc pas acquise.

Les grilles de 3 et 2 mm sont rejetées pour fragments déconnectés :
respectivement 17 et quatre cellules hors de la composante principale.
Aucune n'est éliminée pour faire passer un calcul. La grille de 1,8 mm est
connexe mais échoue au contrôle de volume de 6 %. Les trois grilles retenues
pour le raffinement sont intégralement connexes.

L'[analyseur](../../../twins/935-horizontal-cooling-system-f0/source/assess_mac_fea.py)
vérifie les empreintes, tous les nœuds, les huit points de Gauss de chaque
élément et toutes les réactions de l'alésage. Les forces et moments ferment
avec des erreurs relatives inférieures à 2 × 10⁻⁹ pour les trois matériaux
de la grille 1,5 mm, normalisées par les sommes des charges centrifuges en
valeur absolue. Une vérification indépendante retrouve les rapports de
contrainte proportionnels à la densité et de déplacement proportionnels
à densité/module d'Young, sous les hypothèses communes.

Le centre de masse de cette reconstruction se trouve à **2,53 mm supposés**
de l'axe. À 6 000 tr/min, le modèle rigide donne une force de balourd
conditionnelle d'environ **1,16 kN en aluminium**. Ce résultat peut provenir
des formes reconstruites, des fermetures ou du recalage ; il ne mesure pas le
balourd du ventilateur réel. Il faut résoudre son origine et prévoir un
équilibrage mesuré avant dimensionnement des appuis ou fabrication.

## Point CFD et suite des calculs

Le nouveau rotor fermé est placé dans le conduit carré hypothétique déjà
défini : 0,6 m³/s imposé, +6 000 tr/min, air à 1,15 kg/m³ et viscosité
cinématique 1,55 × 10⁻⁵ m²/s. OpenCFD v2406 ARM64 exécute MRF/k‑ω SST sur le
Mac. Le maillage passe `checkMesh` avec `Mesh OK.` et 500 itérations se terminent.

Sur les 100 dernières itérations, le déséquilibre massique maximal est
2,03 × 10⁻⁸ relatif. La pression totale moyenne vaut 155,5 Pa et le couple
résistant moyen 2,505 N·m, mais leurs variations crête à crête atteignent
**6,04 % et 1,74 %**. La dérive entre fenêtres de 100 itérations atteint
3,74 % et 1,01 %. Le seuil de stationnarité de 1 % est dépassé : **point rejeté**.
Ces valeurs décrivent une itération de calcul ; elles ne sont ni une courbe
935 acceptée ni des données d'apprentissage PhysicsNeMo.

La prochaine correction doit traiter la définition des surfaces et des appuis
du moyeu, la représentation mécanique des pales et les conditions du vrai
carter. Le raffinement CFD à trois maillages reste à effectuer après acceptation
du pilote ; un calcul transitoire devient pertinent si la configuration ne
permet pas un état stationnaire représentatif. Les variantes de pales ne
doivent pas être classées par un débit non convergé. Les engrenages, roulements,
retenues, joints et fixations du mécanisme restent soumis aux 17 interfaces
documentées et aux mesures manquantes.

## Reproduction

Conserver les anciens résultats et créer un nouveau dossier sous `work/`.
Les arguments de cas sont privés ; chaque cas donne les chemins et SHA-256 du
rotor et des sections, `purpose: hypothesis_screen`, `scale_verified: false`
et `scale_mm_per_source_unit: 1`. Les paramètres fluide figurent dans le cas
archivé. Le mode `fea-fields` demande aussi l'analyse FEA, les deux CSV, leurs
empreintes et leurs comptes de lignes ; il refuse une analyse déséquilibrée.

Avec Git, récupérer chacun des quatre dépôts dans un nouveau répertoire et
vérifier les révisions avant compilation :

```sh
python3 - <<'PY'
import json, pathlib, subprocess
pins = json.loads(pathlib.Path('twins/935-horizontal-cooling-system-f0/source/picogk-mac-study/libraries.lock.json').read_text())
root = pathlib.Path('work/PRIVATE/upstream')
root.mkdir(parents=True, exist_ok=False)
for item in pins['libraries']:
    path = root / item['directory']
    subprocess.run(['git', 'init', str(path)], check=True)
    subprocess.run(['git', '-C', str(path), 'remote', 'add', 'origin', item['repository']], check=True)
    subprocess.run(['git', '-C', str(path), 'fetch', '--depth', '1', 'origin', item['commit']], check=True)
    subprocess.run(['git', '-C', str(path), 'checkout', '--detach', 'FETCH_HEAD'], check=True)
    assert subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'], text=True).strip() == item['commit']
PY
dotnet build twins/935-horizontal-cooling-system-f0/source/picogk-mac-study/MacStudy935.csproj \
  -c Release -p:PicoGKAssembly=/PRIVATE/PicoGK.dll -p:UpstreamRoot="$PWD/work/PRIVATE/upstream"
# Utiliser la bibliothèque native osx-arm64 déjà qualifiée.
DYLD_LIBRARY_PATH=/PRIVATE/PicoGK/native/osx-arm64 dotnet \
  twins/935-horizontal-cooling-system-f0/source/picogk-mac-study/bin/Release/net9.0/MacStudy935.dll \
  witness work/PRIVATE/new-witness
# Répéter la même commande pour les modes roots, thickness, simulation et fea-fields,
# avec le cas privé avant le nouveau dossier de sortie.
python twins/935-horizontal-cooling-system-f0/source/assess_mac_fea.py \
  work/PRIVATE/prepared work/PRIVATE/solved work/PRIVATE/new-assessment
python -m unittest discover -s tests -p test_935_mac_picogk.py -v
make check
```

Les scripts existants `prepare_candidate_fea.py`, `run_candidate_fea.sh`,
`prepare_candidate_cfd.py`, `run_candidate_cfd.sh` et `assess_candidate_cfd.py`
restent réutilisés, sans changement. Les journaux et reçus privés gardent les
commandes et entrées exactes. Le logiciel et les essais sur hypothèses avancent ;
la compatibilité historique, la calibration, la qualification matière/procédé
et les essais physiques restent ouverts.
