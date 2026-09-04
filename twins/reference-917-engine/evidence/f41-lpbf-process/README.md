# F41 — écran LPBF multi-échelle

Ce dossier publie le premier écran d'impression métallique réellement exécuté
sur la culasse F41. Il lie un maître STEP monobloc, un audit géométrique de la
pièce complète, un historique thermique macroscopique, une distorsion
CalculiX et un calcul local de bain de fusion ORNL AdditiveFOAM.

La machine de référence est une ZRapid iSLM420DN chinoise. La recette de départ
AlSi10Mg provient d'une publication utilisant cette même machine : `500 W`,
`1 300 mm/s`, hatch `0,10 mm`, couche `40 µm`, spot publié `80 µm` et plateau
à `30 °C`. Les cas `400`, `450` et `500 W` ont été exécutés sur OpenFOAM 14 et
AdditiveFOAM 2.0.0 avec deux couches et 16 rangs MPI par cas.

## Résultat

- le STEP se réimporte comme un solide OCCT unique ;
- la peau triangulée est étanche et monocomposante ;
- aucune cavité fermée n'est détectée aux pas voxel `2,0` et `1,25 mm` ;
- l'orientation `scan_y_down` tient dans le volume conditionnel de la machine ;
- le planning complet représente `5 153` couches de `40 µm` ;
- les trois calculs AdditiveFOAM se terminent sans erreur et fondent
  l'AlSi10Mg ;
- la taille maximale du bain à `500 W` vaut `0,8377 × 0,2443 × 0,2845 mm`
  selon l'objet fonctionnel AdditiveFOAM à `870 K` ;
- les trois cas atteignent néanmoins la borne numérique de `3 300 K` ;
- l'écran d'épaisseur, la convergence de contrainte et la qualification du
  procédé échouent.

Le verdict est donc **correction géométrique et calibration procédé requises**.
Il ne s'agit ni d'un fichier machine, ni d'une carte fournisseur qualifiée, ni
d'une autorisation d'impression ou de démarrage moteur.

## Fichiers

- le maître B-Rep conditionnel est conservé dans `work/917-f41-lpbf/` et
  verrouillé par SHA-256 ; il n'est pas publié tant que les droits du scan
  source ne permettent pas la redistribution ;
- `917-head-lpbf-candidate-f41.png` : extérieur, face combustion et coupe ;
- `917-head-lpbf-candidate-f41-report.json` : construction géométrique ;
- `917-head-lpbf-candidate-f41-audit.json` : épaisseur, vides, orientation et
  activation de couches ;
- `917-head-lpbf-macro-f41-report.json` et `.png` : thermique pièce complète ;
- `917-head-lpbf-calculix-f41-report.json` et `.png` : distorsion et contrainte ;
- `917-head-lpbf-additivefoam-f41-report.json`, `.png` et `.mp4` : bain de
  fusion local, sensibilité de puissance et animation.

Le générateur paramétrique et tous les rapports sont versionnés ; le scan brut,
le STEP et le STL dérivés restent locaux. La méthode, les limites et les références sont détaillées dans
`docs/917_F41_LPBF_PROCESS.md`.
