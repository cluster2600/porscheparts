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
    VE --> HK[/usr/sbin/sshd wrapper<br/>ssh-keygen -A éphémère]
    HK --> SD[sshd.real]
    SD --> OS[917-cad-vast-onstart<br/>clé publique injectée + smoke]
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

Le wrapper ne doit être promu qu'après publication réussie, pull anonyme du
digest exact **et connexion `ssh_direct` réelle**. Le premier digest publié
ci-dessous est conservé comme trace historique mais révoqué pour toute nouvelle
location : Vast a invoqué `sshd` avant `onstart`, alors que l'image avait retiré
les clés hôte générées pendant le build. Le résultat réel était
`sshd: no hostkeys available -- exiting`. Le prochain digest n'est autorisé
qu'après le smoke distant complet décrit plus bas.

Les valeurs invariantes de la recette corrigée sont :

```text
image repository: ghcr.io/cluster2600/3dprinting993-cad-author-f28
revoked image: ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:dd0a9745badb03a30a795509b442e53ac27675d1ee8f08ef8dfd3498be4b4c16
image: <digest corrigé à publier puis qualifier sur Vast>
runtype: ssh_direct
remote user: root
onstart: /usr/local/bin/917-cad-vast-onstart
sshd wrapper: /usr/sbin/sshd
real sshd: /usr/lib/openssh/sshd.real
runtime host keys: ssh-keygen -A, aucune clé privée hôte dans l'image
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
et exécute ensuite `onstart`. L'observation réelle montre que son entrypoint
appelle `/usr/sbin/sshd` avant `onstart`. La recette corrigée conserve donc
`ssh_direct`, déplace le binaire OpenSSH immuable vers
`/usr/lib/openssh/sshd.real` et place à son chemin habituel un wrapper minimal.
Celui-ci exécute `ssh-keygen -A`, vérifie que les clés privées nouvellement
créées appartiennent à `root:root` avec le mode `0600`, écrit un marqueur dans
`/run/sshd`, puis remplace son processus par `sshd.real`. Les clés naissent dans
la couche écrivable de l'instance et ne sont jamais intégrées à une couche OCI.
`onstart` refuse de créer `READY` sans le marqueur. L'image finit en `USER 0:0`,
mais aucune commande CAO documentée ne s'exécute directement comme root.

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
Le staging refuse une archive compressée supérieure à 512 Mio, plus de 10 000
membres, un fichier supérieur à 64 Mio ou plus de 2 Gio après extraction.
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
`sshd` et laisse toutes les gates Vast et moteur fermées. Le workflow ajoute un
second conteneur éphémère, sans réseau : il appelle `/usr/sbin/sshd -T` pour
reproduire l'ordre Vast, exige la création des clés hôte runtime et du marqueur,
puis seulement exécute `917-cad-vast-onstart`. Le conteneur est détruit à la fin
du smoke et ses clés avec lui.

Le workflow refuse aussi une couche ajoutée supérieure à 16 000 000 octets
selon la métrique Docker Linux native. Le digest historique désormais révoqué
ajoutait 11 392 378 octets à F28. La taille de la recette corrigée doit être
remesurée par le nouveau workflow ; Docker Desktop n'est pas utilisé comme
preuve de publication.

## Sélection et lancement bornés

Une offre donnée peut disparaître à tout moment ; aucun identifiant de machine
n'est donc inscrit dans le code. Le wrapper liste les offres qui respectent le
contrat CPU/CAO, puis impose une sélection explicite :

```bash
./deploy/openbao/openbao-vastai component-factory-f41-offers
./deploy/openbao/openbao-vastai launch-component-factory-f41 <offer_id>
```

Tant que `COMPONENT_FACTORY_F41_IMAGE` désigne le digest révoqué, la seconde
commande échoue avant le verrou de location, l'enregistrement SSH et l'appel de
création payant. La denylist ne doit être levée qu'en remplaçant cette référence
par le nouveau digest après publication et poignée de main Vast vérifiée.

Le lancement refuse un prix total supérieur à 1,25 USD/h, un
`inet_up_cost` ou `inet_down_cost` absent, non fini, négatif ou supérieur à
0,05 USD/Go, moins de 64 CPU effectifs, moins de 256 000 Mo de RAM, moins de
300 Go de disque, une fiabilité inférieure à 0,985, une machine non vérifiée ou
une seconde instance appartenant à la famille F41. Le tarif réseau est revérifié
sur le contrat post-lancement lorsqu'il y est exposé.

Chaque appel payant reçoit un label de tentative aléatoire de 80 bits, long de
60 caractères, sous le préfixe F41. Ce label corrèle exclusivement l'appel et
son éventuel rollback : l'identifiant `new_contract` n'est jamais détruit sans
preuve de cette appartenance. Le garde préalable reconnaît aussi les autres
labels de tentative F41 afin de refuser deux lanceurs concurrents. Après la
création, le singleton est revérifié sur toute la famille de labels, pas seulement
sur la tentative courante. Il exige trois snapshots globaux complets, identiques
et espacés avant de déclarer la stabilité ; disparition, changement ou second
membre pendant cette fenêtre échoue fermé. En cas de course, seul le membre
portant le label de cette tentative est réconcilié et détruit ;
`singleton_verified` ne peut donc pas être annoncé tant qu'un autre membre F41
existe. Toute réponse de création non confirmée, y compris HTTP 4xx, déclenche
cette réconciliation exacte. Si cette réconciliation ou destruction échoue, la
CLI écrit immédiatement sur stderr qu'une instance peut encore tourner et être
facturée, avec le label exact à inspecter, y compris avant de propager une
annulation clavier. Le wrapper transmet uniquement l'image immuable, ce label,
le disque, `ssh_direct`, un environnement vide et l'onstart fixe. La clé privée
reste locale ; seule la clé publique approuvée peut être enregistrée chez Vast.

build123d/OCCT n'utilise pas le GPU. Le parallélisme doit venir de plusieurs
jobs CAO indépendants, chacun lancé par `917-cad-run-job`; un job individuel
reste limité à un thread natif afin d'éviter la surallocation.

La récupération des résultats n'est jamais automatique. Avant SCP, l'opérateur
doit produire côté instance une archive de résultats d'au plus 2 Gio, enregistrer
sa taille et son SHA-256, puis refuser localement tout écart de taille ou de hash.
Après cette récupération vérifiée de `/workspace/results`, le wrapper doit
arrêter la location. La conversion/validation SimReady et les calculs
PhysicsNeMo nécessitant un GPU restent dans des images et locations séparées.

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

`lock.json` reste volontairement le verrou de construction prépublication : y
inscrire le digest de l'image qui l'embarque créerait une référence circulaire
et un nouveau digest. Le digest qualifié est donc enregistré hors de l'image
dans le wrapper et dans
`twins/reference-917-engine/evidence/f41-vast-image-publication/`. Les preuves
d'exécution Vast et F41 restent une promotion ultérieure et séparée.
