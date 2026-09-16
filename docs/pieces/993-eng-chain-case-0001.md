<!-- engendre par scripts/render_part_pages.py - ne pas editer a la main -->

# Carter de chaîne de distribution 993 et ses couvercles

**Statut : **interdit en l'état**. Aucune pièce n'est libérée ; voir [SAFETY.md](../../SAFETY.md).**

Cible d'instruction : le carter de chaîne de la planche d'usine 103-05, ses trois couvercles, ses ponts d'huile et son tendeur. La fiche établit l'identité et le raisonnement matière ; elle ne constitue ni une géométrie de remplacement, ni une autorisation de fabrication. Retenue parce que le triage du catalogue d'usine en fait un cas de consolidation sérieux — et parce que la grille titane le refuse trois fois.

Fiche du catalogue : [`catalog/parts/993-eng-chain-case-0001.json`](../../catalog/parts/993-eng-chain-case-0001.json)

## Identité

| champ | valeur |
|---|---|
| identifiant | 993-ENG-CHAIN-CASE-0001 |
| génération | 993 |
| variantes | 993_tous_modeles_a_confirmer_par_variante |
| années | 1994 à 1998 |
| références Porsche | 993 105 093 05, 964 105 094 04, 993 105 022 01, 964 105 107 01, 964 105 108 01, 993 107 087 51, 993 107 088 52, 993 107 088 00 |
| catégorie | engine_timing_chain_case |
| classe de sécurité | prohibited_pending_engineering |
| usage prévu | Instruction documentaire et comparaison de procédés ; aucune fabrication, aucun montage, aucune mise en route |

## Matière et fabrication

| champ | valeur |
|---|---|
| procédé préféré | à décider |
| procédés candidats | casting, LPBF, CNC |
| famille de matière | aluminium, par cohérence avec le carter moteur |
| nuance | non identifié ; l'origine est une pièce de fonderie dont la nuance n'est pas publiée |
| norme |  |
| exigences fournisseur | non renseigné |
| post-traitement | non renseigné |

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

- [`parts/993-eng-chain-case-0001/derived/chain_case_concept_f0.step`](../../parts/993-eng-chain-case-0001/derived/chain_case_concept_f0.step)

## Provenance et sources

| champ | valeur |
|---|---|
| licence de la fiche | MIT pour la fiche ; aucune géométrie tierce redistribuée |

**Sources**

- [Catalogue d'usine 993, planche 103-05 Chain case](https://porschefanatics.com/oem/993/103-05/)

## Validation

| champ | valeur |
|---|---|
| statut | concept |
| essais véhicule | non renseigné |
| revu par |  |
| limites | non renseigné |

**Preuves**

- [`catalog/sources/src-pet-993-103-05-chain-case.json`](../../catalog/sources/src-pet-993-103-05-chain-case.json)
- [`docs/993/993_CACHE_DE_CHAINE_103-05.md`](../../docs/993/993_CACHE_DE_CHAINE_103-05.md)

---

*Page engendrée depuis la fiche du catalogue par `scripts/render_part_pages.py`, vérifiée par `make check`. Toute correction se fait dans la fiche, pas ici.*
