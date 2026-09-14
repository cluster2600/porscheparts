# Témoin fin à masque monde fixe — comparaison rejetée

Cette version séparée conserve le programme, les critères et les reçus du
témoin 0,2 précédent. Le témoin 0,1 utilise les mêmes cylindres, le même rayon
de fermeture 1 et les mêmes régions monde : région autorisée
`[-8,-3,-8] → [8,3,8]`, masque `[-7.4,-2.4,-7.4] → [7.4,2.4,7.4]`.
Le recul est fixé à **0,6 unité**, soit 3h au pas 0,2 et 6h au pas 0,1.
L'alternative 3h au pas 0,1 aurait changé le masque à 0,3 unité ; elle n'a
pas été exécutée. La comparaison vise donc une même géométrie monde, mais
ne démontre pas une convergence asymptotique à partir de deux extractions.

La politique séparée `criteria-0p1-fixed-margin.json` a été enregistrée avant
exécution. Elle fixe les critères 5 % sur le volume effectivement ajouté
`Vaprès−Vavant` (dénominateur : volume ajouté au pas fin) et 0,2 unité sur les
distances bidirectionnelles échantillonnées. L'ajout booléen diagnostique
n'est pas confondu avec cette différence de volumes globaux.

## Garde renforcé, sans écraser le reçu précédent

`audit_buffered_surface.py` v2 exige explicitement les compteurs et deltas SDF
nuls hors ROI et aux protections, **zéro paire indisponible**, les six noms
de champs VDB exacts avec comparaisons bit à bit réussies et non vides, les
gardes d'occupation des deux conventions de zéro, la topologie normalisée
et le support de tous les triangles modifiés dans la ROI. L'audit v1
affichait les différences SDF mais ne les incluait pas dans sa décision.

Le reçu 0,2 exact a été relu avec cette décision v2 dans un **nouveau**
rapport, sans recalcul natif ni modification des anciens reçus : il passe.
Les tests numériques couvrent chaque échec SDF/VDB/occupation, les ensembles
de surfaces vides, le seuil volumique et un témoin de distance triangle-plan.
Ils complètent les contrats de politique et la revue indépendante du code.

## Résultats du 8 septembre 2026

Au pas **0,1**, 8 615 125 nœuds ont été comparés. Les valeurs de six champs
VDB relus sont bit à bit identiques dans leurs boîtes natives ; l'extérieur
de ces boîtes n'est pas inclus dans cette preuve. Aucun signe ni valeur SDF
n'a changé hors de la ROI autorisée. En revanche, **24 points protégés** sont
passés de zéro à strictement négatifs : changement pour `<0`, pas pour `<=0`.
Le maximum de différence SDF protégée est **0,0017724712379276752 unité monde**.
Cette différence n'est pas une borne du déplacement de l'isosurface.

| Contrôle | Pas 0,2 | Pas 0,1 |
|---|---:|---:|
| Volume réellement ajouté, unité³ | 9,4851540221 | 8,1763984723 |
| Volume de l'ajout diagnostique, unité³ | 5,8665534947 | 7,0556823288 |
| Résidu entre les deux, unité³ | 3,6186005274 | 1,1207161435 |
| Points protégés modifiés, convention `<0` | 0 | 24 |
| Triangles bruts exactement nuls, candidat | 16 | 0 |
| Triangles bruts exactement nuls, ajout diagnostique | 8 | 40 |

Au pas fin, les surfaces avant et après passent l'écran combinatoire brut.
L'ajout diagnostique brut reste rejeté à cause de ses 40 triangles nuls.
Après la seule suppression exacte de ces triangles dans une copie en mémoire,
chacune des trois surfaces forme une composante fermée orientée combinatoire.
Cela ne vérifie pas les auto-intersections géométriques ni la physique.

Les 19 846 faces retirées et 20 678 ajoutées au pas fin sont toutes contenues
dans la région autorisée. **Cela ne protège pas une interface située à
l'intérieur de cette région** : le garde des 24 points reste en échec.

L'écart relatif des volumes réellement ajoutés est **16,006504 % > 5 %**.
Les maxima des distances bidirectionnelles échantillonnées sont :

- Avant : **0,09240311** unité.
- Après : **0,10105891** unité.
- Ajout diagnostique : **0,36516039** unité, au-delà de **0,2**.

Les distances sont calculées vers toutes les faces de la surface cible, à
partir d'au plus 20 000 sommets/centroïdes déterministes par direction.
Ce ne sont pas des bornes de Hausdorff continues. Le résidu volumique reste
inexpliqué et n'est pas supprimé du rapport.

## Cause géométrique du garde : masque et protection se recouvrent

`diagnose_protected_points.py` utilise uniquement le reçu existant, sans
recalcul de champ. Les 24 points sont tous dans le masque intérieur et dans
la bande protégée autour de l'anneau `R=10, Y=0`. Le rayon du coin XZ du masque
vaut **10,46518036**, supérieur à 10 : une boîte reculée axialement ne suffit
pas à exclure une couronne radiale.

Les coordonnées synthétiques sont les symétries et permutations X/Z des
paires `(6,7000003 ; 7,3)`, `(6,8 ; 7,2000003)` et `(6,9 ; 7,1)`, à Y=0.
Leur distance à l'anneau est comprise entre **0,09141766 et 0,09949496 unité**.
Le diagnostic conserve les 24 coordonnées et valeurs exactes du reçu.
Le recouvrement est démontré ; l'origine algorithmique exacte des variations
SDF n'est pas identifiée par ce seul contrôle.

La correction future justifiable est un masque explicitement disjoint des
protections radiales, à tester séparément. Aucun nouveau masque, aucune passe
supplémentaire et aucun epsilon de tolérance n'ont été appliqués dans ce lot.

## Ressources et arrêt

Tout a utilisé Kali, réseau désactivé, 2 CPU / 4 Gio, délai maximal 300 s par
étape. Pour les 363 228 triangles du candidat fin, l'audit a reçu un opt-in
**ressources seulement** de 500 000 faces / 1 500 000 sommets. Les helpers
historiques restent inchangés sur disque, avec leurs limites de 150 000 faces.
Les prédicats exacts et seuils géométriques n'ont pas changé.

- Natif : 31,27 s ; pic processus 283 234 304 octets.
- Audit : 60,52 s ; RSS maximal GNU time 705 204 KiB.
- Comparaison : 7,53 s ; RSS maximal GNU time 296 092 KiB.

**Rejet maintenu, aucune application à l'admission privée.** Aucun achat Vast,
aucune modification du maître, aucune qualification CFD ou impression.

Empreintes des reçus privés :

- Natif fin : `7a088f495b8b4b5007e78f2c2d181fdf4e0eeb5fdc66003fab9c917570617ac3`.
- Audit fin v2 : `164093fc8077cd6cf61c977e7ec99bd273970d3e1cf995baf8af64b5862ed344`.
- Comparaison : `5b2db9a7db2234832c4a0c9c58f3248148c15938453bea6ab7fbc6aa179106dc`.
- Diagnostic des protections : `eaa8254fa1624e8fe0d807196671c2a8fb9df00611192c2037c0e45ac630d7e8`.
