# Raffinement local — géométrie réelle, planche21 en préparation

Comparaison du maillage EF7 original et du vrai raffinement adaptatif002,
collecté par ROOT18815 avecRC0 :4passes,160964nœuds et86544élémentsT10.
Le modèle original a159121nœuds et85315T10. Les nœuds existants, rosters et
3218facettes protégées sont conservés ; aucune nouvelle FEA n'est représentée.

| Scope de mesure fixe | Maximum BOÎTE original (mm) | Maximum BOÎTE final (mm) | Cible fixe (mm) |
|---|---:|---:|---:|
| Boîte du pic rigide EF7 | 3.4175796812885544 | 1.3844416177416714 | 1.3844416177456211 |
| Boîte du pic K1000 EF7 | 2.5172357815814346 | 1.2586178907902892 | 1.2586178907907173 |

Les cibles sont la moitié du maximum des six arêtes du **tétraèdre du pic
initial**, respectivement2.7688832354912423 et2.5172357815814346mm. Elles ne
sont pas la moitié du maximum de chaque boîte. Le JSON garde les valeurs
binary64 complètes ; le test≤est réalisé avant arrondi d'affichage. Aucune
convergence des contraintes ni division globale des arêtes par2 n'est affirmée.

L'extraction lit les vrais INP avec le lecteur `audit_energy.read_mesh`, puis
rejoue le mesureur8e38 inchangé. Par boîte : toutes les cellules dont le
centroïde est dans la boîte fournissent leurs six arêtes **entières**, auxquelles
s'ajoutent toutes les arêtes dont les deux extrémités sont dedans. Les seules
paires d'IDs identiques sont dédupliquées pour dessiner ; aucune arête n'est
clippée ou omise. Les comptages avant/après sont6/64cellules et19/132arêtes
pour la première boîte,3/23cellules et12/62arêtes pour la seconde.

Huit vuesXY/XZ gardent le même repère et les mêmes limites par comparaison.
Le petit JSON de25240B contient toutes les positions/IDs/arêtes nécessaires.
Le renderer est autonome pour le replay ; il ne lit ni INP, NPZ, STEP ou sortie
de solveur lors du rendu. Les originaux et le premier rendu sont conservés.
La révisionv2 déplace seulement le bord supérieur des panneaux pour séparer
les titres ; v3 remplace uniquement le pied demandé par root : les résultats
mécaniques et la convergence sont documentés séparément. Les sources et diffs
sont inclus ; la versionv2 et sa capsule restent intactes.

Vérification, depuis n'importe quelcwd :

```sh
python3 -B /CHEMIN/CAPSULE/verify.py
python3 -B /CHEMIN/CAPSULE/selfcheck.py
python3.10 -B /CHEMIN/CAPSULE/render.py render /CHEMIN/CAPSULE/data/figure-data.json a88bbb99453ea311f2e8dbce3ef1c9616436fba80ddeedd01caeb2e92a497ed1 /NOUVELLE/SORTIE
```

NumPy/Matplotlib/Pillow et DejaVu Sans proviennent du runtime existant des
planches scientifiques ; leurs versions/fichiers sont liés au reçu de rendu.
`-I` exclut ce user-site : le premier essai a refusé l'import NumPy avant toute
lecture de maillage et reste conservé hors capsule. Aucune installation.
Le replay est borné95s/CPU90–91,1thread configuré,0worker ; aucune FEA.

Statut : capsule de travail non publiée. Aucun catalogue, galerie ou commit
n'est modifié ; l'inspection PNG/PDF et la décision de publication restent à root.

Le publication.json conserve l'état historique de préparation avant replay et
QA PDF. Les preuves réelles de replay/QA sont des reçus séparés, sans réécrire
la capsule figée. Cette capsule reste non publiée jusqu'à la décision de root.
