# Images de calcul

Cinq images reproductibles pour le travail qui ne tient pas sur un poste
ordinaire. Elles ne sont pas nécessaires pour contribuer au catalogue.

| Fichier | Image | Besoin |
|---|---|---|
| `recon.Dockerfile` | `3dprinting993-recon` | GPU CUDA : photos vers maillage |
| `cadsim.Dockerfile` | `3dprinting993-cadsim` | Processeurs : CAO, maillage, EF, CFD, découpe |
| `physicsml.Dockerfile` | `3dprinting993-physicsml` | GPU CUDA : CAO, EF différentiables et Physics ML |
| `simready.Dockerfile` | `3dprinting993-simready` | GPU RTX : OVRTX, Material/Physics Agents et validation USD |
| `simready-workflow.Dockerfile` | `3dprinting993-simready-workflow` | GPU RTX : image SimReady, prévol CAD et démarrage Vast.ai vérifié |

Tous les outils embarqués s’exécutent sans interface graphique, afin qu’un script
puisse rejouer une chaîne complète à l’identique.

```bash
make container-cadsim
make container-smoke
make container-physicsml
make container-smoke-physicsml
make container-simready
make container-simready-workflow
make container-smoke-simready
make container-smoke-simready-workflow
```

`simready` est volontairement mono-conteneur. Vast.ai exécute déjà l'image
dans un conteneur non privilégié et n'autorise pas Docker-in-Docker. OVRTX,
Material Agent et Physics Agent sont donc installés dans des environnements
Python séparés et lancés directement par Supervisor. Aucun secret n'est inclus
dans l'image : `simready-services start` refuse de démarrer avant l'installation
de `/workspace/secrets/nvidia.env` par le wrapper OpenBao.

L'image `simready-workflow` embarque `simready-vast-onstart`. Ce script corrige
les droits du fichier `authorized_keys` injecté par Vast.ai, vérifie le GPU et
le runtime SimReady, puis crée `/workspace/READY`. Le wrapper OpenBao peut donc
appeler ce script sans recopier une séquence shell susceptible de diverger.

L'environnement de validation inclut Pillow : les rendus OVRTX peuvent ainsi
échouer automatiquement lorsqu'un PNG est vide ou uniforme, au lieu de valider
seulement la présence d'un fichier. Le smoke test bloque la publication si cette
inspection de pixels n'est pas disponible.

Cette image combine des composants sous licences distinctes. Le convertisseur
CAD NVIDIA reste soumis à sa propre licence Omniverse et ne doit pas être
présenté comme un composant libre, même si l'orchestration du dépôt l'est.

`physicsml` regroupe JAX-FEM, PhysicsNeMo et DeepXDE avec les outils de
géométrie/maillage/EF de `cadsim`. L’extra GNN de PhysicsNeMo est désactivé par
défaut pour garder une construction reproductible sur plusieurs architectures ;
activez-le avec `--build-arg PHYSICSNEMO_EXTRAS=cu12,sym,mesh-extras,model-extras,gnns`.

`examples/cad_to_fea.py` fait tourner la chaîne complète — solide paramétrique,
STEP, maillage tétraédrique, calcul CalculiX — sans une seule interaction
graphique. C’est la vérification utile : un outil qui répond `--version` ne
prouve rien.

`smoke-test.sh` échoue si un outil annoncé ne répond pas ; `entrypoint.sh` rend
l’environnement du conteneur visible dans les sessions injectées par un
hébergeur ; `provision-vastai.sh` installe à la demande ce qui est trop lourd
pour l’image.

Déploiement, coûts et hygiène des données :
[../docs/COMPUTE_ENVIRONMENT.md](../docs/COMPUTE_ENVIRONMENT.md).
Justification des choix logiciels :
[../docs/decisions/0002-scriptable-toolchain.md](../docs/decisions/0002-scriptable-toolchain.md).
