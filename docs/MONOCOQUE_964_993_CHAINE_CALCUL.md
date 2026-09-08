# Chaine de calcul du monocoque : qui fait quoi, et ou il faut autre chose

Question posee : faut-il un autre logiciel pour calculer notre alternative ?
Reponse courte : **non pour la raideur et le drapage, oui pour le choc.**

## 1. Ce que CalculiX fait, et c'est desormais prouve

CalculiX 2.21 est le solveur de reference du dossier. Sa capacite sur composite
n'etait pas acquise : elle a ete etablie et validee le 2026-09-04.

- stratifie multicouche reel, `*SHELL SECTION, COMPOSITE`, un pli par couche ;
- orientation materiau par pli et par famille de panneaux ;
- materiau orthotrope, `*ELASTIC, TYPE=ENGINEERING CONSTANTS` ;
- validation sur cas analytique : traction uniaxiale sur pli UD, E1 a 0 degre et
  E2 a 90 degres retrouves **a 3 % pres**.

Trois contraintes non evidentes, consignees parce qu'elles couteraient une
journee a qui les redecouvrirait : `COMPOSITE` exige des coques **quadratiques**
S6 ou S8R ; le 4e champ d'une couche est un **nom d'orientation** et non un
angle ; `OUTPUT=2D` est **ignore**, le `.frd` portant le modele 3D etendu.

Couvre donc, sans autre logiciel : raideur en torsion et en flexion, drapage,
comparaison d'architectures, modes propres, thermique, non-lineaire materiau et
geometrique. C'est tout le programme jusqu'a M6.

## 2. Ce que CalculiX ne fait pas, et qui exige autre chose

| besoin | pourquoi CalculiX ne suffit pas | outil |
|---|---|---|
| **choc, absorption, integrite cellule** | solveur implicite ; le choc est un probleme explicite a grandes deformations, contact generalise et rupture | **OpenRadioss** (open source, Altair, 2022) ; a defaut LS-DYNA ou Abaqus/Explicit |
| **rupture et delaminage du stratifie** | aucun critere composite integre : ni Hashin, ni Puck, ni zone cohesive | post-traitement des contraintes par pli, a ecrire ; ou solveur dedie |
| **drapabilite** | question de fabrication, pas de mecanique : une nappe ne se pose pas sur une double courbure quelconque | outil de drapage dedie, tous commerciaux |
| **exploration a grande dimension** | chaque calcul coute ; il en faudrait des milliers | modele de substitution, voir section 3 |

**Le choc est le seul verrou logiciel reel du programme**, et il tombe
exactement sur la classe `prohibited_pending_engineering`.

### Ce qui existe reellement en open source pour le choc

Verifie le 2026-09-04.

| projet | licence | statut |
|---|---|---|
| **[OpenRadioss](https://github.com/OpenRadioss/OpenRadioss)** | **AGPL-3.0** | solveur explicite **industriel**, ouvert par Altair en septembre 2022. C'est le meme code que le Radioss commercial employe en crash automobile par des constructeurs. **La reponse.** |
| FrontISTR | ouvert | explicite present, bien moins mature en crash |
| Code_Aster, Elmer | ouverts | riches, mais ce ne sont pas des codes de crash |
| CalculiX | ouvert | implicite ; hors sujet pour le choc |

OpenRadioss lit son format natif `.rad`, **le format LS-DYNA `.k`/`.key`
nativement**, et l'Abaqus `.inp` par convertisseur. L'interoperabilite n'est donc
pas un obstacle, et les modeles de corps humain publics sont utilisables.

**La reserve porte sur le composite, et elle est serieuse.** Le depot OpenRadioss
annonce les materiaux legers et composites comme un axe d'amelioration, ce qui
veut dire que ce n'est pas son point fort etabli, et le suivi du projet porte une
question ouverte sur le crash composite. Or le comportement en choc d'un
stratifie carbone — ecrasement progressif, delaminage, rupture de fibre — est
**le probleme le plus difficile de toute la simulation de crash**, y compris dans
les codes commerciaux. Il ne se predit pas sans calibration sur essais de
coupons et de tubes d'ecrasement.

Conclusion a tenir : OpenRadioss permet de **concevoir** les zones d'absorption
et de comparer des architectures. Il ne permet **a personne**, ni a nous ni a un
editeur commercial, de revendiquer une tenue au choc sans essais physiques.

## 3. PhysicsNeMo : ou il sert reellement, et pourquoi pas encore

PhysicsNeMo **n'est pas un solveur de structure**. C'est un cadre d'apprentissage
physique : il produit des modeles de substitution entraines sur des calculs
existants. Il ne remplace pas CalculiX, il l'amortit.

Usage legitime dans ce programme : une fois le drapage zone parametre, l'espace
de conception a des dizaines de dimensions — angles par zone, nombre de plis,
sections, hauteurs d'anneau. L'explorer par calcul direct est hors de portee ; un
substitut entraine sur quelques centaines de cas CalculiX le rend praticable.

**Et NVIDIA publie exactement ce cas d'usage.** PhysicsNeMo porte un exemple
`structural_mechanics/crash` : un substitut de crash entraine sur des
simulations LS-DYNA existantes, lues depuis les `d3plot` par PhysicsNeMo-Curator,
avec plusieurs architectures — GeoTransolver, Transolver, MeshGraphNet,
FIGConvUNet, GeoFlare — sur des cas de caisse en blanc, d'absorbeur et de poutre
de pare-chocs.

Deux enseignements, et ils confirment le role assigne ici :

- **c'est un substitut, pas un solveur.** Il apprend d'un code de crash ; il ne
  le remplace pas. La chaine reste solveur -> corpus -> substitut ;
- **les tailles d'echantillon sont modestes** — de l'ordre de 121 cas
  d'entrainement pour la poutre de pare-chocs. C'est de l'exploration de
  conception, pas de la certification. L'exemple porte d'ailleurs ses propres
  limites declarees : normalisation incomplete, `batch_size=1`.

Piste a verifier : l'exemple ingere du `d3plot` LS-DYNA. Savoir si la sortie
d'OpenRadioss s'y raccorde directement, ou demande une conversion, decide du cout
de cette branche. A instruire avant de l'engager.

**Trois conditions, aucune remplie aujourd'hui :**

1. **Un corpus coherent.** Le dossier compte aujourd'hui une quinzaine de cas,
   dont plusieurs a geometrie changeante. Ce n'est pas un ensemble
   d'apprentissage, c'est une serie d'essais. Il en faut des centaines, sur une
   parametrisation figee.
2. **La regle du depot.** `ROADMAP.md` classe hors perimetre un « modele IA de
   substitution avant l'existence d'un corpus FEA/CFD coherent ». La condition 1
   n'est pas une preference, c'est une regle ecrite.
3. **Le conteneur.** `docs/917_MODULAR_COMPUTE_STACK.md` indique que
   `physicsnemo-cae-cu12` a un lock OCI verifie mais que **son smoke GPU et son
   transport SSH restent faux** : il n'est pas autorise pour un job long.

S'y ajoute un fait materiel : **il n'y a pas de GPU sur cette machine**
(`nvidia-smi` absent). Tout entrainement passe par une location Vast.ai, ce que
`containers/provision-vastai.sh` prevoit deja.

Consequence d'ordonnancement : PhysicsNeMo vient **apres** la generation du
corpus, laquelle ne demande aucun GPU — un plan d'experiences CalculiX est du
calcul CPU, massivement parallele et exécutable sur n'importe quelle machine.

## 3bis. Ce qui est deja pret pour PhysicsNeMo, sans GPU ni SSH

Prepare le 2026-09-04, precisement parce que la condition bloquante — le corpus —
ne demande aucun materiel particulier.

`fea/doe_corpus.py` produit le corpus par plan d'experiences CalculiX :

- **espace fige** : sept architectures, huit sections `ASSUMED` balayees en
  hypercube latin, epaisseur de peau et module. Le plan explore donc autant
  l'incertitude du modele que la conception ;
- **cible en champ, pas en scalaire.** Chaque cas conserve le champ nodal de
  deplacement sur son maillage. C'est ce qui justifie PhysicsNeMo : une raideur
  scalaire fonction de huit parametres se regresserait sans lui ;
- **reproductible** : tirage deterministe par graine, parametres portes par
  chaque cas, empreintes des scripts dans le manifeste ;
- **reprenable** : relancer complete un corpus au lieu de le refaire ;
- **debit mesure : 2,3 s par cas** en ordre 1. Mille cas tiennent en 40 minutes
  de CPU, sur cette machine, sans rien louer.

Pour lancer, plus tard ou maintenant :

    python3 doe_corpus.py --smoke          # 4 cas, verifie la chaine
    python3 doe_corpus.py --n 1000         # corpus d'entrainement

### Corpus genere le 2026-09-07

Premier corpus complet, graine 0, elements d'ordre 1.

| grandeur | valeur |
|---|---|
| cas demandes / ecrits | 1000 / **998** |
| duree | 35 min, un seul coeur de machine de bureau |
| taille | 126 Mo |
| raideur K | 365 a 26 637 N.m/deg, mediane 5535 |
| masse | 21,3 a 164,2 kg |
| noeuds par cas | 2 389 a 7 461 |
| champs non finis, K nul ou negatif | **aucun** |

Repartition par architecture entre 122 et 156 cas sur sept familles : le plan
n'est pas biaise. L'amplitude de K est d'un facteur 73 entre le cas le plus
souple et le plus raide, ce qui donne au substitut de quoi apprendre autre chose
que du bruit.

**Les deux cas perdus sont instructifs.** Tous deux sont des `fbtap` — la cage
ouverte : pieds milieu et brancards sans cadre de baie ni pavillon pour fermer a
l'avant. CalculiX s'y interrompt en pleine factorisation, sans message, ce qui a
d'abord ete lu comme la signature d'un systeme quasi singulier — un
quasi-mecanisme qui se calcule mal parce qu'il est un quasi-mecanisme.

**Cette lecture etait fausse**, et le corpus elargi l'a montre : sur 3000 cas,
onze echecs, tous `fbtap` a nouveau. Le message existait, mais partait sur
`stderr`, que `run_fea.py` n'affichait pas. Il dit `fatal error in
GPart_makeYCmap / bad input` : c'est le **partitionneur de graphe de SPOOLES**
qui echoue, pas le systeme qui est singulier. C'est deterministe, insensible au
nombre de fils, et le solveur iteratif de CalculiX resout ces memes cas en une
dizaine de secondes — ce qu'il ne ferait pas d'un systeme reellement singulier.
Reste vrai que l'architecture, elle, n'est pas tiree au hasard : c'est bien la
topologie de la cage ouverte qui met le partitionneur en defaut.

Avec le repli de solveur, le corpus est complet : **3000 cas ecrits, zero echec**.

**Point pour la passe d'entrainement :** le nombre de noeuds varie d'un cas a
l'autre, de 2 389 a 7 461. C'est precisement pourquoi l'exemple crash de
PhysicsNeMo travaille a `batch_size=1`. Il faudra soit accepter cette contrainte,
soit uniformiser le maillage, ce qui appauvrirait le corpus.

Les sections `ASSUMED` de `build_body.py` sont desormais surchargeables par
l'environnement (`BODY_SILL_H`, `BODY_TUN_W`...). Sans surcharge, les valeurs
publiees sont inchangees : le cas de reference redonne bien 2442 N.m/deg.

### Corpus elargi du 2026-09-07, et ce que son audit a trouve

Le corpus a ete refait a 3000 cas apres que le plan d'experiences eut ete corrige
sur deux points (decouplage de G, refus d'une reprise incoherente). Il a ensuite
ete **audite avant tout entrainement**, par `fea/corpus_audit.py`, et l'audit a
coute moins d'une minute de CPU pour ce qu'il a rapporte.

| grandeur | valeur |
|---|---|
| cas demandes / ecrits | 3000 / **3000**, zero echec |
| duree | 1 h 48, quatre coeurs de machine de bureau |
| raideur K | 376 a 44 242 N.m/deg, mediane 5826 |
| noeuds par cas | 2 402 a 7 530 |
| repartition sur sept architectures | 394 a 442 cas, aucun ecart > 2 sigma |

**Trois controles passent.** L'exposant `d ln K / d ln t` vaut 1,00 sur les sept
architectures : la loi d'echelle lineaire en epaisseur est bien dans le corpus.
La somme `d ln K / d ln E + d ln K / d ln G` vaut 1,000 partout, comme l'exige
l'homogeneite de degre 1 de l'elasticite lineaire — un controle, pas un
ajustement. Et l'exposant de G monte de 0,364 sur le plancher nu a 0,631 sur la
cellule fermee : le changement de mecanisme est present.

**Un controle rate, et c'est le plus important.** Cette montee de l'exposant de G
devrait partir de **zero** sur le plancher nu, puisque `dominance_study.py` y
mesure +2,1 % en doublant G. Elle part de 0,364. La cause n'est pas le corpus
mais l'element : le corpus est en **S3 lineaires**, `dominance_study.py` en **S6
quadratiques**, et les S3 attribuent au cisaillement une part de la raideur qui
revient a la flexion. Le README du dossier FEA chiffre l'ecart architecture par
architecture. Un substitut entraine sur ce corpus apprendrait donc, sur les
architectures ouvertes, une repartition flexion / cisaillement fausse — celle-la
meme que le decouplage de G avait pour but de lui enseigner.

**Le corpus contient aussi des valeurs simplement fausses.** L'ajustement
log-lineaire a signale un cas aberrant ; rejoue, il rend 4422 N.m/deg au lieu des
39 269 stockes. Sur 65 cas rejoues au total, deux divergent — l'un d'un facteur
9, l'autre de 2,4 %. Le champ de deplacement stocke est coherent avec la raideur
stockee dans les deux cas : ils viennent du meme solve rate, et **aucun controle
interne ne peut les voir**. `fea/corpus_repair.py` rejoue le corpus et ne
remplace une valeur que si deux calculs independants s'accordent contre elle.

**Le lot de validation est gele** (`corpus/split.json`, 450 cas sur 3000,
stratifie par architecture, graine 20260907). Il a ete tire avant qu'aucun
substitut n'existe, ce qui est le seul moment ou cela veut dire quelque chose :
un lot de test choisi apres coup est une note qu'on se donne a soi-meme.

### Corpus S6, celui qui servira a l'entrainement

Meme graine et meme plan que le corpus S3, donc comparable cas par cas.

| grandeur | corpus S3 | corpus S6 |
|---|---|---|
| cas ecrits | 3000 / 3000 | **3000 / 3000** |
| element | S3 lineaire | **S6 quadratique** |
| duree | 1 h 48 | 2 h 05, en douze tranches |
| taille | 126 Mo | 1,1 Go |
| noeuds par cas | 2 402 a 7 530 | 9 703 a 31 098 |
| K | 376 a 44 242, mediane 5826 | 133 a 33 455, mediane 3983 |
| exposant de G, plancher nu | 0,364 | **0,051** |
| exposant de G, cellule fermee | 0,631 | 0,593 |
| exposant d'epaisseur | 1,00 | 1,14 a 1,22 |

**Le controle qui avait disqualifie le corpus S3 passe.** L'exposant de G sur le
plancher nu vaut 0,051 pour 0,03 attendu de `dominance_study.py`, contre 0,364 en
S3. La repartition flexion / cisaillement est correcte, et le substitut peut
maintenant l'apprendre.

**Un controle nouveau est a lire avec soin.** L'exposant d'epaisseur, exactement
1,00 en S3, vaut 1,10 mesure hors corpus sur cinq epaisseurs, et 1,14 a 1,22 dans
l'ajustement multivarie du corpus. La structure ne travaille pas en flexion de
plaque — 1,10 reste tres loin de 3 — mais l'exactitude de la loi lineaire etait
une propriete de l'element lineaire, pas de la structure. Le README du dossier
FEA porte le detail et la consequence sur la question 0,8 / 1,0 mm.

Le corpus S3 reste comme terme de comparaison sur l'effet de l'ordre d'element,
et pour rien d'autre.

**Reste a faire quand l'acces GPU sera la** — et rien de tout cela n'est bloquant
aujourd'hui : conversion du corpus vers VTP ou Zarr par PhysicsNeMo-Curator,
choix d'architecture, entrainement, et surtout **validation du substitut contre
des cas CalculiX tenus hors apprentissage**. Un substitut non valide n'a pas plus
de valeur qu'une image de rendu.

## 4. Omniverse : visualisation et assemblage, pas physique

Omniverse et la chaine SimReady servent au contexte visuel, a l'assemblage USD et
au rendu. **Ils ne demontrent aucun comportement physique.** Le dossier 917 porte
deja cette regle mot pour mot : « un rendu OVRTX, une photo ou un film ne demontre
ni comportement physique, ni puissance, ni tenue thermique, ni aptitude a la
fabrication ».

Elle vaut a l'identique ici, et davantage : une belle image de monocoque est
exactement le genre de preuve que ZESAD ne fournit pas, et que nous avons choisi
de ne pas opposer. Statut des images : les quatre images `simready-*` ne sont pas
autorisees tant que leurs smoke tests ne sont pas verts.

Usage utile et honnete : montrer le reseau de datums cale sur le scan, visualiser
les chemins d'effort issus de CalculiX, presenter l'assemblage. Jamais comme
argument structurel.

## 5. Ordonnancement

| etape | outil | GPU | bloque par |
|---|---|---|---|
| raideur, drapage, architecture | CalculiX | non | rien — **disponible maintenant** |
| plan d'experiences, corpus | CalculiX en parallele | non | parametrisation figee |
| **generation du corpus** | **CalculiX, CPU** | **non** | **fait le 2026-09-07 : 3000 cas S3 audites, corpus S6 en cours** |
| substitut de conception | PhysicsNeMo | oui, Vast.ai | corpus + smoke GPU du conteneur |
| choc | OpenRadioss | non | geometrie, donc M1 |
| correlation choc | essais physiques | — | rien ne les remplace |
| visualisation, assemblage | Omniverse / USD | oui | smoke tests des images |

**Rien dans cette chaine n'est actuellement bloque par un manque de logiciel, sauf
le choc.** Ce qui bloque est ailleurs : le reseau de datums, et l'absence de
denominateur mesure. Ajouter des solveurs maintenant n'avancerait pas le
programme d'une journee.
