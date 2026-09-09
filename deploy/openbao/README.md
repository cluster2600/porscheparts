# Wrappers OpenBao pour GHCR et Vast.ai

Ce dossier versionne les wrappers Vast.ai et GHCR utilisés pour l'image
SimReady locale. Il ne contient aucun secret. `openbao-vastai` garde la
location, l'unicité et la destruction ; `openbao-ghcr` vérifie l'accès au
digest puis délègue uniquement l'offre explicitement relue. Le chemin F39
utilise directement l'image publique immuable et ne transmet aucun identifiant
GHCR à Vast.ai.

Le wrapper est volontairement borné à :

- la lecture du secret existant `secrets/github` via une AppRole dédiée ;
- l'identité GHCR `cluster2600` ;
- l'image `cluster2600/3dprinting993-simready-local-ai` ;
- le digest OCI déclaré dans `openbao-ghcr` ;
- une opération de lancement SimReady explicite du wrapper `openbao-vastai`.
- l'image F39 publique
  `ghcr.io/cluster2600/3dprinting993-wave-action-f39@sha256:742569a45becdd00b9f8d32b057156e68d0bb0489cef1fa97d2e6543fce096a3` ;
- une offre F39 relue par identifiant, à 1,25 USD/h maximum, avec au moins
  64 threads CPU effectifs, 256 000 MB de RAM et 300 GB de disque ;
- une machine vérifiée, de fiabilité minimale 0,985, louable et non déjà louée.

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

openbao-vastai wave-offers
openbao-vastai launch-wave-f39 OFFER_ID
```

L'identifiant reste obligatoire : l'offre doit être relue avant location. Pour
SimReady, le wrapper Vast refuse un second contrat portant le label du projet
et contrôle l'unicité après création.

Pour F39, `wave-offers` demande le prix total avec 300 GB de stockage puis
réapplique localement chaque seuil. `launch-wave-f39` refait la correspondance
exacte sur l'identifiant et revalide l'offre immédiatement avant l'appel payant.
Le conteneur utilise `ssh_direct`; son `onstart` exécute
`/opt/917-engine-wave-f39/smoke.py`. Il supprime d'abord tout ancien
`/workspace/READY`, puis ne recrée ce marqueur que si le smoke termine sans
sortie d'erreur.

Ce `onstart` est obligatoire : la documentation officielle Vast.ai précise
que les modes SSH/Jupyter remplacent l'`ENTRYPOINT` de l'image par celui de
Vast, puis exécutent `onstart` après cette initialisation. Voir
[Creating Instances with the API](https://docs.vast.ai/api-reference/creating-instances-with-api).
Le wrapper effectue aussi un prévol d'unicité sous verrou local et refuse de
louer si une instance portant déjà le label F39 existe. Après création, il
relit la liste complète et exige que l'identifiant retourné soit l'unique
instance portant ce label. Il relit ensuite le contrat Vast et exige le digest
immuable, le label, un état final `running`, au moins 64 threads CPU effectifs,
256 000 MB de RAM, 300 GB de disque, un prix total au plus égal à 1,25 USD/h et
une machine vérifiée. Le succès n'est annoncé qu'après une connexion OpenSSH
en `BatchMode`, avec la clé privée approuvée `~/.ssh/id_vastai` explicitement
sélectionnée, puis lecture et validation de `/workspace/READY`, du JSON smoke
et de l'absence de sortie d'erreur. La clé n'a donc pas besoin d'être chargée
dans `ssh-agent`; son contenu privé n'est jamais lu ni affiché par le wrapper.

Toute erreur de cette vérification post-création détruit exactement
l'identifiant retourné et exige que sa disparition soit confirmée dans la liste
paginée. Après un résultat de création incertain (erreur réseau, erreur sûre du
wrapper ou HTTP 5xx), le wrapper réconcilie le label F39 : il détruit et vérifie
absente l'unique instance correspondante. Il ne détruit rien automatiquement si
plusieurs identifiants portent ce label, et une réponse HTTP 4xx certaine ne
déclenche aucun nettoyage destructif. L'appel de création payant n'est jamais
retenté automatiquement : aucune branche ne peut créer implicitement une
seconde instance.

Si aucune instance n'est observable avant l'expiration de la fenêtre de
réconciliation d'un lancement incertain, le wrapper échoue explicitement et
interdit toute relance automatique : il faut d'abord inspecter la liste des
instances. De même, `stop ID` exige à la fois l'accusé de réception de Vast.ai
et la relecture de l'état final `stopped` avant d'annoncer le succès.

L'offre `#49655039` est uniquement un candidat communiqué par l'utilisateur le
2 septembre 2026. Sa présence dans les tests est une fixture : elle ne garantit
ni sa disponibilité actuelle, ni son prix futur, et n'atteste aucune location.
Il faut impérativement la revoir dans la sortie courante de `wave-offers` avant
de lancer la commande avec cet identifiant ou tout autre identifiant conforme.
