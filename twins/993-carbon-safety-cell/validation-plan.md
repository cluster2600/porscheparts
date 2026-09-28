# Plan de validation — monocoque carbone 964/993

## Conclusion actuelle

Le projet possède un **concept CAO**, un **concept de moule** et un **screening structurel F1**. Il ne possède pas encore la preuve nécessaire pour fabriquer, monter ou utiliser la cellule. Une simulation logicielle seule ne peut pas prouver qu'une structure de protection des occupants est bonne pour la route ou le circuit.

Le contrat machine-readable est dans `engineering-validation-contract.json`. Il garde explicitement fermées les autorisations de fabrication, installation, démarrage moteur, essai routier et essai circuit.

## Ce qui est déjà vérifié

- Huit architectures sont soumises aux mêmes chargements et hypothèses dans un treillis 3D linéaire.
- La variante tout CFRP `all_carbon_multicell_x10` donne 21 011,7 Nm/deg et 25 238,5 N/mm dans ce seul modèle 993 d'enveloppe.
- Les contrôles d'enveloppe du même candidat donnent 20 914,7 Nm/deg avec les voies publiées de la 964 C2 et 21 011,7 Nm/deg avec les voies de référence 993 ; les voies ne sont pas des points de suspension.
- Le cas torsionnel a été reconstruit dans CalculiX 2.21. L'écart avec le solveur Python est de `1.46e-6`, inférieur à la tolérance numérique `1e-4`.
- Les STEP cellule, modules 964/993 et outillage sont générés par build123d/OCCT ; le rapport recense 32 solides de cellule, 12 solides par jeu de modules et 7 secteurs d'outillage.
- La limite de la vérification CalculiX est volontairement étroite : elle contrôle l'implémentation du même treillis, pas la fidélité physique d'une coque composite.

## Modèles à construire

1. **F2 métrologie et interfaces.** Scanner une caisse saine 964 et une caisse saine 993, puis mesurer séparément par CMM les points de suspension, direction, sous-châssis, groupe motopropulseur, portes, vitrages, sièges et retenues. Chaque mesure conserve unité, incertitude, méthode et température.
2. **F3 coque composite.** Remplacer les barres équivalentes par des coques multicouches, solides d'âme, joints cohésifs, inserts et contacts. Étudier le maillage et les critères de ruine avec les propriétés issues des coupons.
3. **F3 explicite.** Construire sous OpenRadioss les cas toit, frontal, décalé, latéral, poteau, arrière et retournement jugés applicables. Utiliser uniquement des barrières, mannequins et critères correctement validés.
4. **F4 corrélé.** Corréler calculs et essais de coupons, détails, sous-ensembles et caisse. Réserver un cas physique non utilisé au recalage pour la validation finale.

## Cas de charge structurels minimaux

La base de masse est 1 200 kg. Avant F3, il faut fermer la répartition avant/arrière, le centre de gravité, les masses non suspendues, les pneus et les charges aérodynamiques. Les enveloppes préliminaires 3 g vertical, 1,5 g longitudinal et 1,8 g latéral servent à construire les cas, mais ne sont pas encore des facteurs d'homologation.

| Famille | Entrées à figer | Sorties et critère |
|---|---|---|
| Torsion caisse | couples aux points de suspension, conditions de bridage, masse de test | rigidité, contraintes, énergie des joints, corrélation au banc |
| Flexion verticale | masses suspendues, occupants, carburant, aero, bosses | flèches, flambement, marges stratifié et collages |
| Freinage/virage | pneus, aero, transferts, combinatoires | charges interfaces et fatigue multiaxiale |
| Siège/retenue | sièges, ancrages, ceintures, occupants | intégrité inserts, arrachement, espace de survie |
| Toit/intrusion | procédure fixée avec expert | courbe force-déplacement et espace de survie, puis essai physique |
| Modal/NVH | groupes motopropulseurs, suspension, portes/vitrages | fréquences, formes modales et séparation avec excitations |
| Fatigue route/circuit | télémétrie instrumentée représentative | dommage cumulé avec facteurs approuvés et dommages d'impact |

La procédure NHTSA TP-216a-01 peut servir de référence de pré-développement pour le toit. Elle ne remplace pas la détermination de la procédure suisse/européenne applicable et ne transforme pas un résultat numérique en conformité.

## Validation composite et fabrication

- Figer fibre, résine, tissu, âme, adhésif, inserts et barrières galvaniques.
- Produire plusieurs lots de coupons et valeurs admissibles pour température, humidité, vieillissement et fluides automobiles.
- Tester les rayons, arrêts de plis, trous, inserts, recouvrements, collages, réparations et dommages d'impact représentatifs.
- Simuler drapage, cure, exothermie, vide, pression autoclave et dilatation de l'outillage.
- Contrôler chaque premier article par métrologie et CND, avec coupons témoins du cycle.

## Autorisation route et circuit

Une homologation routière dépend du pays, de la catégorie du véhicule, de son historique et de l'étendue exacte des transformations. L'éligibilité circuit dépend en plus de l'organisateur ou du règlement technique. Les deux décisions nécessitent un dossier gelé et des avis écrits distincts. Une autorisation de track day ne vaut pas homologation routière, et l'inverse non plus.

## Logiciels libres proposés

- build123d/Open CASCADE pour les masters paramétriques et STEP ;
- Gmsh puis CalculiX ou Code_Aster pour le statique, modal et fatigue de pré-développement ;
- OpenRadioss pour l'explicite/crash ;
- ParaView pour la revue des champs et maillages ;
- OpenUSD et Omniverse pour l'assemblage, les variantes, les métadonnées de simulation et la revue visuelle ;
- PhysicsNeMo seulement après existence d'un jeu de calculs et d'essais suffisamment riche : un surrogate ne crée pas une preuve absente.

Les versions de solveur, fichiers d'entrée, maillages, propriétés, conditions aux limites et résultats doivent être immuables et liés au numéro de configuration de la pièce.
