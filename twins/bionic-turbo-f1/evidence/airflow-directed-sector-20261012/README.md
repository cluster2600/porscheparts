# Secteur dirigé : qualité des cellules et sensibilité au pas de temps

Cette étape utilise un petit secteur synthétique extrait du témoin 035.
Elle ne reconstruit pas le turbo complet. Les parois de coupe angulaire sont
artificielles et fixes ; rotor et ports sont absents. Aucun débit ou gain de
puissance physique n'est évalué.

## Pourquoi raffiner dans la direction angulaire

La localisation des rejets de 041 est reproduite après vérification de tous
les payloads parents. Les 61 440 sous-cellules rejetées comprennent 40 960
tétraèdres et 20 480 pyramides. Leurs hauteurs sont de 24,992 à 25,009 µm,
pour des arêtes de base de 683,987 à 749,308 µm. Cela motive une réduction
de la longueur angulaire, sans changer les pas axial et radial ni les seuils
natifs. Ce constat ne prouve pas une cause unique.

Le facteur angulaire huit vise des segments d'environ 90 µm au lieu de
700 µm. Il n'est pas choisi par assouplissement des critères du mailleur.
Le préparateur réutilise les points et les adresses de la grille 035 ; il
refuse une grille incomplète ou dupliquée. Il est destiné à cette grille
locale à cinq couches, pas à un maillage adaptatif quelconque.

## Géométrie et contrôle natif

Une lecture indépendante de la connectivité prouve que le secteur grossier
contient exactement 315 points, 608 faces et 160 cellules sources. Ses
96 faces de paroi d'origine sont complétées par 160 faces de coupe fixes.
L'angle est 2,8125°. Le témoin 042 facette les faces gauchies puis subdivise
les cellules en conservant la frontière, selon les préparateurs épinglés
040/041. Ses 1 280 cellules reproduisent le rejet : 480 déterminants trop
faibles, minimum 0,0001356918 ; 1 200 faces dépassent 70° de non-orthogonalité,
maximum 83,8078°. Aucun solveur n'est lancé sur 042.

043 affine seulement la direction angulaire huit fois. Les nouveaux points
MRF sont projetés sur le même profil analytique ; ses facettes deviennent
plus fines, elles ne sont pas géométriquement identiques aux anciennes
cordes. Tous les anciens points restent identiques. Les points des murs
latéraux sont des interpolations sur leurs facettes d'origine, avec une
erreur de plan maximale de 1,062e-17 m. Les plans de fermeture et de coupe
restent fixes. Le volume de frontière vaut 1,266450596871644e-9 m³ ; les
lectures 042/043 ne diffèrent que de 5e-16 relatif.

043 possède 3 065 points, 26 864 faces et 12 480 cellules : 9 600 tétraèdres
et 2 880 pyramides. Les 320 quadrilatères MRF restent plans et tangents :
normale géométrique de rotation maximale 1,65448e-11 m/s. Le bilan
maximal par cellule tournante est 2,11758e-21 m³/s. Ce flux est géométrique,
sans valeur de débit d'air. `checkMesh -allTopology -allGeometry` donne
`Mesh OK`, une région fluide, aucune concavité et un déterminant minimal
0,0067637044. Les 417 faces au-dessus de 70° de non-orthogonalité sont
conservées dans les diagnostics : maximum 70,8352°. Cette admission ne
prouve pas la stabilité temporelle.

## Comparaisons d'écoulement au repos

Les équations, schémas, conditions aux limites et tolérances restent celles
de 026. La précision écrite reste 16. Les seuils d'identité au repos sont
0,001 Pa, 1e-6 K et 1e-8 m/s, à maintenir pendant 20 µs.

044 utilise le pas initial de 0,1 µs, 200 pas. Son Courant maximal atteint
2,0599324, contre 0,0442925 pour 039 avec le même pas. Le changement de
volume et de forme des cellules change donc aussi la résolution temporelle
relative. Il termine nativement mais échoue aux trois seuils ; ses champs
p/T/U sont relus et finis. 647 plafonds de 1 000 itérations de pression sont
atteints. Ce cas reste rejeté.

045 est le contrôle inertiel : seule la vitesse du repère devient zéro.
046 est le contrôle temporel tournant : seul le pas est divisé par deux,
à 0,05 µs, avec 400 pas pour conserver 20 µs. L'intervalle d'écriture finale
passe à 400 ; ce changement ne modifie pas les équations. Ce sont des
contrôles distincts, et aucun ancien calcul n'est relancé.

| Cas | Modification | Erreur p max (Pa) | Erreur T max (K) | U max (m/s) | Repos |
|---|---|---:|---:|---:|---|
| 044 | Tournant, pas 0,1 µs | 0,00285414 | 1,98373e-6 | 4,50283e-5 | Rejeté |
| 045 | Seul omega = 0 | 4,07454e-10 | 1,02318e-12 | 6,54559e-12 | Seuils respectés |
| 046 | Tournant, pas 0,05 µs | 0,140880 | 9,62009e-5 | 0,00196865 | Rejeté |

Les trois calculs terminent nativement, code zéro, en 442,783 s, 538,979 s
et 761,493 s respectivement. Les champs p/T/U sont relus, avec 12 480
cellules finies chacun. La comparaison des entrées prouve que 044/045 ne
diffèrent que par MRFProperties, et 044/046 que par controlDict. Le maximum
Courant de 046 est environ 1,0299662. La diminution du pas n'améliore pas
le repos sur la même durée physique ; le Courant élevé de 044 n'est donc
pas une explication suffisante ni une correction démontrée.

Les plafonds de 1 000 itérations de pression sont atteints 647, 800 et
1 168 fois respectivement. **Aucune convergence linéaire n'est qualifiée.**
Le contrôle inertiel est utile, mais il ne valide pas le modèle tournant.
Les valeurs de Courant et la totalité des historiques sont conservées.

La prochaine enquête doit distinguer opérateur tournant, correction de
pression, forme des cellules et frontières synthétiques de coupe. Ne pas
transposer ces murs artificiels au turbo réel, ni attribuer la dérive à une
cause unique sans contrôle supplémentaire. Un éventuel témoin périodique
constituerait un problème aux limites différent et devrait être présenté
comme tel ; il ne ferait pas disparaître les rejets des murs fixes.
La [source officielle v2406 de l'équation de pression](https://gitlab.com/openfoam/core/openfoam/-/raw/OpenFOAM-v2406/applications/solvers/compressible/rhoPimpleFoam/pEqn.H)
est référencée avec son empreinte, sans modification de code ou de réglage
de solveur. Aucun balayage arbitraire de tolérances n'est justifié par ces
résultats.

## Reproduction et limites

`run_sector.py 1 42` et `run_sector.py 8 43` créent des cas neufs. Ils
conservent les maillages de base et intermédiaires ainsi que le maillage
final. Les coordonnées et connectivités sont générées directement ; le
blockMeshDict parent est conservé comme entrée historique et n'est pas
exécuté. Les contrôles natifs utilisent l'image OpenFOAM v2406 épinglée.
Les trois runners d'écoulement conservent les entrées, journaux, champs et
reçus terminaux. Les lecteurs vérifient les empreintes et relisent les
champs natifs, sans se limiter aux résumés.

105 tests turbo réussissent et un est ignoré. `make check` exécute 3 829
tests, avec 171 ignorés, les deux échecs flottants et trois erreurs
rtree/networkx hors turbo déjà connus. Les tests ajoutés couvrent le partage
des faces, la conservation du volume et des points, les parois, la tangence
MRF et le refus d'une grille incomplète. Aucune preuve précédente n'est
modifiée.

L'admission, l'identité au repos, la convergence linéaire et l'indépendance
au maillage/au pas sont des qualifications différentes. Un témoin local
ne qualifie ni le turbo complet ni des couches de paroi, une courbe de débit,
une puissance maximale ou un jumeau calibré. La correction roue–écrou 033
reste à conserver dans la prochaine reconstruction complète.

## Archive native

[Archive 042–046](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-directed-sector-2026-10-12) : 190 fichiers, 3471115 octets, SHA-256
`ecc721d4596107a38857571f68dc932e3e3003b281b3d857e00990c2c603f8f4`.
Tous les payloads sont relus localement. Les cinq actifs GitHub sont
vérifiés par tailles et SHA-256 distants, sans second téléchargement
intégral revendiqué. Les journaux et leur espacement restent inchangés
pour conserver leurs empreintes.

