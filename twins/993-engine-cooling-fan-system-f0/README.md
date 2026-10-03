# Programme ventilateur Porsche 993

[Accueil du dépôt](../../README.md) · [Registre du programme](program/program.json) · [Commandes](program/REPRODUCE.md) · [Validation et données manquantes](program/VALIDATION_PLAN.md)

[Recherche documentaire multilingue 911 / 935 / 993 : sources, paramètres et contradictions](program/research/README.md)

**État au 3 octobre 2026 : études exploratoires, aucune pièce validée.** Le scan
fourni comme « 935 » est retrouvé et audité en privé ; son identité, ses unités,
sa calibration et les droits sur ses dérivés restent inconnus ; l'acquisition
Wolfe Classics est rapportée par les justificatifs privés. L'équivalence avec
un ventilateur 993 reste une hypothèse. Aucun brut ni dérivé de ce scan n'est publié.

## Parcours des travaux

| Étape | Livrables et preuves | État réel |
|---|---|---|
| Identification / scan | [Audit et frontière privée](program/SCAN_INTAKE.md), [sources et nomenclature](REFERENCE_REBUILD.md), [registre](reference-research.json) | Scan ouvert ; deux composantes ; échelle et pièce non établies |
| Modèle de référence | [Source éditable PicoGK](source/picogk-reference/Program.cs), [paramètres](source/picogk-reference/reference.json), [contrôles](results/reference/validation.json), [vues calculées](results/reference/reference-review.png) | Reconstruction hypothétique Turbo, distincte du scan |
| Variantes | [Étude A–E](ORGANIC_BLADE_STUDY.md), [plans de balayage](results/airflow-sweep-20260929/configs/plan.json), [candidat Qwen / PR105](https://github.com/cluster2600/porscheparts/pull/105) | Variantes traçables ; aucune forme optimale établie |
| Rotation / structure / modes | [Calculs centrifuges](results/organic/structure/), [nouveau calcul modal](program/EXECUTION_20261003.md) | Calculs exécutés ; appuis/matière hypothétiques, fatigue et convergence non qualifiées |
| Aérodynamique | [PR103 / diagnostic](MESH_RECOVERY_20261001.md), [reprise PR105](https://github.com/cluster2600/porscheparts/pull/105), [audit des sorties finales](program/EXECUTION_20261003.md) | Deux maillages acceptés ; calculs terminés à 2 000 itérations, convergence rejetée |
| Fabrication additive | [Écran géométrique](PRINT_RELEASE.md), [scénario machine/matière](zrapid-print-process.json), [code thermique](source/simulate_zrapid_print.py) | LPBF AlSi10Mg exploratoire ; pas de prédiction qualifiée de distorsion/résidus |
| Omniverse / OpenUSD | [Asset organisé](program/fan-program.usda), [contrôles et portée](program/EXECUTION_20261003.md), [archive des démonstrateurs](OMNIVERSE_DIGITAL_TWIN.md) | Composition et unités contrôlées ; géométrie et jumeau physique non validés |

![Vues issues du modèle paramétrique de référence, sans qualification dimensionnelle](results/reference/reference-review.png)

## Trois identités à ne pas confondre

Le [catalogue Carrera F0](../../catalog/parts/993-eng-cooling-impeller-alsi10mg-f0-0001.json)
reste la source de vérité pour cet ancien concept : référence 96410601531,
géométrie synthétique de 280 mm, douze pales et statut
`prohibited_pending_engineering`. Son ancien [carter](../../catalog/parts/993-eng-fan-housing-alsi10mg-f0-0001.json)
ne devient pas le carter Turbo.

La reconstruction du 28 septembre cible **993 Turbo M64.60 / 96410601522**, avec
un diamètre de travail hypothétique de 245 mm et onze pales. Les interfaces du
moyeu, du carter 99310666750, du cône, des entretoises, des poulies et de
l'alternateur restent à mesurer. Aucun alternateur n'est sélectionné par
l'utilisateur : 175 A / 240 A restent des alternatives de recherche avec des
contraintes d'entraînement distinctes. Les dimensions
d'un alternateur AS-PL ne sont pas celles du PMB. Il n'existe pas de fiche
catalogue fonctionnelle validée pour cette reconstruction.

Le **scan « 935 »** forme une troisième branche d'investigation. Il ne remplace
aucune des deux précédentes par simple similarité visuelle. Porsche distingue
les turbines Turbo et Carrera dans [ORIGINALE 05, page PDF 7](https://assets-v2.porsche.com/int/-/media/Project/PCOM/SharedSite/PorscheClassic/ORIGINALE/Editions---EN/originale-05-ww.pdf).
Cette source ne tranche pas l'identité de la pièce scannée.

## Reprise utile

Les [critères de validation](program/VALIDATION_PLAN.md) ordonnent les travaux
restants. L'audit et la préparation des modèles restent possibles ; une
géométrie fonctionnelle issue du scan demande d'abord son identité, une référence
dimensionnelle indépendante, les raccords mesurés et la portée de réutilisation.
Les anciens champs CFD/thermiques ne sont pas transférés au scan ou à la nouvelle
référence. Aucune fabrication, commande, rotation physique ni installation
n'est autorisée par ce programme.
