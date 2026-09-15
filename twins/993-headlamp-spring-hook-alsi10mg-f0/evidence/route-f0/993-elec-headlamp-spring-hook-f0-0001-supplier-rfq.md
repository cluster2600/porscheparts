# Demande de devis — 993-ELEC-HEADLAMP-SPRING-HOOK-F0-0001

**Crochet de réparation du ressort de lampe, concept F0 aluminium**

Ce document est une **demande de devis et de faisabilite**, pas un ordre de
fabrication. La piece est classee `functional` et n'est autorisee ni au montage, ni a la vente.
Le fournisseur est invite a contredire ce qui suit.

## 1. Ce qui est fourni

| fichier | role | SHA-256 |
|---|---|---|
| `headlamp_spring_hook_f0.step` | maitre STEP | `33af8accffdc2be801193daa1a6ee6ceb0dd41f8c5ad5ecf8263f710cab6dc9c` |
| `headlamp_spring_hook_f0.stl` | surface d'analyse STL | `b24962e14fc5ab4fb810d352c17c207fff763cb25f0d14a83fc8b0f72695cb1d` |
| `993-elec-headlamp-spring-hook-f0-0001-lpbf-geometry-report.json` | criblage geometrique etape 03 | `2430a8fe3129954f94c5b86cb33edbf3d6470c07b745e6841315b15c571f5ec4` |

Le STEP est le maitre. Le STL est une surface d'analyse derivee, a tolerance
de corde declaree ; il ne fait pas foi sur la cote.

## 2. Route candidate

| poste | valeur |
|---|---|
| alliage | EOS Aluminium AlSi10Mg |
| designations | DIN EN 1706 EN AC-43000, ASTM F3318-18 |
| machine | EOS M 290 |
| jeu de parametres | AlSi10Mg_FlexM291 2.01 |
| gaz | Argon |
| plateau | 35 °C |
| orientation de criblage | `roll_y_45` |
| hauteur de construction | 12.7 mm |
| couches a 30 µm | 425 |
| masse de criblage | 2.35 g |
| temps d'exposition au debit publie | 0.05 h |

## 3. Ce que le dossier ne contient pas — questions au fournisseur

- **orientation_engineering_reviewed** — L'orientation vient d'une regle de criblage automatique, pas d'une revue DfAM.
- **temperature_dependent_constitutive_card_available** — La carte procede se declare elle-meme incomplete : exact laser path, hatch, contour and exposure schedule exported for this build ; powder optical properties and temperature-dependent liquid/solid thermal card ; temperature- and orientation-dependent elastic-plastic constitutive card.
- **heat_treatment_route_defined** — La carte procede ne publie aucun traitement thermique : detente, revenu et etat metallurgique de livraison restent a contractualiser.
- **machining_stock_defined** — Aucune surepaisseur d'usinage n'est definie, donc aucune surface fonctionnelle n'est garantie a la tolerance.
- **part_allowables_derived_from_coupons** — Les valeurs publiees sont des coupons EOS as-manufactured (Rp0,2 vertical 233 MPa, fatigue 110 MPa a 20 millions de cycles) : ce ne sont pas des admissibles de cette piece, dans cette orientation, a cet etat de surface.
- **powder_lot_traceability_contracted** — Ni lot, ni nombre de reemplois, ni certificat matiere ne sont engages avec un fournisseur.

## 4. Livrables attendus avec le devis

- procede et machine reellement employes, avec le jeu de parametres qualifie ;
- epaisseur de couche proposee, et proprietes coupon **de cette epaisseur** ;
- orientation et topologie de supports proposees, avec justification ;
- traitement thermique, etat de livraison et HIP si juge necessaire ;
- surepaisseurs d'usinage sur les surfaces fonctionnelles ;
- certificat matiere, lot de poudre et nombre de reemplois ;
- controle dimensionnel des quatre cotes et du profil axial ;
- comparaison chiffree avec le tournage CNC de la meme geometrie.

## 5. Reserve

Les cotes du modele proviennent d'une fiche commerciale, pas d'un plan
d'origine ni d'une mesure. Elles sont des variables de conception. Aucune
piece issue de ce dossier ne doit etre montee sur un vehicule avant mesure
d'un exemplaire et controle du logement.
