# Périmètre et provenance de la vérification

Le point de départ est le commit main `522b972cc9bf6fd3d3e130303e795790b947ffe7` (PR238). Les huit manifestes de dépendances sont ancrés par les métadonnées Git de ce commit. Le lecteur vérifie leurs 196 entrées avant application. Les mêmes 153 boîtes proviennent des lignes non exclues de PR237 ; leur identité avec `boxes.json` PR238 est vérifiée. Chaque boîte est un intervalle entier fermé d'encadrement, dans la restriction `u=q_m` ; aucun ratio ponctuel n'est choisi.

`verify_angles.py` n'importe ni `check_angles.py` PR237 ni le nouvel évaluateur primaire des moments PR236. Il importe le lecteur indépendant `verify_centres_v2.py` et substitue à sa classe Fraction la représentation entière `dyadic192.py` PR238. La preuve et les 624 comparaisons arithmétiques/neuf références géométriques de PR238 restent des dépendances immuables ; elles ne sont pas rejouées ou présentées comme de nouvelles validations. Le produit après réciproque arrondie, les racines et les bornes extérieures gardent exactement leur suite d'opérations à 192 bits fractionnaires.

Les six gabarits hex réduits reconstruisent séparément toutes les faces. La suppression des répétitions adjacentes ne retire que les faces effondrées de moins de trois sommets. Deux occurrences internes ont des cycles opposés. La liste des points dépendant de v détermine les cellules et les 9472 angles potentiellement variables. Après retrait des deux témoins anciens, les 9470 tuples et l'ordre angle archivé décroissant puis labels sont comparés à la liste PR237. Aucun tri sur une géométrie nouvelle.

Pour chaque cellule utilisée et chaque boîte : coordonnées affines rationnelles issues de `system.json`, translation par le premier sommet source constant, centres de faces d'éventail et moments pyramidaux signés, puis restitution de la translation. Le volume inférieur doit être strictement positif. Chaque angle utilise l'aire orientée de sa face côté owner et les deux centres volumiques reconstruits. Aucun centre libre, aucune normale retournée acceptée par la seule mise au carré. Les mêmes bornes rationnelles de κ sont réutilisées.

## Format du certificat

`angular-bounds.jsonl.gz` contient une ligne JSON par couple boîte/contrainte, dans l'ordre des boîtes puis de `order.json` :

`[parent_leaf, rank, D_lo, D_hi, Q_lo, Q_hi, R_lo, R_hi]`

Les six derniers entiers représentent leurs valeurs divisées par `2^192`. `D=Δ·S`, `Q=|Δ|²|S|²` et `R=D²/Q−κ`. Une borne positive exige `D_lo>0`, `Q_lo>0`, `R_lo>=0`. Un refus exige `D_hi<=0` ou `R_hi<0`. Les autres résultats restent indécis. L'inventaire contrôle les 9470 rangs de chaque boîte, sans trou, doublon ni arrêt précoce.

Le certificat PR237 ne contient pas les anciennes bornes individuelles positives ou indécises. Cette phase ne peut donc comparer leur inclusion numérique ni identifier a posteriori chaque ancienne face positive d'une boîte mixte. Elle fournit un calcul indépendant complet, compare les comptes par boîte et confirme les boîtes dont toutes les contraintes étaient déclarées positives. `read_certificate.py` vérifie après coup l'inventaire et tous les signes des bornes enregistrées ; ce n'est pas une seconde reconstruction géométrique indépendante. Celle-ci est précisément le rôle de `verify_angles.py` par rapport au calcul primaire PR237.

## Limites

Les deux angles anciens sont hérités sur leurs feuilles exactes depuis les bornes combinées PR236 et leur lecture indépendante achevée. Les déterminants, plans et volumes PR238 sont repris par leurs résultats épinglés, sans relancer leurs parcours. La réunion concerne seulement les prédicats variables nécessaires ; les contraintes constantes restent dans leur périmètre propre. Elle ne certifie aucune géométrie nouvelle, aucun ratio, ni une absence d'intersections. Les branches natives ROOTVSMALL/VSMALL et les erreurs d'arrondi OpenFOAM ne sont pas qualifiées par ces expressions mathématiques. Admission native, repos global, CFD et calibration restent distincts.
