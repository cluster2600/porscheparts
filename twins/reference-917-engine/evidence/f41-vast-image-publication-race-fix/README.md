# F41 — publication corrigée de l'image Vast CAD

Ce dossier conserve uniquement la preuve textuelle de la publication corrigeant
la course entre les appels `sshd` et `onstart`. Le workflow GitHub Actions
[`33708557585`](https://github.com/cluster2600/3dprinting993/actions/runs/33708557585)
s'est terminé avec la conclusion `success` sur le commit
`7ae01d2fb67fe13385726124f9dfac249b99e8ea`.

## Résultat vérifié

L'index OCI publié et tiré anonymement est :

`ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:c59c53b2611a1e3a9e9de5d2cedf8bfb0cd57e72582b2d6b29f6c8fc82bf7e6b`

- manifeste `linux/amd64` :
  `sha256:7a7f83cbe9f37e381ba763f2f7f1126d816c27c16712575cf5104d312045ac44` ;
- manifeste d'attestation :
  `sha256:fd1610badfd3a8d4f7fe3d09db61ac6551c3706ed057e13d59ecba863630df92` ;
- taille compressée de la configuration et des couches : `254 621 325` octets ;
- le budget d'ajout décompressé de `16 000 000` octets a réussi dans le workflow ;
- artefact de preuves : `9876138185`, taille `363 827` octets, digest
  `sha256:dac83038b4c394edee308559212dbabfecf5eae9dfc579678a40c7754e95b9b8`.

Toutes les étapes ont réussi, dont le smoke à froid sans pré-appel à `sshd`, le
smoke de contention qui observe réellement un enfant `flock`, les smokes CAO
synthétiques et le pull anonyme du digest exact. Cela autorise uniquement ce
digest comme candidat à une qualification Vast supervisée.

Le prédécesseur `sha256:7155af27…` reste révoqué. Ses preuves de publication et
d'échec Vast demeurent intactes dans `../f41-vast-image-publication/` et
`../f41-vast-runtime-attempt-1/`.

## Limites de la preuve

L'image corrigée n'a pas encore exécuté le lot F41 sur Vast. Aucun composant
moteur réel, STEP de production, assemblage, USD SimReady, calcul PhysicsNeMo,
résultat à 1 600 ch ou autorisation d'impression métallique n'est démontré ici.
Toutes ces gates restent fermées.

Ce dossier ne contient aucun scan, géométrie, archive OCI, artefact binaire,
secret ou journal runtime.
