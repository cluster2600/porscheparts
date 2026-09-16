<!-- engendre par scripts/render_part_pages.py - ne pas editer a la main -->

# Soupapes d'echappement 993 - proxies F1

**Statut : **interdit en l'état**. Aucune pièce n'est libérée ; voir [SAFETY.md](../../SAFETY.md).**

Proxies parametriques non fonctionnels des soupapes d'echappement Carrera et Turbo pour comparer encombrement et masse entre acier generique, Inconel 751 et Ti-6Al-4V sans conclure a une aptitude moteur.

Fiche du catalogue : [`catalog/parts/993-eng-exhaust-valve-f1-0001.json`](../../catalog/parts/993-eng-exhaust-valve-f1-0001.json)

## Identité

| champ | valeur |
|---|---|
| identifiant | 993-ENG-EXHAUST-VALVE-F1-0001 |
| génération | 993 |
| variantes | 993_Carrera, 993_Turbo |
| années | 1994 à 1998 |
| références Porsche | 99310541901, 99310541984, 99310541952, 99310541953 |
| catégorie | engine_valvetrain |
| classe de sécurité | prohibited_pending_engineering |
| usage prévu | Simulation thermique et dynamique preliminaire, masse comparative et controle d'encombrement uniquement |

## Matière et fabrication

| champ | valeur |
|---|---|
| procédé préféré | CNC |
| procédés candidats | CNC, LPBF, DMLS |
| famille de matière | nickel alloy reference |
| nuance | INCONEL 751 / UNS N07751 candidate |
| norme | manufacturer bulletin; application-specific qualification required |
| exigences fournisseur | material heat and lot certificates, process route, dimensional and NDT reports, hot fatigue and oxidation validation, professional engineering release |
| post-traitement | precipitation treatment per qualified route, finish machining, stem, seat, groove and tip finishing, coating or hard-facing decision after tribology review |

**Titane**

| champ | valeur |
|---|---|
| alliage | Ti-6Al-4V retained only as a deliberately challenged comparison for exhaust service |
| traitement thermique | not selected |
| HIP | to_be_determined |
| surfaces usinées | stem, seat face, tip, keeper groove |
| inspection | CT, metallography, surface roughness, dimensional inspection, hot fatigue, oxidation and wear testing |
| isolation galvanique | seat, guide, retainer and coating compatibility must be reviewed |
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

- [`parts/993-eng-exhaust-valve-f1-0001/derived/993-carrera-exhaust-42_5-f1.step`](../../parts/993-eng-exhaust-valve-f1-0001/derived/993-carrera-exhaust-42_5-f1.step)
- [`parts/993-eng-exhaust-valve-f1-0001/derived/993-turbo-exhaust-43_5-f1.step`](../../parts/993-eng-exhaust-valve-f1-0001/derived/993-turbo-exhaust-43_5-f1.step)

## Provenance et sources

| champ | valeur |
|---|---|
| licence de la fiche | MIT for code and record; no third-party geometry redistributed |

**Sources**

- [partworks - Dimensions declarees de soupapes d'echappement 993](https://partworks.de/Porsche/993-Ersatzteile_s2)
- [Special Metals - INCONEL alloy 751](https://www.specialmetals.com/documents/technical-bulletins/inconel/inconel-alloy-751.pdf)

## Validation

| champ | valeur |
|---|---|
| statut | concept |
| essais véhicule | non renseigné |
| revu par |  |
| limites | non renseigné |

**Preuves**

- `SRC-PARTWORKS-993-EXHAUST-VALVE-DIMENSIONS` — *absent du dépôt*
- `SRC-SPECIAL-METALS-INCONEL-751` — *absent du dépôt*

---

*Page engendrée depuis la fiche du catalogue par `scripts/render_part_pages.py`, vérifiée par `make check`. Toute correction se fait dans la fiche, pas ici.*
