# Cache-moyeu 993 — concept AlSi10Mg F0

PorscheFanatics identifie `993 361 303 07` comme cache-moyeu et conserve son
statut PET historique `U`, supprimé sans remplacement, tout en indiquant que sa
disponibilité actuelle est inconnue. Partworks vend actuellement une variante
originale et déclare : plastique, diamètre extérieur `76 mm`, diamètre intérieur
`60 mm` et hauteur `46 mm`.

Le F0 conserve uniquement ces trois dimensions. Sa face est volontairement
neutre : aucun blason, logo ou dessin Porsche n'est reproduit. La jupe, la bague
de centrage et les quatre languettes avec bourrelets sont des hypothèses propres
au projet.

## Pourquoi tester l'AM métal

Le LPBF consolide dans un seul solide une face, deux bagues et quatre languettes
avec contre-dépouilles. Cela peut avoir un intérêt pour une petite série ou une
variante personnalisée. L'original étant en plastique, MJF, SLS et injection
restent toutefois des concurrents probablement plus légers et plus souples.
Le procédé reste donc `undecided`.

## Criblage exécuté

Pour des hypothèses de flèche de clipsage `0,4 mm`, frottement `0,30`, vitesse
`250 km/h`, rayon roulant `315 mm`, choc axial `20 g` et écart thermique
`120 K`, le rapport recalcule :

- volume exact des cylindres annulaires et languettes, puis masse `rho V` ;
- `I=b t³/12`, effort de console `3 E I delta/L³` et contrainte en racine ;
- capacité de rétention par frottement et demande inertielle axiale ;
- vitesse de roue `omega=v/R`, charge centrifuge des languettes et contrainte
  circonférentielle de la bague ;
- dilatation différentielle aluminium/acier ;
- BREP OCCT unique et relecture du STEP.

Le concept donne `75,29 g`, `16,59 N` par languette, `93,33 MPa` en racine et
un ratio synthétique rétention/demande de `1,35`. Ce ratio n'est pas un facteur
de sécurité : géométrie de roue, frottement, fatigue, usure et choc réels sont
absents.

## Gates avant prototype routier

1. Mesurer une roue identifiée et un cache réel : alésage, clips, insertion,
   arrachement et tolérances.
2. Comparer objectivement AlSi10Mg, polymère MJF/SLS et injection.
3. Ajouter congés, orientation, traitement thermique et état de surface.
4. Contrôler CT et dimensionnellement, puis tester insertion/arrachement,
   rotation, choc, corrosion et cycles thermiques sur banc.
5. Obtenir une revue professionnelle du risque de détachement avant route.

PhysicsNeMo attendra des courbes d'insertion, des essais de rotation et des
cycles thermiques. SimReady reste différé tant que l'interface de roue et la
loi de rétention ne sont pas mesurées.
