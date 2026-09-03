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
    OS --> NT[/root/.no_auto_tmux<br/>root:root 0600]
    NT --> READY[/workspace/READY]
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

Un digest ne peut être inscrit dans le wrapper comme candidat à sa première
qualification supervisée qu'après publication réussie et pull anonyme exact.
Il ne devient qualifié qu'après une commande BatchMode `ssh_direct` réelle,
la récupération intègre du lot et la destruction vérifiée de l'instance. Quatre
digests sont révoqués pour toute nouvelle location. Le premier avait retiré les clés hôte :
Vast invoquait `sshd` avant `onstart`, avec le résultat
`sshd: no hostkeys available -- exiting`. Le second a bien établi SSH et créé
des sessions, mais le bloc auto-tmux injecté par Vast dans `/root/.bashrc`
interceptait aussi les commandes non interactives (`no sessions` puis
`open terminal failed: not a terminal`). Le troisième a été bloqué avant toute
location : un test du bundle Git réel a trouvé que le stager exigeait à tort
`0755` pour toute source Python. Le quatrième passait le smoke séquentiel, mais
retirait brièvement le marqueur des clés hôte lors de rappels `sshd` concurrents.
La course a été reproduite nativement avec les codes `83` et `1`; le verrou et
la publication atomique du marqueur la corrigent. Aucun nouveau candidat ne
devient qualifié avant le smoke distant complet décrit plus bas.

Les valeurs invariantes de la recette corrigée sont :

```text
image repository: ghcr.io/cluster2600/3dprinting993-cad-author-f28
revoked image 1: ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:dd0a9745badb03a30a795509b442e53ac27675d1ee8f08ef8dfd3498be4b4c16
revoked image 2: ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:66cef346acfd8b3d84e87fa5c53d112ade07d4e183a3e1c00165d6a1c922f70a
revoked image 3: ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:356a92db961bd4d14aaba3ad44379e869b7f36cf741c0411dca40ed7e299b91f
revoked image 4: ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:7155af27ddd4c909c29bbd599dbe18472661c0c5d6575906371a16e7420b7fce
publication workflow 33696007854: success, image révoquée après test du bundle Git réel
revocation: before Vast spend; real Git bundle mode mismatch found by supervisor tests
replacement workflow 33699574489: success, linux/amd64 + attestations + anonymous pull
supervised qualification candidate: pending corrected immutable publication
replacement linux/amd64 manifest: pending corrected immutable publication
runtype: ssh_direct
remote user: root
image onstart: /usr/local/bin/917-cad-vast-onstart
active wrapper onstart: atomic status wrapper, then /usr/local/bin/917-cad-vast-onstart
sshd wrapper: /usr/sbin/sshd
real sshd: /usr/lib/openssh/sshd.real
runtime host keys: ssh-keygen -A, aucune clé privée hôte dans l'image
noninteractive shell marker: /root/.no_auto_tmux, root:root, mode 0600
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
Celui-ci sérialise avec `flock`, exécute `ssh-keygen -A`, vérifie que les clés
privées nouvellement créées appartiennent à `root:root` avec le mode `0600`,
publie atomiquement un marqueur dans `/run/sshd`, libère le verrou, puis remplace
son processus par `sshd.real`. Si Vast n'a pas emprunté ce chemin interne avant
`onstart`, le prévol appelle lui-même `/usr/sbin/sshd -T` et obtient le même
contrat sans lancer un second démon. Les clés naissent dans
la couche écrivable de l'instance et ne sont jamais intégrées à une couche OCI.
L'image crée aussi `/root/.no_auto_tmux` comme fichier vide `root:root` de mode
`0600`. `onstart` rejette un lien ou un type spécial, recrée ce marqueur avec les
mêmes métadonnées et refuse de créer `READY` sans lui ni le marqueur des clés
hôte. Ce fichier est le mécanisme prévu par le shell Vast pour ne pas attacher
auto-tmux aux commandes SSH non interactives. L'image finit en `USER 0:0`, mais
aucune commande CAO documentée ne s'exécute directement comme root.

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

Le mode est celui du blob Git, pas une règle fondée sur l'extension : les
sources Python importées restent `0644`, tandis que le lanceur Python et les
deux scripts shell réellement exécutés restent `0755`. Le stager compare une
table exacte couvrant toute l'allowlist et les tests la confrontent aux modes
de `git ls-files -s`.

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
`sshd` et laisse toutes les gates Vast et moteur fermées. Le workflow exécute
ensuite deux smokes éphémères supplémentaires, sans réseau. Le premier lance
directement `917-cad-vast-onstart` sans pré-appel à `sshd` et prouve son
auto-provisionnement à froid. Le second publie d'abord le marqueur, détient
explicitement le verrou FD8, puis vérifie qu'un appel concurrent à
`/usr/sbin/sshd -T` attend réellement dans `flock` pendant qu'`onstart` lit un
marqueur stable. Les smokes `onstart` exigent aussi le fichier
`/root/.no_auto_tmux` régulier, `root:root`, mode `0600`. Chaque conteneur est
détruit à la fin du smoke et ses clés avec lui.

Le workflow refuse aussi une couche ajoutée supérieure à 16 000 000 octets
selon la métrique Docker Linux native. Le digest historique désormais révoqué
ajoutait 11 392 378 octets à F28. La taille de la recette corrigée doit être
remesurée par le nouveau workflow ; Docker Desktop n'est pas utilisé comme
preuve de publication.

## Sélection et lancement bornés

Une offre donnée peut disparaître à tout moment ; aucun identifiant de machine
n'est donc inscrit dans le code. Le wrapper liste les offres qui respectent le
contrat CPU/CAO, puis le superviseur impose une sélection explicite et possède
seul le parcours payant :

```bash
./deploy/openbao/openbao-vastai component-factory-f41-offers
./deploy/openbao/run-917-component-factory-f41-cad \
  --offer-id "${OFFER_ID}" \
  --bundle "${BUNDLE}" \
  --expected-sha256 "${BUNDLE_SHA256}" \
  --source-revision "${PUBLIC_REVISION}" \
  --expected-image "${F41_IMAGE}" \
  --job-id "${JOB_ID}" \
  --output-root "${OUTPUT_ROOT}"
```

La commande interne `openbao-vastai launch-component-factory-f41` ne doit pas
être appelée directement par l'opérateur. Le superviseur crée et persiste le
label de tentative avant l'appel payant, sépare stdout et stderr, puis assure
la continuité du fichier `known_hosts` strict pendant toute la session.

L'`onstart` actif envoyé par le wrapper enveloppe le script immuable de l'image
et publie atomiquement `/workspace/f41-onstart-status.json`. Son schéma fermé
distingue `running`, `passed` et `failed` avec un code de sortie borné. Le probe
distant ouvre ce statut, `READY` et le rapport smoke avec `O_NOFOLLOW` et
`O_NONBLOCK`, exige des fichiers réguliers non vides et limite les lectures à
16 Kio pour le statut et `READY`, puis 1 Mio pour le rapport. Les codes distants
41 à 46 sont convertis en catégories fixes ; aucune sortie SSH arbitraire n'est
réémise. Les échecs d'authentification, de clé hôte, de rapport, de contrat ou
d'`onstart` échouent immédiatement. Le démarrage, l'attente de `READY` et les
échecs transitoires de transport (refus, timeout, connexion fermée, réseau
injoignable ou erreur générique) restent réessayables dans la fenêtre bornée.
Le processus OpenSSH est lancé dans son propre groupe avec une échéance absolue
de 20 secondes et un drain progressif limité à 64 Kio par flux. Tout dépassement
arrête le groupe par `TERM`, puis `KILL`, échoue immédiatement et déclenche le
rollback Vast avant qu'une sortie distante puisse saturer la mémoire locale.
Un défaut de création, d'E/S locale ou de terminaison du probe est également
fatal, exposé uniquement par une catégorie fixe et jamais par sa sortie brute.

Le wrapper refuse tous les digests révoqués avant le verrou de location,
l'enregistrement SSH et l'appel de création payant. Le prochain digest ne sera
admis pour la qualification réelle que via le superviseur borné, après contrôle
du bundle Git réel. Il ne sera qualifié qu'après réussite de la commande
BatchMode sans auto-tmux, récupération intègre du lot, puis destruction vérifiée
de l'instance.

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
le disque, `ssh_direct`, un environnement vide et l'`onstart` déterministe. La
clé privée reste locale ; seule la clé publique approuvée peut être enregistrée
chez Vast.

build123d/OCCT n'utilise pas le GPU. Le parallélisme doit venir de plusieurs
jobs CAO indépendants, chacun lancé par `917-cad-run-job`; un job individuel
reste limité à un thread natif afin d'éviter la surallocation.

La récupération est intégrée au superviseur. Il produit côté instance une
archive GNU tar d'au plus 512 Mio en excluant exactement `.runtime`, enregistre
sa taille et son SHA-256, la télécharge d'abord sous un nom `.partial`, puis
refuse tout écart de taille, de hash ou de liste de membres. Il détruit ensuite
la location et exige à la fois le succès du DELETE, son JSON exact et cinq
inventaires complets, valides et consécutifs sans cette instance dans une
fenêtre bornée. Un identifiant d'instance déjà attribué au label de tentative
reçoit toujours le DELETE : une absence transitoire de l'inventaire ne peut pas
le court-circuiter. stdout et stderr de chaque commande sont bornés à 2 Mio
pendant son exécution ; un dépassement interrompt son groupe de processus et
déclenche le nettoyage. La validation locale des 18 artefacts ne commence
qu'après la preuve transactionnelle d'absence. Toute impossibilité de confirmer
le nettoyage retourne le code critique 97 et indique que la machine peut encore
être facturée. La conversion/validation SimReady et les calculs PhysicsNeMo
nécessitant un GPU restent dans des images et locations séparées.

Si le child a déjà effectué le rollback après un échec de création ou de
qualification, il émet une seule ligne `OPENBAO_VASTAI_F41_CLEANUP` avec un JSON
à clés exactes, uniquement après acquittement du DELETE et absence paginée. Le
superviseur exige l'ID, le label et l'image attendus, puis cinq nouveaux
inventaires complets sans aucune instance F41. Il n'envoie pas un second DELETE
si cette absence est stable. Un reçu absent, dupliqué ou incohérent n'est jamais
accepté : si le label exact réapparaît, le superviseur le détruit lui-même ; si
l'absence ne peut pas être liée à une preuve de DELETE, il conserve le code 97.

Le premier essai supervisé est consigné dans
`twins/reference-917-engine/evidence/f41-vast-runtime-attempt-1/`. Il n'a produit
aucune CAO. Trente inventaires complets ont ensuite confirmé l'absence de
l'instance, mais l'ancien probe ne permettait pas de classifier l'échec SSH ou
`READY`; ce constat ne qualifie donc ni l'image sur Vast ni le lot F41.

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
et un nouveau digest. Le candidat publié est donc enregistré hors de l'image
dans le wrapper et dans
`twins/reference-917-engine/evidence/f41-vast-image-publication/`. Les preuves
d'exécution Vast et F41 restent une promotion ultérieure et séparée.
