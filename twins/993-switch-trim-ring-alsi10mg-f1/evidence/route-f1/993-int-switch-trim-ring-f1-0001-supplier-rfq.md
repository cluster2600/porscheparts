# Demande de devis — 993-INT-SWITCH-TRIM-RING-F1-0001

**Bague aluminium de finition de commutateur, reconstruction F1**

Ce document est une **demande de devis et de faisabilite**, pas un ordre de
fabrication. La piece est classee `non_critical` et n'est autorisee ni au montage, ni a la vente.
Le fournisseur est invite a contredire ce qui suit.

## 1. Ce qui est fourni

| fichier | role | SHA-256 |
|---|---|---|
| `switch_trim_ring_f1.step` | maitre STEP | `3b59150dc69d962d9ea5606fd23d3afc552c953c919150c307904b351bba00df` |
| `switch_trim_ring_f1.stl` | surface d'analyse STL | `c610c7ca70c7df19f1778a848f521abca0356d88f699668fd89b3141934c4ddc` |
| `993-int-switch-trim-ring-f1-0001-lpbf-geometry-report.json` | criblage geometrique etape 03 | `0d0cdca17a71dc19d01b499286b7c9232ac0fbc37e03da134908d2bf9523ba26` |

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
| hauteur de construction | 29.0 mm |
| couches a 30 µm | 967 |
| masse de criblage | 6.12 g |
| temps d'exposition au debit publie | 0.13 h |

## 3. Ce que le dossier ne contient pas — questions au fournisseur

- **layer_thickness_consistent** — Le tranchage a ete conduit a 50 um alors que la seule route publiee de cet alliage sur cette machine est a 30 um. Le nombre de couches, la duree et les proprietes coupon ne se transposent pas d'une epaisseur a l'autre.
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
