# Porsche 917 — recalcul du refroidissement de culasse F38

## Verdict

F38 améliore la définition du passage d'air et ferme numériquement le bilan
énergétique d'un **canal inter-ailettes canonique**, mais ne ferme pas le
refroidissement de la culasse. La température de pont projetée reste comprise
entre 375,8 et 381,2 °C, au-dessus de l'écran burst de 260 °C et de la plage
d'interpolation de la carte matière provisoire CP1, limitée à 300 °C.

```text
whole_head_CHT_complete = false
hot_material_coupon_card_qualified = false
metal_print_authorized = false
engine_start_authorized = false
```

Le volume B-Rep rectangulaire intermédiaire a été rejeté comme non fidèle au
scan. Les résultats OpenFOAM ci-dessous restent donc une étude de passage. La
projection globale utilise la surface de la peau F37 conforme au scan,
0,1848697 m² si une unité OBJ vaut un millimètre. Ce n'est pas une surface
mesurée sur un B-Rep F38 accepté.

## Définition candidate du refroidissement

Le passage retenu pour la prochaine vraie CHT comporte :

- 12 niveaux d'ailettes et 11 jeux par demi-banc, soit 22 passages équivalents ;
- épaisseur 2,0 mm, jeu 4,5 mm, pas 6,5 mm ;
- carénage à jeu 12 mm ;
- séparateur central et deux déflecteurs inclinés vers le pont échappement ;
- épaisseur minimale nominale des déflecteurs 1,8 mm ;
- direction héritée de F36 : `+y` vers `-y` dans le repère du scan.

L'aire ouverte de 0,008514 m² et la capture hypothétique de 70 % donnent
61,74 m/s dans les passages à 0,85 kg/s par tête. Le débit est l'hypothèse F34
historique conservée, pas une carte de soufflante mesurée.

## Conditions imposées sans recalage sur le résultat

| Paramètre | Valeur |
| --- | ---: |
| Air entrant | 308,15 K / 35 °C |
| Débit nominal par tête | 0,85 kg/s |
| Fraction captée, candidat | 70 % |
| Parois du canal CFD | 533,15 K / 260 °C |
| Charge thermique par tête | 4,30 kW |
| Pression totale soufflante disponible | 6,70 kPa |
| Écran température pont | 260 °C |

La charge de 4,30 kW est l'ordre de grandeur rétrodéduit du modèle solide F36.
Elle n'a pas été abaissée pour faire passer F38.

## Méthode A — OpenFOAM 14

Le cas résout un canal droit de 180 × 4,5 × 86 mm avec deux faces d'ailettes
isothermes et `noSlip`, deux plans de symétrie, un gaz parfait à propriétés
constantes et le modèle RANS k-ω SST. Il ne contient ni le contournement de la
culasse, ni les déflecteurs, ni la conduction solide : ce n'est pas une CHT.

| Maille | Cellules hexa | h effectif | Δp | Erreur masse | Erreur énergie |
| --- | ---: | ---: | ---: | ---: | ---: |
| coarse | 17 280 | 202,09 W/m²K | 1,692 kPa | 2,55×10⁻¹¹ | 1,694 % |
| fine | 138 240 | 201,84 W/m²K | 1,716 kPa | 3,17×10⁻¹¹ | 1,771 % |

La variation de `h` entre les deux mailles vaut 0,122 %, et les deux bilans
énergétiques ferment sous 5 %. Les sorties OpenFOAM exactes, les journaux et
les profils axiaux de température sont publiés avec leurs SHA-256.

## Méthode B — corrélation indépendante

La seconde méthode applique :

```text
Dh = 2 g W / (g + W)
Re = rho V Dh / mu
f = (0,79 ln(Re) - 1,64)^-2
Nu = [(f/8)(Re-1000)Pr] / [1 + 12,7 sqrt(f/8)(Pr^(2/3)-1)]
h = Nu k_air / Dh
eta_fin = tanh(m L_fin)/(m L_fin)
m = sqrt[2 h/(k_s t_fin)]
```

Avec `Re = 31 454`, elle donne `h_eff = 193,94 W/m²K` et une perte droite de
1,061 kPa. L'écart à OpenFOAM est de 4,08 % sur `h`, mais de 61,72 % sur
`Δp`. Le seuil conservateur de 20 % sur la pression échoue. L'accord sur `h`
ne constitue pas une validation physique.

## Réseau thermique non linéaire

La conduction chambre → pont → racine d'ailette est projetée avec une longueur
caractéristique de 8 mm et une section efficace de 1 200 mm². Ces deux valeurs
sont un écran conservateur, pas une géométrie mesurée. La conductivité CP1 est
la carte provisoire de F36 : 150 W/mK à 20 °C, 135 W/mK à 200 °C et
120 W/mK à 300 °C. Le solveur intègre `k(T)` :

```text
Q L / A = integral(T_root, T_bridge) k(T) dT
T_root = T_air + Q/(h A_wetted)
```

| Source de h | Racine ailette | Pont chambre | Écran 260 °C | Dans CP1 ≤300 °C |
| --- | ---: | ---: | --- | --- |
| OpenFOAM fine | 150,24 °C | 375,79 °C | échec | échec |
| Gnielinski + efficacité | 154,93 °C | 381,23 °C | échec | échec |

Les valeurs au-dessus de 300 °C utilisent une prolongation conservatrice de la
dernière conductivité et ne sont donc pas des prédictions matière qualifiées.

## Balayage des améliorations

| Variante | Capture | h effectif | Δp total estimé | T pont projetée | Décision |
| --- | ---: | ---: | ---: | ---: | --- |
| Sans carénage | 45 % | 144,67 W/m²K | 0,668 kPa | 427,9 °C | thermique rejetée |
| Carénage 12 mm | 60 % | 175,37 W/m²K | 2,077 kPa | 395,9 °C | thermique rejetée |
| Splitter + déflecteurs | 70 % | 193,95 W/m²K | 4,944 kPa | 381,2 °C | candidat CHT, thermique rejetée |
| Jets échappement agressifs | 78 % | 207,94 W/m²K | 9,855 kPa | 371,9 °C | pression et thermique rejetées |

Le splitter et les déflecteurs sont retenus uniquement pour la prochaine étude
CHT parce qu'ils maximisent `h` parmi les variantes qui respectent 6,70 kPa.
Ils ne sont pas sélectionnés pour fabrication.

## Travaux encore obligatoires

1. reconstruire un B-Rep fidèle à la peau du scan et mesurer sa surface réelle ;
2. créer le domaine d'air complet avec carénage, fuites et déflecteurs ;
3. lancer une vraie CHT solide–air avec `k(T)` issue des coupons F38 ;
4. ajouter contact sièges/guides, gaz cycliques, huile et rayonnement ;
5. corréler débit, pression et températures sur banc instrumenté ;
6. confirmer l'échelle et les interfaces moteur avant toute fabrication.

## Reproduction

```bash
python3 twins/reference-917-engine/source/run_f38_cooling_redesign.py \
  --contract twins/reference-917-engine/f38-cooling-redesign.json \
  --output work/917-f38-cooling --prepare

docker run --rm -v "$PWD:/workspace" -w /workspace \
  --entrypoint /bin/bash 3dprinting993-cae-aircooled-f34:dev \
  -lc 'source /opt/openfoam14/etc/bashrc && \
  twins/reference-917-engine/source/run_f38_openfoam_fin_channel.sh work/917-f38-cooling'

python3 twins/reference-917-engine/source/run_f38_cooling_redesign.py \
  --contract twins/reference-917-engine/f38-cooling-redesign.json \
  --output work/917-f38-cooling --summarize
```
