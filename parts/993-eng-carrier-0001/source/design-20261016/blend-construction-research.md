# Construction du pied tangent de racine — 16 octobre 2026

La voie recommandée est une **surface rationnelle de translation**, construite
à partir de la courbe d’intersection des deux surfaces support. Elle remplace le
calcul de congé sur le corps découpé. La construction est cohérente avec le
diagnostic indépendant de l’arête 614, mais son admission dépend encore des
terminaisons, de l’assemblage CAO et des nouveaux calculs. Aucune géométrie de
`toolchain_audit` n’a été modifiée pour cette recherche.

Le support installé a été vérifié : build123d 0.11.1 / OCP 7.9.3.1 expose déjà
`Geom_BSplineSurface`, `Face.make_surface_patch`,
`BRepOffsetAPI_MakeFilling`, `G0Error` et `G1Error`. Aucune installation n’est
nécessaire pour les deux méthodes ci-dessous.

## 1. Pied rationnel exact à section YZ — priorité

Les deux supports diagnostiqués sont des extrusions : le cap suit `z=h(x)` et
la face de nervure `y=f(x)`. Leur intersection est
`C(t)=(x(t),f(x(t)),h(x(t)))`. Le quart de cercle unité YZ utilise les pôles
`Q0=(0,-1,0)`, `Q1=(0,0,0)`, `Q2=(0,0,1)` et les poids
`[1,sqrt(1/2),1]`.

On construit directement `F(t,v)=C(t)+r(t)Q(v)`. Si `r(t)` est exprimé dans la
**même base rationnelle** que C, avec coefficients `ri`, le réseau de surface
est `Pij=Ci+ri*Qj`, de poids `wi*wj`. Il conserve les nœuds/degré de C dans la
direction longitudinale et un degré 2, nœuds `[0,1]`, multiplicités `[3,3]`
dans l’autre direction. Le constructeur rationalisé est disponible dans
[OCCT 7.9.3, Geom_BSplineSurface](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_9_3/src/Geom/Geom_BSplineSurface.hxx#L213-L222).

La tangence suit de la construction, sans loft ajusté :

- Au bord cap, `Fv` est parallèle à Y et
  `Ft=(x',f'-r',h')`. La normale est parallèle à `(-h',0,x')`, celle du cap.
- Au bord nervure, `Fv` est parallèle à Z et
  `Ft=(x',f',h'+r')`. La normale est parallèle à `(-f',x',0)`, celle de la nervure.

Cette preuve vaut aussi pour un rayon variable positif. Le rayon est celui
de la **section YZ**, et ne doit pas être annoncé comme un rayon constant
dans la section normale 3D. L’extinction `r=0` produit un bord paramétrique
dégénéré ; elle demande un traitement topologique explicite.

La peau est ensuite fermée par un volume recouvrant l’intérieur des deux
supports, puis cousue et fusionnée. Les outils et ouvertures doivent être
appliqués dans un ordre qui conserve ce pied. Un simple bouchon exposé à
l’extrémité créerait une nouvelle rupture de tangence.

Deux contrôles sont particulièrement nécessaires ici : les rails déplacés
doivent rester dans les **faces découpées**, et les jonctions longitudinales
avec le cylindre de fenêtre 235 et la fin de nervure doivent être continues.
Une génératrice étendue avant la découpe de fenêtre ou un raccord au troisième
support évite de fermer au voisinage immédiat du pic.

Coût estimé : un module OCP de l’ordre de 100–200 lignes, sans dépendance
supplémentaire, plus les contrôles existants. Le risque principal est la
fermeture et la fusion, plutôt que le calcul de la surface. Un témoin
algébrique distinct a réellement évalué une surface rationnelle à rayon
variable dans OCP : résidu ponctuel nul à la précision imprimée et résidus
sinus de tangence `5.99e-17` et `3.51e-16`. Ce témoin ne construit pas le
carrier et ne valide pas ses booléens.

## 2. Raccord G1 contraint sur les supports — solution de repli CAO

Pour une terminaison qui rencontre un troisième support, définir un contour
fermé avec deux rails sur le cap et la nervure, et des raccords de fermeture
sur les supports voisins. Passer chaque rail avec sa face support et l’ordre
`GeomAbs_G1` à `BRepOffsetAPI_MakeFilling`, fermer le volume puis fusionner.
Cela autorise un raccord dont la section n’est pas nécessairement circulaire.

Le [source OCCT MakeFilling](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_9_3/src/BRepOffsetAPI/BRepOffsetAPI_MakeFilling.hxx)
fournit les contraintes et les erreurs maximales `G0Error`/`G1Error`.
[BRepFill_Filling](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_9_3/src/BRepFill/BRepFill_Filling.hxx#L49-L55)
précise que des contraintes incompatibles peuvent être ignorées : `IsDone`
ou un solide valide ne suffisent donc pas. Il faut conserver les erreurs par
bord et vérifier indépendamment positions et normales après couture et union.
Le [wrapper build123d 0.11.1](https://github.com/gumyr/build123d/blob/v0.11.1/src/build123d/topology/two_d.py)
expose déjà cette construction ; l’appel OCP direct permet de garder ses erreurs.

Coût estimé : moyen, environ 150–300 lignes avec les courbes de contour et la
couture, sans installation. Cette voie est plus adaptée à une fermeture
multisupport, mais moins déterministe que le réseau exact de la méthode 1.
Un loft lissé ne garantit pas à lui seul la tangence aux supports ; le
[loft OCCT](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_9_3/src/BRepOffsetAPI/BRepOffsetAPI_ThruSections.hxx)
est une approximation entre sections. Le
[sweep à guide auxiliaire avec contact](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_9_3/src/BRepOffsetAPI/BRepOffsetAPI_MakePipeShell.hxx#L49-L51)
ne promet que C0 dans ce mode : il ne remplace pas le contrôle G1.

## PicoGK/SDF localisé — dernier recours, pas exécuté

PicoGK expose `IImplicit`, les booléens, `OverOffset` et `Fillet`; ce dernier
est un effet de double offset du champ complet, pas une sélection d’arête.
Le [source épinglé de LEAP71](https://github.com/leap71/PicoGK/blob/0e6cf6b6f4993ec16dbcd72d8f27f26b999980f3/Base/Voxels.cs#L532-L591)
et la [discussion des mainteneurs](https://github.com/leap71/PicoGK/discussions/44)
confirment ce périmètre. Les wrappers locaux `parts/picogk-catalog/common/Sdf.cs`
et `RotKit.cs` existent ; ils n’ont pas été modifiés ni exécutés.

Pour préserver exactement les interfaces, il faudrait conserver le STEP
original et produire **uniquement un ajout local**, dont le domaine est
disjoint de toutes les régions protégées. Une voxelisation globale, même
suivie d’une recoupe des trous, ne démontrerait pas leur conservation exacte.
La source éditable serait un C# + paramètres, avec STEP et fonctions de
masquage épinglés. Le champ doit éviter toute modification en dehors de la
zone motivée par les contraintes.

Le chemin compatible avec la recette actuelle serait : mailler cet ajout,
le convertir en BRep facettée fermée, puis le fusionner au STEP original.
Les surfaces analytiques des ports resteraient ainsi disponibles pour les
groupes et chargements du maillage Gmsh existant. Tous les contrôles CAO,
interfaces, masse et STEP seraient requis, sans exception.

Une sortie STL seule peut aussi être tétraédralisée par la procédure
[Gmsh t13](https://gmsh.info/doc/texinfo/#t13) : classification, création des
surfaces discrètes, boucle et volume, puis maillage 3D. Elle demande toutefois
un nouvel adaptateur de groupes de ports/appuis ; la reconnaissance actuelle
par cylindres analytiques ne s’applique pas à un STL. Ce n’est donc pas un
remplacement direct du STEP.

La fidélité doit être mesurée dans les deux sens contre la définition de
l’ajout, sur les normales, les sections, le volume et la jonction avec le
corps. La taille de voxel seule ne garantit pas le seuil de surface existant
de 0,06 mm. Un pas serait choisi à partir de ce budget, puis un seul raffinement
motivé si nécessaire ; aucune grille n’a été exécutée. Les tétraèdres doivent
être conformes, à Jacobien positif, liés aux mêmes charges et contrôlés par
les mêmes bilans. Les seuils de masse 1,30 kg et de transfert STEP 1e-8 restent
inchangés. Cette voie coûte davantage que les deux constructions CAO et
ajoute un problème de discrétisation avant même le nouveau calcul mécanique.
