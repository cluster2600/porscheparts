# M64 — maillage du domaine à partition unifiée

## Résultat — volume obtenu, qualité OpenFOAM toujours refusée

Le domaine gazeux `fab1338a…` dispose d'un **nouveau paquet natif avec
86 faces, 191 arêtes, 118 sommets, une coque et un solide**. Le transfert
des rôles, les exports de faces, l'inventaire des guides et la quadrature
ont été exécutés. **Le nouveau maillage Delaunay contient 401 961
tétraèdres et 186 370 triangles de frontière**, obtenus en 36,113 s.
Ses onze gardes d'intégrité et les enveloppes radiales des guides avant
et après la 3D passent. **OpenFOAM rejette encore cinq familles de qualité**,
contre six auparavant ; le nombre de cellules à faible déterminant
**augmente de 4 579 à 5 442**. Un nouveau contrôle des huit courbes natives
couvre désormais l'interface entière ; le refus historique des quatre
seules chaînes C0 reste consigné, sans être requalifié en succès.
L'essai de subdivision centrale exécuté ensuite diminue les faibles
déterminants, mais dégrade d'autres indicateurs : **il n'est pas adopté**.

Cette étape ne valide ni CFD, ni thermique, ni résistance, ni procédé LPBF.
L'impression, le montage M64 et le fonctionnement à 700 PS biturbo ne sont
pas autorisés ou démontrés. Les données géométriques détaillées restent privées.

## Du candidat contrôlé au paquet de calcul

La [correction native et sa revue indépendante](M64_LOCALISATION_ET_HXT_20260908.md)
expliquent l'unification des anciennes faces 37, 38 et 40 en une seule
face de conduit. Les interfaces de siège, les tronçons C0 et les passages
annulaires n'ont pas été supprimés pour faciliter le calcul.

La revue `7bd9c92d…` compare le candidat au **témoin de sérialisation OCCT**
`cf81801a…`, pas à une identité brute de tous les descripteurs du scan.
Cette distinction reste conservée dans le nouveau manifeste `58b8be5a…`.
La correspondance comprend 85 faces un-à-un et le groupe trois-vers-un ;
ce n'est donc pas une bijection globale entre les anciens et nouveaux indices.

Le [constructeur du paquet](../twins/m64-cylinder-head/source/flowbench-intake/package_unified_gas_domain.py)
lie explicitement domaine, manifeste d'origine, revue et sources par leurs
empreintes. Il exporte et relit les **86 faces natives** : chacune est
reconnue comme une face et passe BRepCheck. Les rôles sont affectés sans
face non appariée ou ambiguë ; les entrées et le domaine maître restent inchangés.

**Réserve sur `native_roundtrip` :** pour le corps de ce paquet, il s'agit
d'une copie bit-identique de `fab1338a…`, puis de sa relecture et de ses
contrôles B-Rep/BOP. Le champ ne constitue pas un nouveau cycle complet
d'écriture puis relecture OCCT du corps. Les exports puis relectures des
faces, en revanche, ont bien été effectués. Aucun export STEP n'est qualifié.

Les contrôles des cols d'admission et de communication des prolongements
de guides sont **hérités via la revue de correspondance des frontières**.
Aucune nouvelle intersection booléenne des cols ou guides n'a été calculée
sur ce paquet. Les joints de tige du banc restent idéalisés ; leur étanchéité
physique n'est pas qualifiée. Les valeurs historiques ne deviennent pas
des mesures nouvelles sur ce candidat.

## Inventaire et référence d'intégration nouveaux

L'inventaire `815716df…` relit les 86 faces, identifie 33 surfaces
cylindriques et les huit portions annulaires guide–tige : nouveaux indices
53–56 et 59–62. Il ne contient **aucun résultat de maillage** : la garde
d'enveloppe de facettes reste à `null` et `mesh_accepted` à `false`.
Cette garde devra être évaluée sur les triangles réellement générés.

La quadrature `1bdb66f6…` a été recalculée sur le domaine exact `fab1338a…` :

| Méthode native | Volume en unités de scan³ |
| --- | ---: |
| Non adaptative | 995 961,70449802 |
| Adaptative, précision demandée 10⁻⁹ | 995 964,5870689296 |

L'estimation de quadrature n'est pas une borne d'erreur démontrée. Ces
volumes ne sont pas des mm³ certifiés : l'échelle du scan reste une hypothèse.
La référence non adaptative servira à comparer l'import Gmsh sur la même
base d'intégration, sans transférer celle d'un ancien candidat.

## Passe exécutée et comparaison descriptive

La passe a utilisé Gmsh 4.15.2, **Delaunay 3D (`Mesh.Algorithm3D = 1`)**,
avec une limite de quatre CPU, 4 Gio et 300 s sur Kali. Le champ local
des guides reste à 0,20 unité de scan. Le champ visant l'ancienne micro-bande
« face 38 » est retiré : cet indice ne représente plus cette partition.
Ce retrait n'est ni un agrandissement du jeu guide–tige ni une relaxation
des critères de qualité. Les choix d'algorithmes sont décrits dans le
[manuel officiel Gmsh](https://gmsh.info/doc/texinfo/gmsh.html).

Le volume `c0cbb257…` est relu depuis MSH 2.2. Les onze gardes ne détectent
ni tétraèdre de volume non positif, ni frontière manquante ou surajoutée,
ni rupture de connectivité ; les groupes et la CAO native sont conservés.
La surface pré-3D `0ab139b2…` contient 93 185 nœuds. Les gardes radiales
des huit portions guide–tige passent sur leurs facettes réelles avant et
après la 3D : ce résultat ne provient pas de l'inventaire sans maillage.

| Diagnostic Gmsh après relecture | Ancien `7fc114c1…` | Nouveau `fab1338a…` |
| --- | ---: | ---: |
| Tétraèdres | 469 985 | 401 961 |
| SICN minimal | 2,5073×10⁻⁷ | 1,29054×10⁻⁵ |
| SICN inférieur à 0,1 | 1 343 | 491 |
| SICN inférieur à 10⁻⁶ | 5 | 0 |

Cette comparaison est **descriptive**, pas une causalité isolée :
l'unification des partitions et la suppression du champ devenu obsolète
« face 38 » constituent deux changements. Le SICN est un diagnostic Gmsh,
pas un substitut aux critères OpenFOAM ou une preuve de précision CFD.

## Contrôle OpenFOAM réellement exécuté

La revue `48c9803b…` autorisait uniquement conversion et diagnostic,
sans solveur. Elle retrouve avant/après 3D les 93 185 nœuds de frontière
et 186 370 triangles orientés avec leurs rôles et 86 faces natives.
Les coordonnées ASCII sont identiques ; 185 881 identifiants de triangles
sont réaffectés sans changement de géométrie ni de connectivité.

Les quatre commandes `gmshToFoam`, `transformPoints`, `createPatch` et
`checkMesh -allTopology -allGeometry` terminent avec le code zéro.
Cependant le journal conclut **`Failed 5 mesh checks`**, sans `Mesh OK` :
le superviseur renvoie donc le code 2. Un succès de processus ne vaut pas
acceptation de qualité. Aucun solveur CFD n'a été lancé.

| Contrôle OpenFOAM | Ancien `7fc114c1…` | Nouveau `fab1338a…` |
| --- | ---: | ---: |
| Rapport d'aspect excessif : cellules ; maximum | 130 ; 23 937,13 | 3 ; 2 011,04 |
| Skewness excessive : faces ; maximum | 73 ; 346,48 | 10 ; 13,1054 |
| Déterminant inférieur à 0,001 : cellules | 4 579 | **5 442 — aggravation** |
| Concavité : cellules | 23 | 0 |
| Poids d'interpolation inférieur à 0,05 : faces | 1 146 | 519 |
| Rapport de volumes inférieur à 0,01 : faces | 540 | 149 |

La concavité passe désormais ; les cinq autres familles restent rejetées.
En outre, 262 008 faces dépassent 70° de non-orthogonalité et cinq arêtes
sont signalées trop courtes : ce sont des avertissements distincts, pas
deux familles supplémentaires dans le compte des cinq échecs.

L'échelle 0,001 est appliquée une seule fois, toujours comme hypothèse.
Les trois frontières comptent 184 917 faces `walls`, 1 191 de sortie et
262 d'entrée. Les fichiers d'origine restent inchangés ; le changement
de type des parois ne change pas la géométrie. L'absence du conteneur
de diagnostic après nettoyage est vérifiée.

## Premier contre-audit C0 : refus historique conservé

Le contrôle indépendant `ec44d805…` termine en **8,312 s, code 2**.
Les cinq ancres sont distinctes et appariées de manière unique avec une
distance mesurée nulle. Les quatre courbes C0 natives 97–100 sont chacune
représentées par une chaîne monotone de respectivement **12, 2, 2 et 2
segments**. Ces contrôles locaux passent séparément.

La conservation pré/post 3D des 93 185 nœuds et 186 370 triangles passe
également ; le contre-audit retrouve ces triangles comme la vraie frontière
orientée vers l'extérieur des tétraèdres, et pas seulement comme des
enregistrements de surface conservés dans le fichier MSH.

**Le résultat global de ce premier audit reste refusé.** L'interface des faces 36/37 contient
34 arêtes de maillage, dont seulement 18 couvertes par les quatre chaînes
et 16 autres. Après fusion, l'interface native comporte les courbes 93–100,
au lieu des seules 97–100 de l'ancienne paire de faces. Le prédicat
historique exigeant que les quatre chaînes couvrent toute l'interface
ne correspond donc plus à ce périmètre élargi. Aucun critère n'a été changé
pour convertir ce refus en acceptation.

Les quatre chaînes seules ne prouvent ni la couverture complète, ni la
classification native 1D du maillage, ni la fidélité continue des cordes
à la CAO. Le contrôle étendu ci-dessous répond au premier de ces manques.

## Résultats supplémentaires : interface complète et défauts localisés

Le nouveau contrôle `dfdeb376…` examine **les huit courbes natives 93–100**
et leurs chaînes : **34 arêtes de maillage sur 34 couvertes**, sans manque,
surplus ni double compte. L'inventaire natif et ses ancres sont appariés
de façon unique ; la conservation de la vraie frontière tétraédrique
reste vérifiée. Ce contrôle de portée limitée termine en 7,674 s.
Il recalcule aussi l'ancien sous-ensemble C0 : **18/34, refus inchangé**.
Étendre explicitement l'inventaire à toute l'interface n'est pas supprimer
les 16 arêtes restantes du critère. Cela ne prouve toujours ni conformité
continue des cordes, ni qualité CFD ou fabrication.

Les cinq familles OpenFOAM sont maintenant localisées sur **ce même volume**,
via les labels natifs, les 112 649 points et les 186 370 triangles de
frontière ; les 86 faces et leurs rôles sont retrouvés. L'appariement tient
compte de l'écriture OpenFOAM à 12 chiffres significatifs, sans prétendre
à une identité binaire des coordonnées et sans employer le VTK comme CAO.

Sur les **5 442 cellules à faible déterminant, 4 382 touchent les passages
annulaires guide–tige**. Les trois cellules à fort rapport d'aspect touchent
la face 37 ; les dix faces à forte skewness se répartissent entre les faces
natives 29 (cinq), 28 (trois) et 36 (deux). Une adjacence n'établit pas,
à elle seule, la cause numérique ou physique du défaut.

Le nombre de faces internes des cellules à faible déterminant se répartit
ainsi : **degré 1 : 1 ; degré 2 : 710 ; degré 3 : 4 605 ; degré 4 : 126**.
Il s'agit d'un diagnostic topologique du cas sans frontières couplées,
pas d'une exemption de qualité.

Pour une cellule 3D et les faces internes ou couplées `I`, OpenFOAM 14 calcule
`A_moy = Σᵢ∈I |Sᵢ| / |I|`, puis
`D = |det(Σᵢ∈I (Sᵢ/A_moy) ⊗ (Sᵢ/A_moy))|` ; si `I` est vide, `D = 0`.
**Les parois non couplées sont exclues de cette somme.** Ce déterminant de
tenseur d'aires n'est pas le Jacobien du tétraèdre. La formule est vérifiée
dans [`primitiveMeshCheck.C`, commit `7b05503f98a85be88af930df48623b4d152bfc35`](https://github.com/OpenFOAM/OpenFOAM-14/blob/7b05503f98a85be88af930df48623b4d152bfc35/src/meshCheck/primitiveMeshCheck/primitiveMeshCheck.C#L457-L551).

Avec au plus deux vecteurs dans cette somme, son rang ne peut pas atteindre
trois : cela explique une difficulté structurelle pour 711 cellules du
lot, pas les 4 731 autres. Cette observation a motivé l'essai ciblé
ci-dessous ; elle ne permettait pas d'en présumer la qualité finale.

## Essai topologique exécuté : candidat rejeté

Le producteur `59893e71…` subdivise chacun des **711 tétraèdres ayant au
plus deux faces internes** en quatre enfants autour d'un nouveau barycentre :
2 844 enfants, en 12,144 s. Le candidat est `7e942138…`, distinct de la
référence `c0cbb257…`. La sélection vient de l'incidence de tout le maillage,
pas de la seule liste des défauts OpenFOAM.

Le contre-audit `2d9cdd23…`, en 11,879 s, conserve exactement les
112 649 enregistrements de nœuds d'origine, les 186 370 triangles de
frontière et les 401 250 tétraèdres non ciblés. Les 711 nouveaux nœuds
sont vérifiés séparément. En arithmétique rationnelle sur les coordonnées
décimales sérialisées, chaque enfant a exactement **un quart du volume
positif du parent**. La vraie frontière et les orientations internes sont
préservées. Ce contrôle de transformation n'accepte pas la qualité du candidat.

| Mesure après relecture ou `checkMesh` | Référence `c0cbb257…` | Candidat `7e942138…` |
| --- | ---: | ---: |
| Tétraèdres | 401 961 | 404 094 |
| Cellules de déterminant inférieur à 0,001 | 5 442 | 5 259 |
| Rapport d'aspect excessif : cellules | 3 | 3 |
| Skewness excessive : faces | 10 | 10 |
| Poids d'interpolation inférieur à 0,05 : faces | 519 | **529** |
| Rapport de volumes inférieur à 0,01 : faces | 149 | **158** |
| Non-orthogonalité supérieure à 70° : faces | 262 008 | **263 136** |
| Tétraèdres de SICN inférieur à 0,1 | 491 | **1 000** |
| SICN minimal | 1,29054×10⁻⁵ | 1,29054×10⁻⁵ |

La relecture Gmsh prend 1,287 s, sans optimisation du fichier. La chaîne
OpenFOAM termine en environ 9 s : ses quatre commandes rendent zéro,
mais **cinq familles restent rejetées** et le superviseur rend 2.
La réduction de 183 faibles déterminants ne compense pas les dégradations
observées ; **la référence `c0cbb257…` est conservée et le candidat n'est
pas adopté**. Aucun solveur CFD, calcul thermique ou essai LPBF n'est lancé.

```mermaid
flowchart TD
    A["Vraie frontière conservée ; 8 courbes couvrent 34/34 arêtes"] --> B["Localisation native des 5 familles et degrés internes"]
    B --> C["711 parents subdivisés ; transformation contre-vérifiée"]
    C --> D["Même checkMesh : 5 familles refusées, autres indicateurs dégradés"]
    D --> E["Candidat non adopté ; référence conservée"]
    E --> F["Maillage annulaire conforme et partition volumique locale à préparer"]
    F --> G["Nouveau checkMesh obligatoire ; aucune CFD avant acceptation et revue"]
```

Les résultats des anciens maillages ne sont pas attribués à cette passe.
La suite vise un maillage conforme des passages annulaires et une partition
volumique locale adaptée, **sans déformer la CAO ni élargir les jeux pour
faire passer le contrôle**. Aucun modèle annulaire simplifié n'a encore
été exécuté ou qualifié. Un volume produit ne suffit pas à autoriser un solveur CFD.

## Traçabilité et ressources

Au checkpoint courant, `make check` s'est terminé avec le code **0** :
**2 391 tests** dans la suite principale en **178,922 s**, dont **108 ignorés**,
puis cibles complémentaires terminées. Journal privé :
`dc765bd25cd723689caad0c97dda53d12afdd8bcf81cc83cb354c865d92df23a`.
Ces tests vérifient les logiciels et contrats ; ils ne renversent aucun refus
du contrôle de maillage ni ne valident physiquement la culasse.

Le [reçu public synthétique](../twins/m64-cylinder-head/evidence/unified-native-mesh-20260908.json)
regroupe les empreintes, mesures, refus et limites de cette passe. Les géométries
et coordonnées détaillées restent dans les traces privées.

Le [reçu de l'interface complète et de l'essai de subdivision](../twins/m64-cylinder-head/evidence/unified-interface-and-star-trial-20260908.json)
porte les preuves supplémentaires : producteur `59893e71…`, contre-audit
`2d9cdd23…`, contrôle OpenFOAM `9c68cb1d…`, journal `135f9d8f…` et
qualité Gmsh `1f3af0ca…`. Il distingue l'intégrité conservée du rejet de qualité.

Empreintes du paquet préparé : domaine `fab1338a…`, manifeste `58b8be5a…`,
source du constructeur `9bb1486f…`, revue `7bd9c92d…`, inventaire `815716df…`
et quadrature `1bdb66f6…`. Le rapport de passe est `de7094fd…` ; ses
maillages volume et pré-3D sont respectivement `c0cbb257…` et `0ab139b2…`.
La revue de conversion est `48c9803b…`, le reçu OpenFOAM `a466529e…`
et son journal `f3ec17cd…`. Le contre-audit C0 est `ec44d805…`, lié à
la source `d29d5dae…` ; ses 20 tests ciblés passent sans test ignoré.
Ces tests logiciels ne remplacent pas le refus observé sur le maillage réel.

Nouveaux reçus : inventaire complet d'interface `dfdeb376…`, localisation
`801dad7d…`, complément des degrés `ca37bc26…`, export des ensembles natifs
`4eb33217…`. Ils concernent les mêmes fichiers `c0cbb257…` et `0ab139b2…` ;
ils sont distincts des reçus de l'essai de subdivision `7e942138…`.

Pour le maillage Delaunay initial, la source réellement exécutée est **`04811670b4e46fbbc4e1268e277db9744ec39cb20846869243d5623bf7164408`**,
gelée dans les traces privées. Après cette passe, une garde de prévol a été
ajoutée contre l'omission de la taille et de la référence des guides ; huit
tests ciblés du profil unifié passent. La passe exécutée fournissait déjà
ces options et a vérifié les facettes. **La source durcie ultérieure ne lui
est pas attribuée rétroactivement.** Le point de départ source reste `e9ac07c`.

Aucune nouvelle dépense Vast pour cette exécution locale x86. Le solde
disponible vérifié est **43,9166429608502 USD**, sous le plafond utilisateur
de **44 USD** ; aucune instance Vast n'est présente au relevé vérifié.
Les deux conteneurs de diagnostic de l'essai sur Kali, limités chacun à
quatre CPU et 4 Gio, ont été supprimés ; leur absence a été vérifiée.
Aucune promesse de maillage accepté ou de culasse imprimable n'est attachée
à ce résultat d'intégrité.
