# Contrôle périodique du secteur synthétique

Ce contrôle remplace les murs des deux coupes angulaires de 043 par une
paire cyclique. C'est un autre problème aux limites, pas une correction du
turbo réel. Les essais à murs fixes 044 et 046 restent rejetés et conservés.
Aucun rotor, port ou débit forcé n'est présent.

## Conservation et admission

047 garde exactement les 3 065 points, les 26 864 faces, les 12 480 cellules
et les 6 240 cellules tournantes de 043. Seule la numérotation des faces de
frontière et de leurs propriétaires est permutée. Les voisins, zones et
ensembles sont contrôlés ; les 417 faces du diagnostic nonOrthoFaces sont
intérieures, donc leur fichier reste identique. Les 768 faces de paroi
restantes conservent exactement leurs sommets et leur orientation.

Les 80 faces de chaque coupe sont appariées par une rotation de 2π/128
(2,8125°) autour de z. Les sommets et normales opposées sont vérifiés.
La transformation analytique du vecteur omega × r concorde à
7,396e-13 m/s. Il s'agit d'une vérification algébrique, pas d'un essai
manufacturé du transfert vectoriel dans la bibliothèque native.
Le type natif est cyclic, transform rotational, avec le centre et l'axe
explicitement déclarés. checkMesh vérifie les points couplés : écart moyen
1,74215e-17 m. Il conclut Mesh OK, une région fluide, aucune concavité,
déterminant minimal 0,0067637044. Les 417 faces au-dessus de 70° sont
conservées, avec un maximum de 70,8352°.

Les 320 quadrilatères MRF restent intacts : normale géométrique maximale
1,65448e-11 m/s et planéité à 5,726e-18 m. Tous les bilans géométriques par
cellule sont relus. Ils ne représentent pas des débits physiques.
Le volume total natif vaut 1,266450596871634e-9 m³.

## Contrôle de repos

048 reprend ce maillage avec les équations, schémas, tolérances, omega et
pas de temps de 044 : 200 pas de 0,1 µs jusqu'à 20 µs. Les seules différences
préparées concernent p/T/U aux coupes cycliques, boundary et les permutations
faces/owner. Les anciens murs latéraux restent fixes. Les seuils restent
0,001 Pa, 1e-6 K et 1e-8 m/s ; aucun réglage de solveur n'est modifié.

048 termine nativement en 479,762 s, code zéro, sans OOM. Les 200 pas
respectent les seuils : erreur de pression maximale 1,58616e-9 Pa,
erreur de température 5,87761e-10 K, vitesse maximale 9,72219e-12 m/s.
Les champs p/T/U finaux sont relus, finis et contiennent 12 480 cellules
chacun ; le maximum de vitesse du seul champ final vaut 9,58604e-12 m/s.
Tous les payloads et entrées préparées sont vérifiés par leurs empreintes.

| Contrôle | Erreur p maximale (Pa) | Erreur T maximale (K) | U maximale (m/s) | Repos |
|---|---:|---:|---:|---|
| 044, coupes fixes | 0,00285414 | 1,98373e-6 | 4,50283e-5 | Rejeté |
| 048, coupes cycliques | 1,58616e-9 | 5,87761e-10 | 9,72219e-12 | Seuils respectés |

Le Courant maximal de 048 reste 2,059932382 : son maintien près de celui
de 044 exclut d'attribuer ce résultat à une réduction du pas de temps.
800 plafonds de 1 000 itérations de pression sont atteints ; aucune
convergence linéaire n'est qualifiée. Le respect du repos ne démontre pas
la stabilité d'une perturbation finie ni la précision d'un écoulement forcé.

## Portée de la comparaison

La comparaison isole les conditions des coupes synthétiques sur cette même
géométrie. Elle ne démontre ni une cause unique de dérive dans tous les
maillages, ni la stabilité de perturbations, ni la convergence linéaire,
ni une correction du turbo complet. Le bilan géométrique et la tangence
MRF ne suffisent pas seuls à qualifier une simulation.

Le source officiel v2406 MRFZone.C classe les patches couplés et les
patches exclus parmi les faces demandant un traitement particulier.
Cette inspection ne prouve pas une cause unique et aucun code natif n'est
modifié. L'URL et l'empreinte figurent dans mrf-source-reference.json.

Le premier lecteur de différences attendait à tort une modification de
nonOrthoFaces ; son refus est conservé. La version v2 corrige uniquement
cette attente, sans modifier les entrées natives. Les sources et preuves
antérieures restent inchangées.

106 tests turbo réussissent et un est ignoré. make check exécute
3 836 tests, avec 172 ignorés, les deux échecs flottants et trois erreurs
rtree/networkx hors turbo déjà connus. Le test ajouté vérifie l'appariement,
la transformation des vecteurs et le refus d'un sommet déplacé.

checkMesh réécrit l'en-tête de son ensemble diagnostique nonOrthoFaces
dans 047 ; les labels sont relus et concordants. Les fichiers physiques
restent conservés. Le manifeste préparé et le reçu natif sont gardés
séparément, sans écraser leurs empreintes.

[Archive native 047–048](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-periodic-sector-2026-10-12) : 61 fichiers, 1265644 octets ; SHA-256
`df828dbbc0c19be352e928cdb2cb07fff9a4e8be5f030a830c273b6e8ab17730`.
Tous les payloads du TAR sont relus localement. Les cinq actifs GitHub
sont vérifiés par tailles et SHA-256 distants ; aucun second téléchargement
intégral distant n'est revendiqué. Les anciens calculs restent conservés.
