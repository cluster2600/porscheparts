# Programme véhicule Porsche 993 — reconstruction virtuelle

Ce dossier transforme le squelette du catalogue 993 en programme d'ingénierie
vérifiable. Il ne contient pas encore une voiture reconstruite. Il fournit le
contrat qui empêche de confondre une référence catalogue, une pièce montée, une
géométrie CAO, un calcul et une preuve de fonctionnement.

## Point de départ mesuré par le dépôt

- 10 familles PET ;
- 239 illustrations devenues 239 lots de travail ;
- 12 864 lignes de référence agrégées ;
- 12 879 jumeaux documentaires PET F0, dont 15 références relues en contexte ;
- 6 013 jumeaux maîtres, un par référence OEM normalisée ;
- 6 013 tâches d'ingénierie inverse, une par jumeau maître ;
- 9 fiches de pièce, 4 composants, 2 assemblages et 3 zones de jumeau
  actuellement enregistrés ;
- 18 proxys de pièce visibles en OpenUSD : quatre roues et quatorze enveloppes
  de produits dimensionnés ;
- 0 lot F2, 0 lot F3, 0 calcul véhicule de référence, 0 surrogate véhicule
  PhysicsNeMo et 0 véhicule SimReady.

Les 12 864 lignes ne sont **pas** 12 864 pièces montées sur une voiture. Le
catalogue mélange variantes, carrosseries, millésimes, boîtes, transmissions,
options et remplacements. `VEH-00` doit produire une configuration et une
nomenclature cohérentes avant tout assemblage véhicule.

L'inventaire exhaustif est décrit par `twins/pet-993/index-f0.json`. Les dix
shards JSONL complets sont générés sous `work/pet-993/` afin de conserver les
lignes détaillées dans la frontière de droits PorscheFanatics et de ne pas
versionner les transcriptions PET dans ce dépôt.

`variant-configurations-f0.json` instancie huit contrats séparés : Carrera,
Carrera 4, Carrera S, Carrera 4S, RS, Turbo, Turbo S et GT2. La Turbo est la
première cible d'intégration parce que la fiche source la marque `mvp`. Seules
13 références relues peuvent actuellement être affectées à une variante, pour
28 liens au total ; aucun des huit BOM n'est complet.

Ces huit fiches ne couvrent pas l'univers 993 : elles sont toutes des coupés.
Le PET contient 62 annotations `CABRIO`, 33 `TARGA`, 16 familles de codes moteur,
13 familles de codes de boîte et 56 familles de codes option.
`configuration-axes-f0.json` isole désormais quatre contrats provisoires :
Cabriolet (73 occurrences candidates), Targa (50), boîte manuelle 6 rapports
familles G50/G64 (89) et Tiptronic 4 rapports famille A50 (2). Le sommaire PET
confirme l'interprétation des familles de boîte, mais ces axes ne sont pas encore
combinés avec variante, millésime, marché, moteur et options ; ils ne forment
donc aucun BOM véhicule complet.

`configuration-roster-f0.json` effectue ensuite une intersection conservatrice
des trois tableaux PET `SUMMARY TYPES`, `SUMMARY ENGINES` et
`SUMM.TRANSMISS.`. Il conserve 69 lignes type/VIN, 34 options moteur et 40
options de boîte, qui produisent 149 configurations candidates pour 67 lignes
type. Deux plages Carrera RS 1996 restent sans boîte explicite. La file de revue
de 151 entrées place ces lacunes et les douze candidats Turbo en tête. Aucun de
ces candidats n'est relu, promu ou considéré comme un BOM véhicule.

`configuration-part-links-f0.json` rattache les occurrences PET à ce registre
lorsqu'une occurrence possède une quantité positive unique et une seule famille
de contrainte : variante, carrosserie, moteur ou boîte. Sur 694 occurrences
éligibles, 682 produisent 24 063 liens vers les 149 configurations candidates.
Les douze non résolues révèlent précisément les contrats encore absents :
Carrera S, Carrera 4S, Turbo S et A50.07. Le code `Z64.20` est correctement isolé
comme pont avant et non comme boîte de vitesses. Un lien ne filtre
qu'une dimension ; il ne constitue ni une entrée de BOM, ni une preuve de montage.

`turbo-integration-seed-f0.json` fixe désormais une hypothèse d'assemblage
réversible : Turbo Coupé 1998 RoW, M64.60 et G64.51. Elle fusionne dix
occurrences Turbo relues avec 315 contraintes compatibles de carrosserie,
moteur, boîte ou variante. Après dédoublonnage, la graine couvre 325 occurrences,
316 maîtres et les dix systèmes, mais seulement 74 des 239 illustrations. Les
12 554 occurrences restantes ne sont pas déclarées incompatibles : elles ne
sont simplement pas encore résolues pour cette configuration. Le total candidat
de 580 instances n'est donc pas un nombre de pièces véhicule ni un BOM.

`configuration-exceptions-f0.json` trace maintenant ces douze occurrences dans
quatre contrats dédiés : huit Carrera S, deux Carrera 4S, une Turbo S et une
A50.07. Carrera S/4S sont ancrées par l'ordre d'information PET, Turbo S par
l'option M092, et A50.07 par son annotation de pièce. Le rapprochement possible
avec A50.05/A5007 reste explicitement non résolu et aucune exception n'est
promue en configuration ou en BOM.

La lecture automatique conservatrice de la colonne PET `Model` ajoute 173
candidats non promus, soit 178 liens : 108 candidats concernent la Turbo et un
seul la Turbo S. Ils restent séparés des 13 références relues par un humain.
GT2 reste sans affectation prouvée ou candidate directe.

`manual-evidence-routing-f0.json` route maintenant les 2 496 faits quantitatifs
du registre du manuel d'atelier. Les groupes de réparation et en-têtes placent
2 442 faits dans les dix systèmes véhicule ; 54 occurrences OCR restent sans
système fiable. Une correspondance de description exacte, limitée au même
système, produit 1 569 liens de revue vers 417 maîtres PET. Ces liens restent des
candidats : aucun couple, filetage ou dimension du manuel n'est automatiquement
attribué à une référence OEM.

`twins/pet-993/engineering-readiness-f0.json` transforme cette couverture en
file de travail exhaustive sans inventer de CAO. Elle classe 317 tâches `P0`
possédant une preuve d'intégration Turbo, puis 206 `P1`, 161 `P2`, 2 617 `P3`
et 2 712 `P4` selon l'applicabilité et la criticité des systèmes. Parmi les
6 013 références, 677 peuvent passer à l'acquisition de géométrie éditable et
d'interfaces, trois soupapes ont une porte F2 dédiée, une tâche vise l'inférence
virtuelle F2, trois tâches configurées de la planche `202-16` visent la
résolution de topologie et d'interfaces, et 5 329 restent bloquées sur la
configuration. Aucune tâche n'est
encore relue comme dossier d'ingénierie, et aucun résultat de solveur n'existe.
Les candidats PhysicsNeMo sont routés par domaine depuis le snapshot NVIDIA
`4fbfcfd62bf050b48ceec6b438da409b9f4644b3` ; leur exécution reste désactivée.
Quatre dossiers d'ingénierie existants du catalogue sont également raccordés à
huit maîtres PET. Ce raccord transporte uniquement leurs hypothèses et limites
vers la file de revue : il ne sélectionne ni matière, ni procédé, ni géométrie,
ni résultat de validation.
Le contrat `twins/pet-993/engineering-evidence-links-f0.json` y ajoute dix cas
de charge uniques provenant des jumeaux catalogue et des contrats moteur. Ils
restent tous à l'état bloqué et rendent explicites les données encore requises
pour les soupapes, les K16 et le berceau moteur.

## Architecture

`program-definition.json` est la définition humaine : politiques de preuve,
domaines de calcul, interfaces entre systèmes, lots fonctionnels, usage des LLM,
PhysicsNeMo et séquence Omniverse. Le générateur la combine avec
`catalog/reference/993-assembly-skeleton.json` pour produire `program-f0.json`.

`functional-flow-graph-f0.json` rend les interfaces système calculables. Dix
types de flux décrivent couple et puissance, torseurs structurels, masse et
enthalpie des fluides, hydraulique, électricité, signaux, cinématique, état
véhicule, thermique et efforts conducteur. Vingt-neuf arêtes couvrent les vingt
paires d'interfaces physiques déclarées ainsi que neuf liens de configuration.
Les 239 paquets d'illustration sont reliés à ces arêtes système. Sept missions
virtuelles — démarrage, accélération, freinage, virage, arrêt chaud, manœuvre et
pointe électrique — possèdent maintenant un contrat, mais aucune ne passe tant
que les ports et bilans ne sont pas quantifiés.

`usd/993-functional-flow-f0.usda` rend cette topologie inspectable dans un outil
OpenUSD : dix marqueurs système et 29 courbes colorées, en mètres et axe Z. Il
s'agit d'un diagramme F0, sans géométrie de pièce, masse, collision, matériau ou
schéma physique. Le préflight NVIDIA CAD-to-SimReady en lecture seule accepte le
fichier comme entrée, mais reste bloqué sur les API Python OpenUSD, Asset
Validator, SimReady Foundation et les services OVRTX, Material et Physics. Le
résultat est capturé dans `functional-flow-simready-preflight-f0.json` ; aucune
validation ou assignation SimReady n'est revendiquée.

Le catalogue complet possède aussi une fédération OpenUSD F0 générée sous
`work/pet-993/openusd/pet-993-part-masters-f0.usda`. La couche racine compose
seize couches indexées par hash et expose exactement 6 013 prims de jumeau
maître, 12 879 occurrences documentaires et 6 325 liens d'appartenance système.
Chaque prim transporte son état de configuration, priorité, archétype, prochaine
porte, preuves déclarées et états de calcul. Il ne contient encore aucune
géométrie ou transformation véhicule. Les références et descriptions détaillées
restent dans `work/`; seul le manifeste agrégé et ses empreintes sont versionnés
dans `twins/pet-993/openusd-federation-f0.json`.
Neuf maîtres possèdent maintenant un lien candidat vers un proxy OpenUSD et son
source OpenSCAD, obtenu par égalité exacte de la référence OEM normalisée. Ces
neuf enveloppes restent non composées et non positionnées : le lien prouve une
identité candidate, pas la forme ou le montage.
Leur état courant est maintenant spécialisé : deux proxies K16, cinq proxies de
chaîne d'air, un proxy d'écran thermique et un proxy de support moteur contraint
par la masse. Le contrat K16 couvre en plus deux révisions PET sans proxy
d'enveloppe propre, soit quatre tâches K16 au total. Aucun maître ne
reste dans l'état générique `F1_envelope_identity_linked_unvalidated`. Le
support moteur passe à la porte
`infer_and_cross_check_F2_interface_coordinates_with_uncertainty`; cela ne lui
accorde toujours aucune géométrie F2, aucun résultat CAE et aucun crédit
SimReady.

La planche PET `202-16` est maintenant couverte par un contrat F1 non spatial :
71 occurrences se ferment sur 40 maîtres exacts. Les K16 et l'écran thermique
conservent leurs contrats plus spécifiques ; les 35 autres maîtres passent à
`F1_turbo_lubrication_control_topology_readiness_unvalidated`. Le diagramme
OpenUSD, ses dix équations et ses six cas bloqués ne fournissent ni géométrie de
pièce, ni matière, ni résultat de solveur, ni validation SimReady.

Les huit lots fonctionnels sont :

1. `VEH-00` — configurations, nomenclature, repères, masse et inerties ;
2. `VEH-10` — caisse porteuse et enveloppe ;
3. `VEH-20` — châssis roulant ;
4. `VEH-30` — groupe motopropulseur ;
5. `VEH-40` — fluides et thermique ;
6. `VEH-50` — électricité et commandes ;
7. `VEH-60` — habitacle et retenue ;
8. `VEH-90` — intégration, scène OpenUSD et missions véhicule.

Chaque illustration PET reste `F0_reference` tant que l'identité de la variante,
la CAO éditable, les transformations, interfaces, tolérances, matières, charges
et critères ne sont pas documentés.

## Modèles mathématiques et PhysicsNeMo

Les solveurs déterministes restent les références : CAO et empilements de
tolérances, CalculiX, OpenFOAM, modèles 0D/1D, cinématique/multicorps, dynamique
véhicule, réseau électrique et logique de contrôle. Les solveurs MBD, crash et
électrique doivent encore être sélectionnés puis validés par des cas analytiques.

La découverte NVIDIA du 2 septembre 2026 confirme un menu de surrogates :
GeoTransolver, Transolver, MeshGraphNet et FIGConvUNet pour les champs sur
géométries irrégulières ; DoMINO et FIGConvUNet pour l'aérodynamique externe.
Ils restent désactivés jusqu'à l'existence d'un DOE de solveur convergé, de jeux
séparés par famille de géométrie/charge, de seuils d'erreur et d'une abstention
hors domaine.

Un LLM peut extraire des faits sourcés, proposer des hypothèses et générer des
tests. Il ne remplace ni un solveur, ni une cote, ni une qualification matière,
ni une autorité de sécurité.

## Omniverse / SimReady

Le statut véhicule est `blocked_before_preflight`. Il manque une source CAO
véhicule, des assemblages F2/F3 et une disponibilité actuelle vérifiée des
services OVRTX, Material et Physics. La séquence obligatoire est conservée dans
le contrat : source, préflight, contexte, conversion, validation USD minimale,
assignation, conformance, validateurs, rendu et package.

Le préflight de validation locale exécuté le 2 septembre 2026 sur le proxy USD
du berceau moteur est `blocked` : `pxr`, Asset Validator et le checkout
SimReady Foundation sont absents. Cette preuve empêche explicitement de
présenter les proxys actuels comme validés par Omniverse.

Les USD F1 existants peuvent être contrôlés comme fichiers OpenUSD. Cela ne
constitue ni une validation SimReady, ni une simulation, ni une preuve de
fonctionnement.

## Commandes

```bash
make vehicle-993-program
make vehicle-993-program-check
make vehicle-993-turbo-seed
make vehicle-993-turbo-seed-check
make vehicle-993-flow-graph
make vehicle-993-flow-graph-check
make vehicle-993-flow-usd
make vehicle-993-flow-usd-check
make pet-993-openusd
make pet-993-openusd-check
make vehicle-993-configuration-axes
make vehicle-993-configuration-axes-check
make vehicle-993-configuration-roster
make vehicle-993-configuration-roster-check
make vehicle-993-configuration-part-links
make vehicle-993-configuration-part-links-check
make vehicle-993-configuration-exceptions
make vehicle-993-configuration-exceptions-check
make vehicle-993-variants
make vehicle-993-variants-check
make pet-993-engineering-readiness
make pet-993-engineering-readiness-check
make pet-993-engineering-evidence
make pet-993-engineering-evidence-check
make vehicle-993-manual-evidence
make vehicle-993-manual-evidence-check
```

Le premier régénère le manifeste. Le second échoue si le squelette, la définition
ou l'inventaire ont changé sans mise à jour du manifeste.

## Plafond de preuve

Avec la contrainte de ne recevoir aucune mesure ni aucun essai physique
supplémentaire, le programme peut atteindre au mieux `F3_engineering` virtuel
pour les pièces disposant d'entrées suffisantes. `F4_correlated`, la sécurité
réelle, l'aptitude routière et la libération de fabrication fonctionnelle restent
impossibles à démontrer.
