# Jumeaux documentaires du catalogue PET 993

Ce dossier matérialise tout le catalogue PET 993 au niveau documentaire
`F0_reference`. L'index versionné décrit 12 879 occurrences et 6 013 jumeaux
maîtres de référence OEM :

- 12 864 transcriptions automatiques `listed` ;
- 15 références relues dans leur contexte PET ;
- 6 013 références OEM distinctes ;
- 239 illustrations réparties dans les dix systèmes `0xx` à `9xx`.

Une occurrence n'est pas une pièce montée. La même vis, rondelle ou référence
peut appartenir à plusieurs illustrations, tandis que le catalogue mélange
variantes, carrosseries, années, transmissions, options et remplacements.

## Frontière des droits

Les sources détaillées restent dans le dépôt sibling PorscheFanatics. Les PDF
PET, illustrations et scans ne sont pas copiés ici. Le dépôt versionne seulement
`index-f0.json`, qui contient les comptes, les empreintes SHA-256, le statut des
droits déclaré par la source et les empreintes des dix shards générés.

`catalog-crosswalk-f0.json` relie les références OEM portées par les fiches
`catalog/parts/*.json` aux occurrences PET. Ce lien affirme uniquement une
identité documentaire. Les revendications de variante, compatibilité
géométrique et libération de fabrication restent toutes à `false`.

`applicability-evidence-f0.json` exploite uniquement la colonne `Model` écrite
sur la ligne d'une référence dans l'extraction KAT 517 Porsche Classic. Il
recense 1 002 occurrences annotées et 173 candidats de BOM à quantité unique,
soit 178 liens de variante. Les titres de section, codes moteur, boîte, option
et carrosserie ne sont jamais promus automatiquement. Le texte PET brut reste
hors du dépôt et son empreinte SHA-256 ferme la provenance.

Les records complets sont produits sous `work/pet-993/twins/*.jsonl`, ignoré par
Git. Chaque ligne est un jumeau stable comprenant :

- référence OEM, description et contexte PET ;
- système, illustration et lot `WP-993-*` ;
- niveau de lecture de la source ;
- variantes et quantité uniquement lorsqu'elles sont prouvées en contexte ;
- état CAO, matière, interfaces, solveur, PhysicsNeMo et SimReady ;
- interdictions explicites de montage, fabrication et usage routier.

Les seize shards `work/pet-993/part-masters/*.jsonl` regroupent toutes les
occurrences partageant une référence OEM normalisée. Un maître conserve les
descriptions, révisions, systèmes, illustrations, observations matière et
preuves de variantes par contexte. Il ne transforme jamais ces observations en
matière choisie, compatibilité universelle ou équivalence de remplacement.

`visual-proxy-atlas-f0.json` ferme la couverture visuelle des 6 013 maîtres.
Le générateur instancie 42 symboles d'archétype dans seize couches
OpenUSD et les range dans dix grilles système déterministes. La scène
`work/vehicle-993/openusd/993-pet-catalogue-digital-twin-f0.usda` compose le
graphe documentaire, cet atlas et la topologie des flux dans un seul actif.
Les formes distinguent les familles pour la navigation ; leurs dimensions et
positions ne représentent ni la pièce réelle ni son montage dans la voiture.

La première cible d'assemblage est fixée dans
`twins/vehicle-993/turbo-integration-seed-f0.json` : Turbo Coupé 1998 RoW,
M64.60 et G64.51. Ses 325 occurrences candidates couvrent 316 maîtres et les dix
systèmes. Ce sous-ensemble reste une graine, pas une BOM : 5 697 maîtres et
12 554 occurrences sont encore hors de cette sélection.

`engineering-readiness-f0.json` indexe désormais une tâche d'ingénierie inverse
pour chacun des 6 013 maîtres. Les seize shards correspondants sont générés sous
`work/pet-993/engineering-readiness/*.jsonl`. Chaque tâche fixe sa criticité, ses
domaines de calcul, ses preuves de configuration, sa prochaine porte et
l'obligation de faire précéder tout surrogate PhysicsNeMo par un solveur de
référence convergé. Chaque tâche reçoit la liste des modèles PhysicsNeMo
compatibles avec ses domaines, vérifiée sur le dépôt NVIDIA au commit
`4fbfcfd62bf050b48ceec6b438da409b9f4644b3`, mais aucun modèle n'est encore
sélectionné ni exécuté. La file contient 317 priorités `P0` liées à l'intégration
Turbo, 206 `P1`, 161 `P2`, 2 617 `P3` et 2 712 `P4`.

Le routage d'archétype couvre les 6 013 maîtres sans laisser de route vide :
5 380 routes sont des hypothèses lexicales tirées des descriptions PET et 633
sont seulement des replis sur le système PET principal. Ces 633 replis ne sont
pas des classifications de pièce. Les 6 013 routes restent non relues par un
humain et ne valent ni identification géométrique, ni sélection de matière, ni
résultat de solveur. L'audit et ses règles sont conservés dans
`engineering-readiness-f0.json`.

`material-process-routing-f0.json` ajoute ensuite un dossier de présélection à
chacun des 6 013 maîtres. Les 42 archétypes sont regroupés en quinze profils de
propriétés, procédés et modèles mathématiques de référence. Les sorties de
travail contiennent 6 013 routages : 5 405 ont au moins une route additive à
étudier, 450 incluent une famille titane avec les huit contrôles supplémentaires
obligatoires, et 275 lignes de service, étiquette ou documentation restent des
articles de spécification ou d'approvisionnement au lieu d'être artificiellement
transformées en pièces imprimables. Ces nombres sont un triage, pas un choix :
zéro matière, zéro procédé et zéro solveur sont sélectionnés.

`porschefanatics-crosswalk-f0.json` rattache les données du catalogue
PorscheFanatics uniquement lorsque `replacesOem` correspond exactement à une
référence maître PET normalisée. Sur 109 316 fiches commerciales, six liens
explicites concernent deux maîtres PET. Les six portent une désignation matière
sans base qualifiée : elles restent donc des observations sur des alternatives
commerciales, et non la matière OEM, une équivalence fonctionnelle ou une route
de fabrication sélectionnée. Les rapprochements par nom, description,
catégorie, compatibilité 993 générale ou LLM sont interdits par ce contrat.

Cette file ne contient encore aucun calcul composant de référence. Sur les
6 013 tâches, 684 disposent d'une preuve de configuration ; 664 sont routées
vers l'acquisition générique d'une CAO éditable et d'interfaces mesurées, tandis
que 20 suivent une porte spécialisée déjà définie. Les 5 329 autres doivent
d'abord résoudre leur applicabilité. Les compteurs de géométries
éditables, matières qualifiées, solveurs de référence, résultats PhysicsNeMo,
assets SimReady et libérations de fabrication restent tous à zéro.

Une seule tâche, le berceau moteur `993 115 021 53`, possède désormais un
surrogate structurel F1 contraint par son enveloppe et sa masse documentaires.
Le tube creux uniforme ferme mathématiquement 1,96 kg et produit deux bornes de
sensibilité en flexion. Ses interfaces restent deux domaines de recherche sans
point sélectionné : le compteur F2 reste donc à zéro, comme son crédit CAE
composant.

Trois maîtres supplémentaires possèdent un surrogate dimensionnel F1 éditable :
soupape d'admission `993 105 409 02`, échappement Carrera `993 105 419 01` et
échappement Turbo `993 105 419 52`. Les deux profils d'échappement conservent
leurs trois dimensions commerciales ; l'admission garde sa longueur comme
hypothèse. Leurs géométries de siège, guide et clavettes, leurs tolérances et
leurs propriétés à chaud restent inconnues. La partition de fidélité est
désormais de 5 842 maîtres F0, trois surrogates de soupapes F1, quatre guides
K16, cinq guides de chaîne d'air, un écran thermique, un berceau moteur, 35
maîtres de topologie `202-16`, 81 maîtres de topologie `104-01` et 41 maîtres de
topologie `104-05`, sans géométrie F2 ni résultat de solveur.

Les huit scènes d'ingénierie du berceau, des trois soupapes, des deux K16, des
cinq composants de suralimentation, de l'écran thermique et des topologies
`202-16`/`104-01`/`104-05` passent les contrôles OpenUSD stricts, pour 97
primitives guides et 171 maîtres PET liés. Cette conformité OpenUSD
n'est pas une validation NVIDIA Asset Validator ou SimReady ; ces étapes restent
bloquées par le préflight des services.

Le rapport `k16-envelope-flow-readiness-f1.json` raccorde quatre maîtres PET à
deux boîtes d'encombrement, deux masses et quatre coupons de diamètre réservés
au côté droit. Il enregistre aussi six équations 0D, toutes non évaluées faute de
cartes et de conditions de fonctionnement K16. Les candidats PhysicsNeMo sont
documentés au commit vérifié, mais aucun modèle n'est sélectionné ni exécuté.
Les suggestions de matières par sous-ensemble restent des hypothèses LLM non
sourcées ; aucune voie fonctionnelle CNC ou additive n'est libérée.

Le rapport `oil-tank-circuit-topology-readiness-f1.json` relie les 153
occurrences de la planche `104-01` à 81 maîtres exacts, dont 72 vus dans les
deux sources PET. Il formalise onze équations de bilan hydraulique, thermique,
de niveau et d'aération, quarante paramètres inconnus et sept cas de charge
bloqués. Son OpenUSD est un graphe non spatial : raccords, cotes, matières,
positions véhicule et liaison au retour turbo restent à démontrer.

Le rapport `oil-cooler-circuit-topology-readiness-f1.json` relie les 80
occurrences de la planche `104-05` à 43 maîtres exacts, dont 37 vus dans les
deux sources PET. Il formalise quatorze équations symboliques, quarante-quatre
paramètres inconnus et huit cas de charge bloqués autour de l'échangeur, des
conduites, du guidage d'air, du ventilateur et de la sonde de température. Son
OpenUSD reste un graphe non spatial sans interface, matière qualifiée, calcul de
référence ou résultat PhysicsNeMo ; deux maîtres communs à un contrat antérieur
conservent donc leur état spécialisé plus prioritaire.

Le rapport `charge-air-chain-readiness-f1.json` relie cinq autres maîtres PET de
la planche 107-45 : les deux durites, l'échangeur, le conduit d'air et la sonde de
température. Il produit cinq enveloppes F1 et huit équations 0D non évaluées. Les
diamètres 43/57 mm d'un kit aftermarket sont isolés en coupons non positionnés ;
une paire 66/68 mm incohérente est mise en quarantaine. Aucun diamètre n'est
promu en interface OEM, aucune matière n'est sélectionnée et aucun calcul
PhysicsNeMo ou SimReady n'est revendiqué.

Les tâches incorporent aussi le routage du manuel d'atelier sans promouvoir son
OCR : 417 maîtres possèdent au moins un candidat de revue, pour 1 569 liens au
total. Chaque lien conserve la page, la collection et l'ambiguïté lexicale ; le
compteur de cotes ou couples attribués automatiquement reste à zéro.

Le crosswalk des fiches d'ingénierie détaillées relie en outre quatre dossiers
du catalogue à huit maîtres PET : berceau moteur, soupapes d'admission et
d'échappement, et paire de turbocompresseurs K16. Les tâches exposent leurs
hypothèses de géométrie, matière, procédé et validation pour revue, mais n'en
font aucune décision qualifiée. Les compteurs de promotions matière, procédé,
géométrie ou validation restent à zéro.

`engineering-evidence-links-f0.json` complète ce raccord avec trois contrats de
jumeau catalogue, quatre proxys moteur et dix cas de charge uniques. Les
soupapes héritent des contrats thermique, dynamique et distribution ; les K16
du contrat CFD compressible, thermique et rotordynamique ; le berceau de six cas
structurels et modaux. Les treize liens pièce-cas sont tous bloqués faute
d'entrées : aucun calcul de référence ou PhysicsNeMo n'est promu.
Le contrat ajoute séparément cinq liens d'identité vers le lot de chaîne d'air,
portant à treize le nombre de tâches dotées d'une preuve d'ingénierie liée, sans
crédit CAE ou libération.

Le registre `catalog/reference/993-declared-part-data.json` enrichit neuf
jumeaux maîtres avec un encombrement déclaré. Un seul possède aussi une famille
matière non générique : le berceau moteur, avec « acier » inféré. Ces valeurs
restent des observations tierces ; le compteur de matières qualifiées demeure
à zéro.

## Génération

```bash
make pet-993-twins
make pet-993-twins-check
make pet-993-index-check
make pet-993-engineering-readiness
make pet-993-engineering-readiness-check
make pet-993-engineering-readiness-index-check
make pet-993-porschefanatics-crosswalk
make pet-993-porschefanatics-crosswalk-check
make pet-993-porschefanatics-crosswalk-index-check
make pet-993-material-process-routing
make pet-993-material-process-routing-check
make pet-993-material-process-routing-index-check
make pet-993-engineering-evidence
make pet-993-engineering-evidence-check
make pet-993-engineering-evidence-index-check
make valve-dimensional-surrogates-check
make k16-envelope-flow-surrogates-check
make charge-air-chain-surrogates-check
make engineering-guides-openusd-check
make pet-993-visual-atlas
make pet-993-visual-atlas-check
make pet-993-visual-atlas-index-check
```

`pet-993-twins` lit par défaut `../porschefanatics.com/data/oem-listed.json` et
`data/oem-parts.json`, régénère les dix shards et met à jour l'index versionné.
`pet-993-twins-check` recalcule tout depuis la source externe et compare chaque
octet, y compris le crosswalk. `pet-993-index-check` vérifie uniquement l'index
et le crosswalk versionnés et convient à un environnement ne possédant pas le
dépôt sibling.

`pet-993-engineering-readiness` reconstruit la file complète depuis les maîtres,
le registre de configurations, les liens de contraintes, les exceptions et le
contrat programme. Le mode `check` recalcule aussi les seize shards ; le mode
`index-check` contrôle le manifeste versionné sans régénération.

`pet-993-material-process-routing` dérive les quinze profils de triage depuis la
file d'ingénierie, le crosswalk PorscheFanatics et le contrat véhicule. Il
produit seize shards de travail et un manifeste versionné sans descriptions ni
références OEM. Une famille matière ou une route de procédé reste candidate
jusqu'à disponibilité de la géométrie, des charges, de l'environnement et des
propriétés dépendantes du procédé.

`pet-993-porschefanatics-crosswalk` recalcule les liens exacts depuis les onze
shards `data/parts/*.json` du dépôt sibling. Le manifeste versionné conserve les
empreintes et les comptes ; les détails commerciaux et URL restent sous
`work/pet-993/`. Le mode `index-check` vérifie les preuves versionnées sans lire
les fiches commerciales détaillées.

`pet-993-visual-atlas` régénère les 42 prototypes, les seize couches de
proxies et la scène composée. Son mode `check-index` ne dépend pas des couches
de travail ignorées par Git et vérifie les comptes, empreintes et frontières de
revendication du manifeste versionné.

`visual-proxy-atlas-openusd-validation-f0.json` lie par SHA-256 les trois
scènes racines à une exécution réussie de `usdchecker --strict` avec Apple USD
Tools 0.25.11. Ce contrôle résout aussi les dépendances des seize shards. Il ne
remplace pas NVIDIA Asset Validator et ne constitue pas une validation
SimReady.

## Ce qui reste à faire

Le catalogue entier existe désormais comme graphe documentaire, mais pas comme
CAO. Pour passer une occurrence à `F1_envelope`, `F2_interface` ou
`F3_engineering`, il faut enrichir son jumeau avec des sources autorisées de
géométrie, repères, interfaces, matière, charges, conditions aux limites et
critères. Les décisions de variante doivent construire une nomenclature
configurée ; elles ne peuvent pas être inférées de la seule présence dans PET.

L'atlas couvre visuellement 100 % des maîtres sans changer leur maturité : les
6 004 objets F0 restent F0, les neuf enveloppes F1 restent des candidats non
validés, et les compteurs de géométrie d'ingénierie, transformations véhicule,
calculs CAE, résultats PhysicsNeMo et validation SimReady restent à zéro.
