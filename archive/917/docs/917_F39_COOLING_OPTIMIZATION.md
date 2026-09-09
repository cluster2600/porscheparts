# Porsche 917 — optimisation du refroidissement F39

## Verdict

F39 identifie **un candidat numérique à soumettre ensuite à une CHT de culasse
complète**. Il ne valide pas une pièce. Les 35 combinaisons qui franchissent
l'écran nominal utilisent toutes le plafond hypothétique de 1 200 W de chaleur
extraite localement par l'huile. Sans cette extraction, aucune combinaison ne
respecte `T_pont <= 260 °C`.

La géométrie retenue par l'algorithme comporte 14 niveaux d'ailettes de 2,4 mm,
un jeu libre de 3,5 mm, un rayon de pied de 4 mm, une portée moyenne de 100 mm et
le déflecteur `splitter12`. Ces dimensions sont des variables d'optimisation
conditionnelles à l'échelle du scan, et non des cotes Porsche certifiées.

## Frontière de preuve

Le calcul est indépendant de la reconstruction B-Rep F39. L'aire d'échange est
un proxy extrapolé depuis la surface extérieure du maillage scan-conforming F37
(`0,1848696736 m²` si l'unité du scan est le millimètre). Elle n'est pas une aire
mouillée extraite d'un B-Rep F39 accepté. Le volume d'air réel, les fuites du
carénage, les zones masquées, les contacts siège/guide et les galeries d'huile
ne sont donc pas représentés.

La méthode A n'est pas une nouvelle CFD pour chaque candidat : elle met à
l'échelle le résultat du canal OpenFOAM F38 à 138 240 cellules (`h=201,843
W/m²K`, `Δp=1 715,57 Pa`). La méthode B est indépendante de cet ancrage dans ses
équations primaires et applique Gnielinski, Darcy–Weisbach et une efficacité
d'ailette 1D. Les deux méthodes partagent nécessairement les mêmes hypothèses de
géométrie, propriétés d'air, débit et charge.

## Conditions aux limites

- air entrant : `308,15 K` ;
- débit nominal disponible par tête : `0,85 kg/s` ;
- charge thermique chambre nominale : `4 300 W` ;
- densité, viscosité, conductivité et Prandtl de l'air : respectivement `1,132
  kg/m³`, `1,9e-5 Pa.s`, `0,0273 W/mK` et `0,70` ;
- écran de pression : `Δp <= 6,7 kPa` pour les deux méthodes ;
- écran thermique : `T_pont <= 260 °C` pour les deux méthodes ;
- accord demandé : `|h_A-h_B|/h_B <= 20 %` ;
- conductivité CP1 provisoire : 150 W/mK à 20 °C, 135 W/mK à 200 °C, 120 W/mK
  à 300 °C, sans coupon à chaud ;
- huile locale : 0, 600 ou 1 200 W ; `c_p=2 200 J/kgK`, `ΔT=25 K`.

Les fractions de captage et pertes singulières des variantes `open`,
`shroud16`, `splitter12` et `exhaust_jets8` sont des hypothèses explicites du
contrat, pas une fan map mesurée.

## Modèles mathématiques

Pour `N_p=2(N_ailettes-1)` passages, le modèle utilise :

```text
A_ouverte = N_p × jeu × portée
V = débit × fraction_captée / (rho × A_ouverte)
D_h = 2 × jeu × portée / (jeu + portée)
```

La méthode A applique des lois d'échelle documentées :

```text
h_A = h_ref (V/V_ref)^0,8 (D_h/D_h,ref)^-0,2 × eta/eta_ref
Δp_A = Δp_ref (V/V_ref)^2 (D_h/D_h,ref)^-0,25 (L/L_ref) + K rho V²/2
```

La méthode B emploie :

```text
f = (0,79 ln(Re) - 1,64)^-2
Nu = [(f/8)(Re-1000)Pr] / [1+12,7 sqrt(f/8)(Pr^(2/3)-1)]
h_B = Nu k_air/D_h × eta
Δp_B = f L/D_h × rho V²/2 + K rho V²/2
eta = tanh(m L_ailette)/(m L_ailette)
```

Le réseau thermique conservatif impose `Q_total=Q_air+Q_huile`, calcule
`T_racine=T_air+Q_air/(h A_proxy)`, puis résout la conduction non linéaire :

```text
∫[T_racine,T_pont] k(T)dT = Q_air L_pont/A_pont
```

La loi `k(T)` est intégrée exactement par morceaux. Le rayon de pied augmente la
section conductrice du modèle de 6 % par millimètre ajouté. Cette relation reste
une hypothèse de criblage faute de section de pont mesurée.

## Plan d'expériences et résultats exécutés

Le script a évalué 1 728 combinaisons ; 432 respectent l'écran d'encombrement
conditionnel de 84 mm ; 35 franchissent les trois objectifs nominaux.

| Cas | `T_pont,max` | `Δp_max` | `h_A / h_B` | Verdict numérique |
|---|---:|---:|---:|---|
| candidat nominal, 0,85 kg/s, 4,3 kW, huile 1,2 kW | 230,83 °C | 4,991 kPa | 205,66 / 199,70 W/m²K | passe |
| meilleure variante sous contraintes air, huile 0 W | 315,83 °C | 4,991 kPa | idem | échoue T |
| meilleure variante sous contraintes air, huile 600 W | 272,36 °C | 4,991 kPa | idem | échoue T |
| hors-calage, 0,85 kg/s, 5,2 kW | 293,90 °C | 4,991 kPa | 205,66 / 199,70 W/m²K | échoue T |
| hors-calage, 1,05 kg/s, 4,3 kW | 222,02 °C | 7,617 kPa | dépend du débit | échoue Δp/débit |

L'écart relatif de `h` nominal vaut 2,99 % et celui de perte de charge vaut
7,03 %. Tous les cas géométriquement admissibles restent dans le domaine
turbulent utilisé par Gnielinski (`Re > 3 000`). L'extraction de 1 200 W
correspond à un débit d'huile théorique de `0,02182 kg/s` pour 25 K d'élévation.
Ce débit et ce coefficient d'échange ne sont pas validés par une géométrie
hydraulique.

## Fichiers et reproduction

```bash
python3 twins/reference-917-engine/source/run_f39_cooling_optimization.py \
  --contract twins/reference-917-engine/f39-cooling-optimization.json \
  --output work/917-f39-cooling-optimization
python3 tests/test_917_f39_cooling_optimization.py -v
```

Les preuves publiées comprennent le JSON complet, le CSV des 432 candidats
géométriquement admissibles, l'image de coupe fonctionnelle avec espace de
conception et une carte charge-débit/dépendance à l'huile.

## Décision fail-closed

L'écran numérique nominal autorise uniquement la préparation d'une prochaine
CHT de culasse. Restent faux : échelle absolue certifiée, B-Rep F39 accepté,
géométrie et échange d'huile validés, fan map et fuites mesurées, carte matière
issue de coupons à chaud, CHT culasse complète, fatigue thermomécanique,
corrélation physique, autorisation d'impression métal et autorisation de
démarrage moteur.
