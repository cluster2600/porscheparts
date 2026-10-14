# Train mobile 917 : expérience sous hypothèses

Suite demandée le 10 octobre 2026 : « Continue avec des hypothèses ».
[Les paramètres](assumptions.json) définissent un moteur partiel supposé,
sans identification du spécimen ni calage métrologique sur le scan.
Le [C# PicoGK](Program.cs) construit quatre familles ; le
[pilote Python](run.py) exporte douze instances de chacune, soit **48 instances**,
et contrôle la géométrie et une cinématique à manetons partagés.
Le piston est creux, avec calotte, jupe et deux bossages d'axe. Ce n'est pas
un moteur complet ni un assemblage accepté pour fonctionner.

## Hypothèses de départ

| Paramètre | Valeur supposée | Origine et limite |
|---|---:|---|
| Alésage × course | 85 × 66 mm | amorce documentaire secondaire de la variante 4,5 L, spécimen non identifié |
| Entraxe de bielle | 132 mm | ancienne hypothèse schématique, aucune cote Porsche mesurée |
| Pas longitudinal / central / décalage des bancs | 118 / 173 / 37 mm | estimations extérieures arrondies du scan, sous hypothèse 1 mm par unité ; banc négatif décalé vers X positif |
| Pied de cylindre / longueur | 70 / 122 mm | choix d'étude depuis un axe de vilebrequin arbitraire |
| Diamètre extérieur / ailettes | 95 / 110 mm | choix d'étude, huit ailettes de 3 mm au pas de 14 mm |
| Jeu diamétral piston | 0,2 mm | choix d'étude, non résolu par les grilles de 1 et 0,5 mm |
| Hauteur piston / jupe / calotte | 44 / 3 / 4,5 mm | choix après rejet du piston plein ; tenue thermique et mécanique inconnue |
| Début intérieur / diamètre des bossages | ±20 / 32 mm | choix de dégagement du pied de bielle, engagement et jeux à qualifier |
| Phases des six paires | 0°, 120°, 240°, 60°, 180°, 300° | hypothèse d'assemblage, pas une preuve d'ordre d'allumage |

Le repère n'est pas enregistré sur le scan. Les axes sont nivelés par hypothèse.
Les autres dimensions, masses volumiques, pressions et régimes sont des choix
explicites dans le JSON. Aucun paramètre supposé ne devient une mesure.

## Résultats exécutés sur le Mac

Le [relevé textuel](execution-20261010.json) contient les empreintes des sources,
exports privés, audits et scénarios. L'exécution finale `run-005` utilise PicoGK
2.3.0, .NET 9.0.317 et les deux grilles à géométrie cible constante.

| Famille | Triangles dérivés, grille 1 mm | Triangles dérivés, grille 0,5 mm | Variation de volume / volume fin | Écart au volume analytique, grille fine |
|---|---:|---:|---:|---:|
| Cylindre à ailettes | 257 696 | 1 042 544 | 0,691 % | 0,224 % |
| Piston creux avec bossages et trou d'axe | 88 612 | 357 896 | 0,482 % | non évalué |
| Bielle à deux yeux | 36 420 | 147 536 | 0,887 % | non évalué |
| Axe creux | 19 008 | 75 816 | 0,754 % | 0,253 % |

Ces deux niveaux montrent une évolution de volume ; ils ne démontrent pas
une convergence asymptotique ni une précision locale des interfaces.
Les quatre familles dérivées sont fermées, orientées, à volume positif et à
une composante, avec des sondes indépendantes dans les trous et la matière.

Les STL natifs contiennent des triangles d'aire nulle : 120/240/16 pour
piston/bielle/axe à 1 mm, puis 1 440/316/524/56 pour les quatre familles à
0,5 mm. Ils restent conservés et rejetés tels quels. Le témoin numérique
[existant](../../../twins/m64-cylinder-head/source/picogk-local-junction/exact_zero_countertrial.py)
est réutilisé pour un dérivé qui retire seulement les faces dont le produit
vectoriel float64 est exactement nul. Aucun seuil de proximité, déplacement
de sommet ou changement d'orientation n'est appliqué. Une empreinte des faces
orientées et un audit indépendant vérifient le dérivé. Cela ne prouve pas une
équivalence symbolique de surfaces continues.
L'essai initial `run-001`, arrêté sur le piston brut, et `run-002`, antérieur
au contrôle d'interférence, restent conservés hors Git. `run-003` conserve le
piston plein rejeté pour interférence. `run-004`, premier piston creux, reste
rejeté après retrait des faces nulles : 670 arêtes à incidence supérieure à
deux, 615 composantes. Aucun remplissage de trou ni déplacement de sommet
n'a forcé son acceptation. La hauteur et la calotte sont ensuite révisées
pour écarter les tangences nominales ; `run-005` passe les écrans de maillage.

La cinématique parcourt 360° par pas de 1°. Les deux bancs utilisent la même
position transversale du maneton ; leurs axes piston suivent les deux racines
opposées de la fermeture de bielle. La course est 66 mm et l'erreur de fermeture
maximale est 5,69 × 10⁻¹⁴ mm. La dérivée seconde analytique est aussi contrôlée
par différences finies dans les tests.

**Rejets utiles :** les entraxes 120 et 144 mm ne gardent pas la jupe entière
dans ce cylindre supposé : marges axiales de −5 et −7 mm. L'entraxe 132 mm
donne +5 mm sur ce seul critère. Les seize sondes du pied de bielle
(huit angles, deux bancs), dans la matière du piston plein de `run-003`,
sont hors matière du piston creux final. Le défaut observé est corrigé sur
ces sondes ; ce contrôle échantillonné ne couvre pas toutes les collisions
possibles, ni les jeux minimaux. Un contrôle complet du volume balayé reste
nécessaire. Les jeux d'axe, coussinet et retenue ne sont pas définis.

## Matériaux candidats et première enveloppe de charge

| Famille | Candidat d'étude | Masse volumique supposée | Masse par prototype, grille fine |
|---|---|---:|---:|
| Cylindre | AlSi10Mg | 2 700 kg/m³ | 0,621 kg |
| Piston creux | aluminium forgé | 2 700 kg/m³ | 0,186 kg |
| Bielle | Ti6Al4V, alternative acier | 4 430 / 7 800 kg/m³ | 0,193 kg pour Ti6Al4V |
| Axe | acier | 7 800 kg/m³ | 0,084 kg |

La population partielle avec bielles titane pèse 13,00 kg sous ces hypothèses.
Ce n'est pas la masse du moteur ; le piston reste sans segments ni retenues.
La route forgée du piston est une piste conventionnelle, pas une matière LPBF.
Les pistes LPBF aluminium sont documentées par
[EOS](https://www.eos.info/metal-solutions/metal-materials/aluminium).
Aucune limite admissible de ce fournisseur n'est transférée à ces pièces.

Les dix-huit scénarios croisent deux matières de bielle, 4 000/6 000/8 000 tr/min
et 40/60/80 bar de pression maximale supposée. La masse alternative attribue
un tiers de la masse de bielle au mouvement réciproque. La somme du pic de gaz
et du pic absolu d'inertie constitue une enveloppe ; ces pics ne sont pas
supposés se produire ensemble dans un cycle de combustion établi.
À 8 000 tr/min et 80 bar : 45,40 kN de gaz, 9,67 kN d'inertie avec la bielle
titane, somme 55,07 kN. La division par la section nominale Ø18 donne
216,4 MPa. L'alternative acier donne 56,49 kN et 222,0 MPa. La vitesse moyenne
du piston est 17,6 m/s. **Ces valeurs ne démontrent aucune tenue matière.**

Il manque le chargement angulaire de combustion, température, flexion,
flambement, contacts, coussinets, vis de chapeau, concentrations de contraintes,
fatigue et défauts du procédé. Pour retenir une route additive, il faudra
nuance/lot, machine et paramètres, orientation, supports, traitement thermique,
usinage, état de surface, contrôles et éprouvettes représentatives à chaud.
Le titane exige aussi un dossier de fatigue et d'isolation galvanique.

## Reproduire et poursuivre

```bash
PYTHON=/chemin/vers/python-avec-numpy-scipy-trimesh-rtree-networkx
DOTNET=/chemin/vers/dotnet-9
"$PYTHON" models/917-engine-reconstruction/hypothesis/run.py \
  --output work/917-hypotheses/nouvelle-execution --dotnet "$DOTNET"
"$PYTHON" tests/test_917_picogk_hypotheses.py -v
```

Les STL/VDB, l'assemblage, les transformations, `kinematics.csv`, rapports et
visualisations restent privés dans `work/`. Les sources C# et JSON sont
modifiables et suivies dans Git. Le dossier public contient des résultats
textuels, sans scan ni géométrie dérivée. Aucune fiche de pièce du catalogue
ne reçoit un statut de validation ou de fabrication.

Les douze tests ciblés des deux étapes passent ; le C# compile sans
avertissement ni erreur. `make check` a exécuté 3 626 tests, 153 ignorés,
et s'arrête sur deux comparaisons exactes de flottants dans les dossiers
993 impeller/stator inchangés. Les autres cibles globales ne sont donc pas
atteintes localement. Les contrôles ciblés sont relancés après la révision
du piston ; la CI du dernier commit reste à observer séparément.

La suite consiste à affiner le piston et les interfaces axe/bielle, définir
les chapeaux et coussinets, puis reconstruire vilebrequin, paliers et carter
autour des [interfaces à mesurer](../README.md#interfaces-et-chemins-deffort-à-établir-avant-toute-pièce-fonctionnelle).
Les culasses, distribution, segments, lubrification, refroidissement,
équilibrage et essais physiques restent à réaliser. Les hypothèses permettent
d'avancer le calcul, sans remplacer ces mesures ni la revue professionnelle.
