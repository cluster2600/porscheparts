# F40 — image de transport Vast pour le solveur instationnaire

Cette image ajoute uniquement le transport SSH/SCP nécessaire à Vast au-dessus
du digest public F39. Elle ne contient ni dépôt, ni scan, ni géométrie privée,
ni clé, ni résultat F40. Aeolus1D 0.3.3 et toute sa fermeture numérique restent
ceux de l'image F39 immuable.

Le choix d'une image séparée évite d'installer OpenSSH à chaque location et
sépare deux autorités : `root` transporte et prépare une archive, tandis que le
solveur s'exécute obligatoirement sous `9139:9139`, avec `NoNewPrivs=1` et une
capability bounding set vide.

## Cycle d'exécution

```mermaid
flowchart LR
    OCI[OCI linux/amd64<br/>F39 par digest + OpenSSH fixe] --> VE[Vast remplace ENTRYPOINT<br/>mode ssh_direct]
    VE --> OS[917-wave-vast-onstart<br/>clé injectée + smoke hors ligne]
    OS --> READY[/workspace/READY]
    READY --> SCP[root SSH/SCP<br/>archive vers inbox]
    SCP --> STAGE[917-wave-stage-job<br/>validation tar + chown]
    STAGE --> JOB[/workspace/jobs/id<br/>UID 9139]
    JOB --> DROP[917-wave-run-job<br/>setpriv + NoNewPrivs]
    DROP --> SOLVER[Aeolus/F40<br/>UID 9139 sans capability]
    SOLVER --> OUT[/workspace/results/id]
```

Vast documente que `ssh_direct` provisionne le port 22, remplace l'ENTRYPOINT
de l'image, injecte son propre démarrage SSH, puis exécute `onstart`. Le contrat
de lancement doit donc définir exactement :

```text
runtype: ssh_direct
onstart: /usr/local/bin/917-wave-vast-onstart
```

Références officielles :
[création d'instances et comportement de l'ENTRYPOINT](https://docs.vast.ai/api-reference/creating-instances-with-api),
[environnement Docker Vast](https://docs.vast.ai/guides/instances/docker-environment).

L'image finit volontairement en `USER 0:0` : l'entrypoint injecté doit pouvoir
initialiser `sshd` et la clé publique. Ce n'est pas une autorisation d'exécuter
le solveur comme root. Le seul chemin documenté est `917-wave-run-job`, qui
refuse un job non préparé ou détenu par un autre UID.

## Construction et smoke local

```bash
docker buildx build --platform linux/amd64 \
  -f containers/917-engine-wave-f40-vast/Dockerfile \
  -t 3dprinting993-wave-vast-f40:dev --load .

docker run --rm --platform linux/amd64 --user 0:0 \
  --network none --read-only \
  --tmpfs /tmp:rw,exec,nosuid,nodev,size=256m \
  --tmpfs /workspace:rw,exec,nosuid,nodev,size=256m \
  --tmpfs /run:rw,nosuid,nodev,size=32m \
  --cap-drop ALL --cap-add CHOWN --cap-add DAC_OVERRIDE \
  --cap-add FOWNER --cap-add SETUID --cap-add SETGID --cap-add SETPCAP \
  --security-opt no-new-privileges \
  3dprinting993-wave-vast-f40:dev
```

Les treize paquets Debian sont fixés par version et SHA-256 avant `dpkg -i`.
Le smoke ne démarre pas `sshd`. Il vérifie le paquet OpenSSH, l'absence de clé
hôte ou de `authorized_keys` dans l'image, un staging synthétique, la chute de
privilèges, puis le benchmark Sod F39 sous UID 9139.

## Transfert et campagne

Après publication, il faut d'abord obtenir et relire le digest GHCR, réussir un
pull anonyme `linux/amd64`, puis seulement autoriser le wrapper OpenBao à louer
une instance. Le fichier `lock.json` reste donc prépublication et ses gates
GHCR/Vast sont `false` tant que ces preuves n'ont pas été capturées.

Une fois le SSH Vast vérifié, le protocole dans l'instance est :

```bash
# local : archive publique du commit exact, sans raw scan ni secret
scp -i ~/.ssh/id_vastai f40-public.tar root@HOST:/workspace/inbox/

# distant : refuse traversal, liens, devices, doublons et écrasement
917-wave-stage-job /workspace/inbox/f40-public.tar f40-campaign

# distant : le calcul ne s'exécute jamais comme root
917-wave-run-job f40-campaign python \
  twins/reference-917-engine/source/run_unsteady_convergence_f40.py \
  --project-root . \
  --contract twins/reference-917-engine/unsteady-convergence-campaign-f40.json \
  --output-dir "$WAVE_RESULTS_DIR" --execute --workers 6
```

Le GPU 3060 Ti n'accélère pas Aeolus1D. Cette image exploite le CPU et la RAM ;
elle ne prétend pas utiliser les 384 vCPU avec seulement six cas F40. Une phase
ultérieure peut élargir la matrice de cas avant de justifier ce nœud.

## Limites fermées

Une construction OCI verte prouve seulement la reproductibilité de l'image et
la séparation de privilèges locale. Un pull anonyme prouve seulement que Vast
peut récupérer le digest. Même après une campagne F40, restent non prouvés :

- poignée de main SSH réellement injectée par Vast, avant son test dédié ;
- convergence physique ou corrélation banc ;
- combustion, injection, allumage, turbocompresseurs et 1 600 ch ;
- démarrage moteur, sécurité véhicule et fabrication.

Le lock ne doit être promu qu'avec le digest exact et les artefacts de workflow,
puis complété séparément avec l'identifiant de l'instance et les preuves SSH.
