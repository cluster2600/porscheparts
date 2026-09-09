# Monocoque 964/993 — concept d'architecture et strategie de drapage

Statut : **concept**. Aucune geometrie, aucune cote de piece, aucun drapage
executable. Classe `prohibited_pending_engineering` inchangee.

Ce document contient le travail de conception qui **ne depend d'aucune inconnue
du reseau de datums** — topologie, chemins d'effort, orientation des plis — et
qui pouvait donc etre fait avant le relevé de marbre. Les interfaces, elles, sont
declarees en parametres dans `twins/964-chassis/source/monocoque_interface.py`.

## 1. Ce que le monocoque doit faire, d'apres nos propres mesures

`twins/964-chassis/fea/README.md` etablit trois choses qui commandent la forme.

**La raideur suit l'epaisseur lineairement, pas son cube** (1,251 pour 1,250).
Cela ecarte la flexion de plaque, mais PAS la flexion de poutre a paroi mince :
voir section 3bis, ou la mesure montre que le plancher seul travaille en flexion
et non en cisaillement, contrairement a ce que le dossier affirmait.

**Ce qui paie est la fermeture des anneaux, pas la matiere.** Du plancher nu a la
cellule fermee, K x 3,7. Mais le cadre de pare-brise, 1,1 kg, rapporte 172 a
191 fois plus au kilo que le pavillon, 10,5 kg ; et les pieds milieu ajoutes
seuls, sans rien pour fermer a l'avant, rapportent zero pour 7,5 kg.

**Le carbone est le levier faible.** x 1,25 a masse egale, contre x 1,51 pour
fermer le caisson.

Conclusion de conception : **un monocoque n'est pas une caisse en carbone, c'est
une caisse dont les anneaux sont fermes par construction.** Le materiau vient
apres. C'est aussi ce qui rend le concept defendable face a ZESAD sans avoir
acces a leur produit : l'argument est structurel, pas commercial.

## 2. Les anneaux, par ordre de rendement

L'architecture se definit comme un jeu d'anneaux fermes relies par des poutres
longitudinales. Ordre etabli par `ring_study.py` et `body_study.py` :

| anneau / element | fonction | rendement mesure |
|---|---|---|
| cadre de baie de pare-brise | ferme la cellule en haut a l'avant | **le plus eleve de tout le modele** |
| tunnel central ou poutre longitudinale equivalente | relie les deux anneaux de bout | +71 % a lui seul |
| passages de roue | prolongent le longeron en hauteur aux extremites | eleve |
| tablier et cloison arriere | ferment le caisson en bout | moyen |
| pieds milieu et brancards | ne valent que si un anneau se ferme | nul isole |
| pavillon | remplit une surface deja portee | quasi nul |

Deux consequences qui vont a l'encontre de l'intuition « monocoque = coque » :

- **le pavillon n'est pas une piece structurale** a ce niveau de chargement. Il
  peut etre mince, amovible, ou vitre, sans perte notable de raideur en torsion.
  C'est une liberte de conception, et elle est gratuite ;
- **les pieds milieu ne se dimensionnent pas isolement.** Ils ne servent que
  comme montant d'un anneau ferme. Un pied milieu massif sans cadre de baie est
  de la masse morte, mesuree comme telle.

**Reserve.** Le modele qui produit ce classement n'a ni vitrage colle, ni portes,
ni ouvertures de panneaux. Ces trois absences flattent toutes l'anneau ferme. Le
classement est robuste — verifie a trois finesses de maillage — mais les
rapports le sont moins que l'ordre.

## 3. Le drapage : resultat corrige apres verification

**Une premiere version de cette section annoncait un gain de x 1,75 pour un
drapage +/-45. Ce chiffre est faux et il est retire.** Il valait comme prediction
analytique — un empilement +/-45 rend bien 1,75 fois le module de cisaillement
d'un quasi-isotrope — mais l'hypothese qui le transportait jusqu'a la caisse,
« cette structure travaille en cisaillement », s'est revelee fausse. Voir
section 3bis.

Le calcul par elements finis est desormais possible : `run_fea_laminate.py`
resout un vrai stratifie multicouche (`*SHELL SECTION, COMPOSITE`, une
`*ORIENTATION` par pli et par famille de panneaux). La chaine est validee sur un
cas analytique — traction uniaxiale sur pli UD, `verify_laminate_shear.py` et le
controle uniaxial — qui redonne E1 a 0 degre, E2 a 90 et la valeur hors axe a 45,
a 3 % pres.

Meme masse, huit plis de 0,4 mm, memes conditions aux limites :

| empilement | plancher seul (ouvert) | cellule fermee |
|---|---|---|
| quasi-isotrope | 1586 | 6311 |
| **+/-45** | 696 (**0,44x**) | **6849 (1,09x)** |
| 0/90 | 1910 (1,20x) | 4043 (0,64x) |

**Le classement s'inverse entre l'architecture ouverte et l'architecture
fermee.** Sur le plancher seul, +/-45 perd plus de la moitie de la raideur. Sur
la cellule fermee il gagne, mais de 9 % — pas de 75 %.

Ce que cela veut dire pour le drapage :

- **il n'y a pas d'empilement universellement bon** pour cette caisse. Un pli
  n'est bon que relativement au chemin d'effort du panneau qui le porte ;
- **+/-45 dominant seulement dans les panneaux reellement en cisaillement** —
  flancs de longeron d'une section fermee, ames de cloison — et seulement une
  fois les anneaux fermes ;
- **0/90 la ou l'effort est axial** : semelles de longeron, bordures, chemins de
  flexion, entourage des points durs ;
- **le quasi-isotrope reste un compromis raisonnable par defaut**, ce qui est un
  resultat en soi : il n'est pas le mauvais reglage que cette section annoncait.

Le drapage zone reste le vrai levier du procede, mais son gain se chiffre en
dizaines de pourcents, pas en facteurs, et il demande de connaitre le chemin
d'effort panneau par panneau — ce que le modele actuel ne resout pas.

## 3bis. Cette caisse ne travaille pas en cisaillement, sauf une fois fermee

Le dossier affirmait « caisson en cisaillement de membrane, le critere est
`G/rho` et non `E/rho` ». Cette affirmation reposait sur deux observations dont
aucune ne la demontre :

- la raideur suit lineairement l'epaisseur et non son cube. Cela ecarte la
  flexion de **plaque**, mais pas la flexion d'une **poutre a paroi mince**, dont
  l'inertie varie elle aussi lineairement avec l'epaisseur ;
- la prediction iso-raideur en changeant de materiau tombait a 6,9 %. Mais tous
  les materiaux compares etaient isotropes, donc `G` proportionnel a `E` : ce
  controle ne peut pas, par construction, distinguer l'un de l'autre.

`dominance_study.py` tranche en faisant varier `E` et `G` **separement**, avec un
materiau orthotrope fictif ou les deux sont decouples :

| architecture | doubler E | doubler G | mecanisme |
|---|---|---|---|
| plancher, longerons, traverses | **+93,8 %** | +2,1 % | flexion, quasi pure |
| cellule fermee | +37,7 % | **+56,9 %** | cisaillement dominant, mais mixte |

**Le plancher seul ne travaille pas du tout en cisaillement.** En torsion, ses
deux longerons flechissent en sens opposes : ce sont deux consoles, et le critere
y est `E`. Le cisaillement n'apparait qu'une fois les anneaux fermes, et il ne
devient jamais exclusif.

C'est la meme decouverte que la fermeture des anneaux, vue par un autre bout :
**fermer un anneau ne fait pas qu'ajouter de la raideur, cela change le mecanisme
qui la porte.** Et cela explique exactement l'inversion du tableau de drapage
ci-dessus.

Consequence sur les conclusions materiau : pour le plancher seul, le critere est
`E/rho`, non `G/rho`. Le classement carbone > aramide n'en est pas affecte, le
carbone dominant sur les deux criteres.

## 4. La question du cadre de baie en acier

ZESAD vend une configuration « monocoque avec cadre de baie en acier ». Notre
propre classement place le cadre de baie au premier rang du rendement. Trois
lectures possibles, non exclusives, aucune confirmee :

1. **structurelle** : c'est l'anneau le plus charge, et un stratifie y tient mal
   des efforts concentres et un collage de vitrage ;
2. **procede** : la baie exige une precision de forme que le composite grand
   format tient difficilement sans reprise d'usinage ;
3. **identite du vehicule** : conserver un element d'origine peut servir la voie
   d'homologation, voir `MONOCOQUE_964_993_PROGRAMME.md` section 7.

Cette question doit etre tranchee tot : elle change la nature du produit, son
outillage et probablement son dossier reglementaire. Elle se tranche par la
lecture 3 en premier, qui est juridique et peu couteuse.

## 5. Ce qui reste indetermine, et ce qui le debloque

| indetermine | debloque par |
|---|---|
| positions d'interface suspension et moteur | relevé de marbre (M1) |
| entraxe P5 -> P12, cote gouvernante | relevé de marbre (M1) |
| cible de raideur en valeur absolue | essai de torsion caisse donneur (M2) |
| chemin d'effort panneau par panneau, pour zoner le drapage | modele a sections reelles, non disponible |
| efforts d'introduction aux points durs | modele de chargement vehicule, non commence |
| tenue au choc | essais physiques, non substituables |

## 6. Ce que ce document n'est pas

- Ce n'est pas une conception : ni cote, ni epaisseur, ni sequence d'empilement.
- Le x 1,75 annonce en premiere version etait faux : voir section 3.
- Le classement des anneaux vient d'un modele aux sections `ASSUMED` et non
  converge en maillage. Seuls l'ordre et les ordres de grandeur sont exploitables.
- Rien ici ne concerne la tenue au choc, la resistance, le delaminage, le
  flambement, la fatigue ni le feu.
