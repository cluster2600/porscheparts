# Criblage LPBF F0 — embout ovale IN625

Ce dossier publie le tranchage geometrique complet du STEP et la scene de revue Omniverse associee. Il ne contient ni trajectoires laser, ni supports fournisseur, ni simulation thermomecanique locale du bain de fusion.

Le calcul natif `linux/amd64` retient provisoirement `roll_y_25` sur l'enveloppe nominale EOS M 290 `250 x 250 x 325 mm` :

- `3 702` couches a `40 micrometres` ;
- hauteur issue du maillage tranche : `148,0587 mm` ;
- aucune couche interne vide et un nouvel ilot ;
- `784` couches avec aire non supportee, maximum `0,8426 mm2` ;
- proxy de support `7,194 cm3` ;
- epaisseur mesuree sur le maillage : minimum `0,245 mm`, percentile 1 `0,636 mm`, mediane `0,789 mm` ;
- toutes les sondes restent sous la cible conceptuelle de `1,5 mm` ;
- aucun volume de poudre piege detecte au voxel de `0,5 mm`.

Ces resultats confirment seulement qu'une orientation calculable entre dans la machine. La minceur, les ilots, les supports et la distorsion ferment le gate d'impression. La carte publique EOS M 290 / IN625 / 40 micrometres ne contient pas les donnees proprietaires necessaires au solveur : trajectoires laser, supports, lois dependantes de la temperature, deformation propre, modele recoater et calibration fournisseur.

La scene Omniverse composee a passe les validateurs Minimum, Asset, Geometry et Physics. Sa copie aplatie sert seulement au rendu, car le service OVRTX transporte un fichier unique. Le recoater anime est un guide visuel place au-dessus de la borne conservative de la boite transformee ; aucune collision ni forme deformee n'est simulee.

Artefacts :

- rapport de tranchage : `993-exh-oval-tip-in625-f0-0001-lpbf-geometry-report.json` ;
- manifeste de reproductibilite : `993-exh-oval-tip-in625-f0-0001-lpbf-geometry-manifest.json` ;
- couches : `993-exh-oval-tip-in625-f0-0001-layer-metrics.csv` ;
- synthese Omniverse : `omniverse-build-screen-summary.json` ;
- rendus : `993-exh-oval-tip-in625-f0-0001-lpbf-geometry-screen.png` et `oval-tip-lpbf-build-screen.png`.

Les sorties brutes restent hors Git sous `work/`.
