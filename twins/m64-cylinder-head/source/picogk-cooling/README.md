# Domaines géométriques PicoGK à partir de la culasse

Ce module exploite le runtime PicoGK existant pour préparer des **champs
volumiques de travail**, sans modifier le master ni sa forme extérieure.
Ce n'est ni un solveur thermique ni une nouvelle pièce imprimable.

## Opérations réellement exécutées

1. Lecture du STL en millimètres explicites, sans déplacement, mise à l'échelle
   ou lissage. L'hypothèse `1 unité du scan = 1 mm` reste non certifiée.
2. Construction d'une boîte à distance signée analytique entourant le maillage,
   avec une marge exploratoire de **20 mm de chaque côté**.
3. Différence booléenne boîte moins corps :
   `unclassified-void-complement.stl`.
4. Érosion signée du corps de **1,5 mm**, intersectée avec le corps original :
   `geometric-clearance-core-1p5mm.stl`.
5. Différence corps moins noyau érodé :
   `geometric-protected-skin-1p5mm.stl`.
6. Conservation dans `head-and-cooling-geometry-fields.vdb` de quatre champs
   OpenVDB nommés : corps, complément, noyau et peau. Relecture **par nom**,
   vérification de la résolution et des quatre volumes (écart relatif maximal
   de `1e-6`). L'ordre des champs OpenVDB n'est pas présumé stable.

Un témoin synthétique de cube creux (20 mm extérieur, 12 mm intérieur,
volume analytique de 6 272 mm³) vérifie l'intégration orientée des triangles.
`CalculateProperties` refait un maillage puis une voxelisation : sur les
domaines à cavités imbriquées testés, son volume surestime fortement le vide
ou la peau. Le rapport **conserve cette valeur et signale l'écart**. Les
contrôles de partition utilisent une intégration indépendante orientée des
triangles par le théorème de la divergence, avec sommation compensée. Leur
interprétation en volumes fermés reste conditionnée par l'audit topologique.
L'audit indépendant des STL bruts à 0,6 mm a trouvé quatre triangles d'aire
exactement nulle dans le complément et dans la peau. Le noyau était fermé et
orienté sans ce défaut. Un code `GEOMETRY_PASS` ne signifie donc pas que tous
les exports sont manifold : les bruts restent conservés, et tout nettoyage
strictement limité doit produire un dérivé distinct avec hashes et contrôles.

Un second contrôle échantillonne l'occupation native sur une grille
espacée de 6 mm : corps/vide et noyau/peau doivent être disjoints et reformer
respectivement la boîte et le corps. Les points proches d'une interface sous
petites perturbations sont exclus et comptés. Ce test n'est pas exhaustif et
ne prouve ni la connectivité du fluide ni l'égalité de chaque voxel.

### Adaptateur ABI isolé et témoin de régression

Le runtime Linux épinglé retourne un `bool` C++ sur **un octet** pour
`Voxels_bIsInside`. La déclaration C# amont utilise le marshalling implicite
`BOOL` sur quatre octets. Dans le test réel Linux amd64, cet appel amont
renvoyait vrai aux 22 140 points, pour le corps **et** son complément. Cette
exécution a été conservée avec le code d'échec `3`, sans transformer le
contrôle défaillant en réussite.

`NativeOccupancy` dans `Program.cs` déclare seulement cet appel avec un retour
`byte`, limité à 0 ou 1, et accède aux deux handles exacts via les accesseurs
typés .NET 9. Cela ne modifie **ni** l'image publiée, **ni** le kernel natif,
**ni** l'assembly PicoGK amont. Cet adaptateur dépend explicitement des
sources épinglées : il doit être réaudité avant changement de version.

Chaque lancement commence par un témoin indépendant dans le cube creux :
`(0,0,0)` est dans la cavité, `(8,0,0)` dans la matière et `(20,0,0)` à
l'extérieur. Les classifications exigées sont donc `false, true, false`.
Les résultats amont et ceux du retour sur un octet figurent dans le rapport.
Un échec arrête le lancement avant le traitement de la culasse.

Le fichier `patches/picogk-0e6cf6b-bIsInside-I1.patch` documente la correction
amont équivalente (`[return: MarshalAs(UnmanagedType.I1)]`). Il n'est **pas**
appliqué automatiquement. Ne pas cumuler des modifications amont non tracées
avec ce module et ne pas annoncer que l'image publiée contient cette correction.

Le 7 septembre 2026, le traitement de la pièce réelle à 0,6 mm a passé ce
témoin et les 22 140 points de partition sans chevauchement ni défaut d'union.
Les écarts de volume orienté étaient environ `1,01e-7` (corps + complément)
et `2,30e-7` (noyau + peau). Cela reste un contrôle numérique de géométrie,
pas une validation thermique, mécanique ou d'impression.

Ces deux traitements de domaines (0,6 et 0,3 mm) ont utilisé l'image locale
préqualifiée `3dprinting993-picogk-m64:preflight`, ID
`sha256:a570938d6111a8a5595f0404c18d63bacfe617e91850772b14bbc010bea55f4a`.
Ce n'est pas le digest GHCR publié : les sources amont sont épinglées,
et les hashes de cette image, du kernel et du module sont tracés dans
`provenance.json` et le reçu d'exécution. Ne pas confondre ces traitements
avec les allers-retours `HeadVoxels` exécutés séparément sur l'image publique.

Une répétition supplémentaire à 0,6 mm sur Vast a ensuite utilisé le digest
GHCR qualifié. Les trois STL sont identiques à ceux de Kali ; le VDB n'est
pas identique octet pour octet. La compilation du module, les contrôles et
l'arrêt de l'instance figurent dans le
[reçu Vast](../../evidence/picogk-vast-execution-20260907.json).

Régression native synthétique indépendante de toute culasse privée :

```sh
sh /workspace/picogk-cooling/test-native.sh /workspace
```

Ce script compile le module, produit une sphère témoin puis teste toutes les
opérations et les deux témoins de cube creux (volume orienté et occupation).
Il conserve son dossier temporaire privé et son rapport. Les quatre tests
Python `tests/test_picogk_cooling.py` sont des contrôles légers des contrats
de source : ils ne remplacent pas cette exécution du runtime natif.

Le rapport fournit les hashes du master, des sorties, du programme compilé et
de la bibliothèque native, les volumes, les enveloppes, la durée et la mémoire
maximale. Un contrôle de partition compare corps + complément à la boîte,
puis noyau + peau au corps. Le seuil exploratoire de 2 % est uniquement un
filtre numérique grossier : il ne remplace pas une étude de convergence.

## Limites à ne pas confondre

- Le complément contient l'air extérieur **et** tous les passages, logements
  et cavités accessibles ou fermées. Il n'est pas encore un domaine de
  refroidissement qualifié. Une séparation par occupation/propagation depuis
  des points de départ, les interfaces et les conditions limites restent à
  définir. Deux composantes de surface STL ne signifient pas deux volumes de
  fluide : une enveloppe externe et une paroi interne peuvent border un seul
  volume fluide connecté.
- Le noyau érodé n'est **pas une zone autorisée à retirer** ni un masque validé
  pour des canaux. Les 1,5 mm ne découlent d'aucun calcul de résistance,
  transfert thermique, carte matériau ou procédé d'impression qualifié.
- La « peau protégée » décrit seulement une opération géométrique. Elle
  n'établit pas une épaisseur minimale sûre et n'est pas une mesure de paroi.
- Les champs sont des `GRID_LEVEL_SET` OpenVDB à bande étroite ; ils ne sont
  pas une distance exacte en tout point du domaine et ne constituent pas un
  B-Rep usinable.
- Aucun canal, congé, nouvelle forme extérieure ou ovale n'est ajouté.

## Exécution dans l'image déjà construite

Copier ces deux fichiers source dans un répertoire de travail privé du
conteneur PicoGK, puis utiliser son SDK existant, sans nouvelle image :

```sh
dotnet build /workspace/picogk-cooling/CoolingDomains.csproj \
  -c Release -o /workspace/picogk-cooling-bin \
  -p:UpstreamRoot=/upstream -p:GeneratePackageOnBuild=false
timeout --signal=TERM --kill-after=15 1200 \
  dotnet /workspace/picogk-cooling-bin/CoolingDomains.dll \
  /workspace/private/master-body.stl /workspace/private/cooling-0p6 0.6
```

Le répertoire de sortie doit être nouveau. Le STL d'entrée peut être monté
en lecture seule. Les codes de sortie sont : `0` pour géométrie générée et
contrôles volumiques passés, `3` pour avertissement de partition volumique,
`1` pour erreur et `2` pour arguments refusés. Une anomalie d'occupation
échantillonnée produit également le code `3`. Aucun de ces états ne signifie
une validation physique ou une autorisation de fabrication.

Sources : [PicoGK épinglé](https://github.com/leap71/PicoGK/tree/0e6cf6b6f4993ec16dbcd72d8f27f26b999980f3),
[PicoGKRuntime épinglé](https://github.com/leap71/PicoGKRuntime/tree/0f26321c18ed878a7820ef769c38fd5d49d39242).
