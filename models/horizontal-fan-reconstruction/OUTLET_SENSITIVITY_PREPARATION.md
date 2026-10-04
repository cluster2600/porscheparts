# Sensibilité à la position de sortie : préparation D2

**Préparation uniquement : aucun nouveau maillage ni solveur lancé.** Le
[diagnostic](results/cfd/outlet-preparation-diagnostic.json) relit les champs
natifs privés vérifiés par SHA. Le [protocole proposé](parameters/outlet-sensitivity-proposed-protocol.json)
fixe les hypothèses, les observables et le budget avant une éventuelle exécution.
[D1C](D1C_EXECUTION.md) reste le dernier calcul : V2 fin admis numériquement,
sortie et champs locaux non qualifiés. Les dimensions installées restent inconnues.

## Distance et forme proposées

La sortie actuelle est à z = −49,5 mm, rayon maximal 138,6 mm : 4 542 triangles,
0,0603336 m², contour polygonal de 156 arêtes. Aucun propriétaire de face de
sortie n'appartient à la zone MRF, dont les centres couvrent z ≈ ±41,2498 mm.
À 960, le reflux brut est 0,123990 m³/s ; **87,48 % de ce reflux se trouve à
r < 0,6 fois le rayon de sortie**. L'anneau externe r > 0,75 R apporte
1,150090 m³/s net. Ce reflux central étendu justifie de déplacer sensiblement
la frontière, plutôt que de traiter uniquement le jeu de bout de pale.
Aucun champ n'existe sous la sortie actuelle : ni longueur de fermeture de
recirculation ni minimum physique d'extension ne peuvent être déduits.

Le premier essai proposé ajoute **275 mm vers −Z**, un diamètre *supposé* du
rotor, jusqu'à z = −324,5 mm. C'est une distance discriminante proposée, sans
preuve qu'elle suffise. La distance axiale du hotspot identifié à la frontière
passe d'environ 33,6 à 308,6 mm. La section reste le même polygone : ni diffuseur,
élargissement radial, plénum automobile ou nouveau jeu n'est introduit.

Les triangles existants seraient prolongés en **50 couches prismatiques de
5,5 mm** : 227 100 nouvelles cellules, total 680 596 contre 453 496. Ce pas reste
inférieur à la cible globale 5,6 mm du cœur ; 40 couches seraient moins coûteuses
mais donnent 6,875 mm. Le diagnostic algébrique donne un minimum de déterminant
interne proxy 0,380274 pour la dernière couche à 50 niveaux, au-dessus du seuil
original 0,001. **Ce screening ne remplace pas checkMesh.** Les sommets/cellules,
volumes et connectivité du cœur, le CAD V2, les patches physiques, le rotor et
l'appartenance MRF doivent être inchangés. Les anciennes faces de sortie deviennent
internes avec correspondance explicite et orientation vers −Z ; aucune
interpolation du cœur ni renumérotation des cellules communes.

Les parois du prolongement virtuel utilisent `U slip`, `p/k/omega zeroGradient`
et `nut calculated`, sur un patch générique. Le carter original reste inchangé.
Cela évite l'ajout d'une perte de frottement de conduit sans géométrie mesurée ;
confinement et mélange turbulent du sillage restent possibles. Une différence
mesurée dépendrait donc du **domaine ainsi modélisé**, pas seulement d'une erreur
artificielle de condition limite. La condition slip est documentée dans le
[code Foundation13](https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-13/master/src/finiteVolume/fields/fvPatchFields/derived/slip/slipFvPatchField.H).

La sortie éloignée conserve les conditions originales : p cinématique fixée à
0, `U pressureInletOutletVelocity`, k/omega `inletOutlet` avec valeurs entrantes
0,01 m²/s² et 10 s⁻¹, `nut calculated`. Entrée, rotation 6 000 tr/min, air
ρ = 1,2 kg/m³, ν = 1,5e−5 m²/s, kOmegaSST, schémas du premier ordre,
relaxation p = 0,15, relTol = 0,01 et **SIMPLE.consistent yes** restent identiques.
Les valeurs de turbulence sont des hypothèses, sans mesure installée.

## Observables dans le cœur strictement commun

| Observable | Sélection fixe | Statistique et unités |
|---|---|---|
| Q commun | Anciennes 4 542 faces, `commonOutletFlux` | Somme orientée de phi, positive vers −Z, m³/s ; hors MRF |
| Couple et puissance | Même surface rotor, même origine/axe Z | Couple total pression + visqueux du fluide sur rotor, N·m ; puissance = −Tz Ω, W |
| Pression commune | 5 825 cellules à −38 ≤ z < −34 mm, `commonPressureBand` | Moyenne volumique de p × ρ, Pa ; même sélection originale |
| Diagnostics de proximité | 4 542 propriétaires de sortie et 10 117 cellules de sillage r ≥ 120 mm, −22 ≤ z < −10 mm | Moyennes et différences locales, sans admission physique |

Les identifiants privés de cellules, volumes et hashes de chaque sélection sont
conservés ; la pression commune V2 `consistent yes` à 960 est **85,643055 Pa**.
Cette moyenne de bande est une pression statique de contrôle, pas une élévation
de pression entre ports. Comparer directement p = 0 à l'ancienne frontière avec
p interne après extension confondrait deux statistiques différentes. p est un
scalaire statique dans les deux régions ; le débit utilise exclusivement la
face commune hors MRF.

Le [fragment functionObjects](parameters/outlet-common-functionObjects.dict)
prépare une écriture à chaque itération. `surfaceFieldValue/orientedSum(phi)`
respecte la flipMap du faceZone ; le
[code officiel](https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-13/master/src/functionObjects/field/fieldValues/surfaceFieldValue/surfaceFieldValue.H)
précise que les champs volumiques ne sont pas interpolés sur ses faces internes.
La pression utilise donc `volFieldValue/volAverage` sur un cellZone fixe,
conformément au
[code officiel](https://raw.githubusercontent.com/OpenFOAM/OpenFOAM-13/master/src/functionObjects/field/fieldValues/volFieldValue/volFieldValue.H).
Le fragment ne crée pas les zones et n'a pas encore été testé dans un nouveau cas.

## Écart local de 317,7 Pa : ce que montrent réellement les champs

Les deux champs 960 comparés ont **le même domaine** et partent du même état 900 ;
seul le couplage `consistent` change. La cellule 288831, volume 0,712311 mm³,
est à (46,230 ; 124,591 ; −15,887) mm, r = 132,892 mm. Sa distance au centroïde
de face rotor le plus proche est environ 0,509 mm ; c'est un proxy géométrique,
pas une distance exacte à la surface. Sa pression passe de −1 248,215 Pa à 900
à −1 340,396 Pa dans le témoin et −1 022,727 Pa dans D1C : les évolutions
opposées −92,181 et +225,488 Pa expliquent arithmétiquement **317,669 Pa d'écart**.
ΔU vaut 6,820 m/s dans cette cellule ; le maximum ΔU ailleurs atteint 67,665 m/s.

La RMS volumique globale Δp est seulement 0,544038 Pa et le percentile 99 par
nombre de cellules vaut 0,216176 Pa. Cependant, les 12 cellules dépassant
100 Pa représentent 0,0006963 % du volume et portent 52,05 % de l'écart quadratique
pondéré. La bande z ∈ [−20 ; −15] mm concentre le hotspot ; à la sortie
z ∈ [−49,5 ; −45] mm le maximum est 8,096 Pa. Les intégrales stables masquent donc
une sensibilité locale forte. Ce constat ne localise pas les résidus algébriques,
ne démontre aucune oscillation physique, et ne prouve pas une causalité de sortie.
Le futur contrôle doit conserver RMS, percentiles et maxima, y compris dans le
sillage, même si ses observables intégrées passent.

## Protocole court et lecture des gates

1. Préparer l'append de prismes et les correspondances explicites, conserver
   l'affectation MPI des cellules du cœur sur quatre rangs ; affecter les colonnes
   au rang propriétaire de leur face originale. Vérifier identité CAD/cœur/MRF,
   zones communes et orientation. Exiger **checkMesh standard et étendu indépendants**,
   zéro échec et seuils originaux avant tout solveur. Stop si cette préparation
   échoue ; ni seuil assoupli ni remeshing du rotor dans ce lot.
2. Relancer **deux cas séquentiels de 60 itérations 961–1020**, depuis le même état
   privé D1C/960 avec `consistent yes` : sortie actuelle puis éloignée. Le témoin
   900–960 conservé ne remplace pas ce nouveau témoin. Cœur initial identique ;
   ajout initialisé par colonnes à partir des valeurs/flux de sortie, recette et
   hashes enregistrés avant départ. Le transitoire numérique ajouté peut rendre
   le budget insuffisant. Mesurer chaque itération, sauvegarder 980/1000/1020,
   aucune continuation automatique.
3. Exiger les **dix critères numériques originaux** et vingt mesures consécutives
   1001–1020, champs finis/complets adaptés au nombre réel de cellules. Ajouter
   un contrôle prospectif de stationnarité : pression commune écart-type ≤ 2 Pa ;
   entre les deux dernières fenêtres, ΔQ ≤ 1 %, ΔT ≤ 2 %, Δpression ≤ 2 Pa ;
   entre checkpoints 1000/1020, RMS volumique sur cœur Δp ≤ 1 Pa et ΔU ≤ 0,1 m/s.
   Les maxima locaux restent publiés et non qualifiés. Les résidus de matrices
   normalisés sur deux tailles de domaine ne mesurent pas directement l'effet
   physique du domaine.
4. **Seulement si les deux cas passent ces contrôles**, comparer leurs moyennes
   sur 1001–1020 : |ΔQ|/max(|Qa|,|Qb|) ≤ 1 %, |ΔT|/max(|Ta|,|Tb|) ≤ 2 %, idem
   puissance ; |Δpression commune| ≤ max(5 Pa, 1 % du maximum des deux valeurs
   absolues). Une division par zéro est explicitement indéfinie. Ces seuils sont
   un screening déclaré par l'analyste, sans tolérance Porsche ou validation
   expérimentale. Échec numérique : comparaison **inconclusive**. Numérique
   passé mais différences hors bandes : **point de fonctionnement du modèle
   dépendant du domaine**. Passage : seules ces intégrales sont peu sensibles à
   **cette extension** ; aucune indépendance générale, amélioration airflow,
   convergence locale ou validation du refroidissement installé.

## Budget proposé et préconditions restantes

D1C a coûté 117,182 s de solveur pour 60 itérations ; le ratio de cellules 1,501
estime environ 175,87 s pour la branche prolongée, sans garantie d'évolution du
conditionnement. Proposition : **4 CPU, plafond RAM + swap 5 GiB, réseau absent,
8–10 minutes nominales, 720 s maximum** pour l'ensemble exécution.
Sous-plafonds : append et gates 120 s, solveur témoin 180 s, solveur prolongé
300 s, préparation/reconstruction/audit/archivage 120 s. Le délai global reste
prioritaire, arrêt sans retry. Cette durée exclut le développement préalable du
mesher et du runner, qui **ne sont pas encore implémentés**. La mémoire proposée
est une limite et une estimation, pas une mesure agrégée du futur cas.

Préconditions : recette d'append et runner vérifiables, gates indépendants du
nouveau maillage, démarrage et correspondances des champs audités, lecture
correcte des quatre nouveaux functionObjects, ressources réellement libres et
coordination avant tout lancement. Aucun solveur futur n'est engagé par cette
préparation. Scan brut, champs complets et sélections natives restent privés.

Vérification reproductible sans solveur : `make fan-program-check`. La
[commande de diagnostic](source/diagnose_outlet_preparation.py) prend cinq chemins
privés : témoin960, archive D1C extraite, historique900, rapport JSON, sélection
NPZ privée. Elle refuse les entrées qui diffèrent des manifestes natifs ; sa
reproduction complète requiert ces entrées privées.
