# F42.1 — réparation topologique non déformante

## Verdict

La tentative `SameParameter` est **rejetée**. Elle respecte le verrou de forme,
mais ne produit pas un STEP propre : après export/réimport, OCCT trouve 239
p-courbes invalides et 9 faces auto-intersectées. Gmsh n'achève pas le maillage
3D. Aucun STEP F42.1 n'est publié ni présenté comme réparable, imprimable ou
ajusté à une Porsche 917.

## Verrou géométrique

La seule opération autorisée est `BRepLib.SameParameter` sur une copie
topologique créée avec `BRepBuilderAPI_Copy(copyGeom=False, copyMesh=False)`.
Cela partage les objets de surfaces et courbes 3D avec l'original. Le programme
ne contient ni offset, ni couture globale, ni reconstruction de surface, ni
`ShapeFix_Shape` généraliste.

Le seuil absolu demandé est de 0,02 unité de scan. Comme l'unité absolue du scan
n'est pas certifiée, il ne doit pas être transformé en tolérance OEM de 0,02 mm.

## Matrice `SameParameter`

| Tolérance | P-courbes invalides avant export | Δ volume | Δ aire | Invariants stricts |
|---:|---:|---:|---:|:---:|
| 1e-7 | 148 | +15,1366 | −0,06918 | échec |
| 1e-6 | 138 | +19,7905 | −0,06865 | échec |
| 1e-5 | 131 | +19,7883 | −0,06344 | échec |
| 1e-4 | 131 | +2,33e-10 | +2,91e-11 | réussite |
| 1e-3 | 131 | 0 | 0 | réussite |
| 2e-2 | 131 | 0 | 0 | réussite |

`1e-4` est retenu comme plus petite tolérance du meilleur groupe non déformant.
Avant export, les 320/320 surfaces 3D sont les mêmes objets OCCT ; 937/937
courbes 3D sont identiques et trois arêtes dégénérées sont nulles dans les deux
formes. Les domaines/ranges des courbes 3D ne changent pas.

## Round-trip du candidat privé

- bbox : déplacement maximal nul ;
- Δ volume : +0,042987 unité³, soit `3,96e-8` relatif ;
- Δ aire : +0,014425 unité², soit `8,07e-8` relatif ;
- distance de peau OCCT symétrique : 80 + 80 échantillons, zéro échec,
  maximum `1,69e-13` unité ;
- topologie : 1 solide, 1 coque, 0 arête libre, 0 arête non-manifold ;
- `BRepCheck_Analyzer` exact : valide ;
- `BOPAlgo_ArgumentAnalyzer` : 248 défauts, dont 239
  `InvalidCurveOnSurface` et 9 `SelfIntersect`.

Le seuil de déplacement passe, mais la porte `zero_BOPAlgo_faults` échoue. Le
fichier temporaire `917-head-f42-1-rejected-candidate.local.step` reste dans
`work/`, hors Git et explicitement classé comme candidat rejeté.

## Rejeu Gmsh

Gmsh 4.12.1 a relu ce round-trip via son importeur OpenCASCADE. Après 6 min 30
de raffinements de surfaces répétés :

- aucun marqueur `Done meshing 3D` et aucun fichier `.msh` ;
- 85 avertissements d'éléments invalides ;
- 25 tags de surfaces distincts ;
- 3 482 éléments invalides cumulés entre passes, valeur non unique.

Les 25 faces sont toutes des B-splines. Dans le rapprochement provisoire entre
tags Gmsh et ordre de parcours OCCT, 23/25 recoupent une face à p-courbe invalide
et 8/25 une face auto-intersectée. Les identifiants sont :

`3, 10, 27, 35, 65, 66, 68, 91, 93, 94, 117, 152, 168, 193, 199, 205, 211, 236, 259, 261, 269, 272, 274, 277, 292`.

Ce rapprochement n'est pas une désignation topologique persistante : toute
reconstruction doit d'abord établir un nom stable par provenance d'opération,
signature de surface et frontières 3D.

## Plan de patches

1. **Groupe externe auto-intersecté** — faces B-spline `152, 193, 199, 211,
   236, 269, 272, 274` dans les 25 tags Gmsh. Reconstruire localement chaque
   patch depuis les profils F40 verrouillés, en conservant les courbes frontières
   3D. Cette action change potentiellement une surface 3D et était donc interdite
   en F42.1.
2. **Groupe p-courbe** — reprojeter chaque courbe 2D sur la surface B-spline 3D
   inchangée, puis reconstruire seulement le wire de trim. Accepter uniquement
   si le handle de surface 3D reste identique et si le défaut BOP disparaît.
3. **Groupe Gmsh sans recoupement BOP provisoire** — tags `3` et `91`. Examiner
   qualité paramétrique, singularités UV et frontières avant toute modification.
4. **Surfaces fonctionnelles internes** — relancer les outils analytiques
   chambre/conduits/puits sur la peau verrouillée après correction des B-splines,
   plutôt que déplacer la peau externe pour rendre le booléen possible.
5. **Acceptation** — distance de peau symétrique et continue ≤0,02 unité, bbox
   verrouillée, BRepCheck exact, zéro défaut BOP, maillage Gmsh 3D de qualité,
   puis nouvel écran d'épaisseur. Toute porte physique reste fermée.

## Livrables

- [résumé de la tentative](../twins/reference-917-engine/evidence/f42-1-topology-repair/917-head-f42-1-repair-summary.json) ;
- [carte publique des 25 faces](../twins/reference-917-engine/evidence/f42-1-topology-repair/917-head-f42-1-face-map.json) ;
- [rendu coloré de la carte](../twins/reference-917-engine/evidence/f42-1-topology-repair/917-head-f42-1-face-map.png).

Les rapports contenant des coordonnées de faces ou d'échantillons, le STEP source, le candidat rejeté et
le log Gmsh restent sous `work/` et ne sont pas versionnés.

## Reproduction privée

```bash
python twins/reference-917-engine/source/repair_topology_f42_1.py \
  --input /chemin/prive/917-head-lpbf-candidate-f41.step \
  --output work/917-f42-1-brep/917-head-f42-1-private-repair-report.json \
  --candidate-step work/917-f42-1-brep/917-head-f42-1-rejected-candidate.local.step \
  --expected-sha256 b3110e5d6d102c7af865b4f5a8067281ed4b9452e331eb68433e4119d36c609a

make 917-f42-1-topology-repair-test
```

Une réussite numérique future ne certifiera toujours ni l'échelle, ni
l'ajustement 917, ni la matière à chaud, ni la fatigue, ni la fabrication.
