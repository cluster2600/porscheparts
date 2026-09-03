# F41 — preuve de publication de l'image Vast CAD

Ce dossier conserve uniquement une preuve textuelle de publication de l'image
de transport et de CAO F41. Le workflow GitHub Actions
[`33699574489`](https://github.com/cluster2600/3dprinting993/actions/runs/33699574489)
s'est terminé avec la conclusion `success` sur le commit
`7eec184437fc71f10d6a8f07aa4ba2e518a058bb`.

## Résultat vérifié

L'index OCI publié est :

`ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:7155af27ddd4c909c29bbd599dbe18472661c0c5d6575906371a16e7420b7fce`

- manifeste `linux/amd64` :
  `sha256:320be537646fdd41fe3fdb3d66c764ef746fc8561475f6e1ae1d13514bad8ffd` ;
- manifeste d'attestation :
  `sha256:c1d3a108058e80e8cc5f762855a360ec0695a7301a9987494275d901d3516de6` ;
- taille compressée du manifeste d'exécution, configuration et couches :
  `254 619 946` octets ;
- le contrôle du budget d'ajout local de `16 000 000` octets a réussi dans le
  workflow ; la taille décompressée exacte n'est pas dupliquée dans cette preuve ;
- artefact de preuves GitHub Actions : `9873059134`, taille `363 235` octets,
  digest `sha256:867b816661183d588df2f042db96a3880cece5ac90a114f42fde9ae816b36447`.

Toutes les étapes du workflow ont réussi, notamment les smokes synthétiques, le
contrôle de l'image de base, le prévol `/workspace/READY` et le pull anonyme du
digest exact. Cela qualifie la publication OCI et autorise ce digest uniquement
comme candidat à sa première qualification Vast supervisée. Cela ne qualifie ni
le runtime Vast ni une exécution distante de la fabrique de composants.

La première tentative Vast est documentée dans
[`../f41-vast-runtime-attempt-1/`](../f41-vast-runtime-attempt-1/). Elle a échoué
avant le transfert du bundle et avant la CAO ; l'instance est absente, mais le
runtime et le lot F41 restent non qualifiés. Le digest demeure seulement un
candidat pour un nouvel essai supervisé sur un autre hôte.

## Limites de la preuve

Le STEP utilisé par les smokes est synthétique. Aucun composant moteur F41 réel
n'a été généré ou validé par cette publication. Les gates de CAO réelle,
validation dimensionnelle, corrélation physique, simulation moteur,
fabrication, impression métallique et démarrage restent toutes à `false`.

Ce dossier ne contient aucun scan, modèle 3D, rendu, archive OCI, artefact du
workflow, secret ou autre actif binaire. `README.md` et `summary.json` sont les
deux seules preuves publiées ici.
