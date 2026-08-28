# Chaîne d’outils

La sélection privilégie les logiciels gratuits, open source, multiplateformes et
les formats ouverts. Un outil propriétaire n’est accepté que lorsqu’il est imposé
par une machine industrielle ou un prestataire, et ne doit pas devenir la seule
source éditable du projet.

## Acquisition et reconstruction

| Besoin | Outil privilégié | Licence / accès | Format de sortie |
|---|---|---|---|
| Photogrammétrie | Meshroom / AliceVision | Open source | OBJ, point cloud |
| Reconstruction avancée | COLMAP | Open source | Caméras, nuage, maillage |
| Nuages de points | CloudCompare | Open source | E57, PLY, LAS |
| Nettoyage de maillage | MeshLab | Open source | PLY, OBJ, STL |
| Formes organiques | Blender | Open source | BLEND, OBJ, PLY |

Un scanner commercial peut fournir les données, mais les exports doivent rester
accessibles dans un format documenté.

## CAO

| Besoin | Outil privilégié | Usage |
|---|---|---|
| Pièces mécaniques | FreeCAD | CAO paramétrique, STEP, plans et assemblages |
| Géométrie générative simple | OpenSCAD | Modèles reproductibles sous forme de code |
| Surfaces organiques | Blender puis FreeCAD | Référence maillée puis reconstruction solide |

Ordre des formats maîtres : `.FCStd` ou `.scad`, puis `.step`. Les formats `.3mf`
et `.stl` sont des dérivés de fabrication.

## Simulation et inspection numérique

| Besoin | Outil privilégié |
|---|---|
| Maillage éléments finis | Gmsh |
| Calcul mécanique | CalculiX |
| Post-traitement | ParaView |
| Intégration simplifiée | atelier FEM de FreeCAD |
| CFD exploratoire | OpenFOAM |

Ces outils permettent une étude initiale. Pour une pièce critique, le modèle, les
cas de charge, les propriétés du lot imprimé et les résultats doivent être revus
par une personne compétente.

## Impression polymère

- PrusaSlicer ou OrcaSlicer pour FFF/FDM
- UVtools pour inspection de travaux résine, si nécessaire
- 3MF comme format de travail lorsque possible

## Fabrication titane

La préparation de construction LPBF dépend généralement du logiciel propriétaire
de la machine. Le projet fournit au fabricant :

- STEP et plan coté ;
- matière et norme ;
- surfaces à usiner ;
- exigences de traitement et contrôle ;
- version et empreinte des fichiers.

Le fabricant reste responsable de l’orientation finale, des supports et des
paramètres qualifiés. Le projet conserve leurs rapports sans publier les secrets
industriels du prestataire.

## Gestion du projet

- Git et GitHub pour versions, issues et revues
- Markdown et JSON comme sources portables
- Python standard library pour les contrôles locaux
- GitHub Actions pour exécuter `make check` sur le dépôt public
