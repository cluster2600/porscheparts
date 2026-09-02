# F26 — contexte topologique déterministe des frontières du scan 917

F26 prépare la revue humaine exhaustive des **944 frontières F18**. Pour chaque
frontière, le générateur montre les faces incidentes, puis **exactement deux
anneaux topologiques** de faces voisines. Il produit quatre vues orthographiques
et un locator global dans chaque vue. Il ne classe aucune ouverture et ne
confirme aucune interface.

Les SVG contiennent des coordonnées dérivées du scan : toutes les sorties F26
restent dans `work/`, hors Git. Le dépôt ne contient que le contrat, le code, la
fixture synthétique et la définition de l'image.

## Définition topologique

- `incident_faces` : faces propriétaires d'au moins une arête d'incidence 1 de
  la composante F18 ;
- `ring_1` : faces partageant une arête triangulaire complète avec les faces
  incidentes, hors faces incidentes ;
- `ring_2` : faces partageant une arête triangulaire complète avec `ring_1`,
  hors faces incidentes et `ring_1` ;
- les trois ensembles sont disjoints ; une arête non-manifold provoque un échec
  fermé ;
- un anneau peut être vide sur une fixture pathologique, mais les deux niveaux
  sont toujours calculés et enregistrés. La fixture de smoke exige que les deux
  anneaux soient non vides.

```mermaid
flowchart LR
    M[OBJ externe local\nSHA-256 obligatoire] --> R[Recalcul identité F18]
    F[Rapport F18 local\nSHA-256 obligatoire] --> R
    C[Contrat F26 suivi\ngates fermés] --> R
    R --> I[Faces incidentes]
    I --> A1[Anneau topologique 1]
    A1 --> A2[Anneau topologique 2]
    I --> V[4 vues orthographiques]
    A1 --> V
    A2 --> V
    V --> L[Locator global par vue]
    L --> O[JSON + SVG par frontière\nCSV + manifeste avec SHA-256]
    O --> H[Revue humaine\nétat undetermined]
```

Les quatre projections portent des noms de coordonnées de scan, pas des noms
physiques :

1. `scan_xy_plus_z` ;
2. `scan_xy_minus_z` ;
3. `scan_xz_plus_y` ;
4. `scan_yz_plus_x`.

L'unité, l'échelle et le sens physique des axes restent non confirmés.

## Lots et sorties locales

La limite dure est de **48 composantes par lot**. Les 944 composantes donnent
donc 20 lots : 19 lots de 48 et un lot de 32. La structure locale est :

```text
work/917-engine/topology-context-f26/
├── topology-context-manifest-f26.json
├── topology-context-inventory-f26.csv
├── batch_0001/
│   ├── boundary_0001.json
│   └── boundary_0001.svg
└── ...
```

Le manifeste fournit le SHA-256 et le nombre d'octets de chaque JSON/SVG et du
CSV. Il ne se hache pas lui-même afin d'éviter une référence récursive. Chaque
JSON conserve `review.state = undetermined`,
`semantic_interface_confirmed = false` et `release_authority = false`.

## Contrat d'entrée fail-closed

Le générateur exige :

- un OBJ externe, un rapport F18 et le contrat F26, tous liés par SHA-256 ;
- dans `source` F18, `actual_sha256` et `expected_sha256` doivent tous deux
  correspondre à l'OBJ, `provenance_hash_matched` doit être vrai et
  `raw_geometry_embedded_in_report` doit être faux ;
- le nombre attendu de composantes ;
- une correspondance exacte des identifiants, rangs, nombres d'arêtes et de
  sommets, topologie simple et classe géométrique F18 recalculés depuis l'OBJ ;
- zéro interface F18 confirmée et tous les gates physiques fermés ;
- des fichiers réguliers non symlinkés, bornés en taille ;
- un répertoire de sortie nouveau. Aucun écrasement n'est permis. La
  parent de sortie doit être privé (`0700`) et appartenir à l'UID du runtime ;
  son device/inode est gardé jusqu'à la fin. La publication crée le répertoire
  final avec `mkdir` exclusif, lie les fichiers sans remplacement et publie le
  manifeste en dernier comme marqueur de fin ;
  un répertoire incomplet après crash reste bloqué et doit être audité ;

Le parseur OBJ F26 est volontairement limité : sommets finis, indices valides,
polygones de 3 à 64 sommets triangulés en éventail, lignes de 4096 octets au
maximum, coordonnées finies de valeur absolue au plus `1e12`, 10 millions de
sommets et 20 millions de triangles maximum. Un contexte est limité à deux
millions de faces, un SVG à 256 Mio et toute la sortie à 8 Gio. L'estimation
SVG et la réservation de sortie sont vérifiées avant la construction du texte.
Il n'utilise ni Trimesh, ni Matplotlib, ni FreeCAD.

## Image Docker dédiée avant le scan canonique

L'image F26 est distincte des images CAO, CFD et PhysicsNeMo. Elle contient
uniquement Python 3.12.14, NumPy 2.2.6, le contrat et les deux scripts F18/F26.
Elle est `linux/amd64`, CPU, non-root (`9174:9174`), sans port, sans GPU, sans
scan, sans dataset et sans poids de modèle.

```mermaid
flowchart TD
    D[Dockerfile + NumPy avec hash] --> B[Build linux/amd64]
    B --> S[Smoke OBJ synthétique\nréseau none, rootfs read-only]
    S -->|vert| P[Publication GHCR par digest]
    P --> A[Provenance SLSA + SBOM SPDX\naccès anonyme vérifié]
    A --> K[Créer le lock F26]
    K --> X[Autoriser seulement alors\nle calcul sur le scan canonique]
    S -->|échec| Z[Scan canonique interdit]
```

Construction locale de la candidate :

```bash
docker buildx build \
  --platform linux/amd64 \
  --file containers/topology-context-f26.Dockerfile \
  --load \
  --tag 3dprinting993-topology-context-f26:local \
  .

docker run --rm --platform linux/amd64 \
  --network none --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=128m \
  --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges \
  3dprinting993-topology-context-f26:local
```

Le workflow manuel
`.github/workflows/topology-context-f26-image.yml` construit et, sur demande,
publie `ghcr.io/cluster2600/3dprinting993-topology-context-f26`. Il vérifie le
digest exact, le manifeste `linux/amd64`, le sujet d'attestation, la provenance,
le SBOM, NumPy 2.2.6 et le smoke renforcé. Un second smoke crée des entrées
synthétiques, les remonte en lecture seule, remonte une sortie `0700` possédée
par `9174:9174` en lecture-écriture et exécute la vraie CLI F26. Il vérifie que
les hashes d'entrée n'ont pas changé et que la sortie est possédée par l'UID du
runtime. Enfin, un `DOCKER_CONFIG` propre effectue un pull anonyme du digest et
relance le smoke hors ligne ; une simple inspection de manifeste ne suffit pas.

## Publication immuable vérifiée

Le workflow de publication est vert :
[run 33585072387](https://github.com/cluster2600/3dprinting993/actions/runs/33585072387),
sur la révision `88d5033187d27ba47a51fb2f5f3a3230878ed6fa`. La seule
référence exécutable autorisée est désormais le digest public immuable :

```text
ghcr.io/cluster2600/3dprinting993-topology-context-f26@sha256:41764d6d6ed935a763a6b1e07524c68961555b2724e67bbf48a2f261c35a3b10
```

Le lock F26 suivi
[`topology-context-f26.lock.json`](../containers/topology-context-f26.lock.json)
relit les empreintes des neuf entrées exactes de construction et de contrôle.
Il fixe l'index OCI, son unique manifeste `linux/amd64`, le manifeste
d'attestation lié à ce sujet, la provenance SLSA, le SBOM SPDX, le smoke hors
ligne, le smoke des montages et le pull suivi du smoke par accès anonyme au
digest exact. Le runtime est CPU, non-root (`9174:9174`) et ne contient aucun
scan ni aucune sortie dérivée du scan. La provenance et le SBOM ne constituent
pas une signature cryptographique ; ce gate reste fermé.

Deux gates seulement sont vrais : `immutable_public_image_verified` et
`linux_amd64_offline_smoke_verified`. Les fixtures synthétiques prouvent que le
logiciel déterministe s'exécute, que les entrées restent en lecture seule et que
la sortie privée appartient à l'UID du runtime. Elles ne prouvent pas
l'identité du moteur, l'échelle, les interfaces, une CAO, une géométrie CAE,
PhysicsNeMo, Omniverse, la fabrication, l'impression ou le fonctionnement du
moteur. Tous ces gates restent explicitement faux.

Le champ `image.immutable_digest` du contrat générique reste volontairement
`null` : le contrat ne doit pas devenir une autorité de publication implicite.
Le verrou séparé est l'unique source d'autorité pour cette image exacte.
Le scan canonique ne doit pas être monté avec une autre référence, un tag
mutable ou une image locale non liée à ce verrou.

## Commande canonique autorisée uniquement par le verrou exact

Le modèle suivant ne peut utiliser que la référence immuable du verrou. Il
génère des preuves visuelles locales pour revue humaine ; il n'ouvre aucun gate
physique :

```bash
docker run --rm --platform linux/amd64 \
  --network none --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=256m \
  --pids-limit 128 --cap-drop ALL --security-opt no-new-privileges \
  --mount type=bind,src="$F26_INPUT_DIR",dst=/workspace/input,readonly \
  --mount type=bind,src="$F26_OUTPUT_DIR",dst=/workspace/output \
  "$F26_IMAGE_BY_DIGEST" \
  python /opt/3dprinting993/twins/reference-917-engine/source/build_topology_context_f26.py \
    --contract /opt/3dprinting993/twins/reference-917-engine/topology-context-contract-f26.json \
    --contract-sha256 863a50e1ec577ed79740877292fbbf7e2ae0af73d4996afe8d067fb261445575 \
    --mesh /workspace/input/engine.obj \
    --mesh-sha256 "$F26_MESH_SHA256" \
    --f18-report /workspace/input/boundary-review-f18.json \
    --f18-report-sha256 "$F26_REPORT_SHA256" \
    --expected-components 944 \
    --batch-size 48 \
    --output /workspace/output/topology-context-f26
```

Les variables doivent être définies explicitement. Aucun secret n'est requis.
Le scan et le rapport sont montés en lecture seule ; seul le répertoire de
sortie est inscriptible. Avant cette commande, `F26_OUTPUT_DIR` doit être créé
en mode `0700` et appartenir à l'UID/GID `9174:9174` visible dans le conteneur.

## Ce que F26 ne prouve pas

F26 ne prouve ni l'identité du moteur, ni l'échelle, ni les interfaces, ni une
géométrie étanche, ni les matériaux, ni les tolérances, ni un cas de charge. Il
ne valide aucun solveur classique, aucune donnée PhysicsNeMo, aucun USD
SimReady, aucune fabrication et aucun démarrage moteur. Les SVG améliorent la
preuve visuelle nécessaire à la future revue humaine ; ils ne la remplacent
pas.
