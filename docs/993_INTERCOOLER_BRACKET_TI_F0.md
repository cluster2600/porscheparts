# Support d'intercooler 993 Turbo/GT2 — concept titane F0

Ce quatrième pilote est le premier cas titane. Le catalogue PorscheFanatics et
la planche PET `107-45` situent les supports `993 110 110 50` et
`993 110 110 52` dans le circuit de suralimentation. La fiche FVD du support
renforcé `FVD11011050` publie une enveloppe de **255 × 80 × 23 mm**, une masse de
**0,2 kg** et l'application 993 Turbo/GT2. Elle ne publie ni matière, ni
entraxe, ni interfaces, ni tolérances, ni charges.

Le modèle n'est donc pas une copie. Il conserve l'enveloppe publiée et propose
une topologie indépendante : cadre courbe ouvert à deux rails, deux yeux
d'extrémité et un plot central intégré. Les deux évidements restent ouverts
pour éviter toute poudre prisonnière. Tous les perçages et chemins de charge
sont des paramètres F0 à remplacer par des mesures.

## Pourquoi étudier le LPBF titane

Le cas présente un intérêt AM réel à faible volume : chemin de charge courbe,
bossages et support central consolidés, évidements ouverts et possibilité de
mettre la matière dans les directions utiles. Mais le procédé n'est pas encore
le choix gagnant. Une comparaison chiffrée avec usinage 5 axes, tôle assemblée
ou forge doit inclure coût, matière perdue, finition, inspection et fatigue.

Le Ti-6Al-4V est seulement candidat. La densité, le module et la dilatation de
criblage viennent d'une fiche TIMET corroyée ; sa limite minimale de tôle n'est
pas une valeur admissible LPBF. EOS confirme que la performance imprimée dépend
de la machine, des paramètres, de l'orientation et du traitement thermique.

## Criblage mathématique exécuté

Sous un cas synthétique de charge centrale `400 N`, portée `220 mm` et
`+120 K` :

- `A = n b t` et `I = n b t³ / 12` pour deux rails effectifs ;
- `Mmax = F L / 4`, `sigma = M c / I` et `tau_max = 1,5 F / A` ;
- contrainte équivalente `sqrt(sigma² + 3 tau²)` ;
- flèche `F L³ / (48 E I)` ;
- matage moyen `R / (d t)`, masse `rho V` et dilatation `alpha L delta_T` ;
- aire polygonale par formule du lacet, volume analytique, BREP OCCT unique et
  relecture du STEP.

Le modèle donne `41 869,51 mm³`, soit `185,06 g` avec la densité Ti64 de
criblage, `229,42 MPa` équivalent, `2,80 mm` de flèche et `0,238 mm` de
dilatation libre. Ce sont des résultats de régression du concept, pas une
validation du support ni une comparaison de résistance avec le produit FVD.

## Gates avant prototype

1. Numériser une pièce identifiée et mesurer tous les datums, entraxes,
   alésages, jeux et surfaces d'appui.
2. Mesurer masse d'intercooler, efforts des conduits, précharges, température et
   spectre vibratoire sur véhicule.
3. Réaliser FEA contact/non-linéaire, modal, thermique et fatigue avec carte
   matériau qualifiée pour la machine et l'orientation.
4. Geler orientation, supports, traitement thermique, décision HIP,
   surépaisseurs et isolation galvanique aluminium/titane/acier.
5. Contrôler CT et dimensionnellement, puis tester preuve statique, vibration,
   cycles thermiques et étanchéité sur banc avant tout montage.

PhysicsNeMo ne peut devenir utile qu'après production de cas CAE ou d'essais
corrélés ; sans données, un surrogate ne prouverait rien. Le transfert
SimReady est différé jusqu'à la définition des interfaces et d'une carte
matériau qualifiée.
