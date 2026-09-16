<!-- engendre par scripts/render_part_pages.py - ne pas editer a la main -->

# Carter fixe de ventilateur moteur, concept AlSi10Mg F0

**Statut : **interdit en l'état**. Aucune pièce n'est libérée ; voir [SAFETY.md](../../SAFETY.md).**

Concept indépendant d'un carter annulaire 993 réunissant coque, bride frontale, support d'alternateur et six rayons. Les sources établissent la référence, une enveloppe commerciale, deux masses cohérentes et une déclaration revendeur aluminium, mais aucune géométrie d'interface ; le F0 ne reproduit pas la pièce Porsche.

Fiche du catalogue : [`catalog/parts/993-eng-fan-housing-alsi10mg-f0-0001.json`](../../catalog/parts/993-eng-fan-housing-alsi10mg-f0-0001.json)

## Identité

| champ | valeur |
|---|---|
| identifiant | 993-ENG-FAN-HOUSING-ALSI10MG-F0-0001 |
| génération | 993 |
| variantes | 993_air_cooled_fitment_to_confirm |
| années | 1994 à 1998 |
| références Porsche | 99310666703, 99310666701 |
| catégorie | engine_cooling_fan_housing |
| classe de sécurité | prohibited_pending_engineering |
| usage prévu | Criblage F0 de CAO ouverte, valeur DfAM, débit, perte de charge, flexion, modal, thermique et masse ; aucune fabrication, installation, rotation du ventilateur ou mise en route moteur autorisée |

## Matière et fabrication

| champ | valeur |
|---|---|
| procédé préféré | à décider |
| procédés candidats | LPBF, DMLS, casting, CNC |
| famille de matière | alliage aluminium-silicium-magnésium candidat LPBF |
| nuance | EOS Aluminium AlSi10Mg T6 de comparaison ; remplacement commercial déclaré seulement aluminium non spécifié |
| norme | DIN EN 1706 EN AC-43000 et ASTM F3318 pour le candidat ; spécification de refroidissement, fatigue et confinement propre au programme à contractualiser |
| exigences fournisseur | machine grand plateau, paramètres, orientation, supports, poudre et lot traçables, coupons orientés avec traction, fatigue, fluage et corrosion à chaud, témoins de distorsion annulaire et d'état de surface du conduit, CT intégral, FPI et métallographie avec critères de défauts zonés, métrologie alésage, concentricité, alternateur, fixations, joint et enveloppe, preuve d'écoulement, vibration, survitesse/confinement, cyclage thermique et endurance moteur |
| post-traitement | orientation et supports de l'anneau de 300 x 300 x 170 mm à qualifier, détensionnement puis T6 avec trempe et distorsion suivies, HIP à décider sur fatigue, étanchéité air et résultats de tomographie, usinage de l'alésage ventilateur, portée alternateur, fixation, joint et datums, ébavurage, dépoudrage ouvert et finition du conduit sans particules, traitement anticorrosion compatible températures, fixations et compartiment moteur, contrôle final des jeux avant toute rotation |

## Géométrie

| champ | valeur |
|---|---|
| type de source | mixed |
| format du maître | build123d |
| unités | mm |
| précision (mm) | non renseigné |

**Fichier maître**

- [`parts/993-eng-fan-housing-alsi10mg-f0-0001/source/fan_housing.py`](../../parts/993-eng-fan-housing-alsi10mg-f0-0001/source/fan_housing.py)

**Fichiers dérivés**

- [`parts/993-eng-fan-housing-alsi10mg-f0-0001/derived/fan_housing_alsi10mg_f0.step`](../../parts/993-eng-fan-housing-alsi10mg-f0-0001/derived/fan_housing_alsi10mg_f0.step)

## Provenance et sources

| champ | valeur |
|---|---|
| licence de la fiche | MIT pour le concept, le script et les calculs ; aucune photographie, illustration, surface Porsche/PorscheFanatics/FVD/Centre Porsche Roissy/CarParts/EOS ou géométrie commerciale redistribuée |

**Sources**

- [PorscheFanatics - carter et flux du ventilateur moteur 993](https://porschefanatics.com/engine/993/)
- [FVD Brombacher - carter 993 106 667 03](https://www.fvd.net/en-us/shop/fan-housing-993-99310666703~p248872)
- [Centre Porsche Roissy - boîtier de soufflerie 993 106 667 03](https://www.boutiqueporscheroissy.fr/produit/99310666703-boitier-de-la-soufflerie-porsche/)
- [CarParts - carter 993 déclaré aluminium](https://www.carparts.com/details/fan-shroud/genuine-porsche/gxl99310666703)
- [EOS Aluminium AlSi10Mg material data sheet](https://www.eos.info/metal-solutions/metal-materials/data-sheets/mds-eos-aluminium-alsi10mg)

## Validation

| champ | valeur |
|---|---|
| statut | concept |
| essais véhicule | non renseigné |
| revu par |  |
| limites | non renseigné |

**Preuves**

- [`catalog/sources/src-porschefanatics-993-fan-housing-candidate.json`](../../catalog/sources/src-porschefanatics-993-fan-housing-candidate.json)
- [`catalog/sources/src-fvd-993-fan-housing-dimensions.json`](../../catalog/sources/src-fvd-993-fan-housing-dimensions.json)
- [`catalog/sources/src-porsche-roissy-993-fan-housing-mass.json`](../../catalog/sources/src-porsche-roissy-993-fan-housing-mass.json)
- [`catalog/sources/src-carparts-993-fan-housing-aluminium.json`](../../catalog/sources/src-carparts-993-fan-housing-aluminium.json)
- [`catalog/sources/src-eos-alsi10mg-current-page.json`](../../catalog/sources/src-eos-alsi10mg-current-page.json)
- [`parts/993-eng-fan-housing-alsi10mg-f0-0001/evidence/engineering-screen.json`](../../parts/993-eng-fan-housing-alsi10mg-f0-0001/evidence/engineering-screen.json)

## Dossiers de conception

- [993_ENGINE_COOLING_FAN_SYSTEM_F0](../../docs/993/993_ENGINE_COOLING_FAN_SYSTEM_F0.md)
- [993_FAN_HOUSING_ALSI10MG_F0](../../docs/993/993_FAN_HOUSING_ALSI10MG_F0.md)

---

*Page engendrée depuis la fiche du catalogue par `scripts/render_part_pages.py`, vérifiée par `make check`. Toute correction se fait dans la fiche, pas ici.*
