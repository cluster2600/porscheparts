# Carter fixe de ventilateur moteur 993 — AlSi10Mg F0

Ce candidat vise la partie **stationnaire** du refroidissement, jamais la
turbine tournante. PorscheFanatics rappelle que le carter distribue l'air à
l'ensemble du moteur : son ajustement et son étanchéité sont fonctionnels.

FVD publie la référence `993 106 667 03`, une enveloppe produit
`300 × 300 × 170 mm` et `1,9 kg`. Le Centre Porsche Roissy publie `1,86 kg` et
relie aussi `993 106 667 01`. Un revendeur décrit la pièce comme aluminium,
sans nuance, procédé ni certificat. Ces éléments suffisent à borner un F0, pas
à reconstruire une pièce ajustable.

## Géométrie et valeur additive

Le maître build123d conserve l'enveloppe publiée, puis emploie des interfaces
entièrement synthétiques : gorge `252 mm`, coque `3 mm`, bride `4 mm`, support
annulaire `90/70 mm`, six rayons `81 × 12 × 12 mm` et six trous `6,6 mm`.

Le STEP relu contient un solide BREP valide, sans turbine, et une voie d'air
ouverte. Son volume est `668 006,23 mm³`, soit `1 783,58 g` en AlSi10Mg. La
proximité des `1,86–1,90 kg` commerciaux n'est pas une validation : plusieurs
géométries très différentes peuvent avoir la même masse.

Un brut parallélépipédique plein pèserait `40,851 kg`, soit `22,90` fois le F0.
L'AM peut donc se défendre pour une restauration à faible volume, en consolidant
coque, bride, support et rayons. Une fonderie aluminium/magnésium qualifiée reste
toutefois la référence à battre en coût, fatigue, état de surface et cadence.

## Criblage d'écoulement

Avec le cas synthétique `Q = 1,25 m³/s`, la section annulaire vaut :

`A = π(D² - d²)/4 = 0,043514 m²`, puis `v = Q/A = 28,73 m/s`.

Pour `ρ = 1,05 kg/m³` et `K = 0,8`, le modèle concentré donne :

`Δp = Kρv²/2 = 346,58 Pa`, puis `P = ΔpQ = 433,23 W`.

L'écran passe sous une limite arbitraire de `500 Pa`, rapport `1,443`. Ce n'est
ni une courbe de ventilateur, ni la répartition du débit vers les cylindres.

## Structure, modal et thermique

Une charge radiale synthétique de `2 kN` est répartie également sur six rayons.
Le modèle de poutre donne `I = bt³/12 = 1 728 mm⁴`, `93,75 MPa` et
`0,488 mm` en bout. Le rapport à `245 MPa` vaut `2,61` : l'écran statique passe
de justesse sur la flèche maximale `0,50 mm`.

Le premier mode de rayon encastré simplifié vaut `1 512,8 Hz`. Une excitation
synthétique à onze pales et `6 000 tr/min` vaut `1 100 Hz`; séparation `37,5 %`,
au-dessus de la cible `20 %`. Cet écran ne remplace pas un modèle modal du
carter assemblé.

À `150 °C` depuis `20 °C`, la gorge croît librement de `0,688 mm`. Totalement
contrainte, `σ = EαΔT` atteint `191,1 MPa`; le rapport `245/191,1 = 1,282` est
inférieur à `1,5` : **échec thermique**. Le F0 global échoue donc volontairement.

## Reproduction

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/work" -w /work \
  ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57 \
  python parts/993-eng-fan-housing-alsi10mg-f0-0001/source/fan_housing.py \
  --out parts/993-eng-fan-housing-alsi10mg-f0-0001/derived/fan_housing_alsi10mg_f0.step \
  --report parts/993-eng-fan-housing-alsi10mg-f0-0001/evidence/engineering-screen.json
```

## Gates suivants

1. Scanner carter, turbine, moyeu, alternateur, tôlerie et joints assemblés.
2. Mesurer alésage, concentricité, datums, jeux de pale et tolérances thermiques.
3. Instrumenter débit, pression, fuite, températures, régime, vibrations et belt load.
4. Reconstruire les conduits et exécuter CFD/CHT avec courbe ventilateur mesurée.
5. Exécuter FEA assemblée, modal/harmonique, fatigue et confinement de pale.
6. Comparer fonderie, fabrication usinée et LPBF avec coût/qualité complets.
7. Qualifier orientation, supports, T6, HIP, usinage, CT, FPI et endurance.

PhysicsNeMo reste différé jusqu'à l'existence de jeux CFD/CHT/structure/modal
corrélés, avec entraînement, validation, holdout et hors distribution séparés.
Le F0 est interdit de fabrication, rotation, installation et mise en route.
