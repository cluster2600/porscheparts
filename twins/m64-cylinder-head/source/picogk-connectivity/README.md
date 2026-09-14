# Connectivité échantillonnée des vides PicoGK

Ce module **lit** le VDB existant, sans modifier le corps, créer de conduit,
lisser ou retraiter ses surfaces. Il distingue la connectivité d'un volume
vide de la connexité des surfaces STL qui le bordent. Une enveloppe externe
et une paroi interne peuvent délimiter un seul volume fluide connecté.

## Deux contrôles séparés

1. `OccupancySampler` C# relit par nom `head_body` et
   `unclassified_void_complement`. Il vérifie le hash VDB du rapport source,
   les quatre champs et leur résolution, puis utilise l'adaptateur ABI isolé
   sur un octet déjà documenté dans `picogk-cooling`. Le témoin natif
   intérieur/matière/extérieur précède toute lecture de la pièce.
2. `connectivity.py` propage depuis **tous les échantillons vides des six faces
   du bord**. Il calcule séparément les connectivités à 6 voisins (faces) et
   à 26 voisins (faces, arêtes, sommets). Aucun raccord périodique n'est permis.

Les positions de la grille sont `enclosure_min + (indice + phase) × pas`,
avec dimensions `floor(taille_boîte/pas)`. Le cadre de départ est ainsi
explicitement intérieur à la boîte de travail. Une présence de matière sur
son bord invalide le contrôle. L'échelle « mm » reste celle de l'hypothèse
non certifiée du VDB, sans nouveau recalage. La grille de connectivité peut
être plus grossière que les voxels natifs : les deux pas sont enregistrés.

Les cellules non reliées au bord sont des **cavités potentielles de cette
grille**, pas une preuve d'étanchéité physique. Une ouverture sous-résolue peut
disparaître ; un simple contact diagonal accepté à 26 voisins n'offre pas
nécessairement une section de passage physique. Aucun résultat ne classe
automatiquement admission, échappement, lubrification ou refroidissement.

## Témoins et arrêt conservateur

Les tests Python exécutent le vrai algorithme sur un cube creux, un tunnel,
un tunnel rebouché, un contact diagonal, les six faces de départ, les cas
tout vide/tout plein et des données invalides. Ils vérifient aussi la
conservation de l'entrée et l'absence d'autorisation CFD/fabrication.

Le mode natif `--witness` génère seulement deux petites géométries synthétiques
(cube creux puis cube avec tunnel) pour tester l'occupation avant le corps.
Un recouvrement autre qu'un double zéro exactement démontré, ou un défaut
d'union, reste un **échec**, conserve `sampling-report.json` et `FAILED.json`,
et interdit la propagation Python.

Attention au zéro : le kernel épinglé définit `bIsInside` par une lecture du
voxel d'indice arrondi, **SDF ≤ 0**, pas par une interpolation continue. Une
interface exactement au niveau zéro peut donc appartenir aux deux champs.
Le sampler diagnostique chaque recouvrement (maximum 4 096) par lecture d'une
coupe SDF native, avec X croissant/Y décroissant et le même arrondi natif.
Le premier témoin tunnel a été rejeté pour 48 recouvrements ; la relecture
signée a démontré 48 couples `(-0,+0)` et aucune double valeur négative.
Ce reçu initial est conservé. Deux conventions explicites sont désormais
exécutées sur la même grille : double zéro affecté à la matière (principale)
ou au vide (sensibilité), chacune avec 6 et 26 voisins. Aucun epsilon, point
supprimé ou déplacement n'est appliqué. Les masques ne doivent différer que
du nombre exact de doubles zéros. Toute autre contradiction reste bloquante.
Ces valeurs sont en unités SDF natives, pas une mesure de distance en mm.

## Exécution bornée

```sh
python3 -B -m unittest discover -s tests -p test_picogk_connectivity.py -v
dotnet build OccupancySampler.csproj -c Release -o NEW_BIN \
  -p:UpstreamRoot=/upstream -p:GeneratePackageOnBuild=false
timeout --signal=TERM --kill-after=10 300 \
  dotnet NEW_BIN/OccupancySampler.dll --witness NEW_WITNESS_DIR
python3 -B connectivity.py NEW_WITNESS_DIR/hollow-cube NEW_WITNESS_DIR/hollow-connectivity.json
python3 -B connectivity.py NEW_WITNESS_DIR/cube-with-tunnel NEW_WITNESS_DIR/tunnel-connectivity.json
python3 -B check-native-witness.py NEW_WITNESS_DIR
```

Après réussite des témoins seulement, le mode de lecture du corps est :

```sh
timeout --signal=TERM --kill-after=10 300 \
  dotnet NEW_BIN/OccupancySampler.dll INPUT.vdb SOURCE_REPORT.json \
  NEW_PRIVATE_SAMPLES 1.2 0.371
timeout --signal=TERM --kill-after=10 300 \
  python3 -B connectivity.py NEW_PRIVATE_SAMPLES NEW_PRIVATE_CONNECTIVITY.json
```

Employer les ressources existantes, au plus 2 CPU et 4 Gio. Aucun paquet
Python tiers n'est requis. Le programme refuse plus de quatre millions
d'échantillons ; la file utilise des entiers de quatre octets et les labels
un octet par échantillon. Chaque propagation est bornée à 240 secondes et
100 000 composantes. Les sorties doivent être nouvelles. Les VDB, masques
d'occupation, positions et boîtes de composantes privées ne vont pas au dépôt.

Un volume calculé par `nombre_de_cellules × pas³` est une estimation de
grille. L'accord entre 6 et 26 voisins ne prouve ni la convergence en pas et
en phase, ni la continuité géométrique, ni un maillage CFD exploitable.
Les bornes numériques ci-dessus ne sont pas des critères physiques.

## Premier résultat privé, 7 septembre 2026

Le [reçu public agrégé](../../evidence/picogk-connectivity-20260907.json)
trace la lecture du champ natif de 0,3 sur la grille de pas 1,2, phase 0,371.
Sur 2 719 728 échantillons, 1 898 164 sont vides et **tous sont reliés au bord**
en 6 comme en 26 voisins. Aucune composante isolée n'est détectée **sur cette
grille seulement**. Elle ne contient aucun double zéro : les deux masques sont
identiques et les résultats de sensibilité ont donc été réutilisés, pas
recalculés artificiellement pour annoncer quatre exécutions distinctes.

L'audit triangulaire indépendant des résolutions plus fines a signalé de
minuscules coques orientées négativement. Un pas 1,2 peut ne pas les rencontrer.
Le présent contrôle ne les supprime pas et ne tranche ni leur imbrication,
ni leur caractère physique : **absence détectée sur la grille ≠ absence de
cavité dans le B-Rep, le VDB ou la pièce réelle**. La comparaison en résolution
et en phase, et la localisation géométrique ciblée restent à faire.
