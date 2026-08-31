# Environnement de calcul

Le travail lourd du projet — reconstruction photogrammétrique, maillage, calcul
EF et CFD — ne tient pas sur un poste ordinaire. Il est décrit ici comme deux
images conteneurs reproductibles, exécutables localement ou sur une machine GPU
louée à l’heure.

Aucun conteneur n’est nécessaire pour contribuer au catalogue. `make check`
reste une commande Python sans dépendance.

## Trois images, trois besoins

| Image | Besoin | Contenu | Ordre de grandeur |
|---|---|---|---|
| `3dprinting993-recon` | CUDA | COLMAP, GLOMAP, Blender, Open3D, pymeshlab, OpenCV | photos → maillage à l’échelle |
| `3dprinting993-cadsim` | cœurs et mémoire | build123d, CadQuery, Gmsh, CalculiX, OpenFOAM, PrusaSlicer | code → STEP → calcul → G-code |
| `3dprinting993-mesh-cfd` | cœurs et mémoire | Blender, pymeshlab, trimesh, build123d, Gmsh, OpenFOAM | scan OBJ → segmentation → proxy STEP → domaine CFD |

La séparation est volontaire. La reconstruction a besoin d’un GPU et d’une image
CUDA lourde ; le calcul a besoin de processeurs et tourne aussi bien sur une
machine sans GPU, souvent bien moins chère. Louer un GPU pour faire tourner
OpenFOAM est du gaspillage.

Les choix logiciels sont justifiés dans
[decisions/0002-scriptable-toolchain.md](decisions/0002-scriptable-toolchain.md) :
tout outil retenu s'exécute sans interface graphique.

Le LLM n'est volontairement pas ajouté à ces images : on lance l'image vLLM
sur une instance GPU séparée, puis les images de reconstruction et de calcul au
besoin. Le modèle retenu, le dimensionnement GPU et la frontière d'autorité du
LLM sont décrits dans [AI_DIGITAL_TWIN_STACK.md](AI_DIGITAL_TWIN_STACK.md).

## Construire et vérifier

```bash
make container-recon      # image GPU
make container-cadsim     # image CPU
make container-mesh-cfd   # image CPU dédiée aux gros scans et à la CFD
make container-smoke      # exécute smoke-test.sh dans les trois images
```

`containers/smoke-test.sh` échoue si un outil annoncé ne répond pas. Une image
qui ne passe pas ce test ne part pas sur une machine payante.

Un test de version ne prouve cependant pas qu’une chaîne fonctionne.
`containers/examples/cad_to_fea.py` enchaîne solide paramétrique, export STEP,
maillage tétraédrique et calcul CalculiX en une seule commande :

```bash
docker run --rm -v "$PWD/work:/tmp/chain" \
    3dprinting993-cadsim:dev python /tmp/chain/cad_to_fea.py
```

## Déployer sur une machine louée

L’exemple utilise vast.ai ; le principe vaut pour tout hébergeur qui exécute une
image Docker.

1. **Publier l’image** sur un registre accessible :

   ```bash
   make container-push REGISTRY=ghcr.io/<compte> IMAGE_TAG=2026.08.28
   ```

2. **Choisir la machine.** Pour la reconstruction, viser une génération Ampere ou
   Ada (RTX 3090, 4090, A100, L40S) : les binaires CUDA 12 y sont sûrs. Vérifier
   aussi le débit réseau du nœud, car l’image se télécharge à chaque location, et
   l’espace disque, qui est fixé à la création et non modifiable ensuite.

3. **Renseigner le modèle d’instance** : image `…/3dprinting993-recon:<tag>`, mode
   de lancement `Entrypoint`, et éventuellement `PROVISIONING_SCRIPT` pointant sur
   l’URL brute de `containers/provision-vastai.sh`.

   Les modes `SSH` et `Jupyter` remplacent l’entrypoint de l’image : les variables
   d’environnement et le `PATH` du conteneur ne sont alors pas visibles dans la
   session. Le script de provisionnement les réécrit dans `/etc/environment`.

4. **Envoyer les données**, jamais par Git :

   ```bash
   rsync -avP ./photos/ root@<hôte>:<port>:/workspace/images/
   ```

5. **Récupérer les résultats** puis **détruire l’instance**. Le disque loué n’est
   pas une sauvegarde.

## Contraintes de version connues

- COLMAP est compilé depuis les sources : ni les paquets Ubuntu ni conda-forge ne
  fournissent CUDA, donc la reconstruction dense y est absente.
- GLOMAP 1.2.0 ne compile pas contre COLMAP 4.1.1 : l’API `Rigid3d` a changé. Il
  est donc construit contre le COLMAP qu’il épingle, sous son propre préfixe. Les
  deux cohabitent, `colmap` restant la version courante.
- Meshroom 2025.1 est compilé avec CUDA 12 et exige une capacité de calcul ≥ 5.0.
  Pour une carte Blackwell récente, vérifier la compatibilité avant de louer.

## Chaîne de reconstruction type

```bash
colmap feature_extractor   --database_path sfm/db.db --image_path images \
                           --ImageReader.single_camera 1
colmap exhaustive_matcher  --database_path sfm/db.db
glomap mapper              --database_path sfm/db.db --image_path images --output_path sfm
colmap image_undistorter   --image_path images --input_path sfm/0 --output_path dense
colmap patch_match_stereo  --workspace_path dense          # CUDA obligatoire
colmap stereo_fusion       --workspace_path dense --output_path dense/fused.ply
```

La mise à l’échelle n’est pas automatique : une reconstruction photogrammétrique
est juste à un facteur près. Placer une référence de longueur connue dans la
scène et recaler ensuite (`colmap model_aligner`), sinon le maillage n’est pas
une mesure. Voir [SOURCE_POLICY.md](SOURCE_POLICY.md).

## Hygiène des données

Une machine louée appartient à quelqu’un d’autre.

- Aucune clé privée, aucun jeton, aucun identifiant de véhicule sur l’instance.
- Les photos et scans bruts restent hors du dépôt Git, conformément à
  [AGENTS.md](../AGENTS.md).
- Ne pas y traiter de données personnelles : plaques, visages, documents
  d’immatriculation.
- Ce qui revient dans le dépôt est le résultat traité et sa traçabilité, pas le
  contenu brut.

## Coût

La location se paie à l’heure, image comprise. Trois réflexes :

- construire et tester l’image localement avant de louer ;
- préparer le jeu de photos et le script complet avant de démarrer l’instance ;
- lancer la chaîne sous `tmux`, une déconnexion ne devant pas tuer le calcul.
