# F36 — recoupement CFD et thermique final

Ce dossier publie une synthèse reproductible de la campagne numérique F36 :

- `cross-solver-report.json` contient les résultats chiffrés, les empreintes des
  preuves OpenFOAM et la matrice de décision ;
- `openfoam-runs/` publie les entrées compactes réellement lues pour chacun des
  huit cas, y compris les sept cas de carénage rejetés ;
- `openfoam-run-manifest.json` relie chaque ligne numérique sélectionnée à son
  fichier, sa taille et son SHA-256 ;
- `bundle-manifest.json` couvre le rapport, la planche, le manifeste des cas et
  tout l'arbre `openfoam-runs/` ;
- `917-head-f36-final-cfd-thermal.png` est la planche lisible de synthèse.

Les champs volumineux restent sous
`work/917-scan-conforming-f36/final-cross-solver-013/`, tandis que les journaux,
configurations, contrôles de maillage et séries `.dat` consommés sont publiés
ici. La synthèse se régénère avec
`twins/reference-917-engine/source/build_f36_final_cfd_thermal_evidence.py`.

Le résultat est volontairement bloquant : FluidX3D n'atteint pas l'indépendance
de grille, le cas OpenFOAM commun prédit un échange très inférieur et le
contrôle strict de son maillage n'est pas vert. Sur le carénage 20 mm, deux
mailles RANS terminent mais échouent le bilan énergie et l'accord de grille ;
deux diagnostics laminaires sont également rejetés et deux domaines longs
s'arrêtent par instabilité. Aucun carénage n'est sélectionné, et ces fichiers
n'autorisent ni impression métal ni démarrage moteur. Il ne s'agit pas d'une
CHT ni d'une corrélation physique.
