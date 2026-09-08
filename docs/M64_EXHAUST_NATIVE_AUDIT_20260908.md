# M64 — passage d’échappement natif : candidat conservé, non validé

Le corps avec admission et échappement a été exporté, mais **reste refusé** :
le contrôle bit à bit des tolérances après sérialisation échoue et un audit
BOP indépendant signale deux `BOPAlgo_GeomAbs_C0`, encore non localisés.
Aucune dérogation, qualification fonctionnelle ou autorisation de fabrication
n’est accordée. La [capsule de preuves](../twins/m64-cylinder-head/evidence/exhaust-native-audit-20260908.json)
relie les trois étapes aux reçus privés, sans publier la géométrie.

## Trois étapes distinctes

| Étape réellement exécutée | Observation | Décision conservée |
|---|---|---|
| Essai 01 | Appel d’API `HasErrors` indisponible sur l’objet `BRepAlgoAPI_Cut` ; arrêt avant export | Erreur du programme, pas preuve d’invalidité de la pièce |
| Essai 02 | Export natif `21c9c40b…`, un solide, une coque, 4 900 faces ; BRepCheck exact valide avant/après relecture | Refus `rejected_native_tolerance_integrity` |
| Audit indépendant | Relecture du même export, cinq modes BOP activés ensemble ; deux signalements C0 | Refus maintenu, incidence non qualifiée |

L’essai 01 termine avec un code travailleur 1 et un code conteneur 2, en
7,514 s murales supervisées. L’essai 02 termine avec le code 2 en 12,569 s.
Son calcul natif dure 11,554 s ; son intervalle conteneur est
11:20:12,499–11:20:24,905 UTC, le 8 septembre 2026.

Le corps d’entrée `33375e12…` et l’outil d’échappement `9e1ab8b3…` sont
épinglés. Aucun changement de repère supplémentaire n’est appliqué, aucun
STEP n’est utilisé et les originaux restent intacts. Le refus préalable
relatif au maintien des guides n’est pas effacé par cette nouvelle découpe.
La référence reste issue du scan 935 ; `1 unité = 1 mm` demeure une hypothèse,
pas une échelle ni une compatibilité d’interfaces M64 certifiées.

## Ce que le diagnostic de sérialisation démontre — et ne démontre pas

Les listes enregistrées présentent 89 différences parmi 5 176 tolérances de
sommets. L’écart absolu maximal est `4,235164736271502e−21` unité de scan.
Les 10 075 tolérances d’arêtes et les 4 900 tolérances de faces sont identiques ;
les extrema et les tolérances des entrées sont inchangés. Le volume adaptatif
calculé avant et après relecture est égal, sans constituer une preuve globale
d’identité géométrique.

Sur ces listes ordonnées, `float(format(avant, '.15g')) == relecture`
reproduit exactement les 5 176 valeurs, dont les 89 différentes. Les témoins
à 16 et 17 chiffres ne reproduisent aucune des 89 différences. Ce reçu
arithmétique seul ne vérifiait pas le code de sérialisation et n’établit
**aucune correspondance géométrique indépendante de tous les sommets**.

La lecture primaire ultérieure d’OCCT 7.9.3 montre que
[`TopTools_ShapeSet::Write`](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_9_3/src/TopTools/TopTools_ShapeSet.cxx#L427-L515)
fixe la précision à 15 chiffres, appelle l’écriture de la géométrie puis
restaure la précision. La
[routine des sommets](https://github.com/Open-Cascade-SAS/OCCT/blob/V7_9_3/src/BRepTools/BRepTools_ShapeSet.cxx#L497-L508)
écrit leur tolérance dans ce flux. C’est cohérent avec l’arrondi observé,
pas une déformation mécanique mesurée ni une preuve complète d’invariance.
Le refus historique demeure, sans dérogation générale ni tolérance de
fabrication déduite ; les deux C0 restent un obstacle distinct.

## Audit BOP séparé, en lecture seule

Le reçu indépendant `09dfd5e6…` est lié au candidat sauvegardé. BRepCheck
exact est valide ; BOP signale `HasFaulty=true`, `HasErrors=false` et
`HasWarnings=false`, avec **deux `BOPAlgo_GeomAbs_C0` au total**.
Les modes `SelfInterMode`, `SmallEdgeMode`, `RebuildFaceMode`,
`ContinuityMode` et `CurveOnSurfaceMode` sont activés dans ce même audit,
avec fuzzy nul, sans arrêt au premier défaut.

Ce contrôle dure 174,308 s pour BOP, 177,111 s au niveau du wrapper, et
retourne 2. Les tolérances et toutes les entrées restent inchangées ; aucun
B-Rep/STEP n’est écrit ou réparé. Les deux signalements ne sont **pas des
fissures physiques démontrées** : leurs entités et leur incidence fonctionnelle
ne sont pas encore déterminées. Ce reçu ne transforme aucun refus en succès.

```mermaid
flowchart TD
    A["Essai 01 : erreur API, aucun export"] --> B["Essai 02 : export natif du corps"]
    B --> C["Tolérances bit à bit : refus conservé"]
    C --> D["Audit séparé : deux C0 non localisés"]
    D --> E["Localiser et qualifier avant nouvelle décision"]
    E --> F["Contrôles fonctionnels, CFD et fabrication toujours non autorisés"]
```

## Ce qui reste absent

Le `Common` du matériau réellement retiré et le BOP final du producteur
n’ont pas été exécutés : ils sont situés après le garde de sérialisation.
L’audit séparé ne remplace pas ce `Common` ni les contrôles fonctionnels 6–12 :
continuité du gaz complet quatre soupapes, maintien des sièges/guides,
parois après les deux conduits et bandes d’interfaces protégées.
Thermique, résistance, LPBF et validation d’impression ne sont pas exécutés
sur ce candidat. Voir le [dossier matériau/refroidissement/LPBF](M64_700CH_MATERIAL_COOLING_LPBF.md)
pour leurs exigences distinctes.

Une image **privée** est réellement rendue à partir du seul corps exporté :
4 900 faces, 92 118 triangles, déflexions linéaire 0,18 et angulaire 0,25 rad.
Elle montre une vue externe opaque et une demi-coupe d’affichage non bouchée,
sans transformation supplémentaire, lissage, décimation ni génération IA.
Aucun ancien assemblage de douze composants ni aucune ancienne affectation
fonctionnelle de couleurs n’est réutilisé. Le gris n’est pas un choix de
matériau. Image, maillage dérivé et coordonnées restent privés.

## Ressources et portée

Kali x86 : deux CPU, 4 Gio de mémoire et swap combinés, limite 300 s par
exécution native, réseau coupé et entrées montées en lecture seule. L’essai
02 est lié à la commande du wrapper figé ; l’inspection HostConfig en direct
a manqué ce conteneur déjà terminé. Pour l’audit indépendant, les limites
ont aussi été constatées sur le conteneur vivant. Les conteneurs sont
supprimés, absence vérifiée ; aucun OOM ni timeout n’est signalé.

Le rendu local dure 3,834 s d’extraction puis 5,220 s de rendu, sans timeout.
Aucune nouvelle location ni dépense Vast pour ce lot. Le plafond autorisé de
44 USD est un budget, pas une mesure du solde du compte. Cette documentation
ne vaut ni validation de la culasse complète ni autorisation de fabrication.
