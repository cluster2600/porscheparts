# Porsche 917 — dossier LPBF et gamme de fabrication F37

## Décision

La phase F37 dispose maintenant d'une **orientation LPBF candidate**, d'une
stratégie de supports, d'une gamme de traitement/usinage et d'un plan CT/CND.
Elle n'est **pas libérée pour impression métal**. Le résultat calculé sert à
fermer la conception et à préparer un échange traçable avec un fournisseur
LPBF; il ne remplace pas la qualification machine, les coupons, le contrôle de
la poudre, le CT ni les essais physiques.

Les bossages d'appui ajoutés à F37 augmentent le volume net. La masse candidate
est donc recalculée sur le STL F37 exact et comparée explicitement à la cible
F36 de 2,83 kg. Cette cible comparative n'est pas un critère de libération,
mais son dépassement ne doit pas être masqué.

Les trois échecs géométriques/comparatifs mesurés sont bloquants pour la route
actuelle :

- 1,259 % des voxels au-dessus du plateau sont sans appui dans l'audit grossier,
  pour une cible de criblage inférieure à 0,5 %;
- l'épaisseur échantillonnée p01 vaut 0,75 mm, sous la cible de 1,5 mm.
- 23 voxels fermés, soit 0,184 cm³ au pas 2 mm, sont classés comme poudre
  potentiellement piégée.

La masse conditionnelle vaut 2,842938 kg à 2 670 kg/m³, soit 12,94 g au-dessus
de la cible comparative F36 de 2,83 kg.

La CAO F37 ne constitue pas encore un unique B-Rep de culasse. Elle définit des
interfaces fonctionnelles analytiques autour du maillage F36-013 :
porte-culbuteurs, axes, enveloppes de culbuteurs, noyau de galeries, volumes de
surépaisseur et outils de finition. L'enveloppe organique à ailettes reste la
géométrie issue du scan.

## Entrées traçables

Le rapport est généré par
`twins/reference-917-engine/source/compile_f37_lpbf_manufacturing_plan.py`
à partir de cinq entrées :

1. `work/917-scan-conforming-f37/lpbf-exact/lpbf-printability-report.json`;
2. `work/917-scan-conforming-f37/head-mesh-proof/f37-printable-head-mesh-report.json`;
3. `work/917-scan-conforming-f36/lpbf-locked-plate-p3/report.json`;
4. `twins/reference-917-engine/f37-manufacturing-definition.json`;
5. `work/917-scan-conforming-f37/cad/f37-cad-report.json`.

Le script vérifie que l'écran LPBF référence le SHA du maillage F37 exact et
que ce rapport de maillage référence le contrat et la CAO courants avant de
produire :

- `work/917-scan-conforming-f37/lpbf/f37-lpbf-manufacturing-report.json`;
- `work/917-scan-conforming-f37/lpbf/917-head-f37-lpbf-manufacturing.png`.

Commande reproductible :

```bash
make 917-manufacturing-f37-lpbf-screen

python3 twins/reference-917-engine/source/compile_f37_lpbf_manufacturing_plan.py \
  --printability work/917-scan-conforming-f37/lpbf-exact/lpbf-printability-report.json \
  --f37-head-mesh-report work/917-scan-conforming-f37/head-mesh-proof/f37-printable-head-mesh-report.json \
  --locked-plate work/917-scan-conforming-f36/lpbf-locked-plate-p3/report.json \
  --f37-contract twins/reference-917-engine/f37-manufacturing-definition.json \
  --f37-cad-report work/917-scan-conforming-f37/cad/f37-cad-report.json \
  --output work/917-scan-conforming-f37/lpbf
```

Le calcul de plaque bloquée reste explicitement un **proxy mécanique F36** :
il n'applique ni activation de couches, ni contact de supports, ni histoire
thermique au maillage F37 exact. Il ne constitue donc pas une simulation
thermomécanique de fabrication F37.

Le compilateur refuse le rapport si le SHA-256 du STL analysé n'est pas celui
du maillage F37, si le contrat ou la CAO ont changé, si l'état d'échelle
diverge, si l'orientation retenue n'est pas le minimum admissible enregistré,
ou si une entrée porte déjà une autorisation d'impression/démarrage. Il refuse
également de requalifier le calcul plaque bloquée : celui-ci doit rester marqué
`F36` et `not_calibrated_lpbf`.

Le contrôle de non-régression complet, y compris deux solides analytiques
(cavité fermée détectée et trou débouchant non classé comme poudre piégée),
s'exécute dans l'image x86 épinglée :

```bash
make 917-manufacturing-f37-lpbf-audit-check
```

## Méthode voxel et limites mathématiques

À un pas isotrope de 2 mm, le maillage F37 est voxelisé sur sa **surface** sans
appel à `fill(holes)`. Le complément de cette surface est séparé en composantes
6-connexes. Les composantes touchant les six frontières de la grille sont
classées extérieures. Pour chaque autre composante, trois points déterministes
sont classés par nombre d'enroulement signé. La somme des angles solides est
calculée par blocs de 32 768 triangles, sans R-tree : la mémoire est ainsi
bornée par la taille du bloc et ne croît pas comme le produit faces × requêtes.
Une classe contradictoire ou un nombre d'enroulement ambigu fait échouer le
calcul. Une composante dans la matière complète le masque matière, tandis
qu'une composante hors matière compte comme volume fermé susceptible de retenir
la poudre. Le volume rapporté vérifie `V_fermé = N_fermé × p³`.

Le contrôle de support parcourt ensuite l'axe de construction. Un voxel matière
de la couche `k` est considéré soutenu si un voxel existe dans le voisinage
3 × 3 de la couche `k-1`, ce qui représente un cône discret à 45° lorsque les
pas horizontal et vertical sont égaux. La métrique est donc
`f_sans_appui = N_sans_appui / N_matière, couches > plateau`.

Cette discrétisation peut manquer un canal ou un étranglement inférieur à
2 mm, et elle ne modélise ni coulabilité/cohésion de la poudre, ni rugosité, ni
orientation des grains, ni vibration. Zéro voxel fermé reste un **criblage
grossier**, jamais une preuve de dépoudrage.

L'épaisseur est contrôlée sur 4 000 points de surface déterministes. Chaque
rayon part dans la direction opposée à la normale et cherche la première
intersection triangle exacte. Un index uniforme associe les boîtes englobantes
des triangles à des cellules de 4 mm; un parcours DDA visite ensuite uniquement
les cellules traversées. Le nombre de références de l'index est plafonné à
12 000 000 et au moins 95 % des rayons doivent se résoudre, faute de quoi le
calcul s'arrête. Cette méthode supprime le R-tree non borné qui avait dépassé
la mémoire de la machine x86, mais l'épaisseur reste **échantillonnée** : elle
ne remplace pas une carte exhaustive sur le B-Rep ni le contrôle CT.

## Orientation et enveloppe machine

Le criblage compare 34 orientations à l'aide d'un score associant le volume de
colonnes de support projeté, l'aire projetée et le respect de l'enveloppe
250 × 250 × 325 mm. Le meilleur score calculé est `scan_y_down`.

| Grandeur | Résultat conditionnel |
|---|---:|
| Enveloppe orientée | 125,25 × 96,75 × 206,25 mm |
| Nombre de couches à 50 µm | 4 125 |
| Aire de surplomb descendant | 112,85 cm² |
| Aire de support projetée | 110,12 cm² |
| Volume de colonnes de support, proxy | 759,95 cm³ |
| Masse nue à 2,67 g/cm³ | 2,842938 kg |
| Temps d'exposition à 60 cm³/h | 17,75 h |
| Volume fermé au voxel de 2 mm | 0,184 cm³, **échec** |

Les dimensions restent conditionnelles à l'hypothèse « une unité OBJ = un
millimètre ». Le temps ne comprend ni montée en température, ni recoating,
changements de filtre, pauses, refroidissement, contrôles ou aléas. Le volume de
colonnes est un proxy volontairement conservateur, pas un support réellement
tranché.

Dans `scan_y_down`, l'axe +y du scan devient l'axe de construction et le flanc
admission est orienté vers le plateau. Cette orientation réduit le proxy de
support parmi les 34 cas examinés. Elle doit être recalculée sur le B-Rep final
avec le vrai moteur de tranchage du fournisseur.

## Supports à créer sur la CAO finale

Le plan de support ne peut être figé avant l'union de la culasse en un B-Rep et
le choix d'une machine/paramétrie qualifiée. La stratégie imposée est :

- ajouter des plots sacrificiels sur des zones non fonctionnelles du flanc
  admission; ces plots deviennent les références de séparation du plateau;
- utiliser des supports massifs segmentés sous les masses principales et des
  supports légers, retirables par outil, sous les racines d'ailettes;
- interdire le contact des supports avec le deck fini, les logements de siège,
  les alésages de guide, les surfaces de joint et les galeries d'huile;
- documenter pour chaque support l'accès de coupe, l'outil et la trajectoire de
  retrait;
- contrôler couche par couche les îlots thermiques, la collision recoater et
  le transfert de chaleur au plateau;
- démontrer après tranchage moins de 0,5 % de matière sans appui avec la métrique
  F37 ou une métrique fournisseur plus sévère.

La surépaisseur et le plot de support ne doivent jamais être confondus : la
première fournit de la matière à usiner, le second fournit un chemin thermique
et mécanique temporaire.

## Surépaisseurs fonctionnelles F37

Ces valeurs sont des **hypothèses de départ** conditionnelles à l'échelle, pas
des tolérances libérées.

| Surface | Surépaisseur F37 |
|---|---:|
| Deck de combustion, axial | 1,00 mm |
| Registre cylindre, radial | 0,50 mm |
| Logement de siège, radial | 0,30 mm |
| Alésage de guide, radial | 0,20 mm |
| Passage de goujon, radial | 0,30 mm |
| Appui porte-culbuteurs, axial | 0,80 mm |
| Alésage d'axe de culbuteur, radial | 0,30 mm |

La validation requiert un plan de datums A/B/C, un plan de reprise limité si
possible à trois montages, et un calcul de chaîne de cotes comprenant retrait
LPBF,
déformation après séparation, traitement thermique, installation des sièges et
guides et serrage sur cylindre.

## Poudre et galeries d'huile

Le noyau OCCT F37 forme un solide connecté et ouvert par définition, avec des
diamètres candidats de 6 mm pour l'alimentation et le collecteur, 5 mm dans le
porte-culbuteurs, 3 mm pour les quatre branches de dosage et 8 mm pour les
retours. Cela prouve la continuité topologique du noyau seul, pas la
dépoudrabilité de la culasse.

La gamme impose :

1. conserver chaque passage droit et accessible depuis une extrémité de
   nettoyage;
2. ne pas accepter les branches de 3 mm en diamètre final brut d'impression;
3. imprimer des pilotes et percer/aléser ensuite les quatre branches à
   3,00 ± 0,05 mm;
4. dépoudrer par retournements indexés, vibration et gaz sec filtré jusqu'à
   stabilisation de la masse;
5. contrôler les galeries par CT, puis par endoscope lorsque la ligne de vue le
   permet;
6. rincer en circuit fermé, filtrer l'effluent et mesurer la propreté
   particulaire;
7. poser les bouchons uniquement après mesure de débit et épreuve de pression.

La preuve finale doit comprendre une pièce témoin sectionnée ou un coupon de
galerie représentatif. Un volume fermé nul à 2 mm de voxel ne détecte pas les
zones de poudre agglomérée, les rugosités ou les étranglements locaux.

## Traitement thermique

La matière candidate est `Constellium_Aheadd_HT1_plus_HT2_LPBF`. Aucune recette
temps/température n'est inscrite ici sans fiche fournisseur liée à un couple
machine-paramètres-poudre.

Ordre de principe :

1. traitement de détente qualifié alors que la pièce est encore attachée au
   plateau;
2. dépoudrage contrôlé et séparation fil/usinage;
3. traitement final HT2 qualifié;
4. décision HIP seulement après étude porosité-fatigue et validation sur
   coupons; le HIP n'est ni supposé obligatoire ni supposé suffisant;
5. CT/FPI intermédiaire avant usinage des surfaces critiques.

Les coupons du même plateau doivent fournir densité, métallographie, traction
ambiante et à chaud, conductivité thermique à chaud et résultats de fatigue
représentatifs du deck. Une carte générique de matériau n'est pas une carte de
la construction réelle.

## Lecture du proxy F36 « plaque bloquée »

Le modèle CalculiX à maille hexaédrique de 3 mm contient 50 874 éléments et
61 670 nœuds. Il applique un refroidissement uniforme de 280 °C à 20 °C et
bloque les nœuds de plateau. Résultats :

| Indicateur | Valeur |
|---|---:|
| von Mises p95 | 165,57 MPa |
| von Mises p99 | 473,94 MPa |
| von Mises maximum | 1 634,42 MPa |
| déplacement maximum | 1,327 mm |

Ce calcul emploie l'enveloppe parent F36, et non le maillage final F37. Il est
uniquement un **majorant qualitatif de risque de bridage**. Les
contraintes dépassant la limite élastique ne sont pas physiques dans un modèle
linéaire. Le modèle ne contient pas :

- activation couche par couche et historique thermique laser/recoat;
- plasticité, relaxation, fluage et transformation de microstructure;
- anisotropie ou retrait mesurés sur coupons;
- géométrie/contact des supports et comportement du plateau;
- découpe du plateau, enlèvement séquentiel des supports ou usinage.

Le retrait libre d'ordre de grandeur est calculé par
`|ΔLᵢ| = α × |ΔT| × Lᵢ` et vaut 0,81 / 0,62 / 1,33 mm sur l'enveloppe candidate.
Une simulation procédé exploitable devra être calibrée par coupons de pont,
paroi et porte-à-faux puis vérifier le déplacement après chaque étape de
séparation.

## Gamme de fabrication et contrôles

La route proposée est volontairement séquentielle et fail-closed :

1. **Gel conception** : échelle, interfaces 917, B-Rep unique, datums A/B/C et
   chaîne de cotes signés;
2. **Qualification matière/procédé** : lot poudre, machine, paramètres,
   orientation, traitements et coupons qualifiés;
3. **Slicing** : supports réels, recoater, trajectoires laser, dose thermique et
   voies de dépoudrage revus;
4. **Construction** : journaux machine, atmosphère, oxygène, images couche et
   coupons liés au numéro de série;
5. **Détente sur plaque puis dépoudrage**;
6. **Séparation et retrait des supports** sans entaille des ailettes;
7. **Traitement final** suivant la gamme qualifiée;
8. **CT volumique et ressuage fluorescent intermédiaires**;
9. **Usinage fonctionnel** depuis les datums libérés;
10. **Perçage/alésage/lavage des galeries**, débit et pression;
11. **Contrôle final** : CMM, rugosité, planitude, CT ciblé, FPI, étanchéité et
    traçabilité;
12. **Essais physiques** : banc de flux, cyclage thermique instrumenté puis banc
    moteur progressif après revue professionnelle.

## Portes bloquantes avant impression

Les deux constats positifs actuels sont limités : enveloppe compatible sous
hypothèse d'échelle et maillage F37 fermé d'un seul tenant. Le criblage détecte
au contraire 0,184 cm³ de volume fermé au voxel de 2 mm. Toutes les portes
suivantes restent rouges :

- échelle absolue et interfaces Porsche 917;
- B-Rep unique de la culasse F37;
- renforcement des zones sous 1,5 mm et nouveau contrôle d'épaisseur;
- supports réels tranchés et audit couche par couche;
- paramètres machine/poudre et traitements qualifiés;
- carte matériau sur coupons à chaud;
- simulation procédé calibrée;
- datums, chaîne de cotes et reprises d'usinage;
- démonstration physique de dépoudrage;
- critères d'acceptation CT/FPI/dimensionnel/pression;
- revue d'un ingénieur fabrication et d'un fournisseur LPBF qualifié.

Tant que ces preuves ne sont pas liées au rapport, `metal_print_authorized` et
`engine_start_authorized` doivent rester à `false`.
