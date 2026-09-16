<!-- engendre par scripts/render_part_pages.py - ne pas editer a la main -->

# Capot avant, panneau composite

**Statut : fonctionnel. Aucune pièce n'est libérée ; voir [SAFETY.md](../../SAFETY.md).**

Capot avant du 993 reproduit en composite a partir du panneau d'origine en acier. Piece de peau boulonnee, sans fonction structurale ni barre anti-intrusion, retenue comme premier pilote de carrosserie allegee.

Fiche du catalogue : [`catalog/parts/993-body-front-lid-0001.json`](../../catalog/parts/993-body-front-lid-0001.json)

## Identité

| champ | valeur |
|---|---|
| identifiant | 993-BODY-FRONT-LID-0001 |
| génération | 993 |
| variantes | a_confirmer_sur_vehicule |
| années | 1994 à 1998 |
| références Porsche | 993 511 010 01, 993 511 010 31 |
| catégorie | body_panel |
| classe de sécurité | functional |
| usage prévu | Fermeture du compartiment avant ; la piece ne porte aucune charge, mais sa retention engage la securite a vitesse elevee |

## Matière et fabrication

| champ | valeur |
|---|---|
| procédé préféré | à décider |
| procédés candidats | casting |
| famille de matière | composite a matrice organique |
| nuance | fibre et resine a determiner ; verre, carbone ou hybride |
| norme | aucune |
| exigences fournisseur | non renseigné |
| post-traitement | detourage, pose des interfaces de charniere et de serrure, controle de jeu et d'affleurement |

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

- [`parts/993-body-front-lid-0001/derived/front_lid_concept_f0.step`](../../parts/993-body-front-lid-0001/derived/front_lid_concept_f0.step)

## Provenance et sources

| champ | valeur |
|---|---|
| licence de la fiche | MIT for the record, geometry not yet produced |

**Sources**

- [Paul Stephens Autoart - 993R, allegement de carrosserie](https://psautoart.com/993r/)
- [Presse specialisee - Gunther Werks, 993 a carrosserie carbone](https://www.carscoops.com/2022/08/gunther-werks-project-tornado-is-a-carbon-bodied-porsche-993-turbo-restomod-with-up-to-700-hp/)
- [Federleichte Elfer - table des masses, pieces exterieures 993](http://www.federleichte-elfer.de/dp93/aussen.html)

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
