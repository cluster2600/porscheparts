# 935 — rotor fermé sous hypothèses et premiers solveurs

[Dossier](README.md) · [Plan](RECONSTRUCTION_PLAN.md) ·
[État de référence](STATUS_20261012.md) · [Banc](BENCH_PROTOCOL.md)

## Résultat et statut des cinq étapes

Cette continuation produit un **candidat de rotor entier**, des masses et
inerties sur dix cartes matière, un pilote CFD MRF/SST, un maillage mécanique
du rotor entier et un USD géométrique. Elle ne clôt pas les cinq étapes du
système : le mécanisme complet, les interfaces de montage et la confrontation
au banc restent à établir. La cible demeure la 935 ; aucune adaptation 993
n'entre dans ce lot.

| Étape | Travail livré | Clôture |
|---|---|---|
| 1. Métrologie et reconstruction | Source de pale acquise, recalage cyclique des contours, répétition périodique et fermetures explicitement hypothétiques. | Échelle à confirmer par deux cotes par scan ; comparaison indépendante des surfaces et variante exacte encore nécessaires. |
| 2. Pièces et assemblage | Rotor fermé en un solide, STEP relu et FCStd avec composants et union. | Arbres, renvoi, roulements, fixation moteur et guides ne forment pas encore un assemblage fonctionnel. |
| 3. Calculs | Masses/inerties, 80 scénarios cinétiques, pilote CFD et calcul centrifuge 3D. | Convergence CFD/structure, charges aérauliques, thermique, modes, fatigue et transmission ne sont pas validés. |
| 4. Fabrication | Source régénérable, surfaces du candidat et liste des opérations/contrôles ci-dessous. | Dossier provisoire ; interfaces, tolérances, procédés qualifiés et revue mécanique manquent. |
| 5. Jumeau et banc | Géométrie USD, unités SI, dix variantes masse/inertie et rotation prescrite. | Rotor seul ; aucune simulation dynamique du mécanisme ni mesure de banc utilisée. |

Les contrats de référence ne sont pas remplis avec ces hypothèses : les
17 interfaces restent non vérifiées et les autorisations de fabrication et de
validation physique restent à `false`.

## Reconstruction et variantes rejetées

Les anciennes plages observées constituent les entrées. Leur empreinte et
les transformations d'acquisition sont conservées. L'échelle de
**1 mm par unité source** est une hypothèse de travail, pas une calibration ;
les précisions annoncées dans les noms des OBJ ne définissent pas leurs unités.

Une première fermeture utilisait la médiane de plusieurs contours. Elle
produisait un solide valide, mais l'inspection multivue a révélé des pointes
irrégulières. **Cette variante est rejetée**, avec ses géométries, images et
reçus conservés. Une convergence du volume ne suffit pas à accepter une forme.

Le candidat suivant utilise une pale mieux couverte. Les contours sont
recalés par permutation cyclique avant loft ; neuf secteurs identiques sont
une hypothèse de périodicité. Les sections absentes aux pieds/extrémités
prolongent un profil constant ; l'extrémité est recoupée circulairement.
La cuvette, son épaisseur, sa fermeture et le bossage sont des définitions
provisoires. Les raccordements ne constituent pas des congés qualifiés.
Les autres pales acquises restent disponibles pour une comparaison
indépendante ; elles ne sont pas remplacées dans les scans originaux.

Le FCStd contient les composants BRep importés et une union éditable.
Les paramètres et profils régénérables sont dans le cas JSON, les sections
JSON et le programme Python ; ce FCStd n'est pas un historique natif complet
de toutes les sections. Le STEP est relu et contrôlé en volume et solidité.

## Environnement requalifié

Kali2 était inaccessible à l'adresse connue. Aucun changement de certificat
ou de secret n'a été effectué. Les travaux utilisent le Mac et les conteneurs
Linux locaux, sans nouvelle location Vast.

| Outil | Runtime exécuté |
|---|---|
| .NET | SDK 9.0.318, installé dans le dossier privé du lot |
| PicoGK C# | 2.3.0, tag officiel `PicoGK-v2.3.0`, commit `14c5384bcac57ede245021bb78e70d1445b40e3f` |
| PicoGK natif | Core 26.2.0, build du 5 juin 2026, macOS ARM64 |
| FreeCAD | 1.1.4, macOS ARM64 ; STEP/FCStd relus |
| Science/CAO | Linux AMD64 : NumPy 2.5.2, SciPy 1.18.1, build123d 0.11.1, Gmsh 4.12.1 |
| CFD | OpenCFD OpenFOAM v2406, Linux ARM64 |
| Structure | CalculiX 2.21 ; exécutions AMD64 émulée et ARM64 native séparées dans les journaux |
| USD | usd-core 25.11 ; relecture des dix variantes et des tenseurs d'inertie |

Les versions/empreintes effectivement utilisées sont conservées avec les
résultats. Les anciens verrous, reçus et recettes ne sont pas modifiés.
Le code et les binaires PicoGK proviennent du
[dépôt officiel LEAP 71](https://github.com/leap71/PicoGK/tree/PicoGK-v2.3.0).
L'authoring utilise les schémas USD Physics standards ; un export lisible
n'est pas une validation de simulation Omniverse ou du fonctionnement réel.

## Résultats conditionnels du candidat périodique

Le BRep fermé représente environ **426,24 cm³** à l'échelle supposée.
Après correction locale des deux artefacts voxel, la surface fine est fermée,
avec une composante et une orientation cohérente. La variation du volume
entre 0,4 et 0,2 mm vaut **0,0149 %** et celle des inerties principales
**0,0133 %**. Ces contrôles portent sur la discrétisation du candidat,
pas sur sa fidélité historique ou ses tolérances de fabrication.

| Carte | Masse CAD supposée | Inertie polaire au repère candidat |
|---|---:|---:|
| AlSi10Mg | 1,138 kg | 0,009408 kg·m² |
| WE43 | 0,780 kg | 0,006448 kg·m² |
| Ti‑6Al‑4V | 1,876 kg | 0,015504 kg·m² |

À 6 000 tr/min, sur le **même maillage hexaédrique de 1,5 mm**, les calculs
série fournissent les valeurs ci-dessous. L'encastrement et le matériau
isotrope sont supposés ; la pression aérodynamique et la température ne sont
pas appliquées. Le pic n'est pas une contrainte admissible et la convergence
au raffinement n'est pas établie.

| Carte | Pic von Mises | Déplacement maximal |
|---|---:|---:|
| AlSi10Mg | 122,6 MPa | 0,138 mm |
| WE43 | 84,0 MPa | 0,150 mm |
| Ti‑6Al‑4V | 202,1 MPa | 0,145 mm |

Le premier point CFD termine 400 itérations avec une erreur de bilan
volumique d'environ **0,0634 %**. La pression demeure instable : ce point
est **refusé pour la courbe débit–pression**, et aucun rendement du montage
935 n'est annoncé. Les maillages intermédiaire/fin sont préparés ; leur
convergence n'est pas démontrée par le pilote grossier.

## Commandes et interfaces reproductibles

Le coordinateur conserve trois arguments : cas, étape, nouveau dossier privé.
Les étapes nouvelles sont séparées de la reconstruction des surfaces observées :

```sh
python twins/935-horizontal-cooling-system-f0/source/run_reconstruction.py \
  /private/candidate-case.json candidate /private/new-components

python twins/935-horizontal-cooling-system-f0/source/finalize_candidate_cad.py \
  /private/components.step COMPONENTS_SHA256 /private/candidate-case.json /private/new-cad

dotnet build twins/935-horizontal-cooling-system-f0/source/picogk-candidate-rotor/CandidateRotor.csproj \
  -c Release -p:PicoGKAssembly=/private/runtime/PicoGK.dll

dotnet /private/CandidateRotor.dll /private/candidate.stl STL_SHA256 \
  0.4 /private/new-voxels 4,3,2

python twins/935-horizontal-cooling-system-f0/source/run_reconstruction.py \
  /private/cfd-case.json cfd-candidate /private/new-cfd

# Dans le runtime OpenCFD v2406, après chargement de son environnement :
bash twins/935-horizontal-cooling-system-f0/source/run_candidate_cfd.sh /private/new-cfd/artifacts/coarse

python twins/935-horizontal-cooling-system-f0/source/run_reconstruction.py \
  /private/fea-case.json fea-candidate /private/new-fea

# L'exécution série copie le deck vérifié vers un nouveau dossier de travail.
bash twins/935-horizontal-cooling-system-f0/source/run_candidate_fea.sh \
  /private/new-fea/artifacts/rotor.inp DECK_SHA256 /private/new-solve

python twins/935-horizontal-cooling-system-f0/source/run_reconstruction.py \
  /private/twin-case.json twin-candidate /private/new-twin
```

Dans un checkout Git, les sorties dérivées doivent se trouver dans `work/`
ignoré. Les exemples `/private/` désignent un dossier privé extérieur au dépôt.
Un dossier existant est refusé. Chaque cas référence les empreintes des
entrées ; le coordinateur sauvegarde les échecs sans promouvoir les résultats.
Les STL sources du candidat sont en mm ; les STL CFD et le USD sont en mètres.
Le maillage CalculiX utilise N–mm–tonne–s, avec contraintes en MPa.

## Limites des calculs et contrôles

La densité transforme le volume et les inerties géométriques en masse et
inertie mécanique. Les dix cartes précédentes restent des comparateurs.
Le WE43 conserve des propriétés de substitution non qualifiées pour la pièce.
Les scénarios de freinage utilisent les régimes, temps d'arrêt et balourd
supposés de la campagne existante ; ils ne donnent pas de vitesse admissible.

Le pilote CFD place le rotor dans un conduit carré hypothétique :
**6 000 tr/min, débit imposé de 0,6 m³/s**. Ce débit est une condition de banc
numérique, pas le débit prédit du montage moteur. Les stations utilisent
la moyenne surfacique de `rho*(p + |U|²/2)` ; le couple est calculé à partir
du moment fluide au repère candidat. L'acceptation exige aussi la stabilité
de ces grandeurs et les trois maillages. Les premières tentatives ont été
conservées : conversion SI, position du point fluide, diagnostics de
concavité et en-tête du dictionnaire de qualité ont été corrigés. Le contrôle
`checkMesh -meshQuality` applique les seuils explicites ; le diagnostic
géométrique complet du premier maillage demeure conservé séparément.
Les couches de paroi, le y+, le carter réel et les pertes moteur ne sont pas
qualifiés par ce pilote.

Les tentatives tétraédriques du BRep ont échoué sur des intersections de
facettes. Le pilote mécanique utilise donc des cellules hexaédriques dont
les centres sont dans le champ signé PicoGK, avec contrôle Gmsh des Jacobiennes,
de la connexité, du bore et du volume. Aucun fragment n'est silencieusement
supprimé. Les grilles grossières déconnectées ou remplissant le bore sont
refusées. Le cas exécuté encastre un bore nominal ; il applique seulement la
centrifugation, à matériau isotrope et Poisson supposé de 0,33.
Ce n'est ni un contact arbre/moyeu réel, ni un calcul de fatigue.

Les sorties ARM parallèles ayant échoué à l'équilibre des efforts sont
rejetées. Les rejouements et journaux de chaque architecture sont conservés ;
le lanceur utilise désormais un calcul série dans un dossier neuf. Un code
de retour nul ne vaut pas acceptation des contraintes ou de la vitesse.

La voxelisation à 0,2 mm a aussi produit deux petits polyèdres isolés de douze
triangles. Ils sont identifiés comme artefacts numériques d'un BRep d'entrée
à un seul solide, jamais comme fragments du scan. Une exclusion locale
explicite conserve les coordonnées/octets de toutes les autres faces ;
les sorties brutes et la conversion de format rejetée restent conservées.
La fermeture et la connexité du résultat sont recontrôlées après correction.

Le USD vérifie masses, unités, centres et tenseurs d'inertie après relecture.
La rotation est **cinématiquement prescrite** ; elle ne prouve pas que les
engrenages transmettent le couple, que les roulements tiennent ou que les
interférences ont été résolues.

## Fabrication — dossier encore provisoire

| Élément | Définition/contrôle requis avant fabrication fonctionnelle |
|---|---|
| Rotor | Calibrer le scan, qualifier pieds/congés/épaisseurs, bore et retenue ; contrôler déformations, modes précontraints, survitesse et fatigue ; définir équilibrage. |
| Moyeu/arbre | Ajustements, cannelures/clavette, serrage, retenue axiale, concentricité et transmission du couple de freinage mesurés. |
| Renvoi | Denture, rapport, entraxes, appuis, jeu, lubrification, joints et dissipation définis ; une enveloppe extérieure ne les détermine pas. |
| Support/carter | Plans des fixations moteur, chemins de charge, rigidité, jeux chauds/froids et accès maintenance confirmés. |
| Guides d'air | Surfaces, fuites et raccordement au moteur établis avant de conclure au refroidissement installé. |

Pour AlSi10Mg, WE43 ou Ti‑6Al‑4V, le fournisseur doit figer procédé,
orientation, poudre, traitements, reprises d'usinage et coupons. Le dossier
doit couvrir contrôle dimensionnel, défauts/porosité, fatigue, contrôle non
destructif et équilibrage. Pour le titane, ajouter l'isolation galvanique
aux interfaces et la traçabilité des traitements. Les surépaisseurs d'usinage
et tolérances restent à définir avec les interfaces et le procédé retenus ;
les précisions des scans ne les remplacent pas.

Le [protocole de banc](BENCH_PROTOCOL.md) doit ensuite être exécuté sur un
ensemble mécanique revu, avec points de mesure réservés pour la corrélation.
Il faut un donneur/receveur identifié, des cotes de référence et un atelier
ou banc accessible pour clôturer la réplique de montage et la validation physique.
Ni le volume fermé, ni les tests logiciels, ni le USD ne remplacent ces preuves.

Les résultats, cas, sources de chaque tentative et dérivés restent dans le
[dépôt privé](https://github.com/cluster2600/porscheparts-935-private).
Le Git public contient uniquement programmes, tests et documentation.
