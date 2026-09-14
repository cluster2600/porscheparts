# F43 — reconstruction B-Rep locale par contours de scan

## Décision de géométrie

La lignée F39/F42 basée sur une enveloppe elliptique est visuellement obsolète
et interdite pour la suite. F43 reconstruit le corps et les ailettes à partir de
44 coupes irrégulières du stock F36 scan-conforme. Les seuls opérateurs de
construction de l'enveloppe sont des points, segments, fils fermés et un loft
réglé OCCT. Aucun disque, ellipse, cylindre ou parallélépipède global ne définit
la silhouette.

L'origine cyclique des points est alignée entre deux coupes voisines sans
modifier leurs coordonnées. Les diagnostics de maillage ont isolé trois
transitions pathologiques : `z=41,25`, `z=70,25` et `z=75,75` unités de scan.
Ces trois profils sont omis du loft. Le profil supérieur `z=82` conserve sa cote
mais reprend la forme XY du voisin `z=79,5`. Il s'agit de réparations locales et
traçables, pas d'une déformation globale de la peau.

## Provenance et unités

Le seul scan de culasse disponible est la référence publique 935; le scan 917
local représente le carter moteur avec cylindres et ne fournit pas une culasse
isolée exploitable. La géométrie F43 reste donc une référence de forme
scan-conforme, **pas une définition de montage Porsche 917**. Les unités OBJ
sont conservées comme convention numérique. L'échelle absolue, les datums, les
filetages et les interfaces OEM ne sont pas certifiés.

Le scan brut, les profils, le STEP et tous les maillages dérivés restent hors du
dépôt. Le rapport public contient uniquement leurs empreintes, volumes,
surfaces, compteurs et quantiles.

## Contrôles exécutés

Le STEP privé F43 a été réimporté par OCCT et contrôlé avec BRepCheck exact,
BOPAlgo et le contrôle des p-courbes : un solide, une coque, aucune arête libre,
non-manifold ou dégénérée, et aucun défaut BOP/p-courbe. Gmsh 4.15.2 termine le
maillage 2D et 3D du même STEP.

Le meilleur maillage Delaunay raffiné contient 654 729 tétraèdres : aucun
élément n'a un `minSICN <= 0`, mais 378 ont un `minSICN < 0,1`. La majorité est
concentrée dans les bandes de transition `z=40–44` et `z=50–54`. Les essais
Netgen n'améliorent pas le maillage de base; `Relocate3D` l'améliore légèrement;
`UntangleMeshGeometry` le dégrade et est rejeté. La suite défendable est une
partition locale ou des couches/prismes dédiés, sans modifier les autres
contours.

La comparaison unidirectionnelle stock→F43 donne une déviation latérale P95 de
3,207 unités de scan pour un seuil documentaire de 2,0 : échec. L'ajustement des
contours eux-mêmes donne P95 1,027 pour un seuil de 1,5 : réussite. Ces valeurs
ne sont pas une preuve métrologique ou de fitment.

## Verdict

F43 est retenu seulement comme **baseline B-Rep externe non ovale**. Il manque
la chambre, les quatre conduits, les quatre sièges/guides, la bougie, les
galeries d'huile, les interfaces, les jeux et une coque d'épaisseur démontrée.
L'épaisseur minimale de 1,5 mm et l'absence de cavité piégée ne peuvent pas être
validées sur ce volume externe plein. Aucun calcul thermique, structurel,
fatigue ou impression virtuelle ne peut autoriser cette pièce à ce stade.

Le rapport et les images sont dans
`twins/reference-917-engine/evidence/f43-scan-contour-patch/`.
