# Couvercle de carter de chaîne `964 105 107 01` en Ti-6Al-4V

Demande explicite. Ce document dit ce qui se calcule sans la pièce, ce qui se
mesure en une heure, et ce qu'il faut envoyer au fraiseur.

## Identité

Planche d'usine `103-05 Chain case`, **position 15**, désignation `lid`.
Trois couvercles cohabitent sur cette planche : `993 105 022 01` en position 11,
**`964 105 107 01` en position 15**, `964 105 108 01` en position 19. Celui-ci est
apparié au joint `964 105 181 01`, position 16 — le couvercle et son joint se
suivent dans la nomenclature.

C'est donc un couvercle boulonné **étanche à l'huile**.

## Deux réserves, dites une fois

**Le titane alourdit la pièce — à géométrie égale.** 4,43 contre 2,70 g/cm³. Sur
les hypothèses du criblage, 122 g en aluminium deviendraient 199 g en titane,
+64 %. Mais l'épaisseur n'a aucune raison de rester égale, et c'est traité en
détail plus bas : le couvercle **peut** être plus mince. De combien, et si cela
suffit à le rendre plus léger, dépend entièrement de ce qui dimensionne
l'épaisseur d'origine.

**Ce n'est pas une pièce à imprimer.** Couvercle plan boulonné : ni passage
interne, ni sous-ensemble à consolider, ni noyau impossible. Aucune des trois
familles où l'additif gagne. Le **fraisage dans une plaque** est plus rapide,
moins cher, et surtout plus précis là où ça compte, sur le plan de joint.

Bonne nouvelle : cela rend la pièce accessible tout de suite, chez n'importe quel
atelier titane.

## Peut-on le faire plus mince ? Oui. Assez pour gagner du poids ? Ça dépend.

Trois critères possibles, trois réponses différentes. Pour une épaisseur
d'origine de 5 mm prise en hypothèse :

| critère retenu | épaisseur titane | masse vs aluminium |
|---|---|---|
| **raideur en flexion égale** — `t_ti/t_al = (E_al/E_ti)^⅓` | 85,0 % → 4,25 mm | **×1,39**, plus lourd |
| **résistance en flexion égale** — `t_ti/t_al = √(σ_al/σ_ti)` | 46,6 % → 2,33 mm | **×0,76**, 24 % plus léger |
| **masse égale** — `t_ti/t_al = ρ_al/ρ_ti` | 60,9 % → 3,05 mm | il ne reste que **37 %** de la raideur |

Le titane est 1,63 fois plus rigide en module et environ 4,6 fois plus résistant
que l'aluminium de fonderie retenu en criblage. C'est pourquoi les deux premières
lignes divergent autant : sur la raideur, le gain est faible parce qu'elle varie
en `t³` et que le rapport de modules est modeste ; sur la résistance, le gain est
franc parce qu'elle varie en `t²` et que l'écart de limite élastique est énorme.

**Et il existe un troisième cas, le plus probable ici.** L'épaisseur d'une pièce
de fonderie n'est souvent dictée ni par la raideur ni par la résistance, mais par
la fonderie elle-même : paroi minimale coulable, dépouille, remplissage. Une
pièce fraisée n'a aucune de ces contraintes. Dans ce cas le titane peut être plus
mince que la fonte **et** rester plus raide qu'il ne faut.

C'est la mesure et l'œil qui trancheront, pas le calcul : une épaisseur uniforme
généreuse avec de larges congés trahit la fonderie ; des zones minces et des
nervures trahissent un dimensionnement. Relever `D03` en plusieurs points est
donc la cote qui décide du poids final.

Une réserve tient, en revanche : amincir réduit la raideur entre vis, donc la
tenue du plan de joint. Sur un couvercle étanche à l'huile, c'est la contrainte
qui borne l'exercice, et elle se vérifie après relevé des entraxes.

## Ce que le calcul tranche déjà, sans la pièce

C'est le point qui distingue ce couvercle du carter entier, où le titane avait
été refusé.

**La dilatation différentielle tient.** Le carter en aluminium s'allonge plus que
le couvercle en titane ; l'écart doit rentrer dans le jeu de perçage, sinon les
vis travaillent en cisaillement et le plan de joint se déplace.

| grandeur | valeur |
|---|---|
| entraxe extrême supposé | 100 mm |
| écart de température supposé | 100 K |
| allongement du carter aluminium | 0,230 mm |
| allongement du couvercle titane | 0,086 mm |
| **différentiel** | **0,144 mm** |
| jeu disponible, vis M8 dans perçage Ø8,4 | 0,200 mm |
| **marge** | **+0,056 mm** |

Ça passe. Mais la marge est mince et repose sur deux hypothèses — l'entraxe et le
diamètre de perçage — qui sont précisément ce que la mesure doit donner. Si
l'entraxe réel dépasse ~139 mm au même jeu, ça ne passe plus, et il faut alors
ouvrir les perçages.

C'est exactement pourquoi le carter entier, lui, est refusé : son plan de joint
est bien plus étendu.

**Le couple galvanique est déjà traité par la nomenclature.** Le joint
`964 105 181 01` sépare les deux métaux sur tout le plan de joint. L'isolation
principale existe donc déjà. Restent deux chemins : la visserie, si elle touche
les deux pièces, et la face extérieure exposée à l'humidité. Rondelles ou
douilles isolantes, pâte anti-grippage, anodisation du couvercle.

## Ce qu'il faut mesurer — une heure, un pied à coulisse

Le couvercle déposé, à plat sur un marbre ou une vitre. Repère : le coin ou le
perçage le plus éloigné, à déclarer une fois et à garder pour toutes les cotes.

| id | cote | comment |
|---|---|---|
| D01 | contour, longueur | au pied à coulisse, deux fois, dans l'axe long |
| D02 | contour, largeur | idem, perpendiculaire |
| D03 | épaisseur au plan de joint | trois points répartis |
| D04 | épaisseur hors tout si le couvercle est bombé | au sommet |
| D05 | décalage du bombé par rapport au plan de joint | réglet + cale |
| D06 | diamètre des perçages de fixation | trois perçages différents |
| D07 | nombre de perçages | comptage |
| D08 | entraxes perçage à perçage | **tous**, de proche en proche, plus les deux diagonales extrêmes |
| D09 | largeur de la portée de joint | pied à coulisse |
| D10 | épaisseur du joint neuf, non comprimé | sur le joint `964 105 181 01` |
| D11 | centrage : diamètre et position de tout goujon, pion ou épaulement | |
| D12 | rayons d'arête | jeu de rayons ou empreinte |
| D13 | jeu intérieur au couvercle vis-à-vis de la chaîne et du tendeur | **critique** : le couvercle ne doit rien toucher |

D08 et D13 sont les deux qui décident. D08 valide ou invalide la marge de
dilatation calculée plus haut. D13 est la seule qui ne se rattrape pas.

Le dépôt a l'outil de capture :

```bash
python3 scripts/capture_caliper.py \
  --record catalog/measurements/meas-993-chain-case-lid.json \
  --dimension D08 --description "Entraxe percage 1 vers percage 2" \
  --manual --values 62.10,62.08,62.11
```

## Ce qui part chez le fraiseur

- plaque **Ti-6Al-4V Grade 5**, ASTM B265, certificat matière ;
- fraisage du contour, des perçages et du plan de joint ;
- **planéité tenue sur le plan de joint** — c'est la cote fonctionnelle, à fixer
  après relevé ;
- cassage d'arêtes ;
- finition : microbillage, ou anodisation titane si la couleur est recherchée —
  l'anodisation du titane est interférentielle, sans épaisseur notable, donc
  sans effet sur l'ajustement ;
- contrôle dimensionnel du contour, des entraxes et des perçages.

Garder la visserie d'origine en acier, avec pâte anti-grippage. Le titane grippe
sur lui-même ; contre de l'acier avec pâte, c'est maîtrisé.

## Statut

`functional`, pas `non_critical` : la pièce retient de l'huile, et sur un moteur
refroidi par air une fuite a des voisins chauds. Rien n'est autorisé au montage
avant relevé d'un exemplaire, essai d'étanchéité et contrôle du jeu intérieur.

## Reproduction

```bash
python3 parts/993-eng-chain-case-lid-ti-f0-0001/source/chain_case_lid_screen.py \
  --report parts/993-eng-chain-case-lid-ti-f0-0001/evidence/parametric-screen.json
```

Une fois les cotes relevées, le même script les prend en arguments et le rapport
cesse d'être une hypothèse :

```bash
python3 parts/993-eng-chain-case-lid-ti-f0-0001/source/chain_case_lid_screen.py \
  --bolt-circle-mm <D08 max> --plan-area-cm2 <D01xD02> --thickness-mm <D03> \
  --bolt-diameter-mm <vis> --clearance-hole-mm <D06> --measured \
  --report parts/993-eng-chain-case-lid-ti-f0-0001/evidence/parametric-screen.json
```
