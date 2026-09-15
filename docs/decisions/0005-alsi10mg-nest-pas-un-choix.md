# 0005 — L'AlSi10Mg de la bague n'a jamais été choisi

Date : 2026-09-11

## Décision

Cesser de présenter `AlSi10Mg` comme la matière de la bague de commodo
`993-INT-SWITCH-TRIM-RING-F1-0001`. Elle est **héritée**, pas sélectionnée.
Rouvrir la question matière et la question procédé ensemble, avant d'envoyer
quoi que ce soit à un prestataire.

## Ce qui a réellement décidé

L'AlSi10Mg est la seule nuance pour laquelle le dépôt possède une carte
matière-machine-procédé
([`eos-m290-alsi10mg-30um.json`](../../catalog/manufacturing/processes/eos-m290-alsi10mg-30um.json)).
La bague est par ailleurs la seule pièce `non_critical` du catalogue à porter
LPBF parmi ses procédés candidats — les deux autres pièces non critiques sont en
polymère. Le pilote métal est donc issu d'une double élimination, sur la sécurité
d'un côté et sur la documentation disponible de l'autre. À aucun moment un
critère de fonction n'est intervenu.

## Les trois raisons de rouvrir

**1. Le critère qui gouverne cette pièce est l'aspect, pas la tenue.** Une bague
de finition de tableau de bord ne porte rien. Le criblage de l'étape 04 le montre
sans le dire : la seule porte mécanique, la paroi minimale, passe très largement,
et aucun cas de charge n'existe. Ce qui décide ici est l'état de surface, la
brillance et l'accord avec l'habillage voisin.

**2. L'AlSi10Mg est mauvais précisément à l'opération dont la pièce a besoin.**
Sa teneur en silicium de 9 à 11 % le rend impropre à l'anodisation décorative :
le silicium n'étant pas soluble dans l'aluminium, seules les zones pauvres en
silicium s'anodisent et la pièce ressort gris-brun à noire
(`SRC-FEHRMANN-ALMGTY-ANODISING-ALSI10MG-LIMIT`). Or l'anodisation figure
explicitement dans les post-traitements prévus de la fiche. À quoi s'ajoute un
Ra brut de 12 à 25 µm annoncé par le prestataire candidat, sur une pièce visible.
Les nuances corroyées 6xxx font l'inverse : le 6063 T6 est donné excellent en
anodisation brillante (`SRC-1STCHOICEMETALS-6XXX-BRIGHT-ANODISING`), et c'est
très probablement ce qu'est la bague d'origine, décrite comme « aluminium » sans
autre précision par le vendeur.

**3. La grille du dépôt exclut déjà cette pièce de l'additif.**
[`TITANIUM.md`](../TITANIUM.md) retient trois familles où la fabrication additive
gagne : les passages internes inusinables, les fonderies impossibles à noyauter,
et la consolidation de sous-ensembles. Un anneau axisymétrique de 6 g n'est
aucune des trois. Sa propre fiche catalogue le dit depuis le début : « la
géométrie axisymétrique favorise probablement le tournage CNC ; l'intérêt LPBF
reste à démontrer ».

## Conséquence

La question matière et la question procédé n'en font qu'une. Pour cette pièce,
la réponse probable est **une barre de 6xxx tournée puis anodisée brillant**, et
non un frittage laser d'alliage de fonderie. Le devis reste utile — il a été
demandé pour savoir ce qu'un prestataire chinois accepte d'écrire, pas pour
obtenir la bague — mais il doit désormais porter les deux voies et être jugé sur
la comparaison, pas sur le prix du LPBF seul.

## Limite acceptée

Le dépôt ne possède aucune carte matière 6xxx, aucune mesure de la bague
d'origine et aucune identification de sa nuance réelle. La phrase « c'est
probablement du 6063 anodisé brillant » est une hypothèse de niveau B, pas une
identification. Elle ne devient une décision qu'après mesure d'un exemplaire.

## Ce que cela ouvre

Si l'objectif est d'imprimer du métal parce que l'additif est la bonne réponse,
et non parce que la pièce était la moins risquée, alors le choix doit se faire
dans les trois familles de `TITANIUM.md`. Les candidats du catalogue qui y
appartiennent réellement — conduits internes, boîtes à eau, collecteurs — sont
aujourd'hui tous classés `functional` ou
`prohibited_pending_engineering`. Choisir l'un d'eux signifie accepter un
chemin d'ingénierie, pas un pilote de chaîne numérique. C'est un arbitrage à
poser explicitement, pas à contourner en reprenant la pièce la plus inoffensive.
