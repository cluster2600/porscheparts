# Jumeau numérique de la Porsche 993

## Objectif

Le jumeau sert d'abord à inventorier, représenter et assembler ce qui est connu.
La phase active ne prévoit aucune impression. Lorsque les preuves le permettent,
il pourra ensuite éliminer des erreurs de montage et étudier le comportement
mécanique ou thermique. Il ne prétend pas être une copie certifiée de toutes les
993.

Un composant n'entre dans le graphe actif que si taille, masse, matière et
application sont sourcées. Un assemblage logique affirme que des pièces vont
ensemble ; un assemblage positionné exige en plus leurs repères et
transformations 3D.

Le modèle est construit par zones : tableau de bord, porte, siège, baie moteur,
train roulant et carrosserie. La précision est déclarée par composant et par
interface, car une même zone peut combiner un habillage visuel `F0` et des
fixations mesurées `F2`.

## Première tranche géométrique — tableau de bord, en attente

Le MVP assemble :

1. le cache d'interrupteur candidat ;
2. l'ouverture et l'épaisseur du panneau qui le reçoit ;
3. le volume libre derrière le panneau ;
4. les marges minimales d'insertion, de recouvrement, de clipsage et de recul.

Le script
`twins/993-cabin-dashboard-switch-0001/source/check_fit.py` lit une fiche de
mesure et refuse de calculer si une cote manque. Il produit un rapport JSON avec
la marge nominale et la marge garantie au pire cas, incertitudes comprises.

```bash
python3 twins/993-cabin-dashboard-switch-0001/source/check_fit.py \
  --measurements catalog/measurements/meas-993-dashboard-switch-zone-0001.json \
  --out twins/993-cabin-dashboard-switch-0001/derived/fit-report.json
```

## Première intégration géométrique — roues et moyeux

Le registre contient maintenant une seconde zone active :
`TWIN-993-WHEEL-HUB-INTERFACES-0001`. Elle référence quatre solides STEP
reproductibles à partir du même maître build123d :

- Fuchs 7J × 17 ET55, avant ;
- Fuchs 9J × 17 ET55, arrière ;
- Fuchs 8J × 18 ET52, avant ;
- Fuchs 10J × 18 ET65, arrière.

Ces objets sont des proxys d'interface `F1_envelope` : cylindre nominal,
largeur nominale et alésage central. Ils rendent les composants visibles et
assemblables dans FreeCAD, mais ne reproduisent ni les branches, ni le profil
réel de jante, ni les sièges de boulons. Les deux moyeux restent des repères
logiques sans géométrie. Le twin est donc au statut `concept`, et non
`digitally_checked`.

Pour passer à `F2_interface`, il faut mesurer ou sourcer la face d'appui, le
centrage du moyeu, le type de siège des fixations, l'enveloppe du frein, les
tolérances et les transformations dans le repère véhicule. Alors seulement un
calcul de collision ou de marge pourra devenir une preuve numérique.

## Première tranche automatisée — encombrements disponibles

Le générateur `scripts/generate_catalogue_part_twins.py` matérialise maintenant
un proxy OpenUSD distinct pour chaque entrée disposant d'un encombrement déclaré.
Le premier lot comporte 18 actifs suivis dans `twins/catalogue-parts/index.json` :
quatre roues Fuchs et quatorze enveloppes de produits, dont le berceau moteur
Turbo `993 115 021 53`, les turbocompresseurs, durites, échangeurs, conduit,
support, écran et sonde.

Le catalogue PorscheFanatics sert ici au recoupement de l'identité et de
l'application PET. Il confirme pour le berceau le groupe 109-00, la position 17
et la destination 993 Turbo. Il ne fournit aucune cote CAO : la géométrie du
berceau reste donc une enveloppe déclarée de 600 × 50 × 50 mm, et sa matière
« acier » reste une inférence explicitement signalée. Les roues utilisent leurs
dimensions et leur aluminium forgé documentés par Fuchs ; leurs branches,
sièges de fixation et profils de jante ne sont pas reconstruits. Pour treize
des quatorze enveloppes, la matière reste `unresolved` et la représentation
visuelle emploie un matériau documentaire neutre, sans propriété physique.

Ces USD restent `F1_envelope`, sans schéma physique, collision ni revendication
SimReady. Ils rendent le lot visible et traçable dans une scène, mais ne changent
aucun statut de validation ou de libération.

La passe suivante se génère avec `make catalogue-engineering`. Le fichier
`twins/catalogue-parts/engineering-f0.json` porte les contrats d'acquisition, de
fabrication et de simulation. CalculiX reste la référence structurelle ;
PhysicsNeMo/MeshGraphNet est réservé à un surrogate entraîné sur des résultats
CAE convergés puis corrélés à des essais. Le contrôle échoue fermé : en l'absence
de géométrie F3, de nuance qualifiée, de charges ou de critères d'acceptation,
aucun résultat de résistance ni aucune libération de fabrication n'est émis.

Pour le premier item de la file, le berceau Turbo `993 115 021 53`, le rapport
`engine-carrier-material-screening-f1.json` exécute un modèle analytique de
flexion sur coupon générique. Il quantifie le compromis acier/titane et
dépriorise la voie titane dans ce programme conceptuel. Comme aucune surface
porteuse ni interface réelle n'entre dans ce modèle, le rapport accorde zéro
crédit au composant, ne choisit aucune nuance et ne remplace pas un calcul EF du
berceau.

Le témoin mathématique
`engine-carrier-mass-constrained-surrogate-f1.json` exploite ensuite les seules
grandeurs disponibles sans leur faire dire davantage : enveloppe 600 × 50 ×
50 mm, masse 1,96 kg et densité générique d'acier 7 850 kg/m³. Un tube creux
carré uniforme occupant toute l'enveloppe referme exactement la masse avec une
section de 416,135881 mm², un taux de remplissage de 0,166454 et une paroi
équivalente de 2,175320 mm. Ce solide éditable SCAD et sa couche OpenUSD sont
un surrogate structurel `F1`, pas la géométrie OEM.

Deux cas analytiques volontairement extrêmes encadrent la sensibilité sous la
borne documentaire de 1 912,29675 N : poutre simplement appuyée chargée au
centre, 45,1129 MPa et 0,2578 mm ; console chargée en bout, 180,4517 MPa et
4,1246 mm. Ces résultats dépendent entièrement du tube uniforme, des appuis
idéalisés et de propriétés génériques. Ils n'accordent aucun crédit CAE au
composant, ne qualifient aucune nuance et ne constituent aucun critère
d'acceptation.

Le contrat `engine-carrier-virtual-f2-readiness.json` ouvre l'étape suivante sans
inventer de métrologie. Il relie le berceau à deux identités adjacentes relues
dans le catalogue PorscheFanatics — la patte moteur `993 115 103 52` et les deux
silentblocs `993 375 049 05` — comme hypothèses topologiques, jamais comme preuve
de leurs liaisons physiques. Dix-neuf paramètres d'interface, de charge, de
matière et d'acceptation restent explicitement inconnus. Huit cas de charge sont
formulés ; seule la borne documentaire `0–1 912,29675 N` du poids statique est
calculable à partir du candidat de masse moteur de 195 kg et d'une fraction de
charge comprise entre zéro et un. Cette borne ne produit aucune contrainte,
durée de vie ou décision matière.

La couche OpenUSD
`engineering/993-engine-carrier-virtual-f2-readiness.usda` compose l'enveloppe
F1, le surrogate contraint par la masse et ces deux interfaces sans coordonnées, transformation véhicule,
schéma physique ni géométrie F2. Elle est visualisable comme graphe sémantique,
mais n'est ni PhysX, ni SimReady. Le LLM ne peut émettre que des hypothèses
assorties d'incertitudes ; CalculiX reste la référence structurelle et
PhysicsNeMo demeure désactivé avant un jeu de résultats EF convergés.

Le couvercle de protection thermique gauche `993 123 113 51` possède désormais
un contrat spécialisé dans `turbo-heat-shield-readiness-f1.json`. Le guide SCAD
et la couche OpenUSD conservent uniquement l'enveloppe fournisseur
160 × 110 × 105 mm et la masse de 0,23 kg. Ils ne représentent ni la surface
formée, ni l'épaisseur, ni les fixations, ni la face chaude. Le modèle formule
sept équations de rayonnement, convection, conduction, bilan transitoire,
dilatation et contrainte thermique conditionnelle. Les quatre cas thermique et
durabilité restent bloqués par 25 paramètres inconnus. Les familles de tôles et
d'isolants sont donc des hypothèses de présélection, sans nuance ni procédé
fonctionnel retenu.

Après ce raccord, les neuf maîtres PET possédant un proxy par référence OEM
exacte sont tous distingués par un contrat spécialisé : deux K16, cinq éléments
de chaîne d'air, le couvercle thermique et le support moteur. Le contrat K16
porte aussi cette préparation sur deux révisions PET supplémentaires sans leur
inventer une nouvelle enveloppe. Il ne reste aucun état courant générique
`F1_envelope_identity_linked_unvalidated`; cette disparition signifie une
meilleure qualification du travail restant, pas une géométrie F2 validée.

Le lot suivant couvre les soupapes liées exactement au PET. Le générateur
`generate_pet_993_valve_surrogates.py` produit un maître SCAD paramétrique, une
scène OpenUSD et un rapport pour trois variantes : admission `993 105 409 02`,
échappement Carrera `993 105 419 01` et échappement Turbo `993 105 419 52`.
Deux autres références Turbo annoncées par la même source, `993 105 419 84` et
`993 105 419 53`, restent hors raccord PET plutôt que d'être inventées.

Les échappements conservent leurs triplets déclarés 109 × 42,5 × 8 mm et
108,9 × 43,5 × 8 mm. Pour l'admission, seuls la tête de 49 mm, la queue de 8 mm
et la masse de 120 g sont déclarés ; la longueur 109 mm reste explicitement une
hypothèse tirée de l'enveloppe commerciale de 110 mm. Le profil tête–col–queue,
l'épaisseur de tête de 2,5 mm et le col de 8 mm sont des hypothèses de
visualisation F1. Le contrôle de cohérence de l'admission donne 122,0637 g avec
la densité générique d'acier, soit un écart de 2,0637 g ; cette proximité
n'identifie ni l'alliage ni la géométrie réelle.

Le Ti-6Al-4V, l'Inconel 751 et l'acier générique restent uniquement des familles
de comparaison. Aucune matière, voie CNC ou additive n'est sélectionnée. Les
interfaces siège, guide, clavettes et chaîne de distribution, ainsi que les
températures, jeux chauds, courbes de ressort et profils de came, restent
inconnus. Les trois cas thermique, dynamique et fatigue sont donc bloqués avant
solveur de référence et PhysicsNeMo.

Le lot K16 relie ensuite les quatre références gauche/droite du PET. Le
générateur `generate_pet_993_k16_surrogates.py` conserve les deux enveloppes
complètes déclarées de 280 × 190 × 210 mm, les masses de 5,76 et 5,60 kg et,
pour le turbo droit seulement, les diamètres compresseur 40,6/60,5 mm et turbine
54,96/48,97 mm. Les diamètres sont dessinés comme quatre coupons indépendants,
hors des boîtes d'encombrement : aucune position de roue ni surface de carter
n'est déduite. Les quatre maîtres PET passent ainsi en
`F1_k16_envelope_diameter_guides_unvalidated`, sans géométrie F2 ou F3.

Le même rapport ferme cinq contrôles arithmétiques : masse totale déclarée de
11,36 kg, écart gauche/droite de 0,16 kg, volume d'enveloppe et ordre numérique
des diamètres. La valeur combinée de 508,4139 kg/m³ est une métrique de colis
creux multimatériau, pas une densité. Six équations 0D définissent rapport de
pression, puissances compresseur/turbine, équilibre d'arbre, coordonnées
corrigées et vitesse de pointe. Aucun point n'est calculé : cartes, débits,
pressions, températures, rendements, vitesse, inertie et pertes restent absents.

La découverte PhysicsNeMo vérifie GeoTransolver, Transolver et MeshGraphNet
comme candidats futurs après CFD de référence ; DoMINO reste documenté mais non
sélectionné, son exemple étant aérodynamique externe. Le cas OpenFOAM existant
reste un smoke test de diffuseur synthétique et ne reçoit aucun crédit K16. Les
familles de matières proposées par sous-ensemble sont des hypothèses LLM non
sourcées et non sélectionnées ; l'impression ou l'usinage d'un turbo fonctionnel
reste interdit avant géométrie, propriétés, équilibre, confinement et revue
professionnelle.

Le lot de chaîne d'air de suralimentation relie ensuite cinq références exactes
de la planche PET 107-45 : durites gauche/droite `993 110 633 56` et
`993 110 632 56`, échangeur `993 110 330 53`, conduit `993 110 340 54` et
sonde `993 606 114 00`. `generate_pet_993_charge_air_surrogates.py` ne dessine
que cinq enveloppes fournisseur. Les diamètres 43/57 mm d'un kit aftermarket
restent deux coupons non positionnés et non affectés à un côté ou à une interface
OEM. Une autre fiche annonçant un diamètre intérieur de 68 mm supérieur à son
diamètre extérieur de 66 mm est mise en quarantaine plutôt que corrigée.

Le réseau de suralimentation associé contient huit équations 0D symboliques :
conservation de masse, vitesses de branche, pertes de charge, bilan thermique,
efficacité échangeur, perte de pression du noyau et réponse du capteur. Aucun
point n'est évalué faute de sections, volumes, cartographies, températures,
pressions et calibration. GeoTransolver, Transolver et MeshGraphNet restent un
menu futur après CFD/CHT de référence ; DoMINO n'est pas retenu comme preuve de
flux interne.

`engineering-guides-openusd-validation-f1.json` enregistre huit validations
`usdchecker --strict` réussies : berceau, trois
soupapes, deux K16, cinq guides de suralimentation, écran thermique et topologie
huile/commande de la planche `202-16`, plus le circuit du réservoir d'huile
`104-01` et le circuit du refroidisseur d'huile `104-05`, soit 97 primitives
guides. Cette preuve
porte sur la syntaxe et les
dépendances OpenUSD. NVIDIA Asset Validator, les services Material/Physics et
SimReady restent non exécutés, conformément au préflight bloqué.

Le contrat `twins/catalogue-parts/physicsnemo-structural-f0.json` fixe aussi le
format du futur jeu de données : maillage non structuré en unités SI, conditions
aux limites et propriétés matière comme entrées, champs de déplacement et de
contrainte comme cibles, puis séparation des jeux par révision géométrique et
enveloppe de charge. Le pilote `GeoTransolver` est choisi comme patron initial,
mais son exécution reste désactivée tant que les portes F3, CalculiX, convergence
de maillage et essai physique ne sont pas franchies.

## Programme véhicule complet indexé sur le catalogue

Le manifeste `twins/vehicle-993/program-f0.json` couvre maintenant les dix
familles PET, leurs 239 illustrations et 12 864 lignes de référence agrégées.
Chaque illustration devient un lot de travail F0 relié à des domaines de calcul,
des interfaces intersystèmes et des portes de preuve. Les huit lots fonctionnels
`VEH-00` à `VEH-90` ordonnent configuration, caisse, châssis, groupe
motopropulseur, fluides, électricité, habitacle et intégration véhicule.

Le générateur `scripts/generate_pet_993_twins.py` matérialise en plus 12 879
jumeaux documentaires F0 : les 12 864 transcriptions automatiques et 15
références relues en contexte. Ces occurrences sont également regroupées en
6 013 jumeaux maîtres, un par référence OEM normalisée. Les vingt-six shards
complets restent sous `work/pet-993/`. Deux manifestes sont versionnés :
`twins/pet-993/index-f0.json` pour les comptes, empreintes et contrôles, puis le
crosswalk décrit ci-dessous. Aucun PDF ni illustration PET n'est copié dans ce
dépôt.

Le crosswalk `twins/pet-993/catalog-crosswalk-f0.json` relie les références OEM
des fiches d'ingénierie internes aux occurrences PET. Une correspondance prouve
seulement que les identifiants documentaires concordent ; elle ne valide ni la
variante, ni les interfaces, ni la géométrie, ni la fabrication.

Le contrat `twins/vehicle-993/variant-configurations-f0.json` sépare les huit
variantes documentées. La Turbo est la première cible d'intégration sur la base
du marqueur `mvp` de la source. Treize références relues produisent 28
affectations de variante. La colonne `Model` du KAT 517 apporte en plus 173
candidats machine à quantité unique et 178 liens de variante. La Turbo S reçoit
un candidat direct ; GT2 reste vide. Aucun candidat machine n'est promu au rang
de lecture humaine et aucun BOM n'est présenté comme complet. Il reste 12 691
occurrences sans candidat direct de ce type.

L'univers de configuration est lui-même incomplet : les huit fiches véhicule
sources sont des coupés, alors que les colonnes PET contiennent 62 annotations
`CABRIO`, 33 `TARGA`, ainsi que des codes moteur, boîte et option absents des
contrats. Le manifeste `twins/vehicle-993/configuration-axes-f0.json` isole
maintenant quatre axes provisoires : Cabriolet (73 occurrences candidates),
Targa (50), manuelle 6 rapports G50/G64 (89) et Tiptronic 4 rapports A50 (2).
Le produit cartésien entre ces axes est interdit : il reste à prouver les
intersections avec variante, millésime, marché, moteur et options avant de créer
des configurations véhicule distinctes ou de revendiquer un BOM complet.

Le registre `twins/vehicle-993/configuration-roster-f0.json` franchit une étape
supplémentaire sans lever ce verrou : 69 lignes type/VIN, 34 options moteur et
40 options de boîte issues des trois sommaires PET produisent 149 intersections
candidates. Elles couvrent 67 lignes type ; les deux plages Carrera RS 1996
restent bloquées faute de boîte 1996 explicitement listée. Une file de revue de
151 entrées conserve chaque candidat et chaque lacune à l'état non relu. La
discordance source `G64.42`/`G6452` et la coquille `CARERRA` sont tracées comme
anomalies plutôt que corrigées silencieusement.

Le joint `twins/vehicle-993/configuration-part-links-f0.json` applique ce registre
aux occurrences de pièce. Parmi 694 contraintes PET mono-dimensionnelles à
quantité unique, 682 génèrent 24 063 liens vers les 149 configurations candidates.
Les douze contraintes sans cible concernent Carrera S, Carrera 4S, Turbo S et
A50.07. `Z64.20` est classé séparément comme code de pont avant, ce qui évite de
le traiter à tort comme une boîte de vitesses.
Ces liens ne sont pas des BOM, car chacun ne prouve qu'une seule dimension de
l'applicabilité et aucun n'est encore relu par un humain.

Une configuration d'intégration réversible est maintenant fixée dans
`twins/vehicle-993/turbo-integration-seed-f0.json` : Turbo Coupé 1998 RoW,
M64.60, G64.51. La fusion de dix occurrences Turbo relues et de 315 contraintes
mono-dimensionnelles donne 325 occurrences candidates, 316 maîtres et 580
instances candidates dans les dix systèmes. Elle ne couvre que 74 des 239
illustrations ; les 12 554 occurrences hors graine restent à résoudre et le
total d'instances ne doit pas être lu comme un BOM véhicule.

Les douze exceptions sont désormais toutes rattachées à
`twins/vehicle-993/configuration-exceptions-f0.json` : huit occurrences Carrera S,
deux Carrera 4S, une Turbo S et une A50.07. Le contrat distingue présence dans
l'ordre PET, option spéciale M092 et annotation de pièce. Pour A50.07, il trace
séparément le type A50.05 et le numéro A5007 des sommaires 1997–1998, mais interdit
de les déclarer équivalents sans revue du contexte et des règles de remplacement.

Neuf jumeaux maîtres PET reçoivent désormais l'encombrement déclaré du registre
`993-declared-part-data.json`. Un seul recoupe aussi une famille matière non
générique, l'acier inféré du berceau moteur. Ces rattachements n'augmentent pas
la fidélité : aucune nuance ni propriété matière n'est qualifiée.

Le manifeste `twins/pet-993/engineering-readiness-f0.json` donne maintenant à
chacun des 6 013 maîtres une tâche d'ingénierie inverse stable. Il relie identité
OEM, illustrations, criticité programme, domaines de calcul, candidats de
configuration, exceptions et prochaine porte de preuve. La première file
contient 317 pièces `P0` appuyées par une preuve d'intégration Turbo ; les autres
priorités couvrent 206 `P1`, 161 `P2`, 2 617 `P3` et 2 712 `P4`.

Le contrat `twins/vehicle-993/manual-evidence-routing-f0.json` exploite les
2 496 faits déjà extraits du manuel sans les sur-promouvoir. Il route 2 442
enregistrements vers les familles système et laisse 54 OCR non résolus. Les
descriptions exactes dans un même système donnent 1 569 liens de revue vers 417
maîtres PET ; même les dix lignes lexicalement non ambiguës restent à confirmer
dans leur contexte avant toute attribution de cote, couple ou charge.

Le crosswalk d'ingénierie rattache aussi quatre fiches détaillées du catalogue à
huit maîtres PET. Le berceau moteur, les deux familles de soupapes et la paire
de K16 apportent ainsi des hypothèses traçables de matière, procédé, géométrie
et validation à la file de revue. Aucune de ces hypothèses n'est promue en choix
qualifié ou en preuve de fonctionnement.

Dans la partition de fidélité courante, 5 842 maîtres restent F0, trois ont un
surrogate dimensionnel de soupape, quatre les guides K16, cinq les guides de la
chaîne d'air, un l'écran thermique, un le support moteur et 35 la topologie
huile/commande non spatiale `202-16`. Quatre-vingt-un autres maîtres portent
désormais la topologie non spatiale du réservoir d'huile et de ses conduites
`104-01`, et 41 celle du refroidisseur d'huile et de son circuit d'air `104-05`.
Les états
d'ingénierie spécialisés ne remplacent pas les proxys catalogue existants : ils
les dépassent seulement comme état d'ingénierie
affiché, tout en conservant leurs liens d'identité et sans composer leur
géométrie dans le véhicule.

`twins/pet-993/engineering-evidence-links-f0.json` relie à ces mêmes maîtres
trois contrats de jumeau catalogue, quatre proxys moteur et dix cas de charge
uniques, soit treize liens pièce-cas. Les modèles couvrent structure, modes,
fatigue, thermique, dynamique de distribution, CFD compressible et
rotordynamique. Chaque cas conserve son statut bloqué et ses entrées manquantes ;
aucun résultat n'est fabriqué à partir du seul nom de pièce.

Le même contrat ajoute les liens directs de la chaîne d'air, de l'écran
thermique, des 40 maîtres de `202-16`, des 81 maîtres de `104-01` et des 43
maîtres de `104-05`, fondés sur l'identité exacte du master PET. Au total, 171
tâches portent 178 liens de preuve d'ingénierie ; les recouvrements entre
contrats restent visibles. Aucun lien n'ajoute de
résultat de solveur, de matière qualifiée, de validation SimReady ou de
libération.

La découverte live PhysicsNeMo du 2 septembre 2026 est ancrée au commit NVIDIA
`4fbfcfd62bf050b48ceec6b438da409b9f4644b3`. Les tâches associent les domaines
admissibles à GeoTransolver, Transolver, MeshGraphNet, FIGConvUNet ou DoMINO ;
ces noms constituent un menu de surrogates, jamais un résultat de calcul.

Cette exhaustivité est une couverture de travail, pas une reconstruction
géométrique : 664 tâches peuvent commencer l'acquisition de CAO éditable et
d'interfaces, trois tâches de soupape ont un jalon F2 dédié, une tâche vise
l'inférence virtuelle F2, trois tâches `202-16` configurées visent la résolution
de topologie et d'interfaces, et douze tâches `104-01` configurées visent la
résolution du circuit, de ses interfaces et des propriétés d'huile. Une tâche
`104-05` configurée vise désormais la topologie du refroidisseur, ses interfaces,
les propriétés huile/air et la commande du ventilateur, tandis que 5 329 doivent
d'abord résoudre leur
applicabilité. Les
6 013 décisions matière, procédés de fabrication, calculs de référence,
surrogates PhysicsNeMo, validations SimReady et libérations restent fermées.

Ces 12 864 lignes ne forment pas la nomenclature d'une voiture : elles mélangent
les variantes, millésimes, carrosseries, boîtes, transmissions, options et
remplacements du catalogue. La graine Turbo donne maintenant une cible
canonique de travail ; il reste à résoudre ses règles d'exclusion et à rattacher
chaque instance montée à son illustration sans recopier les données protégées
du catalogue.

Le graphe `twins/vehicle-993/functional-flow-graph-f0.json` définit ensuite les
bilans intersystèmes. Ses dix familles de flux et 29 arêtes couvrent les vingt
paires d'interfaces du programme et relient les 239 paquets d'illustration à
leurs échanges de puissance, efforts, fluides, chaleur, hydraulique,
électricité, signaux et cinématique. Les équations de conservation sont écrites
avant les résultats. Les sept missions véhicule restent toutes bloquées avec
zéro port quantifié, zéro bilan fermé et zéro résultat PhysicsNeMo.

La scène `twins/vehicle-993/usd/993-functional-flow-f0.usda` projette ce graphe
en OpenUSD F0 : dix marqueurs système et 29 courbes, sans géométrie véhicule,
matériau, collision ou schéma physique. Le préflight NVIDIA en lecture seule du
2 septembre 2026 confirme que la source est lisible et la destination
préparable. Il bloque toutefois avant validation sur l'absence des API Python
OpenUSD, d'Asset Validator, de SimReady Foundation et de services sains OVRTX,
Material et Physics. Cette scène n'est donc ni SimReady ni une voiture simulée.

La fédération `work/pet-993/openusd/pet-993-part-masters-f0.usda` couvre
désormais tous les 6 013 maîtres PET dans seize sous-couches OpenUSD. Les prims
portent l'identité documentaire, les 6 325 appartenances système, la priorité,
l'archétype, les preuves disponibles et la prochaine porte d'ingénierie. Les
descriptions et références restent dans cette sortie de travail non versionnée ;
`twins/pet-993/openusd-federation-f0.json` n'en conserve que les comptes et
empreintes. Cette couverture reste F0 : zéro géométrie, zéro position véhicule,
zéro matière qualifiée, zéro résultat de solveur, zéro validation PhysicsNeMo ou
SimReady et zéro libération de fabrication.
Neuf des maîtres sont en outre reliés, par égalité exacte de référence OEM, à
une enveloppe OpenUSD F1 et à son source OpenSCAD existant. Les liens sont
explicitement candidats : aucune enveloppe n'est composée dans la voiture,
positionnée ou créditée comme géométrie de montage.
Ces neuf dossiers sont maintenant remplacés, comme état courant, par leurs
contrats spécialisés. Avec les 35 maîtres `202-16` restants, les 81 maîtres
`104-01` et les 41 maîtres `104-05`, 5 842 tâches
restent `F0_reference`. Le berceau Turbo, déjà contraint pour la cible
d'intégration, est routé vers la reconstruction F2 de ses interfaces.

### Atlas visuel complet du catalogue PET

`scripts/generate_pet_993_visual_proxy_atlas.py` donne une présence 3D à chacun
des 6 013 maîtres sous forme de symbole OpenUSD instancié. Quarante-deux prototypes
différencient les archétypes mécaniques et dix grilles séparent les systèmes
PET. La scène composée
`work/vehicle-993/openusd/993-pet-catalogue-digital-twin-f0.usda` rassemble la
fédération documentaire, les 6 013 proxies et le graphe fonctionnel.

Le routage déterministe associé couvre les 6 013 maîtres : 5 380 hypothèses
reposent sur des mots-clés de description et 633 routes utilisent uniquement le
contexte du système PET principal. Aucune n'est déclarée relue par un humain.
Les replis système ne constituent pas une classification de pièce et le routage
vers un domaine de simulation ne constitue pas un résultat de solveur.

Le contrat `twins/pet-993/material-process-routing-f0.json` couvre aussi les
6 013 maîtres avec quinze profils de présélection matière-procédé-modèle. Il
signale 5 405 tâches ayant au moins une route additive candidate et 450 tâches
où une famille titane peut seulement être étudiée avec les huit contrôles
spécifiques du programme. Les 275 articles de service, étiquettes et lignes
documentaires sont routés vers spécification ou fournisseur qualifié, sans les
forcer dans une fabrication additive. Toutes les sélections et validations
restent à zéro tant que les entrées propres à la pièce manquent.

Le crosswalk `twins/pet-993/porschefanatics-crosswalk-f0.json` ajoute une
preuve commerciale bornée : six revendications `replacesOem` exactes se
rattachent à deux maîtres PET. Elles décrivent des alternatives du marché et
leurs procédés déclarés, mais aucune des six ne possède une base matière
qualifiée. Le programme interdit donc d'en déduire la géométrie ou la matière
OEM, l'équivalence fonctionnelle, le procédé choisi ou une libération de
fabrication. Les 29 400 fiches à compatibilité 993 générale ne créent aucun
lien pièce-maître sans référence OEM explicite.

### Repère véhicule F1 sourcé

Le fichier `twins/vehicle-993/usd/993-reference-frame-f1.usda` convertit les
sept cotes documentées de l'enveloppe OpenSCAD en un repère OpenUSD exprimé en
mètres. Il matérialise une cage d'encombrement, les voies avant et arrière,
l'empattement, une ligne de garde au sol et l'axe médian. Quatre relations
mathématiques simples vérifient que l'empattement, les voies et la garde au sol
restent à l'intérieur de l'enveloppe publiée.

Quatre contraintes massiques de la même page sont conservées séparément :
1 370 kg à vide, 1 690 kg en masse totale, 720 kg maximum à l'avant et
1 065 kg maximum à l'arrière. Les différences calculées de 320 kg de charge
utile documentaire et 95 kg de marge cumulée des capacités d'essieux sont des
contrôles arithmétiques, pas un modèle de répartition de masse.

Ce repère ne résout pas les porte-à-faux : la position longitudinale des deux
essieux est une hypothèse d'affichage explicitement marquée. Le contrat
`twins/vehicle-993/reference-frame-openusd-f1.json` crédite donc sept dimensions
sourcées, cinq primitives de référence, mais zéro surface de carrosserie, zéro
interface F2 et zéro pièce positionnée. La préflight CAD-to-SimReady étant
bloquée, aucun matériau, schéma physique ou statut SimReady n'est attribué.

Ce jalon ferme la couverture visuelle, pas la reconstruction mécanique. Les
dimensions des symboles servent uniquement à l'affichage et les translations
sont des indices de grille : zéro symbole n'est crédité comme géométrie
d'ingénierie ou position véhicule. Ils ne portent ni collision, ni masse, ni
matériau qualifié, ni résultat de solveur. Ils sont également exclus des jeux
d'entraînement et de validation PhysicsNeMo.

Les prototypes, l'atlas complet et la scène composée passent tous les trois
`usdchecker --strict` avec Apple USD Tools 0.25.11. Le rapport versionné
`twins/pet-993/visual-proxy-atlas-openusd-validation-f0.json` est lié par
empreinte aux actifs validés. Ce succès confirme la conformité OpenUSD et la
résolution de composition, pas SimReady : NVIDIA Asset Validator et SimReady
Foundation restent hors de cette preuve.

Le contrat sépare les modèles mathématiques de référence, les surrogates
PhysicsNeMo et la fédération Omniverse. Aucun matériau ni procédé n'est choisi
sans géométrie, environnement, charges et propriétés dépendantes du procédé.
PhysicsNeMo reste désactivé sans corpus de solveur convergé. La chaîne SimReady
reste bloquée avant préflight faute de source véhicule complète et de services
OVRTX/Material/Physics actuellement vérifiés.

Avec l'absence assumée de nouvelle métrologie ou de nouveaux essais, la cible
maximale est un `F3_engineering` virtuel avec incertitudes et domaines de
validité. Cela ne permet pas d'atteindre `F4_correlated`, de revendiquer un
véhicule réel fonctionnel, ni de libérer une pièce critique pour fabrication.

## Ordre de construction

| Tranche | Zone | Premier test |
|---|---|---|
| DT-01 | Tableau de bord | insertion et clipsage du cache d'interrupteur |
| DT-02 | Porte | montage et débattement de la poignée |
| DT-03 | Glissière de siège | symétrie, collision et accès aux fixations |
| DT-04 | Baie moteur | interfaces du berceau, sans validation structurelle |
| DT-05 | Repère caisse | rattachement des zones aux points de référence carrosserie |

La carrosserie complète et les scans visuels viennent ensuite comme contexte.
Cette séquence permet de tester une première pièce sans attendre plusieurs mois
de reconstruction de la voiture entière.

## Ce que signifie « testé dans le jumeau »

- `geometry_ready` : toutes les géométries et incertitudes requises existent ;
- `digitally_checked` : toutes les règles déclarées ont été exécutées et le
  rapport est versionné ;
- `physically_correlated` : un montage réel a été comparé aux prédictions.

La corrélation physique reste un niveau futur. Pour une pièce critique, un
succès numérique ne remplacera ni la revue d'ingénierie ni les essais matière et
fatigue si une fabrication est un jour décidée.
