# Autres angles nécessaires sur les boîtes restantes

Le parcours des autres angles variables exclut **six boîtes supplémentaires**, avec témoins vérifiés indépendamment. La largeur exclue sur la restriction u=q_m passe de 3937/4096 à **3943/4096**, soit 96,2646484375 %. **153 boîtes restent non exclues**. Aucun ratio ponctuel, nouvelle subdivision, candidat, dictionnaire, natif ou solveur ; aucune admission.

## Protocole fixé avant calcul

Les 159 boîtes non exclues PR236 sont reprises exactement : 114 satisfaisaient les six contraintes sélectionnées et 45 restaient indécises. Les moments centrés PR236 et le noyau dyadique 160 bits PR233 sont importés à leurs empreintes, sans exécuter leurs modules principaux. Aucune nouvelle identité ou approximation plane.

Le registre des faces partagées retrouve les 9472 contraintes angulaires potentiellement variables. Les deux témoins déjà réencadrés sont retirés du nouveau parcours. Les **9470 autres contraintes** sont ordonnées par angle archivé décroissant, puis labels owner/neighbour croissants. C'est un ordre de contrôle de contraintes, pas une recherche de ratios. L'ordre complet est dans l'archive.

| Famille | Contraintes programmées |
|---|---:|
| axiale/axiale | 4350 |
| axiale/hex extérieur | 1536 |
| angulaire/axiale | 768 |
| hex extérieur/hex extérieur | 2816 |

Chaque boîte entière est parcourue jusqu'au premier refus certain, ou jusqu'à la fin de la liste. Les signes de D et du résidu D²/(|Δ|²|S|²)−κ sont conservés ; κ et le seuil de 70° sont inchangés. Les centres proviennent des moments, avec volumes pyramidaux signés. Une singularité d'encadrement reste indécise.

## Résultats

Le calcul principal termine les 159 boîtes en 872,600 s : **1 448 960 évaluations**. Il enregistre 1 440 051 bornes positives, 8903 indécises et six refus. Les cinq premières exclusions proviennent de la paire **2996/2998**, quatrième contrainte de l'ordre ; la sixième de **3392/3394**, trentième contrainte. Toutes sont axiales/axiales. Les six boîtes étaient auparavant indécises ; aucune des 114 boîtes satisfaisant les anciens six témoins n'est ainsi exclue.

Les 153 boîtes sans refus parcourent chacune les 9470 contraintes. Le calcul principal compte 115 boîtes où toutes ces nouvelles bornes sont positives et 38 avec au moins une borne indécise. Parmi les 115, 113 satisfaisaient déjà les six témoins précédents. **Ces comptages positifs/indécis ne sont pas tous recalculés par le lecteur indépendant** : ils restent descriptifs et ne constituent pas un certificat d'admission, même pour les seuls angles.

Sur les 2351 feuilles combinées : 2198 exclues, 153 non exclues ; largeurs exactes 3943/4096 et 153/4096. La couverture reste sans trou. Trois plages de statuts figurent dans `summary.json`. Ce ne sont ni des probabilités, ni des composantes de faisabilité physique, ni une mesure du système à deux inconnues. Aucun ratio n'est choisi.

## Ce qui est vérifié indépendamment

`verify_exclusions.py` importe le lecteur de moments Fraction 192 bits PR236 à son empreinte et reconstruit les faces par les six gabarits hex réduits. Il vérifie les cycles orientés opposés, les 9470 contraintes de l'ordre, les 159 boîtes et leur provenance, puis **chaque témoin des six exclusions** : coordonnées, centres, volumes positifs, D et résidu. Les bornes indépendantes sont incluses dans les bornes principales et leurs résidus sont strictement négatifs sur les boîtes entières. Aucun faux voisin ni mur introduit.

La lecture indépendante ne rejoue pas les autres 1 448 954 évaluations. Elle contrôle la structure des comptes et la fin de parcours des 153 boîtes, sans certifier chaque signe positif ou indécis. Cette limite est explicite dans le reçu. `verify_dependency_chain.py` ancre les six manifestes parents au commit de fusion exact PR236 et relit leurs payloads. Toutes les sources et preuves antérieures restent immuables.

Aucune assertion refusée, aucune installation. Les calculs concernent les expressions mathématiques encadrées, pas les arrondis d'une exécution OpenFOAM. Les déterminants, paires de plans, volumes et obligations géométriques complets restent ouverts. La preuve de partage, frontière, couverture orientée, non-intersection, planéité et bilan reste nécessaire avant admission native. Parois gauchies 086/091, parois physiques, couches et repos global restent distincts ; 084 demeure incomplet et n'est pas relancé. Aucun débit, puissance ou calibration validé.
