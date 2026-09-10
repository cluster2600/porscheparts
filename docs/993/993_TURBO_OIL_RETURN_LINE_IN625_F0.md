# Conduite de retour d'huile turbo — concept IN625 F0

Cette pièce est un bon candidat de présélection additive : une conduite courbe
de faible série peut réunir tube et brides, supprimer des soudures et être
adaptée à un espace moteur mesuré. Elle est aussi un bon exemple de cas où
l'impression 3D ne doit pas être choisie trop tôt.

Patrick Motorsports vend un jeu gauche/droit pour 993 Turbo `1996–1997`, entre
pompe à huile et réservoir, avec une forme annoncée contre le retour d'huile.
Le fabricant demande de monter côté carter puis d'ajuster la ligne vers le
turbo. PorscheFanatics classe ce circuit parmi les points à améliorer.

Aucune source ne publie dimensions, matière, paroi, pression, température ou
débit. Le F0 représente donc un seul côté entièrement synthétique ; la référence
commerciale `TUR 993 107 338 53 PMS` n'est pas traitée comme un numéro Porsche.

## Géométrie F0

Le maître build123d crée un tube balayé de `12,7 mm` extérieur, `1,2 mm` de
paroi, `10,3 mm` intérieur, sur une ligne centrale supposée de `175 mm`. Deux
brides circulaires `30 × 4 mm` et quatre perçages sont intégrés.

Le STEP relu contient un seul solide BREP valide avec un passage interne
continu. Son enveloppe vaut `140 × 60 × 94 mm`, son volume `11 985,86 mm³` et
sa masse IN625 théorique `101,16 g`. Ces valeurs décrivent le concept, pas la
pièce commerciale.

## Hydraulique

Le point synthétique utilise `2 L/min` d'huile à `120 °C`, densité
`850 kg/m³`, viscosité dynamique `0,015 Pa·s`, une remontée de `90 mm` et un
coefficient de pertes singulières `K = 4`.

`v = Q/A`, `Re = ρvD/μ`, puis, puisque `Re = 233`, `f = 64/Re`.

La perte est calculée par :

`Δp = f(L/D)ρv²/2 + Kρv²/2 + ρgΔz`

Le résultat vaut `1,339 kPa`, soit un rapport `3,734` face au seuil synthétique
de `5 kPa / 1,5`. Cet écran passe, mais il est monophasique : l'huile aérée,
les pulsations, la pompe de balayage et le retour diphasique sont absents.

## Pression et flexion

À `0,3 MPa`, les formules de paroi mince donnent `1,288 MPa` en circonférentiel,
`0,644 MPa` en axial et `1,115 MPa` de von Mises. Avec un effort transversal
synthétique de `100 N` sur `120 mm`, la contrainte combinée vaut `27,41 MPa`.
Le rapport à Rp0,2 ambiant `640 MPa` vaut `23,35` : cet écran passe largement.

Il ne couvre ni coude, ni pied de bride, ni défaut LPBF, ni contrainte
résiduelle, ni vibration. La pression d'éclatement algébrique n'est donc pas
une pression autorisée.

## Thermique et souplesse

EOS IN625 M 290 `40 µm` fournit la comparaison mécanique. La densité et les
constantes thermiques proviennent du bulletin IN625 corroyé Special Metals et
ne sont pas une carte admissible LPBF à chaud.

Entre `20` et `600 °C`, la dilatation libre de la ligne serait `1,391 mm`.
Totalement bloquée, la borne `σ = EαΔT` atteint `1 620,98 MPa`, soit un rapport
de seulement `0,395` : **échec**. Pour conserver le seuil `1,5`, le modèle
indique que la fraction effective de blocage axial devrait rester sous `0,263`.

La puissance de conduction pure par la paroi atteint une borne irréaliste de
`39,6 kW` parce que les résistances convectives huile/gaz sont omises. Elle
prouve seulement qu'une CHT avec cokéfaction et vraie température de peau est
nécessaire.

## Décision F0

La conduite passe les écrans hydrauliques et de membrane, mais échoue si elle
est thermiquement contrainte. Surtout, le produit existant doit être ajusté au
montage : une ligne LPBF rigide n'a aucun sens avant la mesure des deux voitures
types, des mouvements moteur-turbo et des interfaces.

Le procédé de référence reste donc **indécis** entre tube formé/soudé et LPBF
IN625. L'AM n'est intéressante que si la consolidation, l'encombrement mesuré,
la propreté interne et la répétabilité compensent réellement le coût et la
perte d'ajustabilité.

## Reproduction

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/work" -w /work \
  ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57 \
  python parts/993-eng-turbo-oil-return-line-in625-f0-0001/source/turbo_oil_return_line.py \
  --out parts/993-eng-turbo-oil-return-line-in625-f0-0001/derived/turbo_oil_return_line_in625_f0.step \
  --report parts/993-eng-turbo-oil-return-line-in625-f0-0001/evidence/engineering-screen.json
```

## Gates suivants

1. Scanner les deux lignes et leurs interfaces dans plusieurs positions moteur.
2. Mesurer débit, huile aérée, pression, température, drainage et retour.
3. Mesurer mouvements relatifs, température de peau, flux et vibration.
4. Construire CFD diphasique, CHT et FEA flexible avec corrélation banc.
5. Comparer tube formé/soudé et LPBF sur masse, coût, fatigue et ajustabilité.
6. Qualifier paroi, supports, dé-poudrage, traitement, usinage et propreté.
7. Passer CT, pression, fuite, éclatement, débit, cyclage et vibration.

PhysicsNeMo reste différé jusqu'à l'existence de séries CFD/CHT/structure
corrélées avec holdout et cas hors distribution. Toutes les autorisations de
fabrication, huile, turbo, moteur et véhicule restent fermées.
