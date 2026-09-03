# F42.2 — reconstruction chirurgicale des p-courbes

## Verdict

La tentative est **rejetée**. La peau 3D reste inchangée, mais aucun STEP propre
n'est obtenu : le round-trip conserve 246 défauts BOPAlgo et Gmsh ne termine
même pas le maillage surfacique. Aucun STEP F42.2 n'est publié ni présenté comme
CAE-ready, imprimable ou ajusté à une Porsche 917.

## Périmètre autorisé

Les opérations sont limitées à :

- copie topologique `copyGeom=False`, donc surfaces et courbes 3D partagées ;
- `BRepLib.SameParameter` à `1e-4` unité de scan ;
- suppression d'une p-courbe fautive sur un couple face/arête précis ;
- reprojection de la courbe 3D existante avec `ShapeFix_Edge.FixAddPCurve` ;
- tolérance de projection plafonnée à `0,02` unité de scan.

Il n'existe dans le programme ni offset, ni couture, ni reconstruction de
surface, ni reconstruction de courbe 3D. L'unité absolue du scan restant non
certifiée, `0,02` unité ne doit pas être interprété comme `0,02 mm` OEM.

## Essai sur les 25 faces F42.1

Après `SameParameter`, OCCT signale 131 couples face/arête fautifs répartis sur
73 faces. Parmi eux, 69 couples appartiennent aux 25 faces cartographiées en
F42.1 et ont été reprojetés à `0,005` unité :

- défauts de p-courbes : 131 → 62 ;
- variation de volume : `+14,0087` unité³, soit `+1,29e-5` relatif ;
- variation d'aire : `+0,3968` unité², soit `+2,22e-6` relatif ;
- variation de bbox : nulle ;
- surfaces 3D identiques : 320/320 ;
- courbes 3D identiques : 937/937, plus trois arêtes dégénérées nulles.

La seule carte de 25 faces ne peut donc mathématiquement pas satisfaire la
porte `BOPAlgo = 0`, car 62 défauts subsistent, dont la majorité hors de ce
périmètre.

## Extension diagnostique bornée

Pour tester honnêtement la porte zéro défaut, une seconde copie a reprojeté les
131 couples initialement fautifs, sans changer leur support 3D. Cette extension
n'est pas promue en réparation produit :

- défauts de p-courbes avant export : 131 → 4 ;
- BOPAlgo complet avant export : 14 défauts, soit 4
  `InvalidCurveOnSurface` et 10 `SelfIntersect` ;
- variation de volume : `+37,5020` unité³, soit `+3,45e-5` relatif ;
- variation d'aire : `−4,7467` unité², soit `−2,66e-5` relatif ;
- bbox inchangée ;
- tolérance maximale d'arête : `0,02` unité.

Les quatre défauts restants correspondent à deux arêtes partagées par trois
faces coniques. Un échantillonnage de 201 paramètres par couple mesure un écart
courbe–surface maximal de `0,116868` unité pour la première arête et environ
`0,05999` pour la seconde. Ces valeurs dépassent le plafond `0,02`. Les faire
passer exigerait de déplacer la courbe 3D ou la surface conique, deux opérations
explicitement interdites en F42.2.

Cet échantillonnage local n'est pas une borne continue. Il suffit néanmoins à
prouver l'échec, puisqu'un seul point au-dessus de `0,02` ferme la porte.

## STEP privé réouvert

Le candidat diagnostique a été écrit puis réimporté avec OCCT :

- bbox : variation maximale nulle ;
- distance de peau symétrique OCCT : 80 + 80 échantillons, maximum
  `1,69e-13` unité ;
- variation de volume : `+3,45e-5` relatif ;
- variation d'aire : `−2,66e-5` relatif ;
- 1 solide, 1 coque, 0 arête libre, 0 arête non-manifold ;
- `BRepCheck_Analyzer` exact : valide ;
- BOPAlgo : **246 défauts**, dont 237 `InvalidCurveOnSurface` et 9
  `SelfIntersect`.

Le contraste 14 défauts avant export contre 246 après réimport montre que la
représentation STEP ne stabilise pas les p-courbes recalculées. Un
`BRepCheck=True` isolé n'est donc pas une preuve de CAO/CAE propre.

## Rejeu Gmsh

Gmsh 4.12.1 a relu le candidat via l'importeur OpenCASCADE, depuis un montage
en lecture seule. Après six minutes de raffinements répétés :

- `Done meshing 1D` présent ;
- aucun `Done meshing 2D` ni `Done meshing 3D` ;
- aucun fichier `.msh` créé ;
- 85 avertissements d'éléments surfaciques invalides ;
- 25 surfaces distinctes concernées ;
- 3 486 éléments invalides cumulés entre les passes, valeur non unique.

Le processus a été arrêté après cette boucle sans progression vers le maillage
3D. Les logs et éventuels produits Gmsh restent privés sous `work/`.

## Étape suivante techniquement nécessaire

La réparation exacte ne peut plus rester purement topologique. Il faut d'abord
reconstruire les deux arêtes 3D coniques ou leurs supports avec une règle de
provenance explicite, puis les neuf patches auto-intersectés déjà identifiés en
F42.1. Toute proposition future doit encore passer : écart continu de peau
≤0,02 unité, bbox verrouillée, BRepCheck exact, BOPAlgo zéro défaut, STEP
round-trip stable et maillage volumique Gmsh de qualité.

Cette étape changerait potentiellement la géométrie 3D et demande donc une
autorisation distincte et une justification métrologique.

## Livrables publiables

- [rapport JSON](../twins/reference-917-engine/evidence/f42-2-pcurve-repair/917-head-f42-2-pcurve-repair-summary.json) ;
- [rendu diagnostique](../twins/reference-917-engine/evidence/f42-2-pcurve-repair/917-head-f42-2-pcurve-diagnostic.png).

Le STEP source, le candidat rejeté, le rapport avec identifiants détaillés, le
log et le maillage Gmsh restent sous `work/`, hors Git.

## Vérification autonome

```bash
make 917-f42-2-pcurve-repair-test
```

Une future réussite géométrique ne certifierait toujours ni l'échelle absolue,
ni l'ajustement 917, ni la matière à chaud, ni la fatigue, ni la fabrication.
