# Correctif du contrat Marangoni pour OpenFOAM 14

Ce patch ajoute uniquement `assignable() const { return false; }` à la
condition Marangoni ORNL. Il permet à `constrainHbyA` de préserver la
condition normale lors de la construction du prédicteur de pression.
Il ne modifie ni `evaluate`, ni `snGrad`, ni les équations de pression,
ni les propriétés matériau. Ce n'est pas une qualification de culasse.

Le fichier amont, sous **GPL-3.0-or-later**, est
[`marangoniFvPatchVectorField.H`](https://github.com/ORNL/AdditiveFOAM/blob/9c05c5eb54db03faa342b14b0806efe740de8c44/applications/solvers/additiveFoam/derivedFvPatchFields/marangoni/marangoniFvPatchVectorField.H).
Le patch est distribué sous la même licence. Le contexte testé est
OpenFOAM 14, commit `7b05503f98a85be88af930df48623b4d152bfc35`.
Le diff est sans lignes de contexte : l'empreinte exacte d'entrée ci-dessous
est donc une précondition, et l'empreinte de sortie doit être vérifiée.

Empreintes SHA-256 du header :

- Entrée exigée : `bb21f5c705425c6903945f9ca95055d6ca4083d8b9d58e1b15e2a1c75deb022a`.
- Sortie testée : `c1bb4ab01a24a907aefda0995d7df650d4dc46c23f61f9d1130bd7d6a601a33c`.

Sur une **copie neuve des sources** du solveur, depuis le dossier qui
contient `derivedFvPatchFields/`, vérifier le hash d'entrée avant d'appliquer
le patch avec `patch -p1`. Refuser toute différence d'empreinte ou tout
contexte ambigu ; ne pas remplacer un binaire historique en place.
Recompiler ensuite le solveur dans un répertoire de sortie séparé et
enregistrer les empreintes des sources, bibliothèques et exécutable.

Le [témoin natif ancien/nouveau](../../../../docs/M64_F58_PREDICTOR_CONTRACT_20260908.md)
vérifie la conservation de la traction et l'étape native `adjustPhi`.
Une réussite de ce témoin ne suffit pas à accepter un coupon LPBF : ses
bilans, son couplage, sa convergence et sa calibration physique restent
des contrôles distincts.
