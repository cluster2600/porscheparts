# F35 — conteneur Gmsh de maillage CPU

## Périmètre

`gmsh-mesh-f35` est une recette minimale `linux/amd64`, sans GPU et non-root,
destinée au nœud Intel. Elle verrouille Python 3.12.14 par digest, Gmsh 4.15.2
par hash de wheel et les 24 paquets ELF Debian nécessaires par SHA-256.

Le smoke crée un cylindre OCC **synthétique**, définit les groupes physiques
`fluid_volume`, `inlet`, `outlet` et `wall`, génère des éléments 3D et refuse
les Jacobiennes nulles, négatives ou non finies. Aucun scan, STEP moteur,
maillage Porsche, secret, solveur CFD ou résultat physique n'entre dans l'image.

## Exécution locale

```bash
make 917-gmsh-mesh-f35-test
make 917-gmsh-mesh-f35-image
make 917-gmsh-mesh-f35-smoke
```

Le smoke d'exécution impose `--network none`, un système de fichiers en lecture
seule, un `/tmp` éphémère et l'UID/GID `9135:9135`. Sa réussite prouve seulement
que la recette sait mailler ce volume synthétique avec Gmsh 4.15.2.

## Publication et gates

Le workflow manuel construit un candidat GHCR `linux/amd64`, vérifie le digest
OCI, la provenance, le SBOM contenant Gmsh 4.15.2, le smoke durci puis un pull
anonyme du même digest. Un tag `verified-...` unique peut ensuite pointer ce
digest; aucun tag, y compris `latest`, n'est une autorité de reproduction.
Le manifeste d'inputs attestés inclut le lock fail-closed et son test en plus
de la recette, des verrous de dépendances et du smoke ; le test exige que cette
liste et le bloc `sha256sum` du workflow restent exactement alignés.
Le déclenchement exige aussi une confirmation explicite de la revue GPL et de
l'accès au code source correspondant; cette case n'est pas une preuve en soi et
doit être appuyée par la revue de conformité.

Le fichier `containers/gmsh-mesh-f35.lock.json` reste volontairement
fail-closed avec `publication_verified=false` tant que ces preuves n'existent
pas. Il sépare les gates logicielles des gates physiques. Aucune gate de
géométrie moteur, CFD, corrélation, fitment ou fabrication n'est ouverte par ce
lot.

## Licence et limites

Gmsh est distribué sous GPL v2 ou ultérieure, avec une exception de liaison
décrite par le projet. La GPL autorise l'usage commercial; la redistribution du
wheel et de `libgmsh` impose toutefois ses obligations, notamment l'accès au
code source correspondant. Les notices Debian sont copiées dans l'image, mais
le SBOM peut manquer des composants liés statiquement : une revue de conformité
et une offre de source accessible restent nécessaires avant publication
publique ou intégration fermée.

Sources officielles :

- [Gmsh — téléchargement, version et licence](https://gmsh.info/)
- [Documentation Gmsh 4.15.2](https://gmsh.info/doc/texinfo/gmsh.html)
- [Paquet Python Gmsh 4.15.2](https://pypi.org/project/gmsh/4.15.2/)
