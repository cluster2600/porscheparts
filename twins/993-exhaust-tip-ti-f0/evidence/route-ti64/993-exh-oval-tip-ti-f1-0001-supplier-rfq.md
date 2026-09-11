# Demande de devis — 993-EXH-OVAL-TIP-TI-F1-0001

**Embout d'échappement ovale, variante titane F1**

Ce document est une **demande de devis et de faisabilite**, pas un ordre de
fabrication. La piece est classee `functional` et n'est autorisee ni au montage, ni a la vente.
Le fournisseur est invite a contredire ce qui suit.

## 1. Ce qui est fourni

| fichier | role | SHA-256 |
|---|---|---|
| `oval_exhaust_tip_ti_f1.step` | maitre STEP | `6dc3da8a65242471d0cd9d65b8b40f44660897b923d207e5b1cf1d1b2bc4f758` |
| `oval_exhaust_tip_ti_f1.stl` | surface d'analyse STL | `7a2a8e65aa7d0d7771cc49b8fa9aaf116ba6eb4d124b843a8584f9cf85bd265e` |
| `993-exh-oval-tip-ti-f1-0001-lpbf-geometry-report.json` | criblage geometrique etape 03 | `f7ee5b3a6363a13e4b55d13ab5d2e57095083104a80f45b387ea43ec6a5c3b9d` |

Le STEP est le maitre. Le STL est une surface d'analyse derivee, a tolerance
de corde declaree ; il ne fait pas foi sur la cote.

## 2. Route candidate

| poste | valeur |
|---|---|
| alliage | EOS Titanium Ti64 |
| designations | Ti-6Al-4V, ASTM F2924 a contractualiser si cette route est retenue |
| machine | EOS M 290 |
| jeu de parametres |  |
| gaz | Argon |
| plateau | non publie |
| orientation de criblage | `roll_y_25` |
| hauteur de construction | 148.1 mm |
| couches a 30 µm | 4936 |
| masse de criblage | 212.34 g |
| temps d'exposition au debit publie | 3.08 h |

## 3. Ce que le dossier ne contient pas — questions au fournisseur

- **orientation_engineering_reviewed** — L'orientation vient d'une regle de criblage automatique, pas d'une revue DfAM.
- **temperature_dependent_constitutive_card_available** — La carte procede se declare elle-meme incomplete : carte thermique et elasto-plastique dependante de la temperature pour cette route ; admissibles de fatigue a l'etat de surface reel de la piece ; limite d'oxydation et tenue au cyclage thermique de l'etat livre.
- **machining_stock_defined** — Aucune surepaisseur d'usinage n'est definie, donc aucune surface fonctionnelle n'est garantie a la tolerance.
- **part_allowables_derived_from_coupons** — Les valeurs publiees sont des coupons EOS as-manufactured (Rp0,2 vertical 965 MPa, aucune donnee de fatigue publiee) : ce ne sont pas des admissibles de cette piece, dans cette orientation, a cet etat de surface.
- **powder_lot_traceability_contracted** — Ni lot, ni nombre de reemplois, ni certificat matiere ne sont engages avec un fournisseur.
- **alloy_ceiling_above_declared_service_temperature** — La temperature declaree de 427 °C depasse le plafond de l'alliage de 27 °C. Cette temperature est une entree synthetique jamais mesuree : c'est elle qu'il faut aller chercher avant de changer d'alliage.

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
