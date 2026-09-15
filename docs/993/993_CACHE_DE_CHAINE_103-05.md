# Carter de chaîne, planche 103-05 — bon candidat additif, en aluminium

Troisième pièce instruite après l'embout et le circuit d'huile de turbo. Le
verdict suit le même schéma, et c'est ce qui le rend intéressant : la question
du procédé et la question de la matière ne se répondent pas ensemble.

## Ce que la planche établit

| position | références | désignation |
|---|---|---|
| 1, 5 | `993 105 093 05`, `964 105 094 04` | `chain case` |
| 11, 15, 19 | `993 105 022 01`, `964 105 107 01`, `964 105 108 01` | `lid` |
| 9, 10 | `964 105 079 00`, `964 105 080 00` | `chain adjuster` |
| 21, 27, 28 | `993 107 088 00`, `993 107 087 51`, `993 107 088 52` | `bridge`, **aussi décrits `oil gallery`** |
| 23 | `964 105 110 01` | `bearing` |
| 24 | `993 106 253 06` | `heat protection plate` |

Le détail qui compte est la double désignation des positions 27 et 28 : **pont
et galerie d'huile à la fois**. Un carter, ses couvercles, un palier, un tendeur
et des galeries d'huile rapportées sur une même planche, cela décrit un
sous-ensemble que la fabrication additive consolide naturellement.

Et la tôle de protection thermique en position 24 dit le reste du contexte :
cette pièce a des voisins chauds.

## Pourquoi c'est un vrai candidat additif

Consolidation et passages internes, deux des trois familles de `TITANIUM.md`.
Les galeries d'huile d'un carter de distribution sont exactement le genre de
volume qu'une fonderie noyaute mal et qu'un usinage atteint par des perçages
croisés rebouchés ensuite. En additif, elles se dessinent directement.

Le criblage lui donne un score brut de **+4**.

## Pourquoi le titane y est refusé

Deux motifs, après examen — et pas ceux qu'on croit.

**Le grippage et le couple galvanique ne suffisent pas à refuser.** Le carter se
dépose à l'entretien et se boulonne sur de l'aluminium, c'est vrai. Mais des
inserts acier dans les portées de goujons traitent le premier, un revêtement et
un mastic d'étanchéité traitent le second. Ce sont des parades connues. La grille
dit d'ailleurs « contact glissant **non traité** » et « couple galvanique **non
maîtrisé** », et `SAFETY.md` inscrit leur prévention parmi les exigences
minimales du métal : ce sont des travaux à faire, pas des motifs d'abandon.

**La dilatation différentielle, elle, reste sans parade.** Le carter se boulonne
sur le carter moteur en aluminium, sur un plan de joint étendu. Le titane se
dilate à peu près deux fois moins. À température d'huile, un assemblage long
entre deux matières aussi éloignées travaille son joint et ses fixations. Je n'ai
pas de conception de plan de joint à proposer qui reprenne cela, et tant que je
n'en ai pas, la condition bloque.

**Et surtout, le titane n'améliore pas la matière d'origine.** Une fonte
d'aluminium boulonnée sur un carter d'aluminium : le titane y perd sur la
dilatation, sur le couple galvanique et sur le prix, sans rien apporter en
température ni en corrosion. C'est le motif le plus simple, et c'est celui que le
criblage ne savait pas formuler avant cette pièce.

## Les deux corrections que cette pièce a provoquées

**Première correction, dans le mauvais sens.** Le criblage ne traitait que deux
des cinq contre-indications comme des refus. J'ai rendu les cinq rédhibitoires —
et j'ai supprimé au passage les mots « non traité » et « non maîtrisé » que la
grille contient. Les pièces éligibles sont tombées de 5 à 1, pour une mauvaise
raison.

**Seconde correction, la bonne.** Une contre-indication est une **condition à
lever**. Elle bloque tant qu'aucune parade n'est déclarée ; une parade déclarée
la transforme en exigence portée à la route, que le fournisseur devra tenir. Et
il manquait la question que la grille pose pourtant explicitement — « corrosion
problématique **avec la matière d'origine** » : **le titane bat-il l'incumbent ?**
Sans elle, le criblage notait des mots au lieu de comparer des métaux, et
classait premier un collecteur d'admission en aluminium tiède.

## Verdict

`prohibited_pending_engineering`, et pas seulement pour des raisons de données :
le carter porte la distribution et de l'huile sous pression, sa rupture peut
coûter le moteur, et la planche elle-même signale un voisinage chaud.

Si ce sous-ensemble est un jour refabriqué en additif — et il le mérite — ce sera
**en aluminium**, qui accompagne la dilatation du carter moteur et supprime le
couple galvanique. Pas en titane.

C'est la troisième fois de suite que l'instruction sépare les deux questions.
Cela commence à ressembler à une règle, et elle est maintenant écrite dans
[`SAFETY.md`](../../SAFETY.md) : le procédé et la matière sont deux jugements
indépendants, rendus séparément.

## Ce que ce criblage ne dit pas

Il porte sur les 33 fiches de `catalog/parts`, pas sur la voiture. Le catalogue
d'usine 993 compte **6 259 références distinctes** ; les fiches en couvrent une
fraction de pourcent. « Une seule pièce éligible » est donc une phrase sur l'état
du dépôt, jamais sur l'automobile. Le balayage large est le triage PET, qui
retient 70 désignations dont trois seulement ont été instruites à ce jour.
