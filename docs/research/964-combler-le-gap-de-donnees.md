# Combler le gap de donnees du jumeau 964 : etat des pistes au 2026-09-04

Deux verrous bloquent le dossier. Ce document dit ce qui a ete essaye, ce qui est
ferme, et ce qui reste a faire — en distinguant ce qui depend de nous de ce qui
depend d'un tiers.

## Verrou A : le calage longitudinal du reseau de datums

### Le diagnostic a change

La recherche du point 17 sur le scan a echoue, et le README du jumeau en conclut
qu'il faut « localiser un point de datum publie ». C'est vrai, mais la formulation
masque le vrai probleme : **ce n'est pas un trou qu'il faut, c'est une cote**.

Les entites les mieux localisees du scan ne sont pas les percages — le scan ne les
resout pas, resultat negatif solidement etabli — ce sont les **centres de roue**,
reproductibles a +/- 7 mm et robustes au rayon de pneu. Ce qui manque n'est donc
pas une feature, c'est **une seule cote longitudinale publiee entre un point de
datum et une ligne d'essieu**. Le volume IV a ete relu ligne a ligne le
2026-09-04 : il ne la donne pas. Il donne des hauteurs au sol, pas des stations.

### Une piste dormante, deja dans le depot

`SRC-RENNLIST-993-BODY-DIMENSIONS-PDF` signale trois pieces jointes non obtenues,
dont un « Porsche 993 body measurement PDF » annonce comme un **tableau de points
en millimetres**. C'est exactement l'objet manquant, et il concerne la 993.

Or un recoupement fait le 2026-09-04 rend cette piste bien meilleure qu'elle n'en
avait l'air. `SRC-RENNLIST-993-JACKING-POINT-DISCREPANCY` rapporte, pour une 993,
une distance avant-arriere entre points de levage de **1245 mm**. C'est, au
millimetre pres, la cote **R du manuel 964**, publiee a 1245 +/- 2 mm entre P17 et
P18. Une source independante et non-Porsche reproduit donc la transcription du
volume V, et surtout **964 et 993 partagent l'entraxe longitudinal des points de
levage**. Un tableau de points 993 serait donc, au moins en partie,
transferable — et le depot est deja oriente 993.

C'est la piste la moins couteuse du dossier et elle n'a jamais ete poussee.

### Editeurs de donnees de marbre

| editeur | statut | remarque |
|---|---|---|
| Celette | ferme | jeu 564.320 specifique 964, 42 points, documentation sous authentification |
| Car-O-Data | identifie | jamais sollicite |
| **Autorobot** | **nouveau, 2026-09-04** | voir `SRC-AUTOROBOT-MEASURING-DATA-SERVICE` |
| Spanesi, Josam, Globaljig, Blackhawk, Chief | non essayes | |

Autorobot est le meilleur des trois connus pour une raison precise : ses fiches
contiennent des **photographies des points de mesure**. L'echec du recalage vient
de l'impossibilite d'associer un point de datum publie a une entite physique du
scan ; une photographie leve exactement cette ambiguite. Autorobot decrit aussi sa
methode — relevé sur vehicules non accidentes bridés sur banc — et diffuse des
fiches unitaires en PDF et en format ADF, donc **une fiche est un objet qui se
demande**. Acces par abonnement, pas de base publique, couverture des millesimes
1989-1994 non annoncee. Contact usine publie.

**La voie realiste, pour les trois editeurs, est la meme : un atelier abonne, ou
une demande de fiche unitaire au titre d'un projet de documentation. Pas un
abonnement.**

### Homologation FIA

Piste neuve et gratuite : la 964 Cup et la Carrera RS ont ete homologuees, la RS
N/GT au 2 mars 1992. La base `historicdb.fia.com` porte une entree
`porsche-carrera-rs`. **Elle renvoie 403 a toute lecture automatisee** : elle doit
etre ouverte dans un navigateur. Reserve a poser d'emblee : une fiche
d'homologation donne des cotes d'encombrement, un empattement, des voies et parfois
un plan cote, mais **rarement des coordonnees de points de caisse**. Piste a cout
nul, rendement incertain.

### Ce qui a ete verifie et acquis le 2026-09-04

- **Troisieme controle d'echelle, independant.** Longueur hors-tout du scan dans
  le repere vehicule : **4282,4 mm** contre **4275 mm** au catalogue 964, soit
  **+7,4 mm ou +0,17 %**. Meme signe et meme ordre que l'ecart d'empattement de
  +0,27 %. Ne cale rien en X — les extremites sont des peaux de pare-chocs et non
  des plans de reference — mais confirme que le repere est sain.
- **Un bug de repere corrige.** `wheel_fits.npy` etait en coordonnees scan et
  incombinable avec `verts_vehicle.npy`. Voir `source/wheels_vehicle.py`.
- **Le soubassement est plat.** Voir `source/tunnel_probe.py` et l'etude
  composite : pas de tunnel central sur la 964.

### Reste a faire, non fait ici

- **Un second scan, carrosserie de serie.** Le scan actuel est une carrosserie
  large probablement modifiee, qui masque les bas de caisse d'origine. Depend d'un
  contributeur.
- **Le relevé de marbre.** Depend d'un tiers. C'est l'item le plus decisif.

## Verrou B : la raideur en torsion d'une caisse 964 complete

### Ce verrou a ete contourne, pas ouvert

La bonne nouvelle est qu'il **n'a plus a etre ouvert pour l'essentiel**.
L'affirmation a tester — « le levier d'un monocoque est architectural » — est
relative, donc elle se mesure sans aucun denominateur exterieur. C'est fait :
voir `docs/research/964-chassis-carbone-kevlar.md`. Un fil germanophone consulte
le meme jour fait d'ailleurs remarquer que les constructeurs eux-memes ne
publient que du relatif, faute de protocole normalise.

### Ce que la recherche du 2026-09-04 a donne

Recherche germanophone ciblee sur `Verwindungssteifigkeit` et
`Torsionssteifigkeit`, non couverte par la campagne du 2026-09-03 : **aucune
valeur d'usine**. Le fil PFF « Karosseriesteifigkeit » n'en donne aucune et
explique pourquoi.

Un seul chiffre a emerge, et il est mauvais : **964 Carrera coupe environ 11 563
N.m/deg**, 993 environ 13 876. Voir `SRC-RENNLIST-911-TORSIONAL-RIGIDITY-LIST`.
L'auteur les presente lui-meme comme des valeurs « qui circulent en ligne », sans
source primaire, sans protocole, et sans dire s'il s'agit de caisse en blanc ou de
vehicule complet. **A ne pas utiliser comme reference.** Consigne uniquement pour
que la recherche ne soit pas refaite.

### Reste a faire, non fait ici

- Dossier de presse Porsche de 1988 et litterature SAE de benchmarking de caisses.
- Preparateurs restomod : recherche faite sur Tuthill, aucun chiffre publie trouve.
- **Etendre le modele coque** au pavillon, aux pieds milieu, aux passages de roue
  et au cadre de pare-brise. Ne demande aucune donnee exterieure, seulement des
  sections `ASSUMED` supplementaires, et ferait converger le modele vers une
  caisse. C'est la suite naturelle de l'etude d'architecture.

## Priorites

1. **Le tableau de points 993 de Rennlist.** Gratuit, deja identifie dans le
   depot, et le recoupement a 1245 mm le rend transferable a la 964.
2. **Une demande de fiche unitaire a Autorobot**, en invoquant les photographies
   de points de mesure. Gratuit a demander.
3. **La base FIA**, a ouvrir dans un navigateur.
4. **Etendre le modele coque.** Entierement sous notre controle.
5. Le relevé de marbre et le scan de serie, qui dependent de tiers et restent les
   deux items decisifs.
