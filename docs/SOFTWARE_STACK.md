# Stack logicielle du jumeau numérique

Cette page décrit la stack retenue au **2 septembre 2026**, à partir du commit
`b36ddca175897795f63e98e2826083da1376c725` de `main`. Elle distingue les
outils vérifiés des briques seulement définies ou encore bloquées.

```mermaid
flowchart LR
    PET["PET / PorscheFanatics<br/>JSON et provenance"] --> CAD["CAO<br/>build123d / OCCT / STEP"]
    CAD --> MESH["Scan et maillage<br/>trimesh / pymeshlab / Gmsh"]
    MESH --> CAE["Référence physique<br/>CalculiX / OpenFOAM / Cantera / FluidX3D"]
    CAE --> PN["Surrogates<br/>PhysicsNeMo"]
    PN --> USD["OpenUSD<br/>SimReady / OVRTX"]
    USD --> MFG["Fabrication<br/>STEP / 3MF / PrusaSlicer"]
```

## Socle

| Couche | Stack | Rôle |
| --- | --- | --- |
| Données | JSON, schémas JSON, Markdown | `catalog/parts/*.json` est la source de vérité |
| Automatisation | Python standard library, GNU Make | Génération, validation et `make check` |
| Versionnement | Git, GitHub, GitHub Actions | Revue, CI et preuves de build |
| Conteneurs | Docker, Buildx, GHCR | Images `linux/amd64` par digest immuable |
| Secrets/location | wrappers OpenBao, CLI Vast.ai | Accès borné, singleton, récupération et destruction |
| Formats maîtres | build123d, `.FCStd`, OpenSCAD, STEP | Géométrie éditable et dimensionnelle |
| Formats dérivés | STL, 3MF, OBJ, PLY, OpenUSD | Impression, scan, assemblage et visualisation |

Voir aussi [TOOLCHAIN.md](TOOLCHAIN.md),
[COMPUTE_ENVIRONMENT.md](COMPUTE_ENVIRONMENT.md) et
[AI_DIGITAL_TWIN_STACK.md](AI_DIGITAL_TWIN_STACK.md).

## CAO, scan et métrologie

- CAO qualifiée : Python 3.12.14, build123d 0.11.1 et OCCT 7.9.3.1
  dans `cad-author-f28` ; sortie BREP/STEP.
- Scan qualifié : NumPy 2.5.2, SciPy 1.18.1, trimesh 5.1.0,
  pymeshlab 2025.7.post1 et Rtree 1.4.1 dans `scan-mesh-f17`.
- Image générale `mesh-cfd` : Blender, Gmsh, OpenFOAM 13, build123d,
  meshio et manifold3d.
- FreeCAD et OpenSCAD servent à l'auteur/revue humaine ; STEP reste le format
  d'échange dimensionnel et STL/3MF restent des dérivés.

L'image `mesh-cfd` est native sur le X1 `amd64`. Sur le Mac Apple Silicon, son
exécution `amd64` utilise QEMU et Blender n'est pas fiable ; les gros scans
partent donc sur le X1 ou une machine louée.

## Solveurs physiques

| Domaine | Stack retenue | Limite actuelle |
| --- | --- | --- |
| Maillage | Gmsh | La convergence reste à démontrer par cas |
| Structure/thermique | CalculiX `ccx` | Pas de validation physique automatique |
| CFD | OpenFOAM 13 ; OpenFOAM 14 + ICengines/AATE au commit `c0f75f953d67cd325d28d1300672d14288f22934` | Un build ne valide pas un moteur |
| Thermochimie/réseaux | Cantera 3.2.0, NumPy 2.5.2 | Fixtures et modèles non corrélés |
| Contre-calcul LBM | FluidX3D au commit `aba941305a2cc67b0953ba1d2ba177b590dcccc3` | Licence non commerciale |
| Post-traitement | meshio, PyVista, ParaView, `ccx2paraview` | Inspection et conversion des champs |

## IA et PhysicsNeMo

PhysicsNeMo **n'est pas un LLM** et ne remplace pas le solveur de référence.
La stack qualifiée hors GPU est :

- NVIDIA PhysicsNeMo 2.2.1 ;
- Python 3.12.3 ;
- PyTorch 2.10.0 + CUDA 12.8, torchvision 0.25.0 ;
- PyTorch Geometric 2.8.0.post1 ;
- imports vérifiés : DoMINO, GeoTransolver et MeshGraphNet.

Le build, le pull public par digest et le smoke hors GPU sont verts. Le smoke
GPU, l'entraînement, le holdout/OOD et la corrélation physique restent bloqués ;
un long job Vast.ai n'est donc pas encore autorisé.

La voie LLM documentée prévoit Qwen3-Coder-30B-A3B-Instruct pour le code/CAO et
Qwen3-VL-8B-Instruct pour la lecture multimodale, servis par vLLM. L'image
`simready-local-ai` définit aussi Qwen2.5-VL-7B-Instruct au commit
`cc594898137f460bfe9f0759e9844b3ce807cfb5`, vLLM 0.26.0+cu129 et
PyTorch 2.11.0 CUDA 12.9. Cette variante est définie, pas qualifiée comme
runtime courant. Codex orchestre le travail mais n'est jamais une preuve CAE.

## Omniverse et SimReady

L'image Ubuntu 24.04/Python 3.12 isole OVRTX, Material Agent et Physics Agent :

- NVIDIA Content Agents : commit `36dbf3f274f8e256637230a05a085853f65cc175` ;
- SimReady Foundation : commit `0ed0dfbc539c9de99289771bd6848effe3ef5779` ;
- `usd-convert-cad` 0.2.0 ;
- base `simready-workflow` : digest
  `sha256:0562c69276c0d3065990cb9b1b8641dcd29355d0dccb9082dcf266fa2d22e90a` ;
- base `simready-local-ai` : digest workflow
  `sha256:41ddde8e527fcc17a3f29ac90183bd1326c330388240baf2004f99de980d6ebe`.

Le [prévol courant](../twins/vehicle-993/functional-flow-simready-preflight-f0.json)
est bloqué : OpenUSD/Asset Validator et les services Material, Physics et OVRTX
ne sont pas tous disponibles et sains sur le Mac. Aucun statut SimReady validé
ni véhicule fonctionnel n'est revendiqué.

## Images OCI verrouillées

| Image | Digest SHA-256 | Preuve actuelle |
| --- | --- | --- |
| `obj-metrology-f15` | `827e639cd126441dfa98fc097d4c8b09a01a28e25545de62ca3a01da963b959a` | Smoke CPU hors réseau |
| `scan-mesh-f17` | `b48f23d64ceab9c2e6b7b7474cdd81011d27b8a584f7af6b50b6cc05823c5189` | Smoke CPU synthétique |
| `boundary-review-f23` | `860fb1c481a8a4b72cf14d9f1d15d65b9adf327cf268ebbcc26da127427126c9` | Smoke CPU hors réseau |
| `topology-context-f26` | `41764d6d6ed935a763a6b1e07524c68961555b2724e67bbf48a2f261c35a3b10` | Smoke CPU hors réseau |
| `cad-author-f28` | `18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57` | STEP synthétique, SBOM, provenance |
| `air-oil-cycle-f34b` | `369d51ee12c259e844d01817702d8debedcf400087ab9b289b8e59671d296664` | Prévol et fixture Cantera non moteur |
| `physicsnemo-cae-cu12` | `045e8bc3151e0938d0f339aceb74c8583878effe5d0e316715e10818a018598a` | Pull public et smoke hors GPU |

Les images générales `recon`, `cadsim`, `mesh-cfd`, `physicsml`, `simready`,
`simready-workflow` et `simready-local-ai` sont définies mais n'ont pas toutes
un lock équivalent. Les tags expérimentaux locaux absents de `main` sont exclus.

## Infrastructure observée

| Nœud | Stack observée | Rôle |
| --- | --- | --- |
| Mac Apple Silicon | macOS 27.0, `arm64`, 10 CPU, 64 Gio ; Docker 29.7.2, Compose 5.4.0, Python 3.10.11 | Contrôleur, catalogue, tests et revue |
| X1 | Kali Rolling, `x86_64`, 12 CPU, 15 Gio ; Docker 28.5.2, Buildx 0.29.1, Compose 2.40.3, Python 3.13.14 | Worker Docker CPU natif `linux/amd64` |
| Vast.ai | conteneurs `linux/amd64` par digest sur GPU NVIDIA loué à la demande | Reconstruction CUDA, PhysicsNeMo, Omniverse |

Les adresses privées, comptes et clés ne sont pas publiés. Les scripts de
[`deploy/vast/simready/`](../deploy/vast/simready/) contrôlent l'instance,
transfèrent une allowlist, récupèrent les résultats et vérifient la destruction.
Le wrapper GHCR installé correspond au dépôt. Le wrapper Vast.ai répond à son
contrôle de lecture mais diffère de la copie versionnée ; il doit être
resynchronisé avant toute location payante.

## Gates avant calcul GPU payant

1. Image `linux/amd64` verte et référencée par digest immuable.
2. Pull GHCR, clé SSH et smoke GPU vérifiés.
3. Entrées et SHA-256 figés, sans secret ni donnée interdite.
4. Coût et unicité de l'instance contrôlés.
5. Récupération et destruction préparées avant le lancement.

Le runbook est [917_VAST_SIMREADY_NATIVE.md](917_VAST_SIMREADY_NATIVE.md).
Une sortie verte valide la chaîne logicielle, jamais la précision d'une pièce,
la physique d'un moteur ou une autorisation de fabrication.
