# Dimensionnement : Mezger 4 L biturbo, 1 000 ch moteur, SP95

La cible demandée est désormais un six-cylindres Mezger **4 L, biturbo,
quatre soupapes et deux points d'allumage par cylindre, au SP95**, pour banc
et piste. Les calculs ci-dessous déterminent des besoins conditionnels ; ils
ne démontrent pas que 1 000 ch sont atteignables au SP95 sur le donneur.

Le [calculateur](source/mezger_sp95_budget.py) et son
[rapport complet](derived/mezger-sp95-budget.json) conservent les hypothèses,
les unités, les sensibilités, les empreintes des sources Python et du contrôle géométrique et les
inconnues. Aucun résultat ne constitue une consigne de réglage moteur.

## Hypothèses et équations

| Entrée | Valeur du scénario central | Statut |
|---|---:|---|
| Puissance au vilebrequin | 1 000 ch = 735,499 kW | Demande utilisateur, ch métriques |
| Alésage × course | 102 × 81,6 mm | Hypothèse de l'étude 4 L, pas une mesure du donneur |
| Cylindrée calculée | 4 000,660 cm³ | Six cylindres, quatre temps |
| Régime à puissance cible | 7 000 tr/min | Hypothèse, balayage 6 500–8 000 |
| Rendement effectif sur PCI | 30 % | Hypothèse, balayage 26–34 % |
| Lambda | 0,82 | Hypothèse, balayage 0,78–0,86 |
| PCI / AFR stœchiométrique / masse volumique carburant | 42,5 MJ/kg / 14,4 / 745 kg/m³ | Substitut de calcul, lot SP95 non caractérisé |
| Remplissage volumétrique | 100 % à la densité du collecteur | Hypothèse, balayage 90–110 % |
| Air au collecteur | 50 °C | Hypothèse, balayage 40–60 °C |
| Atmosphère / pertes filtre / pertes circuit de charge | 1,01325 bar / 0,02 bar / 0,10 bar | Hypothèses constantes |
| Rendement isentropique compresseur / température d'entrée | 72 % / 25 °C | Hypothèses, carte non sélectionnée |
| Chaleur vers l'eau des seules culasses | 12 % de la puissance chimique | Hypothèse, balayage 8–16 % |
| Eau : cp / masse volumique / échauffement | 4 180 J/(kg·K) / 965 kg/m³ / 15 K | Eau seule, propriétés constantes ; mélange non choisi |

Le SP95 fixe ici **RON 95**. La teneur en éthanol reste inconnue : les labels
E5/E10 sont distincts de l'indice d'octane, et le SP95 peut notamment être E10
selon le marché. Les trois triplets de propriétés carburant du JSON sont des
sensibilités illustratives, sans certificat de lot ni correspondance exacte
E5/E10. Voir l'explication primaire du
[Department for Transport](https://www.gov.uk/guidance/e10-petrol-explained).

Avec P en W, Vd en m³ et n en tr/min :

```text
Vd = 6 × π/4 × alésage² × course
Couple = P / (2πn/60)
PME = 4π × couple / Vd                         [Pa, moteur quatre temps]
Vitesse moyenne du piston = 2 × course × n/60  [m/s]
Puissance chimique = P / rendement effectif
Débit carburant = puissance chimique / PCI     [kg/s]
Débit air = débit carburant × AFR_stœch × lambda
p_collecteur = débit air × R_air × T_collecteur / (VE × Vd × n/120)
PR_compresseur = (p_collecteur + perte aval) / (p_atmosphère − perte filtre)
T_sortie = T_entrée × [1 + (PR^((γ−1)/γ) − 1)/η_compresseur]
Q_échangeurs_air = débit air × cp_air × (T_sortie − T_collecteur)
Q_eau_culasses = fraction vers culasses × puissance chimique
Débit eau = Q_eau_culasses / (cp_eau × ΔT_eau)  [kg/s]
Diamètre équivalent = √(4 × débit volumique / (π × vitesse choisie))
```

Le rendement est un rendement **au frein**, qui intègre déjà les pertes du
moteur dans son bilan global. Les consommations de nouveaux auxiliaires
doivent être définies pour conserver une cible nette cohérente. Les balayages
font varier une entrée à la fois : richesse, rendement, remplissage et
cliquetis sont couplés dans le moteur réel. Enrichir ne garantit donc pas la
même puissance avec moins d'air comme le laisserait croire une lecture
isolée de l'équation à rendement maintenu constant.

## Couple et contraintes mécaniques

Chaque ligne impose **1 000 ch à ce régime** : ce n'est pas une courbe de
couple prédite ni un choix de régime maximal.

| Régime, tr/min | Couple, N·m | PME, bar | Vitesse moyenne piston, m/s | Surpression de remplissage, bar |
|---:|---:|---:|---:|---:|
| 6 500 | 1 080,5 | 33,94 | 17,68 | 1,90 |
| 7 000 | 1 003,4 | 31,52 | 19,04 | 1,69 |
| 7 500 | 936,5 | 29,42 | 20,40 | 1,51 |
| 8 000 | 877,9 | 27,58 | 21,76 | 1,36 |

La PME n'est **pas** la pression maximale de combustion. Pour préparer de
futurs cas de charge, des pics purement hypothétiques de 140, 180 et 220 bar
correspondent, sur un alésage de 102 mm, à **114,4 / 147,1 / 179,8 kN** de
force de gaz. Ce ne sont ni des pressions prédites ni des charges admissibles.
Le serrage, les portées, les efforts d'inertie, la fatigue et la tenue du bloc
et de la distribution restent à établir sur la variante exacte.

Le volume mort total requis par cylindre vaut Vc = (Vd/6)/(RC−1) :

| Rapport volumétrique exploré | Volume mort total, cm³ |
|---:|---:|
| 8,0:1 | 95,25 |
| 8,5:1 | 88,90 |
| 9,0:1 | 83,35 |
| 9,5:1 | 78,44 |

Ce volume comprend chambre, joint, jeu au plan de joint et effet du piston.
Il ne faut pas copier cette valeur dans la seule cavité de la culasse.
Aucun de ces rapports volumétriques n'est sélectionné ou validé sur SP95.

## Air, turbos et carburant

Au scénario central : **207,7 kg/h**, soit **278,8 L/h de carburant**,
et **0,681 kg/s d'air** au total. Chaque turbo doit donc fournir environ
**0,341 kg/s, soit 45,1 lb/min de débit réel**, à un rapport de pression
compresseur de **2,83**. Ce débit n'est pas corrigé aux conditions de
référence d'une carte fournisseur. Les deux turbos partagent ici le débit
également ; cette répartition reste à vérifier.

Le collecteur est à **2,707 bar absolus**, soit **1,694 bar relatifs**.
Le modèle d'air à γ=1,4 et cp=1 005 J/(kg·K) donne **168 °C** à la sortie
des compresseurs et **80,9 kW** à évacuer dans les échangeurs d'air pour
obtenir 50 °C au collecteur. Ce sont des besoins stationnaires, pas des
dimensions d'échangeur. La sélection nécessite cartes de rendement,
pompage, étranglement, vitesse et contre-pression turbine sur toute la
plage moteur. Les pressions doivent être absolues pour calculer PR ; voir
[Garrett, lecture des cartes et calcul du rapport de pression](https://www.garrettmotion.com/wp-content/uploads/2018/05/Garrett-Performance-Products-Catalog.pdf).

| Rendement supposé | Consommation spécifique, g/kWh | Carburant, L/h | Air, kg/s | Surpression calculée, bar |
|---:|---:|---:|---:|---:|
| 26 % | 325,8 | 321,6 | 0,786 | 2,11 |
| 30 % | 282,4 | 278,8 | 0,681 | 1,69 |
| 34 % | 249,1 | 246,0 | 0,601 | 1,38 |

Avec **six injecteurs indirects**, un rapport cyclique supposé de 80 %
et un différentiel injecteur de 3 bar, le besoin central est **968 cm³/min
par injecteur**, pour le carburant supposé. Une réserve de débit de 25 %
donne **348 L/h de pompe à environ 4,69 bar au-dessus du réservoir** si le
régulateur maintient 3 bar au-dessus du collecteur. Les pertes de ligne
s'ajoutent ; une annonce de débit à pression nulle ne suffit pas. La donnée
injecteur doit être ramenée au même fluide et différentiel, avec temps morts
et fenêtre d'injection. Ce calcul ne choisit ni injecteurs ni pompe.

**Point SP95 : aucune pression « sûre » ne se déduit du RON seul.** La
température de charge, la chambre, le diamètre, la position des bougies,
le rapport volumétrique et l'allumage modifient la limite de cliquetis,
comme l'explique [Garrett](https://www.garrettmotion.com/knowledge-center-category/oem/advanced/).
Le double allumage demandé reste une proposition à caractériser en combustion :
aucun gain de puissance, d'avance ou de résistance au cliquetis n'est crédité.
Le moteur doit pouvoir réduire sa charge si la limite mesurée l'impose ; les
1 000 ch restent une cible à vérifier au banc sur le carburant réel.

## Eau : conséquence directe pour la culasse PicoGK

Au point central, les culasses évacuent **294,2 kW**, soit **49,0 kW par
culasse**. À ΔT=15 K, cela représente **291,7 L/min** pour les six,
**145,9 L/min par banc** et **48,6 L/min par culasse**, avec six branches
en parallèle équilibrées. Les cylindres, l'huile et les turbos ne sont pas
inclus dans cette charge d'eau. Leur part reste dans les 1 422 kW non affectés
du bilan ; elle ne peut pas être ajoutée arbitrairement au radiateur culasse.

| Part de l'énergie carburant vers les culasses | Chaleur totale, kW | Eau à ΔT=15 K, L/min | Par culasse, L/min | Ø intérieur équivalent à 3 m/s, mm |
|---:|---:|---:|---:|---:|
| 8 % | 196,1 | 194,5 | 32,4 | 15,14 |
| 12 % | 294,2 | 291,7 | 48,6 | 18,55 |
| 16 % | 392,3 | 389,0 | 64,8 | 21,41 |

La plage combinée des seuls balayages thermiques, à rendement 30 %, donne
**24,3 à 97,2 L/min par culasse** et **13,1 à 26,2 mm** de diamètre
équivalent pour 3 m/s (fractions 8–16 %, ΔT=10–20 K). Ce n'est pas un
intervalle statistique ni une enveloppe garantie. Le mélange antigel et
les propriétés à température modifieront ces valeurs. Les formulations de
référence de l'[IAPWS](https://iapws.org/technical-guidance/release/LiquidWater)
permettent de remplacer ensuite les constantes d'eau ; elles n'ont pas été
évaluées dans ce calcul simplifié.

Les ports de l'étude bionique existante ont une section d'environ
**75,842 mm²**, d'après le
[contrôle géométrique](derived/architecture-report.json).
Leur vitesse moyenne serait **10,69 m/s** au point central. La pression
dynamique correspondante est **0,551 bar** ; elle n'est pas la perte de
charge du circuit. Les changements de section, coudes, canaux et rugosités
nécessitent le calcul hydraulique/CFD pour choisir la pompe.

Pour la prochaine variante de géométrie, réserver à ce point de calcul une
section d'entrée **et** de sortie équivalente à **18,55 mm de diamètre
intérieur**, et environ **32,12 mm** pour chaque collecteur de banc,
si 3 m/s est conservé comme cible exploratoire. Les raccords, les branches
internes et leur répartition doivent suivre ce débit ; ce diamètre seul
ne dimensionne pas le réseau. Aucune modification des STL/VDB déjà attestés
n'est effectuée par ce calcul.

La pièce étudiée reste quatre soupapes/double allumage. Les deux puits
de 7 mm existants sont des réservations, pas des filetages de bougie ni des
interfaces qualifiées. Les photographies de
[Performance Developments](https://performancedevelopments.com/porsche-962c-race-engine-part-3/)
montrent une construction modifiée par ce motoriste avec chemises séparées ;
elles ne donnent pas les interfaces d'un Mezger donneur ni ses galeries d'eau.
Les cotes d'axes, les portées, la distribution, les inserts et les volumes
nécessaires au double allumage restent à mesurer/définir.

## Matériau et Peltier

La conduction seule donne ΔT = flux surfacique × épaisseur / conductivité.
À **3 MW/m²** et **4,5 mm**, des conductivités hypothétiques de
100 / 160 / 220 / 320 W/(m·K) donnent **135 / 84,4 / 61,4 / 42,2 K**
de gradient à travers le métal. Cela n'inclut ni la convection ni les
résistances d'interface ; le flux réel n'est pas mesuré.

Une conductivité élevée ne suffit donc pas à sélectionner la culasse.
Le fournisseur distingue lui-même
[Aheadd CP1, orienté conductivité, et HT1, orienté température et résistance](https://www.constellium.com/products/aluminium-powders/).
Les valeurs du balayage ne sont attribuées à aucun de ces alliages.
Conductivité en fonction de T, fatigue thermique, fluage, dilatation,
rétention des sièges/guides et procédé LPBF doivent être documentés avant
de choisir aluminium ou cuivre allié. Aucun matériau n'est qualifié ici.

Le bilan Peltier réutilise le calculateur existant, sans rendement inventé
de module. Pour absorber les **294,2 kW** des culasses avec COP=1, il faudrait
**294,2 kW électriques aux modules**, **326,9 kW au bus** avec conversion
90 %, et **621,1 kW rejetés à l'ambiance** en incluant le convertisseur.
À 48 V cela représente **6 810 A**, avant pompes et ventilateurs. Même à
COP=2, le bus demanderait 163,4 kW. Le refroidissement primaire retenu pour
la suite du dimensionnement est donc une boucle eau/radiateurs ; un éventuel
Peltier reste limité à une étude auxiliaire séparée. Une alimentation par
le moteur augmenterait ses besoins et impose de refaire le bilan net.

## Chaîne d'outils et vérification

Cette étape fournit les conditions de dimensionnement à transmettre à la
chaîne [documentée dans le dépôt](../../docs/TOOLCHAIN.md). Elle ne transforme
pas un bilan 0D en simulation de culasse.

| Étape | Résultat ou dépendance |
|---|---|
| Sources et métrologie | Sources citées ; donneur précis, interfaces et lot carburant inconnus |
| Calcul Python | Bilan puissance, air, carburant, eau, sections et sensibilités réellement exécuté |
| Qwen local | Exécution réelle r3 ; réponse invalide rejetée, aucune équation intégrée |
| PicoGK / ShapeKernel / LatticeLibrary / VDB | Géométrie existante conservée ; nouvelles exigences de débit ci-dessus |
| Gmsh / OpenFOAM / CalculiX | Pas exécutés dans cette étape ; interface métal/eau conforme et charges à établir |
| USD / rendu | Pas de nouvelle géométrie ni de nouveau rendu produit par ce calcul |
| LPBF / corrélation / banc | Procédé, coupons, métrologie, mesures de combustion et revue professionnelle requis |

Reproduire depuis la racine du dépôt, avec Python 3.12 comme en CI :

```sh
python3 twins/962-cylinder-head-f0/source/mezger_sp95_budget.py
python3 -m unittest discover -s tests -p 'test_962_mezger_sp95_budget.py' -v
```

La réponse et le reçu Qwen sont conservés dans
[l'archive de cette exécution](derived/qwen-assistance/mezger-sp95-r3/review.json).
La réponse enfreint la demande sans code, utilise `lambda` comme variable
Python et dégrade le facteur tr/min → rad/s de 60 à 6. Elle est tronquée
à 768 tokens et n'a pas été exécutée. La relecture est donc rejetée ; elle
ne constitue aucune validation supplémentaire.

Les six tests vérifient indépendamment le bilan énergie, la relation
puissance/PME, la continuité air/eau/sections, les sensibilités, le rejet des
entrées invalides, les empreintes de l'exécution Qwen et la cohérence du rapport enregistré. Tous les drapeaux
de qualification restent faux ; le boost admissible au SP95 reste `null`.
