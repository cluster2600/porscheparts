<!-- engendre par scripts/render_part_pages.py - ne pas editer a la main -->

# Soupape d'admission 993 - proxy F1 et variante titane

**Statut : **interdit en l'état**. Aucune pièce n'est libérée ; voir [SAFETY.md](../../SAFETY.md).**

Proxy parametrique non fonctionnel pour comparer l'encombrement et la masse d'une soupape d'admission 993 de tete 49 mm et queue 8 mm, avec variante Ti-6Al-4V explicitement limitee a la simulation.

Fiche du catalogue : [`catalog/parts/993-eng-intake-valve-f1-0001.json`](../../catalog/parts/993-eng-intake-valve-f1-0001.json)

## Identité

| champ | valeur |
|---|---|
| identifiant | 993-ENG-INTAKE-VALVE-F1-0001 |
| génération | 993 |
| variantes | 993_C2, 993_C4, 993_Turbo |
| années | 1994 à 1998 |
| références Porsche | 99310540902 |
| catégorie | engine_valvetrain |
| classe de sécurité | prohibited_pending_engineering |
| usage prévu | Simulation de masse, preparation de collision et controle d'encombrement uniquement |

## Matière et fabrication

| champ | valeur |
|---|---|
| procédé préféré | DMLS |
| procédés candidats | CNC, LPBF, DMLS |
| famille de matière | titanium comparison |
| nuance | Ti-6Al-4V Grade 5 |
| norme | ASTM F2924 chemistry reference |
| exigences fournisseur | lot traceability, process qualification, CT and metallography, dimensional report, fatigue and hot-valvetrain validation, professional engineering release |
| post-traitement | heat treatment qualified for the exact process, HIP decision by fatigue qualification, finish machining of stem, tip, groove and seat, surface treatment and polishing to be engineered |

**Titane**

| champ | valeur |
|---|---|
| alliage | Ti-6Al-4V Grade 5 candidate for intake study only |
| traitement thermique | to be tied to machine and parameter set; EOS reference recommends stress relief/ductility treatment |
| HIP | to_be_determined |
| surfaces usinées | stem, seat face, tip, keeper groove |
| inspection | CT, density, metallography, surface roughness, dimensional inspection, high-cycle fatigue |
| isolation galvanique | compatibility with guide, seat, retainer and coatings must be reviewed |
| hypothèses de fatigue | non renseigné |

## Géométrie

| champ | valeur |
|---|---|
| type de source | estimated |
| format du maître | build123d |
| unités | mm |
| précision (mm) | non renseigné |

**Fichier maître**

- [`twins/reference-935-cylinder-head/source/build_valve_variants.py`](../../twins/reference-935-cylinder-head/source/build_valve_variants.py)

**Fichiers dérivés**

- [`parts/993-eng-intake-valve-f1-0001/derived/993-intake-49-f1.step`](../../parts/993-eng-intake-valve-f1-0001/derived/993-intake-49-f1.step)

## Provenance et sources

| champ | valeur |
|---|---|
| licence de la fiche | MIT for code and record; no third-party geometry redistributed |

**Sources**

- [FVD - Dimensions declarees de soupape d'admission 993](https://www.fvd.net/de/shop/einlassventil-49mm-993-94-95-turbo-95-98-m64-05-06-07-08-60-nicht-natrium-gekuehlt-99310540902eq1-99310540902~p306501)
- [EOS Titanium Ti64 Grade 5](https://www.eos.info/metal-solutions/metal-materials/data-sheets/mds-eos-titanium-ti64-grade-5)

## Validation

| champ | valeur |
|---|---|
| statut | concept |
| essais véhicule | non renseigné |
| revu par |  |
| limites | non renseigné |

**Preuves**

- `SRC-FVD-993-INLET-VALVE-DIMENSIONS` — *absent du dépôt*
- `SRC-EOS-TI64-GRADE5` — *absent du dépôt*

---

*Page engendrée depuis la fiche du catalogue par `scripts/render_part_pages.py`, vérifiée par `make check`. Toute correction se fait dans la fiche, pas ici.*
