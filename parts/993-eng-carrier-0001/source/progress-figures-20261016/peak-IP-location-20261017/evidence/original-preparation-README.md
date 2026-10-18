# Planche 20 — localisation des quatre pics IP réels

Préparation uniquement : **aucune image n'a encore été rendue**. Le
post-traitement réel de root est clos (session 61481, RC0, reçu dfb458b2 et
clôture a3c474e0). Les quatre JSON de cas, leur assessment et leurs deux reçus
sont copiés à l'octet avec leurs empreintes dans `data/`. Aucun DAT, champ de
contraintes complet ou maillage n'est recalculé.

La planche utilise les **45 654 facettes de surface du vrai maillage EF7**,
linéaires aux coins des C3D10 à milieux droits, en coordonnées natives non
déformées. Son NPZ complet b89c47fe est copié sans changement (3,55 Mo) ; pas de
nouvelle copie du STL de 29 Mo. Le maillage9 reste la source authentique de ses
deux positions et maxima dans les reçus. Aucun transfert de contrainte entre
maillages, aucune inversion de pose à 45°, aucune amplification géométrique.

Deux projections orthographiques XY/XZ montrent toute la pièce. Deux zooms
explicitement cadrés montrent les racines en XY et l'œil droit en XZ. Toutes les
facettes sont soumises au dessin dans chaque panneau ; le cadrage des zooms est
un clipping de vue, sans simplification du maillage. Le fond est gris uniforme,
rasterisé dans SVG/PDF ; aucune carte continue de contrainte n'est interpolée.

Les quatre maxima sont conservés :

| Repère | Cas | Maximum IP (MPa) | h mesuré (mm) |
|---|---|---:|---:|
| A | mesh9, rigide | 700,7608420501294 | 2,6038677635386436 |
| B | mesh9, K1000 | 1857,9107572863848 | 2,6038677635386436 |
| C | mesh7, rigide | 617,7164972717483 | 2,7688832354912423 |
| D | mesh7, K1000 | 1676,5460429720838 | 2,5172357815814346 |

A et B ont **exactement la même position** (élément 38852, IP3). Le cercle et la
croix restent concentriques ; seul le texte est décalé en points typographiques.
Les nombres sources complets restent dans les JSON ; l'affichage des MPa et h
est arrondi à six décimales. h est la plus grande des six arêtes de coin du
tétraèdre du pic, pas l'étiquette globale 7 ou 9.

Le chargement conservé est Fz = −4 000 N et My = +850 000 N·mm. K1000 signifie
une raideur translationnelle totale de 1 000 N/mm **par œil et par axe**, avec
ressorts distribués sur ses nœuds (`simulate.py`, lignes 226–236). Le tableau
des distances garde les seuls ensembles nodaux discrets déjà calculés :
déplacements imposés, ressorts au sol et charges. Ces distances ne sont pas des
distances aux surfaces de condition limite et ne prouvent pas une singularité.

La masse affichée est celle du **modèle CAD** à 4 420 kg/m³ :
1,262212620786407 kg ≤ plafond déclaré 1,30 kg. Aucune masse EF n'est calculée.
La figure ne déduit pas de convergence d'un changement de localisation des
maxima ; aucun seuil matière n'est ajouté.

`selfcheck.py` utilise la stdlib et vérifie les quatre cas complets, les valeurs,
coïncidences, axes sans jitter, chargement, masse et refus de perte d'un pic.
Le mode `preflight` du renderer n'importe ni NumPy ni Matplotlib.

Le rendu futur utilise le même runtime scientifique que les planches publiées
(Python 3.10.11, Matplotlib 3.10.8, NumPy 2.2.6, Pillow 11.3.0). Le renderer est
autonome avec `data/`, indépendant du cwd ; il ne charge aucun ancien module
FEA. Le launch réutilise le superviseur 4d18 inchangé, nice10, un thread et zéro
worker : 120 s externes, grâces10+10, 95 s internes, CPU90/91. Les SHA finaux et
requêtes du superviseur ont l'overhead qu'il documente.

Commande exacte future dans `command.json`, à exécuter **après GO root** depuis
`/` ou tout autre cwd. Sorties prévues : PNG, SVG et PDF, avec un reçu de rendu
liant données, runtime réellement chargé, limites des axes et tous les maxima.
Aucun de ces fichiers de rendu n'est produit pendant cette préparation.
