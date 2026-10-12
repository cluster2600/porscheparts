# Programme produit : kit moteur inspiré du 962, objectif 1 000 ch

**Objectif exprimé par le propriétaire : développer puis vendre un kit
permettant de transformer un moteur classique de 911, 964 ou 993 en moteur
moderne inspiré du 962.** Il conserve la cible quatre soupapes, double
allumage, refroidissement à eau, géométrie bionique et fabrication additive.
Les 1 000 ch sont un objectif de développement, sans résultat moteur à ce jour.

Le [registre produit](kit-program.json) conserve cet objectif, les inconnues,
les variantes et les preuves requises. Le nom « kit 962 » est un nom de
travail ; le produit proposé est une conversion moderne, pas un moteur
Porsche 962 d'origine.

## Première version et décisions ouvertes

Le premier livrable industriel proposé est **un moteur démonstrateur sur banc,
construit sur une seule variante identifiée**, puis installé et testé dans
une seule configuration de véhicule. Le kit commercial viendrait après
qualification, avec montage par un motoriste et dossier de traçabilité.

Pour les calculs de cadrage, l'hypothèse provisoire est **1 000 ch métriques
(PS) au vilebrequin**. Le propriétaire doit encore préciser moteur/roues et
priorité piste/route. Aucun calcul ne convertit une puissance moteur en
puissance aux roues par un pourcentage de pertes arbitraire.

Le M64/60 de 993 Turbo est proposé comme premier **candidat de référence**
parce que le [programme moteur existant](../m64-engine-system/program.json)
porte déjà sur cette variante. Sa disponibilité physique et sa capacité à
1 000 ch ne sont pas établies. Cette proposition ne choisit pas le donneur
à la place du propriétaire et ne prouve pas la compatibilité Carrera.

| Base commerciale envisagée | Traitement dans le programme |
|---|---|
| 993 Turbo M64/60 | Candidat initial ; carter, cylindres, goujons, huile et transmission à mesurer/qualifier |
| 993 Carrera M64 | Variante séparée ; conversion atmosphérique–turbo et interfaces à établir |
| 964 Carrera M64 | Variante séparée, comparée au donneur pilote après métrologie |
| 964 Turbo | Distinguer moteur exact et cylindrée ; ne pas assimiler toute 964 à un M64 |
| 911 classiques plus anciennes | Phase ultérieure par type moteur ; pas de kit universel revendiqué |

**Verrou central : peut-on conserver durablement le carter donneur à la
puissance et au cycle d'utilisation retenus ?** S'il faut un autre carter,
il faudra recadrer le kit, son coût et la part réellement conservée du moteur.
La robustesse d'un carter Turbo ne se transmet pas par hypothèse à un Carrera.

## Périmètre du kit à développer

| Sous-ensemble | Route de fabrication proposée | Dépendance de qualification |
|---|---|---|
| Six culasses, 24 soupapes, 12 bougies | Corps LPBF ; sièges, guides, filets et plans repris par usinage ; composants de soupapes dédiés | Métrologie M64, chambres/ports, tenue des sièges, étanchéité et fatigue |
| Porte-arbres et entraînement DOHC | Architecture compatible avec le donneur à définir ; engrenages/chaînes, arbres et contacts usinés | Cinématique, lubrification, jeux, piston–soupape et durée de vie |
| Cylindres et liaison aux culasses | Réemploi ou remplacement selon CHT ; refroidissement complet à eau à comparer à une solution mixte | Plans de feu, registres, précharge, déformation et joints |
| Bas moteur | Carter inspecté puis calculé ; pistons/bielles/vilebrequin conventionnels ou composants spécialisés qualifiés | Pression cylindre, paliers, fatigue, détonation, régimes et couple |
| Eau et huile | Galeries/collecteurs complexes candidats AM ; pompes, radiateurs, joints et raccords qualifiés | Débit, perte de charge, dégazage, ébullition, retour d'huile et charge thermique |
| Suralimentation et air de charge | Turbos achetés et caractérisés ; collecteurs/plénums candidats AM ; échangeurs et wastegates dédiés | Cartes débit/pression, contre-pression, températures et réponse transitoire |
| Alimentation et commande | Injecteurs/pompes/capteurs/ECU qualifiés, calibration double allumage | Carburant et pression, cliquetis, richesse, protections et modes dégradés |
| Installation véhicule | Supports et conduites par variante ; embrayage, boîte et transmission vérifiés | Couple, refroidissement dans la voiture, freinage/pneus et usage visé |
| Livraison commerciale | Nomenclature, manuel, couples/jeux approuvés, numéros de série, contrôle final, entretien et pièces de rechange | Répétabilité de fabrication, montage atelier, coût total et règles d'usage |

L'impression 3D sert les conduits internes et les formes impossibles ou coûteuses
à produire autrement. Elle ne devient pas une exigence pour chaque pièce.
Un carter, une culasse ou une bielle imprimée n'est accepté qu'après comparaison
du procédé avec les alternatives et qualification de sa fonction. Le kit
pourra donc combiner pièces imprimées, forgées, usinées et achetées.

Les pistes CP1/CuCrZr du [dossier matière](README.md#matière--conductivité-et-tenue-à-chaud)
restent ouvertes. Aucun gain, masse, prix ou durée de vie n'est promis.
Les turbos K16 du jumeau M64 existant sont une référence d'origine, pas une
sélection de turbos pour 1 000 ch.

## Ce que signifie la cible de puissance

Calculs quatre temps de cadrage, avec une cylindrée **hypothétique de 3,6 L** :

| Point de calcul | Puissance | Couple associé | PME frein associée |
|---|---:|---:|---:|
| 1 000 PS à 6 000 tr/min | 735,499 kW | 1 170,6 N·m | 40,86 bar |
| 1 000 PS à 7 000 tr/min | 735,499 kW | 1 003,4 N·m | 35,02 bar |

Relations : `P = 2πNT/60` et `PME = 4πT/Vd`. La PME est une pression
moyenne équivalente au frein, **pas la pression maximale de combustion**.
Ces points ne choisissent ni régime, cylindrée, boost, rendement ni carburant.
Ils ne calculent pas le flux thermique vers une culasse et ne valident pas
le carter ou la boîte. Les valeurs complètes sont dans
[kit-program.json](kit-program.json), vérifiées par un test dimensionnel.

Le moteur doit être défini par une courbe couple/puissance, un carburant,
des conditions d'entrée et un cycle de service. Une pointe au banc ne démontre
pas une puissance continue ni une durée de vie commerciale. Standard de
correction, instrumentation, répétitions, durée d'endurance et intervalle
de maintenance doivent être fixés **avant** l'essai de qualification.

## Précédents consultés et signal commercial

[Swindon Powertrain](https://swindonpowertrain.com/products/24-valve-porsche-911-m64-cylinder-head-kit/)
propose un kit 24 soupapes pour M64 964/993 conservant, selon le fabricant,
des interfaces de distribution et lubrification d'origine. Sa
[fiche](https://swindonpowertrain.com/wp-content/uploads/2025/10/M64-24V-Cylinder-Head-Kit-Product-Sheet-0923.pdf)
énumère un kit complet de culasses et distribution, avec cylindres refroidis
par air. Cela constitue un précédent de conversion, sans prouver notre
architecture à eau, le double allumage ou 1 000 ch.

Le [webshop consulté le 12 octobre 2026](https://webshop.swindonpowertrain.com/index.php?product_id=361&route=product%2Fproduct)
affiche £31 447,50 hors taxes pour le kit de base, sur commande. C'est un
prix concurrent affiché, pas notre devis, notre coût de revient ni une preuve
de ventes. Le produit complet et ses accessoires ont un périmètre distinct.

Le [guide MAHLE Motorsport 2024](https://www.us.mahle.com/media/usa/motorsports/2024-mahle-motorsport-porsche-application-guide-2.pdf),
page imprimée 5, distingue notamment des applications 993 Turbo de celles
964 Turbo/993 Carrera convertie et des montages avec/sans reprise des registres.
C'est un motif concret pour qualifier les variantes séparément ; ses cotes
de kit ne remplacent pas la mesure du carter donneur et ne constituent pas
des limites de puissance.

**Hypothèse client à tester :** propriétaires de 964/993 et ateliers de
préparation souhaitant une conversion documentée, avec puissance, maintenance
et coût d'installation maîtrisés. L'existence d'une offre concurrente ne
démontre pas leur volonté de payer pour notre produit.

La première recherche commerciale proposée porte sur cinq entretiens avec
propriétaires et cinq avec motoristes/installateurs : besoin réel, usage,
carburant disponible, prix total posé acceptable, entretien et conditions
d'achat. Aucun entretien ni engagement d'achat n'est effectué ou revendiqué
ici. Pas de chiffre d'affaires projeté à partir d'un nombre de clients supposé.

Le prix de vente ne sera proposé qu'après nomenclature chiffrée, devis de
fabrication/usinage/contrôle, rendement matière et rebuts, assemblage,
calibration, installation, garantie/SAV et petites séries. Les fournisseurs,
prix, volumes et marge restent inconnus.

## Parcours de qualification et critères de réussite

1. **G0 — cible produit.** Fixer puissance moteur/roues, usage, carburant,
   cycle de service et donneur précis. Définir contenu livré, installation et
   coût total visé avec les premiers utilisateurs.
2. **G1 — interfaces et bas moteur.** Métrologie/CT du donneur ; carte de
   compatibilité ; revue du carter, des goujons et du chemin d'effort. Évaluer
   conservation/remplacement des cylindres et de l'entraînement de distribution.
3. **G2 — une culasse et coupons.** Reconstruction M64, quatre soupapes et
   deux bougies implantées sur des interfaces mesurées ; CHT et contraintes,
   coupons LPBF, CT, nettoyage, matériau et épreuve hydraulique approuvée.
4. **G3 — moteur six cylindres instrumenté.** Montage complet, calibration
   et montées en charge par paliers approuvés par le motoriste ; surveiller
   pression cylindre, températures, huile/eau, cliquetis et déformations.
   Une mesure reproductible à la cible ne clôt pas le programme d'endurance.
5. **G4 — véhicule et endurance.** Valider installation, gestion thermique,
   transmission, freinage et cycle client ; fixer limites d'utilisation,
   entretien et exigences réglementaires propres au pays et à l'usage.
6. **G5 — petite série vendable.** Revue professionnelle et plan approuvé,
   procédé répétable, essais réussis, compatibilités publiées, montage atelier,
   traçabilité, coût, garantie et support. Vente et allégations techniques
   suivent les preuves, pas le rendu du jumeau.

Les gates G1–G5 restent ouvertes. Le
[contrat culasse F0](interface-contract.json) et ses empreintes sont conservés.
Le [programme M64 existant](../m64-engine-system/program.json) apporte des
références par zone sans transmettre ses niveaux de fidélité ou interfaces à
ce kit. PicoGK/CHT/calcul mécanique/assemblage sont reliés selon
l'[architecture existante](../../docs/architecture/README.md) ; aucun nouveau
simulateur, scheduler, achat, contact fournisseur ou précommande n'est lancé.
