<!-- engendre par scripts/render_part_pages.py - ne pas editer a la main -->

# Couvercle thermique gauche de turbo 993, concept IN625 F0

**Statut : fonctionnel. Aucune pièce n'est libérée ; voir [SAFETY.md](../../SAFETY.md).**

Concept indépendant de coque ouverte avec bossages intégrés pour cribler une refabrication LPBF en IN625. PorscheFanatics confirme l'identité PET ; FVD publie seulement l'enveloppe et la masse du couvercle gauche 993 123 113 51.

Fiche du catalogue : [`catalog/parts/993-eng-turbo-heat-shield-in625-f0-0001.json`](../../catalog/parts/993-eng-turbo-heat-shield-in625-f0-0001.json)

## Identité

| champ | valeur |
|---|---|
| identifiant | 993-ENG-TURBO-HEAT-SHIELD-IN625-F0-0001 |
| génération | 993 |
| variantes | 993_Turbo, 993_GT2 |
| années | 1995 à 1998 |
| références Porsche | 99312311351 |
| catégorie | turbocharger_heat_protection |
| classe de sécurité | functional |
| usage prévu | Criblage CAO, thermique, mécanique et DfAM ; aucune fabrication pour montage ni installation véhicule autorisée |

## Matière et fabrication

| champ | valeur |
|---|---|
| procédé préféré | à décider |
| procédés candidats | LPBF, DMLS, sheet_metal |
| famille de matière | superalliage nickel LPBF candidat |
| nuance | EOS NickelAlloy IN625 / UNS N06625 de criblage ; matière OEM inconnue |
| norme | ASTM F3055, AMS 7000 ou AMS 7001 à contractualiser selon le procédé retenu |
| exigences fournisseur | poudre, machine, paramètres, orientation, lot et recyclage traçables, capabilité démontrée sur paroi 0,8 mm et coupons représentatifs, contrôle dimensionnel de l'enveloppe, des bords et interfaces, CT ou radiographie des bossages et ressuage après finition, rugosité, porosité, contraintes résiduelles et distorsion contractualisées, essais thermiques, vibratoires et cycliques avant montage |
| post-traitement | retrait des supports avec ouverture complète de la coque, détensionnement qualifié pour la machine et les paramètres, découpe du plateau et redressage contrôlé de la paroi mince, usinage ou alésage des interfaces après ajout des surépaisseurs, ébavurage et finition des bords, revêtement thermique à décider après essais |

## Géométrie

| champ | valeur |
|---|---|
| type de source | mixed |
| format du maître | build123d |
| unités | mm |
| précision (mm) | non renseigné |

**Fichier maître**

- [`parts/993-eng-turbo-heat-shield-in625-f0-0001/source/turbo_heat_shield.py`](../../parts/993-eng-turbo-heat-shield-in625-f0-0001/source/turbo_heat_shield.py)

**Fichiers dérivés**

- [`parts/993-eng-turbo-heat-shield-in625-f0-0001/derived/turbo_heat_shield_in625_f0.step`](../../parts/993-eng-turbo-heat-shield-in625-f0-0001/derived/turbo_heat_shield_in625_f0.step)

## Images

![993-eng-turbo-heat-shield-in625-f0-0001-lpbf-geometry-screen](../../parts/993-eng-turbo-heat-shield-in625-f0-0001/evidence/lpbf-f0/993-eng-turbo-heat-shield-in625-f0-0001-lpbf-geometry-screen.png)

*parts/993-eng-turbo-heat-shield-in625-f0-0001/evidence/lpbf-f0/993-eng-turbo-heat-shield-in625-f0-0001-lpbf-geometry-screen.png*

## Provenance et sources

| champ | valeur |
|---|---|
| licence de la fiche | MIT pour le concept, le script et les calculs ; aucune photographie, illustration PET ou géométrie commerciale redistribuée |

**Sources**

- [PorscheFanatics - relevé PET des groupes Turbo 993](https://porschefanatics.com/oem/993/202-16/)
- [FVD - couvercle thermique gauche 99312311351](https://www.fvd.net/en-ch/shop/cover-heat-protection-turbo-loader-left-99312311351~p248974)
- [EOS NickelAlloy IN625 material data sheet](https://www.eos.info/05-datasheet-images/Assets_MDS_Metal/EOS_NickelAlloy_IN625/Material_DataSheet_EOS_NickelAlloy_IN625_en.pdf)
- [Special Metals - INCONEL alloy 625](https://www.specialmetals.com/documents/technical-bulletins/inconel/inconel-alloy-625.pdf)

## Validation

| champ | valeur |
|---|---|
| statut | concept |
| essais véhicule | non renseigné |
| revu par |  |
| limites | non renseigné |

**Preuves**

- [`catalog/sources/src-porschefanatics-993-turbo-pet.json`](../../catalog/sources/src-porschefanatics-993-turbo-pet.json)
- [`catalog/sources/src-fvd-993-turbo-heat-shield-dimensions.json`](../../catalog/sources/src-fvd-993-turbo-heat-shield-dimensions.json)
- [`catalog/sources/src-eos-in625-material-data.json`](../../catalog/sources/src-eos-in625-material-data.json)
- [`catalog/sources/src-special-metals-inconel-625.json`](../../catalog/sources/src-special-metals-inconel-625.json)
- [`parts/993-eng-turbo-heat-shield-in625-f0-0001/evidence/engineering-screen.json`](../../parts/993-eng-turbo-heat-shield-in625-f0-0001/evidence/engineering-screen.json)

## Dossiers de conception

- [993_TURBO_HEAT_SHIELD_IN625_F0](../../docs/993/993_TURBO_HEAT_SHIELD_IN625_F0.md)

---

*Page engendrée depuis la fiche du catalogue par `scripts/render_part_pages.py`, vérifiée par `make check`. Toute correction se fait dans la fiche, pas ici.*
