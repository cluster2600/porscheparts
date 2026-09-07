# Corps à quatre logements — audit CAO du 7 septembre 2026

Le corps privé possède maintenant quatre contre-alésages de sièges et quatre
passages de guides. Après correction locale des courbes de découpe, son STEP
passe les contrôles BRep et les cinq modes BOP exécutés. **C'est un essai
d'intégration géométrique incomplet, pas une culasse M64 fonctionnelle ou imprimable.**

Le [reçu public vérifiable](../twins/m64-cylinder-head/evidence/four-seat-body-cad-audit-20260907.json)
consigne les empreintes SHA-256 des sources, du corps avant/après correction,
de l'assemblage et des trois rapports privés relus. Il ne contient ni scan, ni
CAO privée, ni image dérivée, ni coordonnées ou identifiants de faces du scan.

## Périmètre et hypothèses

Le corps F43 provient de la reconstruction d'une référence scannée 935 : ce
n'est pas une définition certifiée M64. Le module V2 fournit les douze composants
réels : quatre soupapes, quatre sièges, quatre guides. Leur recalage emploie
**1 unité du scan par mm du module**, une rotation Z de −90° et une translation
Z de +3 unités. Ces hypothèses ne certifient ni l'échelle ni les interfaces moteur.
Les deux maîtres sont restés inchangés.

Les logements sont nominaux, sans serrage choisi : Ø43 pour les deux sièges
d'admission, Ø36 à l'échappement et Ø11 pour les guides, exprimés en mm du module
avant le recalage hypothétique. Les portées coniques appartiennent aux inserts
et aux soupapes ; les logements dans le corps sont cylindriques.

## Résultats vérifiés

| Contrôle | Résultat et portée |
|---|---|
| Corps final après STEP | 1 solide, 1 coque, 5 130 faces ; aucune arête libre ou non-manifold. |
| BRep / BOP | BRep valide ; aucun résultat fautif dans les modes auto-intersection, petite arête, reconstruction de face, continuité et courbe sur surface. Ces contrôles portent sur le corps. |
| Assemblage privé | Corps + 12 composants, soit 13 solides ; ce décompte ne valide pas le fonctionnement de l'ensemble. |
| Contacts au fermé | Volume d'intersection corps découpé/composant nul pour les 12 composants. Les 8 inserts de siège/guide sont entièrement contenus dans le corps initial par contrôle volumique. |
| Soupapes mobiles | 8 contrôles discrets sur le corps corrigé : fermé et levée maximale de chaque soupape ; volumes d'intersection nuls. Levées candidates : 11,5 admission et 9,6 échappement, en unités du scan sous l'hypothèse d'échelle. |

Les quatre résultats à levée maximale s'appliquent également aux intersections
avec le **corps fixe** lorsque les quatre soupapes sont à leur maximum. Aucun
calcul couplé supplémentaire, balayage continu, collision soupape-soupape,
piston ou loi de came n'a été exécuté dans cet essai.

## Correction locale et changements non nuls

Le premier STEP signalait cinq défauts `InvalidCurveOnSurface` dans le contrôle
spécifique des courbes sur surfaces. Seules leurs représentations 2D sur les
cylindres ont été reconstruites : projection analytique, 129 points et dérivées
exactes aux extrémités. L'interpolation sans ces contraintes avait été rejetée.
Aucun traitement global ni relèvement de tolérance n'a été appliqué.

Après aller-retour STEP, les 5 286 sommets, 10 412 arêtes et 5 130 faces ont été
comparés. Le déplacement 3D maximal **échantillonné** est de 2,29325 × 10⁻¹² unité
sur les arêtes ; le volume varie de **+1,64399 × 10⁻⁵ unité³**. Les tolérances
n'augmentent nulle part ; quatre sommets et trois arêtes voient leur tolérance
diminuer. Ces variations sont consignées, pas assimilées à une identité exacte.
Le contrôle sur 2 001 points par courbe corrigée atteint au plus
5,18164 × 10⁻⁸ unité ; ce n'est pas une borne continue de l'erreur géométrique.

## Portions de surface retirées, pas « 54 trous »

Le traçage des opérations booléennes identifie **54 portions de faces sources**
retirées hors des faces planes extrêmes : 26 côté admission 1 et 28 côté
échappement 2. Leurs aires cumulées sont respectivement 270,458 et 258,615 unités².
Ce découpage topologique ne compte pas des ouvertures physiques distinctes.

La projection conservative de leurs boîtes sur les axes situe ces 54 portions
au-dessus de l'engagement réel des guides, sans recouvrement des intervalles
siège/guide. Un manque de matière à ces appuis n'est donc **pas démontré**.
Le futur espace de distribution reste à définir avant de qualifier ces sorties.
L'enveloppe globale ne change qu'à 2,35 × 10⁻¹² unité près après perçage, mais
cette stabilité ne signifie pas que toute la peau extérieure est inchangée.

## Ce qui reste à établir

Conduits et chambre finale, porte-arbres et distribution complète, piston et
cinématique continue, galeries d'huile, filetages, serrages à froid/à chaud,
matériaux et interfaces M64 demeurent à définir ou qualifier. Aucun résultat
thermique, mécanique ou de procédé LPBF n'est validé pour ce corps par cet audit.
**Aucune autorisation de fabrication ou de fonctionnement moteur n'en découle.**
