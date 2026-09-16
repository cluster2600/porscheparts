<!-- engendre par scripts/render_part_pages.py - ne pas editer a la main -->

# Berceau moteur Turbo (Motortraeger)

**Statut : **critique pour la sécurité**. Aucune pièce n'est libérée ; voir [SAFETY.md](../../SAFETY.md).**

Traverse portant le groupe motopropulseur du 993 Turbo, reference 993 115 021 53. Le catalogue PET la place dans le groupe illustre 109-00 « Engine suspension Turbo », position 17 : la destination Turbo est etablie, pas deduite. Piece structurale reprenant la masse du moteur et ses efforts dynamiques vers la caisse.

Fiche du catalogue : [`catalog/parts/993-eng-carrier-0001.json`](../../catalog/parts/993-eng-carrier-0001.json)

## Identité

| champ | valeur |
|---|---|
| identifiant | 993-ENG-CARRIER-0001 |
| génération | 993 |
| variantes | 993_Turbo |
| années | 1994 à 1998 |
| références Porsche | 993 115 021 53 |
| catégorie | powertrain_mounting |
| classe de sécurité | safety_critical |
| usage prévu | Support du groupe motopropulseur et transmission de ses efforts a la caisse |

## Matière et fabrication

| champ | valeur |
|---|---|
| procédé préféré | CNC |
| procédés candidats | CNC, casting, sheet_metal |
| famille de matière | acier ; 42CrMo4 trempe revenu ou 17-4PH envisages pour une piece usinee |
| nuance | nuance inconnue ; finition doree evoquant une zingaison passivee jaune |
| norme | aucune |
| exigences fournisseur | Tracabilite matiere et lot, Procede et parametres qualifies par le fabricant, Controle dimensionnel des interfaces de fixation, Controle non destructif adapte a une piece structurale, Rapport de fabrication conserve et relie a la revision du STEP |
| post-traitement | rayons de raccordement soignes, etat de surface fin dans les zones tendues, grenaillage de precontrainte, protection anticorrosion si nuance non inoxydable |

## Géométrie

| champ | valeur |
|---|---|
| type de source | estimated |
| format du maître | build123d |
| unités | mm |
| précision (mm) | non renseigné |

**Fichier maître**

- [`scripts/build_993_concept_f0.py`](../../scripts/build_993_concept_f0.py)

**Fichiers dérivés**

- [`parts/993-eng-carrier-0001/derived/engine_carrier_concept_f0.step`](../../parts/993-eng-carrier-0001/derived/engine_carrier_concept_f0.step)

## Provenance et sources

| champ | valeur |
|---|---|
| licence de la fiche | MIT for the record, geometry not yet produced |

**Sources**

- [Porsche Classic Genuine Parts Catalogue - 911 (993)](https://www.porsche.com/australia/accessoriesandservice/classic/originalpartscatalogue/)
- [teile.com - Motortraeger 911 993, groupe 109-00 Motoraufhaengung](https://teile.com/de/porsche-ersatzteile-onlineshop/modell-911-993/2/Motor-Kuehlung/109-Motoraufhaengung/5/109-00-Motoraufhaengung/Motortraeger/1503)
- [Rennline - tubular engine carrier for 964/993 non turbo](https://www.rennline.com/tubular-engine-carrier-sku-m19/)
- [Elferspot - Porsche 993 portrait, facts and specifications](https://www.elferspot.com/en/magazine/porsche-993-portrait/)
- [Porsche Fanatics - fiche OEM 993 115 021 53](https://porschefanatics.com/oem/993-115-021-53/)
- [Porsche PET - 911 1994-1998 Type 993, revision KAT 17](https://rsworkshop.ch/downloaded/pet-porsche/993_1994-98_KATALOG.pdf)
- [Porsche Club GB - Cracked engine mount bracket](https://www.porscheclubgb.com/forum/threads/cracked-engine-mount-bracket.124901/)
- [PFF - Rennline Motortraeger / Schwert](https://www.pff.de/thread/2823902-rennline-motortraeger-schwert/)
- [Porsche - manuel d'atelier 911 (993), groupe 10, table des couples de serrage](https://www.pelicanparts.com/More_Info/WKD483121.htm?pn=WKD-483-121-OEM)
- [FVD - Engine suspension bracket / carrier 993 Turbo, 99311502153](https://www.fvd.net/en-us/shop/)

## Validation

| champ | valeur |
|---|---|
| statut | concept |
| essais véhicule | non renseigné |
| revu par |  |
| limites | non renseigné |

**Preuves**

- aucun

---

*Page engendrée depuis la fiche du catalogue par `scripts/render_part_pages.py`, vérifiée par `make check`. Toute correction se fait dans la fiche, pas ici.*
