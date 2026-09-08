# Console de filtre à huile moteur 993 — AlSi10Mg F0

Ce vingtième candidat est une console moteur à deux galeries d'huile intégrées.
L'intérêt de la fabrication additive est précis : créer deux trajets non
colinéaires, le socle du filtre et les ports dans un seul corps, sans bouchons
de perçage transversal. Une fonderie ou un usinage 6061-T6 avec bouchons reste
cependant une solution concurrente à comparer.

PorscheFanatics identifie `993 107 057 00` et `993 107 057 01` comme consoles à
la position 44 du groupe `101-10`, puis le filtre moteur `993 107 203 03` et sa
réponse MAHLE `OC 229` à la position 48. OEMVWShop déclare `0,78 kg` pour la
console `...01`, sans protocole. La fiche OC 229 donne `Ø76 × 101 mm`,
`M20×1,5`; les données distributeur ajoutent `Ø72/62 mm`, `20 Nm` et `333 g`.
Ces valeurs définissent le composant accouplé, pas la console.

## Géométrie F0

Le maître build123d est entièrement indépendant : corps `130 × 90 × 20 mm`,
socle de filtre `Ø82 mm`, bossage non fileté `Ø20 mm`, quatre perçages
synthétiques et deux ports `Ø16 mm`. Deux galeries inclinées et décalées relient
les ports à une entrée annulaire et à une sortie centrale `Ø12 mm`.

Le STEP relu dans l'image CAO verrouillée contient un solide BREP valide de
`144 × 90 × 50 mm`, deux galeries, quatre ouvertures fonctionnelles et aucun
volume de poudre fermé. Son volume vaut `314 735,40 mm³` et sa masse théorique
AlSi10Mg `840,34 g`. Le parallélépipède enveloppe pèserait `1 730,16 g`, soit
un rapport brut/F0 de `2,06`.

La masse F0 vaut `1,073 ×` les `780 g` commerciaux, mais cette proximité ne
valide rien : ni frontière de pesée, ni surface, ni matière OEM ne sont connues.

## Hydraulique chaud/froid

Le scénario de régression impose `30 L/min`, huile à `850 kg/m³`, rugosité
effective `0,05 mm` et trois tronçons `16/12/16 mm`. Il utilise :

`v = Q/A`, `Re = ρvd/μ`

`f = 64/Re` en laminaire, sinon l'approximation de Haaland,

`Δp = Σ[(fL/d + K)ρv²/2]`

L'occurrence OCR du manuel indique environ `6,5 bar` à `5 000 tr/min` et
`90 °C`, sans vérification visuelle. Le seuil de régression est arbitrairement
fixé à 5 %, soit `32,5 kPa`.

- chaud, `μ = 0,012 Pa·s` : `28,82 kPa`, rapport `1,128` — **passe** ;
- froid, `μ = 0,25 Pa·s` : `44,65 kPa`, rapport `0,728` — **échoue**.

Le calcul omet le média filtrant, la soupape de dérivation, les vraies pertes
locales, les raccords et le circuit moteur. Il ne prédit donc pas la pression
d'huile du véhicule.

## Pression, filtre et thermique

À une épreuve synthétique de `12 bar`, l'écran membrane
`σ = pd/(2t)` avec `d = 16 mm` et `t = 4 mm` donne `2,4 MPa`, soit un rapport
ambiant à la limite de `102,08`.

Le couple publié du filtre est traité par `F = T/(Kd)` avec `K = 0,20`, donc
`5 000 N`. Sur un anneau synthétique `Ø72/62`, la pression moyenne vaut
`4,751 MPa`. Un engagement supposé de `12 mm` donne `22,97 MPa` de Von Mises
sur le filet simplifié et un rapport `10,67`. Ces deux écrans passent, mais ne
valident ni le filet réel ni le joint.

À `150 °C` depuis `20 °C`, la croissance libre sur `144 mm` vaut `0,393 mm`.
Totalement contrainte, `σ = EαΔT` atteint `191,1 MPa`, soit un rapport `1,282`
contre le seuil `1,5` — **échec**.

## Décision F0

La consolidation des galeries justifie l'étude LPBF, mais l'écran hydraulique
à froid et l'écran thermique échouent. Le procédé reste indécis entre fonderie,
CNC 6061-T6 avec bouchons qualifiés et LPBF AlSi10Mg. La propreté interne est
un gate majeur : absence de poudre prisonnière ne signifie pas dépoudrage ou
propreté moteur validés.

## Reproduction

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/work" -w /work \
  ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57 \
  python parts/993-eng-oil-filter-console-alsi10mg-f0-0001/source/oil_filter_console.py \
  --out parts/993-eng-oil-filter-console-alsi10mg-f0-0001/derived/oil_filter_console_alsi10mg_f0.step \
  --report parts/993-eng-oil-filter-console-alsi10mg-f0-0001/evidence/engineering-screen.json
```

## Gates suivants

1. Scanner la console, le carter, le filtre, les joints, capteurs et conduites.
2. Contrôler visuellement dans le manuel les pressions et conditions exactes.
3. Mesurer débit, viscosité, pression pulsée, températures et contamination.
4. Reconstruire les galeries et interfaces sur datums et tolérances mesurés.
5. Exécuter CFD/CHT, cavitation, pression pulsée, contact, modal et fatigue.
6. Comparer fonderie, CNC+bouchons et LPBF sur coût, masse, fuite et propreté.
7. Qualifier orientation, T6/HIP, usinage, CT, FPI, épreuve, fuite et rinçage.
8. Passer un banc hydraulique chaud/froid, puis endurance moteur et dyno.

PhysicsNeMo reste différé jusqu'à l'existence de séries CFD/CHT/structure/fuite
corrélées et séparées en entraînement, validation, holdout et hors distribution.
Le F0 est interdit de fabrication, circulation d'huile, montage et moteur.
