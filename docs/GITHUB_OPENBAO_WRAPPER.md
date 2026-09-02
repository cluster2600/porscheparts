# Wrapper GitHub borné par OpenBao

`deploy/openbao/openbao-github` pousse uniquement la branche `codex/*` courante
du dépôt `cluster2600/3dprinting993` et déclenche uniquement les deux workflows
Vast F40/F41 explicitement autorisés. Il réutilise l'AppRole déjà provisionnée
pour `openbao-ghcr`; aucun jeton n'est ajouté au dépôt ou à la ligne de commande.

Le wrapper désactive le helper Git du trousseau macOS pour son sous-processus.
Il transmet l'en-tête HTTP d'authentification à Git par configuration
d'environnement éphémère, sans URL contenant un secret, masque défensivement
la valeur avant toute erreur et révoque toujours le jeton de session OpenBao.

## Installation et contrôles

```zsh
cd /Users/maxime/projects/3dprinting993
install -m 0755 deploy/openbao/openbao-github \
  /Users/maxime/.local/bin/openbao-github
rehash
openbao-github --check
openbao-github --auth-check
```

`--check` ne lit aucun secret. `--auth-check` vérifie uniquement le dépôt fixe et
exige que l'identité GitHub renvoie l'autorisation `push`.

## Opérations autorisées

Le worktree doit être propre avant un push :

```zsh
openbao-github push-current
```

Après publication de la branche, un workflow peut être déclenché par son nom
exact et la même branche :

```zsh
openbao-github dispatch 917-engine-wave-f40-vast-image.yml \
  codex/917-f40-vast-runtime-hardening

openbao-github runs 917-engine-wave-f40-vast-image.yml \
  codex/917-f40-vast-runtime-hardening

# Reconstruire et publier uniquement la grande image SimReady locale.
# Le wrapper fixe les inputs image=simready-local-ai et push=true.
openbao-github publish-simready-local-ai \
  codex/917-f40-vast-runtime-hardening
```

Le second workflow autorisé est
`917-component-factory-f41-vast-image.yml`. Aucun workflow arbitraire, branche
`main`, fork, autre dépôt, création de PR ou fusion n'est exposé par ce wrapper.

## Frontière de confiance

Un push réussi ne prouve ni que GitHub Actions est vert, ni qu'un digest GHCR
est public, ni que Vast peut établir une session SSH. Ces états sont vérifiés
séparément avant toute location. Le wrapper n'envoie aucun scan, manuel,
identifiant de véhicule ou donnée privée : seuls les objets Git déjà committés
sur une branche `codex/*` peuvent être poussés.
