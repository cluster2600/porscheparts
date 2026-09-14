# F35 — image OpenFOAM moteur CPU

## Périmètre

`openfoam-engine-f35` est une image dédiée `linux/amd64`, non-root, destinée au
nœud Intel. Elle contient OpenFOAM Foundation 14, OpenMPI et quatre utilitaires
du dépôt public ICengines/AATE verrouillé au commit
`c0f75f953d67cd325d28d1300672d14288f22934` :

- `engineMeshConfig` ;
- `moveSurfaces` ;
- `predictRemeshInstants` ;
- `reorderPatchesAndFaces`.

Le build compile ces outils depuis une archive dont le SHA-256 est vérifié. Les
liens auxiliaires pointant vers l'arbre de compilation sont supprimés avant la
copie multi-stage. L'image n'inclut ni Gmsh, ni scan, ni STEP Porsche, ni
mécanisme chimique, ni secret.

La base Ubuntu, les trois paquets demandés, le commit ICengines et son archive
sont verrouillés. La fermeture complète des dépendances transitives APT et
l'empreinte de la clé du dépôt OpenFOAM ne le sont pas encore octet par octet :
le digest OCI publié sera l'autorité de déploiement, mais une reconstruction
future peut diverger tant que ce verrou de supply chain n'est pas ajouté.

## Smoke réel mais synthétique

Le smoke génère deux cas de Poiseuille depuis le contrat F25, puis exécute :

1. `blockMesh`, `checkMesh` et `foamRun` en série ;
2. `blockMesh`, `decomposePar` et `foamRun` sur deux rangs OpenMPI.

Il vérifie OpenFOAM 14, la version du paquet, les quatre exécutables et les deux
bibliothèques ICengines. Sa sortie conserve explicitement
`engine_simulation_proved=false` et `performance_1600_hp_proved=false`.

```bash
make 917-openfoam-engine-f35-test
make 917-openfoam-engine-f35-image
make 917-openfoam-engine-f35-smoke
```

Le smoke durci est exécuté sans réseau, avec le système de fichiers en lecture
seule, toutes les capabilities supprimées, `no-new-privileges`, un `/tmp` et un
`/dev/shm` éphémères. Il ne constitue ni un cas moteur mobile, ni une simulation
de combustion.

## Publication

Le workflow manuel GitHub construit sur `main`, publie un candidat GHCR
`linux/amd64`, vérifie digest, provenance, SBOM, UID/GID et smoke durci. Il se
déconnecte ensuite de GHCR et répète pull et smoke avec une configuration Docker
anonyme vide. Le digest, pas le tag, est l'autorité de reproduction.

Le déclenchement exige une confirmation explicite de la revue GPL et de l'accès
au code source correspondant d'OpenFOAM et ICengines. Cette confirmation reste
un gate de publication : elle ne remplace pas le dossier de conformité ni les
obligations de redistribution applicables.

Le verrou `containers/openfoam-engine-f35.lock.json` reste entièrement fermé
jusqu'à réussite de cette publication. Même après publication, tous les gates
physiques restent fermés : géométrie 917, maillage mobile, combustion, spray,
CHT, convergence de maillage, corrélation banc, fabrication et 1 600 ch.

Sources amont :

- [OpenFOAM Foundation 14](https://openfoam.org/version/14/) ;
- [OpenFOAM ICengines](https://github.com/OpenFOAM/ICengines) ;
- [Open MPI](https://www.open-mpi.org/).
