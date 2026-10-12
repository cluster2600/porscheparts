# Domaine fluide idéalisé du compresseur

Ce générateur construit un **candidat de domaine numérique scellé**, distinct
de l'assemblage réel à 39 pièces. Il utilise le carter final F0/F1 et les trois
obstacles rotatifs F0 identifiés par leurs SHA-256. Il ne produit aucun résultat
CFD et ne déclare pas le domaine prêt pour un solveur.

La géométrie source est fixée au comparatif F0/F1 à 0,50 mm ; le domaine est
revoxelisé à **0,25 mm** depuis l'essai 005. Les paramètres de carter
doivent correspondre exactement à cette étude. F1 accepte la loi de volute
`radius_linear` ou `area_affine`, le profil `conical` ou `wheel_shroud`, avec un
jeu radial de profil fixé à **1,5 mm**. La régularisation du carter est finie,
entre **0,5 et 1 mm**, sans dépasser le quart de l'épaisseur ; les fichiers
de paramètres de l'étude utilisent **0,5 mm**. Ces quatre champs d'étude sont
absents pour F0 et obligatoires ensemble pour F1. Une configuration différente est refusée,
ainsi que les paramètres inconnus, manquants ou dupliqués.

## Construction et frontières

1. Importer `housing.stl` et `flow-domain.stl`, après comparaison de leurs
   empreintes et nombres de triangles avec le rapport du carter.
2. Dilater le domaine nominal de **1 mm**, pour constituer un masque assez
   large pour atteindre les surfaces internes du carter régularisé.
3. Ajouter le prolongement de sortie : cylindre de rayon **14 mm**, axe Y,
   centre transverse `(49, 0)` en X/Z, de **Y = 40 à Y = 81 mm** avant lissage.
   La coupe finale à Y = 80 mm intervient seulement après régularisation.
4. Soustraire une fermeture arrière idéale de rayon **35,5 mm**, sous
   **Z = −3,75 mm**. L'entrée reste prolongée au-delà du futur plan Z = 44 mm.
5. Soustraire **après l'ajout de la sortie** le carter final importé, puis
   l'union de la roue de compresseur, de l'arbre et de l'écrou F0.
6. Régulariser le volume fluide avec `Smoothen(0.125 mm)` puis appliquer les
   plans d'entrée Z = 44 et de sortie Y = 80. Cette dernière coupe est limitée
   à un cylindre de rayon 16 mm entourant le prolongement de sortie ; elle ne
   traverse pas la volute.

Le masque nominal dilaté n'est pas une définition autorisée de paroi interne.
L'inspection indépendante doit démontrer que la frontière fluide suit le carter
final ou les obstacles, sauf aux surfaces idéalisées explicitement créées :
fermeture arrière, entrée et prolongement de sortie. Si le masque limite ailleurs
le fluide, le domaine doit être rejeté. Les STL d'entrée exacts et le masque
dilaté sont exportés pour permettre cette comparaison.

La régularisation finale de 0,125 mm peut déplacer la frontière fluide ; son
volume avant et après traitement est consigné. Les plans de coupe finaux
sont définis exactement dans les champs implicites ; leur position dans les
triangles exportés reste à vérifier. La réimportation des STL dans le noyau à
0,25 mm peut également déplacer leurs surfaces. Le contrôle de proximité actuel
refuse les centroïdes des faces physiques distants de plus de **0,65 mm** du
carter ou du rotor source. Il ne borne pas la distance de tous les points des
triangles ; cette limite doit être levée avant un classement. Une distance
nominale ne constitue pas une mesure de jeu.

Les champs de volume issus de `PicoGK.CalculateProperties` sont des diagnostics
du noyau. Ils ne sont pas équivalents au volume net signé du STL, qui inclut les
enveloppes orientées des obstacles : pour la référence 003, ces valeurs sont
respectivement **261 762,52 mm³** et **231 942,59 mm³**. L'inspection indépendante
doit conserver cette distinction et utiliser le volume net signé pour décrire
le domaine fluide exporté.

Le premier domaine a été rejeté pour une poche arrière de 61,12 mm³, de petits
îlots près de R34 et Z−8, et huit facettes dégénérées au raccord arrière. Le
rayon de fermeture passe donc de 34 à 35,5 mm pour englober la lèvre du masque.
Les sources de cet essai sont conservées dans
`work/bionic-f1-20261011/fluid-001-source`. Aucun triangle n'est réparé ou
supprimé. Un écrêtage global de la sortie autour de Y42 n'est pas ajouté : cette
région recoupe la volute, qui doit rester entière.

L'essai 003 passe les premiers contrôles de fermeture des surfaces, mais 482 faces de référence restent hors des
frontières admissibles près du bord d'entrée Z = 44 mm. Lisser un volume déjà
coupé arrondit ce bord ; une seconde coupe ne restitue pas la surface retirée.
L'essai 004 reporte donc la coupe d'entrée après le lissage et prolonge la sortie
jusqu'à Y = 81 mm avant sa coupe finale à Y = 80 mm. Ses sources précédentes sont
conservées dans `work/bionic-f1-20261011/fluid-003-source`. Les critères de
topologie et de proximité de 0,65 mm restent identiques pour l'inspection 004.

Cette inspection conserve huit triangles hors du critère de proximité,
identiques sur la référence et la variante volute. Chacun relie deux sommets
du cap Z44 à un sommet de paroi Z43,8. Leur distance au centroïde vaut
0,665–0,671 mm ; le sommet de paroi est à 0,254–0,268 mm du carter source.
La préparation 005 les traite explicitement comme un **raccord numérique
d'entrée** : deux sommets sur Z44, troisième dans Z43,5..44 et R21..22,5,
rayons de tous les sommets ≤22,5 mm, arêtes ≤1,5 mm et distance du centroïde
au carter ≤0,75 mm. Les parois hors de ce raccord restent soumises à 0,65 mm.
Le rapport compte les faces, leur aire et leur écart maximal. Aucun triangle
n'est déplacé ou supprimé. Cette admission sert uniquement au pilote ; la
sensibilité aux raccords d'entrée reste à qualifier avant un classement.

Le [diagnostic indépendant ultérieur](../evidence/fluid-004-topology-diagnostic.json)
**révoque l'admission du domaine 004 pour la CFD** : sa revoxelisation
à 0,5 mm fusionne la roue et l'écrou, pourtant séparés d'au moins 0,499 mm
selon leurs plans extrêmes Z. L'union du rotor crée cinq anses ; la frontière
fluide en présente 29. Une surface fermée et orientée ne suffisait donc pas.
Le nouveau contrôle exige une enveloppe extérieure d'Euler 2 et deux obstacles
intérieurs distincts d'Euler 0 chacun, correspondant aux alésages de la roue
et de l'écrou. Cette attente vient des sources séparées, pas du résultat à accepter.

L'essai 005 réduit le voxel fluide à 0,25 mm et la régularisation à 0,125 mm,
en gardant les STL sources et les fermetures. Il retrouve les trois solides
séparés du rotor, mais huit facettes exactement dégénérées et quatre petites
coquilles de volume nul font rejeter le fluide. L'essai 006 applique le même
décalage de grille `(0,173 ; 0,119 ; 0,071)` mm que le générateur de carter :
imports, champs, bornes et sondes sont transformés ensemble, puis les exports
reviennent au repère initial. Les deux domaines 006 passent les contrôles
stricts des triangles et des trois coquilles attendues ; aucun triangle n'est
retiré. Les domaines précédents et
leurs reçus restent conservés comme essais rejetés. Le passage arrière du
STL 004 mesure environ 0,634 mm au minimum des 720 rayons examinés ; ce minimum
échantillonné ne démontre ni le minimum global ni sa résolution hydrodynamique.

La préparation des frontières 008 est ensuite rejetée par le
[contrôle indépendant du joint arrière](../evidence/rotor-label-diagnostic-008.json) :
près de l'arbre, comparer seulement les distances au rotor et au carter
attribuait des faces fixes au rotor. La préparation 009 compare aussi la
distance à la fermeture cylindrique fixe, sans immobiliser l'arbre voisin.
Elle réserve les labels d'entrée/sortie aux triangles coplanaires à 10⁻⁶ mm
près ; les facettes du bord presque coplanaires restent des parois. Ce seuil
correspond au contrôle des ports du préparateur CFD. Les triangles et leurs
coordonnées sont conservés intégralement.

## Exécution

```sh
dotnet build twins/bionic-turbo-f1/cfd-geometry/CfdGeometry.csproj -c Release
dotnet twins/bionic-turbo-f1/cfd-geometry/bin/Release/net9.0/CfdGeometry.dll --self-test
dotnet twins/bionic-turbo-f1/cfd-geometry/bin/Release/net9.0/CfdGeometry.dll \
  HOUSING_RUN F0_ASSEMBLY_RUN NEW_OUTPUT_DIR
```

`HOUSING_RUN` contient les deux STL et `report.json` ; `F0_ASSEMBLY_RUN` contient
`compressor-wheel.stl`, `shaft.stl`, `compressor-nut.stl` et son `report.json`.
Les empreintes des obstacles doivent aussi correspondre aux trois empreintes F0
épinglées dans le générateur. Le dossier de sortie doit être neuf. Une erreur
après sa création conserve les fichiers déjà produits et écrit `FAILED.json`.

L'exécution native doit être enveloppée par le verrou machine
`parts/picogk-catalog/tools/run_part.py`, comme l'assemblage F0 ; aucun autre
processus PicoGK natif ne doit tourner simultanément. La compilation et
`--self-test` ne lancent pas de géométrie native.

Les principaux exports sont `fluid.stl`, `rotor-union.stl`, `housing-final.stl`,
`nominal-mask.stl`, `rear-seal.stl` et `outlet-extension.stl`. Les autres copies
STL et les deux rapports d'entrée conservent les sources nécessaires à l'audit.
`report.json` consigne les empreintes, paramètres, volumes, limites et sondes
natives. La sonde `(15, 0, 40)` doit être dans le fluide ; elle ne prouve pas à
elle seule que toutes les régions fluides sont connectées.

L'union du rotor doit conserver les jeux hypothétiques entre ses trois pièces :
trois enveloppes solides distinctes sont attendues ici. L'inspection du fluide doit
interpréter correctement les surfaces orientées des obstacles et identifier les
composantes fluides ; elle ne doit ni supprimer de triangles ni relier les
obstacles artificiellement pour faire passer un test.

Il reste à vérifier les maillages, leur topologie, la proximité aux surfaces
sources, l'absence de frontières parasites et le classement exhaustif des faces
en entrée, sortie, rotor et paroi fixe. Ces contrôles précèdent toute préparation
de maillage volumique ou déclaration de résultat CFD.
