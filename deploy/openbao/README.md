# Wrapper OpenBao pour GHCR

Ce dossier versionne les wrappers Vast.ai et GHCR utilisés pour l'image
SimReady locale. Il ne contient aucun secret. `openbao-vastai` garde la
location, l'unicité et la destruction ; `openbao-ghcr` vérifie l'accès au
digest puis délègue uniquement l'offre explicitement relue.

Le wrapper est volontairement borné à :

- la lecture du secret existant `secrets/github` via une AppRole dédiée ;
- l'identité GHCR `cluster2600` ;
- l'image `cluster2600/3dprinting993-simready-local-ai` ;
- le digest OCI déclaré dans `openbao-ghcr` ;
- une opération de lancement SimReady explicite du wrapper `openbao-vastai`.

Il accepte un token stocké sous l'un des champs `GITHUB_TOKEN`, `GH_TOKEN`,
`github_token` ou `token`. Sa valeur n'est jamais imprimée. Le wrapper vérifie
l'accès au manifeste épinglé localement, puis lance l'image publique sans
transmettre le token à Vast.ai.

## Installation

Le secret GitHub doit déjà exister. Le script de provisionnement contrôle
uniquement ses métadonnées, crée une politique de lecture exacte et installe le
wrapper dans `~/.local/bin` :

```zsh
cd /Users/maxime/projects/3dprinting993
install -m 0755 deploy/openbao/openbao-vastai /Users/maxime/.local/bin/openbao-vastai
bash deploy/openbao/provision-openbao-ghcr.sh
rehash
openbao-ghcr --check
openbao-ghcr --auth-check
```

`--check` ne lit pas le secret. `--auth-check` lit temporairement le token via
l'AppRole, vérifie le manifeste GHCR, puis révoque le jeton de session OpenBao.

Le lancement reste séparé de l'installation :

```zsh
openbao-vastai heavy-offers
openbao-ghcr launch-vast-simready-heavy OFFER_ID
```

L'identifiant reste obligatoire : l'offre doit être relue avant location. Le
wrapper Vast refuse un second contrat portant le label du projet et contrôle
l'unicité après création.
