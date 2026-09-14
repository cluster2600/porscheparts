# Couvre-culasse supérieur 993 avec tours COP — AlSi10Mg F0

Ce candidat met à profit la fabrication additive pour consolider une coque
ouverte, six ailettes et trois supports de bobines coil-on-plug. PorscheFanatics
identifie précisément l'intégration COP comme l'intérêt du kit BBi et catalogue
plusieurs caches aluminium usinés.

FVD publie un kit complet de quatre caches, joints et visserie en aluminium
billet, avec une enveloppe commerciale `400 × 150 × 200 mm` et une masse
`3,32 kg`. Protomotive confirme une paire supérieure 993 Carrera/Turbo usinée
dans du `6061-T6`. Aucun de ces chiffres ne définit une pièce individuelle.

## Géométrie F0

Le maître build123d est donc entièrement propre : un cache supérieur ouvert de
`220 × 95 × 25 mm`, toit `3 mm`, bride latérale `6 mm`, dix perçages
synthétiques, six ailettes et trois tours COP. L'enveloppe totale atteint
`220 × 95 × 45 mm`.

Le STEP relu contient un solide BREP valide, une face huile ouverte, dix
perçages, trois passages COP et six ailettes. Son volume vaut
`181 143,43 mm³` et sa masse AlSi10Mg théorique `483,65 g`. Un parallélépipède
billet enveloppe pèserait `2 511,14 g`, soit un rapport théorique `5,19`.

Projeter quatre F0 donne `1,935 kg`, mais cette valeur ne peut pas être comparée
directement aux `3,32 kg` FVD : le kit réel contient des caches différents,
des joints et de la visserie.

## Pression et serrage

Le toit est criblé comme une bande simplement appuyée sous `20 kPa` :

`σ = 0,75 × p × a² / t²`

Pour `a = 45 mm` et `t = 3 mm`, la contrainte vaut `3,375 MPa`, soit un rapport
à la limite AlSi10Mg de `72,59`. Cet écran passe.

PorscheFanatics transcrit `9,7 Nm` pour un cache M6, mais la valeur OCR reste
non vérifiée. Avec le modèle provisoire `F = T/(Kd)` et `K = 0,20`, chaque
fixation donnerait `8,08 kN`. La pression moyenne de bande vaut `22,23 MPa` et
le pied de bride synthétique `134,72 MPa`, soit un rapport `1,819`. Ces calculs
ne constituent ni couple de montage ni preuve d'étanchéité.

## Trois échecs thermiques

À `200 °C` depuis `20 °C`, la croissance libre sur `220 mm` vaut `0,832 mm`.
Totalement contrainte, `σ = EαΔT` atteint `264,6 MPa` face à `245 MPa`, rapport
`0,926` : **échec**.

Un gradient synthétique de `50 K` à travers le toit donne :

`κ = αΔT/t`, puis `w = κL²/8`

Le voile estimé vaut `2,117 mm`, contre une cible de joint `0,10 mm`, rapport
`0,047` : **échec**. Ce modèle volontairement sévère montre que nervures,
séquence d'usinage et compensation de traitement sont indispensables.

Enfin, avec `h = 30 W/m²K`, les surfaces simplifiées rejettent `157,2 W` face à
une cible synthétique `300 W`, rapport `0,524` : **échec**. Il manque la
conduction vers la culasse, l'huile, le rayonnement et le débit d'air réel.

## Décision F0

La consolidation COP et la réduction de brut rendent l'AM intéressante, mais
le F0 ne tient pas ses écrans thermiques et aucune interface n'est mesurée. Le
procédé reste indécis entre injection d'origine, fonderie, billet 6061-T6 et
LPBF AlSi10Mg.

## Reproduction

```bash
docker run --rm --platform linux/amd64 -v "$PWD:/work" -w /work \
  ghcr.io/cluster2600/3dprinting993-cad-author-f28@sha256:18dbfa559306a31c909480695acf0e89a9bc904c83d280065c1d9d29036fec57 \
  python parts/993-eng-upper-valve-cover-alsi10mg-f0-0001/source/upper_valve_cover.py \
  --out parts/993-eng-upper-valve-cover-alsi10mg-f0-0001/derived/upper_valve_cover_alsi10mg_f0.step \
  --report parts/993-eng-upper-valve-cover-alsi10mg-f0-0001/evidence/engineering-screen.json
```

## Gates suivants

1. Scanner les quatre caches, joints, faces de culasse, bobines et faisceau.
2. Vérifier le couple primaire, la séquence et la loi réelle du joint.
3. Mesurer pression carter, températures, flux, huile, air et vibration.
4. Redessiner bride, nervures, évents et tours COP sur interfaces mesurées.
5. Exécuter CHT, contact joint non linéaire, modal, fatigue et relaxation.
6. Qualifier orientation, supports, T6, trempe, HIP, usinage et anodisation.
7. Passer CT, FPI, planéité, pression, fuite, cycle thermique et endurance.

PhysicsNeMo reste différé jusqu'à l'existence de séries CHT/structure/joint
corrélées, séparées en entraînement, validation, holdout et hors distribution.
Le F0 est interdit de fabrication, étanchéité, montage et moteur.
