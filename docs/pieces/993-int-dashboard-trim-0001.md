<!-- engendre par scripts/render_part_pages.py - ne pas editer a la main -->

# Habillage de planche de bord, composite

**Statut : fonctionnel. Aucune pièce n'est libérée ; voir [SAFETY.md](../../SAFETY.md).**

Habillage de planche de bord du 993 reproduit en composite, **pour les seuls vehicules sans airbag passager**. La piece n'est pas la planche de bord : celle-ci, 993 502 027 02, est une tole de caisse. C'est l'habillage qui la recouvre, pose sur ecrous a griffes et vis autotaraudeuses. Retenue parce qu'aucun fabricant ne la propose en carbone, contrairement aux panneaux de carrosserie.

Fiche du catalogue : [`catalog/parts/993-int-dashboard-trim-0001.json`](../../catalog/parts/993-int-dashboard-trim-0001.json)

## Identité

| champ | valeur |
|---|---|
| identifiant | 993-INT-DASHBOARD-TRIM-0001 |
| génération | 993 |
| variantes | M564 sans airbag, Carrera RS M002, Carrera RS Clubsport M003 |
| années | 1994 à 1998 |
| références Porsche | 993 552 055 00, 993 552 056 00, 993 552 055 70, 993 552 056 70 |
| catégorie | interior_trim |
| classe de sécurité | functional |
| usage prévu | Habillage visible de la traverse de planche de bord sur vehicule sans airbag passager, portant les aerateurs et la casquette d'instruments, et recevant la baguette de protection des genoux qui reste d'origine |

## Matière et fabrication

| champ | valeur |
|---|---|
| procédé préféré | à décider |
| procédés candidats | casting |
| famille de matière | composite a matrice organique |
| nuance | fibre et resine a determiner ; le rendu visible impose un tissu et un etat de surface, ce que ne fait aucun panneau cache |
| norme | aucune |
| exigences fournisseur | non renseigné |
| post-traitement | detourage des ouvertures d'aerateurs et d'instruments, pose des inserts et des points d'accrochage, finition de surface visible, vernis et tenue UV, controle de jeu avec casquette, console centrale et montants |

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

- [`parts/993-int-dashboard-trim-0001/derived/dashboard_trim_concept_f0.step`](../../parts/993-int-dashboard-trim-0001/derived/dashboard_trim_concept_f0.step)

## Provenance et sources

| champ | valeur |
|---|---|
| licence de la fiche | MIT for the record, geometry not yet produced |

**Sources**

- [Porsche PET - 911 1994-1998 Type 993, catalogue de pieces revision Kat 017](https://rsworkshop.ch/downloaded/pet-porsche/993_1994-98_KATALOG.pdf)
- [Federleichte Elfer - table des masses, interieur 993](http://www.federleichte-elfer.de/dp93/innen.html)

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
