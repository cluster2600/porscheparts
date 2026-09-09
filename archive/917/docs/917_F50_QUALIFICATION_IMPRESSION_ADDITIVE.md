# Porsche 917 F50 — qualification virtuelle d'impression additive 2V/4V

## Verdict

F50 exécute deux méthodes numériques complémentaires et reproductibles sur les
deux architectures. Le tranchage macro porte sur la tessellation privée issue
du même maître natif F50 ; AdditiveFOAM porte uniquement sur un témoin local du
procédé. Aucun résultat ne constitue une autorisation de fabrication ni de
démarrage moteur.

Les maîtres `.brep` et leurs tessellations restent privés. Le dépôt ne contient
que leurs empreintes SHA-256, des métriques agrégées par couche, des résultats
agrégés de coupons, des images de graphes et une vidéo de procédé. La peau du
scan n'a été ni modifiée, ni remplacée par une enveloppe, ni déformée par un
scaling directionnel. Aucun ovale ou ellipse globale n'a été créé.

## Entrées verrouillées

| Variante | SHA-256 du maître natif privé | Statut topologique privé |
|---|---|---|
| 2V | `1574eb58b7af09bcadab6c9cfcdd9a56940d479a5aa1b1eb807d31d41d4f7c36` | 1 solide, 1 shell, BRepCheck exact valide, free=0, non-manifold=0 |
| 4V | `10ff1a2af8f2dbca78cf6ac2f72a9e1f2842e171f1e1e76080f07eacd4162131` | 1 solide, 1 shell, BRepCheck exact valide, free=0, non-manifold=0 |

L'unité du scan est interprétée comme le millimètre pour l'écran candidat.
L'échelle absolue et les interfaces Porsche ne sont pas certifiées.

## Méthode 1 — géométrie et tranchage macro pleine pièce

La machine candidate est une **Velo3D Sapphire standard** : cylindre de
fabrication de 315 mm de diamètre sur 400 mm de haut, deux lasers de 1 kW et
recoater sans contact. Ces caractéristiques viennent de la [fiche produit
officielle Velo3D](https://www.velo3d.com/wp-content/uploads/2022/05/Sapphire-and-Sapphire-1Mz-Product-Brief-05-2022.pdf).
PWR indique exploiter des machines Velo3D et que le CP1 accepte des couches de
50 ou 100 micromètres ; cela ne remplace pas une carte procédé signée pour notre
lot de poudre et notre géométrie ([source PWR](https://www.pwr.com.au/products/additive-manufacturing)).

Six orientations rigides sont criblées. Parmi celles qui entrent dans
l'enveloppe machine nue, la candidate minimise l'aire projetée des triangles
descendants au-delà de 45 degrés. La pièce est ensuite tranchée par intersections
triangle-plan à 50 micromètres sur toute sa hauteur :

\[
N=\left\lceil\frac{H}{t}\right\rceil,
\qquad
D_{XY}=\sqrt{L_X^2+L_Y^2}.
\]

Le support est un majorant par colonnes verticales sur une grille de 0,5 mm,
pas une topologie de supports du fournisseur. L'épaisseur est sondée par la
méthode locale `max_sphere` sur 2 000 centres de faces déterministes pondérés
par aire. Le dépoudrage est un écran voxel à 1,5 mm avec propagation 6-connexe
depuis l'extérieur ; il ne voit pas les pièges inférieurs à sa résolution.

| Résultat | 2V | 4V |
|---|---:|---:|
| Orientation candidate | `build_y` | `build_y` |
| Transformations | rigides seulement | rigides seulement |
| Hauteur / couches | 205,500 mm / 4 111 | 205,500 mm / 4 111 |
| Diamètre conservatif requis | 144,943 mm | 144,943 mm |
| Marge diamétrale nominale | 170,057 mm | 170,057 mm |
| Couches avec zone non soutenue | 1 867 | 1 859 |
| Îlots nouveaux | 90 | 81 |
| Proxy de supports | 299,008 cm³ | 319,273 cm³ |
| Épaisseur p01 | 0,500 mm | 0,464 mm |
| Sondes sous 1,5 mm | **10,55 %** | **9,70 %** |
| Volume fermé détecté à 1,5 mm | 0 mm³ | 0 mm³ |

Le 4V a un peu moins de sondes fines et d'îlots, mais son proxy conservatif de
supports est plus élevé. L'entrée dans l'enveloppe nue est verte. L'épaisseur,
les supports fournisseur, l'accès de retrait, le recoater avec pièce déformée
et la preuve physique de dépoudrage restent rouges.

## Méthode 2 — AdditiveFOAM local `multiLayerPBF`

La seconde méthode utilise OpenFOAM 14 et [ORNL
AdditiveFOAM](https://github.com/ORNL/AdditiveFOAM) au commit
`9c05c5eb54db03faa342b14b0806efe740de8c44`. Elle résout localement :

\[
\rho c_p\frac{\partial T}{\partial t}
=\nabla\!\cdot(k\nabla T)+Q_{laser}-Q_{pertes}+Q_{latent}.
\]

Chaque cas simule deux couches de 50 micromètres sur une piste courte de
0,4 mm dans un domaine de 0,8 × 0,5 × 0,3 mm. Le jeu AlSi10Mg F42 est un
**contrôle numérique**, pas une carte CP1 inventée. Les configurations sont
liées aux deux empreintes maîtres ; la géométrie de culasse n'entre pas dans le
maillage local. Une égalité 2V/4V ne prouve donc pas une égalité de distorsion
pleine pièce.

Les quatre exécutions sont finies, avec six états VTK par cas et le build
OpenFOAM observé `14-7b05503f98a8`. Elles échouent néanmoins toutes au plafond
de 3 300 K :

| Cas | Résolution | \(E_v\) (J/mm³) | Tmax (K) | T p99 (K) | Volume fondu (mm³) | Bain L × l × p (mm) |
|---|---|---:|---:|---:|---:|---:|
| témoin 380 W / 1 300 mm/s / 0,15 mm | coarse | 38,974 | **3 300** | 1 953,154 | 0,009562 | 0,4423 × 0,2343 × 0,2429 |
| témoin 380 W / 1 300 mm/s / 0,15 mm | nominal | 38,974 | **3 300** | 1 907,120 | 0,005436 | 0,4403 × 0,2336 × 0,2544 |
| témoin 380 W / 1 300 mm/s / 0,15 mm | fine | 38,974 | **3 300** | 1 962,850 | 0,009667 | 0,4424 × 0,2315 × 0,2535 |
| sensibilité 360 W / 1 500 mm/s / 0,16 mm | nominal | 30,000 | **3 300** | 1 670,520 | 0,004036 | 0,4301 × 0,2148 × 0,2244 |

Entre nominal et fin, l'écart relatif vaut 2,84 % sur T p99, 0,48 % sur la
longueur, 0,89 % sur la largeur et 0,35 % sur la profondeur. Le volume fondu
varie toutefois de **43,77 %**. La convergence globale est donc rouge, même si
les quatre solveurs sont arrivés à leur temps final avec des champs finis.

La densité volumique nominale affichée est :

\[
E_v=\frac{P}{v\,h\,t}.
\]

Le plafond numérique de 3 300 K est traité comme une donnée censurée et un
échec. La convergence nominal-fin exige au plus 3 % sur la température p99 et
5 % sur le volume fondu et les trois dimensions du bain.

## Distorsion thermo-mécanique pleine pièce

Elle n'est pas calculée en F50. Il manque une carte CP1 complète dépendante de
la température (plasticité, écrouissage, fluage/relaxation), calibrée sur le
procédé, le traitement 400 °C/4 h et les déformations mesurées. Produire un
champ pleine culasse sans cette carte fabriquerait de la preuve matière. Le
témoin thermo-mécanique circulaire F50 existant reste une sensibilité locale,
pas une FEA de culasse complète.

## Portes rouges avant toute impression

- corriger et recontrôler toutes les zones sous 1,5 mm sans toucher la peau du
  scan en dehors d'une modification de conception explicitement justifiée ;
- obtenir de PWR/Velo3D la recette CP1, le fichier machine, les supports, les
  compensations et la simulation de collision recoater signés ;
- démontrer l'accès de dépoudrage puis le contrôler par endoscopie et CT ;
- qualifier des coupons dans trois orientations à froid et à chaud, puis la
  carte thermo-mécanique et la distorsion pleine pièce ;
- ajouter surépaisseurs d'usinage, datums, filetages et plan de contrôle ;
- corréler CT/CND, banc de flux, CHT et banc moteur.

Tant que ces preuves n'existent pas, `metal_print_authorized=false` et
`engine_start_authorized=false`.

## Reproduction publique

La géométrie privée est nécessaire pour reproduire la méthode 1 ; elle n'est
pas publiée. Le verrou privé de boîte englobante, lié à la variante et au hash
du maître, est fourni au script par `--expected-bounds-lock` ; ses coordonnées
ne sont pas codées dans le dépôt. Le script refuse un maître dont le hash ou la
boîte englobante ne correspond pas à ce verrou. Le témoin AdditiveFOAM se reproduit sans
géométrie privée grâce au verrou public des empreintes. Les contrôles publiés
s'exécutent avec :

```bash
make 917-additive-print-f50-check
```
