# Image CFD/CAE F47 pour la campagne F46

## Résultat actuel

F47 fournit une recette `linux/amd64` unique et un transport compatible avec le
contrôleur F46. Elle assemble OpenFOAM Foundation 14, les utilitaires officiels
AATE/OpenFOAM ICengines à la révision `c0f75f`, Cantera 3.2.0, Gmsh et
CalculiX. Elle n'embarque ni scan, ni domaine moteur, ni carte matériau, ni
secret.

Ce lot ne rend pas les 26 cas exécutables. Le manifeste F46 contient toujours
zéro cas prêt : les domaines 2V/4V, lois de soupape, cartes matériau à chaud et
commandes liées par SHA restent absents. Une image verte prouve seulement que
les solveurs et le superviseur peuvent exécuter leurs fixtures génériques.

Le build natif réellement exécuté sur la machine Kali `x86_64` a produit
l'image locale `sha256:a233511bef9b4fbf0653ca94258061d61b3fccbd6b4e3ef6d71c669d70de1c17`
de 2 212 871 101 octets. La passe finale à caches chauds a duré environ
23 secondes, dont 21,5 secondes de smokes. Le parcours initial avec
téléchargement des dépendances a pris environ huit minutes; cette durée est une
observation opérateur, pas une mesure instrumentée. La preuve structurée est
[`kali-local-build.json`](../twins/reference-917-engine/evidence/f47-cfd-cae-image/kali-local-build.json),
SHA-256 `457b133c4a8a2187ffb0c12696694a35187da7175cdfc8aec47032d989cfeee4`.

## Autorité solveur

- OpenFOAM 14, paquet `20260724`, exécute la fixture de Poiseuille F25.
- AATE/OpenFOAM ICengines est compilé depuis la révision officielle
  `c0f75f953d67cd325d28d1300672d14288f22934`; quatre utilitaires réels sont
  invoqués.
- Cantera est verrouillé à 3.2.0 par quatre roues `linux/amd64` avec SHA-256.
- Gmsh maille un cylindre à section circulaire; aucune section elliptique ou
  ovale n'est autorisée.
- CalculiX résout un cube élastique générique.
- `foamMultiRun` exécute deux pas réellement couplés fluide/métal/chauffage de
  la fixture officielle `heatedDuct`; ce smoke CHT reste générique.
- Le solveur historique `engineFoam` n'est pas compilé. Il reste explicitement
  optionnel et `not_built`.
- Aucun exécutable, lien ou alias nommé `ICEEngineFoam` n'est créé. Le nom ne
  désigne pas un binaire officiel prouvé dans l'autorité F46.

## Séparation root / calcul

Vast `ssh_direct` impose un transport root afin de recevoir la clé publique et
de démarrer `sshd`. Ce root est limité aux clés hôte éphémères, au prévol et au
watchdog. `f46-run-manifest`, les smokes et tous les solveurs tombent sous
`9147:9147`, sans groupes supplémentaires et avec `no-new-privs`.

`f46-vast-onstart --deadline-epoch EPOCH` refuse une échéance passée ou située
à plus de huit heures. Il arme un watchdog distant indépendant des API Vast.
À l'échéance, ce watchdog crée `/workspace/F46_STOP`, envoie `SIGTERM` aux seuls
processus UID 9147, attend 30 secondes puis envoie `SIGKILL`. La destruction de
l'instance et la preuve d'inventaire vide restent la responsabilité du
contrôleur local F46.

Le runner refuse les plans non autorisés, les commandes shell sous forme de
chaîne, les fichiers hors `/workspace/f46`, les SHA d'entrée incorrects, une
deadline échue et les jetons de géométrie interdits. Il exécute chaque commande
comme tableau d'arguments, une seule famille lourde à la fois.

## Publication fail-closed

Le workflow manuel construit uniquement `linux/amd64`, publie un candidat avec
SBOM et provenance BuildKit, vérifie l'index OCI et le manifeste plateforme,
puis exerce les smokes CPU hors ligne. Il ne fabrique pas une preuve GPU.
Le dépôt cible est verrouillé à
`ghcr.io/cluster2600/3dprinting993-cfd-cae-f46`; la référence consommable par
le contrôleur doit toujours être son digest OCI `@sha256:...`, jamais un tag.

La qualification F46 complète reste fermée tant que toutes ces preuves ne sont
pas simultanément réelles :

1. `nvidia-smi` réel et allocation CUDA Driver API de 4096 octets;
2. digest GHCR, manifeste `linux/amd64`, SBOM et provenance vérifiés;
3. nouveau pull anonyme par digest et smoke identique;
4. preuve image commise puis verrouillée dans le contrat F46.

Le build CPU local, même réussi sur Kali, ne peut donc ni ouvrir
`F46_runtime_smoke_verified`, ni autoriser Vast.

## Reproduction locale native

Depuis une copie propre du dépôt sur un hôte Docker `x86_64` :

```sh
docker build --platform linux/amd64 \
  -f containers/917-f47-cfd-cae/Dockerfile \
  -t 3dprinting993-cfd-cae-f47:local .

docker run --rm --platform linux/amd64 --user 9147:9147 \
  --entrypoint /usr/local/bin/f47-image-smoke --network none --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,size=2g \
  --tmpfs /workspace:rw,nosuid,nodev,uid=9147,gid=9147,mode=0750,size=2g \
  --pids-limit 512 --cap-drop ALL --security-opt no-new-privileges \
  3dprinting993-cfd-cae-f47:local
```

La recette verrouille les images de base, les roues Python, l'archive AATE et
les versions APT directes. Elle n'est pas déclarée reproductible bit à bit :
les dépendances APT transitives ne sont pas encore chacune verrouillées par
artefact et SHA-256.

## Limite d'ingénierie

Toutes les fixtures F47 sont synthétiques et génériques. Elles ne valident ni
la combustion, ni le refroidissement, ni la résistance de la culasse, ni une
impression 3D. Les portes physiques, fabrication, démarrage moteur et
installation véhicule restent fermées.
