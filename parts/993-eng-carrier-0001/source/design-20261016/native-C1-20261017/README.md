# Maître BREP C1 et deux calculs complets du support 993

Cette capsule conserve la révision native C1, sa surface retriangulée, son maillage volumique et les sorties réelles des deux calculs linéaires. Le maître éditable est le BREP a42e ; les fichiers STEP refusés restent des pièces historiques.

| Cas | Déplacement maximal | Contrainte IP maximale | Erreur relative d’énergie |
| --- | --- | --- | --- |
| Fixations bloquées | 2,794104 mm | 907,278068 MPa | 3,59345e-9 |
| Ressorts K1000 par œil et axe | 18,171491 mm | 2663,075178 MPa | 3,15118e-9 |

Les deux maxima se trouvent dans l’élément 84037, IP1, aux coordonnées [82,136315 ; -14,388848 ; 12,860258] mm. Le modèle conserve Fz=-4000 N, My=850000 N·mm, E=107000 MPa et nu=0,31. Chaque œil reçoit au total 1000 N/mm par axe dans le cas souple. La masse CAO est 1,262369675 kg sous le plafond de 1,30 kg.

Les archives conservent les rapports entiers, DAT/FRD/NPZ, decks, fichiers CAO/maillages et leurs empreintes ; aucun runtime installé n’est copié. Elles mesurent chacune moins de 100 Mo. Les résultats de l’ancienne géométrie restent des comparaisons descriptives ; ils ne fournissent pas une convergence à C1. Le test local h/2 de C1 est distinct de cette capsule.

## Vérifier et restaurer

Utiliser l’empreinte du manifeste indiquée dans le reçu de publication adjacent :

```sh
python3 -I -B restore.py verify --manifest-sha256 EMPREINTE
python3 -I -B restore.py restore DOSSIER_NEUF --manifest-sha256 EMPREINTE
```

`replay_analysis.py` restaure les originaux et recalcule uniquement les deux audits d’énergie et les deux rapports complets de pics, sans relancer CalculiX, Gmsh ou la CAO. Il exige le runtime NumPy épinglé dans runtime-provenance.json, cwd=/, nice10 et les trois variables BLAS à1. Les coordonnées sont celles de la référence non déformée ; aucun pic n’est exclu. Le reçu réel de ce rejeu est ajouté séparément après exécution.

Les sources d’analyse et le vérificateur BREP sont conservés byte pour byte. Les adaptations du restaurateur et du lanceur sont décrites avec inverse exact dans source-derivation.json. Le format de base des utilitaires vient de la capsule H2 historique ; leurs intitulés de docstring sont conservés, et le présent manifeste lie exclusivement C1 et ses résultats ci-dessus.
