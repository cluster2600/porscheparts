# Audit OpenFOAM F0 — embout ovale IN625

L'audit relie le rapport CFD publie a `24` artefacts bruts presents sur la machine Linux : cas, maillages et journaux pour les pas nominaux `6`, `4` et `3 mm`. Les tailles et SHA-256 ont tous ete verifies.

Le solveur stationnaire a atteint ses criteres de residus sur les trois grilles, mais la preuve reste diagnostique :

- `6 mm` : `12 622` tetraedres, perte de pression `330,65 Pa` ;
- `4 mm` : `40 186` tetraedres, perte de pression `446,70 Pa` ;
- `3 mm` : `91 086` tetraedres, perte de pression `502,87 Pa` ;
- variation fine de perte de pression : `11,17 %`, au-dessus du seuil de `10 %` ;
- variation fine de vitesse de sortie : `0,0146 %` ;
- controle etendu de maillage non conforme sur les trois cas, avec respectivement `83`, `124` et `163` cellules a faible determinant.

Le resultat ne ferme donc pas le gate CFD : il manque une grille plus fine ou une strategie de maillage amelioree, les pulsations moteur, les conditions mesurees, la rugosite, la temperature et la correlation au banc.

`openfoam-evidence-audit.json` est le rapport public. Les donnees brutes ne sont pas commitees.
