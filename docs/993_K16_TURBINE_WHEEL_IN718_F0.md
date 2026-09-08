# Roue de turbine K16 — concept IN718 F0

Cette seizième pièce métallique distincte du programme est le premier modèle du
rotor chaud K16. L'intérêt additif est réel pour une pièce de rechange complexe
et produite en faible volume : douze pales peuvent être itérées sans recréer un
outillage de fonderie. Cela ne rend pas automatiquement le LPBF préférable. Une
roue nickel moulée et qualifiée reste la référence industrielle à battre.

Le résultat F0 est un **rejet**, ce qui est utile : le modèle passe le disque
centrifuge mais échoue au pied de pale, au gradient thermique et à l'enveloppe
de température retenue. Rien dans ce dossier n'autorise une fabrication ou une
rotation.

## Faits et hypothèses

TurboMaster relie le K16 droit `5316-988-6735` de la 993 Turbo à la roue/arbre
`5316-120-5000`. Le relevé fournisseur Invasion déclare `54,96 mm` à l'inducer,
`48,97 mm` à l'exducer et douze pales. Une roue de remplacement Kinugawa pour
la même référence annonce `49/55 mm`, une hauteur de pointe de `9,4 mm` et un
arbre de `8,42 mm`.

Ce sont les seuls faits géométriques utilisés. L'enveloppe axiale `20 mm`, le
disque, le moyeu et les pales droites `2,4 → 0,8 mm` sont des hypothèses propres
au projet. Chaque effilement continu est représenté en CAO par quatre paliers.
L'arbre complet, sa liaison, les profils, le vrillage, les congés, les jeux et
les corrections d'équilibrage sont absents.

PorscheFanatics confirme le contexte biturbo 993 et l'intérêt des upgrades de
la ligne chaude, mais ne catalogue aucune roue additive ni géométrie K16
réutilisable.

## Matière candidate

Le criblage emploie EOS NickelAlloy IN718 API sur M 290, couche `40 µm`, après
traitement thermique. EOS publie TRL `9`, une paroi minimale typique
`0,3–0,4 mm`, une densité `8,15 g/cm³`, `0,03 %` de défauts moyens et, à
l'ambiante en vertical, Rp0,2 `865 MPa`, Rm `1 236 MPa`, allongement `28 %`.

Ces résultats sont des coupons liés au procédé API. Ils ne donnent ni HCF, ni
LCF, ni fluage, ni propagation, ni admissible d'éclatement pour ce rotor. EOS
présente génériquement l'IN718 pour des usages jusqu'à `700 °C`. Le catalogue
BorgWarner donne un contexte T3 de `950 °C` continu pour la ligne d'upgrade,
mais T3 est une température de gaz, pas une température métal K16 mesurée. Le
dépassement de `250 °C` est donc un signal d'arrêt, pas une preuve de fusion.

## CAO calculable

Le STEP relu dans l'image verrouillée contient un solide BREP valide de
`54,96 × 54,96 × 20,00 mm`, douze pales et un marqueur d'interface arbre de
`8,42 mm`. Le volume vaut `17 076,46 mm³` et la masse IN718 théorique
`139,17 g`. Un cylindre enveloppe pèserait `386,70 g`, soit un ratio brut/pièce
de `2,779`. L'arbre complet n'est pas modélisé.

## Rotation et sur-vitesse

Faute de trace de vitesse K16, le rotor partage uniquement le point de
régression du compresseur F1 : Mach périphérique compresseur `0,9`, donnant
`103 464 tr/min`. La pointe turbine atteint alors `297,74 m/s`.

Pour une pale d'épaisseur linéaire `t(r)` :

`V = h × L × (t_racine + t_pointe) / 2`

`F = ρ × V × ω² × r_moyen`

`σ_racine = Kt × F / (t_racine × h)`

Avec `Kt = 2,5` et la sur-vitesse `1,2×`, la contrainte atteint
`701,50 MPa`. Le rapport Rp0,2 ambiant/contrainte vaut `1,233`, sous le seuil
de régression `1,5` : **échec**.

Le disque tournant est criblé par
`σ = (3 + ν) / 8 × ρ × ω² × r²`. À la sur-vitesse il atteint `427,85 MPa`,
soit un rapport ambiant `2,022` : cet écran seul passe.

## Thermique

La borne totalement contrainte emploie
`σ_th = E × α × ΔT / (1 − ν)` avec un gradient synthétique `350 K`. Elle donne
`1 528,17 MPa`, donc un rapport ambiant `0,566` : **échec**. Le module et le
coefficient de Poisson sont provisoires ; appliquer une limite ambiante à ce
cas chaud ne constitue pas un calcul de durée de vie.

En extrapolant le coefficient EOS à `700 °C` jusqu'au contexte gaz `950 °C`,
la croissance radiale libre serait `0,396 mm`. Le jeu réel n'est pas connu et
la température métal ne peut pas être assimilée à T3. La valeur sert seulement
à montrer que le couplage thermique-carter est indispensable.

## Bilan de puissance à un point

Le même point compresseur demande `13,11 kW`. Avec un rendement mécanique
supposé `0,95`, la turbine doit fournir `13,81 kW`, soit `1,274 N·m`. Pour un
AFR synthétique `12`, un rendement turbine `0,70` et une sortie `110 kPa`, le
bilan parfait-gaz exige un rapport d'expansion `1,419`.

Ce résultat n'est ni une carte turbine, ni une preuve de débit. Il ignore la
volute, les aubages réels, les pulsations, la wastegate, les fuites et les
pertes de palier.

L'énergie de rotation approximative du solide F0 vaut `3,08 kJ`. Un balourd de
`10 mg·mm` produit `1,17 N`. En `100 h`, le modèle cumule `620,8 millions` de
tours et `7,45 milliards` de passages de pale. Sans courbes HCF/LCF à chaud,
le calcul de vie reste explicitement non calculable.

## Reproduction

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/work" -w /work \
  ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57 \
  python parts/993-eng-k16-turbine-wheel-in718-f0-0001/source/turbine_wheel.py \
  --out parts/993-eng-k16-turbine-wheel-in718-f0-0001/derived/turbine_wheel_in718_f0.step \
  --report parts/993-eng-k16-turbine-wheel-in718-f0-0001/evidence/engineering-screen.json
```

## Gates suivants

1. Scanner par CT la roue `5316-120-5000`, l'arbre et la liaison.
2. Reconstruire les profils, congés, surfaces de moyeu et interfaces mesurés.
3. Mesurer vitesse, T3, température métal, pressions, débit, wastegate et cycle.
4. Comparer fonderie qualifiée, usinage et LPBF avec une vraie route roue-arbre.
5. Exécuter CFD tournante, CHT, FSI, FEA centrifuge-thermique, Campbell,
   rotor-dynamique, fluage, HCF/LCF et éclatement probabiliste convergés.
6. Qualifier poudre, paramètres, orientation, supports, traitement, HIP,
   usinage, polissage, liaison, CT, FPI, métallurgie et équilibrage.
7. Passer spin proof, sur-vitesse et éclatement confinés avant tout banc turbo.

PhysicsNeMo reste différé : il faut d'abord des séries CFD/CHT/structure
corrélées avec jeux d'entraînement, de validation, de holdout et hors
distribution. Le F0 est interdit de fabrication, rotation, turbo et moteur.
