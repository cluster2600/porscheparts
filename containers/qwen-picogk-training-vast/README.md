# Image d'entraînement Qwen/PicoGK pour Vast

Image `linux/amd64` dédiée aux commandes explicites de QLoRA sur
`mlx-community/Qwen2.5-Coder-7B-Instruct-4bit`. Elle réutilise le trainer
MLX local vérifié et ne démarre aucun entraînement. Les sources sont dans
`/opt/qwen-training` ; données, modèle, cache, verrou et résultats restent sur
le volume `/workspace`.

Build local réalisé le 14 octobre 2026 : tag
`qwen-picogk-training-vast:20261014`, image ID
`sha256:6be0f4cfb7edb60432486e1236ae34836ac64942e2b321ec6e16fac6e647f9e5`,
mesure historique du build **2 997 776 273 octets** (~3,00 Go).
Le contrôle actuel par `docker image inspect` rapporte **7 903 264 657 octets**
(~7,90 Go). La relation entre ces deux mesures n'a pas été établie ; les 3 Go
historiques ne décrivent pas la taille locale décompressée annoncée maintenant.
[`build-result.json`](build-result.json) contient les empreintes et résultats
du conteneur exact : `pip check` réussi, **15 contrôles CPU** réussis, corpus
au mauvais SHA refusé avec code 2 avant tout modèle et sans nouveau run.
Ce reçu décrit le build local ; la publication GitHub de la même recette est
consignée séparément ci-dessous. Aucun test GPU n'est réalisé.

## Image publiée sur GitHub

Le [package public GHCR](https://github.com/cluster2600/porscheparts/pkgs/container/qwen-picogk-training-vast)
est lié à `cluster2600/porscheparts`. Le [run GitHub Actions](https://github.com/cluster2600/porscheparts/actions/runs/38630047489)
du commit `32c9e21991b23462fac50116b07019c6e02e161e` réussit : build Linux amd64,
versions principales, freeze, `pip check`, 15 contrôles CPU avant publication
puis contrôle de l'image retéléchargée par digest. Le téléchargement anonyme
sur le Mac et les mêmes 15 contrôles passent également.

```sh
docker pull --platform linux/amd64 ghcr.io/cluster2600/qwen-picogk-training-vast@sha256:e30a824082404c040fc54d7979933219523b16e633672c86b14a6530820df46e
```

Docker annonce **7 875 038 439 octets** (~7,88 Go) pour l'image publiée et
retéléchargée. [`publication-result.json`](publication-result.json) contient
les reçus et liaisons vérifiés. Ce build CI reprend la recette ; son digest
diffère du build local. Les dépendances transitives et APT sont résolues lors
du build et son freeze est conservé. L'exécution GPU et le transport SSH sur
Vast restent non vérifiés ; ce package ne contient ni poids ni corpus.

Python **3.12.13**, MLX **0.32.3**, MLX-LM avec les extras `train,cuda12`
**0.31.3**, NumPy **2.5.3** et Transformers **5.17.0** sont épinglés.
Le digest de l'image Python est dans le Dockerfile. Le build conserve la
résolution complète des dépendances dans
`/opt/qwen-training/resolved-packages.txt` ; ces dépendances transitives et les
paquets APT restent résolus au moment du build. Il faut employer le digest de
l'image construite pour reproduire cet environnement exact.

Le [backend CUDA de MLX](https://ml-explore.github.io/mlx/build/html/install.html#cuda)
requiert notamment Linux avec glibc ≥ 2.35, une architecture NVIDIA ≥ SM 7.5
et un pilote ≥ 550.54.14 pour CUDA 12. L'installation des wheels CUDA ne
démontre ni leur exécution GPU, ni la capacité d'entraîner à 6 144 tokens.
Le trainer impose 22 GiB de mémoire MLX, 512 MiB de cache, batch 1 et
gradient checkpointing. Les variables du backend sont
`MLX_CUDA_GRAPH_CACHE_SIZE=16384` et `MLX_ENABLE_CACHE_THRASHING_CHECK=1`.
Le trainer les fixe avant l'import MLX, même dans une session SSH sans les
variables du lancement Docker. Le nom du contrôle est vérifié dans la
[source MLX 0.32.3](https://github.com/ml-explore/mlx/blob/v0.32.3/mlx/backend/cuda/lru_cache.h).

## Construction et contrôle CPU

Depuis la racine du dépôt, avec un répertoire Docker temporaire contenant
seulement `{"auths":{}}` et le plugin Buildx public :

```sh
docker --config "$task_docker_config" buildx build \
  --platform linux/amd64 --load \
  -t qwen-picogk-training-vast:20261014 \
  -f containers/qwen-picogk-training-vast/Dockerfile .

docker --config "$task_docker_config" run --rm --platform linux/amd64 \
  --network none qwen-picogk-training-vast:20261014 \
  python /opt/qwen-training/image_smoke.py
```

`Dockerfile.dockerignore` fonctionne comme une liste fermée de huit fichiers.
Il exclut corpus, poids, scans, secrets et reste du dépôt. Aucun secret de
registre n'est nécessaire au build ; aucun credential helper n'est utilisé.
Le build effectue `pip check`, contrôle les empreintes des sources et exécute
le smoke CPU. Ce smoke vérifie notamment l'aide des deux commandes, les
schemas des messages, le SHA du corpus, les chemins/symlinks, l'exclusion des
tâches finales et le refus d'un profil modifié avant tout chargement MLX.
Un import natif `mlx.core` sans pilote NVIDIA échoue avec
`ImportError: libcuda.so.1: cannot open shared object file`. Le smoke CPU
contrôle donc le préflight et les dépendances Python ; il ne valide pas les
tensors natifs du wheel CUDA. Le pilote et ses bibliothèques doivent être
injectés par le runtime NVIDIA de l'hôte GPU.
L'image annonce `NVIDIA_VISIBLE_DEVICES=all` et les capacités `compute,utility`
comme les images CUDA ; l'allocation de l'instance doit restreindre la visibilité
aux GPU autorisés. Sur un hôte Docker NVIDIA local, utiliser `--gpus all` pour
injecter les pilotes. Sans GPU demandé, aucune bibliothèque de pilote n'est
injectée. Voir la [configuration officielle NVIDIA](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/docker-specialized.html).

OpenSSH est installé pour le transport `ssh_direct` de Vast. Les clés hôte
créées à l'installation sont retirées du même layer. Le défaut `CMD ["bash"]`
ne démarre aucun daemon ; le transport et la génération de nouvelles clés hôte
restent du ressort du lancement de l'instance. Aucun port API n'est exposé.

## Préparer le volume et télécharger la base

Sur une instance GPU explicitement autorisée, déposer seulement les deux
fichiers du corpus source validé dans :

```text
/workspace/data/manifest.json
/workspace/data/train-chat.jsonl
```

Le manifeste doit avoir le SHA-256
`71ce762b893d19d5918e183e8d76c88b365f326b3b7a3418af495f53084514f5` ;
le corpus source doit avoir le SHA-256
`9966a99f998f544fdfe3d9370f53e131e5ae31061b3e89ae196d3f34e56d6a65`.
Ces fichiers restent externes à Git et à l'image. Ils sont contrôlés avant
création d'un nouveau résultat d'entraînement.

Les commandes suivantes sont manuelles :

```sh
cp --no-clobber /opt/qwen-training/base-profile-7b.json /workspace/base-profile-7b.json
python /opt/qwen-training/download-model7b.py
```

Le téléchargement est anonyme, sans token implicite ni chargement de tensors.
Il épingle la révision `019cc73c45c770444708a6dd8690c66243cc5c80`, les neuf
fichiers du profil, leur SHA-256 et les identités Git/LFS publiées.
Les poids ont le SHA-256
`56a3d94706833f753e6c6b47ea57af8ef638cd8cc1d74eca1142ba640b26060e`.
Un dossier `model7b` ou un manifeste déjà présent bloque un nouveau download ;
les fichiers partiels d'un échec sont conservés pour examen explicite.
Les symlinks existants sont refusés ; le manifeste final est créé en mode
exclusif. Python `-O` est refusé afin de conserver les assertions de vérification.
Le disque doit disposer de la place des fichiers plus une réserve de 2 GiB.

## Smoke GPU puis entraînement explicite

Pour le premier essai, avec une limite de temps externe :

```sh
python -c 'import mlx.core as mx; assert mx.cuda.is_available(); mx.set_default_device(mx.gpu); x=mx.array([1,2,3]); y=x+1; mx.eval(y); assert y.tolist()==[2,3,4]; print("CUDA arithmetic passed")'

timeout --signal=TERM --kill-after=60s 15m \
  python /opt/qwen-training/train.py \
  --name cuda-smoke-001 --iters 3 \
  --base-profile /workspace/base-profile-7b.json \
  --corpus /workspace/data/train-chat.jsonl \
  --corpus-sha256 9966a99f998f544fdfe3d9370f53e131e5ae31061b3e89ae196d3f34e56d6a65
```

Pour une expérience approuvée, fournir un nouveau nom et un nombre d'itérations
en conservant un timeout et le budget au niveau de l'opérateur. Un corpus
supplémentaire exige son SHA exact et le même format de deux messages
`user`/`assistant` non vides. Aucun apprentissage ne tronque silencieusement
les séquences au-delà de 6 144 tokens. `--resume` accepte un fichier adapter
externe contenu dans `/workspace` ; son empreinte est inscrite au protocole.

Chaque nouveau run se trouve sous `/workspace/runs/<name>` et ne remplace
jamais un run existant. Le verrou est `/workspace/train.lock`. Le trainer
charge la base locale avec `trust_remote_code=False` et le réseau Hugging Face
désactivé, enregistre protocole et empreintes, puis contrôle que tous les
tensors de l'adapter final sont finis. Une limite de mémoire peut faire échouer
le run ; elle ne garantit pas l'absence d'OOM du pilote ou des bibliothèques.

Exporter les résultats et vérifier leurs empreintes avant d'arrêter ou de
détruire une instance. La location, le coût, le timeout, l'export et la
destruction de l'instance restent des opérations externes à cette image.
Le smoke ne sélectionne pas un adapter et n'autorise aucune fabrication.

## Provenance et limites

[`inputs.json`](inputs.json) enregistre les empreintes du bundle local
`vast-pilot-20261014/remote-bundle` et les adaptations minimales : racine
`/workspace`, modules en `/opt`, corpus obligatoire, profil 7B exact, garde des
chemins, manifeste/corpus vérifiés avant création d'un run, download neuf
fichiers contrôlé contre le profil. `base_runtime.py` et le profil restent
identiques au bundle vérifié. La boucle de training, ses hyperparamètres,
contrôles tensors et receipts sont conservés.

Aucune image n'est publiée par ces commandes. Le build et le smoke CPU doivent
être distingués du test CUDA sur une vraie instance et des évaluations PicoGK
indépendantes. Un adapter entraîné n'est pas une preuve géométrique ou physique.
