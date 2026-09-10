# Roue de compresseur K16 — itération Al2139 AM F1

Le F0 AlSi10Mg a rempli son rôle : il a échoué. À Mach périphérique `0,9` et
sur-vitesse `1,2×`, sa pale principale droite atteignait `390,9 MPa` face à une
comparaison ambiante de `245 MPa`, soit un rapport de `0,627`.

Le F1 conserve exactement les seuls faits géométriques publiés pour la roue
K16 droite `53241232006` : inducer `40,6 mm`, exducer `60,5 mm`, six pales
principales et six séparatrices. Le changement porte sur la matière candidate
et la distribution d'épaisseur, pas sur une prétendue reconstruction OEM.

## Modification d'ingénierie

La pale principale passe de `1,2 mm` uniforme à une loi linéaire
`3,0 → 0,8 mm`. La séparatrice passe à `2,4 → 0,8 mm`. La CAO verrouillée
approxime chaque loi par quatre tronçons radiaux chevauchants ; le calcul de
force utilise l'intégrale continue exacte de l'épaisseur.

L'AlSi10Mg est remplacé comme candidat par EOS Aluminium Al2139 AM sur M 290,
`60 µm`, traité thermiquement. EOS publie pour cette route TRL `3`, une paroi
minimale de `0,4 mm`, une densité moyenne d'au moins `2,84 g/cm³`, `0,2–0,3 %`
de défauts moyens, Rp0,2 `460 MPa`, Rm vertical `520 MPa` et allongement
vertical `4 %` à l'ambiante. Ces valeurs ne sont pas des admissibles rotor.

## Résultat CAO

Le STEP relu contient un solide BREP valide de `60,5 × 60,5 × 18 mm`, douze
pales et un alésage traversant. Son volume vaut `13 554,48 mm³` et sa masse
théorique `38,49 g`. Un cylindre enveloppe Al2139 pèserait `146,96 g`, soit un
rapport théorique `3,82`. Ce n'est ni un brut industriel ni un calcul de coût.

## Calcul de pale effilée

Pour une épaisseur linéaire `t(r)`, le volume de pale emploie :

`V = h × L × (t_racine + t_pointe) / 2`

La force centrifuge utilise le premier moment radial exact :

`F = ρ × h × ω² × ∫ r × t(r) dr`

Puis la contrainte de racine est criblée par :

`σ = Kt × F / (t_racine × h)` et `σ_survitesse = σ × 1,2²`.

La pale principale F1 pèse analytiquement `1,380 g`, avec rayon moyen
`16,382 mm`. Elle produit `2,654 kN`, `160,84 MPa` nominal et `231,61 MPa` à la
sur-vitesse. La séparatrice atteint `200,10 MPa` à la sur-vitesse.

Le ratio gouvernant Al2139/contrainte vaut donc `1,986`, contre `0,627` au F0,
soit `40,75 %` de contrainte en moins malgré la densité plus élevée. Le disque
donne un ratio `2,516` et la borne thermique totalement contrainte `1,905`.
Les trois dépassent le seuil de régression `1,5`.

**Cela signifie uniquement que le F1 passe trois équations ambiantes.** La
limite `460 MPa` vient d'éprouvettes T4, le module et la dilatation restent
provisoires, et aucune HCF à chaud n'est disponible. Il n'existe toujours ni
profil aérodynamique, ni carte K16, ni rotor complet.

## Point aérothermique inchangé

Le point synthétique reste `103 464 tr/min`, `0,08194 m³/s` par banc, Mach axial
`0,190`, rapport de pression `1,8`, rendement `0,72`, sortie `413,8 K` et
puissance `13,11 kW`. Il sert uniquement à comparer F0 et F1 sur une même base.

La croissance centrifuge plus thermique vaut `0,159 mm`, alors que le jeu réel
est inconnu. L'énergie de rotation approximative monte à `1 034 J`; dix mg·mm
de balourd produisent `1,17 N`. Ces valeurs renforcent l'exigence d'un spin rig
confiné et ne prouvent aucune tenue.

## Reproduction

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/work" -w /work \
  ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57 \
  python parts/993-eng-k16-compressor-wheel-al2139-f1-0001/source/compressor_wheel_f1.py \
  --out parts/993-eng-k16-compressor-wheel-al2139-f1-0001/derived/compressor_wheel_al2139_f1.step \
  --report parts/993-eng-k16-compressor-wheel-al2139-f1-0001/evidence/engineering-screen.json
```

## Gates suivants

1. Mesurer/CT la roue K16 et tout l'ensemble arbre-écrou-backplate-carter.
2. Construire de vraies surfaces de pales depuis métrologie et aéro inverse.
3. Obtenir carte, vitesses, températures, jeux, balourd et cycle de service.
4. Exécuter CFD tournante, FSI, FEA centrifuge-thermique, rotor dynamique,
   Campbell, HCF et analyse probabiliste d'éclatement avec convergence.
5. Qualifier Al2139, orientation, supports, traitement, défauts, finition,
   usinage, CT et équilibrage.
6. Passer spin proof, sur-vitesse et éclatement confinés avant tout banc turbo.

PhysicsNeMo attend les séries corrélées CFD-structure-rotordynamique avec train,
holdout et hors-distribution. Le F1 n'est autorisé ni pour fabrication, ni pour
rotation, ni pour turbo ou moteur.
