# Variantes paramétriques du côté froid

Ce dossier contient trois variantes exploratoires du même diffuseur froid
stationnaire :

| Variante | Usage | Statut de la géométrie |
| --- | --- | --- |
| `K16-OEM` | contrôle de référence | hypothèse conservant le premier harnais |
| `K16-24-HYBRID` | sensibilité hybride | hypothèse autour de l'inducer FVD de 47,5 mm |
| `K24-REFERENCE` | sensibilité haut débit | hypothèse, aucune géométrie K24 publique exploitable |

La source de vérité est [`variants.json`](variants.json). Les sources
préparateurs sont attachées aux variantes comme références déclarées, mais leurs
cibles de puissance ne sont pas injectées dans le solveur. Le débit est le même
pour les trois cas (`0,156 kg/s` par turbo) afin d'isoler l'effet de la section
synthetique ; les vitesses d'entrée sont dérivées de la densité et de la section.

Les dossiers sous `cases/` sont générés par
[`scripts/generate_turbo_variants.py`](../../scripts/generate_turbo_variants.py).
Ils contiennent les champs OpenFOAM et le `blockMeshDict` correspondant. Le
maillage produit reste un conduit rectangulaire à section équivalente : il ne
contient aucune roue, volute, CHRA, wastegate, interface de bride ou surface
mesurée du K16/K24.

## Utilisation

Depuis la racine :

```bash
make turbo-variants
make turbo-variants-check
```

Dans le conteneur `cadsim`, pour un cas donné :

```bash
source /opt/openfoam13/etc/bashrc
cd /workspace/simulation/993-turbo-variants/cases/K16-OEM
blockMesh
checkMesh
simpleFoam
```

Les trois cas sont des comparaisons numériques relatives et non une validation
de turbo. Il manque toujours une CAO ou un scan licencié, les cartes
compresseur/turbine, les profils d'aubes, les jeux, les températures, la vitesse
de rotor et les données brutes de banc. Aucune pièce tournante ou chargée ne
doit être fabriquée à partir de ces fichiers.
