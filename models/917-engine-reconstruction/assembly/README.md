# Moteur complet de conception : quatre soupapes et turbos bioniques

Cette branche réunit **119 définitions géométriques et 1 129 occurrences** :
12 ensembles de culasse à quatre soupapes, 48 soupapes et deux turbos bioniques
à 39 composants chacun. Elle couvre les 44 familles du programme moteur F1/F3,
avec leurs remplacements modernes explicites, et ajoute guides, sièges,
ressorts doubles, retenues, goujons, joints, pompes, circuits et accessoires.
Ce périmètre de représentation est complet ; **la nomenclature de fabrication
et la définition fonctionnelle de chaque pièce ne le sont pas**.

La base de cette nouvelle variante conserve l'alésage/course FIA **85 × 66 mm**.
Ce n'est ni une réplique homologuée de la 917, ni le modèle 90 × 70,4 mm du
programme F33, ni une preuve de sa cible de puissance. Les cotes FIA passent
le validateur documentaire déjà utilisé dans la tranche précédente. Les
matériaux, les interfaces modernes et les nouvelles formes restent des
hypothèses. Le catalogue existant n'accorde aucune qualification nouvelle.

## Ce qui est repris

- La [culasse quatre soupapes air + huile](../../../docs/studies/993-air-oil-20261002/README.md),
  son corps et ses 12 maillages de soupapes, sièges et guides, exactement
  identifiés par le [manifeste publié](../../../docs/studies/993-air-oil-20261002/delivery-manifest.json).
  Les nouvelles piles de ressorts suivent les axes des guides repris ; leurs
  hauteurs installées restent des hypothèses. Aucun changement d'échelle
  n'est appliqué. Une culasse issue du scan 935 ne démontre aucune interface 917.
- Nos 39 composants du turbo bionique F0,
  sans substitution par une enveloppe K16 ou Garrett. Chaque maillage conserve
  ses coordonnées, triangles et empreinte. Cette dépendance provient d'une
  autre branche locale, au commit `aba24fd351930ed4cee194b8cc557c3b80238894`,
  pas encore accessible sur GitHub lors du contrôle. Fournir sa livraison
  locale au programme de reconstruction ; ses sources éditables sont
  conservées dans la livraison privée et ne sont pas publiées par cette PR.
Les travaux F1 du turbo en cours ne sont pas repris.
- Les générateurs PicoGK de cylindre, piston, bielle et axe ainsi que la
  cinématique et le validateur FIA des tranches précédentes, laissés intacts.
- Les fonctions de placement F1/F3 pour les accessoires conservés. Les pièces
  historiques remplacées sont comptabilisées : allumage par bobines,
  injection électronique, culbuteurs et wastegates internes.

Le maître natif F50 est documenté dans le Git, mais sa géométrie privée n'a
pas été retrouvée dans les emplacements locaux explorés. Le modèle intégré
ici est donc précisément la livraison air + huile du 2 octobre, pas une
reconstitution du maître F50 ou une ancienne culasse générique F29.

## Ce qui est créé avec PicoGK

[engine_layout.py](engine_layout.py) définit les formes, la nomenclature et les placements ;
[design.json](design.json) expose les hypothèses du mécanisme et les routes
matière/procédé. [Program.cs](Program.cs) utilise le noyau natif PicoGK 2.3.0
pour construire les composants et enregistrer des **STL et VDB séparés**.

Les demi-carters possèdent des nervures ramifiées entre les stations de palier
et l'enveloppe des cylindres. Les supports de distribution ont des branches
rayonnantes ; les collecteurs creux réunissent six branches par banc. Ces
règles bioniques sont un dessin paramétrique reproductible, sans optimisation
topologique, preuve de chemin d'effort ou performance CFD/FEA.
L'enveloppe de ces carters est elle aussi une hypothèse : elle n'est pas
recalée ni ajustée au scan 917. Les coques issues du scan restent dans la
première tranche ; elles ne sont pas remplacées ou déclarées compatibles par
ce nouvel assemblage. Leur recalage reste nécessaire avant toute fidélité
dimensionnelle ou intégration des interfaces réelles.

Le vilebrequin représente six manetons partagés, les phases déclarées et huit
paliers. Ses joues ont une épaisseur axiale limitée. Les trois gorges proposées
dans chaque piston sont soustraites au modèle antérieur, sans modifier ce
générateur. Le nouveau cylindre commence à 50 mm et mesure 160 mm : il couvre
le piston symétrique supposé de 86 mm et place le plan de culasse à 210 mm.
Ces trois valeurs **ne proviennent pas de la FIA**. La cote FIA de 43 mm est
la distance axe–calotte ; la jupe inférieure de 43 mm reste une hypothèse.
Le maneton reste à 52 mm de référence FIA ; le logement de bielle passe à
56,25 mm avec une allocation radiale supposée de 2,125 mm. L'ancien coussinet
d'environ 1 mm ne restait pas connexe sur la grille de 1 mm. Ce choix rend
le concept représentable ; il ne définit pas un coussinet de fonctionnement.

Un coussinet de bielle, une paire de clavettes et une enveloppe d'accessoire
peuvent être des unités d'assemblage. Le nombre d'occurrences ne prétend pas
compter chaque demi-coquille, filament, filet ou joint réel. Les alternateurs,
démarreurs, capteurs, injecteurs, électronique et échangeurs sont des enveloppes
d'achat ; les engrenages sont des ébauches sans denture ni loi de contact.
Les internes de ces composants d'achat ne sont pas redessinés.

Les rotations des turbos sont propres, sans miroir : leur axe reste longitudinal
et leurs raccords sont tournés vers l'extérieur de chaque banc. Les extrémités
des nouveaux conduits suivent les centres de raccord du concept F0 : entrée
chaude locale `(43, 56,25, -99,75)` mm et sortie froide `(49, 42,25, 0)` mm.
Ces centres repris ne définissent ni brides ni tolérances d'étanchéité.

Un contrôle indépendant sélectionne les sommets de soupape dont le Z local
est inférieur ou égal à 4 unités, près du plan de joint. Sous l'hypothèse
1 unité = 1 mm, leur rayon maximal dépasse le cercle d'alésage de 85 mm de
**6,238 mm à l'admission et 6,445 mm à l'échappement**. Cela signale une
incompatibilité d'enveloppe à traiter, sans établir à lui seul un contact
piston–soupape. Il faut reconstruire la chambre et l'interface cylindre–culasse
ou sélectionner une autre variante documentée ; leur compatibilité n'est
pas acquise par le placement de ces pièces.

## Reproduire et inspecter

Le programme exige une livraison turbo liée aux empreintes de
[imports.json](imports.json), .NET 9, PicoGK 2.3.0 et un environnement Python
avec NumPy, Trimesh, SciPy, Rtree, NetworkX et Matplotlib. Il refuse les
empreintes divergentes, les variantes FIA mélangées et l'écrasement d'un
dossier existant. La géométrie générée reste sous le répertoire ignoré `work/`.

```sh
python models/917-engine-reconstruction/assembly/run.py \
  --dotnet /chemin/vers/dotnet \
  --turbo-assets /chemin/vers/bionic-turbo-assembly-final \
  --output work/917-4v-biturbo-essai-001
```

Chaque grille de 1 et 0,5 mm conserve ses STL natifs, VDB et reçus. Le témoin
numérique indépendant déjà présent dans le dépôt produit un dérivé supprimant
uniquement les triangles dont le produit vectoriel est exactement nul en
float64. Aucun sommet n'est déplacé ; aucun triangle non nul n'est supprimé.
Les maillages hérités ne subissent aucune suppression. Fermeture, orientation,
volume positif, unicité du composant et absence de doublons sont inspectés.
La fidélité continue au scan et les auto-intersections continues ne sont pas
certifiées par ces contrôles.
Ces grilles ne définissent pas les tolérances de paliers, de segments ou
d'usinage. La route proposée combine impression des structures candidates,
usinage, pièces forgées et composants d'achat ; elle ne prévoit pas d'imprimer
l'ensemble du mécanisme en l'état.

L'export GLB conserve les définitions séparées et les 1 129 transformations,
avec conversion mm → m. Sa réouverture vérifie les noms, nombres, triangles et
l'erreur de transport. L'aperçu PNG utilise des points échantillonnés sur les
surfaces, uniquement pour la présentation ; les STL et le GLB gardent les triangles
des modèles contrôlés. `assembly.json` contient la nomenclature, les placements,
les empreintes des imports et la couverture F1/F3 ; `validation.json` consigne
les contrôles de mouvement et les conflits observés.

Le complément [render_surfaces.py](render_surfaces.py) lit ce même GLB avec
VTK 9.7.1 et produit quatre panneaux avec **surfaces opaques et ombrées** :
assemblage complet, mécanisme avec culasses, demi-carter avec vilebrequin et
légende. Il conserve tous les triangles, sans échantillonnage ni simplification,
vérifie les noms et placements importés et contrôle l'empreinte du GLB avant
et après le rendu. Les couleurs servent à la lecture ; elles ne qualifient pas
les matériaux. Les anciens aperçus et reçus restent conservés.
Le [reçu du rendu](surface-preview-20261011.json) lie les sources, l'image privée
et la géométrie inchangée. Le PNG demeure dans la livraison locale ignorée.

```sh
python models/917-engine-reconstruction/assembly/render_surfaces.py \
  --delivery work/917-4v-biturbo-20261011/livraison \
  --output work/917-solid-surfaces-20261011/nouveau-rendu
```

## Matériaux et étapes de qualification

Le [reçu d'exécution](execution-20261011.json) lie les sources et les résultats :
67 définitions natives contrôlées sur les deux grilles, 52 imports contrôlés
sans retouche et GLB de 119 définitions / 1 129 placements. L'erreur maximale
mesurée lors de la réouverture du GLB est inférieure à `3 × 10⁻⁸ m` ; il s'agit
d'une erreur de transport numérique, pas d'une précision physique.
Quatre conduits ont été régénérés après les rejets ; les 63 autres définitions
natives inchangées sont réutilisées avec contrôle de leurs empreintes.
La correction de l'aperçu après l'export ne change que la fonction de
présentation ; son reçu conserve cette distinction et l'empreinte du GLB.

Les 24 tests ciblés passent. Le contrôle global local a exécuté 3 638 tests,
avec 153 ignorés et deux échecs préexistants de comparaison flottante dans les
modèles 993 d'impulseur/stator inchangés. Les cibles suivantes de `make check`
ne sont pas atteintes. Les dernières corrections des conduits, poses et de
l'aperçu ont été suivies d'une nouvelle vérification ciblée.

| Famille | Route candidate | Qualification manquante |
|---|---|---|
| Culasses | CP1 LPBF, traitement et usinage des interfaces | carte matière à chaud du lot imprimé, fatigue, porosité, parois, dépoudrage, étanchéité et métrologie |
| Carters, supports, conduits froids | alliage aluminium à sélectionner, LPBF puis usinage | précharges, contraintes, rigidité, dilatation, accessibilité et joints |
| Pistons | 2618 forgé et usiné | températures, fatigue, jupe, gorges, jeux, calotte et équilibrage |
| Bielles | Ti-6Al-4V forgé et usiné | alliage et état exacts, boulons, fatigue, tenue des coussinets, équilibrage et isolation galvanique |
| Vilebrequin, axes, cames | acier à sélectionner, traitement et rectification | profils, rayons, lubrification, dureté, contacts, fatigue et dynamique |
| Collecteurs chauds | IN625 candidat, LPBF ou fabrication conventionnelle | tenue au cycle thermique, porosité, fissures, soudure, brides et inspection |
| Soupapes, ressorts, paliers, retenues, joints, électronique | composants qualifiés à acheter ou à définir avec un fournisseur | plans, tolérances, certificats, charges et conditions de service |
| Roues et arbres des turbos | définition fournisseur ou programme rotor spécialisé | aérodynamique, jeux à chaud, dynamique, équilibrage, confinement et survitesse |

[EOS décrit CP1](https://www.eos.info/metal-solutions/metal-materials/aluminium)
comme un alliage aluminium–fer–zirconium pour la fabrication additive ; cela
ne fournit pas une carte admissible de notre culasse imprimée. Pour les
soupapes d'échappement, [Special Metals décrit INCONEL 751](https://www.specialmetals.com/documents/technical-bulletins/inconel/inconel-alloy-751.pdf)
pour cet usage : cette référence est une piste fournisseur et ne qualifie
aucune soupape de cet assemblage. Aucune propriété mécanique n'est inventée
pour produire un facteur de sécurité.

La fabrication devra suivre le
[contrat matière LPBF existant](../../../twins/reference-917-engine/material-lpbf-qualification-f49.json)
et une revue professionnelle, avec alliage/lot, machine, paramètres,
orientation, supports, traitement, surépaisseurs, usinage, inspection CT/CMM,
épreuves de pression, corrosion/galvanisme et hypothèses de fatigue documentés.
Ensuite viennent les contacts et jeux à chaud, le balayage piston–soupapes,
les lois de came, les circuits réels, le calcul thermique/structural, les
cartographies des turbos et un banc instrumenté. **Les formes fermées et
les identités de cinématique ne constituent pas une autorisation d'impression
métal ou de démarrage.**
