# Partage paramétrique et couverture des fermetures

Le partage des faces et la couverture des deux fermetures planes sont établis sur l'enveloppe **fermée des 153 boîtes restantes PR239**, avec `u=q_m` fixé. Aucun ratio ponctuel, subdivision, candidat, dictionnaire, cas natif ou solveur n'est créé. Les deux boîtes aux déterminants indécis restent incluses. L'admission géométrique/native complète demeure ouverte.

Le domaine exact de v est `[18685771944522017155/18446744073709551616 ; 9345323731508729405/9223372036854775808]`. Les coordonnées restent les fonctions affines rationnelles issues des binary64 sources PR232. La spécification est écrite avant calcul dans `preflight.md`. Neuf manifestes parents, ancrés au commit main PR239 `740cdf56a8fdc2b167d942759dc9d594d1b435d9`, et tous leurs payloads sont vérifiés.

## Partage et incidences

Les 6144 cellules sont connectées par leur graphe de faces. Les 13696 faces internes apparaissent chacune dans exactement deux cellules, avec des cycles opposés. Le même label désigne la même fonction de coordonnées dans chaque occurrence : leur partage est exact sur tout le domaine, sans tolérance de raccord. La frontière de 4864 faces égale exactement celle déclarée PR229 après réduction des répétitions des gabarits dégénérés.

Les arêtes de chaque cellule et de la frontière s'annulent en sens opposés. La frontière comporte 4096 sommets, 8960 arêtes et une caractéristique d'Euler égale à zéro ; chaque lien de sommet est un cycle connexe. Ces contrôles sont combinatoires et **ne prouvent pas un plongement sans intersection en 3D**, ni l'absence de recouvrement des cellules. Les 2304 faces latérales de frontière et les 384 quads MRF sont constants en coordonnées et cycles. Aucun bilan de débit physique n'en est déduit.

## Fermetures planes

Chaque fermeture contient 1280 faces, exactement dans le plan de sa station source, pour tout v. La triangulation de preuve de chaque face est l'éventail à la moyenne arithmétique de ses sommets : **4352 triangles par fermeture, 8704 au total**. Ces points centraux sont des objets de preuve ; ils ne sont pas ajoutés au maillage.

Les polynômes d'aires et de demi-plans sont encadrés en Bernstein rationnel sur l'intervalle entier. Les **21504 bornes** sont strictement positives. Chaque face est strictement convexe, chaque triangle d'éventail a une aire positive. Les arêtes restantes après annulation forment deux boucles fixes de 256 sommets : extérieure positive et intérieure négative. Convexité stricte des deux polygones et inclusion stricte du polygone intérieur sont vérifiées contre tous les demi-plans pertinents, sans simple test ponctuel de barycentre.

La preuve autonome `proof.md` utilise l'additivité des traversées orientées d'un rayon : l'annulation des arêtes donne l'indicatrice de l'anneau, et la positivité des triangles interdit les recouvrements de leurs intérieurs. Elle établit **la couverture exacte de chaque anneau polygonal fermé et les intérieurs disjoints de ses triangles de preuve**, pour toute valeur du domaine. Cela ne s'étend pas implicitement aux faces gauchies ou aux cellules volumiques.

L'aire totale est un polynôme constant, exactement égal à l'aire extérieure moins l'aire intérieure. Les valeurs décimales ci-dessous ne remplacent pas les rationnels du reçu :

| Fermeture | Aire constante (m²) | Borne minimale de double aire triangulaire (m²) |
|---|---:|---:|
| Basse | 7,008021556433157e−5 | 4,553993726239832e−9 |
| Haute | 6,547483935072378e−5 | 4,254724464368203e−9 |

L'égalité d'aires seule n'est pas le certificat de couverture ; la chaîne orientée, les boucles emboîtées et les aires positives en sont les hypothèses essentielles.

## Lecture indépendante et limites

`verify_boundary_v2.py` reconstruit séparément toutes les faces à partir des six gabarits hex réduits. Il vérifie les polynômes par une algèbre creuse, leurs bornes par Casteljau rationnel, les incidences, les cycles, les boucles et toutes les hypothèses de couverture. Les coefficients et bornes concordent exactement. Les algèbres épinglées PR235 sont réutilisées sans refaire leurs dérivations. Calcul principal : 6,233 s ; lecture indépendante : 7,367 s, sans valeur de benchmark CFD.

Le lecteur v1 et son assertion sur deux représentations du polynôme nul sont conservés ; la correction limitée de v2 est vérifiée par `reader-fix-readback.json`. Voir `validation.md` pour les tests, les cinq problèmes locaux hors turbo inchangés et les journaux.

Les modèles complets et les journaux sont dans l'[archive publiée](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-parametric-boundary-2026-10-13). Aucune preuve de non-intersection volumique, de planéité globale, de bilan de rotation global, d'admission native ou de repos n'est ajoutée. Les 113 boîtes satisfaisant les prédicats variables nécessaires restent non admises. Trois intervalles synthétiques ne qualifient pas toute la couronne ni les surfaces physiques. 084 reste incomplet et n'est pas relancé. Aucun débit, puissance ou calibration validé ; suite dans `next-scope.md`.
