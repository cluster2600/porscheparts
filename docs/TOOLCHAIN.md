# Chaîne d’outils

La sélection privilégie les logiciels gratuits, open source, multiplateformes et
les formats ouverts. Un outil propriétaire n’est accepté que lorsqu’il est imposé
par une machine industrielle ou un prestataire, et ne doit pas devenir la seule
source éditable du projet.

À qualité égale, l’outil retenu est celui qui s’exécute sans interface
graphique : voir [decisions/0002-scriptable-toolchain.md](decisions/0002-scriptable-toolchain.md).
Les tableaux ci-dessous indiquent donc la commande ou l’API utilisée, pas
seulement le nom du logiciel. Les images conteneurs correspondantes sont
décrites dans [COMPUTE_ENVIRONMENT.md](COMPUTE_ENVIRONMENT.md).

## Acquisition et reconstruction

| Besoin | Outil privilégié | Pilotage | Format de sortie |
|---|---|---|---|
| Pose des caméras | COLMAP puis GLOMAP | CLI | Base SQLite, poses |
| Reconstruction dense | COLMAP `patch_match_stereo` | CLI, CUDA requis | PLY dense |
| Nettoyage de maillage | pymeshlab | API Python | PLY, OBJ, STL |
| Nuages de points | Open3D | API Python | PLY, PCD |
| Formes organiques | Blender `--background --python` | Script Python | BLEND, OBJ, PLY |
| Second avis photogrammétrie | Meshroom `meshroom_batch` | CLI, installé à la demande | OBJ, nuage |

| Capture d’instrument | `scripts/capture_caliper.py` | CLI, pyserial | Fiche de mesure JSON |
| Prise de vue pilotée | `scripts/capture_photoset.py` | CLI, gphoto2 | Images et manifeste |

Un scanner commercial peut fournir les données, mais les exports doivent rester
accessibles dans un format documenté.

Une mesure recopiée à la main n’est pas traçable. Quand l’instrument sait
transmettre sa lecture, la fiche enregistre l’horodatage machine et l’instrument
utilisé ; sinon elle porte explicitement la mention `manual_entry`.

## CAO

| Besoin | Outil privilégié | Usage |
|---|---|---|
| Pièces mécaniques | build123d ou CadQuery | CAO écrite en Python sur noyau OCCT, export STEP |
| Géométrie générative simple | OpenSCAD | Modèles reproductibles sous forme de code |
| Surfaces organiques | Blender puis reconstruction solide | Référence maillée puis solide paramétrique |
| Revue humaine et FEM interactif | FreeCAD | Inspection STEP, vérification visuelle |

Une pièce peut donc avoir pour source maîtresse un script Python versionné qui
régénère son STEP. Le fichier `.FCStd` reste accepté ; il est simplement moins
facile à relire en revue.

Ordre des formats maîtres : script `build123d`, `.FCStd` ou `.scad`, puis
`.step`. Les formats `.3mf` et `.stl` sont des dérivés de fabrication.

## Simulation et inspection numérique

| Besoin | Outil privilégié | Pilotage |
|---|---|---|
| Maillage éléments finis | Gmsh | API Python |
| Calcul mécanique | CalculiX `ccx` | Jeu de données texte |
| Conversion de résultats | `ccx2paraview`, meshio | CLI et Python |
| Post-traitement | PyVista, ParaView | Script Python |
| CFD exploratoire | OpenFOAM + foamlib | CLI et Python |

Ces outils permettent une étude initiale. Pour une pièce critique, le modèle, les
cas de charge, les propriétés du lot imprimé et les résultats doivent être revus
par une personne compétente.

## Impression polymère

- PrusaSlicer en ligne de commande pour la découpe en lot, OrcaSlicer pour le
  réglage interactif d’une machine
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
