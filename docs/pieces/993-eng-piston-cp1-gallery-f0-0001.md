<!-- engendre par scripts/render_part_pages.py - ne pas editer a la main -->

# Piston M64/60 à galerie de refroidissement, concept CP1 F0

**Statut : **interdit en l'état**. Aucune pièce n'est libérée ; voir [SAFETY.md](../../SAFETY.md).**

Concept indépendant de piston LPBF Aheadd CP1 avec galerie torique sous calotte et deux ports temporaires de dépoudrage. Seuls l'alésage/course/régime M64/60 et le précédent méthodologique Porsche sont publiés ; toute la géométrie du piston reste une hypothèse F0.

Fiche du catalogue : [`catalog/parts/993-eng-piston-cp1-gallery-f0-0001.json`](../../catalog/parts/993-eng-piston-cp1-gallery-f0-0001.json)

## Identité

| champ | valeur |
|---|---|
| identifiant | 993-ENG-PISTON-CP1-GALLERY-F0-0001 |
| génération | 993 |
| variantes | 993_Turbo, M64_60_research |
| années | 1995 à 1998 |
| références Porsche | non renseigné |
| catégorie | piston_with_cooling_gallery |
| classe de sécurité | prohibited_pending_engineering |
| usage prévu | Criblage CAO, DfAM, mécanique de plaque, inertie, pression d'axe, conduction et hydraulique de galerie ; aucune fabrication, installation ou mise en route moteur autorisée |

## Matière et fabrication

| champ | valeur |
|---|---|
| procédé préféré | LPBF |
| procédés candidats | LPBF, DMLS, CNC, casting |
| famille de matière | alliage aluminium-fer-zirconium LPBF candidat |
| nuance | Constellium Aheadd CP1, route Velo3D Sapphire 50 µm de criblage uniquement |
| norme | AMS7074 pour la poudre et spécification piston/machine propre au programme à contractualiser |
| exigences fournisseur | poudre CP1, machine, paramètres, orientation, lot et recyclage traçables, coupons orientés avec traction, fatigue, fluage, conductivité et dilatation de l'ambiante à la température qualifiée, simulation et témoins de distorsion pour calotte, galerie, bossages et gorges, CT avant et après usinage/fermeture des ports, porosité et épaisseur de galerie contractualisées, métrologie du profil de jupe, ovalisation, conicité, compression height, gorges, axe et masse bout à bout, épreuve hydraulique, cycles thermomécaniques, fatigue grandeur réelle et 200 h moteur avant véhicule |
| post-traitement | évacuation contrôlée de toute la poudre par deux ports temporaires opposés, traitement 400 °C pendant 4 h selon la route publiée, à requalifier sur la pièce, HIP à décider après analyse des défauts, de la fatigue et de la galerie, fermeture des ports par procédé qualifié puis épreuve et CT de la galerie, usinage du diamètre, de la jupe, des gorges, des alésages d'axe et des faces de référence, finition, revêtement antifriction, appairage axe/segments et équilibrage par jeu |

## Géométrie

| champ | valeur |
|---|---|
| type de source | mixed |
| format du maître | build123d |
| unités | mm |
| précision (mm) | non renseigné |

**Fichier maître**

- [`parts/993-eng-piston-cp1-gallery-f0-0001/source/piston.py`](../../parts/993-eng-piston-cp1-gallery-f0-0001/source/piston.py)

**Fichiers dérivés**

- [`parts/993-eng-piston-cp1-gallery-f0-0001/derived/piston_cp1_gallery_f0.step`](../../parts/993-eng-piston-cp1-gallery-f0-0001/derived/piston_cp1_gallery_f0.step)

## Provenance et sources

| champ | valeur |
|---|---|
| licence de la fiche | MIT pour le concept, le script et les calculs ; aucune photographie, surface Porsche/MAHLE/Swindon ou géométrie commerciale redistribuée |

**Sources**

- [PorscheFanatics - précédent piston additif et pistons 993](https://porschefanatics.com/parts/c/engine-internals/)
- [Porsche Newsroom - pistons fabriqués par fusion laser](https://newsroom.porsche.com/en/2020/technology/porsche-cooperation-mahle-trumpf-pistons-3d-printer-power-efficiency-911-gt2-rs-21462.html)
- [elferclassic - données techniques allemandes du 993 Turbo](https://www.elferclassic.de/technik/techdaten/993-turbo-95-98-techdat.php)
- [Velo3D - Aheadd CP1 Material & Process Capability](https://velo3d.com/wp-content/uploads/2025/04/Velo3D-Material-Datasheet-Aluminum-CP1.pdf)
- [Constellium - Aheadd CP1 product fact sheet](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/product_sheet_aheadd_cp1_nov_2021docx.e81a7d073ebf.pdf)
- [IAV / GVSETS 2018 - piston diesel additif](https://events.esd.org/wp-content/uploads/2018/07/3D-Printed-Piston-for-Heavy-Duty-Diesel-Engines.pdf)

## Validation

| champ | valeur |
|---|---|
| statut | concept |
| essais véhicule | non renseigné |
| revu par |  |
| limites | non renseigné |

**Preuves**

- [`catalog/sources/src-porschefanatics-993-additive-piston-precedent.json`](../../catalog/sources/src-porschefanatics-993-additive-piston-precedent.json)
- [`catalog/sources/src-porsche-additive-piston-validation.json`](../../catalog/sources/src-porsche-additive-piston-validation.json)
- [`catalog/sources/src-elferclassic-993-turbo-technical-data.json`](../../catalog/sources/src-elferclassic-993-turbo-technical-data.json)
- [`catalog/sources/src-velo3d-cp1-material-datasheet.json`](../../catalog/sources/src-velo3d-cp1-material-datasheet.json)
- [`catalog/sources/src-constellium-aheadd-cp1-product-sheet.json`](../../catalog/sources/src-constellium-aheadd-cp1-product-sheet.json)
- [`catalog/sources/src-iav-2018-additive-heavy-duty-piston.json`](../../catalog/sources/src-iav-2018-additive-heavy-duty-piston.json)
- [`catalog/twins/twin-993-m64-60-piston-gallery-f0.json`](../../catalog/twins/twin-993-m64-60-piston-gallery-f0.json)
- [`parts/993-eng-piston-cp1-gallery-f0-0001/evidence/engineering-screen.json`](../../parts/993-eng-piston-cp1-gallery-f0-0001/evidence/engineering-screen.json)
- [`twins/993-m64-60-piston-gallery-f0/evidence/picogk-f0/picogk-optimization-screen.json`](../../twins/993-m64-60-piston-gallery-f0/evidence/picogk-f0/picogk-optimization-screen.json)
- [`twins/993-m64-60-piston-gallery-f0/evidence/picogk-f0/picogk-output-integrity.json`](../../twins/993-m64-60-piston-gallery-f0/evidence/picogk-f0/picogk-output-integrity.json)
- [`twins/993-m64-60-piston-gallery-f0/evidence/calculix-f0/calculix-thermomechanical-screen.json`](../../twins/993-m64-60-piston-gallery-f0/evidence/calculix-f0/calculix-thermomechanical-screen.json)
- [`twins/993-m64-60-piston-gallery-f0/evidence/lpbf-f0/993-eng-piston-cp1-gallery-f0-0001-lpbf-geometry-report.json`](../../twins/993-m64-60-piston-gallery-f0/evidence/lpbf-f0/993-eng-piston-cp1-gallery-f0-0001-lpbf-geometry-report.json)
- [`twins/993-m64-60-piston-gallery-f0/evidence/simready-f0/simready-validation-summary.json`](../../twins/993-m64-60-piston-gallery-f0/evidence/simready-f0/simready-validation-summary.json)

## Dossiers de conception

- [993_PISTON_CP1_COOLING_GALLERY_F0](../../docs/993/993_PISTON_CP1_COOLING_GALLERY_F0.md)

---

*Page engendrée depuis la fiche du catalogue par `scripts/render_part_pages.py`, vérifiée par `make check`. Toute correction se fait dans la fiche, pas ici.*
