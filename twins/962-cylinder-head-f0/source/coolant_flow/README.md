# Reproduire la préparation du volume d'eau

Utiliser deux environnements existants : `MR_PY` avec MeshLib 3.1.4.297 et
`CAD_PY` avec Gmsh 4.15.2, NumPy, SciPy, trimesh/rtree et matplotlib.
`INPUT` désigne le STL d'eau Ø102 inspecté, en mm. `OUT` doit être un nouveau
répertoire local ; chaque sous-répertoire de sortie doit rester absent avant
son appel. Les dépendances natives et l'exécution parallèle peuvent changer
les identités numériques d'un nouveau calcul : les reçus décrivent les
fichiers effectivement produits, sans promesse de reproduction bit à bit.

```sh
SRC=twins/962-cylinder-head-f0/source/coolant_flow
SHA=feeaddaf029a8635a7e580f1a6916c5c85b44ada9db947e6602203f8d3c6156f
"$MR_PY" -B "$SRC/prepare_surface.py" prepare "$INPUT" "$SHA" "$OUT/surface-a"
"$CAD_PY" -B "$SRC/prepare_surface.py" inspect "$INPUT" "$SHA" "$OUT/surface-a"
"$CAD_PY" -B "$SRC/repair_slivers.py" "$OUT/surface-a" "$OUT/surface-b"
"$CAD_PY" -B "$SRC/repair_last_edge.py" "$OUT/surface-b" "$OUT/surface-c"
"$CAD_PY" -B "$SRC/prepare_surface.py" inspect "$INPUT" "$SHA" "$OUT/surface-c"
"$CAD_PY" -B "$SRC/mesh_hxt.py" "$OUT/surface-c" "$OUT/volume-a"
"$CAD_PY" -B "$SRC/read_saved.py" "$OUT/surface-c" "$OUT/volume-a"
```

Sur le fichier conservé, les trois tétraèdres déficients nécessitent ensuite
une optimisation de points intérieurs. N'appliquer cette suite que si le
rapport signale encore des cellules sous le seuil ; aucune réparation n'est
nécessaire lorsqu'il est déjà satisfait.

```sh
"$CAD_PY" -B "$SRC/relocate_nodes.py" "$OUT/volume-a" "$OUT/volume-b"
"$CAD_PY" -B "$SRC/relocate_patch.py" "$OUT/volume-b" "$OUT/volume-c"
"$CAD_PY" -B "$SRC/read_saved.py" "$OUT/surface-c" "$OUT/volume-c"
"$CAD_PY" -B "$SRC/render_quality.py" "$OUT/surface-c" "$OUT/volume-c" "$OUT/quality.png"
"$CAD_PY" -B -m unittest discover -s tests -p 'test_962_coolant_surface.py' -v
```

`mesh_surface.py` conserve la voie de reparamétrage rejetée.
`mesh_discrete.py` et `mesh_frontal.py` conservent les autres constructions
réellement essayées. `optimize_saved.py` conserve les essais d'optimisation
standard ; leurs résultats ne sont pas sélectionnés comme meilleurs.
Les fichiers dont les empreintes figurent dans les rapports sont conservés
intacts. Toute évolution doit utiliser une nouvelle source et un nouveau reçu.

Le [dossier de cette étape](../../COOLANT_MESH_FOLLOWUP.md) distingue les
contrôles volumétriques, le contrôle OpenFOAM non exécuté et la qualification
physique ouverte. Aucun des programmes ne délivre une autorisation de
fabrication ou une solution hydraulique.
