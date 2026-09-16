<!-- engendre par scripts/render_part_pages.py - ne pas editer a la main -->

# Collecteur d'admission trois conduits 993, concept AlSi10Mg F0

**Statut : fonctionnel. Aucune pièce n'est libérée ; voir [SAFETY.md](../../SAFETY.md).**

Concept indépendant de collecteur à trois conduits coniques décalés et deux brides communes pour cribler le LPBF AlSi10Mg. PorscheFanatics et Patrick Motorsports recoupent le kit PMO FUE PMO 9150, annoncé 46 x 42 x 100 mm, trois boulons, deux pièces et finition aluminium brute ; aucune géométrie d'interface n'est publiée.

Fiche du catalogue : [`catalog/parts/993-eng-three-runner-intake-alsi10mg-f0-0001.json`](../../catalog/parts/993-eng-three-runner-intake-alsi10mg-f0-0001.json)

## Identité

| champ | valeur |
|---|---|
| identifiant | 993-ENG-THREE-RUNNER-INTAKE-ALSI10MG-F0-0001 |
| génération | 993 |
| variantes | 993_3.6L_conversion, 993_3.8L_conversion, 964_shared_engine_conversion |
| années | 1994 à 1998 |
| références Porsche | non renseigné |
| catégorie | three_runner_intake_manifold |
| classe de sécurité | functional |
| usage prévu | Criblage CAO, DfAM, débit, acoustique, pression et thermique ; aucune fabrication, installation ou mise en route moteur autorisée |

## Matière et fabrication

| champ | valeur |
|---|---|
| procédé préféré | à décider |
| procédés candidats | LPBF, DMLS, CNC, casting |
| famille de matière | alliage aluminium LPBF candidat |
| nuance | AlSi10Mg générique de criblage ; alliage et état du produit PMO inconnus |
| norme | ASTM F3318 et spécification moteur propre au programme à contractualiser si le LPBF est retenu |
| exigences fournisseur | poudre, machine, paramètres, orientation, lot et recyclage traçables, capabilité sur parois de 2 mm, conduits inclinés et brides de 6 mm, simulation de supports, recoater et distorsion avant lancement, CT des conduits et métrologie des ports, brides et futures fixations, porosité, rugosité, planéité, étanchéité et propreté contractualisées, essais de débit, pression, vibration, cycles thermiques et banc moteur avant véhicule |
| post-traitement | évacuation complète de la poudre par les trois conduits ouverts, détensionnement et traitement thermique qualifiés sur coupons représentatifs, découpe du plateau avec contrôle de planéité des brides, usinage des deux brides, ports et perçages après ajout de surépaisseurs mesurées, ébavurage, polissage ou finition abrasive du chemin de gaz avec rugosité vérifiée, nettoyage particulaire et épreuve de fuite avant tout essai de débit |

## Géométrie

| champ | valeur |
|---|---|
| type de source | mixed |
| format du maître | build123d |
| unités | mm |
| précision (mm) | non renseigné |

**Fichier maître**

- [`parts/993-eng-three-runner-intake-alsi10mg-f0-0001/source/three_runner_intake.py`](../../parts/993-eng-three-runner-intake-alsi10mg-f0-0001/source/three_runner_intake.py)

**Fichiers dérivés**

- [`parts/993-eng-three-runner-intake-alsi10mg-f0-0001/derived/three_runner_intake_alsi10mg_f0.step`](../../parts/993-eng-three-runner-intake-alsi10mg-f0-0001/derived/three_runner_intake_alsi10mg_f0.step)

## Provenance et sources

| champ | valeur |
|---|---|
| licence de la fiche | MIT pour le concept, le script et les calculs ; aucune photographie, marque, illustration ou géométrie PMO/Porsche redistribuée |

**Sources**

- [PorscheFanatics - collecteur PMO 46 mm pour moteur 964/993](https://porschefanatics.com/parts/g/964/)
- [Patrick Motorsports - PMO FUE PMO 9150](https://patrickmotorsports.com/collections/all-engine/products/fuepmo9150)
- [EOS Aluminium AlSi10Mg material page](https://www.eos.info/metal-solutions/metal-materials/data-sheets/mds-eos-aluminium-alsi10mg)

## Validation

| champ | valeur |
|---|---|
| statut | concept |
| essais véhicule | non renseigné |
| revu par |  |
| limites | non renseigné |

**Preuves**

- [`catalog/sources/src-porschefanatics-pmo-964-993-46mm-intake-manifold.json`](../../catalog/sources/src-porschefanatics-pmo-964-993-46mm-intake-manifold.json)
- [`catalog/sources/src-patrick-pmo-964-993-46mm-intake-manifold.json`](../../catalog/sources/src-patrick-pmo-964-993-46mm-intake-manifold.json)
- [`catalog/sources/src-eos-alsi10mg-current-page.json`](../../catalog/sources/src-eos-alsi10mg-current-page.json)
- [`parts/993-eng-three-runner-intake-alsi10mg-f0-0001/evidence/engineering-screen.json`](../../parts/993-eng-three-runner-intake-alsi10mg-f0-0001/evidence/engineering-screen.json)

---

*Page engendrée depuis la fiche du catalogue par `scripts/render_part_pages.py`, vérifiée par `make check`. Toute correction se fait dans la fiche, pas ici.*
