# Cas CFD exploratoire du côté froid

Ce dossier est le premier harnais de simulation du jumeau numérique. Il étudie
un diffuseur fixe paramétrique, sans roue, sans arbre, sans CHRA et sans carter
chaud. La géométrie éditable est
[`cold_side_concept.scad`](../../parts/993-turbocharger-k16-cold-side-prototype/source/cold_side_concept.scad).

Le fichier `parameters.json` sépare les paramètres de conception des données
K16 déclarées par des fournisseurs. Les valeurs K16 servent de contexte et de
contrôle d'encombrement seulement ; elles ne sont pas utilisées pour inventer
les profils aérodynamiques internes.

Le maillage OpenFOAM est volontairement un conduit rectangulaire à section
équivalente. Il permet de vérifier la chaîne `blockMesh` → `simpleFoam` et de
comparer des variantes de diffuseur. Ce n'est pas une représentation CAO du
K16 et les conditions d'entrée sont synthétiques.

## Utilisation

Depuis la racine du dépôt :

```bash
make turbo-cold-side
make turbo-cold-side-check
```

Dans l'image `3dprinting993-cadsim` :

```bash
source /opt/openfoam13/etc/bashrc
cd /workspace/simulation/993-k16-cold-side-baseline
blockMesh
checkMesh
simpleFoam
```

Le cas a été exécuté dans l'image locale `3dprinting993-cadsim:dev` le
30 août 2026 : OpenFOAM a généré le maillage, `checkMesh` a conclu `Mesh OK` et
le solveur a terminé les 500 itérations avec un code de sortie nul. Ce résultat
est un smoke test de la chaîne ; il ne constitue pas une preuve de convergence
physique ni une validation du K16.

Les résultats de solveur doivent rester dans un répertoire de travail ignoré
par Git. Le cas ne constitue pas une validation de pièce, une autorisation de
fabrication ou une preuve de compatibilité avec le véhicule.
