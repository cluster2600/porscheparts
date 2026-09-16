<!-- engendre par scripts/render_part_pages.py - ne pas editer a la main -->

# Bielle 993/993 Turbo, concept topologique Ti64 F0

**Statut : **interdit en l'état**. Aucune pièce n'est libérée ; voir [SAFETY.md](../../SAFETY.md).**

Concept indépendant à deux membrures ouvertes pour cribler une bielle Ti-6Al-4V LPBF. Les cotes clés viennent d'une fiche PAUTER/TZR ; les diamètres extérieurs, membrures, séparation du chapeau et passages de vis restent des hypothèses F0 sans reprise de surface commerciale.

Fiche du catalogue : [`catalog/parts/993-eng-connecting-rod-ti64-f0-0001.json`](../../catalog/parts/993-eng-connecting-rod-ti64-f0-0001.json)

## Identité

| champ | valeur |
|---|---|
| identifiant | 993-ENG-CONNECTING-ROD-TI64-F0-0001 |
| génération | 993 |
| variantes | 993, 993_Turbo, M64_60_research |
| années | 1993 à 1998 |
| références Porsche | non renseigné |
| catégorie | connecting_rod |
| classe de sécurité | prohibited_pending_engineering |
| usage prévu | Criblage CAO, DfAM, masse, charges synthétiques, contraintes nominales et flambement ; aucune fabrication, installation ou mise en route moteur autorisée |

## Matière et fabrication

| champ | valeur |
|---|---|
| procédé préféré | LPBF |
| procédés candidats | LPBF, DMLS, CNC |
| famille de matière | titane candidat |
| nuance | Ti-6Al-4V Grade 5 LPBF de criblage ; alliage PAUTER titane inconnu |
| norme | ASTM F2924 et spécification bielle propre au programme à contractualiser |
| exigences fournisseur | poudre, machine, paramètres, orientation, lot et recyclage de poudre traçables, coupons orientés avec traction, ténacité, fatigue et défauts représentatifs après tous post-traitements, analyse dimensionnelle complète du plan de joint, entraxe, alésages, équerrage et parallélisme, CT du corps et du chapeau, ressuage après usinage et contrôle de rugosité, preuve de capabilité sur précharge, friction, serrage et durée de vie des vis retenues, essais de preuve puis fatigue grandeur réelle avec enveloppe moteur approuvée avant tout dyno |
| post-traitement | évacuation de poudre par topologie entièrement ouverte, détensionnement et traitement thermique qualifiés pour machine, paramètres et orientation, HIP à décider sur population de défauts et essais de fatigue représentatifs, séparation et usinage du chapeau, du plan de joint, des logements de vis et des portées, usinage et finition des deux alésages avec bague de pied et coussinets définis, rayonnage, polissage des chemins de charge, équilibrage bout à bout et par jeu |

**Titane**

| champ | valeur |
|---|---|
| alliage | Ti-6Al-4V Grade 5 candidat uniquement ; l'alliage de l'option PAUTER n'est pas publié |
| traitement thermique | Traitement de détente et de ductilité EOS à qualifier ; aucune recette n'est gelée sans fournisseur, orientation et coupons |
| HIP | to_be_determined |
| surfaces usinées | alésage de tête et portées de coussinets, alésage de pied et portée de bague, plan de joint et datums du chapeau, logements, portées et faces des vis, faces latérales et jeux au vilebrequin |
| inspection | CT du corps, du chapeau, des congés et des transitions de membrures, métrologie complète des alésages, entraxe, plan de joint, parallélisme et équerrage, ressuage après usinage et finition, rugosité, porosité, couche alpha, contraintes résiduelles et équilibrage, essais de preuve et fatigue grandeur réelle avec vis, coussinets et axes représentatifs |
| isolation galvanique | Qualifier couples titane-acier des vis, coussinets et axe, fretting, grippage, revêtements, lubrification, dilatations et contamination galvanique dans l'huile moteur. |
| hypothèses de fatigue | non renseigné |

## Géométrie

| champ | valeur |
|---|---|
| type de source | mixed |
| format du maître | build123d |
| unités | mm |
| précision (mm) | non renseigné |

**Fichier maître**

- [`parts/993-eng-connecting-rod-ti64-f0-0001/source/connecting_rod.py`](../../parts/993-eng-connecting-rod-ti64-f0-0001/source/connecting_rod.py)

**Fichiers dérivés**

- [`parts/993-eng-connecting-rod-ti64-f0-0001/derived/connecting_rod_ti64_f0.step`](../../parts/993-eng-connecting-rod-ti64-f0-0001/derived/connecting_rod_ti64_f0.step)

## Provenance et sources

| champ | valeur |
|---|---|
| licence de la fiche | MIT pour le concept, le script et les calculs ; aucune photographie, surface PAUTER/Porsche ou géométrie commerciale redistribuée |

**Sources**

- [TZR Motorsport - cotes fabricant de bielle PAUTER 993/993 Turbo](https://www.tzr-motorsport.de/993-230-580-1270F)
- [PorscheFanatics - bielles titane pour moteur 993](https://porschefanatics.com/engine/993/)
- [EOS Titanium Ti64 Grade 5 material data sheet](https://www.eos.info/metal-solutions/metal-materials/data-sheets/mds-eos-titanium-ti64-grade-5)
- [TIMETAL 6-4 physical properties](https://www.timet.com/documents/datasheets/alpha-and-beta-alloys/timetal-6-4.pdf)
- [elferclassic - données techniques du 993 Turbo](https://www.elferclassic.de/technik/techdaten/993-turbo-95-98-techdat.php)

## Validation

| champ | valeur |
|---|---|
| statut | concept |
| essais véhicule | non renseigné |
| revu par |  |
| limites | non renseigné |

**Preuves**

- [`catalog/sources/src-tzr-pauter-993-connecting-rod-dimensions.json`](../../catalog/sources/src-tzr-pauter-993-connecting-rod-dimensions.json)
- [`catalog/sources/src-porschefanatics-993-titanium-connecting-rods.json`](../../catalog/sources/src-porschefanatics-993-titanium-connecting-rods.json)
- [`catalog/sources/src-eos-ti64-grade5.json`](../../catalog/sources/src-eos-ti64-grade5.json)
- [`catalog/sources/src-timet-ti64-physical-properties.json`](../../catalog/sources/src-timet-ti64-physical-properties.json)
- [`catalog/sources/src-cecchel-2022-additive-ti-connecting-rod-fatigue.json`](../../catalog/sources/src-cecchel-2022-additive-ti-connecting-rod-fatigue.json)
- [`catalog/sources/src-elferclassic-993-turbo-technical-data.json`](../../catalog/sources/src-elferclassic-993-turbo-technical-data.json)
- [`parts/993-eng-connecting-rod-ti64-f0-0001/evidence/engineering-screen.json`](../../parts/993-eng-connecting-rod-ti64-f0-0001/evidence/engineering-screen.json)

---

*Page engendrée depuis la fiche du catalogue par `scripts/render_part_pages.py`, vérifiée par `make check`. Toute correction se fait dans la fiche, pas ici.*
