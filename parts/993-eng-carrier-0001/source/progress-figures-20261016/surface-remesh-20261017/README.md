# Surface réelle avant et après remaillage

La planche 23 compare les deux STL du prototype C1 natif. Le remaillage Gmsh
4.15.2 conserve son repère et repart du BREP `a42e6942…`, avec un minimum de
0,25 mm, un maximum de 3 mm, courbure 96 et lissage nul.

| Fichier réel | Triangles | Triangles effilés |
|---|---:|---:|
| Export natif `9f816e…` | 44 172 | 463 |
| Surface Gmsh `577f0e…` | 638 174 | 0 |

Le critère reste `aire double / plus grande arête² < 0,001`. Le rendu le
recalcule sur **tous** les triangles. Les tableaux canoniques de l'ancien STL
sont comparés à leurs empreintes dans l'audit libigl réellement exécuté.
La nouvelle surface est liée à sa génération réellement close. Aucun
sommet n'est déplacé par le script de dessin.

Les vues globales dessinent toutes les faces, avec un éclairage géométrique
pour lire les formes. Le zoom utilise la même fenêtre autour de la pire
aiguille initiale. Ses contours orange signalent les faces concernées dans
la projection locale. La sélection du cube est uniquement visuelle.

Les deux STL complets, les sources et les trois exports sont inclus. Le BREP
parent et un moteur de calcul ne sont pas nécessaires pour reproduire cette
image. Les contrôles de fermeture, d'intersection et de distance au BREP ont
leurs propres reçus ; le dessin ne leur attribue aucun verdict supplémentaire.
La masse CAO du prototype reste proche de **1,26237 kg**, sous la limite de
1,30 kg. Les anciens calculs de contraintes ne sont pas transférés à ce congé.

Depuis ce dossier, vérifier les copies sans dépendance scientifique :

```sh
python3 -B verify.py
python3 -B selfcheck.py
```

Pour redessiner, utiliser le runtime du projet PySLM-011 : Python 3.11.15,
NumPy 1.26.4, Matplotlib 3.11.2, VisPy 0.17.0 et son backend Qt existant.
Le chemin de sortie doit être neuf et extérieur à cette capsule :

```sh
/chemin/du/runtime/env/bin/python -I -B figure.py /chemin/neuf/rendu
```

`source-provenance.json` conserve les origines et les copies exactes ;
`manifest.json` couvre tous les fichiers. Les reçus d'exécution conservent
les vrais codes retour et la fermeture des processus. Le rejeu depuis cette
copie est enregistré séparément dans le reçu de publication adjacent.
