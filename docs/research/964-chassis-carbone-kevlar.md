# Chassis carbone/kevlar pour 964 : ce que le calcul dit du remplacement de l'acier

Statut : **etude de materiau, classe `prohibited_pending_engineering`**. Aucune
geometrie de piece, aucune sequence de drapage liberable. Voir `SAFETY.md` : une
structure autoportante porte la retenue des occupants, elle ne se publie qu'apres
revue d'ingenierie formelle.

## Point de depart

`SRC-ZESAD-CARBON-MONOCOQUE-964-993` etablit qu'un monocoque carbone de
remplacement pour 964 et 993 existe commercialement, de 129 990 a 219 990 EUR, en
preimpregne cuit en autoclave. La fiche ne publie **ni masse, ni raideur en
torsion, ni essai de choc, ni homologation, ni sequencement de drapage, ni
materiau d'ame**. Il n'y a donc rien a reproduire ni a confronter : la seule
chose faisable ici est de poser la question par le calcul, sur le modele qu'on a.

## Methode

L'essai est celui, deja en place, du plancher 964 en torsion (`fea/README.md`) :
arriere encastre, couple de 1290 N.m en pointes de longeron, coques S3, CalculiX.
**Ni la geometrie, ni le chargement, ni les conditions aux limites ne changent.**
Seuls le materiau et l'epaisseur changent. La reference est l'acier a 0,8 mm,
2442 N.m/deg — valeur reproduite a l'identique avant toute modification.

Les proprietes de stratifie ne sont pas affirmees, elles sont **calculees**
depuis les constantes de pli unidirectionnel par les invariants de stratifie
(`fea/laminate.py`). Un empilement quasi-isotrope a une matrice de raideur
membranaire A isotrope, ce qui autorise a garder la coque isotrope dans le calcul
et reduit les entrees aux seules constantes de pli. Le module verifie sa propre
algebre : l'empilement QI d'un pli isotrope doit redonner ce meme materiau.

Le carbone QI ressort a **E = 52 401 MPa**, ce qui est la valeur de manuel pour
un T300/epoxy quasi-isotrope. L'hybride carbone/aramide est obtenu par melange
des Q au prorata des plis, ce qui est exact pour A.

## Resultat, a raideur en torsion egale

| materiau | E (MPa) | G (MPa) | epaisseur iso-raideur | plis | K calcule | vM p99 | kg/m2 | vs acier |
|---|---|---|---|---|---|---|---|---|
| acier 0,8 mm (reference) | 210 000 | 80 769 | 0,80 mm | — | 2442 | 69,6 | 6,28 | 1,00x |
| carbone QI | 52 401 | 19 992 | 3,23 mm | 16 | 2503 | 17,0 | 5,17 | **0,82x** |
| hybride carbone/aramide 50/50 QI | 40 669 | 15 447 | 4,18 mm | 20 | 2538 | 13,0 | 6,23 | **0,99x** |
| aramide QI | 28 931 | 10 902 | 5,93 mm | 24 | 2611 | 9,0 | 8,18 | **1,30x** |

Epaisseur de pli cuit prise a 0,25 mm, valeur de travail `ASSUMED`, nombre de
plis arrondi au multiple de 4 qu'exige un empilement QI symetrique.

## Ce qu'il faut en retenir

**Le kevlar est le mauvais materiau pour cette fonction.** A raideur en torsion
egale, un stratifie aramide quasi-isotrope est **30 % plus lourd que l'acier**.
Ce n'est pas une surprise une fois le calcul pose : l'aramide a un module
specifique mediocre. Son interet reel est la tolerance aux dommages, la
resistance a la penetration et le comportement en absorption, pas la raideur.
S'il a une place dans un chassis, c'est en peau sacrificielle locale ou en
couche anti-eclat, **pas dans le chemin d'effort en torsion**.

**Le gain du carbone monolithique est modeste : 18 %.** C'est tres loin de ce que
le mot « carbone » laisse attendre. La raison est mecanique et deja etablie par
ce depot : ce caisson travaille en **cisaillement de membrane**, donc la raideur
suit `G x t` et non `G x t^3`. Le critere qui compte n'est pas le module
specifique `E/rho` mais `G/rho`, et l'ecart y est bien plus faible qu'en flexion.
L'ecart maximal entre l'epaisseur predite par cette loi et le calcul complet est
de 6,9 %, ce qui confirme la loi d'echelle en materiau comme elle l'etait en
epaisseur.

**Une ame en nid d'abeille ne rattrape pas ce resultat en torsion.** Pour un
caisson ferme, la formule de Bredt donne une raideur proportionnelle a `G x t`,
a l'aire enclose au carre et a l'inverse du perimetre : le flux de cisaillement
est porte par les peaux, et separer les peaux par une ame n'augmente pas le
produit `G x t` disponible. Le sandwich achete de la raideur de **flexion de
panneau** et de la tenue au **flambement local**, qui sont des criteres reels et
dimensionnants ailleurs, mais il ne multiplie pas la raideur en torsion du
caisson.

**Le vrai levier n'est pas le materiau, c'est l'architecture.** Les colonnes
`vM p99` le montrent : l'acier de reference plafonne a 86 MPa au pic pour une
limite d'elasticite d'au moins 200 MPa meme en acier doux, et les stratifies
iso-raideur descendent a 9-19 MPa. **Le plancher n'est pas dimensionne par la
contrainte en torsion.** Son epaisseur vient de la raideur, de l'emboutissage, de
la tenue au choc local et de la corrosion. Un echange de materiau a iso-raideur
ne convertit donc aucune marge en masse.

Ce qu'un monocoque de type ZESAD gagne vient d'ailleurs : une coque fermee unique
au lieu d'un assemblage soude par points, une aire enclose plus grande, la
suppression des recouvrements et des joints, et la liberte de mettre la matiere
ou le chemin d'effort passe au lieu de la mettre ou l'emboutissage l'autorise.
**Rien de cela ne se demontre sur un plancher seul** : il y faudrait le tablier,
la cloison arriere, le tunnel, les passages de roue, les pieds milieu et le cadre
de pare-brise, qui portent l'essentiel de la torsion d'une caisse complete et
qu'aucune source du dossier ne cote.

## Architecture contre materiau : la question est tranchee

L'affirmation « le levier est architectural » etait, dans la premiere version de
ce document, un raisonnement. Elle est maintenant mesuree. L'astuce est qu'elle
est **relative** : elle ne demande donc aucune raideur de caisse 964 publiee, ce
qui tombe bien puisqu'il n'en existe pas.

Meme essai de torsion, trois architectures de plus en plus fermees, deux
materiaux **a masse egale** — le stratifie carbone est mis a 3,92 mm pour peser
exactement ce que pese l'acier a 0,8 mm. La grandeur comparee est la raideur
specifique `K/m`.

| architecture | materiau | aire | masse | K (N.m/deg) | K/m |
|---|---|---|---|---|---|
| plancher seul | acier 0,8 mm | 4,40 m2 | 27,7 kg | 2442 | 88,3 |
| plancher seul | carbone QI 3,92 mm | 4,40 m2 | 27,7 kg | 3062 | 110,7 |
| + cloisons | acier 0,8 mm | 5,60 m2 | 35,2 kg | 3147 | 89,4 |
| + cloisons | carbone QI 3,92 mm | 5,60 m2 | 35,2 kg | 3914 | 111,2 |
| + cloisons + tunnel | acier 0,8 mm | 6,40 m2 | 40,2 kg | 5371 | 133,6 |
| + cloisons + tunnel | carbone QI 3,92 mm | 6,40 m2 | 40,2 kg | 6620 | 164,7 |

Ces masses ont ete corrigees le 2026-09-04. Une traverse du modele, placee
derriere le bord arriere du plancher par la chaine de datums non calee, y
flottait : elle comptait 1,66 kg sans porter aucun effort, et minorait donc
toutes les raideurs specifiques. Les raideurs, elles, etaient justes. Voir
`twins/964-chassis/fea/README.md`.

Les deux leviers, a masse egale :

| levier | gain en K/m |
|---|---|
| **fermer la caisse**, a acier constant | **x 1,51** |
| **passer au carbone**, a plancher seul | **x 1,25** |
| les deux ensemble | x 1,86 |

**L'architecture rapporte donc environ 20 % de plus que le materiau**, et surtout
les deux leviers **se multiplient presque exactement** : 1,51 x 1,25 = 1,89
contre 1,86 mesure. Ils sont separables, ce qui veut dire qu'ils ne se
substituent pas l'un a l'autre. Choisir le carbone ne dispense pas de fermer la
caisse, et fermer la caisse ne rend pas le carbone inutile.

Le detail est instructif : l'essentiel du gain architectural ne vient pas des
cloisons mais du **tunnel central**, qui a lui seul fait passer la raideur de
3147 a 5371 N.m/deg, soit +71 %. Une poutre longitudinale fermee sur toute la
longueur vaut plus que deux cloisons en bout.

**Et ce tunnel n'existe pas sur la 964.** Ce parametre etant le plus influent de
tout le dossier, il ne pouvait pas rester `ASSUMED` : il a ete cherche sur le
scan (`source/tunnel_probe.py`). Le relief central du plancher d'habitacle, pris
comme l'ecart entre le Z median a |Y| < 60 mm et celui des flancs a
250 < |Y| < 400 mm, vaut entre **-0,7 et -3,1 mm** sur huit stations couvrant
1000 mm de long. C'est sous le residu de symetrie du scan, qui est de 7,54 mm
RMS : le relief n'est meme pas distinguable du bruit. Le soubassement est plat,
ce qui est coherent avec un moteur arriere et l'absence d'arbre de transmission
longitudinal. En avant de X = -200 mm un creux apparait, mais c'est la zone de
traverse et de train avant, pas un tunnel.

Le cas « tunnel » mesure donc **ce que la 964 n'a pas**, non ce qu'elle a. Cela
ne l'invalide pas, cela le requalifie : c'est le chiffrage d'une modification
architecturale possible, et c'est la conclusion la plus actionnable de l'etude.
**Ajouter une poutre longitudinale fermee rapporte plus que passer au carbone**,
+71 % contre +25 %, et pour une masse bien moindre que le passage au composite de
toute la caisse. Un monocoque de type ZESAD, lui, obtient cette poutre gratuitement
par construction : c'est precisement cela, un gain architectural.

Deux controles de coherence entre les deux etudes. A masse egale, le carbone
donne x 1,25 ; a raideur egale, il donnait 0,82x la masse, soit 1/0,82 = 1,22.
Les deux lectures concordent. Et le cas « plancher seul, acier » redonne 2442
N.m/deg, la valeur d'origine : la refonte du script de geometrie est fidele.

**Reserve majeure.** Les cloisons, leur hauteur de 500 mm et la section de
tunnel 180 x 120 mm sont `ASSUMED` : aucune n'est publiee. Les valeurs absolues
du tableau ne sont donc pas des raideurs de 964. **Seuls les rapports comptent**,
et ce sont eux qui repondent a la question posee.

Le pavillon, les pieds milieu, les passages de roue et le cadre de pare-brise
manquaient egalement a cette etude. Ils ont depuis ete ajoutes au modele, et le
resultat renforce la conclusion de cette page plutot qu'il ne la nuance : du
plancher nu a une cellule fermee, la raideur est multipliee par 3,7, et ce qui
porte ce gain n'est pas la quantite de matiere ajoutee mais la fermeture des
anneaux. Le cadre de pare-brise, 1,1 kg, rapporte deux ordres de grandeur de
plus au kilo que le pavillon, 10,5 kg. Voir
`twins/964-chassis/fea/README.md`.

## Correction du 2026-09-04 : le critere n'est pas `G/rho` pour le plancher

Cette page conclut a plusieurs reprises que « ce caisson travaille en
cisaillement de membrane, donc le critere est `G/rho` et non `E/rho` ». **Cette
lecture mecanique est fausse et elle est corrigee ici.**

Elle s'appuyait sur deux observations dont aucune ne la demontre : la raideur
suit lineairement l'epaisseur, ce qui ecarte la flexion de plaque mais pas celle
d'une poutre a paroi mince ; et la prediction iso-raideur tombe a 6,9 %, mais
tous les materiaux compares sont isotropes, ou `G` est proportionnel a `E`, si
bien que ce controle ne peut pas distinguer l'un de l'autre.

En faisant varier `E` et `G` separement (`fea/dominance_study.py`), on mesure
que doubler `E` rend **+93,8 %** sur le plancher seul quand doubler `G` ne rend
que **+2,1 %** : cette architecture-la travaille en **flexion**. Le cisaillement
ne devient dominant qu'une fois les anneaux fermes, ou la cellule complete donne
+37,7 % et +56,9 %.

**Ce qui reste valide dans cette page :** tous les chiffres. Ils portent sur des
materiaux isotropes, calcules a iso-raideur par un calcul complet, et le
mecanisme sous-jacent ne change pas leur valeur. Le classement carbone devant
aramide est inchange, le carbone dominant sur les deux criteres.

**Ce qui tombe :** la justification par `G/rho`, et avec elle l'idee qu'un
drapage oriente cisaillement serait le bon reglage par defaut. Le calcul
stratifie complet, desormais possible, montre que le classement des empilements
**s'inverse selon l'architecture**. Voir `docs/MONOCOQUE_964_993_ARCHITECTURE.md`.

## Ce que cette etude n'est pas

- **Ce ne sont pas des raideurs de caisse 964.** Le modele est un plancher, deux
  longerons, deux traverses. 2442 N.m/deg n'est pas une valeur de vehicule et
  n'a jamais pu etre confronte a une valeur d'usine : aucune n'est publiee.
- **Seule la raideur est traitee.** Rien ici ne dit quoi que ce soit de la
  resistance du stratifie, du delaminage, des assemblages colles — qui sont le
  point faible reel d'un monocoque composite —, du flambement, de la tenue au
  choc, du comportement au feu, de la fatigue ni du vieillissement. Un critere de
  rupture composite n'est pas une contrainte de von Mises.
- **Les constantes de pli sont de classe manuel, niveau de preuve D.** Elles ne
  sont certifiees par aucun fournisseur. Une fraction volumique de fibres reelle,
  un taux de porosite et un cycle de cuisson les deplaceraient.
- **La geometrie reste non calee.** Le calage longitudinal du reseau de datums du
  jumeau 964 n'est pas resolu, les sections de longeron et de traverse sont
  `ASSUMED`. Aucune piece composite ne peut en sortir.
- **Aucun controle physique.** Conformement a la charte du depot, rien n'a ete
  pese ni mesure sur un vehicule.

## Prochaine donnee utile

Inchangee, et c'est le meme verrou que pour le reste du jumeau : **localiser un
seul point de datum publie** a mieux que sa tolerance calerait la chaine
longitudinale. Sans cela, l'etude de materiau ci-dessus reste ce qu'elle est —
une comparaison correcte sur une geometrie approximative.

Pour l'axe composite specifiquement, la donnee qui manque est une **raideur en
torsion de caisse 964 complete**, mesuree ou publiee. Elle donnerait enfin un
denominateur : sans elle, on sait comparer des materiaux entre eux, mais pas dire
ce qu'un monocoque apporterait a la voiture.

## Reproduire

    source twins/964-chassis/source/env.sh
    cd twins/964-chassis/fea
    pycad laminate.py                          # proprietes QI et auto-verification
    pycad build_shell.py 0.8 1.0
    pycad composite_study.py                   # tableau iso-raideur ci-dessus
    pycad architecture_study.py                # ablation architecture / materiau
