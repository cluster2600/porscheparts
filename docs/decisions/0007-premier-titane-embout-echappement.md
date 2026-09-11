# 0007 — Le premier titane sera l'embout d'échappement, et une mesure décide de l'alliage

Date : 2026-09-11

## Décision

Retenir `993-EXH-OVAL-TIP-TI-F1-0001` comme première pièce titane du dépôt.
**Ne pas fixer l'alliage.** Le Ti-6Al-4V et le Ti-6242 sont tous deux criblés ;
ce qui les sépare est une température de 427 °C qui n'a jamais été mesurée.

## Comment la pièce a été choisie

Pas par élimination — c'est l'erreur que [0005](0005-alsi10mg-nest-pas-un-choix.md)
a corrigée. La grille écrite de [`TITANIUM.md`](../TITANIUM.md) et les trois
familles où l'additif gagne ont été appliquées **aux 32 fiches du catalogue** par
`scripts/screen_titanium_candidates.py`. Les jugements d'entrée sont déclarés
comme tels dans `catalog/manufacturing/titanium-am-screen-inputs.json` :
contredire une case change le rang, et c'est voulu.

| rang | pièce | score | verdict |
|---|---|---:|---|
| 1 | **embout ovale, variante titane** | **+6** | retenue |
| 2 | collecteur d'admission trois conduits | +5 | l'aluminium y reste la bonne matière |
| — | collecteur d'échappement | +7 | meilleur score du lot, **900 °C : cas nickel** |

Cinq pièces seulement sont éligibles sur trente-deux. Vingt-sept tombent sur la
classe de sécurité, l'absence de famille additive, la température, le besoin de
conduire la chaleur ou l'obligation de garder une raideur acier.

L'embout gagne parce que tout converge : consolidation du conduit, de la coque
et des huit nervures en un seul corps, cavité annulaire qu'aucun usinage ne
produit, petite série, rupture bénigne, et **une seule interface à mesurer** —
le diamètre de la sortie. Le précédent existe au plus haut niveau : APWorks
imprime en titane la sortie d'échappement de la Bugatti Chiron Pur Sport.

## Ce que le criblage a trouvé et que personne n'aurait deviné

Ma première estimation de température était 300 °C. La fiche F0 de la pièce
déclare une surface à **700 K, soit 427 °C**. C'est le chiffre du dépôt qui a
été retenu, pas le mien — et il renverse la réponse.

| | Ti-6Al-4V | Ti-6242 |
|---|---|---|
| masse de criblage | **212,3 g** contre 406,4 g en IN625, soit **−47,7 %** | 217,6 g |
| plafond de fluage | 400 °C | 550 °C |
| marge à 427 °C | **−27 °C** | +123 °C |
| épaisseur de couche publiée | 30 µm | aucune |
| paroi minimale publiée | 0,3 à 0,4 mm | aucune |
| traitement thermique publié | 800 °C 2 h sous argon | aucun |
| disponible chez un atelier de service | **oui, partout** | **non** |
| portes fermées à l'étape 04 | 6 | 10 |

Les deux routes s'excluent proprement. Le Ti-6Al-4V est une route réelle,
disponible, documentée, bloquée par **un seul chiffre**. Le Ti-6242 règle ce
chiffre et perd tout le reste : pas de machine, pas d'épaisseur de couche, pas
de fournisseur. Sa première mise en œuvre LPBF publiée date de 2020 ; c'est un
sujet de recherche, pas un article de catalogue.

## Ce qui décide donc

Un thermomètre infrarouge sur la sortie d'échappement, après roulage.

Les 427 °C viennent d'un cas synthétique : gaz à 850 K, moteur 3,8 L à
6 500 tr/min, deux sorties, aucune mesure. Un embout réel, en aval du
silencieux, peut très bien fonctionner cent degrés plus bas. Si la mesure donne
350 °C ou moins, le Ti-6Al-4V passe et la pièce devient commandable chez
n'importe quel atelier titane. Si elle confirme 427 °C, la pièce n'est pas
imprimable en titane à un coût raisonnable, et la réponse redevient l'IN625 —
deux fois plus lourd, mais achetable.

Aucun calcul de ce dépôt ne remplacera cette mesure.

## Où en est la chaîne

| étape | statut |
|---|---|
| 01 — autorité géométrique | `completed_screening` |
| 02 — BREP et maillage | **`passed`** — étanche, monocomposant, 13 820 triangles |
| 03 — tranchage et supports | `completed_screening` — 4 936 couches à 30 µm |
| 04 — carte matière-machine-procédé | `blocked_missing_input` |

## Limites acceptées

- La température qui décide n'est pas mesurée.
- Seule l'enveloppe de sortie 120 × 85 mm est publiée ; longueur, interface
  d'entrée et profondeur d'emmanchement sont des hypothèses F0.
- Le dépoudrage du canal annulaire de 2,7 mm n'est vérifié qu'au criblage voxel
  de 1 mm. Cette résolution ne conclut pas : il faut une endoscopie ou une
  tomographie.
- Deux nouveaux îlots et 1 044 couches à aire non soutenue appellent des
  supports, dont aucun n'est dessiné.
- Le couple galvanique titane/inox à la fixation reste à traiter.

---

## Addendum du 11 septembre 2026 — le périmètre était faux

La décision ci-dessus dit « les 32 fiches du catalogue ». C'est exact, et c'est
insuffisant : le catalogue d'usine 993 compte **6 259 références distinctes**.
Les fiches du dépôt en couvrent **0,51 %**. Écrire « appliquée au catalogue »
laissait croire à une exhaustivité qui n'existait pas.

Deux triages ont été ajoutés pour réparer cela.

**Triage de zones** — `scripts/screen_pet_zones_for_titanium.py`, sur les seules
données du dépôt : 239 illustrations, 499 libellés, 23 zones retenues couvrant
1 538 références. Tourne partout, y compris en intégration.

**Triage pièce à pièce** — `scripts/screen_pet_parts_for_titanium.py`, sur le
relevé de désignations tenu **hors du dépôt**, comme `twin_structure.py` :
1 026 désignations distinctes, 70 retenues, couvrant 439 références. Seules les
conclusions agrégées et une liste courte sont publiées ; les lignes du catalogue
restent chez leur détenteur.

### Ce que le triage élargi trouve

| score | réf. | désignation | lecture |
|---:|---:|---|---|
| +5 | 12 | `heat exchanger` | échangeur de chauffage 993 — **température d'échappement, cas nickel** |
| +5 | 5 | `hot-air manifold` | air chaud, pas gaz ; l'aluminium suffit |
| +4 | **21** | **`tail pipe`** | **la pièce retenue, reconfirmée indépendamment** |
| +4 | 4 | `turbocharger` | interdit en l'état |
| +2 | 21 | `oil pipe` | conduites d'huile de turbo, vrai cas additif, mais fuite d'huile sur échappement |

**La conclusion ne change pas, mais elle est maintenant défendable.** L'embout
sort dans les quatre premiers d'un triage portant sur toute la voiture, et non
plus d'un panier de trente-deux fiches choisies. Les deux désignations qui le
devancent tombent sur la même barrière que le collecteur : la température
d'échappement est un domaine nickel, pas titane.

### Ce que ces triages ne sont pas

Un triage lexical retient des mots, pas des fonctions. Une désignation de trois
mots ne dit ni la matière, ni la masse, ni la température. Une entrée retenue
n'est pas une pièce choisie : c'est une pièce **à aller regarder**, en ouvrant
la ligne PET, puis en la faisant passer par `screen_titanium_candidates.py` avec
un jugement déclaré.

La règle de correction du groupe mérite d'être notée. La première version
excluait une désignation dès qu'une seule de ses planches touchait un organe
présumé critique ; `oil pipe`, qui apparaît une fois sur une planche de carter,
disparaissait ainsi alors que c'est un des meilleurs candidats du lot. Le groupe
n'exclut désormais que s'il accuse **toutes** les planches de la désignation.

---

## Addendum du 11 septembre 2026 (2) — la grille était appliquée trop mollement

L'instruction du carter de chaîne a montré que le criblage ne traitait que deux
des cinq contre-indications de `TITANIUM.md` comme des refus. Les trois autres —
forme simple usinable, grippage sur filetage repris, couple galvanique — n'étaient
que des malus au score. « Quand le titane n'est pas pertinent » énonce pourtant
des refus.

Les cinq sont désormais rédhibitoires, et le classement change de nature :

| | avant | après |
|---|---:|---:|
| pièces éligibles sur 33 | 5 | **1** |

L'embout d'échappement n'est plus le meilleur d'un lot. Il est **le seul candidat
titane du catalogue**. Le collecteur d'admission tombe sur le couple galvanique
avec l'aluminium, le crochet de phare et le levier de porte sur la forme simple,
le cache-moyeu sur les deux.

Cela renforce la décision plutôt que de la fragiliser, mais il faut le dire dans
ce sens : ce n'est pas que l'embout ait gagné, c'est que tous les autres
perdaient déjà et que le criblage ne le disait pas.
