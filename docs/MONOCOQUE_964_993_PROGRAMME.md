# Programme monocoque carbone 964/993 — definition

Statut : **definition de programme**. Ce document ne contient aucune geometrie et
n'en autorise aucune. Il dit ce qu'il faut etablir, dans quel ordre, et ce qui
bloque aujourd'hui.

Objectif vise : un monocoque carbone de remplacement pour restomod 964 et 993,
alternative a l'offre `SRC-ZESAD-CARBON-MONOCOQUE-964-993`, industrialise en
Chine.

Cet objectif **contredit le perimetre ecrit** de `ROADMAP.md`, qui classe le
remplacement de la structure autoportante en « hors perimetre initial ». Le
perimetre est une decision du proprietaire du projet, pas une conclusion
technique ; il doit etre modifie explicitement si ce programme est retenu, et non
contourne en silence. Les portes de `SAFETY.md` et `QUALITY_GATES.md`, elles, ne
sont pas des choix de perimetre : voir la section « Portes de securite ».

## 1. L'axe de differenciation est documentaire, pas materiel

La fiche ZESAD annonce un monocoque carbone preimpregne cuit en autoclave, en
deux configurations, de 129 990 a 219 990 EUR. Elle **ne publie ni masse, ni
raideur en torsion, ni essai de choc, ni homologation, ni partenaire
d'ingenierie, ni sequence de drapage, ni materiau d'ame**. Le site de la societe
non plus.

C'est la faiblesse exploitable, et elle est structurelle : pour une piece qui
porte la retenue des occupants, l'absence de donnee publiee **est** le defaut du
produit. Un concurrent qui publie masse, raideur mesuree, protocole, essais et
voie d'homologation se differencie sur le seul axe ou l'offre en place est nue,
et le fait sans avoir a etre moins cher.

Ce depot est deja outille pour exactement cela : fiches sourcees, niveaux de
preuve, portes qualite, refus documente d'affirmer au-dela des preuves. **La
methode du depot est le produit.** C'est un avantage reel et il ne se copie pas
vite.

Consequence de conception : tout ce qui suit est organise pour produire des
preuves publiables, pas seulement une piece.

## 2. Ce que le depot a deja etabli, et qui porte sur le produit

Trois resultats acquis (voir `twins/964-chassis/fea/README.md`) commandent
l'architecture. Ils sont **relatifs**, donc valides malgre des sections `ASSUMED`.

**Le carbone est le levier faible.** A masse egale, passer au carbone quasi-
isotrope vaut x 1,25 en raideur specifique. Fermer le caisson vaut x 1,51. Les
deux se multiplient. Un monocoque ne gagne pas parce qu'il est en carbone : il
gagne parce qu'il obtient les fermetures **par construction**, en une piece, sans
les compromis d'assemblage d'une caisse en tole soudee.

**La fermeture des anneaux domine tout.** Du plancher nu a une cellule fermee,
K x 3,7. Le classement ne suit pas la masse : le cadre de pare-brise, 1,1 kg,
rapporte 172 a 191 fois plus au kilo que le pavillon, 10,5 kg. Les pieds milieu
et brancards, ajoutes seuls sans rien pour fermer a l'avant, rapportent zero pour
7,5 kg. Verifie a trois finesses de maillage.

**Corollaire produit, et lecture de l'offre concurrente.** ZESAD vend une
configuration « monocoque avec cadre de baie en acier ». Notre propre calcul dit
que le cadre de baie est l'element le plus rentable de toute la caisse. Mettre de
l'acier precisement la est donc defendable, et probablement pas un compromis
esthetique : c'est l'anneau le plus charge, celui ou un composite stratifie tient
le moins bien les efforts concentres et le collage du vitrage. **Hypothese, a
verifier** — la fiche ne dit pas pourquoi cette option existe.

**Le critere materiau est `G/rho`, pas `E/rho`.** Le caisson travaille en
cisaillement de membrane. Une ame de sandwich n'y change rien la ou la peau
travaille en cisaillement plan. Cela pilote le drapage : il faut des plis a
+/-45 degres orientes sur les chemins de cisaillement, pas un quasi-isotrope
uniforme par facilite.

## 3. Le verrou qui commande le programme : le repere

**Aucune geometrie de monocoque n'est concevable aujourd'hui.** Non par principe
de securite, mais par impossibilite metrologique.

Un monocoque remplace la caisse. Il doit donc porter, dans un repere unique et a
mieux que sa tolerance, au minimum :

| interface | tolerance exigee | etat dans le depot |
|---|---|---|
| berceau et points de suspension avant | ~ +/- 1 mm | X non cale |
| fixations de bras arriere | ~ +/- 1 mm | X non cale |
| supports moteur et boite | ~ +/- 1 mm | X non cale, P21 invalide |
| ancrages de ceinture et de siege | reglementaire | non etabli |
| charnieres, gaches, baie de pare-brise | ~ +/- 1 mm | non etabli |

Or `twins/964-chassis/README.md` etablit que **le calage longitudinal du reseau
de datums n'est pas resolu**. Le repere est sain lateralement et en lacet ; la
chaine en X ne l'est pas. Le point P21, palier moteur, tombe a X = -3112 mm,
dans le pare-chocs arriere. La recherche du point 17 sur le scan est un resultat
negatif solide : le scan ne resout pas les percages.

**Ce verrou etait un travail de documentation. Il devient le chemin critique du
produit.** Tant qu'il tient, il n'y a pas de monocoque : il y a un objet qui
ressemble a une caisse et qui ne se monte pas.

Il n'est pas ouvert par du calcul. Il s'ouvre par une donnee, et les pistes sont
deja triees dans `docs/research/964-combler-le-gap-de-donnees.md` : releve de
marbre (Autorobot, Car-O-Data, Celette), tableau de points 993 de Rennlist, scan
de carrosserie de serie. **Le releve de marbre passe de « souhaitable » a
« bloquant ».** C'est le premier budget a engager.

## 4. Le denominateur manquant se mesure, il ne se cherche plus

Verrou B — aucune raideur en torsion de 964 publiee — a ete traite comme un
probleme de recherche bibliographique. Deux campagnes, dont une germanophone,
n'ont rien donne de citable.

**C'est un probleme de mesure, pas de bibliographie.** Un essai de torsion de
caisse en blanc est un essai d'atelier : bridage sur les points de suspension
arriere, couple applique aux tours d'amortisseur avant, mesure de la rotation au
comparateur sur plusieurs stations. Il ne demande ni laboratoire, ni budget
d'homologation.

Mesurer une caisse 964 donneur en torsion donne d'un coup :

- le denominateur que personne ne publie, ZESAD compris ;
- la validation du modele coque, dont toutes les valeurs absolues sont
  aujourd'hui invalidees par des sections `ASSUMED` et une non-convergence de
  maillage ;
- l'argument commercial : « x fois la caisse d'origine, protocole publie ».

**C'est la recommandation la plus rentable de ce document.** Elle est sous notre
controle, elle ne depend d'aucun tiers, et elle transforme tout le travail FEA
existant de qualitatif en quantitatif.

## 5. Specification cible — a remplir, methode fixee

Aucune valeur n'est inscrite ici tant que le paragraphe 4 n'est pas fait.
Inscrire un chiffre maintenant serait exactement ce que ce depot refuse.

| exigence | unite | methode d'etablissement |
|---|---|---|
| raideur en torsion caisse nue | N.m/deg | multiple de la 964 mesuree ; a fixer apres essai |
| masse caisse nue | kg | pesee ; comparer a la 964 mesuree, pas a une valeur de forum |
| frequence propre de torsion | Hz | essai modal, decoule de K et de l'inertie |
| positions d'interface | mm | reseau de datums cale, tolerance +/- 1 mm |
| ancrages ceinture | — | exigence reglementaire du marche vise |
| tenue au choc | — | voir section 7 |
| tolerance de fabrication | mm | capabilite du procede retenu |

Regle : **chaque ligne publiee porte son protocole et son incertitude**, ou n'est
pas publiee. C'est le produit.

## 6. Fabrication en Chine — la capacite n'est pas la contrainte

**Il faut dire les choses dans le bon sens : sur la fabrication, la Chine ne se
contente pas d'egaler ZESAD, elle le depasse.** ZESAD est un atelier allemand
fonde en 2013, developpeur de pieces de competition. L'industrie composite
chinoise de rang aeronautique — infrastructure d'autoclaves batie autour des
programmes civils domestiques, premiere capacite mondiale de fibre de carbone —
travaille a un niveau superieur, sur des pieces plus grandes et sous des systemes
qualite plus exigeants.

La question n'est donc pas « saura-t-on faire aussi bien ». Elle est
« saura-t-on **choisir** le bon atelier », ce qui est un probleme different et
plus facile.

**Correction d'une erreur d'analyse.** Une version precedente de ce document
ecartait l'autoclave au motif que son amortissement serait brutal a bas volume.
C'est faux des lors qu'on **sous-traite** : on loue du temps d'autoclave a qui en
possede deja, on n'amortit pas la cuve. La route exacte de ZESAD — preimpregne
cuit en autoclave — est donc pleinement accessible, et c'est en Chine qu'elle
l'est le plus. Reste le cout d'outillage, reel, mais sans commune mesure avec un
outillage europeen.

| route | fraction volumique | outillage | remarque |
|---|---|---|---|
| preimpregne autoclave | la plus haute, la plus reguliere | cher | route ZESAD, accessible en sous-traitance ; **reference a viser** |
| preimpregne hors autoclave (OOA), etuve | proche autoclave | moyen | alternative credible si l'autoclave n'apporte rien de mesurable |
| infusion sous vide (VARTM) | plus basse, plus dispersee | le moins cher | a ne retenir que si la dispersion est prouvee maitrisee |
| RTM / C-RTM | haute, tres reguliere | tres cher, presse | seulement si le volume monte |

Le choix se tranche sur la **dispersion mesuree** de la fraction volumique et des
proprietes coupons, pas sur une preference ni sur le prix affiche.

**Le vrai piege du sourcing chinois n'est pas la capacite, c'est le tri.**
L'industrie chinoise du carbone automobile est enorme mais tres majoritairement
**cosmetique** : panneaux, aero, habillage, souvent en drapage humide, optimises
pour l'aspect du sergé et non pour une propriete structurale. Une piece de
securite ne se commande pas dans ce vivier-la. Les ateliers pertinents sont ceux
de rang aeronautique ou competition, qui existent et sont nombreux, mais qui
constituent une population distincte. Confondre les deux est le seul vrai risque
de ce volet, et il se traite par les exigences ci-dessous.

**Fibre.** La Chine produit en propre de la fibre de classe T700/T800 — candidats
a verifier : Weihai Guangwei, Zhongfu Shenying, Hengshen, Jilin. C'est un
avantage reel et pas seulement de cout : la fibre a haut module et haute
resistance releve des regimes de controle des biens a double usage, et une chaine
domestique evite ces frictions d'importation. **A verifier fiche technique en
main** : les equivalences annoncees a T700/T800 demandent une qualification par
coupons, pas une lecture de catalogue.

**Ce qu'il faut exiger d'un sous-traitant, et qui trie vite :**

- systeme qualite : AS9100 est plus significatif qu'IATF 16949 pour du composite
  structurel ; l'absence des deux n'est pas redhibitoire mais impose un plan de
  controle ecrit par nous ;
- tracabilite lot de preimpregne, avec relevé de duree de vie hors congelateur ;
- enregistrement de cycle de cuisson par piece, thermocouples dans l'outil ;
- **coupons temoins cuits avec chaque piece**, et essais mecaniques dessus : sans
  cela il n'y a aucune preuve que la piece livree vaut la piece calculee ;
- controle non destructif : ultrasons par transmission ou multi-elements sur les
  zones critiques, avec critere d'acceptation ecrit ;
- propriete de l'outillage et du livre de drapage contractuellement a nous.

**Le risque principal n'est ni le prix ni la capacite, c'est la dispersion.** Un
monocoque dont la raideur varie de 20 % d'un exemplaire a l'autre n'est pas un
produit publiable selon la methode retenue en section 1. Le plan de coupons est
donc une exigence de conception, pas une clause de qualite.

**Et ce qui ne se sous-traite pas, nulle part.** Un excellent atelier fabrique ce
qu'on lui donne : il ne fournit ni l'autorite de conception, ni le drapage, ni la
validation, ni le dossier d'homologation. C'est precisement ce que ZESAD ne
publie pas, donc precisement la ou se joue la difference. Si la fabrication n'est
pas la contrainte — et elle ne l'est pas — alors **la totalite de la valeur et du
risque se concentre sur les sections 3, 4 et 7 de ce document**.

## 7. Identite du vehicule et homologation

C'est la contrainte commerciale reelle, et elle prime sur la technique.

La caisse porte le numero de chassis. Remplacer la structure autoportante pose,
selon le marche, la question de savoir si le vehicule reste le meme vehicule ou
devient un vehicule nouveau — avec, dans le second cas, un dossier de reception
sans commune mesure avec un restomod.

Ce document ne tranche pas cette question : elle est juridique, elle depend du
pays d'immatriculation, et elle doit etre instruite marche par marche **avant**
tout engagement d'outillage. Une hypothese a verifier : la configuration ZESAD
« avec cadre de baie acier » pourrait servir a conserver un element d'origine
porteur de l'identite, autant qu'a repondre au besoin structurel identifie en
section 2.

**Point d'ordonnancement :** l'etude d'homologation est peu couteuse et peut tuer
le programme. Elle passe donc avant la conception detaillee, pas apres.

## 8. Portes de securite — ce qui reste ferme

`SAFETY.md` presume critiques la retenue des occupants, la suspension, les points
de levage et les fixations principales. Un monocoque les porte toutes. Il est
donc `prohibited_pending_engineering` : **jamais publie comme piece liberee** en
l'etat.

Cette classe n'interdit ni d'etudier, ni de calculer, ni de specifier, ni de
mesurer. Elle interdit de **liberer de la geometrie** sans revue d'ingenierie
formelle et plan de validation approuve. Rien dans ce programme ne demande de
lever cette porte, et les sections 3 a 6 sont precisement le travail qui permet
un jour de l'instruire serieusement.

Un point non negociable, et qui n'est pas une question de perimetre : la tenue au
choc d'une structure composite **ne se calcule pas de maniere credible sans
essais physiques**. Un critere de rupture composite n'est pas une contrainte de
von Mises ; la ruine se fait par delaminage, decollement et flambement local,
mecanismes que le modele coque actuel ne represente pas du tout. Aucune
affirmation de securite ne sortira de ce depot sans essais.

## 9. Phases et criteres de sortie

| phase | contenu | critere de sortie | dependance |
|---|---|---|---|
| M0 | etude d'identite et d'homologation, marche par marche | voie identifiee ou programme arrete | juriste |
| M1 | releve de marbre, calage du reseau de datums | 964 en `F2_interface`, interfaces a +/- 1 mm | **tiers, bloquant** |
| M2 | essai de torsion sur caisse 964 donneur | denominateur mesure, protocole publie | caisse donneur |
| M3 | recalage du modele coque sur M2 | ecart modele/mesure connu et documente | M1, M2 |
| M4 | specification cible remplie | tableau section 5 complet | M2, M3 |
| M5 | concept d'architecture et drapage | anneaux fermes, chemins de cisaillement definis | M4 |
| M6 | qualification procede et sous-traitant | plan de coupons valide, dispersion mesuree | M5 |
| M7 | revue d'ingenierie et plan d'essais physiques | revue signee au sens de `SAFETY.md` | M6 |

M0, M1 et M2 sont paralleles et sont les seuls a engager maintenant. **M1 et M2
sont les deux qui commandent tout le reste**, et M2 est le seul entierement sous
notre controle.

## 10. Ce que ce document n'est pas

- Ce n'est pas une conception. Aucune cote, aucun drapage, aucune geometrie.
- Ce n'est pas une autorisation. La classe `prohibited_pending_engineering` est
  inchangee.
- Ce n'est pas une etude de marche, ni un plan d'affaires, ni une evaluation du
  produit ZESAD, dont rien de structurel n'est publie et donc rien n'est
  confrontable.
- Les noms de producteurs de fibre cites sont des candidats a verifier, non des
  fournisseurs qualifies. Aucun n'a ete contacte.
- Le perimetre de `ROADMAP.md` n'est pas modifie par ce document.
