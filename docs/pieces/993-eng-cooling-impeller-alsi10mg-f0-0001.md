<!-- engendre par scripts/render_part_pages.py - ne pas editer a la main -->

# Turbine de refroidissement moteur, concept tournant AlSi10Mg F0

**Statut : **interdit en l'état**. Aucune pièce n'est libérée ; voir [SAFETY.md](../../SAFETY.md).**

Concept indépendant d'une turbine monobloc réunissant moyeu, douze pales balayées et anneau périphérique. PorscheFanatics et les revendeurs établissent la référence 964 106 015 31, une enveloppe commerciale, deux masses cohérentes et une déclaration aluminium, mais aucune géométrie fonctionnelle. Le test d'ensemble rejette explicitement l'interférence avec le carter F0 précédent.

Fiche du catalogue : [`catalog/parts/993-eng-cooling-impeller-alsi10mg-f0-0001.json`](../../catalog/parts/993-eng-cooling-impeller-alsi10mg-f0-0001.json)

## Identité

| champ | valeur |
|---|---|
| identifiant | 993-ENG-COOLING-IMPELLER-ALSI10MG-F0-0001 |
| génération | 993 |
| variantes | 993_Carrera_fitment_to_confirm, 964_shared_component |
| années | 1994 à 1998 |
| références Porsche | 96410601531 |
| catégorie | engine_cooling_fan_impeller |
| classe de sécurité | prohibited_pending_engineering |
| usage prévu | Criblage F0 de CAO ouverte, valeur DfAM, masse, survitesse, contrainte centrifuge, modal, débit cible, thermique et compatibilité avec le carter F0 ; aucune fabrication, rotation, installation ou mise en route autorisée |

## Matière et fabrication

| champ | valeur |
|---|---|
| procédé préféré | à décider |
| procédés candidats | LPBF, DMLS, CNC, casting |
| famille de matière | alliage aluminium-silicium-magnésium candidat LPBF |
| nuance | EOS Aluminium AlSi10Mg T6 de comparaison ; pièce commerciale déclarée seulement aluminium non spécifié |
| norme | DIN EN 1706 EN AC-43000 et ASTM F3318 pour le candidat ; spécification tournante, HCF, balance et survitesse propre au programme à contractualiser |
| exigences fournisseur | machine, paramètres, orientation, supports, poudre, recyclage et lot traçables, coupons orientés avec traction, HCF, fretting et corrosion à chaud, éprouvettes entaillées et témoins de pied de pale dans l'état de surface final, CT intégral, FPI et métallographie avec critères de défauts zonés, métrologie moyeu, alésage, voile, concentricité, pales, jeu et masse, preuve de balance, survitesse, vibration, débit, perte de pale/confinement et endurance |
| post-traitement | orientation, supports et accès entre pales à qualifier, détensionnement puis T6 avec trempe et distorsion suivies, HIP obligatoire à décider par la carte HCF/défauts et non par habitude, usinage du moyeu, alésage, faces et références de correction de balance, finition contrôlée des pieds de pales sans entailles ni média retenu, protection anticorrosion compatible température et fretting, équilibrage dynamique à deux plans après état final |

## Géométrie

| champ | valeur |
|---|---|
| type de source | mixed |
| format du maître | build123d |
| unités | mm |
| précision (mm) | non renseigné |

**Fichier maître**

- [`parts/993-eng-cooling-impeller-alsi10mg-f0-0001/source/cooling_impeller.py`](../../parts/993-eng-cooling-impeller-alsi10mg-f0-0001/source/cooling_impeller.py)

**Fichiers dérivés**

- [`parts/993-eng-cooling-impeller-alsi10mg-f0-0001/derived/cooling_impeller_alsi10mg_f0.step`](../../parts/993-eng-cooling-impeller-alsi10mg-f0-0001/derived/cooling_impeller_alsi10mg_f0.step)

## Provenance et sources

| champ | valeur |
|---|---|
| licence de la fiche | MIT pour le concept, le script et les calculs ; aucune photographie, illustration, surface Porsche/PorscheFanatics/FVD/Porsche Poitiers/Partworks/EOS ou géométrie commerciale redistribuée |

**Sources**

- [PorscheFanatics - turbine de refroidissement moteur 964/993](https://porschefanatics.com/parts/c/cooling/)
- [FVD Brombacher - turbine 964/993 964 106 015 31](https://www.fvd.net/de-ch/shop/laufrad-964-89-94-993-94-98-96410601531~p252655)
- [Centre Service Porsche Poitiers - turbine 964 106 015 31](https://www.boutiqueporschepoitiers.fr/produit/96410601531-turbine-de-refroidissement-moteur-porsche/)
- [Partworks - turbine 964/993 déclarée aluminium](https://partworks.de/Original-fan-wheel-for-Porsche-964-993-Carrera-96410601531)
- [EOS Aluminium AlSi10Mg material data sheet](https://www.eos.info/metal-solutions/metal-materials/data-sheets/mds-eos-aluminium-alsi10mg)

## Validation

| champ | valeur |
|---|---|
| statut | concept |
| essais véhicule | non renseigné |
| revu par |  |
| limites | non renseigné |

**Preuves**

- [`catalog/sources/src-porschefanatics-993-engine-cooling-impeller-candidate.json`](../../catalog/sources/src-porschefanatics-993-engine-cooling-impeller-candidate.json)
- [`catalog/sources/src-fvd-964-993-fan-wheel-dimensions.json`](../../catalog/sources/src-fvd-964-993-fan-wheel-dimensions.json)
- [`catalog/sources/src-porsche-poitiers-964-993-fan-wheel-mass.json`](../../catalog/sources/src-porsche-poitiers-964-993-fan-wheel-mass.json)
- [`catalog/sources/src-partworks-964-993-fan-wheel-aluminium.json`](../../catalog/sources/src-partworks-964-993-fan-wheel-aluminium.json)
- [`catalog/sources/src-eos-alsi10mg-current-page.json`](../../catalog/sources/src-eos-alsi10mg-current-page.json)
- [`parts/993-eng-fan-housing-alsi10mg-f0-0001/evidence/engineering-screen.json`](../../parts/993-eng-fan-housing-alsi10mg-f0-0001/evidence/engineering-screen.json)
- [`parts/993-eng-cooling-impeller-alsi10mg-f0-0001/evidence/engineering-screen.json`](../../parts/993-eng-cooling-impeller-alsi10mg-f0-0001/evidence/engineering-screen.json)

## Dossiers de conception

- [993_COOLING_IMPELLER_ALSI10MG_F0](../../docs/993/993_COOLING_IMPELLER_ALSI10MG_F0.md)
- [993_ENGINE_COOLING_FAN_SYSTEM_F0](../../docs/993/993_ENGINE_COOLING_FAN_SYSTEM_F0.md)

---

*Page engendrée depuis la fiche du catalogue par `scripts/render_part_pages.py`, vérifiée par `make check`. Toute correction se fait dans la fiche, pas ici.*
