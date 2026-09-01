# Conteneur F15 de métrologie et segmentation OBJ

Cette image CPU exécute le vrai pipeline F15 pour caractériser un maillage OBJ
avant reconstruction CAO. Elle inventorie les déclarations, mesure les bornes
en unités OBJ et sépare les composantes connexes. Cette **segmentation géométrique**
ne constitue pas une reconnaissance sémantique des pièces du moteur.

## Pourquoi une image séparée

L'image historique `mesh-cfd` réunit Blender, Gmsh, OpenFOAM, SSH et de
nombreuses bibliothèques. Ce périmètre reste utile plus tard, mais il est trop
large pour l'inventaire initial. Le pipeline F15 s'exécute sans GPU et utilise
uniquement la bibliothèque standard de Python : aucune roue Python, dépendance
native, API ou licence logicielle payante n'est nécessaire.

```mermaid
flowchart LR
    A[Scan OBJ local monté en lecture seule] --> B[Empreinte SHA-256]
    B --> C[Parseur F15 standard library]
    C --> D[Bornes en unités OBJ]
    C --> E[Composantes et incidence des arêtes]
    C --> F[Inventaire o g usemtl mtllib]
    D --> G[Rapports F15 hors Git]
    E --> G
    F --> G
    G --> H{Identité, échelle et interfaces mesurées?}
    H -- non --> I[Reconstruction CAO bloquée]
    H -- oui, preuves indépendantes --> J[CAO paramétrique à valider]
```

## Frontières et reproductibilité

- la base CPython 3.12.14 est fixée au digest de son manifeste
  `linux/amd64` ;
- l'image contient seulement CPython, le contrat F15, son pipeline et le smoke ;
- le processus porte l'UID/GID numérique `9175:9175` et refuse root ;
- aucun scan, dataset, poids de modèle ou secret n'est copié dans l'image ;
- le smoke crée deux tétraèdres synthétiques dans `/tmp`, exécute le vrai
  pipeline avec `--synthetic-fixture-mode`, exige deux composantes et vérifie
  que toutes les autorités de release restent fermées ;
- le workflow manuel publie seulement un tag de commit, récupère le digest immuable,
  contrôle l'attestation BuildKit, l'architecture, l'utilisateur et
  rejoue le smoke sans réseau avec un système de fichiers en lecture seule.

CPython est distribué sous licence Python-2.0. Le contrat, le pipeline et le
smoke suivent la licence MIT du dépôt.

## Construction locale

```bash
docker buildx build \
  --platform linux/amd64 \
  --file containers/obj-metrology-f15.Dockerfile \
  --tag 3dprinting993-obj-metrology-f15:dev \
  --load .

docker run --rm --network none --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=16m \
  --cap-drop ALL --security-opt no-new-privileges \
  3dprinting993-obj-metrology-f15:dev
```

Pour le scan canonique, le fichier brut reste hors Git, monté en lecture seule
sur `/workspace/input`, et `/workspace/output` reçoit les rapports :

```bash
docker run --rm --network none --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=256m \
  --mount type=bind,src="$PWD/raw-scans/917-engine/original",dst=/workspace/input,readonly \
  --mount type=bind,src="$PWD/work/917-engine/scan-segmentation-f15",dst=/workspace/output \
  --entrypoint python3 \
  3dprinting993-obj-metrology-f15:dev \
  /opt/3dprinting993/twins/reference-917-engine/source/build_scan_segmentation_f15.py \
  --contract /opt/3dprinting993/twins/reference-917-engine/scan-segmentation-f15.json \
  --source /workspace/input/917-engine-case-with-cylinders.obj \
  --output /workspace/output
```

## Ce que le résultat ne prouve pas

Un smoke vert, une segmentation ou une image GHCR publiée ne prouve pas
l'identité 917, l'échelle, la fidélité des interfaces, l'étanchéité, la CAO
reconstruite, la tenue thermomécanique, le fonctionnement du moteur ni
l'imprimabilité. Il ne déclenche aucune location Vast.ai. La publication et le
futur fichier de verrouillage du digest sont des étapes distinctes, réalisées
seulement après validation du workflow.
