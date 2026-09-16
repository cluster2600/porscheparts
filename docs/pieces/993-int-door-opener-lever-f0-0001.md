<!-- engendre par scripts/render_part_pages.py - ne pas editer a la main -->

# Levier intérieur d'ouverture de porte 993, concept F0 aluminium

**Statut : fonctionnel. Aucune pièce n'est libérée ; voir [SAFETY.md](../../SAFETY.md).**

Concept indépendant de levier et chape intégrés pour étudier une refabrication LPBF à faible volume. PorscheFanatics établit les références PET gauche et droite ; FVD publie l'enveloppe et la masse d'une paire aftermarket, mais aucune géométrie d'interface ne permet un montage.

Fiche du catalogue : [`catalog/parts/993-int-door-opener-lever-f0-0001.json`](../../catalog/parts/993-int-door-opener-lever-f0-0001.json)

## Identité

| champ | valeur |
|---|---|
| identifiant | 993-INT-DOOR-OPENER-LEVER-F0-0001 |
| génération | 993 |
| variantes | 993_door_trim_variants_to_confirm |
| années | 1994 à 1998 |
| références Porsche | 99355585100, 99355585200 |
| catégorie | interior_door_release |
| classe de sécurité | functional |
| usage prévu | Criblage CAO, DfAM et mécanique d'un levier ouvrant ; aucun montage ou usage d'évacuation autorisé |

## Matière et fabrication

| champ | valeur |
|---|---|
| procédé préféré | LPBF |
| procédés candidats | LPBF, CNC |
| famille de matière | aluminium LPBF candidat |
| nuance | AlSi10Mg de criblage ; matériau OEM et grade du produit commercial inconnus |
| norme | ASTM F3318-18 à contractualiser si le concept progresse |
| exigences fournisseur | poudre, machine, paramètres, orientation et lot traçables, coupon témoin dans l'orientation critique du levier, contrôle dimensionnel de l'enveloppe, du pivot, des portées et des butées, CT ou radiographie de la chape et ressuage après usinage, rugosité et arrondis contrôlés dans les zones de préhension, essais statiques et cycliques instrumentés avant tout montage |
| post-traitement | retrait des supports avec accès conservé aux poches, traitement thermique qualifié pour la machine et l'orientation, alésage et finition du pivot après définition du jeu, usinage des portées de fixation avec surépaisseur future, anodisation ou thermolaquage après contrôle dimensionnel |

## Géométrie

| champ | valeur |
|---|---|
| type de source | mixed |
| format du maître | build123d |
| unités | mm |
| précision (mm) | non renseigné |

**Fichier maître**

- [`parts/993-int-door-opener-lever-f0-0001/source/door_opener_lever.py`](../../parts/993-int-door-opener-lever-f0-0001/source/door_opener_lever.py)

**Fichiers dérivés**

- [`parts/993-int-door-opener-lever-f0-0001/derived/door_opener_lever_f0.step`](../../parts/993-int-door-opener-lever-f0-0001/derived/door_opener_lever_f0.step)
- [`parts/993-int-door-opener-lever-f0-0001/derived/door_opener_lever_f0.stl`](../../parts/993-int-door-opener-lever-f0-0001/derived/door_opener_lever_f0.stl)

## Provenance et sources

| champ | valeur |
|---|---|
| licence de la fiche | MIT pour le concept, le script et les calculs ; aucune photographie ou géométrie commerciale redistribuée |

**Sources**

- [PorscheFanatics - références PET des ouvre-portes intérieurs 993](https://porschefanatics.com/oem/)
- [FVD - jeu d'ouvre-portes aluminium FVD55599301B](https://www.fvd.net/de/shop/tueroeffnersatz-2-stk-aluminium-schwarz-993-fvd55599301b~p310555)
- [EOS Aluminium AlSi10Mg material data sheet](https://www.eos.info/metal-solutions/metal-materials/data-sheets/mds-eos-aluminium-alsi10mg)

## Validation

| champ | valeur |
|---|---|
| statut | concept |
| essais véhicule | non renseigné |
| revu par |  |
| limites | non renseigné |

**Preuves**

- [`catalog/sources/src-porschefanatics-993-door-opener-pet.json`](../../catalog/sources/src-porschefanatics-993-door-opener-pet.json)
- [`catalog/sources/src-fvd-993-door-handle-dimensions.json`](../../catalog/sources/src-fvd-993-door-handle-dimensions.json)
- [`parts/993-int-door-opener-lever-f0-0001/evidence/engineering-screen.json`](../../parts/993-int-door-opener-lever-f0-0001/evidence/engineering-screen.json)
- [`twins/993-door-opener-lever-alsi10mg-f0/evidence/summary.json`](../../twins/993-door-opener-lever-alsi10mg-f0/evidence/summary.json)
- [`twins/993-door-opener-lever-alsi10mg-f0/evidence/lpbf-f0/993-int-door-opener-lever-f0-0001-lpbf-geometry-report.json`](../../twins/993-door-opener-lever-alsi10mg-f0/evidence/lpbf-f0/993-int-door-opener-lever-f0-0001-lpbf-geometry-report.json)
- [`twins/993-door-opener-lever-alsi10mg-f0/evidence/calculix-f0/calculix-thermomechanical-screen.json`](../../twins/993-door-opener-lever-alsi10mg-f0/evidence/calculix-f0/calculix-thermomechanical-screen.json)
- [`twins/993-door-opener-lever-alsi10mg-f0/evidence/simready-f0/binary-validation.json`](../../twins/993-door-opener-lever-alsi10mg-f0/evidence/simready-f0/binary-validation.json)
- [`twins/993-door-opener-lever-alsi10mg-f0/evidence/simready-f0/rigid-scene-validation.json`](../../twins/993-door-opener-lever-alsi10mg-f0/evidence/simready-f0/rigid-scene-validation.json)
- [`twins/993-door-opener-lever-alsi10mg-f0/evidence/simready-f0/ovphysx-rigid-screen.json`](../../twins/993-door-opener-lever-alsi10mg-f0/evidence/simready-f0/ovphysx-rigid-screen.json)

---

*Page engendrée depuis la fiche du catalogue par `scripts/render_part_pages.py`, vérifiée par `make check`. Toute correction se fait dans la fiche, pas ici.*
