# Plan de donnees pour le jumeau numerique du 993 Turbo

Ce document fixe le perimetre avant tout calcul sur Vast.ai. Il ne declare pas
qu'une piece est exacte, ajustee, testee, sure ou liberable.

La collecte specifique des conditions d'ecoulement, des interfaces PET et des
enveloppes fournisseurs est detaillee dans
[`TURBO_AIRFLOW_SIMULATION_DATA.md`](TURBO_AIRFLOW_SIMULATION_DATA.md). Les
debits qui y sont calcules sont des bornes de sensibilite et non des mesures.

## Etat de la collecte

| Donnee | Etat | Niveau d'usage |
|---|---|---|
| Architecture biturbo parallele | Confirmee par Porsche | Conditions de contexte |
| Cylindree moteur | 3 600 cm3 | Conditions de contexte |
| Suralimentation maximale de la 993 Turbo de base | 0,8 bar | Cas de charge public, pas limite de conception |
| Puissance/couple de la version de base | 408 ch / 540 Nm | Cas moteur public, pas carte turbo |
| Famille K16 et references 5316-988-6735/6 | Recoupee fabricant/distributeurs | Identification a confirmer |
| References des sous-ensembles K16 | Catalogue fournisseur | Pistes de nomenclature uniquement |
| Encombrement et masse des K16 complets | FVD : 280 x 190 x 210 mm ; 5,76 kg gauche / 5,6 kg droite | Controle de masse et de packaging ; declaration fournisseur |
| Diametres de roues du K16 droit | 54,96/48,97 mm turbine ; 40,6/60,5 mm compresseur | Bornes de parametrage ; declaration fournisseur, pas profils aero |
| A/R 8.00 | Declaration TurboMaster sur 5316-988-6735 | A ne pas transformer en cote de fabrication |
| Durites de pression turbo-echangeur | FVD : 430 x 70 x 90 mm droite / 430 x 70 x 115 mm gauche ; 0,42 kg chacune | Encombrement de remplacements fournisseur ; masses alternatives EQ 0,52/0,44 kg |
| Conduit d'air d'echangeur `993 110 340 54` | FVD : 600 x 280 x 50 mm ; 0,9 kg | Produit FVD developpe en propre ; reference de packaging, pas geometrie OEM |
| Support renforce d'echangeur FVD11011050 | FVD : 255 x 80 x 23 mm ; 0,2 kg | Upgrade aftermarket ; resistance et interfaces a mesurer |
| Echangeur de remplacement `993 110 330 53` | AKS DASIS 177020T : faisceau 260 x 270 x 60 mm ; 7,06 kg | Noyau de remplacement, pas encombrement complet OEM |
| Echangeur Motorsport FVD110330 | FVD : 870 x 410 x 190 mm ; 10,1 kg | Upgrade avec modifications d'installation ; borne de packaging/thermique |
| Ecran thermique gauche `993 123 113 51` | FVD : 160 x 110 x 105 mm ; 0,23 kg | Encombrement produit ; epaisseur et fixations inconnues |
| Geometrie 3D et tolerances | Absente | Bloquante |
| Cartes debit/pression/rendement | Absentes | Bloquante pour CFD calibree |
| Materiaux et traitements | Absents par sous-ensemble | Bloquante pour FEA thermique/fatigue |
| Jeux, vitesse rotor, equilibrage | Absents | Bloquante pour rotordynamique |

Les donnees publiques Porsche confirment que les deux turbocompresseurs
fonctionnent en parallele, alimentent chacun un banc et comportent une wastegate
integree. Elles ne constituent pas un plan de definition. Voir les sources
enregistrees dans `catalog/sources/` et la fiche cible
`catalog/parts/993-turbocharger-k16-pair-0001.json`.

La recherche germanophone a apporte des bornes supplementaires : FVD publie les
dimensions et masses des deux ensembles K16, et Invasion Auto Products publie des
references de roues et quelques diametres pour le K16 droit. Ces donnees sont
maintenant tracees dans `catalog/reference/993-declared-part-data.json` et dans
les fiches sources correspondantes. Elles permettent un parametrage initial et
un controle de coherence ; elles ne remplacent ni une piece, ni une metrologie,
ni une carte compresseur.

## Pieces adjacentes et nouvelles bornes

La recherche germanophone a aussi produit des bornes autour du turbo. Les
durites `993 110 632 56` et `993 110 633 56` ont un encombrement annonce de
430 mm de long, 70 mm de large, avec 90 mm de haut a droite et 115 mm a gauche.
Le conduit `993 110 340 54` est annonce a 600 x 280 x 50 mm. Ces trois fiches
FVD indiquent qu'il s'agit de produits developpes par FVD : elles sont utiles
pour le packaging et la reconstruction d'une enveloppe, mais ne donnent pas la
section, les rayons, les epaisseurs, les embouts ou les entraxes OEM.

Pour l'echangeur, la fiche allemande AKS DASIS 177020T associee a `993 110 330
53` declare un faisceau de 260 x 270 x 60 mm et une masse de 7,06 kg. Ce sont
les dimensions du noyau, pas celles de l'ensemble complet. Une autre borne est
fournie par l'echangeur Motorsport FVD110330 : 870 x 410 x 190 mm et 10,1 kg,
avec modifications d'installation annoncees. Elle ne doit pas etre melangee
avec l'OEM.

Les valeurs sont enregistrees dans
`catalog/reference/993-declared-part-data.json`, avec un `source_id` distinct
pour chaque fiche. Leur statut reste `declared` : aucune n'est une mesure
physique du projet. Les pages PET de Porsche Fanatics servent a confirmer les
references adjacentes et leurs positions, pas leurs cotes.

## Ce qu'il faut encore obtenir

### Identite et geometrie

- photo lisible de chaque plaque signaletique et identification gauche/droite ;
- numero moteur, annee-modele et configuration exacte : Turbo, Turbo S, GT2 ou
  preparation ;
- scan metrologique ou CAO dont la licence autorise l'usage ;
- repere commun : axe rotor, plans de brides, interfaces huile/air/echappement ;
- surfaces des roues, carters, volute, diffuseur, wastegate et passages d'huile ;
- jeux radial/axial, epaisseurs de paroi, rayons, rugosite et tolerances.

Une photographie, un eclate PET ou une fiche de vendeur ne permet pas de deduire
ces surfaces. Sans piece ou fichier sous licence, la CAO restera un volume
parametrique de recherche, jamais une reproduction.

### Physique et fonctionnement

- points de fonctionnement moteur : regime, debit d'air, pression et temperature
  en entree/sortie ;
- pression et temperature des gaz d'echappement, contre-pression et ouverture de
  wastegate ;
- pression/temperature/debit d'huile et mode de refroidissement du palier ;
- vitesse maximale du rotor et limites surge/choke ;
- historique de fatigue, cycles thermiques et etat d'usure d'un exemplaire.

## Paquet de calcul Vast.ai

Le conteneur `physicsml` est deja prepare pour CAO, maillage, CalculiX,
OpenFOAM, JAX-FEM, PhysicsNeMo et DeepXDE. Le premier job doit rester petit et
reproductible :

1. valider une geometrie parametrique cote froid ;
2. generer un maillage avec rapport de qualite ;
3. executer un cas OpenFOAM de debit/pression ;
4. executer un cas thermique et structural sur la coque avec CalculiX ou
   JAX-FEM ;
5. comparer les sorties a des donnees de reference et conserver les incertitudes ;
6. seulement ensuite entrainer un surrogate Physics ML sur des cas generes par
   solveur.

Le modele de langage peut orchestrer les variantes, verifier les fichiers et
produire des hypotheses. Il ne remplace ni le solveur, ni la metrologie, ni la
qualification du procede additif.

Le premier normalisateur 0D des donnees de banc est dans
`simulation/993-turbo-dyno/`. Il convertit les points de couple et puissance,
calcule le BMEP et attache une enveloppe de debit moteur aux regimes publies.
Les points châssis, les cibles de preparateurs et les courbes moteur rapportees
restent separes par type de banc ; aucune conversion whp vers puissance moteur
n'est appliquee. `make turbo-dyno-check` doit passer avant d'utiliser le paquet
dans un job Vast.ai.

Le premier cas est maintenant dans
`simulation/993-k16-cold-side-baseline/`. Il contient une geometrie OpenSCAD
editable de diffuseur fixe et un harnais OpenFOAM `blockMesh` + `simpleFoam`.
Le maillage est un conduit rectangulaire a section equivalente : il sert a
valider la chaine et comparer des variantes, pas a pretendre reproduire le K16.
Les commandes sont `make turbo-cold-side` puis, dans le conteneur cadsim,
`blockMesh`, `checkMesh` et `simpleFoam`.

Le jeu de comparaison suivant est dans
`simulation/993-turbo-variants/`. Son manifeste unique genere trois cas avec
les memes champs solveur : controle `K16-OEM`, sensibilite `K16-24-HYBRID` et
sensibilite haut debit `K24-REFERENCE`. Le debit commun est derive d'une plage
de fonctionnement estimee ; les diametres et longueurs des trois diffuseurs
sont des hypotheses de recherche marquees comme telles. Utiliser
`make turbo-variants`, puis lancer `blockMesh`, `checkMesh` et `simpleFoam` dans
chaque dossier `cases/<variant>/`. Ces cas ne valident ni les performances des
preparateurs ni la geometrie d'un turbo reel.

## Premier demonstrateur recommande

Le premier demonstrateur est un adaptateur ou conduit cote froid, non rotatif,
non structurel et accessible a une verification d'encombrement. Le flux de
validation est :

1. parametrage CAO avec plages et incertitudes ;
2. prototype polymerique de montage ;
3. calcul de perte de charge et de temperature ;
4. version metal uniquement apres choix du materiau et du procede ;
5. controle metrologique, pression et temperature dans un banc adapte.

Les roues compresseur/turbine, l'arbre, les paliers, l'actionneur et le carter
chaud restent hors fabrication tant qu'une revue d'ingenierie et un plan de
validation approuve ne sont pas disponibles.

## Critere de lancement

On peut louer Vast.ai lorsque le paquet contient au minimum :

- une geometrie ou un parametrage dont la provenance est explicite ;
- un fichier de conditions aux limites et ses unites ;
- un maillage deterministe et un cas de reference qui tourne localement ;
- une matrice des inconnues et une regle d'arret en cas de depassement ;
- un manifeste des sources, licences, versions du conteneur et hash des entrees ;
- un dossier de sortie separe du depot, avec reprise sur checkpoint.

Ce seuil est atteint pour une etude numerique d'adaptateur cote froid. Il ne
l'est pas pour un jumeau valide du turbocompresseur complet.
