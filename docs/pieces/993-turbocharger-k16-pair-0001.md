<!-- engendre par scripts/render_part_pages.py - ne pas editer a la main -->

# Paire de turbocompresseurs K16 de 993 Turbo

**Statut : **interdit en l'état**. Aucune pièce n'est libérée ; voir [SAFETY.md](../../SAFETY.md).**

Cible de recherche du jumeau numerique : deux turbocompresseurs K16 montes en parallele sur la 993 Turbo. Cette fiche etablit l'identite fonctionnelle et les donnees publiques disponibles ; elle ne constitue ni une geometrie de remplacement ni une autorisation de fabrication.

Fiche du catalogue : [`catalog/parts/993-turbocharger-k16-pair-0001.json`](../../catalog/parts/993-turbocharger-k16-pair-0001.json)

## Identité

| champ | valeur |
|---|---|
| identifiant | 993-TURBOCHARGER-K16-PAIR-0001 |
| génération | 993 |
| variantes | 993_Turbo |
| années | 1995 à 1998 |
| références Porsche | 993 123 013 51, 993 123 013 52, 993 123 014 51, 993 123 014 52 |
| catégorie | turbocharger |
| classe de sécurité | prohibited_pending_engineering |
| usage prévu | Recherche, identification, simulation et reconstruction dimensionnelle sous controle d'ingenierie ; aucune utilisation moteur ou routiere a ce stade |

## Matière et fabrication

| champ | valeur |
|---|---|
| procédé préféré | à décider |
| procédés candidats | LPBF, CNC, casting |
| famille de matière | inconnue par sous-ensemble ; a identifier sur pieces et documentation fabricant |
| nuance | non determine |
| norme | aucun |
| exigences fournisseur | Qualification du procede et traçabilite de lot, Dossier thermique, fatigue, rotordynamique et pression, Rapport de metrologie et de controle non destructif, Equilibrage haute vitesse par operateur qualifie, Revue d'ingenierie formelle avant tout essai moteur |
| post-traitement | a definir apres geometrie et materiau, usinage des interfaces et portees, equilibrage de l'ensemble tournant si un rotor est etudie, controle dimensionnel et non destructif |

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

- [`parts/993-turbocharger-k16-pair-0001/derived/k16_pair_concept_f0.step`](../../parts/993-turbocharger-k16-pair-0001/derived/k16_pair_concept_f0.step)

## Provenance et sources

| champ | valeur |
|---|---|
| licence de la fiche | MIT for the record, no third-party geometry redistributed |

**Sources**

- [Porsche Christophorus - Donnees techniques du 911 Turbo (993)](https://newsroom.porsche.com/christophorus/fr/2020/394/turbo-engines.html)
- [BorgWarner - Performance Turbocharger Catalog](https://www.borgwarner.com/docs/default-source/iam/boosting-technologies/bw_turbo-performance-catalog.pdf)
- [FVD Brombacher - encombrement et masse des K16 993](https://www.fvd.net/de/shop/turbolader-k16-rechts-993-serie-99312301452-993123014dx~p239094)
- [Invasion Auto Products - donnees catalogue internes du K16 droit](https://www.invasionautoproducts.com/94pocark16tu.html)
- [Design911 - Cross-reference des turbocompresseurs K16 de 993 Turbo](https://www.design911.co.uk/b/borgwarner/2/)
- [TurboMaster - Eclate de pieces du BorgWarner K16 5316-988-6735](https://www.turbomaster.com/eng/turbo/borgwarner/5316-988-6735/)
- [Porsche Fanatics - releve PET des groupes turbo 993](https://porschefanatics.com/oem/993/202-16/)
- [Porsche Austria - PET 993, groupe 107-45 echangeur d'air](https://www.porsche.at/media/Kwc_Basic_DownloadTag_Component/4740-45397-124814-downloadTag/default/f5000535/1729608718/kat017-d-911-98-katalog.pdf)

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
