# Environnement de calcul

Le travail lourd du projet — reconstruction photogrammétrique, maillage, calcul
EF, CFD et préparation SimReady — ne tient pas sur un poste ordinaire. Il est
décrit ici comme cinq images conteneurs reproductibles, exécutables localement
ou sur une machine GPU louée à l’heure.

Aucun conteneur n’est nécessaire pour contribuer au catalogue. `make check`
reste une commande Python sans dépendance.

## Cinq images, cinq besoins

| Image | Besoin | Contenu | Ordre de grandeur |
|---|---|---|---|
| `3dprinting993-recon` | CUDA | COLMAP, GLOMAP, Blender, Open3D, pymeshlab, OpenCV | photos → maillage à l’échelle |
| `3dprinting993-cadsim` | cœurs et mémoire | build123d, CadQuery, Gmsh, CalculiX, OpenFOAM, PrusaSlicer | code → STEP → calcul → G-code |
| `3dprinting993-mesh-cfd` | cœurs et mémoire | Blender, pymeshlab, trimesh, build123d, Gmsh, OpenFOAM | scan OBJ → segmentation → proxy STEP → domaine CFD |
| `3dprinting993-physicsml` | CUDA + mémoire GPU | contenu de `cadsim`, JAX-FEM, PhysicsNeMo, DeepXDE | maillage → solveur différentiable → modèle physique |
| `3dprinting993-simready` | RTX, 48 Go recommandés | OVRTX, Material Agent, Physics Agent, OpenUSD, SimReady Validator | source 3D → USD enrichi → validation → rendu Omniverse |

La séparation est volontaire. La reconstruction a besoin d’un GPU et d’une image
CUDA lourde ; le calcul classique tourne aussi bien sur une machine sans GPU,
souvent bien moins chère. `physicsml` est réservé aux étapes qui bénéficient
réellement du GPU : solveurs différentiables et apprentissage guidé par la
physique.

`simready` regroupe les trois services NVIDIA dans un seul conteneur, car une
instance Vast.ai standard ne peut pas lancer Docker Compose dans Docker.
L'image doit être construite et testée dans GitHub Actions avant toute
location. Les secrets NVIDIA ne sont jamais placés dans une couche : ils sont
injectés après connexion SSH par le wrapper OpenBao, puis
`simready-services start` valide l'autorisation d'inférence avec une requête
minimale qui n'affiche ni secret ni réponse, puis lance les services natifs.
Une erreur HTTP 401/403 bloque donc la chaîne avant la préparation et le rendu
des lots.

Le 1er septembre 2026, l'image publiée et testée pour cette chaîne est
`ghcr.io/cluster2600/3dprinting993-simready@sha256:3947ea34d5101065c97103cc2176f395cb9753cb1d7807acb3cfd095796a4e1a`.
Sur Vast.ai, les scans 917 et 935 ont été convertis en USD direct et rendus par
OVRTX. Le Material Agent a préparé ses vues mais l'appel au modèle public a été
refusé avec HTTP 403 : conversion et rendu sont prouvés, assignation IA et
Physics Agent ne le sont pas. Cette séparation évite de confondre un service
prêt avec une autorisation d'API valide.

Le validateur de profil doit recevoir les trois répertoires de spécification.
Utiliser le lanceur embarqué plutôt que la commande brute :

```bash
simready-profile-validate scene.usd \
  --profile Prop-Robotics-Physx --version 2.1.0
```

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
make container-physicsml  # image GPU pour JAX-FEM / PhysicsNeMo
make container-simready   # image GPU NVIDIA CAD-to-SimReady, linux/amd64
make container-smoke-all  # exécute smoke-test.sh dans les cinq images
```

`containers/smoke-test.sh` échoue si un outil annoncé ne répond pas. Une image
qui ne passe pas ce test ne part pas sur une machine payante.

Le workflow GitHub utilise Docker Buildx. Si le poste local affiche
« legacy builder is deprecated », installer/activer Buildx ou lancer le build
depuis l’action manuelle `Build compute images` ; le builder legacy peut rester
bloqué pendant la sauvegarde d’une couche CUDA très volumineuse.

L’image `physicsml` épingle JAX `0.11.1`, JAX-FEM `0.0.12`, PhysicsNeMo `2.2.0`
et DeepXDE `1.15.0`. L’extra `gnns` de PhysicsNeMo reste optionnel car il ajoute
des extensions PyTorch dépendantes de l’architecture ; il peut être activé au
build avec `PHYSICSNEMO_EXTRAS`.

Cette image GPU est volumineuse : prévoir au moins 30 Go de disque pour l’image
et davantage pour les jeux de données, checkpoints et résultats. Le smoke test
vérifie les imports sur un runner CPU et vérifie aussi JAX/PyTorch sur une
instance qui expose réellement une carte NVIDIA.

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

   Pour publier seulement l’image GPU dédiée, construire et pousser ses tags
   explicitement après authentification au registre :

   ```bash
   make container-physicsml IMAGE_TAG=2026.08.30
   docker tag 3dprinting993-physicsml:2026.08.30 \
     ghcr.io/<compte>/3dprinting993-physicsml:2026.08.30
   docker push ghcr.io/<compte>/3dprinting993-physicsml:2026.08.30
   ```

2. **Choisir la machine.** Pour la reconstruction, viser une génération Ampere ou
   Ada (RTX 3090, 4090, A100, L40S) : les binaires CUDA 12 y sont sûrs. Vérifier
   aussi le débit réseau du nœud, car l’image se télécharge à chaque location, et
   l’espace disque, qui est fixé à la création et non modifiable ensuite.

3. **Renseigner le modèle d’instance** : pour la chaîne complète CAO/EF/Physics ML,
   choisir l’image `…/3dprinting993-physicsml:<tag>` avec une carte CUDA visible.
   Pour une reconstruction photo seule, utiliser `…/3dprinting993-recon:<tag>`.
   Mode de lancement `Entrypoint`, et éventuellement `PROVISIONING_SCRIPT`
   pointant sur l’URL brute de `containers/provision-vastai.sh`.

   Les modes `SSH` et `Jupyter` remplacent l’entrypoint de l’image : les variables
   d’environnement et le `PATH` du conteneur ne sont alors pas visibles dans la
   session. Le script de provisionnement les réécrit dans `/etc/environment`.

   Commande de lancement recommandée dans un terminal Vast.ai :

   ```bash
   nvidia-smi
   smoke-test.sh physicsml
   mkdir -p /workspace/project
   cd /workspace/project
   ```

   Pour un lancement Docker équivalent avec les répertoires de travail séparés :

   ```bash
   docker run --rm --gpus all --ipc=host --shm-size=16g \
       -v "$PWD:/workspace/project" -v "$PWD/work:/workspace/work" \
       ghcr.io/<compte>/3dprinting993-physicsml:<tag> bash
   ```

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
- Code_Aster n’est pas copié dans `physicsml` : sa distribution reproductible
  officielle s’appuie sur l’environnement Salome-Meca/Singularity. CalculiX est
  inclus pour le chemin EF conteneurisé immédiatement disponible ; Code_Aster
  sera consommé dans son conteneur dédié lorsque nous aurons figé une image et
  un smoke test compatibles Vast.ai.

Références amont utilisées pour le choix des versions :
[PhysicsNeMo](https://github.com/NVIDIA/physicsnemo),
[JAX](https://docs.jax.dev/en/latest/installation.html),
[JAX-FEM](https://github.com/deepmodeling/jax-fem) et
[code_aster](https://code-aster.org/en).

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

## Lire une page rendue en JavaScript

Plusieurs sources du registre répondent mais ne livrent rien : leur contenu
n'existe qu'après exécution du script de page. C'est un problème de rendu, pas
un refus, et il se résout par un navigateur exécuté côté serveur.

**Cloudflare Browser Run** le fournit, avec deux moteurs : Chromium par défaut,
et **Kitesurf**, moteur sans état conçu pour les agents, sorti le 6 août 2026,
gratuit en bêta, annoncé à 3 à 7 fois moins de CPU et de mémoire que Chromium
pour la capture et l'extraction HTML.

Deux voies d'accès, et elles ne se valent pas :

| Voie | Kitesurf | Ce qu'il faut |
|---|---|---|
| Binding Worker, `env.BROWSER.quickAction()` | **non documenté** | un Worker déployé, aucun jeton |
| API REST, `?browser=kitesurf` | **oui** | un jeton `Browser Rendering - Edit` |

Le moteur Kitesurf ne se sélectionne donc, à ce jour, que par l'API REST.

Piège à connaître : `quickAction()` renvoie un objet `Response`, pas un objet
nu. Le sérialiser directement produit `{}` et laisse croire à une page vide. Le
corps utile est `{ success, result }`.

Ce que Browser Run ne résout pas : un hôte qui renvoie 403, et un site qui
refuse les agents nommés. La documentation précise d'ailleurs que Kitesurf ne
sait pas négocier un défi anti-bot à empreintes TLS. Changer d'infrastructure ne
change pas une permission.

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
