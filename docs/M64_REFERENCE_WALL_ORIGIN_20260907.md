# Origine des faibles épaisseurs — référence scan 935, 7 septembre 2026

## Résultat obtenu

L'audit natif OCCT compare **les mêmes rayons** sur la 4V F53 et sur
l'enveloppe F43 avant les découpes internes. Il ne compare pas deux
échantillonnages différents. Les entrées sont contrôlées par SHA-256 ; chaque
intervalle F53 est d'abord reproduit avec une tolérance de `1e-5` unité du
scan. L'héritage exige ensuite que les deux extrémités correspondent à celles
de l'enveloppe à `1e-4` près et que le segment soit classé dans le solide.

| Origine des sondes F54 | Nombre |
|---|---:|
| Trajet déjà présent dans l'enveloppe F43 | 28 |
| Au moins une extrémité créée par une découpe du candidat | 9 |
| Non résolu dans l'audit précédent ; toujours non résolu | 5 |

Les **cinq trajets faibles entre faces non adjacentes**, répartis sur quatre
paires de B-Splines, sont tous hérités de l'enveloppe. Ils se situent dans
trois bandes de transition entre profils `core` et `fin`, et non simplement
entre les deux plans nominaux d'une ailette. Modifier les diamètres des
conduits ne corrigerait donc pas ces quatre zones.

Cela ne démontre pas que le scan brut a ces défauts : F43 est déjà une
reconstruction par sections du stock scan-dérivé, avec réparations antérieures.
Le résultat identifie l'étape où le défaut existe, pas sa cause physique
sur une culasse Porsche originale.

## Localisation et essai de correction

`localize_wall_repair_patches.py` produit un dossier privé pour les quatre
paires : indices des faces liés au STEP exact, coordonnées des intersections,
aires, boîtes, voisinage et proposition d'opération CAO. Aucun indice n'est
réutilisé après modification sans refaire la correspondance.

Un deuxième programme, `trial_local_transition_fillet.py`, examine la paire
la plus faible et les deux arêtes qui la relient à son voisin commun. Le
principe est d'ajouter un congé **uniquement sur un raccord concave**, ce qui
peut épaissir localement côté passage d'air, sans offset global. L'essai est
borné à deux CPU, 4 Gio d'espace d'adressage et 300 secondes.

Sur 36 directions autour de chaque arête, à deux rayons de sondage, les
fractions intérieures sont respectivement 0,472/0,472 et 0,417/0,389. Aucune
arête ne satisfait le filtre concave. **L'opération de congé est donc refusée
avant construction** : pas de STEP corrigé et aucun épaississement revendiqué.
Ce test discret est un filtre de prudence, pas une preuve analytique de la
concavité complète des arêtes.

La prochaine opération proposée est une reconstruction locale de la bande
de transition : identifier les courbes d'ancrage du scan à conserver, les
raccords côté passage d'air ajustables, puis construire le patch contraint
avec `BRepFill_Filling`, remplacer/coudre les faces et refaire les contrôles
d'intégrité, déviation, épaisseur et section de passage. Cette proposition
n'est pas encore un opérateur vérifié. Les courbes autorisées à bouger ne
sont pas encore identifiées ; une modification aveugle n'est pas effectuée.

Conserver exactement les deux surfaces limitantes conserve aussi la longueur
du trajet mesuré. Ajouter de la matière déjà à l'intérieur du solide ne peut
pas augmenter cette longueur. Une correction devra donc déplacer **une
frontière locale**, en conserver le contour maître global et mesurer ce
déplacement explicitement. Son effet sur le refroidissement restera à calculer.

## Image et traçabilité

`render_wall_origin.py` produit une vue de la tessellation du STEP F53 et une
coupe superposant les deux géométries. Les 160 856 triangles du candidat sont
affichés sans décimation. La coupe est tessellée avec une déflexion de 0,15
unité du scan ; le segment rouge de **0,753** vient de l'intersection OCCT
exacte, pas de la figure. Ce n'est ni un rendu Omniverse, ni un champ thermique.

Artefacts privés sur Kali, sous `/tmp/917-f50/out/` :

- `m64-wall-origin-20260907.json` : audit ponctuel complet.
- `m64-wall-repair-patches-20260907.json` : paquet d'intervention local.
- `m64-local-transition-fillet-20260907/report.json` : rejet du filtre concave.
- `m64-wall-origin-render-20260907/935-reference-wall-origin-diagnostic.png` : image.

Empreintes :

- STEP F53 : `700baea66bc72cdb6aee529e21b167270ebde11db94b06f8e1e55ee08bdd9bf2`.
- Enveloppe F43 : `00c26d32820b23b3589beb7b26d34bc3eb176a89000b9374ffdbe334278b41ef`.
- Audit d'origine : `b89fece8c3a5ee49d8ae6641054dc3cb17d7fddb47da1a99096b588c3c7bbec9`.
- Paquet local : `64f7efd3dc581644dfafec615617ec06963267871f4d5c925504418773ee5e57`.
- Image : `d63d4f86923d3b27449c421dd2f3d56ec86801e51acd87195fb0466605518fd3`.

Cinq tests unitaires de classification passent. Ils testent la décision
d'héritage, les découpes, les cas ambigus et les intervalles invalides ; ils
ne prouvent aucune performance mécanique. Les programmes se compilent en
Python et l'audit/visualisation ont réellement tourné avec OCCT sur Kali.
Une seconde exécution de l'audit retrouve les mêmes 28/9/5 classifications
et les cinq trajets non adjacents hérités. Les classificateurs OCCT sont
réutilisés entre sondes pour éviter de recharger le solide à chaque test.

## Périmètre inchangé

Cette géométrie est une **référence de recherche 935 scan-dérivée**, pas une
culasse M64 aux interfaces validées. Échelle absolue non certifiée, contrôle
d'épaisseur non exhaustif, thermique/résistance et LPBF complets non validés.
Aucune fabrication, installation ou mise en route n'est autorisée. Aucun
scan, STEP, STL ni coordonnées privées n'est ajouté au dépôt.
