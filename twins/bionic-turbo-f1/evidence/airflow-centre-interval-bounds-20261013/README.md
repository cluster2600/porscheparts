# Moments centrés : resserrement des deux contraintes angulaires

Les identités des moments natifs sont vérifiées puis publiées avant usage. Sur les **447 mêmes boîtes** indécises de PR235, le regroupement centré des moments permet **288 exclusions supplémentaires**. **114 boîtes passent les six seules contraintes nécessaires sélectionnées** ; **45 restent indécises**. Aucune solution géométrique admissible, aucun ratio ponctuel retenu, candidat, dictionnaire, cas natif ou solveur.

## Périmètre et méthode

La restriction reste u=q_m source exact ; seule v varie par intervalles fermés déjà archivés. La profondeur PR233 est conservée, sans nouvelle subdivision. Le domaine physique de paramètres reste ouvert. Les deux angles sont ceux des faces 837/839 et 3455/3457 ; les déterminants 955, 5019, 2036 et 6027 sont hérités exactement de PR235. Toutes les sources PR229/231/232/233/235 sont relues par empreintes avant calcul.

Pour une face, c est la moyenne des sommets, w_i la norme du produit vectoriel du triangle d'éventail et W leur somme. Pour une cellule, s est la moyenne des centres de faces, V_i les volumes signés des pyramides et V leur somme. Les expressions deviennent :

    C_f = c + Σ w_i(p_i+p_{i+1}−2c)/(3W)
    C   = s + 3Σ V_i(C_fi−s)/(4V)

Ces expressions sont algébriquement identiques aux expressions natives non dégénérées. c et s restent des fonctions de v, jamais des centres ajustés ou gelés. Aucun remplacement par des faces planes. Les V_i restent signés. Les noyaux d'intervalles 160/192 bits sont ceux de PR233, importés à leurs empreintes sans lancer leurs modules principaux. `derivation.md` précise la correspondance native et ses limites.

Cinq actifs préalables ont été publiés avec tailles/digests avant le réencadrement : spécification, dérivation, code des moments, preuve et reçu. Quatre identités de coefficients, deux références à poids signés, cube/pyramide à trois échelles et quadrilatère gauchi symétrique à trois échelles vérifient les regroupements. Ces références ne recherchent aucune dimension de couronne.

## Résultats des bornes

| Statut combiné sur les feuilles PR233 | Feuilles | Largeur relative exacte |
|---|---:|---:|
| Exclues par au moins une contrainte nécessaire | 2 192 | 3 937/4 096 |
| Six contraintes sélectionnées satisfaites sur toute la boîte | 114 | 57/2 048 |
| Indécises | 45 | 45/4 096 |

La largeur exclue passe de **89,0869140625 % à 96,1181640625 %** sur cette restriction seulement. La largeur satisfaisant les six contraintes vaut 2,783203125 %, celle indécise 1,0986328125 %. Ni probabilités, ni fractions du système à deux inconnues, ni régions CFD admises.

Les 894 bornes brutes de D et du résidu angulaire sont toutes incluses dans les anciennes. Le rapport de largeur nouveau/ancien du résidu va de 0,07027694 à 0,07890612. Les intersections sont publiées séparément ; aucune dégradation brute n'est masquée. Parmi les 288 nouvelles exclusions, le premier témoin est l'angle 837/839 pour 229 feuilles, puis 3455/3457 pour 59. Plusieurs contraintes peuvent refuser une même boîte.

Les statuts combinés forment cinq plages : exclusion, indécision (43 feuilles), six contraintes positives (114), indécision (2), exclusion. Les bornes rationnelles complètes figurent dans `comparison.json`. Ce ne sont pas des composantes de faisabilité physique ; aucune monotonie prouvée. Les fermetures et interfaces ne sont pas retirées du système.

## Relecture et limites

`verify_centres_v2.py` reconstruit les faces depuis les six gabarits hex réduits, puis centres/volumes et angles avec Fraction à 192 bits. Il n'importe pas le nouvel évaluateur. Ses 894 bornes sont incluses dans celles à 160 bits ; les classifications et les 1 788 encadrements de volume positifs (quatre cellules par boîte) concordent. Neuf références géométriques indépendantes sont vérifiées. Les quatre déterminants hérités sont comparés exactement au certificat PR235 déjà relu ; ils ne sont pas recalculés par ce lecteur.

La première version du lecteur est conservée : ses calculs passent, mais le champ d'empreinte du noyau contenait celui du dernier manifeste à cause d'une variable locale réutilisée. La v2 corrige seulement ce chemin de métadonnée et le nom de sortie. `verify_provenance.py` confirme des résultats scientifiques identiques ; aucune assertion scientifique refusée, aucun natif rejoué.

Les certificats portent sur les expressions mathématiques avec erreur d'encadrement contrôlée, pas sur les arrondis d'une exécution OpenFOAM ou une admission native. Les branches de dégénérescence ROOTVSMALL/VSMALL ne sont pas qualifiées par cette preuve. Les autres angles, déterminants, plans, volumes, partage, couverture orientée, non-intersection, planéité et bilan restent requis. Les autres critères ne sont pas déduits de ces six témoins. Parois gauchies 086/091, surfaces physiques, couches et repos global restent distincts. Le cas 084 reste incomplet et n'est pas relancé. Aucun débit, puissance ou calibration validé.
