# Essai numerique de resistance — plancher 964 en torsion

Chaine : gmsh 4.15.2 (maillage coque) -> CalculiX 2.21 (elements S3).
Acier E = 210 000 MPa, nu = 0,3. Unites mm, N, MPa.

Cas de charge : arriere encastre, couple de 1290 N.m applique en pointes de
longeron a l'avant (1000 N vers le haut a gauche, 1000 N vers le bas a droite,
bras de levier 1290 mm).

## Epaisseur de tole

Donnee apportee par le proprietaire du projet : **0,8 mm annonce par Porsche,
1,0 mm mesure**. Les deux valeurs sont conservees, non moyennees.

| epaisseur | rotation | raideur en torsion | vM max |
|---|---|---|---|
| 0,8 mm (annonce) | 0,5283 deg | **2442 N.m/deg** | 86,1 MPa |
| 1,0 mm (mesure)  | 0,4222 deg | **3056 N.m/deg** | 68,8 MPa |

Rapport de raideur 1,251 pour un rapport d'epaisseur 1,250. **La raideur suit
l'epaisseur lineairement, pas au cube.** La structure travaille en cisaillement
de membrane, comme un caisson ferme, et non en flexion de plaque. L'ecart entre
0,8 et 1,0 vaut donc 25 % de raideur et 25 % de contrainte : ce n'est pas un
detail de modelisation.

Les 0,2 mm d'ecart demandent une explication avant d'etre utilises. La caisse
964 est galvanisee a chaud ; zinc, appret, peinture et cire de corps creux
s'ajoutent a la tole. Une mesure au pied a coulisse sur panneau en place mesure
l'empilement, pas l'acier. **Pour le calcul, c'est l'epaisseur d'acier qui
porte**, donc 0,8 mm tant que la mesure n'est pas refaite sur tole decapee ou au
mesureur a ultrasons. Retenir 1,0 mm surestimerait la raideur de 25 %.

## Ou ca travaille

Valeurs recalculees apres le retrait de la traverse inerte decrit plus bas. Un
noeud est classe par sa position : longeron si |y| >= 600, traverse s'il est
sous le plancher ou dans l'emprise d'une traverse, plancher sinon.

| zone | contrainte moyenne | p95 | max |
|---|---|---|---|
| longeron (caisson ferme) | 25,5 MPa | 62,3 | 86,1 |
| traverse | 19,6 MPa | 30,0 | 45,7 |
| plancher | 10,6 MPa | 26,5 | 34,1 |

**Le longeron porte la torsion.** Les 1 % de noeuds les plus charges sont a
100 % dans le longeron, et le restent apres exclusion de 300 mm en avant de
l'encastrement : le resultat n'est pas un artefact de condition aux limites.
Environ 22 % du pic brut l'etait toutefois — 86,1 MPa tombent a 66,8 MPa une
fois la zone d'encastrement ecartee. Le rapport longeron/plancher est de 2,41.

Ce resultat converge avec le manuel : la planche 50-013 designe le *inner side
member* comme panneau en acier haute resistance. Porsche a mis l'acier HS la ou
le calcul place le chemin d'effort.

## Ce que ces chiffres ne sont pas

**2442 N.m/deg n'est pas la raideur d'une 964.** Ce modele-ci ne contient que
plancher, deux longerons et deux traverses : ni tablier, ni cloison arriere, ni
tunnel, ni passages de roue, ni pavillon, ni pieds milieu, ni cadre de
pare-brise, qui portent l'essentiel de la torsion d'une caisse complete. Les
sections suivantes les ajoutent une a une — et montrent qu'ensemble elles valent
un facteur 3,7 — mais aucune de ces variantes n'est davantage une raideur de 964.

De plus la section de longeron 90 x 120 mm et la section de traverse 80 x 70 mm
restent `ASSUMED` : le volume V ne les publie pas. La position longitudinale des
traverses depend de la chaine de datums, elle-meme non calee (voir le README du
jumeau).

Sont robustes, parce qu'ils ne dependent pas de ces inconnues :
- la loi d'echelle lineaire en epaisseur, qui est un resultat de mecanique ;
- le fait que le longeron, et non le plancher, porte la torsion ;
- le classement des elements de caisse par leur apport en torsion, verifie a
  trois finesses de maillage.

Ne sont pas robustes : toutes les valeurs absolues de raideur et de contrainte.
Le modele n'est d'ailleurs pas converge en maillage — la raideur baisse encore
de 4 % au dernier raffinement essaye, les elements S3 convergeant par le haut.

## Rejouer

    source ../source/env.sh
    pycad build_shell.py 0.8 1.0 && pycad run_fea.py 0.8 t08
    pycad build_shell.py 1.0 1.0 && pycad run_fea.py 1.0 t10

## Cisaillement ou flexion ? La reponse etait fausse

Ce README affirmait, et l'etude composite avec lui, que « la structure travaille
en cisaillement de membrane, comme un caisson ferme ». **C'est faux pour le
modele sur lequel l'affirmation a ete faite.**

Elle reposait sur deux observations dont aucune ne la demontre. La raideur suit
lineairement l'epaisseur : cela ecarte la flexion de **plaque**, mais pas celle
d'une **poutre a paroi mince**, dont l'inertie varie aussi lineairement avec
l'epaisseur. Et la prediction iso-raideur d'un changement de materiau tombait a
6,9 % : mais tous les materiaux compares etaient isotropes, ou `G` est
proportionnel a `E`, si bien que ce controle ne peut pas, par construction,
distinguer l'un de l'autre.

`dominance_study.py` tranche en faisant varier `E` et `G` **separement**, avec un
materiau orthotrope fictif ou les deux sont decouples. Non physique, et c'est
voulu : c'est un instrument de mesure, pas un materiau.

| architecture | doubler E | doubler G | mecanisme reel |
|---|---|---|---|
| plancher, longerons, traverses | **+93,8 %** | +2,1 % | flexion, quasi pure |
| cellule fermee | +37,7 % | **+56,9 %** | cisaillement dominant, mais mixte |

En torsion, les deux longerons du plancher nu flechissent en sens opposes : ce
sont deux consoles. Le cisaillement n'apparait qu'une fois les anneaux fermes, et
il ne devient jamais exclusif.

C'est la decouverte des anneaux vue par l'autre bout : **fermer un anneau ne fait
pas qu'ajouter de la raideur, cela change le mecanisme qui la porte.**

Ce qui reste vrai : la loi d'echelle lineaire en epaisseur, le fait que le
longeron porte l'effort, et tous les rapports mesures entre architectures. Ce qui
tombe : l'interpretation `G/rho` comme critere de materiau du plancher. Pour le
plancher seul le critere est `E/rho`. Le classement carbone > aramide n'en est
pas affecte, le carbone dominant sur les deux.

    pycad dominance_study.py f
    pycad dominance_study.py fbtaprw

## Stratifies reels : coques composites multicouches

`run_fea_laminate.py` resout un vrai empilement — `*SHELL SECTION, COMPOSITE`,
un pli par couche, une `*ORIENTATION` par angle et par famille de panneaux.

Trois contraintes de CalculiX ont du etre levees, et elles ne sont pas dans la
documentation courante :

- `COMPOSITE` n'accepte **que des coques quadratiques S6 ou S8R**. D'ou l'ordre
  de maillage optionnel de `build_body.py` ;
- le 4e champ d'une couche est un **nom d'orientation**, pas un angle. Un pli a
  45 degres se materialise par une `*ORIENTATION` tournee de 45 degres autour de
  la normale du panneau ;
- `OUTPUT=2D` est ignore : le `.frd` porte le modele 3D etendu et non les noeuds
  d'origine. Les noeuds de mesure sont donc repris **par leur geometrie**, ce qui
  ne depend d'aucune correspondance de numerotation.

La chaine est validee sur un cas analytique avant d'etre utilisee : traction
uniaxiale sur pli unidirectionnel, qui doit rendre E1 a 0 degre et E2 a 90.

| angle | E_x calcule | E_x attendu |
|---|---|---|
| 0 | 130 516 | 135 000 |
| 90 | 9 909 | 10 000 |
| 45 | 13 080 | 13 200 |

Resultat, huit plis de 0,4 mm, meme masse, memes conditions aux limites :

| empilement | plancher seul | cellule fermee |
|---|---|---|
| quasi-isotrope | 1586 | 6311 |
| +/-45 | 696 (0,44x) | **6849 (1,09x)** |
| 0/90 | **1910 (1,20x)** | 4043 (0,64x) |

**Le classement s'inverse avec l'architecture**, exactement comme la sensibilite
`E`/`G` le prevoit. Il n'existe donc pas d'empilement universellement bon pour
cette caisse, et le quasi-isotrope est un compromis defendable et non le mauvais
reglage. Une premiere analyse annoncait x 1,75 pour le +/-45 : c'etait une
prediction analytique valable pour du cisaillement pur, transportee a tort sur
une structure qui n'en fait pas.

    pycad build_body.py 0.8 fbtaprw 1.0 2 && pycad run_fea_laminate.py PM45 cell_PM45

## Variante composite

`run_fea.py` accepte desormais deux arguments optionnels, `E` et `nu`, qui
valent par defaut ceux de l'acier : les appels a deux arguments ci-dessus sont
inchanges. `laminate.py` calcule les proprietes quasi-isotropes d'un stratifie
carbone, aramide ou hybride depuis les constantes de pli, et `composite_study.py`
rejoue l'essai de torsion a raideur egale pour chacun.

Resultat court : a iso-raideur, le carbone monolithique ne gagne que **18 %** de
masse surfacique et l'aramide en **perd 30 %**, parce que ce caisson travaille en
cisaillement de membrane et que le critere est `G/rho`, non `E/rho`. L'analyse
complete et ses reserves sont dans `docs/research/964-chassis-carbone-kevlar.md`.

    pycad build_shell.py 0.8 1.0 && pycad composite_study.py

## Architecture contre materiau

`build_body.py` etend le modele coque aux elements qui **ferment** le caisson —
tablier avant, cloison arriere, tunnel central — et `architecture_study.py`
rejoue l'essai sur trois architectures et deux materiaux a masse egale. Le cas
`f`, plancher seul, redonne le maillage et la valeur de `build_shell.py`.

A masse egale, fermer la caisse vaut **x 1,51** en raideur specifique, passer au
carbone **x 1,25**, et les deux se multiplient (1,86 mesure pour 1,89 attendu) :
les leviers sont separables et ne se substituent pas. Le tunnel central seul
apporte +71 %, plus que les deux cloisons. Sections et hauteurs de cloison sont
`ASSUMED` ; seuls les rapports sont exploitables.

    pycad architecture_study.py

## Une traverse qui ne portait rien

Un controle de connexite ajoute a `build_body.py` a montre que le modele
comportait **deux composantes** et non une. La traverse arriere du reseau de
datums, `trans` a x = -1703, tombe derriere le bord arriere du plancher
modelise, x = -1500 : elle n'etait rattachee a rien. Elle a donc toujours
compte dans l'aire et dans la masse — 0,264 m2 et 1,66 kg, soit **5,7 % de la
masse du modele** — sans porter le moindre effort.

La verification est nette : a geometrie d'origine, retirer cette traverse rend
**exactement 2442 N.m/deg**, la valeur publiee au chiffre pres. Les raideurs
deja publiees etaient donc justes ; ce sont les **masses, et donc toutes les
raideurs specifiques K/m**, qui etaient minorees d'autant.

Elle n'a pas ete rattachee mais **retiree**, parce qu'elle est situee derriere
la section encastree de l'essai : meme reliee, elle ne pourrait rien porter. La
consequence sur les chiffres publies est limitee a l'etude d'architecture, dont
les rapports passent de x 1,61 a **x 1,51** pour la fermeture du caisson et de
x 1,98 a **x 1,86** pour les deux leviers. La conclusion, elle, ne bouge pas.

Le modele CAO `source/floor_assembly.py` n'est pas concerne : il produit un
assemblage de solides distincts, ou une traverse posee sur un point de datum
non cale est un etat documente et non un defaut.

Deux garde-fous sont en place pour que cela ne se reproduise pas en silence :
`build_body.py` echoue si le maillage n'est pas connexe, et `run_fea.py` lit les
bornes du modele **dans le maillage** au lieu de les recopier du script de
construction, ou elles pouvaient diverger.

## Un troisieme garde-fou, sur les fichiers de travail

`run_fea.py` efface desormais les sorties du tag — `.frd`, `.dat`, `.sta`,
`.cvg`, `.12d` — **avant** d'appeler le solveur. Ce n'est pas du menage.

Deux resultats faux ont ete produits pendant cette campagne par des fichiers de
travail laisses en place : un depouillement rendait la solution du run precedent
apres un echec du solveur, et un fichier de travail `.12d` issu d'un maillage
anterieur donnait 2445 N.m/deg et 70,0 MPa au lieu de 2442 et 69,6 sur un
maillage identique. Les ecarts sont petits, ce qui est precisement le probleme :
ils ne se voient pas. Un cas plus visible a aussi ete rencontre, un p99 de
contrainte a 265,8 MPa au lieu de 69,6.

Aucun de ces trois incidents n'a laisse de trace dans une sortie d'erreur.

Le depouillement lui-meme a ete rendu **fail-closed** pour la meme raison : il
moyennait les deplacements sur les seuls noeuds qu'il trouvait dans le `.frd`,
en ignorant silencieusement les manquants. Il verifie maintenant que le fichier
de resultats couvre tout le maillage et que tous les noeuds charges y sont, et
s'arrete sinon.

**Ce que vaut la reproductibilite apres ces corrections.** Cinq executions
consecutives de `body_study.py` rendent des valeurs identiques au chiffre pres,
et `ring_study.py` est stable de meme. Une variation isolee de 0,9 % a toutefois
ete observee sur un cas apres correction, sans etre reproduite depuis. On retient
donc un plancher de resolution de l'ordre du **pour cent** : un increment plus
petit que cela n'est pas une mesure. C'est exactement le cas de la ligne des
pieds milieu ci-dessous, et cela ne concerne aucune autre ligne du tableau.

## Du plancher a la cellule fermee

`body_study.py` prolonge l'echelle des architectures jusqu'a une cellule
complete. C'est la seule piste du dossier qui ne depende d'aucune donnee
exterieure : elle ne demande que des sections `ASSUMED` de plus.

Acier 0,8 mm, meme essai de torsion, meme chargement. Le couple s'applique et la
rotation se mesure desormais sur la **seule section de longeron** : sans cette
borne, le jeu de noeuds charges grossissait avec l'architecture et deux cas ne se
comparaient plus sous le meme chargement.

| architecture | masse | K (N.m/deg) | K/m | dK | dK par kg ajoute |
|---|---|---|---|---|---|
| plancher, longerons, traverses | 27,7 kg | 2442 | 88 | — | — |
| + tablier et cloison arriere | 35,2 kg | 3147 | 89 | +705 | +94 |
| + tunnel central | 40,2 kg | 5371 | 134 | +2224 | +444 |
| + passages de roue | 45,0 kg | 6866 | 153 | +1495 | +315 |
| + pieds milieu et brancards | 52,4 kg | 6859 | 131 | **0** (-7) | **0** |
| + pavillon | 63,0 kg | 6925 | 110 | +66 | +6 |
| + cadre de pare-brise | 64,1 kg | 9093 | 142 | +2167 | **+1961** |

Du plancher nu a la cellule fermee : **K x 3,7 pour une masse x 2,3**.

    pycad body_study.py

## Ce que ce classement dit, et ce qu'il ne dit pas

Deux lignes sortent de l'ordinaire et ne se lisent pas comme les autres.

**Les pieds milieu et les brancards n'apportent rien** — l'increment brut vaut
-7 N.m/deg a cette finesse, +3 et +11 aux deux autres. Un increment negatif
etant mecaniquement impossible, ces trois valeurs disent seulement que l'apport
est **nul a la resolution du calcul**, laquelle est de l'ordre du pour cent,
soit environ 70 N.m/deg ici. Ce n'est pas un defaut du modele : seuls, ces
elements forment un cadre **ouvert a l'avant**, une console encastree sur la
cloison arriere. Ils ajoutent 7,5 kg et aucun chemin d'effort ferme.

**Le cadre de pare-brise apporte le plus gros increment de l'echelle pour
1,1 kg**, le meilleur rendement au kilo de tout le dossier. Il est aussi le
seul element a fermer un anneau : tablier, montants A, traverse haute,
brancards, pieds milieu, montant arriere.

Cette phrase-la est fausse, et la section « L'ordre d'element » plus bas dit
pourquoi : en coques quadratiques, le meilleur rendement au kilo est celui du
tunnel central, pas celui du cadre de baie. Ce qui reste vrai du paragraphe est
le reste : l'anneau ferme, et le pavillon seul ne paie pas.

Cette lecture est une hypothese topologique, donc elle se refute.
`ring_study.py` ajoute pavillon et cadre de pare-brise **separement** a la meme
cage ouverte, a trois finesses de maillage :

| finesse | cage | + pavillon | + pare-brise | pavillon /kg | pare-brise /kg | rapport |
|---|---|---|---|---|---|---|
| 1,0 | 6859 | 6925 | 8180 | +6 | +1195 | 191x |
| 0,7 | 6333 | 6382 | 7220 | +5 | +803 | 172x |
| 0,5 | 6086 | 6123 | 6823 | +3 | +667 | 191x |

Le rapport reste de **deux ordres de grandeur** aux trois finesses, alors que la
raideur absolue derive de 11 % : c'est un resultat de topologie, pas de
discretisation. Et les deux elements ensemble rendent **1,6 fois** la somme de
leurs apports separes — le pavillon ne travaille qu'une fois l'anneau ferme.

    pycad ring_study.py

**Ce que ce n'est pas.** Aucun de ces chiffres n'est une raideur de 964, et
9093 N.m/deg encore moins que les autres : les sections de montant, de brancard
et de pied milieu sont toutes `ASSUMED`, la hauteur de pavillon aussi, et le
modele n'a ni vitrage colle, ni portes, ni ouvertures dans les panneaux — or
c'est precisement une baie vitree qui fait qu'un anneau de caisse reel est moins
ferme que celui-ci. Le modele n'est pas non plus converge en maillage : la
raideur absolue baisse encore de 4 % au dernier raffinement. Ce qui est
exploitable est le **classement** et les rapports, pas les valeurs.

## L'ordre d'element change les conclusions, pas seulement les valeurs

Tout ce qui precede est calcule en triangles **lineaires S3**. Les stratifies
composites, eux, ont ete calcules en **S6 quadratiques**, parce que CalculiX
l'exige pour `*SHELL SECTION, COMPOSITE`. Les deux moities du dossier n'etaient
donc pas comparables, et personne ne l'avait verifie.

`run_fea.py` lit desormais l'ordre dans le maillage et ecrit des elements S6
quand le maillage est quadratique. La meme geometrie, le meme chargement et le
meme depouillement peuvent enfin etre passes dans les deux ordres.

| architecture | masse | S3 | S6 | ecart |
|---|---|---|---|---|
| plancher, longerons, traverses | 27,7 kg | 2442 | **1436** | -41 % |
| + tablier et cloison arriere | 35,2 kg | 3147 | 1550 | -51 % |
| + tunnel central | 40,2 kg | 5371 | 3857 | -28 % |
| + passages de roue | 45,0 kg | 6866 | 5227 | -24 % |
| + pieds milieu et brancards | 52,4 kg | 6859 | 5240 | -24 % |
| + pavillon | 63,0 kg | 6925 | 5264 | -24 % |
| + cadre de pare-brise | 64,1 kg | 9093 | 5415 | -40 % |

Les S3 sont trop raides, et **ils le sont inegalement**. La ou la flexion domine
— le plancher nu — ils surestiment de 70 %. La ou le cisaillement domine, l'ecart
tombe. Ce n'est pas un defaut de finesse de maillage : raffiner en S3 fait
descendre K de 2442 a 1750 sans converger, tandis que le S6 rend 1436 des la
finesse la plus grossiere. **C'est l'ordre de l'element, pas le pas du maillage.**

### Ce que cela detruit

`dominance_study.py` etait deja en S6, et c'est ce qui a permis de voir le
probleme : sur le plancher nu il mesure +2,1 % en doublant G, la ou le meme
modele en S3 en mesure +36,6 %. Verifie avec `run_fea.py`, qui redonne bien
+2,3 % en S6 et +93,5 % en doublant E. **Les S3 attribuent au cisaillement une
part de la raideur qui revient a la flexion**, precisement sur les architectures
ouvertes.

Tombe donc, en plus de la phrase corrigee plus haut : le **rendement au kilo du
cadre de pare-brise**. En S6, l'echelle cumulee donne +151 N.m/deg pour 1,11 kg,
soit +136 par kg, contre +2307 pour 5,01 kg au tunnel central, soit **+460 par
kg**. Le meilleur rendement au kilo du dossier est celui du tunnel, dans les deux
ordres pour ce qui est de l'absolu, et en S6 aussi pour ce qui est du kilo.

### Ce que cela laisse debout

Les trois conclusions de topologie tiennent, et l'une d'elles au chiffre pres.

| resultat | S3 | S6 |
|---|---|---|
| pavillon seul ajoute a la cage ouverte | +66 (+6/kg) | +24 (**+2/kg**) |
| cadre de baie seul ajoute a la meme cage | +1321 (+1190/kg) | +83 (**+75/kg**) |
| rapport des rendements au kilo | 191x | **33x** |
| les deux ensemble / somme des deux seuls | 1,6x | **1,63x** |

Le pavillon seul ne paie pas, le cadre de baie paie beaucoup plus, et les deux
ensemble valent plus que leur somme parce que le pavillon ne travaille qu'une
fois l'anneau ferme. La synergie de 1,6 se retrouve a la troisieme decimale dans
un ordre d'element ou tout le reste a bouge de 25 a 50 % : c'est bien un
resultat de topologie.

Tient aussi le rapport d'ensemble du plancher nu a la cellule fermee : x 3,7 en
S3, **x 3,77 en S6**.

### Ce qu'il faut en retenir pour la suite

Aucune valeur absolue du dossier n'etait exploitable, et cela etait deja ecrit.
Ce qui est nouveau est qu'un **classement** — celui des rendements au kilo — ne
l'etait pas non plus. Les rapports qui survivent au changement d'ordre sont ceux
qui portent sur la topologie ; ceux qui portent sur la repartition flexion /
cisaillement ne survivent pas.

    pycad build_body.py 0.8 f 1.0 2 && pycad run_fea.py 0.8 s6

## Un quatrieme garde-fou, et un repli de solveur

Deux defauts trouves en auditant le corpus du plan d'experiences, tous deux du
meme genre que les precedents : ils produisaient un resultat au lieu d'une erreur.

**SPOOLES echoue sur certaines geometries, et son message ne sortait pas.**
Onze cas du corpus etaient perdus « sans message », ce qui avait ete lu comme la
signature d'un systeme quasi singulier. C'en est une autre : le solveur direct
meurt dans son partitionnement de graphe avec `fatal error in GPart_makeYCmap /
bad input`, message qu'il ecrit sur `stderr` — que `run_fea.py` n'affichait pas.
C'est deterministe, insensible au nombre de fils, et le solveur iteratif de
CalculiX passe sur ces memes cas. `run_fea.py` bascule donc sur lui en repli,
sans jamais s'en servir par defaut. Controles : le cas de reference rend toujours
2442 N.m/deg, et la ou SPOOLES aboutit les deux solveurs s'accordent a 0,04 %.

**Deux campagnes lancees en parallele se partageaient `mesh.npz`.** Elles se
seraient contaminees en silence, et une mesure de cette session l'a effectivement
ete avant que l'on comprenne pourquoi : un rejeu de cas lisait le maillage d'une
autre campagne en cours. `build_body.py` et `run_fea.py` acceptent desormais un
repertoire de travail par la variable `FEA_WORK`, et `doe_corpus.py` en cree un
par campagne. Sans surcharge, rien ne change.

**Le solveur se trompe parfois, et se trompe en silence.** Sur 65 cas du corpus
rejoues a l'identique, 63 redonnent le chiffre stocke a la decimale et deux non :
l'un a 2,4 %, l'autre d'un facteur 9. Le champ de deplacement stocke est
parfaitement coherent avec la raideur stockee dans les deux cas, parce que les
deux viennent du meme solve rate : **aucun controle interne ne peut les voir**.
Seule la repetition les trouve. `corpus_repair.py` rejoue le corpus cas par cas
et ne remplace une valeur que si deux calculs independants s'accordent contre
elle.
