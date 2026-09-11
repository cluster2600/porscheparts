# Couvercle de carter de chaîne `964 105 107 01` en Ti-6Al-4V

> **Correction majeure du 11 septembre 2026.** Tout ce document a d'abord comparé
> le titane à de l'**aluminium**. C'était faux : **la pièce d'origine est en
> magnésium coulé**, et c'est sa corrosion qui fait vivre tout le marché du
> couvercle billet. La section « Contre la vraie matière d'origine » ci-dessous
> refait les comptes, et elle renverse la conclusion sur la masse tout en donnant
> au titane un argument bien plus fort que celui qu'on lui prêtait.

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

### Pourquoi ça bascule : les deux indices

« Le titane est plus résistant, donc moins épais, donc plus léger » est **exact —
à condition que ce soit la résistance qui dimensionne.** Pour une plaque de
contour imposé dont on ajuste l'épaisseur, les deux cas ont chacun leur indice :

| ce qui dimensionne | indice à maximiser | aluminium | titane | Ti/Al |
|---|---|---:|---:|---:|
| **raideur** imposée | `E^⅓ / ρ` | 1,526 | 1,095 | **0,72 — l'alu gagne** |
| **résistance** imposée | `σ_y^½ / ρ` | 4,969 | 6,503 | **1,31 — le titane gagne** |

La raideur d'une plaque varie en `t³`, la résistance en `t²`. Un matériau plus
rigide se rattrape donc à la puissance ⅓, un matériau plus résistant à la
puissance ½. Le titane n'est que **1,63×** plus rigide que l'aluminium mais
**≈ 4,6×** plus résistant : il perd le premier arbitrage et gagne largement le
second.

Détail qui surprend : en traction pure, `E/ρ` vaut 25,9 pour l'aluminium et 25,7
pour le titane — ils sont **équivalents**. Ce n'est qu'en flexion de plaque, où
l'exposant tombe à ⅓, que l'aluminium prend l'avantage.

### Et pour ce couvercle-ci, quatre indices convergent

| observation | ce qu'elle dit |
|---|---|
| serrage **9,7 Nm** | faible effort de serrage → faible réaction de joint → faible demande de flexion |
| visserie **M6** | petites vis, donc probablement nombreuses et rapprochées ; la flèche varie en `L⁴` sur l'entraxe, et des spans courts l'annulent |
| pression interne de carter | quelques centaines de millibars : négligeable |
| pièce de **fonderie** | épaisseur portée par la paroi minimale coulable et la dépouille |

Conclusion honnête : il est **probable que ni la raideur ni la résistance ne
dimensionnent ce couvercle** — c'est la fonderie qui le fait. Dans ce cas la
contrainte disparaît, un couvercle titane fraisé peut simplement être fait mince,
et il sera plus léger.

Ce n'est pas démontré. Il manque `D03` (l'épaisseur d'origine) et `D08`
(l'entraxe, qui pilote la flèche en puissance 4). Mais les quatre indices pointent
dans le même sens, et aucun ne pointe dans l'autre.

**Et il existe un troisième cas, le plus probable ici.** L'épaisseur d'une pièce
de fonderie n'est souvent dictée ni par la raideur ni par la résistance, mais par
la fonderie elle-même : paroi minimale coulable, dépouille, remplissage. Une
pièce fraisée n'a aucune de ces contraintes. Dans ce cas le titane peut être plus
mince que la fonte **et** rester plus raide qu'il ne faut.

### Contre la vraie matière d'origine : le magnésium

| indice | magnésium (origine) | aluminium billet (rechange) | titane |
|---|---:|---:|---:|
| raideur imposée `E^⅓/ρ` | **1,965** | 1,526 | 1,095 |
| résistance imposée `σ_y^½/ρ` | **6,988** | 4,969 | 6,503 |

Le titane est **2,45× plus dense** que le magnésium. Il perd l'arbitrage de
raideur très largement — et il perd **aussi** celui de résistance, de peu.

Donc : « plus résistant donc moins épais donc plus léger » est exact contre
l'aluminium, et **faux contre le magnésium**. Sa densité est trop basse pour être
rattrapée, même par un matériau 5× plus résistant. Un couvercle titane sera plus
lourd que l'origine, quelle que soit l'épaisseur retenue.

### Mais le titane gagne ailleurs, et c'est plus fort

Le mode de défaillance de la pièce d'origine est la **corrosion** : le magnésium
se pique sur ses portées d'étanchéité, et aucun joint n'étanche contre une portée
piquée. C'est exactement le deuxième critère de `TITANIUM.md` — « corrosion
problématique **avec la matière d'origine** » — et il est ici au cœur du sujet.

Un couvercle titane ne se pique pas. Jamais. C'est le seul vrai argument, et il
vaut mieux que celui de la masse qu'on lui prêtait.

### L'obstacle qui reste, et il est sérieux

Le couvercle se boulonne sur un carter **lui aussi en magnésium**. Le magnésium
est le plus anodique des métaux de structure, le titane l'un des plus
cathodiques : c'est **le couple le plus défavorable de la grille**, et
`TITANIUM.md` nomme explicitement le magnésium.

Le joint isole les portées. Il n'isole ni la visserie, ni les chemins d'humidité.
Un couvercle titane pourrait donc protéger sa propre portée **tout en aggravant
l'attaque du carter en face** — c'est-à-dire déplacer le problème sur la pièce
qu'on ne peut pas remplacer.

C'est non résolu, et le criblage le compte comme bloquant.

**C'est aussi pourquoi le marché vend de l'aluminium anodisé** : assez résistant à
la corrosion pour régler le problème, assez proche du magnésium pour que le
couple reste doux, et plus léger que le titane.

### Le seuil décidable

On peut aller plus loin qu'« ça dépend ». Le titane usiné **à la raideur
strictement nécessaire** est plus léger que la fonte dès que celle-ci porte

> **≈ 39 % d'épaisseur de plus que sa propre exigence de raideur.**

Formellement : titane gagnant ⟺ `t_requis / t_coulé < ρ_al / (ρ_ti · 0,851) = 0,717`.

Sur une pièce de fonderie — paroi minimale coulable, dépouille, remplissage —
39 % de gras n'est pas une hypothèse extravagante. C'est le cas courant.

**Et ça se teste pour presque rien.** LN Engineering usine ce même couvercle dans
du 6061 massif, *sans aucune contrainte de fonderie*. Son épaisseur, comparée à
celle de la pièce d'origine, mesure directement le gras. Deux cotes, et la
question est tranchée.

### Ce que le couple de serrage ajoute

Le manuel serre ce couvercle à **9,7 Nm sur du M6**. C'est peu. Un faible couple
veut dire un faible effort de serrage, donc une faible réaction de joint, donc
une faible demande de flexion sur le couvercle. Ajouté à une pression interne de
carter qui se compte en centaines de millibars, cela dit que **la pièce ne
travaille quasiment pas**.

Ce n'est pas une preuve, mais cela pointe dans la même direction : l'épaisseur
d'origine n'est probablement dictée ni par la raideur ni par la résistance, mais
par la fonderie. Et c'est le cas où le titane gagne.

C'est la mesure et l'œil qui trancheront : une épaisseur uniforme généreuse avec
de larges congés trahit la fonderie ; des zones minces et des nervures trahissent
un dimensionnement. `D03` reste la cote qui décide du poids final.

Une réserve tient, en revanche : amincir réduit la raideur entre vis, donc la
tenue du plan de joint. Sur un couvercle étanche à l'huile, c'est la contrainte
qui borne l'exercice, et elle se vérifie après relevé des entraxes.

## Ce que le calcul tranche déjà, sans la pièce

C'est le point qui distingue ce couvercle du carter entier, où le titane avait
été refusé.

**La dilatation différentielle tient, et largement.** Ce calcul a été refait le
11 septembre 2026 : la première version comparait la dilatation d'une portée
entière à un jeu radial, ce qui surestimait le problème d'un facteur deux, et
supposait de la visserie M8 alors que le manuel serre ce couvercle à 9,7 Nm,
c'est-à-dire du M6.

Ce qui doit tenir dans le jeu n'est pas la dilatation des pièces, c'est leur
**écart au perçage le plus éloigné du point fixe** : `δ = r · (α_al − α_ti) · ΔT`.

| grandeur | valeur |
|---|---|
| portée extrême supposée | 100 mm |
| point fixe | centre du semis de vis → `r` = 50 mm |
| écart de température supposé | 100 K |
| **écart relatif au pire perçage** | **0,072 mm** |
| jeu radial, M6 dans perçage Ø6,6 | 0,300 mm |
| **marge** | **+0,228 mm — le jeu n'est utilisé qu'à 24 %** |

Et la sensibilité, parce qu'une marge sans sensibilité ne vaut rien :

| point fixe | Ø6,4 | Ø6,6 | Ø7,0 |
|---|---|---|---|
| centre du semis | 36 % | **24 %** | 14 % |
| douille de centrage en bord | 72 % | 48 % | 29 % |

Ça passe dans les six cas. Le pire — centrage par douille et perçage fin — utilise
72 % du jeu, et c'est celui à surveiller : la planche 103-05 porte justement une
douille de centrage, `993 105 175 00`. Si elle tient ce couvercle, le point fixe
n'est plus le centre du semis et le rayon défavorable double.

**Une réserve de méthode.** Tout ceci suppose les vis centrées dans leurs
perçages au montage à froid. Une vis déjà en appui du mauvais côté n'aurait aucun
jeu : la moitié de la marge affichée est une tolérance de montage, pas une
réserve de calcul.

C'est exactement pourquoi le carter entier, lui, est refusé : sur une portée de
500 mm centrée par une douille, l'écart atteint 0,72 mm et aucun perçage courant
ne l'absorbe.

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

## Sans accès à la pièce — 11 septembre 2026

Le plan de mesure ci-dessus suppose le couvercle en main. Sans accès aux pièces,
la question devient : **les cotes sont-elles trouvables en ligne ?**

Réponse : **non**, et la recherche a quand même rapporté plus que des cotes.

### Ce que le marché établit

Deux reproducteurs indépendants fabriquent ce couvercle.

**LN Engineering** usine des couvercles billet en **aluminium 6061**, donnés
comme remplacement direct de `96410510801` (droite) et **`96410510701`
(gauche)**, conçus pour reprendre la visserie et le joint d'origine
`96410518101`. **Auto-Service Schefter** usine un jeu gauche et droite en CNC,
585 € le jeu.

Trois choses en découlent, et aucune n'est mince :

1. `964 105 107 01` est bien le couvercle **gauche**, apparié au joint
   `964 105 181 01` — confirmé par une source indépendante du catalogue ;
2. la pièce **se reproduit par usinage dans la masse**. Ce n'était jusqu'ici
   qu'un raisonnement de ma part ; c'est maintenant ce que fait le marché ;
3. les deux reproducteurs ont choisi **l'aluminium**. Le titane est donc un
   écart assumé par rapport à ce que deux professionnels ont jugé juste.

Ce qu'aucun des deux ne publie : **la moindre cote**. Ni épaisseur, ni contour,
ni entraxe, ni nombre de vis.

Le manuel d'atelier apporte en revanche une donnée réelle : **« Chain housing
cover : 9,7 Nm »**. Un tel couple situe la visserie en **M6**, pas en M8. La
marge de dilatation calculée plus haut, qui supposait du M8 dans un perçage
Ø8,4, est donc à refaire une fois le perçage connu.

### Ce qui débloque réellement, et ça ne demande pas la voiture

La bonne question n'est pas « où trouver les cotes » mais **« quel est l'objet le
moins cher qui les porte »**.

| objet | ce qu'il donne | ordre de prix |
|---|---|---|
| **le joint `964 105 181 01`** | contour d'étanchéité, entraxes, nombre et diamètre des perçages, largeur de portée | **~13 $** (Victor Reinz 70-29108-00, Elring 471.200) |
| **un couvercle d'occasion** | tout, épaisseur et dégagement intérieur compris | quelques dizaines d'euros chez un casseur de pièces 964 |

Le joint arrive dans une enveloppe et donne à lui seul les deux cotes qui
décidaient, `D08` les entraxes et le contour. Un couvercle d'occasion donne en
plus `D03` l'épaisseur — celle qui dira si l'on peut amincir et donc gagner du
poids — et `D13` le dégagement intérieur, la seule cote qui ne se rattrape pas.

**Aucun des deux ne demande d'accéder à une voiture.** C'est du courrier.

### Ce qu'il ne faut pas faire

Reconstruire les cotes depuis des photos de vente. `SOURCE_POLICY.md` est
explicite : une capture sans échelle n'est pas une mesure. Une pièce étanche à
l'huile dont le plan de joint viendrait d'une photo redimensionnée ne fuirait pas
un peu, elle fuirait.
