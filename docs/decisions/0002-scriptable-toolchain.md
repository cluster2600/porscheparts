# 0002 — Chaîne pilotable par script

Date : 28 août 2026

Révise partiellement [0001](0001-open-toolchain.md).

## Contexte

La décision 0001 a retenu des logiciels libres, mais en les nommant par leur
interface graphique. Or presque tout le travail répétitif du projet —
reconstruction, nettoyage de maillage, export STEP, maillage EF, calcul, découpe
— doit pouvoir tourner sans opérateur devant l’écran, sur une machine louée à
l’heure, et être relancé à l’identique après correction.

Un outil dont l’usage normal passe par des clics n’est pas reproductible : ni un
script, ni un agent, ni une intégration continue ne peuvent le rejouer.

## Décision

Pour chaque besoin, l’outil retenu est celui qui possède une **interface en ligne
de commande ou une API Python complète**, à qualité et licence équivalentes.

| Besoin | 0001 | Retenu | Raison du changement |
|---|---|---|---|
| Structure from motion | Meshroom (GUI) | COLMAP + GLOMAP | CLI complète, base de données inspectable, GLOMAP réduit fortement le temps de pose |
| Reconstruction dense | Meshroom | COLMAP dense (CUDA) | Même chaîne, même format, pas de second écosystème |
| Nettoyage de maillage | MeshLab (GUI) | pymeshlab | Mêmes filtres, appelés depuis Python ; `meshlabserver` n’existe plus |
| Nuages de points | CloudCompare (GUI) | Open3D | API Python, recalage et sous-échantillonnage scriptables |
| CAO paramétrique | FreeCAD (GUI) | build123d et CadQuery | Même noyau OCCT, mais géométrie écrite en Python, relisible en revue et exportable en STEP |
| Maillage EF | Gmsh (GUI) | Gmsh API Python | Maillage piloté par le script qui construit la pièce |
| Calcul | CalculiX | CalculiX | Déjà en ligne de commande, jeu de données texte |
| CFD | OpenFOAM | OpenFOAM + foamlib | Cas pilotés depuis Python plutôt que par édition manuelle de dictionnaires |
| Découpe | PrusaSlicer | PrusaSlicer CLI | Découpe en lot, sans ouvrir l’interface |

## Ce qui ne change pas

- FreeCAD reste un outil légitime de revue humaine, d’inspection STEP et
  d’atelier FEM interactif. Il cesse seulement d’être la source maîtresse.
- OpenSCAD reste valide : c’est déjà du code.
- Blender reste retenu, en mode `--background --python`, pour les opérations de
  maillage lourdes et les rendus de documentation.
- Meshroom reste utilisable comme second avis sur une reconstruction difficile,
  installé à la demande sur la machine louée et non dans l’image.

## Conséquences

- La géométrie maîtresse d’une pièce peut être un fichier Python versionné,
  produisant un STEP reproductible, à côté des formats `.FCStd` et `.scad`.
- Chaque étape devient rejouable : mêmes entrées, même commande, même sortie.
- Les images conteneurs de `containers/` matérialisent cette chaîne.
- Coût : les auteurs habitués au dessin interactif doivent lire du code CAO. La
  contrepartie est une revue possible en diff, ce qu’un fichier binaire interdit.
