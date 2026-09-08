# Monocoque carbone autoporteuse 964/993 — feuille blanche

Ce dossier transforme l'idée d'une monocoque carbone compatible 964/993 en un programme d'ingénierie traçable. ZESAD et RUF sont des **précédents publics**, pas des donneurs de géométrie. Le master CAO est original et paramétrique. La cellule centrale est commune ; des modules CFRP avant/arrière distincts portent les variantes 964 et 993.

« Tout carbone » désigne ici la structure primaire. Des inserts filetés, bagues, axes et fixations métalliques locaux resteront nécessaires, avec dimensionnement au matage et isolation galvanique.

## Livrables présents

- `design-space.json` : hypothèses, enveloppes, masse cible de 1 200 kg, charges et huit architectures ;
- `platform-interface-contract.json` : séparation stricte des interfaces 964 et 993 et liste des coordonnées encore manquantes ;
- `vehicle-packaging-contract.json` : matrice 964/993 × C2/C4, commande de boîte, transmission avant et services à mesurer ;
- `source/check_vehicle_packaging.py` et `derived/packaging-clearance-check.json` : six contrôles reproductibles de cohérence des enveloppes, sans crédit de validation véhicule ;
- `source/build_structural_screening.py` : solveur treillis 3D et génération du cas CalculiX ;
- `derived/structural-screening.md` : classement des formes ;
- `source/verify_calculix.py` : comparaison indépendante du résultat CalculiX ;
- `source/simulate_final_product.py` et `derived/final-product-f1-screening.{json,md}` : cas globaux 3 g vertical, 1,5 g freinage et 1,8 g latéral sur le treillis F1 ;
- `manufacturing-simulation.json`, `source/simulate_manufacturing.py` et `derived/manufacturing-process-screening.{json,md}` : sensibilité thermique/cuisson et dilatation d'outillage, avec cinétique résine explicitement hypothétique ;
- `source/build_cad.py` : génération OCCT de la cellule et du moule ;
- `derived/993-carbon-safety-cell-concept.step` : cellule automobile conceptuelle en 49 solides fonctionnels, avec tunnel creux, ouvrants, planchers, cloisons et passages de roues ;
- `derived/964-carbon-interface-modules-concept.step` : pods d'enveloppe CFRP 964, sans points de suspension inventés ;
- `derived/993-carbon-interface-modules-concept.step` : pods d'enveloppe CFRP 993, sans points de suspension inventés ;
- `derived/964-c2-packaging-envelope.step` et `derived/993-c2-packaging-envelope.step` : commande de boîte et tour de levier C2 ;
- `derived/964-c4-packaging-envelope.step` et `derived/993-c4-packaging-envelope.step` : tube/arbre longitudinal, guidage de commande, pont et demi-arbres avant C4 ;
- `derived/993-carbon-safety-cell-tooling-concept.step` : partition d'outillage conceptuelle en 10 éléments, mandrin de tunnel compris ;
- `source/build_usd.py` : scène OpenUSD avec structure, chargements, appuis, matériaux et forme déformée ;
- `derived/993-carbon-safety-cell-digital-twin.usda` : point d'entrée du jumeau ;
- `derived/964-993-carbon-monocoque-packaging-overview.png` : vue technique de la cellule et des packages C2/C4, générée par code ;
- `derived/964-993-carbon-monocoque-clean-sheet-product-concept-v2.png` : rendu produit génératif original, utile uniquement pour la direction de forme et sans autorité géométrique ;
- `research/product-concept-v2-prompt.md` : prompt et limites de provenance du rendu produit ;
- `mold-plan.json` : exigences restant à fermer avant lancement du moule ;
- `tuv-dimensions-de.json` et `tuv-precheck-de.md` : cotes allemandes
  confirmées, lacunes d'interfaces et route de pré-consultation §19(2)/§21 ;
- `engineering-validation-contract.json` et `validation-plan.md` : échelle de preuve jusqu'à la libération indépendante.
- `simulation-program.json` : routage explicite de la pile publiée dans `docs/SOFTWARE_STACK.md`, des calculs F1 actuels jusqu'aux étapes F2, SimReady et PhysicsNeMo encore bloquées ;
- `simready/material-prompt.txt` et `simready/physics-prompt.txt` : consignes bornées pour l'exécution NVIDIA, sans propriétés mécaniques inventées.
- `evidence/vast-simready-execution-f1.json` : exécution Vast payante, contrat GPU/image/SSH, coût conservateur, récupération et destruction des instances, avec blocage NVIDIA conservé sans faux succès.

## Résultat de présélection

| Architecture | Masse active F1 (kg) | Rigidité torsionnelle F1 (Nm/deg) | Ratio / tub ouvert |
|---|---:|---:|---:|
| tub ouvert | 14,530 | 2 868,5 | 1,000 |
| bas de caisse + tunnel | 27,841 | 4 411,0 | 1,538 |
| cellule carbone fermée | 30,909 | 8 459,3 | 2,949 |
| benchmark hybride | 40,846 | 15 380,5 | 5,362 |
| benchmark multicellulaire hybride | 57,275 | 21 710,1 | 7,568 |
| tout carbone x8 | 69,648 | 19 935,8 | 6,950 |
| tout carbone x10 | 78,079 | 21 011,7 | 7,325 |
| tout carbone x12 | 86,509 | 21 833,4 | 7,611 |

`all_carbon_multicell_x10` est retenue : x8 manque la cible provisoire de 20 000 Nm/deg et x12 offre moins de rigidité spécifique. Les variantes hybrides restent des benchmarks numériques mais sont exclues par la politique « structure primaire CFRP ». Ces chiffres sont des résultats de classement d'un treillis, pas des performances promises du produit fini.

Les trois cas globaux ajoutés donnent, avec les anneaux avant et arrière encastrés et une répartition uniforme des résultantes sur les nœuds de cellule, 1,848 mm sous 3 g vertical, 0,174 mm sous 1,5 g de freinage et 0,686 mm sous 1,8 g latéral. Ce sont des réponses du même treillis isotrope équivalent : aucune contrainte de pli, marge, rupture, liaison ou compatibilité véhicule n'en découle.

La première présélection de cuisson compare deux cycles génériques sur témoins de 4, 8 et 12 mm. Avec la cinétique époxy hypothétique, tous dépassent le seuil provisoire de surtempérature et les sections épaisses montrent un retard thermique important. Ce résultat ne condamne aucun procédé : il montre précisément que les données DSC/DEA fournisseur et un panneau témoin instrumenté sont nécessaires avant de sélectionner cycle, résine ou outillage. La sensibilité de dilatation libre écarte provisoirement l'aluminium non compensé sur 2 272 mm, mais ne libère ni Invar ni outillage CFRP.

## Exécution Vast / Omniverse

Une RTX PRO 6000 WS de 97 887 Mo a été louée via les wrappers OpenBao avec l'image publique `linux/amd64` épinglée. Le runtime GPU, PhysicsNeMo, le démarrage des Content Agents, la paire SSH et le transfert du commit propre ont été contrôlés. Le meilleur run s'est toutefois arrêté au préflight, avant ouverture de l'USD : `PyYAML` manquait dans l'interpréteur `/opt/simready-validation/bin/python` choisi par le runner. Aucun appel Material Agent, Physics Agent, Asset Validator, SimReady Validate ou rendu OVRTX n'a donc été exécuté.

Toutes les instances créées ont été détruites ; l'inventaire final était vide. L'enveloppe de coût conservatrice est de 0,5223 USD, en comptant même la fenêtre d'une création refusée comme si elle avait été facturée. Le rapport ne constitue pas une facture fournisseur. Après cette création refusée, le wrapper a demandé de ne plus relancer automatiquement : la prochaine étape est de préqualifier le couple interpréteur/PyYAML hors d'un nouveau run payant.

## Masse cible et enveloppe de charge

La cible véhicule est **1 200 kg prêt à rouler, sans occupant**, à confirmer avec la configuration et l'expert TÜV. Le budget provisoire réserve 110 kg au système monocoque installé : 90 kg pour la cellule commune et 20 kg pour le jeu de modules de plateforme. À 1 200 kg, les résultantes de départ sont 11 767,98 N à 1 g, 35 303,94 N à 3 g vertical, 17 651,97 N à 1,5 g au freinage et 21 182,36 N à 1,8 g latéral. Elles ne peuvent pas encore être réparties sans masses par essieu, centre de gravité, pneus et aérodynamique.

## Architecture C2 / C4 corrigée

Le caisson extérieur du tunnel est commun et réserve l'enveloppe de la C4, plus encombrante. Le package C2 reçoit une commande de boîte et un tour de levier ; le package C4 ajoute un tube central, l'enveloppe de l'arbre longitudinal, un guidage de commande distinct, le pont avant et les demi-arbres. Les conduites de frein/carburant, les câbles de frein à main et le faisceau sont placés dans des conduits protégés hors du volume tournant.

Les catalogues PET officiels Porsche établissent cette topologie et les variantes de pièces, mais leurs éclatés ne sont pas cotés. Les dimensions de `vehicle_packaging_mm` sont donc des hypothèses de travail jusqu'au scan/CMM de quatre donneuses : 964 C2, 964 C4, 993 C2 et 993 C4.

## Reproduction locale

```bash
python3 twins/993-carbon-safety-cell/source/build_structural_screening.py --write
python3 twins/993-carbon-safety-cell/source/build_structural_screening.py --check
python3 twins/993-carbon-safety-cell/source/verify_calculix.py
python3 twins/993-carbon-safety-cell/source/simulate_final_product.py --write
python3 twins/993-carbon-safety-cell/source/simulate_final_product.py --check
python3 twins/993-carbon-safety-cell/source/simulate_manufacturing.py --write
python3 twins/993-carbon-safety-cell/source/simulate_manufacturing.py --check
python3 twins/993-carbon-safety-cell/source/check_vehicle_packaging.py --write
python3 twins/993-carbon-safety-cell/source/check_vehicle_packaging.py --check
python3 twins/993-carbon-safety-cell/source/build_usd.py --write
python3 twins/993-carbon-safety-cell/source/build_usd.py --check
python3 twins/993-carbon-safety-cell/source/render_concept.py
```

`build_cad.py` exige build123d et OCCT. Il a été exécuté dans l'image locale CAD F28 du dépôt. Le `.inp` CalculiX a été résolu avec CalculiX 2.21.

## Interdictions actuelles

Ne pas fabriquer le moule, ne pas fabriquer ou monter la cellule, ne pas démarrer ou rouler le véhicule et ne pas présenter ce dossier comme une homologation. Les interfaces structurelles 964/993, stratifiés, joints, crashs, essais physiques et signatures professionnelles ne sont pas encore disponibles.
