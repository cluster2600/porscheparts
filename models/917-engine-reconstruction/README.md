# Reconstruction du moteur 917 avec PicoGK

Reprise demandée le 10 octobre 2026 : objectif final **moteur fonctionnel**.
Cette nouvelle étape utilise le scan du carter avec cylindres. Les anciens
[travaux archivés](../../ARCHIVE.md) restent des références de méthode ; leurs
géométries hypothétiques et leurs résultats ne qualifient pas ce moteur.
La variante exacte, la cylindrée et le régime cible restent à déterminer.

L'[assemblage moderne quatre soupapes et biturbo](assembly/README.md) reprend
nos culasses air + huile et nos turbos bioniques : 119 définitions géométriques
et 1 129 occurrences de conception. Les formes manquantes sont paramétriques,
avec nervures et collecteurs ramifiés. Les interfaces et la qualification
fonctionnelle restent ouvertes ; aucune fabrication n'est autorisée.

La [réconciliation FIA du 11 octobre](fia/README.md) exploite les cotes déjà
présentes dans Git, relues sur la fiche originale n° 250. Elle corrige la
distance axe de piston–calotte à 43 mm et applique le diamètre de référence
de maneton 52 mm. Cette correction rejette l'implantation axiale provisoire
du cylindre ; les masses FIA sont aussi utilisées pour une comparaison de
charges. Le spécimen scanné reste à rattacher à la variante documentaire.

La [suite sous hypothèses](hypothesis/README.md), autorisée le même jour,
ajoute quatre familles PicoGK et 48 instances, une cinématique contrôlée et
18 scénarios de charges avec matières candidates. Le contrôle détecte une
interférence du piston plein avec le pied de bielle, puis vérifie le dégagement
des mêmes sondes après construction d'un piston creux à bossages. Les contrôles
restent partiels ; les hypothèses et les versions rejetées sont traçables.

## Première étape exécutable

[reconstruct.py](source/reconstruct.py) vérifie le SHA-256 canonique du scan,
transporte ses triangles sans changement d'échelle et appelle
[le programme C#](source/Program.cs), avec PicoGK 2.3.0 et .NET 9.
PicoGK construit une **coque numérique des surfaces observées**, exportée en
STL et VDB. L'épaisseur de cette coque sert à représenter la surface scannée :
elle ne définit pas l'épaisseur d'un carter réel. Aucun trou n'est interprété
comme un passage d'huile et aucun volume intérieur moteur n'est inventé.

Les deux résolutions par défaut sont 3 et 2 **unités du scan**. Le transport
STL utilise la convention numérique MM de PicoGK sans établir l'unité physique.
L'épaisseur de coque change avec la résolution : la comparaison ne constitue
pas une étude de convergence à géométrie constante.

Un audit indépendant avec trimesh vérifie les nombres finis, l'étanchéité,
l'orientation, le volume positif et le nombre de composantes. Il mesure les
distances source→coque et coque→source sur 2 000 points dans chaque sens,
avec graine 917. Le maximum échantillonné n'est pas une borne de Hausdorff.
Il ne dispose pas encore d'une tolérance d'acceptation métrologique.

Le brut et tous ses dérivés restent hors Git dans `work/`. Chaque exécution
exige un nouveau dossier ; en cas d'échec, les artefacts sont conservés et le
statut ne permet aucune fabrication. Seuls le code et des résultats textuels
sans géométrie pourront accompagner une revue GitHub.

```bash
PYTHON=/chemin/vers/python-avec-numpy-scipy-trimesh-rtree
DOTNET=/chemin/vers/dotnet-9

"$PYTHON" models/917-engine-reconstruction/source/reconstruct.py \
  --source /chemin/vers/917-engine-case-with-cylinders.obj \
  --output work/917-picogk/nouvelle-execution \
  --dotnet "$DOTNET"

"$PYTHON" tests/test_917_picogk_reconstruction.py -v
```

Les fichiers `report.json`, `status.json`, `build.log`, les reçus PicoGK et les
audits par résolution permettent de vérifier l'exécution. Les VDB sont les
champs géométriques ; le C# constitue la source modifiable. Cette étape ne
produit pas de STEP de définition mécanique.

## Exécution locale du 10 octobre 2026

Le [relevé textuel](execution-20261010.json) lie le scan canonique, les sources,
l'exécutable et les exports par SHA-256. PicoGK a été exécuté sur le Mac ARM64
avec .NET 9.0.317. Les deux grilles retenues passent l'audit géométrique :

| Grille, unités du scan | Triangles STL | Composantes de surface fermées | Distance p95 source→coque | Distance p95 coque→source |
|---|---:|---:|---:|---:|
| 3 | 1 162 808 | 167 | 3,426 | 3,472 |
| 2 | 2 605 872 | 118 | 2,157 | 2,270 |

Les distances incluent l'épaisseur volontaire de la coque numérique et ne
sont pas une précision de reconstruction de pièce. Le nombre de composantes
n'est pas une nomenclature mécanique. L'essai à 1,5 unité est conservé et
rejeté : STL non étanche et quatre triangles de surface nulle. Aucune réparation
automatique n'a servi à le faire accepter. Toutes les portes de qualification
physique, de fabrication et de démarrage restent fermées.

Les cinq tests ciblés passent, la compilation C# termine sans avertissement ni
erreur et les liens Markdown sont valides. `make check` a exécuté 3 619 tests
(153 ignorés) puis s'est arrêté : deux comparaisons exactes de nombres flottants
dans les anciens dossiers impeller/stator 993 et une dépendance `networkx`
absente dans l'environnement QA. Après installation locale de cette dépendance,
les deux tests concernés passent ; les deux échecs de comparaison flottante
se reproduisent sur des fichiers inchangés de `origin/main`. Ils ne sont pas
corrigés dans cette reprise du 917. Le contrôle global n'est donc pas vert.

## Interfaces et chemins d'effort à établir avant toute pièce fonctionnelle

| Ensemble | Mesures et interfaces requises | Chemin d'effort ou fonction à démontrer |
|---|---|---|
| Demi-carters | plans de joint, vis et goujons, datums, logements et alignement des paliers, registres des cylindres, circuits d'huile, sortie et supports moteur | efforts des paliers et cylindres vers les carters, boulonnerie, transmission et supports |
| Cylindres et culasses | alésage, registre de pied, portée de culasse, goujons et précharge, sièges/guides, chambre et conduits, épaisseurs et ailettes | pression gaz et dilatation vers culasse, goujons et carter ; évacuation thermique |
| Vilebrequin et train mobile | tourillons/manetons et rayons, axes, jeux, huile, prise centrale, entraxes des bielles, axes/pistons/segments, masses et équilibrage | pression → piston → axe → bielle → maneton → vilebrequin et paliers |
| Distribution et accessoires | profils de came, supports et paliers, entraînement et calage, ressorts, jeux et contacts, fixations de pompe et ventilateur | commande des soupapes et charges transitoires ; débit d'huile et d'air |

Ces interfaces ne sont pas validées par les cercles projetés du scan. Il faut
identifier le spécimen, fixer les repères, relever au moins trois dimensions
indépendantes et documenter l'incertitude. Les intérieurs demandent des mesures
sur moteur démonté, des plans autorisés et/ou une tomographie adaptée.
Les données absentes restent inconnues ; le modèle ne fournit pas sa propre
preuve d'inspection.

## Matériaux et fabrication : candidats, pas choix qualifiés

| Famille | Route à étudier | Qualification nécessaire |
|---|---|---|
| Carter et culasses | aluminium ; comparer fabrication conventionnelle et LPBF, dont AlSi10Mg, AlF357 et Aheadd CP1 selon les températures et la machine | propriétés à chaud, conductivité, dilatation, fatigue thermique, porosité, état usiné et étanchéité |
| Cylindres | corps et surface de frottement à définir ensemble | usure, tribologie, traitement ou chemise, distorsion de l'alésage et transfert thermique |
| Vilebrequin, bielles, pistons et axes | routes conventionnelles prioritaires à comparer aux alternatives qualifiées | fatigue, défauts, traitements, finition, équilibrage et contrôles individuels ; aucun STL du scan ne les définit |
| Soupapes, ressorts, roulements, segments, joints et visserie | composants spécialisés à spécifier ou acheter | référence fournisseur, température/régime/charge admissibles et compatibilité des interfaces |

[EOS](https://www.eos.info/metal-solutions/metal-materials/aluminium) documente
AlSi10Mg et AlF357 pour l'additif ;
[Constellium](https://www.constellium.com/products/aluminium-powders/)
documente Aheadd CP1 pour LPBF. Ces sources établissent des pistes de matière,
pas des valeurs admissibles pour ce moteur. Les dossiers antérieurs
[F19](../../twins/reference-917-engine/manufacturing-routing-f19.json) et
[F49](../../twins/reference-917-engine/material-lpbf-qualification-f49.json)
restent des études à réévaluer, sans transfert de qualification.

Pour chaque pièce candidate : nuance et lot, machine, paramètres, orientation,
supports, évacuation de poudre, traitement thermique/HIP éventuel, surépaisseurs
d'usinage, rugosité, tolérances, contrôles CT/NDT et éprouvettes du procédé final.
Toute route titane doit aussi documenter fatigue et isolation galvanique.
Un moteur fonctionnel n'exige pas que tous ses composants soient imprimés.
Les décisions de pièce et leurs preuves seront portées par `catalog/parts/`.

## Suite du travail et critères de passage

1. **Métrologie** : identité et variante du spécimen, licence exacte, unité,
   incertitude, datums et interfaces mesurés. Critère : contrat d'interfaces
   vérifié indépendamment sur le même spécimen.
2. **CAO par pièce** : carter, cylindre, culasse puis train mobile dans PicoGK,
   avec cotes/tolérances sourcées, assemblage et circuits internes. Critère :
   comparaison au scan et aux mesures, nomenclature et interfaces complètes.
3. **Calculs** : cinématique/contact, lubrification, débit/thermique, contraintes
   et fatigue sur les chargements du moteur choisi. Critère : convergence,
   bilan et corrélation physique ; les essais numériques d'archives ne suffisent pas.
4. **Procédé** : éprouvettes et prototype représentatif, finition et contrôle
   sur la machine retenue. Critère : propriétés admissibles et inspection
   satisfaisant le plan validé par le responsable d'ingénierie.
5. **Essais** : assemblage, étanchéité, lubrification, entraînement externe puis
   banc instrumenté progressif. Critère : revue professionnelle documentée et
   validation du plan avant fabrication ou mise en route de pièces chargées.

Aucune impression métal fonctionnelle, mise en route ou puissance n'est validée
par cette première reconstruction. La prochaine donnée nécessaire est un
contrat de métrologie pour le carter/cylindres exact, avant de figer leur CAO.
