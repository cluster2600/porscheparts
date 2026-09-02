# F41 — preuve de publication de l'image Vast CAD

Ce dossier conserve uniquement une preuve textuelle de publication de l'image
de transport et de CAO F41. Le workflow GitHub Actions
[`33688171549`](https://github.com/cluster2600/3dprinting993/actions/runs/33688171549)
s'est terminé avec la conclusion `success` sur le commit
`cfe575586a05a69b91e1332fbffff3fe4400b494`.

## Résultat vérifié

L'index OCI publié est :

`ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:dd0a9745badb03a30a795509b442e53ac27675d1ee8f08ef8dfd3498be4b4c16`

- manifeste `linux/amd64` :
  `sha256:41c76d24a94c9efce2c175ef99aa41d6c2cd70da3d60dfccff0d0ff67881674c` ;
- manifeste d'attestation :
  `sha256:4860ee7ced377eefa95f922c20a9e14b79cb47db8295edb4194468b28346258b` ;
- taille de l'image : `854 676 395` octets ;
- taille de l'image de base : `843 284 017` octets ;
- ajout local : `11 392 378` octets, sous la limite de `16 000 000` octets ;
- artefact de preuves GitHub Actions : `9868983980`, digest
  `sha256:6917ca5e6fdbde5067c9e6d8ddbae5b7c569ee1af230fca8a0d40696790e911a`.

Toutes les étapes du workflow ont réussi, notamment les smokes synthétiques, le
contrôle de l'image de base, le prévol `/workspace/READY` et le pull anonyme du
digest exact. Cela qualifie la publication OCI et le chemin de démarrage de
l'image, pas une exécution distante de la fabrique de composants.

## Limites de la preuve

Le STEP utilisé par les smokes est synthétique. Aucun composant moteur F41 réel
n'a été généré ou validé par cette publication. Les gates de CAO réelle,
validation dimensionnelle, corrélation physique, simulation moteur,
fabrication, impression métallique et démarrage restent toutes à `false`.

Ce dossier ne contient aucun scan, modèle 3D, rendu, archive OCI, artefact du
workflow, secret ou autre actif binaire. `README.md` et `summary.json` sont les
deux seules preuves publiées ici.
