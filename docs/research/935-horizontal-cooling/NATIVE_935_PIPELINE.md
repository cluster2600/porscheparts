# Assemblage 935 en PicoGK et essai Qwen — 12 octobre 2026

La chaîne géométrique active vise exclusivement le système horizontal de la
935 historique. Elle construit le rotor depuis **neuf pales observées
individuellement**, conserve le scan de l'entraînement et ajoute une admission
avec enveloppe de distribution vers deux banques de trois cylindres.
Les sources C# et les paramètres JSON privés sont éditables.

Le moteur complet 935 n'est pas scanné dans les données retrouvées. Son carter,
ses six cylindres à ailettes et ses six culasses sont donc **13 enveloppes de
positionnement hypothétiques**, sans interfaces ni matière reconstruite.
Le compte de six cylindres est documenté pour la 935 K3 par
[Porsche](https://www.porsche.com/stories/culture/8-porsche-race-cars-that-made-le-mans-history/).
Il ne fixe ni la variante de notre spécimen ni ses dimensions. Aucun scan de
moteur 917 ni programme d'adaptation 993 n'alimente cette scène.

## Géométrie effectivement produite

| Élément | Construction | Statut |
|---|---|---|
| Neuf pales | Contours issus du scan, recalage des sommets entre sections, lofts `PicoGK.Mesh`, puis voxels natifs | Profils ajustés sur les acquisitions ; chaque pale conserve ses propres contours |
| Pieds et extrémités absents | Extrapolation constante du contour disponible le plus proche | Surfaces conçues sous hypothèse |
| Moyeu, dos et alésage | Champs implicites et opérations booléennes PicoGK | Rayons ajustés sur des secteurs observés ; épaisseurs, portée et fermeture non qualifiées |
| Entraînement | Import `PicoGK.Mesh` et transformation rigide du scan ouvert | Tous les triangles observés conservés ; organes cachés et datums non résolus |
| Enveloppes moteur | `PicoGK.Lattice` et champs implicites | Architecture six cylindres ; dimensions et pose hypothétiques |
| Admission et plénum | Coque implicite ouverte, distribution vers les deux banques et passage de l'entraînement | Géométrie provisoire ; sorties, étanchéité et fixations historiques inconnues |

[prepare_native_sections.py](../../../twins/935-horizontal-cooling-system-f0/source/prepare_native_sections.py)
réutilise le recalage de contours existant, séparément pour chacune des neuf
pales. Le registre privé conserve, section par section, les profils acquis
ajustés, les interpolations et les extrapolations. Python prépare les données
numériques ; aucune opération de CAO FreeCAD/build123d n'est appelée dans
cette chaîne. Le
[loft C# existant](../../../twins/935-horizontal-cooling-system-f0/source/picogk-section-loft/Program.cs)
et le nouvel
[assembleur C#](../../../twins/935-horizontal-cooling-system-f0/source/picogk-935-assembly/Program.cs)
créent toutes les surfaces et solides reconstruits dans PicoGK.

Le noyau produit 8, 14 et 30 triangles d'aire exactement nulle aux résolutions
rotor de 1,2, 0,6 et 0,3 unité supposée mm. L'assembleur les retire avec l'API
Mesh native, conserve les sorties non filtrées et limite explicitement ce
retrait. Un contrôle indépendant compare tous les triangles retenus :
coordonnées et ordre inchangés. Aucun triangle d'aire positive n'est supprimé.
Le rotor et le carénage finaux sont chacun une composante fermée, orientée
de façon cohérente et sans triangle d'aire nulle. Cette fermeture ne prouve
ni l'absence de toute auto-intersection ni la conformité au spécimen.

Les premières variantes périodiques et les tentatives échouées restent
archivées. Le moteur 917 de la
[scène précédente](INSPECTION_ASSEMBLY.md) reste un ancien contexte comparatif
exclu de la reconstruction active de la 935.

## Mesures numériques et limites observées

Trois grilles rotor successives, **1,2 → 0,6 → 0,3**, sont calculées avec le
même loft analytique en entrée. L'intégration indépendante des triangles
donne entre les deux grilles fines **0,073 %** de variation du volume et
**0,116 %** du tenseur d'inertie autour de l'origine de l'axe. Le volume fin
est **434 062 unités source³**, conditionnellement 434 062 mm³ sous H-SCALE.
Ces chiffres caractérisent cette reconstruction et ses fermetures hypothétiques.
Ils ne fournissent pas une masse physique sans calibration et densité qualifiée.

La comparaison bidirectionnelle utilise des points uniformément répartis en
aire et leur distance aux triangles. Elle se limite aux intervalles radiaux
acquis de chaque pale, avec une garde de deux unités aux coupes. Tous les
échantillons et les valeurs extrêmes sont conservés. Les pieds, extrémités et
le moyeu extrapolés sont exclus de cette comparaison des zones acquises.
Les RMS scan → candidat vont de **0,035 à 0,350 unité source** ; les percentiles
95 % vont de **0,065 à 0,131**. Dans le sens inverse, les pales 03 et 05
présentent encore des RMS de **1,93 et 2,48** : des surfaces du loft n'ont pas
une acquisition proche correspondante. Il faut classifier ces lacunes et
vérifier localement les contours avant de qualifier une réplique exacte.
Les résultats ne sont pas convertis en tolérances d'usinage ou en précision
de fabrication. Aucun filtrage des grands écarts ne transforme le verdict.

L'assemblage d'inspection utilise une grille de 0,8 pour contenir le coût des
enveloppes moteur ; le rotor fin de 0,3 est livré séparément. Les GLB et USD
conservent tous les triangles de leurs quatre groupes, avec conversion
contrôlée de l'unité supposée mm vers le mètre. Ils n'attribuent aucune liaison
physique, densité ou fixation non documentée.

Le carénage initial intersectait l'entraînement observé. Une découpe PicoGK
supprime ces contacts de surface à la pose étudiée. Ce passage reste ouvert :
son joint, ses pertes d'air et sa conformité historique restent à définir.
L'entraînement traverse aussi le sommet de l'enveloppe hypothétique de carter
moteur. Ce recoupement est conservé et signalé : il faut la géométrie réelle
de la 935 pour résoudre ce montage. Les contrôles portent sur des surfaces
observées et des enveloppes ; les volumes intérieurs inconnus, la dilatation,
la déformation et la dynamique du mécanisme ne sont pas validés.

## Qwen réellement testé

[test_qwen_935.py](../../../twins/935-horizontal-cooling-system-f0/source/test_qwen_935.py)
exécute localement **Qwen2.5-Coder-1.5B-Instruct 4 bits**, révision
`b3252a2f97102b1fb1571fec2c9b27219a8536be`, avec MLX-LM 0.31.3. Il compare
le modèle de base et l'adaptateur existant `coding-003/checkpoint-600`.
Les poids sont vérifiés avant et après ; un verrou évite de perturber un
entraînement actif. Aucun entraînement ni remplacement du modèle par défaut
n'est effectué.

Les cinq cas sont déclarés avant l'inférence : architecture 935/917, unité du
scan, interface partiellement observée, matière inconnue et six positions
hypothétiques prescrites. Température 0, graine 42, limite de 512 jetons.
Le score exige le JSON exact, y compris les types et l'absence de clés dupliquées.

| Modèle | Réponses brutes conformes | Échecs déterminants |
|---|---:|---|
| Base | 0/5 | JSON encadré de Markdown ; architecture proposée à une banque de six |
| Avec adaptateur | 3/5 | Architecture erronée ; coordonnées dupliquées et préfixe Python |

Une réponse du modèle de base contient les six coordonnées prescrites
correctes. Une **étape d'import distincte** retire uniquement sa balise JSON
Markdown complète ; le
[validateur](../../../twins/935-horizontal-cooling-system-f0/source/accept_935_centres.py)
exige ensuite l'égalité avec la définition indépendante. Le C# vérifie à
nouveau les six positions. Cette proposition alimente seulement les
enveloppes moteur hypothétiques ; elle n'infère aucune cote historique.
Le score brut reste 0/5 et le rapport original n'est pas réécrit.

Le petit modèle testé ne peut pas décider de l'architecture, d'une interface
mécanique ou d'une qualification de matière. Sa sortie reste une proposition
à contrôler. Cette conclusion ne mesure pas les performances d'autres
tailles ou versions de Qwen. Aucun code généré par le modèle n'est exécuté.

## Reproduction et conservation

Réutiliser .NET 9, PicoGK 2.3/Core 26.2.0 et les runtimes numériques déjà
installés. Aucun logiciel supplémentaire ni machine Vast n'a été acheté.
Les cas exécutés, sections, paramètres, matrices réversibles et empreintes
sont dans l'[archive privée](https://github.com/cluster2600/porscheparts-935-private/releases/tag/native-six-20261012).
Le [reçu public](native-six-20261012.json) conserve seulement les résultats
et références compatibles avec le dépôt public.

```sh
python twins/935-horizontal-cooling-system-f0/source/prepare_native_sections.py \
  work/PRIVATE/prepare-individual-case.json work/PRIVATE/new-sections
dotnet /PRIVATE/SectionLoft.dll \
  work/PRIVATE/new-sections/sections.json SECTIONS_SHA256 1 0.8 work/PRIVATE/new-lofts
dotnet build twins/935-horizontal-cooling-system-f0/source/picogk-935-assembly/Assembly935.csproj \
  -c Release -p:PicoGKAssembly=/PRIVATE/PicoGK.dll
# Rendre la bibliothèque native officielle accessible au chargeur du système.
dotnet twins/935-horizontal-cooling-system-f0/source/picogk-935-assembly/bin/Release/net9.0/Assembly935.dll \
  work/PRIVATE/individual-assembly.json CASE_SHA256 work/PRIVATE/new-assembly
python twins/935-horizontal-cooling-system-f0/source/export_inspection_assembly.py \
  work/PRIVATE/new-assembly work/PRIVATE/new-exports
python twins/935-horizontal-cooling-system-f0/source/render_935_native.py \
  work/PRIVATE/new-assembly work/PRIVATE/new-exports work/PRIVATE/new-review
python twins/935-horizontal-cooling-system-f0/source/test_qwen_935.py \
  /PRIVATE/existing-m64-qwen-runtime work/PRIVATE/new-qwen-test
python twins/935-horizontal-cooling-system-f0/source/accept_935_centres.py \
  work/PRIVATE/new-qwen-test/responses.json work/PRIVATE/new-validated-centres.json
python -m unittest discover -s tests -p test_935_native_qwen.py -v
make check
```

Le cas d'assemblage impose `target: 935`, six cylindres, `scale_verified: false`,
des hypothèses explicites, les empreintes des pales natives et de la proposition
de positions contrôlée, un seul import d'entraînement et une pose rigide.
Le cas de préparation reprend le schéma existant avec `profile_stride: 1`.
Le mode `rotor_only` sert aux trois grilles ; le mode `assembly` reste borné
à une grille de 0,8 ou plus. Les sorties doivent être nouvelles sous `work/`
ignoré. Les cas altérés sont refusés avant création de géométrie.

Les prochaines corrections concernent la couverture des pales 03/05,
l'identification du carter 935 et de ses fixations, la calibration indépendante
des deux scans et la définition du guide historique. Les anciens résultats
CFD/FEA restent attachés à leurs anciennes géométries : ils ne qualifient pas
ce nouveau rotor. La dynamique, l'aérodynamique de ce carénage et les essais
physiques restent ouverts. Aucune autorisation de fabrication n'est donnée.
