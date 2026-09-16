<!-- engendre par scripts/render_part_pages.py - ne pas editer a la main -->

# Embout d'échappement ovale, variante titane F1

**Statut : fonctionnel. Aucune pièce n'est libérée ; voir [SAFETY.md](../../SAFETY.md).**

Même géométrie double paroi que la variante IN625 F0, criblée en titane. Retenue par le criblage titane du dépôt comme la seule pièce du catalogue où le titane et la fabrication additive gagnent tous les deux sans buter sur la classe de sécurité. L'alliage n'est volontairement pas fixé dans l'identifiant : le Ti-6Al-4V et le Ti-6242 sont tous deux criblés, et c'est une température jamais mesurée qui les sépare.

Fiche du catalogue : [`catalog/parts/993-exh-oval-tip-ti-f1-0001.json`](../../catalog/parts/993-exh-oval-tip-ti-f1-0001.json)

## Identité

| champ | valeur |
|---|---|
| identifiant | 993-EXH-OVAL-TIP-TI-F1-0001 |
| génération | 993 |
| variantes | 993_C2, 993_C4, 993_RS_narrow_body |
| années | 1994 à 1998 |
| références Porsche | non renseigné |
| catégorie | exhaust_tip |
| classe de sécurité | functional |
| usage prévu | Criblage CAO, DfAM, débit, thermique, pression et modal ; aucune fabrication pour montage ni installation véhicule autorisée |

## Matière et fabrication

| champ | valeur |
|---|---|
| procédé préféré | LPBF |
| procédés candidats | LPBF, DMLS, sheet_metal |
| famille de matière | titane |
| nuance | Ti-6Al-4V si la température réelle le permet ; Ti-6242 sinon, mais sans fournisseur identifié |
| norme | ASTM F2924 pour le Ti-6Al-4V PBF-LB ; AMS 4975/4976 pour le Ti-6242 corroyé |
| exigences fournisseur | Certificat matière, lot de poudre et nombre de réemplois, Orientation et topologie de supports proposées, avec justification, Preuve de dépoudrage du canal annulaire, endoscopie ou tomographie, Traitement thermique et état de livraison documentés, Épaisseur de couche employée et propriétés coupon de cette épaisseur |
| post-traitement | détourage, retrait des supports et reprise des attaches, traitement thermique de détente, 800 °C 2 h sous argon sur la route EOS Ti64, dépoudrage contrôlé du canal annulaire de 2,7 mm, endoscopie exigée, état de surface extérieur à définir, l'embout est visible |

**Titane**

| champ | valeur |
|---|---|
| alliage | Ti-6Al-4V candidat principal, Ti-6242 échappatoire haute température |
| traitement thermique | 800 °C 2 h sous argon pour la route EOS Ti64 ; non fixé pour le Ti-6242 |
| HIP | to_be_determined |
| surfaces usinées | non renseigné |
| inspection | contrôle dimensionnel de l'enveloppe de sortie, endoscopie du canal annulaire |
| isolation galvanique | Couple titane/acier inoxydable à la fixation sur la sortie : à traiter, le titane est noble et l'inox le suit de près, mais l'humidité et le sel de route restent présents. |
| hypothèses de fatigue | non renseigné |

## Géométrie

| champ | valeur |
|---|---|
| type de source | mixed |
| format du maître | build123d |
| unités | mm |
| précision (mm) | non renseigné |

**Fichier maître**

- [`parts/993-exh-oval-tip-in625-f0-0001/source/oval_exhaust_tip.py`](../../parts/993-exh-oval-tip-in625-f0-0001/source/oval_exhaust_tip.py)

**Fichiers dérivés**

- [`parts/993-exh-oval-tip-ti-f1-0001/derived/oval_exhaust_tip_ti_f1.step`](../../parts/993-exh-oval-tip-ti-f1-0001/derived/oval_exhaust_tip_ti_f1.step)
- [`parts/993-exh-oval-tip-ti-f1-0001/derived/oval_exhaust_tip_ti_f1.stl`](../../parts/993-exh-oval-tip-ti-f1-0001/derived/oval_exhaust_tip_ti_f1.stl)

## Provenance et sources

| champ | valeur |
|---|---|
| licence de la fiche | MIT pour le concept, le script et les calculs ; aucune photographie, marque, illustration PET ou géométrie commerciale redistribuée |

**Sources**

- [FVD - embouts inox ovales 993 étroites](https://www.fvd.net/de-de/FVD11199300/endrohrsatz-edelstahl-poliert-oval-schraeg-993-120x85mm.html)
- [PorscheFanatics - registre des matériaux déclarés](https://porschefanatics.com/materials/)
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

- [`twins/993-exhaust-tip-ti-f0/evidence/selection/titanium-candidate-screen.json`](../../twins/993-exhaust-tip-ti-f0/evidence/selection/titanium-candidate-screen.json)
- [`parts/993-exh-oval-tip-ti-f1-0001/evidence/engineering-screen-ti64.json`](../../parts/993-exh-oval-tip-ti-f1-0001/evidence/engineering-screen-ti64.json)
- [`parts/993-exh-oval-tip-ti-f1-0001/evidence/engineering-screen-ti6242.json`](../../parts/993-exh-oval-tip-ti-f1-0001/evidence/engineering-screen-ti6242.json)
- [`twins/993-exhaust-tip-ti-f0/evidence/lpbf-f1/993-exh-oval-tip-ti-f1-0001-lpbf-geometry-report.json`](../../twins/993-exhaust-tip-ti-f0/evidence/lpbf-f1/993-exh-oval-tip-ti-f1-0001-lpbf-geometry-report.json)

## Dossiers de conception

- [993_EMBOUT_TITANE_F1](../../docs/993/993_EMBOUT_TITANE_F1.md)

---

*Page engendrée depuis la fiche du catalogue par `scripts/render_part_pages.py`, vérifiée par `make check`. Toute correction se fait dans la fiche, pas ici.*
