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

## Installation courante

Le secret GitHub et les deux AppRoles dédiées doivent déjà exister. La voie
courante installe uniquement les sources versionnées, sans opération
administrative OpenBao :

```zsh
cd /Users/maxime/projects/3dprinting993
install -m 0755 deploy/openbao/openbao-vastai /Users/maxime/.local/bin/openbao-vastai
install -m 0755 deploy/openbao/openbao-ghcr /Users/maxime/.local/bin/openbao-ghcr
rehash
openbao-vastai --check
openbao-vastai --auth-check
openbao-ghcr --check
openbao-ghcr --auth-check
```

`--check` ne lit pas le secret. `--auth-check` lit temporairement le token via
l'AppRole, vérifie le manifeste GHCR, puis révoque le jeton de session OpenBao.

Le script `provision-openbao-ghcr.sh` est réservé à l'initialisation
administrative ponctuelle d'une AppRole absente. Il est hors de la procédure
courante et ne doit pas être relancé lorsque l'identité dédiée existe déjà.

Le lancement reste séparé de l'installation :

```zsh
openbao-vastai heavy-offers
openbao-ghcr launch-vast-simready-heavy OFFER_ID
```

L'identifiant reste obligatoire : l'offre doit être relue avant location. Le
wrapper Vast refuse un second contrat portant le label du projet et contrôle
l'unicité après création.
