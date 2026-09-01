# Image PhysicsNeMo CAE CUDA 12

Cette image est le module GPU de **surrogate learning** du jumeau numérique.
Elle installe PhysicsNeMo 2.2.1 sur Python 3.12, PyTorch 2.10 et CUDA 12.8.
Elle vérifie les imports publics de `DoMINO`, `GeoTransolver` et
`MeshGraphNet` observés dans le tag NVIDIA `v2.2.1`.

L'extra amont `gnns` n'est pas demandé directement : ses métadonnées 2.2.1
référencent un paquet PyPI inexistant nommé `stl`. Les dépendances PyTorch
Geometric réellement nécessaires au smoke test sont donc installées et
épinglées explicitement avant PhysicsNeMo. Le smoke test d'image reste la
preuve que les imports publics attendus sont effectivement résolus.

Elle n'embarque volontairement aucun scan, dataset, poids de modèle, fichier
Porsche, solveur CFD/EF, outil CAO, Omniverse, serveur SSH ou client d'API.
Les entrées et sorties sont montées à l'exécution.

## Construction et vérifications

La cible est volontairement `linux/amd64`, qui correspond aux machines Vast.ai
et aux roues PyTorch Geometric épinglées :

```bash
docker buildx build \
  --platform linux/amd64 \
  --file containers/physicsnemo-cae-cu12.Dockerfile \
  --tag 3dprinting993-physicsnemo-cae-cu12:2.2.1 \
  --load \
  .
```

Le smoke test par défaut fonctionne sans GPU et sans réseau. Il vérifie Python,
les versions installées, `pip check` et les trois imports, mais n'interroge pas
CUDA :

```bash
docker run --rm --network none \
  3dprinting993-physicsnemo-cae-cu12:2.2.1
```

Le prévol d'une location GPU doit être explicite :

```bash
docker run --rm --network none --gpus all \
  3dprinting993-physicsnemo-cae-cu12:2.2.1 \
  physicsnemo-cae-smoke --require-gpu
```

Ce second test ajoute la visibilité du GPU et un petit calcul tensoriel CUDA.
Il ne prouve toujours aucune simulation moteur.

Un job monte son code, ses données de solveur et sa sortie au lieu de les
copier dans l'image :

```bash
docker run --rm --gpus all --network none \
  --volume "$PWD/work/917/reference-dataset:/workspace/input:ro" \
  --volume "$PWD/work/917/physicsnemo-output:/workspace/output" \
  --volume "$PWD/work/917/jobs:/workspace/jobs:ro" \
  3dprinting993-physicsnemo-cae-cu12:2.2.1 \
  python /workspace/jobs/train_surrogate.py
```

Avant toute dépense Vast.ai, l'image doit être reconstruite en CI pour
`linux/amd64`, son smoke test GPU doit passer, elle doit être publiée sur GHCR,
et la location doit utiliser son **digest immuable**, pas le tag. La liste
exacte des dépendances résolues est conservée dans
`/opt/physicsnemo/environment.freeze.txt`.

## Frontière solveur / surrogate

PhysicsNeMo n'est pas le solveur physique de référence. Le flux admissible est :

```mermaid
flowchart LR
    CAD[CAO paramétrique mesurée] --> SOLVER[Solveurs CFD / thermique / EF validés]
    SOLVER --> DATA[Dataset versionné avec maillage, BC et résidus]
    TEST[Banc et métrologie] --> CORR[Corrélation physique]
    DATA --> TRAIN[PhysicsNeMo : entraînement surrogate]
    CORR --> TRAIN
    TRAIN --> HOLDOUT[Validation tenue à l'écart + incertitude / OOD]
    HOLDOUT -->|gates passées| TWIN[Jumeau accéléré]
    HOLDOUT -->|hors domaine| SOLVER
```

- `DoMINO`, `GeoTransolver` et `MeshGraphNet` sont des familles candidates,
  pas une sélection finale ni des modèles pré-entraînés.
- Les résultats CFD, thermiques, EF et multibody doivent d'abord provenir de
  solveurs classiques avec conditions aux limites, convergence et études de
  maillage documentées.
- L'entraînement est bloqué tant que ces références et une corrélation physique
  tenue à l'écart ne sont pas disponibles.
- Une prédiction PhysicsNeMo ne rend pas une pièce fonctionnelle, sûre ou
  imprimable. Tolérances, matériaux, fatigue, coupons, CT, usinage, étanchéité,
  équilibrage et essais banc restent des gates séparées.

## Pourquoi CUDA 12 et pas NGC/CUDA 13

La voie retenue est l'extra officiel `cu12` de PhysicsNeMo 2.2.1, avec PyTorch
CUDA 12.8. L'image de base CUDA est épinglée par digest. La voie CUDA 13 et
l'image NGC ne sont pas utilisées tant qu'un prévol du pilote de la machine
cible n'a pas été archivé. Ce choix évite de confondre compatibilité supposée
et preuve d'exécution.

## Licences et provenance logicielle

| Composant | Licence ou condition principale |
|---|---|
| PhysicsNeMo | Apache-2.0 |
| PyTorch / torchvision | BSD-3-Clause |
| PyTorch Geometric et extensions | MIT |
| RAPIDS cuML / pylibraft | Apache-2.0 |
| CuPy | MIT |
| NVIDIA DALI | Apache-2.0 |
| Image de base NVIDIA CUDA/cuDNN | NVIDIA Deep Learning Container License et NVIDIA CUDA Toolkit EULA |
| Scripts de ce dépôt | licence du dépôt |

La construction ne transfère aucune licence sur les scans, plans, données
Porsche ou datasets montés à l'exécution. Un SBOM et les notices générées pour
l'image publiée restent nécessaires avant diffusion externe, notamment pour
inventorier les dépendances Python et paquets Ubuntu transitifs.

Sources de version : tag officiel
[`NVIDIA/physicsnemo v2.2.1`](https://github.com/NVIDIA/physicsnemo/tree/v2.2.1)
et métadonnées du paquet
[`nvidia-physicsnemo 2.2.1`](https://pypi.org/project/nvidia-physicsnemo/2.2.1/).

## Limites actuelles

- Cette image n'intègre pas les exemples d'entraînement NVIDIA ni un dataset
  moteur ; les imports seuls ne constituent pas un entraînement.
- Les roues GNN épinglées rendent cette variante `linux/amd64` uniquement.
- Les dépendances de premier niveau sont épinglées ; les transitives sont
  capturées au build, puis figées opérationnellement par le digest de l'image.
- Les quelques paquets système Ubuntu suivent les correctifs de sécurité
  disponibles au jour du build ; le digest GHCR et le SBOM, et non une
  reconstruction ultérieure du même Dockerfile, définissent l'artefact publié.
- Aucun prévol de pilote NVIDIA ou smoke GPU n'est possible sur un Mac sans GPU
  NVIDIA. Ces preuves doivent être produites en CI GPU ou sur une location
  courte avant le job long.
- Cette image ne comporte ni serveur SSH ni contrôleur Vast.ai ; l'accès et la
  récupération des artefacts restent la responsabilité du wrapper de
  déploiement approuvé.
