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
