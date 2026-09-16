<!-- engendre par scripts/render_part_pages.py - ne pas editer a la main -->

# Couvercle gauche de carter de chaîne 964 105 107 01, variante Ti-6Al-4V

**Statut : fonctionnel. Aucune pièce n'est libérée ; voir [SAFETY.md](../../SAFETY.md).**

Couvercle gauche boulonné étanche à l'huile du carter de chaîne, planche d'usine 103-05 position 15, apparié au joint 964 105 181 01. Refabrication en Ti-6Al-4V fraisé demandée explicitement. La pièce d'origine est en **magnésium coulé**, dont le mode de défaillance est la corrosion des portées d'étanchéité : c'est là, et non sur la masse, que le titane apporte quelque chose. Contre le magnésium le titane est 2,45 fois plus dense et perd les deux arbitrages de flexion de plaque, résistance comprise. Reste un obstacle sérieux : le couple galvanique titane/magnésium est le plus défavorable de la grille.

Fiche du catalogue : [`catalog/parts/993-eng-chain-case-lid-ti-f0-0001.json`](../../catalog/parts/993-eng-chain-case-lid-ti-f0-0001.json)

## Identité

| champ | valeur |
|---|---|
| identifiant | 993-ENG-CHAIN-CASE-LID-TI-F0-0001 |
| génération | 993 |
| variantes | 993_repartition_par_variante_a_confirmer |
| années | 1994 à 1998 |
| références Porsche | 964 105 107 01, 964 105 181 01 |
| catégorie | engine_timing_chain_case_lid |
| classe de sécurité | functional |
| usage prévu | Criblage paramétrique et préparation de mesure ; aucune fabrication ni montage autorisés avant relevé d'un exemplaire |

## Matière et fabrication

| champ | valeur |
|---|---|
| procédé préféré | CNC |
| procédés candidats | CNC |
| famille de matière | titane |
| nuance | Ti-6Al-4V Grade 5, plaque — choix assumé ; l'aluminium 6061 billet est la réponse du marché |
| norme | ASTM B265 pour la plaque, à contractualiser |
| exigences fournisseur | Certificat matière de la plaque, Planéité et état de surface tenus sur le plan de joint, Contrôle dimensionnel du contour, des entraxes et des perçages |
| post-traitement | surfaçage du plan de joint, planéité à définir après relevé, cassage d'arêtes, microbillage ou anodisation titane selon l'aspect visé, pâte anti-grippage sur la visserie, rondelles isolantes si contact métal direct |

**Titane**

| champ | valeur |
|---|---|
| alliage | Ti-6Al-4V Grade 5 |
| traitement thermique | aucun : pièce fraisée dans une plaque livrée à l'état recuit |
| HIP | not_applicable |
| surfaces usinées | plan de joint, perçages de fixation, contour |
| inspection | planéité du plan de joint, entraxes de perçage, épaisseur |
| isolation galvanique | Le couvercle se boulonne sur un carter lui aussi en magnésium. Le magnésium est le plus anodique des métaux de structure et le titane l'un des plus cathodiques : c'est le couple que TITANIUM.md nomme explicitement. Le joint 964 105 181 01 isole les portées, pas la visserie ni les chemins d'humidité. Un couvercle titane pourrait protéger sa propre portée tout en aggravant l'attaque du carter en face. Non résolu. |
| hypothèses de fatigue | non renseigné |

## Géométrie

| champ | valeur |
|---|---|
| type de source | estimated |
| format du maître | none |
| unités | mm |
| précision (mm) | non renseigné |

**Fichier maître**

- [`parts/993-eng-chain-case-lid-ti-f0-0001/source/chain_case_lid_screen.py`](../../parts/993-eng-chain-case-lid-ti-f0-0001/source/chain_case_lid_screen.py)

**Fichiers dérivés**

- aucun

## Provenance et sources

| champ | valeur |
|---|---|
| licence de la fiche | MIT pour la fiche et le script ; aucune géométrie tierce redistribuée |

**Sources**

- [Catalogue d'usine 993, planche 103-05 Chain case](https://porschefanatics.com/oem/993/103-05/)
- [Reproducteurs commerciaux du couvercle : LN Engineering et Auto-Service Schefter](https://lnengineering.com/porsche-964-993-chain-box-covers.html)

## Validation

| champ | valeur |
|---|---|
| statut | concept |
| essais véhicule | non renseigné |
| revu par |  |
| limites | non renseigné |

**Preuves**

- [`parts/993-eng-chain-case-lid-ti-f0-0001/evidence/parametric-screen.json`](../../parts/993-eng-chain-case-lid-ti-f0-0001/evidence/parametric-screen.json)
- [`catalog/sources/src-pet-993-103-05-chain-case.json`](../../catalog/sources/src-pet-993-103-05-chain-case.json)
- [`docs/993/993_COUVERCLE_CARTER_CHAINE_TI.md`](../../docs/993/993_COUVERCLE_CARTER_CHAINE_TI.md)
- [`catalog/sources/src-couvercle-carter-chaine-964-993-magnesium.json`](../../catalog/sources/src-couvercle-carter-chaine-964-993-magnesium.json)

## Dossiers de conception

- [993_COUVERCLE_CARTER_CHAINE_TI](../../docs/993/993_COUVERCLE_CARTER_CHAINE_TI.md)

---

*Page engendrée depuis la fiche du catalogue par `scripts/render_part_pages.py`, vérifiée par `make check`. Toute correction se fait dans la fiche, pas ici.*
