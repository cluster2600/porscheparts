# Poste PicoGK M64 pour Vast — géométrie headless

Le Dockerfile canonique est `containers/picogk-m64.Dockerfile`, avec le dépôt
comme contexte de build. Il compile le runtime C++ officiel et le code C#
épinglés, conserve leurs sources/licences, puis ajoute SSH, un témoin de
géométrie et l'application `HeadVoxels`. Il ne contient aucun scan ni CAO privée.

## Construction et test

```sh
docker build --platform linux/amd64 -f containers/picogk-m64.Dockerfile \
  -t 3dprinting993-picogk-m64:preflight .
docker run --rm --network none --cpus 2 --memory 4g \
  3dprinting993-picogk-m64:preflight smoke-test.sh picogk-m64
```

Pour réutiliser le runtime natif déjà contrôlé sur Kali : vérifier d'abord
que l'image `3dprinting993-m64-leap71:native-preflight` porte l'identifiant
`sha256:f38695f9ecc99ceef65c5e1fe02adf5dbfa95ee1ae925f95fd47bdba9ebb6178`,
puis ajouter à la construction :

```text
--build-arg NATIVE_IMAGE=3dprinting993-m64-leap71:native-preflight
```

Cette substitution est un cache local vérifié, pas une référence de registre
immuable. La publication CI reconstruit le stage natif depuis les sources.
Une location doit employer le **digest GHCR publié et revérifié**, pas le tag
local ni l'identifiant Docker local.

Le manifeste de base est fixé par SHA-256, le SDK vérifié est **9.0.317**,
le runtime .NET **9.0.19**, les sources et sous-modules sont fixés par commits.
Les paquets Debian résolus sont inventoriés sous `/opt/provenance/`, ainsi que
le hash de la bibliothèque et le rapport du témoin. Les miroirs Debian et
les dépendances NuGet transitives ne sont pas figés dans un snapshot/lock :
ce build est reproductible procéduralement, **pas garanti identique bit à bit**.

## Fonctionnement et interfaces

- `smoke-test.sh picogk-m64` : crée une sphère témoin de rayon 5 mm à voxels
  de 0,5 mm, exporte/recharge son STL, compare son volume à la solution
  analytique avec un seuil de smoke de 10 %, vérifie l'effet d'un offset
  positif, puis exécute `HeadVoxels` sur ce témoin. Aucun serveur X ni GPU.
- `dotnet /opt/m64/HeadVoxels.dll INPUT_STL NEW_OUTPUT_DIR VOXEL_MM` : traite
  une copie du maillage fourni, sans transformation du repère ni écrasement
  du master. Ce programme est géométrique, pas un solveur physique.
- `LD_LIBRARY_PATH=/app` résout le runtime ABI `picogk.26.2.so`.
- Les sources officielles restent dans `/upstream`; les API avancées non
  couvertes par le témoin ne sont pas déclarées testées.

## Démarrage Vast et arrêt

Commande de prévol pour `ssh_direct` :

```text
picogk-vast-onstart --deadline-epoch UNIX_SECONDS
```

Elle refuse un délai passé ou supérieur à trois heures. Le témoin natif
réussit avant l'écriture de `/workspace/PICOGK_READY`, dont le contenu est
`PICOGK_M64_READY`; son rapport est `/workspace/picogk-smoke/report.json`.
La commande se termine après le prévol. Vast démarre SSH avant `onstart` et
peut remplacer `ENTRYPOINT` : le shim SSH éprouvé du dépôt crée donc les
clés hôte avant le vrai démon. Le prévol n'ouvre pas un second serveur.
Le fichier `/root/.no_auto_tmux` assure les commandes SSH non interactives.
Le lanceur doit vérifier réellement la connexion SSH et le marqueur.

L'authentification accepte uniquement une clé publique fournie à l'exécution
par `PUBLIC_KEY` ou un fichier `authorized_keys` monté. Aucun secret ni clé
privée n'est embarqué. Les clés hôte générées par l'installation du paquet
sont supprimées dans la même couche; de nouvelles clés sont créées à chaque
démarrage de conteneur. Mots de passe et clavier interactif sont désactivés.

**Le délai est enregistré dans `/workspace/PICOGK_DEADLINE_EPOCH`, mais ne
constitue pas un arrêt de facturation.** Chaque calcul nécessite son propre
`timeout`; un garde-fou externe doit détruire l'instance à cette échéance et
confirmer sa disparition. Le prévol ne prétend pas assurer cette destruction.

## Limite de la preuve

Le témoin vérifie une installation logicielle et certaines opérations de
géométrie. Sa sphère n'est jamais une forme de culasse, une proposition de
refroidissement, un calcul de résistance ou une validation d'impression.
Le moteur PicoGK est volumique : un export STL n'est pas une reconstruction
B-Rep exacte et n'établit aucune aptitude mécanique ni compatibilité M64.
