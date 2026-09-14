# Bielle 993/993 Turbo — concept topologique Ti64 F0

TZR/PAUTER publie pour sa bielle 993/993 Turbo un entraxe de `127,00 mm`, un
axe de `23,01 mm`, un logement de tête de `58,01 ± 0,003 mm`, des largeurs de
`18,75 mm` et `19,58 mm`, ainsi qu'une masse acier de `535 g`. La fiche annonce
une option titane sur demande avec `33 %` de gain par bielle, sans publier
l'alliage, le procédé ou la masse absolue. PorscheFanatics recoupe les bielles
titane comme candidat moteur 993, mais n'apporte aucune cote.

Le F0 conserve seulement ces cotes publiées. Les diamètres extérieurs
`78/40 mm`, les deux membrures ouvertes `10 × 14 mm`, la séparation visuelle du
chapeau de `0,4 mm` et deux passages de `8,4 mm` sont des hypothèses propres au
projet. Vis, filets, coussinets, bague de pied, canal d'huile, congés qualifiés,
jeux et distribution de masse sont absents.

## Pourquoi étudier l'additif

Une topologie LPBF ouverte peut être remodelée à partir de champs de charge,
avec matière concentrée dans les chemins mécaniques et sans poche de poudre
fermée. Il faut cependant la comparer à une bielle acier 4340 forgée/usinée et
à une bielle titane conventionnelle. L'étude de Cecchel et al. sur une bielle
Ti-6Al-4V optimisée et fabriquée par SLM inclut FEA et fatigue grandeur réelle,
mais rapporte une tenue inférieure à la référence conventionnelle : une belle
topologie et une marge statique ne constituent donc pas une validation fatigue.

Le BREP OCCT et sa relecture STEP sont valides avec deux solides, corps et
chapeau. L'enveloppe F0 vaut `186,0 × 84,0 × 19,58 mm`, le volume
`77 154,68 mm³` et la masse théorique `341,02 g` à `4,42 g/cm³`. Cette masse est
`17,43 g`, soit environ `4,9 %`, sous la cible théorique de `358,45 g` obtenue
par application des `33 %` aux `535 g`. Elle ne valide ni l'offre PAUTER
titane, ni l'équilibrage, ni la résistance du F0.

## Criblages exécutés

Le cas de régression prend l'alésage documentaire de `100 mm`, la course de
`76,4 mm` et `6 720 tr/min`, puis ajoute des hypothèses synthétiques : pression
cylindre `12 MPa`, ensemble piston/axe `600 g`, tiers de masse de bielle en
translation, facteur de concentration `1,5` et cycle de `100 h`.

Les équations donnent, avec la masse CAO, `94,25 kN` de force gaz,
`17,56 kN` d'inertie et une borne de compression de `111,81 kN`. Les deux
membrures idéalisées conduisent à `598,98 MPa` de contrainte locale de
compression et un rapport limite EOS ambiante/contrainte de `1,64`. Le rapport
Euler/charge vaut `5,47`. Les pressions projetées valent `102,80 MPa` en tête
et `248,17 MPa` au pied, le cycle de `100 h` représente `40,32 millions` de
tours et la dilatation libre sur `+100 K` vaut `0,114 mm`.

Ces nombres sont des contrôles mathématiques reproductibles, pas une FEA ni une
prédiction de durée de vie. Ils ignorent notamment contact, précharge des vis,
film d'huile, flexion hors plan, défauts LPBF, état de surface, température et
fatigue multiaxiale.

## Gates suivants

1. Mesurer ou scanner une bielle, son chapeau, ses vis, coussinets, axe et
   interfaces vilebrequin/piston ; relever masse et équilibrage bout à bout.
2. Geler variante M64, enveloppe de pression cylindre, masses mobiles,
   survitesse, cliquetis, température, spectre et durée d'usage.
3. Reconstruire plans de joint, alésages, congés, lubrification, précharge,
   frottement, jeux et tolérances à partir des mesures.
4. Comparer acier, titane conventionnel et Ti64 LPBF par multibody puis FEA 3D
   non linéaire de contact, flambement, modal et fatigue convergés.
5. Optimiser la topologie avec keep-outs, orientations, surépaisseurs et
   contraintes de fabrication, puis qualifier poudre, traitement, HIP, CT,
   rugosité, ressuage et coupons.
6. Réaliser preuve statique et fatigue grandeur réelle avec les vis et paliers
   retenus, puis corréler sur banc et dyno sous revue d'ingénierie moteur.

PhysicsNeMo reste différé jusqu'à disposer d'un ensemble FEA/fatigue corrélé
avec jeux train, holdout et hors-distribution. SimReady attend les interfaces
mesurées de l'assemblage. Ce STEP F0 n'est autorisé ni pour fabrication, ni
pour montage, ni pour mise en route moteur.
