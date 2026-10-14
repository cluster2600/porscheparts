# Interface quatre soupapes / alésage 85 mm

Cette étape transforme le signal de dépassement radial de l'assemblage en un
**contrôle de volumes communs** entre les soupapes héritées, le cylindre et le
piston. Elle propose ensuite quatre **silhouettes d'implantation compactes**
générées avec PicoGK. Le moteur précédent, ses culasses, ses turbos et ses reçus
restent intacts. Les nouvelles silhouettes demandent une reconstruction du corps
de culasse, des sièges, des guides et des conduits avant toute intégration.

Le [plan](plan.json) conserve l'alésage/course documentaire 85 × 66 mm. Les
diamètres de tête 34 mm admission / 29 mm échappement, les centres
`X = ±18 mm, Y = ±17 mm, Z = 4 mm`, les tiges de 6 mm et leurs longueurs de
80 mm sont **de nouvelles hypothèses de conception**. Les axes sont inclinés
de 8°. Disques et tiges servent à l'encombrement ; tulipe, cône de siège,
congés, métal et fabrication ne sont pas définis. Aucun choix de diamètre n'est
validé par un calcul de débit ou une mesure de pièce Porsche.

Le [reçu](execution-20261012.json) couvre 384 cas : quatre soupapes, six levées
de 0 à 12 mm, quatre angles de vilebrequin du banc positif à partir du PMH,
deux variantes et deux maillages natifs de grille 1 / 0,5 mm. Les soupapes
héritées conservent leurs triangles et leurs coordonnées, sous l'hypothèse
non vérifiée 1 unité = 1 mm. Leur mouvement suit les axes estimés des guides.
Le piston conserve le mécanisme bielle–manivelle déjà présent dans le dépôt.
Les intersections utilisent [Manifold](https://github.com/elalish/manifold)
via le helper F37 existant. Ce sont des opérations sur triangles à coordonnées
flottantes, sans preuve d'exactitude BRep ou métrologique. Une erreur de
booléen interrompt le contrôle ; elle ne devient jamais un volume nul accepté.

Sommes des intersections des quatre soupapes, grille fine de 0,5 mm :

| Variante et pose diagnostique | Avec le cylindre | Avec le piston au PMH |
|---|---:|---:|
| Soupapes héritées, levée 0 mm | 112,994 mm³ | 0 mm³ |
| Soupapes héritées, levée 2 mm | 836,652 mm³ | 143,118 mm³ |
| Silhouettes compactes, levée 2 mm | 0 mm³ | 0 mm³ |
| Silhouettes compactes, levée 4 mm | 0 mm³ | 741,027 mm³ |

Les silhouettes compactes n'ont aucun contact avec le cylindre dans les
48 configurations soupape/levée contrôlées sur les deux grilles. À 2 mm de
levée au PMH, leur écart axial minimal de boîte au piston plat vaut seulement
**0,261 mm sur la grille fine**, inférieur à 0,5 mm. Un volume commun nul
ne qualifie donc ni le jeu positif, ni cette levée comme admissible.
Les poses à 4 mm et davantage au PMH restent en contact avec le piston.
Les volumes de contact peuvent diminuer après la traversée de la calotte vers
la cavité du piston ; cela ne rend pas ce mouvement acceptable.

Les courbes relient les poses calculées pour la lecture. Aucun balayage continu,
cycle de 720°, calage des deux bancs, contact entre soupapes, expansion à chaud,
déformation ou tolérance de fabrication n'est validé. L'alliage réel, le procédé
de fabrication et les interfaces mesurées restent `null` dans le plan.

Le dossier local conserve STL/VDB par grille, GLB de comparaison à 2 mm de
levée, rapport complet des contacts, aperçu en surfaces opaques et courbes.
Le bas du cylindre et du piston est masqué à Z = −35 mm et le cylindre est
affiché en demi-coupe uniquement pour la présentation. Le GLB complet reste
inchangé par ce rendu. Ces géométries ne sont pas publiées dans Git.

```sh
python models/917-engine-reconstruction/clearance/check_clearance.py \
  --previous work/917-4v-biturbo-20261011 \
  --dotnet /chemin/vers/dotnet \
  --output work/917-head-clearance-essai-001
python models/917-engine-reconstruction/clearance/render_review.py \
  --run work/917-head-clearance-essai-001 \
  --output work/917-head-clearance-apercu-001
```

Utiliser .NET 9 / PicoGK 2.3.0 et Python avec NumPy, Trimesh, SciPy, Rtree,
NetworkX, Matplotlib, Manifold3D 3.5.4 ; VTK 9.7.1 sert au rendu. Les sorties
doivent être de nouveaux dossiers sous `work/`. Les fichiers d'entrée sont
liés aux empreintes du reçu précédent ; les grilles ne sont pas des tolérances.

La suite est de construire une culasse paramétrique autour de cette implantation,
définir les lois de came et les critères de jeu, puis effectuer les calculs
thermiques, de débit et de résistance avec des matériaux et procédés documentés.
**Aucune autorisation de fabrication ou de mise en marche n'est accordée.**
