# Panneaux de carrosserie en carbone — candidats 993 et 964

Etat : **inventaire documentaire**. Aucune piece n'est qualifiee, aucune
geometrie n'existe, rien n'est propose a la fabrication.

## Pourquoi ces pieces-la, et pas la caisse

`ROADMAP.md` place le monocoque composite hors perimetre et garde les panneaux de
carrosserie comme objectif legitime. La ligne n'est pas arbitraire : elle passe
entre ce qui porte et ce qui habille. `SRC-GUNTHER-WERKS-CARBON-993` la trace
mot pour mot chez le restomod de 993 le plus pousse du marche — « beneath the
carbon fiber, only the structural components and door crash bars remain steel » —
pour un gain annonce de **91 kg** sur les panneaux, caisse acier conservee,
inspectee et renforcee.

Les candidats sont donc les panneaux **boulonnes**, ceux qui se deposent sans
toucher a la structure autoportante. Le catalogue d'usine les designe, et c'est
la premiere chose qu'il sert a etablir.

## Ce que les catalogues d'usine donnent

| generation | catalogue | fiche |
|---|---|---|
| 993 | PET Kat 017, 674 pages, anglais | `SRC-PET-993-KAT17-PDF` |
| 964 | PET Kat 013, 794 pages, allemand | `SRC-PET-964-KAT013-PDF` |

Les deux sont detenus localement par le porteur du projet et leur texte est
extractible : les numeros de piece se relevent sans OCR. Ce depot n'en importe ni
illustration ni extrait ; il n'en conserve que les numeros, qui sont des faits
d'identification.

**Et ce qu'ils ne donnent pas.** Ni cote, ni masse, ni matiere, ni epaisseur. Un
catalogue de pieces etablit l'identite d'une piece et sa place dans un
assemblage. Il ne fonde aucune conception.

### Panneaux boulonnes — 993 (1994-1998)

| panneau | numero | variantes relevees |
|---|---|---|
| Aile avant gauche | 993 503 031 00 | `02` Turbo, `04` Carrera RS |
| Aile avant droite | 993 503 032 00 | `06` a partir de 96, `02`/`08` Turbo, `04` RS |
| Capot avant | 993 511 010 01 | `31` Carrera RS |
| Capot moteur | 993 512 010 00 | — |
| Becquet arriere | 993 512 317 00 | 993 512 511 00 Turbo ; 993 512 119 00/01/02 RS M470/M471 |
| Porte nue gauche | 993 531 005 00 | `01`/`02`/`03` selon conduite et millesime |
| Porte nue droite | 993 531 006 00 | idem |
| Habillage de pare-chocs avant | 993 505 311 00 | `01` version USA |
| Habillage de pare-chocs arriere | 993 505 411 00 | `01` USA, `02`/`03` Turbo |

### Panneaux boulonnes — 964 (1989-1994)

| panneau | numero | variantes relevees |
|---|---|---|
| Aile avant gauche / droite | 964 503 031 02 / 964 503 032 02 | `04` Carrera RS ; 965 503 031/032 `02` et `04` Turbo |
| Capot avant | 964 511 010 00 | Carrera 2/4 |
| Capot moteur | 964 512 010 01 | `02` Carrera RS ; 965 512 010 01 Turbo |
| Becquet arriere | 964 512 017 00 | — |
| Porte nue gauche / droite | 964 531 005 00 / 964 531 006 00 | `03` conduite a droite, `10`/`11` Speedster |
| Habillage de pare-chocs avant | 964 505 113 00 | `01` Carrera 2/4, 965 505 113 01 Turbo |

**Le toit n'y est pas, et c'est voulu.** `993 503 087 00`, *outer roof panel*, est
un panneau **soude**. Le remplacer n'est pas un echange de piece, c'est une
intervention sur la structure — celle que `ROADMAP.md` exclut, et dont l'etude
FEA du 964 montre precisement qu'elle change le mecanisme porteur des que l'on
touche a un anneau ferme.

## Ce que ces panneaux pesent

Une seule source du depot publie des masses par panneau :
`SRC-FEDERLEICHTE-ELFER-993-WEIGHTS`, table comparative d'un preparateur, masse
d'origine contre masse allegee par matiere.

| panneau | origine | carbone | gain | gain par vehicule |
|---|---|---|---|---|
| Aile avant | 7,2 kg | 2,2 kg | -5,0 kg | **-10,0 kg** (x2) |
| Capot avant | 14,0 kg | 4,1 kg | **-9,9 kg** | -9,9 kg |
| Becquet arriere | 12,5 kg | 4,8 kg | -7,7 kg | -7,7 kg |
| Pare-chocs arriere | 5,05 kg | 3,1 kg | -1,95 kg | -1,95 kg |
| Bandeau de feux | 1,26 kg | 0,26 kg | -1,0 kg | -1,0 kg |
| Retroviseurs (paire) | 1,8 kg | 0,25 kg | -1,55 kg | -1,55 kg |

Somme des lignes ci-dessus : **environ 32 kg**. Gunther Werks annonce 91 kg en
remplacant en plus les portes, le toit et les ailes arriere, ce que cette table ne
couvre pas : les deux chiffres sont coherents entre eux.

**Statut de ces masses.** Ce sont des valeurs **declarees par un vendeur**, ni
mesurees par ce depot, ni tracees a une balance, ni assorties d'une tolerance.
Elles servent a classer des candidats, pas a calculer un gain. Les 14,0 kg du
capot avant meritent en particulier d'etre repeses : c'est la valeur la plus
elevee de la table et celle qui commande le classement.

Le seul catalogue commercial qui publie une masse sur chaque fiche produit,
`SRC-ROSEPASSION-993-PARTS`, est **ferme aux agents automatiques** par son
robots.txt. Il ne sera pas interroge par un outil de ce depot ; voir
`docs/decisions/0003-no-vendor-harvesting.md`.

## Ce qui manque, et c'est la meme chose pour tous

Aucun de ces panneaux n'a, dans ce depot :

- de **geometrie**. Aucune CAO, aucun scan. `SRC-SCHONER-993-GT2-LIDAR` revendique
  un scan LiDAR de 993 mais ne publie ni fichier, ni echelle, ni licence : c'est
  une revendication de projet, pas une donnee ;
- de **masse mesuree**, ni de matiere et d'epaisseur d'origine sourcees ;
- d'**interface** : points de fixation, jeux de style, tolerances de montage.

Un panneau de carrosserie se juge d'abord sur ses jeux, et un jeu se mesure. Rien
de ce qui precede ne peut donc franchir les portes de `docs/QUALITY_GATES.md` en
l'etat.

## Le candidat a attaquer en premier

**L'aile avant.** Elle est le meilleur compromis des trois criteres :

- **boulonnee**, deposable sans toucher a la structure, et sans fonction de
  retenue ni d'absorption de choc — contrairement aux habillages de pare-chocs ;
- **10 kg par vehicule**, le plus gros gain de la table, a egalite avec le capot
  mais reparti sur deux pieces plus petites, donc plus faciles a mesurer et a
  mouler ;
- **symetrique** : la gauche valide la droite, ce qui divise par deux le travail
  de qualification geometrique.

Le capot avant vient ensuite, avec une reserve : ses 14,0 kg sont a confirmer
avant d'en faire le premier argument.

## Ce que ce document n'autorise pas

Il n'autorise ni fabrication, ni publication au catalogue, ni annonce de gain de
masse. Il etablit une liste de candidats identifies par leur numero d'usine et
classes par un ordre de grandeur declare. La prochaine etape n'est pas de la CAO :
c'est **une balance et un pied a coulisse sur une aile reelle**, plus la matiere
et l'epaisseur d'origine. Sans quoi le gain annonce reste celui d'un vendeur.
