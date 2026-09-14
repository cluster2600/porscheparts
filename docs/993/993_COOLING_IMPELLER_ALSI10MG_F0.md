# Turbine de refroidissement moteur 993 — AlSi10Mg F0

Cette pièce tournante prolonge directement le carter fixe F0. PorscheFanatics
identifie la turbine Porsche `964 106 015 31` pour 964/993. FVD publie une
enveloppe produit `300 × 300 × 150 mm` et `0,94 kg`; le Centre Service Porsche
Poitiers publie `0,948 kg`. Partworks indique aluminium, sans nuance ni procédé.

## Géométrie F0 et intégration

Le maître build123d est indépendant : diamètre `280 mm`, profondeur `30 mm`,
moyeu annulaire `80/30 mm`, douze pales droites balayées de `10°` et anneau
périphérique `3 mm`. Le STEP relu contient un solide BREP valide de
`370 931,41 mm³`, soit `990,39 g` en AlSi10Mg.

La masse se situe à `+5,36 %` des `940 g` FVD, mais ce rapprochement scalaire ne
valide ni forme, ni balance. Un brut `280 × 280 × 30 mm` pèserait `6,280 kg`,
soit `6,34` fois le F0 : l'AM a un intérêt géométrique et matière réel.

Le premier test d'ensemble est volontairement strict : le carter F0 précédent
possède une gorge synthétique `252 mm`, face à cette turbine `280 mm` :

`c_radial = (252 - 280)/2 = -14 mm`

L'ensemble est donc **incompatible**. Aucune dimension synthétique n'est
silencieusement ajustée; une mesure ou une décision d'architecture est requise.

## Survitesse et énergie

Le cas de régression utilise `10 000 tr/min`, puis `12 000 tr/min` à `1,20×`.
La vitesse de bout en survitesse vaut `175,93 m/s`, Mach `0,467` à `80 °C`.

L'écran d'anneau mince `σθ = ρv²` donne `82,64 MPa`, rapport ambiant
`245/82,64 = 2,965`. Chaque pale synthétique pèse `38,13 g`; le modèle direct
`F = mω²r` donne `5,33 kN` et `38,06 MPa` au pied, rapport `6,44`. Ces deux
écrans passent, mais ignorent entaille, flexion, torsion, défauts LPBF et HCF.

L'inertie polaire analytique vaut `0,00831 kg·m²`; l'énergie en survitesse vaut
`6,56 kJ`. C'est un indicateur de danger, pas une preuve de confinement.

## Modal, débit et thermique

Le premier mode de pale encastrée simplifiée vaut `556,5 Hz`; la fréquence de
passage à douze pales vaut `2 000 Hz`, séparation `72,2 %`. Le passage de cet
écran ne remplace pas un diagramme de Campbell de l'ensemble alternateur/carter.

Le débit `1,01 m³/s` et la hausse de pression `800 Pa` sont des cibles
synthétiques : aire `0,05655 m²`, vitesse moyenne `17,86 m/s`, puissance air
`808 W` et couple idéal `0,772 Nm`. Sans angle/forme de pale et courbe mesurée,
aucune performance de refroidissement n'est calculée.

À `150 °C` depuis `20 °C`, le diamètre croît librement de `0,764 mm`.
Totalement contraint, `σ = EαΔT = 191,1 MPa`; rapport `1,282`, donc **échec**.
Avec l'incompatibilité carter, le résultat global reste rouge.

## Reproduction

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/work" -w /work \
  ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57 \
  python parts/993-eng-cooling-impeller-alsi10mg-f0-0001/source/cooling_impeller.py \
  --out parts/993-eng-cooling-impeller-alsi10mg-f0-0001/derived/cooling_impeller_alsi10mg_f0.step \
  --report parts/993-eng-cooling-impeller-alsi10mg-f0-0001/evidence/engineering-screen.json
```

## Gates suivants

1. Mesurer ensemble turbine, carter, moyeu, axe, alternateur, poulie et cales.
2. Réconcilier diamètre, profondeur, jeu de bout et croissance thermique.
3. Scanner les pales et mesurer régime, débit, pression, température et bruit.
4. Exécuter CFD tournante et CHT avec courbes banc corrélées.
5. Exécuter FEA centrifuge/thermique, Campbell, HCF et perte de pale.
6. Qualifier LPBF, T6/HIP, usinage, CT/FPI et équilibrage deux plans.
7. Passer survitesse confinée, vibration, débit puis endurance cellule moteur.

PhysicsNeMo reste différé jusqu'à l'existence de séries CFD tournantes,
structure/modal/HCF et banc corrélées. Le F0 est interdit de fabrication,
rotation, installation et mise en route.
