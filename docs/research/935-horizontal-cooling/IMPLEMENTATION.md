# Reconstruction exécutée les 5 et 6 octobre 2026

Le coordinateur reconstruit des surfaces réellement acquises et produit des
zones de pales éditables, des exports PicoGK et une revue indépendante. **Le
rotor complet et le mécanisme ne sont pas encore reconstruits ou validés.**
Les anciens proxies restent exclus de cette référence. Le programme 993
vertical demeure distinct.

## État des étapes du plan

| Étape | Exécution et limite |
|---|---|
| 0 — Environnement | Accès Kali2, calculs Python, compilation .NET 9/PicoGK et exports FreeCAD vérifiés. Kali1 indisponible lors du contrôle. Aucune installation ou location. |
| 1 — Géométrie | Deux originaux contrôlés par SHA-256 ; transformations et inverses conservées. Neuf régions de pales détectées sans imposer un comptage. Sections périodiques, neuf plages contiguës, trois résolutions PicoGK et CAO éditable exécutées. Deux zones acquises du moyeu produisent désormais des surfaces analytiques ouvertes FreeCAD/STEP : cylindre intérieur et cône extérieur. Pieds, extrémités, moyeu solide et dos recalé restent à reconstruire. |
| 2 — Mécanisme | Les 17 interfaces et les chemins d'efforts existants sont réutilisés. Le scan extérieur de l'entraînement est préparé et ses bords enregistrés ; sa segmentation mécanique, ses axes et son assemblage restent ouverts. Aucun engrenage intérieur supposé. |
| 3 — Air | Aucun calcul de référence lancé : rotor entier, carter, jeux, repères/sens et conditions du pilote non qualifiés. |
| 4 — Mécanique | Aucun calcul de référence lancé : solides, liaisons, charges et propriétés correspondant au procédé non qualifiés. |
| 5 — Optimisation | Attend une référence calculée et les contraintes de montage. |
| 6 — PhysicsNeMo | Aucun entraînement : absence de jeu de calculs accepté. |
| 7 — Jumeau | Le graphe fonctionnel existant reste une base ; aucun assemblage complet SimReady livré. Le protocole de banc est rédigé. |

Les suffixes `0.5mm` et `0.21mm` désignent les précisions d'acquisition
déclarées par le propriétaire. Ils ne définissent ni les unités OBJ ni les
tolérances d'usinage. Les valeurs dimensionnelles de cette campagne restent
en unités source ou explicitement conditionnelles.

## Environnement effectivement utilisé

Kali2 : Linux sur ext4, 12 processeurs logiques, environ 16 Gio de RAM,
Python 3.14.7, NumPy 2.4.6, SciPy 1.17.1, trimesh 5.1.0,
PyMeshLab 2025.7.post1 et module Gmsh 4.15.2. CalculiX 2.23 répond ; son
option `-v` retourne 201, qui n'est pas un résultat de calcul mécanique.
Le .NET 6 de l'hôte ne suffit pas au programme `net9.0`.

L'image locale déjà installée est figée par son **identifiant d'image** :

```text
sha256:fd50c61399fd8b419b8f63b1eaf33dc5bfaeb5e8df5182ff68c3db45dc600c6a
```

Elle fournit SDK .NET 9.0.317, PicoGK Core 26.2.0 et FreeCAD 1.0.2.
Le runtime PicoGK annonce le build `2026-06-05 21:31:47 picogk`.
Sa bibliothèque native exige
`LD_LIBRARY_PATH=/opt/picogk-native/lib:/app`. FreeCAD utilise
`/opt/freecad/usr/bin/python`, `QT_QPA_PLATFORM=offscreen` et
`LD_LIBRARY_PATH=/opt/freecad/usr/lib`.
Le Python `/opt/geometry-qa/bin/python` contient USD 25.11 ; cela ne qualifie
pas un assemblage physique ou une installation Omniverse complète.

L'autre image de calcul déjà présente contient OpenFOAM 13 ; son identifiant
local est `sha256:49979f46f421459dae4bf21aaa898e2253b07301c3e5b2cabaa6eaf06f54d696`.
Après chargement de `/opt/openfoam13/etc/bashrc`, `foamRun -help` fonctionne.
Ce contrôle CLI n'est pas un calcul accepté. Cette distribution utilise
`momentumTransport`, avec `simulationType RAS` et `model kOmegaSST` pour le
modèle choisi. [Documentation OpenFOAM 13](https://doc.cfd.direct/openfoam/user-guide-v13/turbulence).

Le préflight distingue présence d'un paquet, import fonctionnel, chemin de
commande et véritable exécution. OpenMDAO et PhysicsNeMo ne sont pas installés
dans les environnements Python examinés. Aucun ancien verrou, recette figée
ou fichier de preuve n'est modifié pour cette campagne.

## Commandes reproductibles

Le [cas modèle](../../../twins/935-horizontal-cooling-system-f0/reconstruction-case.template.json)
contient des champs vides ; les coordonnées, fenêtres de sélection et chemins
réels sont renseignés dans une copie privée, après inspection du scan.

```sh
SOURCE=twins/935-horizontal-cooling-system-f0/source
python3 "$SOURCE/run_reconstruction.py" PRIVATE_CASE.json preflight work/NEW-preflight
python3 "$SOURCE/run_reconstruction.py" PRIVATE_CASE.json surfaces work/NEW-surfaces
```

`surfaces` réutilise les lecteurs et préparateurs du dépôt : retrait des seules
faces exactement nulles, pose d'inspection PCA réversible, puis ajustement de
cylindres observés. La PCA ne fournit pas les axes mécaniques. Le reçu garde
chaque face sélectionnée, l'axe ajusté et l'écart entre les deux axes candidats.
Tous les contours de bord et fragments restent disponibles.

Les coupes radiales sont ordonnées puis ajustées par spline périodique SciPy.
Une lacune courte peut être interpolée dans la limite explicitement fournie
et chaque lien est enregistré. Une coupe ouverte, branchée ou insuffisante
est rejetée. **Une coupe rejetée sépare les plages de loft.** Cette règle a
retiré deux interpolations trop longues détectées par la carte d'écarts.
Les bouchons des plages sont des limites artificielles, pas des pieds ou
extrémités mesurés. Les courbes et ces étiquettes restent dans `sections.json`.

Compiler le programme C# dans l'image locale, avec des sorties privées :

```sh
IMAGE=sha256:fd50c61399fd8b419b8f63b1eaf33dc5bfaeb5e8df5182ff68c3db45dc600c6a
docker run --rm --pull=never --user "$(id -u):$(id -g)" \
  -v "$PRIVATE_ROOT:/data" --entrypoint /usr/share/dotnet/dotnet "$IMAGE" \
  build /data/repo/twins/935-horizontal-cooling-system-f0/source/picogk-section-loft/SectionLoft.csproj \
  -p:PicoGKAssembly=/app/PicoGK.dll \
  -p:BaseIntermediateOutputPath=/data/PRIVATE-obj/ -o /data/PRIVATE-bin
```

Le projet compile uniquement `Program.cs` ; les anciens dossiers `obj` ne
peuvent pas introduire des attributs d'assemblage en double.
Renseigner ensuite les empreintes des sections et du DLL, la racine privée,
l'identifiant d'image et le facteur **hypothétique** mm/unité source.

```sh
python3 "$SOURCE/run_reconstruction.py" PRIVATE-080.json picogk work/NEW-080
python3 "$SOURCE/run_reconstruction.py" PRIVATE-040.json picogk work/NEW-040
python3 "$SOURCE/run_reconstruction.py" PRIVATE-020.json picogk work/NEW-020
python3 "$SOURCE/run_reconstruction.py" PRIVATE-020.json cad work/NEW-cad
python3 "$SOURCE/run_reconstruction.py" PRIVATE-REVIEW.json review work/NEW-review
python3 -m unittest discover -s tests -p test_935_scan_reconstruction.py -v
make check
```

Les trois cas PicoGK doivent partager les mêmes sections et la même échelle
conditionnelle ; leurs résolutions sont divisées par deux. Le cas de revue
référence les trois dossiers `artifacts` et les SHA-256 de leurs reçus.
L'étape `cad` crée des lofts BRep réglés à partir des contours échantillonnés,
dans FreeCAD natif et STEP ; elle rouvre les fichiers et contrôle le volume.
Elle ne transforme pas les voxels en interfaces usinées analytiques.

### Surfaces analytiques observées du moyeu

L'étape `hub` reprend les faces des ajustements candidats existants. Une
fenêtre axiale et une limite sur la composante axiale des normales, inspectées
et conservées dans le cas privé, isolent chaque plage des transitions et
fragments. Aucune face du scan original n'est supprimée. Les faces sélectionnées
et exclues, les deux modèles et leurs paramètres sont enregistrés.

```sh
python3 "$SOURCE/run_reconstruction.py" PRIVATE-HUB.json hub work/NEW-hub
python3 "$SOURCE/run_reconstruction.py" PRIVATE-HUB-CAD.json cad-hub work/NEW-hub-cad
```

Le cas `hub` référence `sections.json`, son empreinte et celle du reçu de
surfaces ; il renseigne `hub_surface_selections`, `hub_normal_weight` et
`hub_robust_scale_source_units`. Le cas `cad-hub` référence ensuite le nouveau
`hub-surfaces.json` et son empreinte, avec la même image FreeCAD qualifiée et
une échelle explicitement conditionnelle.

Un secteur angulaire de 10° sur quatre est réservé dans le repère initial
commun aux deux ajustements. SciPy ajuste un cylindre puis un cône avec
distances et normales, sur les autres secteurs. Le cône est retenu uniquement
si RMS **et** percentile 95 s'améliorent sur les secteurs réservés. La distance
est normale à la surface analytique infinie ; elle exclut les bords de coupe.
Ce partage sert à la sélection exploratoire de modèles dans le même scan.
Il ne fournit ni une mesure indépendante ni une validation dimensionnelle.

Sur les deux plages inspectées, le cylindre intérieur est conservé et le cône
extérieur réduit le RMS d'environ **34 %** et le percentile 95 d'environ
**29 %** par rapport au cylindre. Un ajustement conique global incluant les
transitions n'améliorait pas les deux critères ; il reste conservé comme
diagnostic rejeté. Les axes candidats demeurent distincts, sans coaxialité
imposée ni identité de portée fonctionnelle déclarée.

FreeCAD produit deux faces BRep analytiques latérales ouvertes, avec les
interpolations angulaires explicitement étiquetées. Aucun bouchon ni solide
complet n'est exporté. Le STEP relu conserve leur aire ; les fichiers natifs
se rouvrent. Une tessellation du **STEP effectivement exporté**, superposée au
scan dans quatre vues privées, contrôle le transfert des repères. Les bornes
des surfaces sont des limites d'acquisition, pas des faces usinées mesurées.
Les deux composantes topologiques du rotor sont également inventoriées :
elles ne définissent pas deux pièces, et la petite composante ne correspond
pas au dos entier. Aucune registration arbitraire du dos n'est appliquée.

Le coordinateur refuse un dossier existant. Chaque étape publie son reçu
avant de continuer. En cas d'échec, les sorties partielles et `failure.json`
sont conservés. Pour reprendre, réutiliser les entrées vérifiées et choisir un
nouveau dossier ; aucune reprise ne remplace une tentative précédente.
Les étapes CFD, FEA, optimisation et entraînement ne sont pas simulées par
des reçus vides : leur demande est rejetée tant qu'elles ne sont pas implémentées.

## Premier jalon géométrique obtenu, avec réserves

Le dossier privé contient quatre vues superposées scan/lofts, les sections des
neuf pales, les coupes cylindriques du moyeu, les écarts bidirectionnels et la
localisation de tous les bords non résolus. Il conserve également les coupes
rejetées et les éventuelles interpolations. Les fichiers source sont inchangés.

La revue indépendante utilise 18 000 points tirés selon l'aire, comparés aux
**triangles**, dans les deux directions, avec graines et points sauvegardés.
Elle exclut une marge autour des bouchons artificiels. Des écarts élevés
subsistent ; le percentile 95 seul ne clôt donc pas la fidélité géométrique.
Les distances non calibrées ne sont pas comparées à une tolérance en mm.

Les neuf plages fermées présentent zéro face auto-intersectée, zéro face
incidente à une arête non-manifold et zéro sommet non-manifold dans l'audit
MeshLab. Pour la discrétisation de **ces seules plages**, les deux résolutions
finales donnent **0,1204 %** de variation du volume et **0,1412 %** pour la
plus grande variation des inerties principales. L'inertie est transportée à
l'origine du repère candidat, pas laissée au centre de masse.
Ces résultats ne donnent ni la masse du rotor entier ni sa résistance.

Les tentatives rejetées sont conservées : fermeture Poisson et proxy visuel
historiques ; lofts traversant des coupes manquantes ; seconde interpolation
B-spline FreeCAD donnant un BRep invalide. La version retenue utilise les
contours échantillonnés sans seconde interpolation. Aucun ancien reçu n'est
réécrit pour présenter ces tentatives comme acceptées.

## Suite, dépendances et critères d'acceptation

Le [contrat indépendant des 17 interfaces](../../../twins/935-horizontal-cooling-system-f0/interface-contract.json)
et la [matrice des entrées existante](../../../twins/935-horizontal-cooling-system/data/input-matrix.json)
restent les références. La recherche consolidée distingue variante historique,
kit commercial, données génériques et données du spécimen. Un scan extérieur
ne fournit pas les dentures, références de roulements, précharges ou joints.

1. Terminer les régions du rotor et segmenter l'entraînement ; classer les
   acquisitions du dos avant une registration rigide justifiée. Obtenir deux
   cotes indépendantes par scan pour calibrer, avec incertitude et provenance.
   Reconstruire les portées, axes et faces usinées en analytique/BRep ; fermer
   les surfaces manquantes seulement avec une preuve ou une interpolation
   explicitement localisée. Convergence volume/inertie < 1 % ne remplace pas
   l'écart au scan ni la mesure des interfaces.
2. Établir axes, sens vus, rapports signés, retenues, jeux et chemins d'efforts.
   Identifier les composants internes avant calcul détaillé ; contrôler
   interférences sur un tour complet et aux températures définies.
3. Préparer un pilote OpenFOAM MRF, k–ω SST, régime/air/stations de pression
   explicités ; aucune valeur de débit imposée n'est un débit prédit. Trois
   maillages, qualité sans erreur bloquante, déséquilibre massique < 0,1 %,
   variation finale des moyennes < 1 %, différence des deux maillages fins
   < 3 %. Employer ensuite un calcul transitoire pour les interactions
   rotor/carter. Le réseau moteur n'est ajouté qu'avec ses passages/résistances.
4. Gmsh/CalculiX : centrifuge, pression issue de CFD, transmission, contacts
   et thermique disponible. Vérifier équilibre et calculs analytiques,
   convergence contraintes non singulières/déplacements < 5 % et fréquences
   précontraintes < 2 %. AlSi10Mg, WE43 et Ti64 restent les trois premières
   cartes ; la carte WE43 générique existante est un substitut corroyé,
   insuffisant pour une limite LPBF. Fatigue ou propriété manquante : conclusion
   correspondante impossible, sans valeur inventée.
5. SciPy optimise avec les solveurs de référence ; OpenMDAO coordonne une fois
   ces appels disponibles. Aucune dérivée automatique à travers PicoGK.
   Conserver les interfaces et comparer air utile à puissance comparable,
   masse et inertie dans les mêmes conditions.
6. PhysicsNeMo 2.2.1, [FullyConnected](https://raw.githubusercontent.com/NVIDIA/physicsnemo/v2.2.1/physicsnemo/models/mlp/fully_connected.py) : pression et couple depuis paramètres
   et conditions. Séparer les géométries entières entre entraînement/test,
   déclarer la normalisation et obtenir erreur normalisée < 5 % sur chacun
   des deux résultats. Interdire l'extrapolation ; recalculer les candidats
   retenus avec les solveurs. Un échec du modèle ne bloque pas les solveurs.
7. Composer les pièces et liaisons en USD SI avec conversions contrôlées,
   résultats et empreintes. Livrer nomenclature, plans et comparaison seulement
   quand leurs entrées sont établies. Le [protocole de banc](BENCH_PROTOCOL.md)
   couvre régime, couple, débit, pression, vibrations, température et huile.

Les seuils ci-dessus qualifient les calculs. Les vitesses admissibles, limites
de résistance, fatigue et équilibrage viennent des données des pièces et de
la revue mécanique. **Aucune validation physique ni autorisation de fabrication.**

Les scans, leurs dérivés et les paramètres permettant de les reconstruire
restent privés sous `work/`. Git reçoit uniquement les programmes, tests,
documentation et synthèses compatibles avec les droits disponibles. Le rapport
privé conserve versions, empreintes, transformations, états et limitations.

## Vérification logicielle et sauvegarde

Les huit tests ciblés passent avec les dépendances scientifiques de Kali2 :
axe synthétique incliné, lacunes locales, spline périodique, séparation des
lofts aux coupes absentes, protections des empreintes/sorties, lois d'échelle
du volume/inertie et conservation des échecs lors d'une reprise. Le nouveau
test récupère un cylindre et un cône synthétiques inclinés sur des secteurs
réservés disjoints ; il refuse les échelles de calcul non finies et un partage
angulaire insuffisant.
Compilation native C# : zéro erreur, zéro avertissement. CAO FreeCAD et STEP
rouverts ; trois runs PicoGK et revues indépendantes exécutés.

`make check` passe sur une copie ext4 des fichiers effectivement suivis par
Git, avec `PYTHONNOUSERSITE=1` et `umask 022` : suite découverte de 3 554 tests
lors de la continuation du 6 octobre,
dont 181 ignorés pour dépendances optionnelles, puis contrôles complémentaires
du Makefile. Le test ciblé est exécuté séparément avec SciPy/trimesh disponibles.
Cette séparation évite les bindings OCP personnels incompatibles de l'hôte.
Le premier contrôle du 6 octobre a détecté un import de trimesh inutile au
chargement du nouveau test. Cet import est désormais limité à la lecture du
scan ; le test analytique utilise NumPy/SciPy. L'échec et le log final accepté
sont conservés séparément. Les paramètres géométriques avant/après ce correctif
sont identiques octet par octet.
L'archive de contrôle conserve les fichiers suivis même si leur chemin est
ignoré par défaut ; les métadonnées AppleDouble de transfert sont retirées de
cette seule copie de contrôle. Aucun fichier métier n'est modifié pour faire
passer les contrôles. Le contrôle documentaire trouve zéro lien cassé dans
804 fichiers Markdown ; `git diff --check` passe.

Les 80 fichiers privés de surfaces, exports et revues sont copiés sur Mac et
Kali2 avec comparaison de toutes les empreintes. Les deux scans originaux
gardent leurs SHA-256. Les logs, reçus et tentatives précédentes sont conservés.
Aucune dépense Vast et aucune validation physique dans cette campagne.

Les [archives GitHub privées](https://github.com/cluster2600/porscheparts-935-private)
conservent les deux originaux, tous les résultats scientifiques et tentatives
antérieures, paramètres, CAO, maillages et logs. La capture du 5 octobre est
publiée dans [sa release d'archive](https://github.com/cluster2600/porscheparts-935-private/releases/tag/reconstruction-20261005) ;
la continuation du moyeu dispose d'une
[capture séparée](https://github.com/cluster2600/porscheparts-935-private/releases/tag/hub-surfaces-20261006).
Les manifestes donnent les empreintes par fichier et par archive. Les
empreintes SHA-256 retournées par GitHub sont comparées aux archives locales
après publication. Les copies intégrales du dépôt public sont exclues des
archives de résultats puisqu'elles sont déjà dans Git ; le commit des sources
et leurs instantanés sont conservés. Ces archives ne constituent pas une
qualification de fabrication. Le code et les synthèses demeurent dans
[la PR publique #132](https://github.com/cluster2600/porscheparts/pull/132).
