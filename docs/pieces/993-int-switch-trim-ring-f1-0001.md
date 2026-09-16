<!-- engendre par scripts/render_part_pages.py - ne pas editer a la main -->

# Bague aluminium de finition de commutateur, reconstruction F1

**Statut : non critique. Aucune pièce n'est libérée ; voir [SAFETY.md](../../SAFETY.md).**

Bague de finition de commutateur, reconstruction F1. Le pilote a servi à valider la chaîne CAO, le criblage LPBF et la confrontation à une route réelle ; cette dernière a conclu que la pièce doit être tournée dans une nuance 6xxx et non frittée. Ce n'est ni une géométrie OEM ni une pièce autorisée au montage.

Fiche du catalogue : [`catalog/parts/993-int-switch-trim-ring-f1-0001.json`](../../catalog/parts/993-int-switch-trim-ring-f1-0001.json)

## Identité

| champ | valeur |
|---|---|
| identifiant | 993-INT-SWITCH-TRIM-RING-F1-0001 |
| génération | 993 |
| variantes | 993_tous_modeles_selon_fournisseur_a_confirmer |
| années | 1994 à 1998 |
| références Porsche | non renseigné |
| catégorie | interior_trim |
| classe de sécurité | non_critical |
| usage prévu | Pilote de reconstruction et de comparaison LPBF/CNC, sans montage véhicule à ce stade |

## Matière et fabrication

| champ | valeur |
|---|---|
| procédé préféré | CNC |
| procédés candidats | LPBF, CNC |
| famille de matière | aluminium corroyé série 6000 |
| nuance | EN AW-6063 T6 retenu pour l'anodisation brillante ; EN AW-6061 T6 en repli si le tourneur refuse |
| norme | EN 755-2 pour la barre ; nuance d'origine toujours non identifiée |
| exigences fournisseur | Certificat matière et état métallurgique de la barre, Tolérance réellement tenue sur le diamètre extérieur, Épaisseur d'anodisation obtenue et sa dispersion, Chiffrage du 6061 T6 en regard, avec ce que l'aspect y perd, Contrôle dimensionnel des quatre cotes et du profil axial |
| post-traitement | tournage de finition, Ra cible 0,8 µm sur les faces visibles, chanfreins ou rayons d'arête à décider puis à porter au modèle, anodisation sulfurique décorative incolore, croissance de couche à retrancher de la cote d'ajustement |

## Géométrie

| champ | valeur |
|---|---|
| type de source | estimated |
| format du maître | build123d |
| unités | mm |
| précision (mm) | non renseigné |

**Fichier maître**

- [`parts/993-int-switch-trim-ring-f1-0001/source/switch_trim_ring.py`](../../parts/993-int-switch-trim-ring-f1-0001/source/switch_trim_ring.py)

**Fichiers dérivés**

- [`parts/993-int-switch-trim-ring-f1-0001/derived/switch_trim_ring_f1.step`](../../parts/993-int-switch-trim-ring-f1-0001/derived/switch_trim_ring_f1.step)
- [`parts/993-int-switch-trim-ring-f1-0001/derived/switch_trim_ring_f1.stl`](../../parts/993-int-switch-trim-ring-f1-0001/derived/switch_trim_ring_f1.stl)

## Provenance et sources

| champ | valeur |
|---|---|
| licence de la fiche | MIT pour le script et la fiche ; aucun média ou modèle tiers redistribué |

**Sources**

- [Oldtimer-Ersatzteile24 - Bague de finition de commutateur 911/964/993](https://oldtimer-ersatzteile24.de/alu-zierring-decorring-fuer-porsche-911-964-993-armaturenbrett-eq850101)
- [EOS Aluminium AlSi10Mg material data sheet](https://www.eos.info/metal-solutions/metal-materials/data-sheets/mds-eos-aluminium-alsi10mg)

## Validation

| champ | valeur |
|---|---|
| statut | concept |
| essais véhicule | non renseigné |
| revu par |  |
| limites | non renseigné |

**Preuves**

- [`catalog/sources/src-oldtimer-ersatzteile24-993-switch-ring-dimensions.json`](../../catalog/sources/src-oldtimer-ersatzteile24-993-switch-ring-dimensions.json)
- [`parts/993-int-switch-trim-ring-f1-0001/evidence/geometry-screen.json`](../../parts/993-int-switch-trim-ring-f1-0001/evidence/geometry-screen.json)
- [`twins/993-switch-trim-ring-f1/evidence/turning-f1/993-int-switch-trim-ring-f1-0001-turning-route-card.json`](../../twins/993-switch-trim-ring-f1/evidence/turning-f1/993-int-switch-trim-ring-f1-0001-turning-route-card.json)

## Dossiers de conception

- [993_SOURCING_CHINE_LPBF](../../docs/993/993_SOURCING_CHINE_LPBF.md)
- [993_SWITCH_TRIM_RING_F1](../../docs/993/993_SWITCH_TRIM_RING_F1.md)

---

*Page engendrée depuis la fiche du catalogue par `scripts/render_part_pages.py`, vérifiée par `make check`. Toute correction se fait dans la fiche, pas ici.*
