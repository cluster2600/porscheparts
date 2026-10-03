# Informations nécessaires sur les deux OBJ et leur assemblage

Cette liste structure la demande préparée dans Gmail. L'adresse, le contenu du
mail, le brouillon et toute future réponse restent privés. La préparation d'un
brouillon ne constitue pas un envoi ou une commande fournisseur.

| Priorité | Information demandée | Contrat à compléter |
|---|---|---|
| 1 | Identité et variante du donneur, références des pièces, appairage réel des deux scans | `exact_donor_variant`, identité des composants |
| 1 | Unité OBJ, sens des suffixes 0,5/0,21 mm, deux cotes physiques indépendantes par scan, outil et incertitude | `scans[].scale_to_mm`, preuves de calibration |
| 1 | Photos montées, repères communs, transformations d'acquisition ; dos du rotor mal aligné et couverture manquante | Repères, registration, carte de couverture |
| 2 | Alésage/moyeu, face d'appui, clavette/cannelure ou fixation et retenue axiale | `rotor-hub`, `hub-output` |
| 2 | Axes d'entrée/sortie, faces et trous support/moteur, entraxes, filetages et empilages | `case-mounts`, `mounts-engine`, appuis |
| 2 | Pièces incluses/retirées, données originales non décimées, captures séparées et réparations appliquées | Segmentation et provenance des acquisitions |
| 3 | Type de transmission, dentures/rapport, sens de rotation, portées, roulements, jeux/précharges, emplacement accouplement | `input-gearset`, `gearset-output`, appuis et accouplement |
| 3 | Alimentation/retour huile, filetages, restrictions et joints | `lube-drive` et domaine lubrification |
| 3 | Carter, guides et poulies assortis au même donneur ; ambiguïté du guide annoncé 935/décrit 934 | `rotor-inlet`, `inlet-guides`, `guides-engine`, courroie |
| 4 | Masses/matières documentées, rapports des trois arbres, cartes débit/pression/couple, températures et conditions d'essai | Modèles mécaniques, aérauliques et thermiques |
| 4 | Catalogue/instructions disponibles et droit de partage ; licence des scans, CAD dérivé, simulation, impression et publication | Provenance et usages autorisés |

Pour une cote : identifier les deux éléments entre lesquels elle est prise,
unité, outil, incertitude et état d'assemblage. Une photo annotée du même
spécimen avec relevé au pied à coulisse est une première preuve documentaire ;
elle ne remplace pas un dossier métrologique sur les interfaces critiques.

Le traitement des réponses garde « inconnu » lorsqu'une donnée n'est pas
disponible. Un diamètre d'un autre rotor, une masse de reproduction commerciale
ou une pose ajustée dans le modèle ne valident pas les fichiers fournis.
