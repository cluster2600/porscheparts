# Preuve moteur OpenFOAM F37 — portée exacte

Ce dossier ferme explicitement la demande `iceEngineFoam` sans transformer un
tutoriel en preuve de culasse. L'image de calcul installée ne contient aucun
exécutable `iceEngineFoam`, `engineFoam`, `XiEngineFoam` ou `coldEngineFoam`.
OpenFOAM Foundation 13 fournit à la place le chemin modulaire `foamRun`, le
module `XiFluid` et le moteur de maillage `multiValveEngine`.

Le tutoriel officiel `XiFluid/engine2Valve2D` a réellement été maillé puis
exécuté de 0 à 110 degrés vilebrequin sur x86_64. Le passage de topologie à
100 CAD, du maillage fermé de 2 178 cellules au maillage ouvert de 3 966
cellules, a été traversé. `checkMesh` et les deux exécutions se terminent avec
un code nul.

Cela démontre seulement que la chaîne moteur mobile installée fonctionne. Le
cas est 2D, générique et à deux soupapes. Il n'emploie aucune géométrie F37.
La pression Cantera F33 demeure une charge structurelle aval non corrélée; elle
n'a pas été injectée dans ce tutoriel.

Les logs complets restent sur l'instance de calcul et sont liés par SHA-256
dans `report.json`. Seuls le contrôle de maillage complet et un extrait borné
du solveur sont publiés ici. Aucun maillage moteur ni scan brut n'est publié.

Verdict : chemin solveur moteur **PASSE**; calcul moteur F37 **BLOQUÉ**; métal
imprimable et démarrage moteur **NON AUTORISÉS**.
