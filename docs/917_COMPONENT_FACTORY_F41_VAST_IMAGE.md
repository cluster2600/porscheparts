# F41 — image Vast CPU/CAO de la fabrique de composants

Cette image est un worker de calcul **CAO**, pas un moteur virtuel validé. Elle
ajoute seulement OpenSSH au digest immuable F28 qui contient Python 3.12.14,
build123d 0.11.1, lib3mf 2.5.0 et OCCT 7.9.3.1. Elle n'embarque ni dépôt, ni
scan, ni modèle 917, ni STEP produit, ni secret. Le staging n'accepte aucun
fichier de géométrie. La fixture du smoke est un parallélépipède synthétique
percé, sans dimension issue d'une Porsche.

La séparation est volontaire : cette image CPU produit et contrôle des solides
STEP. La conversion USD, l'assignation des matériaux/physiques et les profils
SimReady restent des étapes NVIDIA distinctes, après préflight. Un STEP fermé
n'est donc ni un USD SimReady ni une preuve de fabricabilité.

## Autorités et flux

```mermaid
flowchart LR
    BASE[F28 immuable<br/>build123d + OCCT] --> OCI[OCI linux/amd64<br/>OpenSSH fixe seulement]
    OCI --> VE[Vast remplace ENTRYPOINT<br/>runtype ssh_direct]
    VE --> OS[917-cad-vast-onstart<br/>clé publique injectée + smoke]
    OS --> READY[/workspace/READY]
    READY --> SCP[root SSH/SCP<br/>bundle F41 public]
    SCP --> STAGE[917-cad-stage-job<br/>allowlist + manifeste + SHA-256]
    STAGE --> JOB[/workspace/jobs/id<br/>UID 9178]
    JOB --> DROP[917-cad-run-job<br/>setpriv + NoNewPrivs]
    DROP --> CAD[build123d / OCCT<br/>UID 9178 sans capability]
    CAD --> OUT[/workspace/results/id]
    OUT -. étape séparée .-> USD[Préflight puis USD/SimReady]
```

`root` est limité au démarrage SSH injecté, au SCP et à la validation du
bundle. Le compte existant `cad-author` conserve l'UID/GID `9178:9178`, son
shell `nologin`, `NoNewPrivs=1` et une capability bounding set vide.

## Contrat exact pour le wrapper

Le wrapper ne doit être promu qu'après publication réussie et pull anonyme du
digest exact. Les valeurs invariantes sont :

```text
image repository: ghcr.io/cluster2600/3dprinting993-cad-author-f28
image: ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:<digest-F41-publié>
runtype: ssh_direct
remote user: root
onstart: /usr/local/bin/917-cad-vast-onstart
ready probe: /workspace/READY
smoke report: /workspace/image-smoke.json
staging: 917-cad-stage-job /workspace/inbox/917-component-factory-f41-public.tar.gz <job-id>
project root: /workspace/jobs/<job-id>/917-component-factory-f41
execution: 917-cad-run-job <job-id> 917-component-factory-f41/twins/reference-917-engine/source/run_component_factory_f41_cad_job.sh /workspace/results/<job-id>
results: /workspace/results/<job-id>/
```

Le wrapper doit utiliser exactement ce nom d'archive. Le lanceur fixe dans
l'environnement CAO :

```text
F41_RUNTIME_IMAGE_REF=ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57
```

Cette valeur lie honnêtement le runner à la base CAO dont cette image dérive ;
elle n'affirme pas que le digest F41 externe est identique au digest F28.

Vast documente que `ssh_direct` remplace l'ENTRYPOINT de l'image, prépare SSH
et exécute ensuite `onstart`. L'image finit donc en `USER 0:0`, mais aucune
commande CAO documentée ne s'exécute directement comme root.

Références officielles :
[création d'instances et remplacement de l'ENTRYPOINT](https://docs.vast.ai/api-reference/creating-instances-with-api),
[environnement Docker Vast](https://docs.vast.ai/guides/instances/docker-environment).

## Bundle d'entrée public

Le bundle est produit par
`twins/reference-917-engine/source/build_component_factory_bundle_f41.py` et
s'appelle `917-component-factory-f41-public.tar.gz`. Sa racine unique est
`917-component-factory-f41/`; le manifeste embarqué est
`917-component-factory-f41/BUNDLE-MANIFEST.json`.

Chaque payload doit appartenir à l'allowlist F41, figurer exactement dans
`files` et respecter taille, mode et SHA-256 déclarés. Tous les payloads doivent
être du texte UTF-8. `STEP`, `STL`, `3MF`, `OBJ`, `USD`, `FCStd` et tout autre
binaire sont refusés.
Les chemins `raw-scans`, liens, devices, doublons, chemins absolus, traversées
`..`, marqueurs de clés privées et marqueurs de variables de secrets sont aussi
refusés. Une géométrie dérivée, même visible ailleurs, n'est pas transférable
par ce contrat.

Schéma abrégé du manifeste embarqué :

```json
{
  "all_payload_files_utf8_text": true,
  "archive_member_count": 2,
  "binary_payload_included": false,
  "bundle_root": "917-component-factory-f41",
  "file_count": 1,
  "files": [
    {"mode": "0755", "path": "twins/reference-917-engine/source/execute_component_factory_f41.py", "sha256": "<64-hex>", "size_bytes": 123}
  ],
  "newly_generated_geometry_included": false,
  "phase": "F41",
  "private_absolute_path_included": false,
  "public_remote_refs": ["refs/remotes/origin/main"],
  "raw_scan_included": false,
  "required_runtime_images": [
    "ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57",
    "ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:41ddde8e527fcc17a3f29ac90183bd1326c330388240baf2004f99de980d6ebe"
  ],
  "schema_version": "1.1.0",
  "secret_included": false,
  "source_repository_state": "clean_commit_visible_at_exact_remote_ref",
  "source_revision": "<40-ou-64-hex>",
  "status": "public_transfer_bundle_file_manifest"
}
```

Le `file_count` réel est validé, pas déduit de cet exemple abrégé. Cette
déclaration et ces hashes ne rendent pas magiquement une donnée publique : le
wrapper doit constituer le bundle depuis un checkout neuf et propre d'un
commit déjà visible sur GitHub, jamais depuis le worktree de développement.
Le builder vérifie une référence distante au même SHA, exige un statut Git vide
et lit chaque payload avec `git show HEAD:<path>` plutôt que depuis le système
de fichiers du worktree.
Le rapport externe `bundle-manifest.json` lie le SHA-256 de l'archive ; le
wrapper compare ce hash au champ `archive_sha256` rendu par le staging distant
avant tout lancement. Aucun scan acheté ne doit entrer dans cette archive.

Séquence de préparation dans un arbre Git public propre :

```bash
public_checkout="$(mktemp -d)/3dprinting993-public"
git clone --filter=blob:none https://github.com/cluster2600/3dprinting993.git "${public_checkout}"
git -C "${public_checkout}" checkout --detach "${PUBLIC_REVISION}"
test -z "$(git -C "${public_checkout}" status --porcelain)"
bundle_output="$(mktemp -d)/f41-public-bundle"
python "${public_checkout}/twins/reference-917-engine/source/build_component_factory_bundle_f41.py" \
  --project-root "${public_checkout}" --output "${bundle_output}"
local_sha="$(jq -er '.archive.sha256' "${bundle_output}/bundle-manifest.json")"
test "$(sha256sum "${bundle_output}/917-component-factory-f41-public.tar.gz" | cut -d' ' -f1)" = "${local_sha}"
```

Après SCP dans `/workspace/inbox/`, le wrapper exécute le staging, conserve son
JSON et exige `archive_sha256 == local_sha`,
`regular_payloads_utf8_text_only == true`, `private_assets_included == false`
et `secret_material_included == false`.
Seulement alors il lance la commande `execution` exacte ci-dessus.

## Construction et smoke local

```bash
docker buildx build --platform linux/amd64 \
  -f containers/917-component-factory-f41-vast/Dockerfile \
  -t 3dprinting993-f41-cad-vast:dev --load .

docker run --rm --platform linux/amd64 --user 0:0 \
  --network none --read-only \
  --tmpfs /tmp:rw,exec,nosuid,nodev,size=512m \
  --tmpfs /workspace:rw,exec,nosuid,nodev,size=512m \
  --tmpfs /run:rw,nosuid,nodev,size=32m \
  --pids-limit 128 --cap-drop ALL \
  --cap-add CHOWN --cap-add DAC_OVERRIDE --cap-add FOWNER \
  --cap-add SETUID --cap-add SETGID --cap-add SETPCAP \
  --security-opt no-new-privileges \
  3dprinting993-f41-cad-vast:dev
```

Le smoke réalise réellement : validation du manifeste public, extraction du
tar, changement de propriétaire, chute de privilèges, création build123d,
export STEP, réouverture OCCT et contrôle d'un solide fermé. Il ne démarre pas
`sshd` et laisse toutes les gates Vast et moteur fermées.

Le workflow refuse aussi une couche ajoutée supérieure à 8 000 000 octets
selon la métrique locale Docker. Le build de développement observé ajoute
environ 3,8 Mo à F28 ; la preuve publiée restera celle du workflow GHCR.

## Usage de la machine proposée

L'offre Vast `#49655039` est intéressante ici pour ses nombreux CPU et sa RAM,
pas pour sa RTX 3060 Ti : build123d/OCCT n'utilisent pas ce GPU. Le parallélisme
doit venir de plusieurs jobs CAO indépendants, chacun lancé par
`917-cad-run-job`; un job individuel reste limité à un thread natif afin
d'éviter la surallocation.

Après récupération et vérification des hashes de `/workspace/results`, le
wrapper doit arrêter la location. La conversion/validation SimReady et les
calculs PhysicsNeMo nécessitant un GPU restent dans des images et locations
séparées.

## Limites fermées

Même avec une image verte et un STEP fermé, restent faux tant que leurs preuves
spécifiques n'existent pas :

- poignée de main SSH sur une vraie instance Vast ;
- exécution du lot F41 et conformité dimensionnelle de ses composants ;
- assemblage cinématique, jeux, tolérances et collision ;
- matériaux, charges, fatigue, thermique, CFD, combustion et corrélation banc ;
- USD/Omniverse SimReady et PhysicsNeMo ;
- puissance mécanique de 1 600 ch, démarrage moteur et sécurité véhicule ;
- autorisation de fabriquer, notamment pistons, bielles et pièces en titane.

Le fichier `lock.json` ne doit recevoir le digest et les preuves GHCR qu'après
la fin verte du workflow. Les preuves Vast et F41 restent une promotion
ultérieure et séparée.
