# Porsche 917 — F42.1, optimisation thermique sans modifier l'enveloppe

## Verdict

F42.1 ne valide ni une CHT ni une culasse imprimable. Elle quantifie, sur le
solide F41 exact déjà discrétisé, l'effet de la convection et de la conductivité,
puis confronte ces résultats à une méthode analytique indépendante. Aucune des
cinq options examinées ne respecte simultanément `Tmax <= 260 °C` et
`Delta p <= 6,7 kPa`.

L'enveloppe externe F41 reste inchangée. Les carénages, déflecteurs et surfaces
internes supplémentaires sont des variables d'étude; leur CAO, leurs jeux et
leurs pertes singulières ne sont pas validés.

## Méthode A — CalculiX réellement exécuté

Le même maillage voxel F41 est utilisé pour tous les cas : 85 334 éléments
`DC3D8`, 99 391 noeuds et le SHA STL
`2c1af796e851b680f67fd28b780d4b00fb8115efcf7e25a30d99361e6da1ac81`.
Les 21 397 faces du film d'air externe reçoivent successivement 150, 300, 450,
650, 900, 1 500 et 3 000 W/m²K. Le point F42 publié à 215,76 W/m²K est conservé,
et deux calculs supplémentaires appliquent une conductivité multipliée par
0,8 et 1,2.

| h (W/m²K) | Tmax (°C) | p95 (°C) |
|---:|---:|---:|
| 150,00 | 616,9 | 492,5 |
| 215,76 | 542,2 | 414,4 |
| 300,00 | 483,8 | 353,8 |
| 450,00 | 423,0 | 290,9 |
| 650,00 | 377,7 | 246,4 |
| 900,00 | 344,8 | 216,1 |
| 1 500,00 | 304,6 | 180,8 |
| 3 000,00 | 267,5 | 148,9 |

À h=215,76 W/m²K, multiplier la conductivité provisoire par 0,8 porte Tmax à
593,0 °C; la multiplier par 1,2 l'abaisse à 507,0 °C. La carte matériau reste
non qualifiée au-dessus de 300 °C : ces nombres sont des écrans de sensibilité,
pas une autorisation matériau.

Un ajustement monotone `T = a + b h^-n` sur les huit points de convection donne
une erreur RMS de 1,46 °C sur Tmax et 2,14 °C sur p95. Il estime h=3 383 W/m²K
pour Tmax=260 °C, au-delà du dernier point réellement calculé; cette valeur est
donc une extrapolation. Pour p95, le seuil ajusté est 584 W/m²K, cohérent avec le
passage réel entre 450 et 650 W/m²K.

## Méthode B — réseau conservatif et Gnielinski/Darcy

La seconde méthode réutilise les 26 passages réduits F42 et calcule h par
Gnielinski, la perte linéaire par Darcy-Weisbach, puis un réseau
air-racine-pont. Elle est indépendante de CalculiX, mais emploie de façon
optimiste toute la surface du scan (0,179816 m²) comme surface mouillée.

Ce réseau demande :

- h=1 375,9 W/m²K à aire nominale pour atteindre 260 °C ;
- ou 1,1467 m² de surface, soit 6,377 fois la surface nominale, à
  h=215,76 W/m²K ;
- la conversion de h=1 375,9 W/m²K en débit incompressible donne 6,37 kg/s par
  tête, 584 m/s et 74,6 kPa.

Ce dernier point dépasse Mach 0,3 (Mach calculé 1,66). La corrélation
incompressible n'est plus acceptable : 74,6 kPa est seulement un indicateur
d'impossibilité, pas une perte de charge de conception. L'extrapolation
CalculiX à h=3 383 W/m²K demanderait formellement 19,36 kg/s et 563,5 kPa, à
Mach 5,05; elle est encore moins physiquement utilisable.

Le contrôle croisé h hérité de F42 reste à 6,45 % entre Gnielinski et le canal
OpenFOAM F38 convergé, donc sous 20 %. Il ne concerne pas la tête F41 complète.
La divergence de perte de charge reste 57,3 %, donc le critère de 20 % échoue.

## Options comparées

Les pertes ci-dessous sont des bornes basses de canal droit : les pertes des
déflecteurs et des ailettes ajoutées ne sont pas incluses.

| Option | h équivalent (W/m²K) | Delta p min. (kPa) | T pont réseau (°C) | Tmax surrogate CalculiX (°C) |
|---|---:|---:|---:|---:|
| F41, capture 70 % | 215,8 | 1,09 | 370,7 | 540,7 |
| carénage/déflecteurs, capture 100 % | 284,1 | 2,04 | 339,5 | 491,1 |
| surface interne +25 % | 269,7 | 1,09 | 344,7 | 499,9 |
| conductivité +20 % | 215,8 | 1,09 | 330,9 | 506,2 |
| combinaison capture 100 %, aire +25 %, k +20 % | 355,1 | 2,04 | 279,9 | 421,3 |

La combinaison est la meilleure température de l'étude, mais reste à 279,9 °C
dans le réseau et 421,3 °C dans le surrogate CalculiX. Aucun `PASS` thermique
n'est revendiqué. Les valeurs du surrogate pour les options ne sont pas des
CalculiX de géométries modifiées.

## Reproductibilité et limites

Préparer les decks locaux, exécuter chaque dossier avec CalculiX, puis publier :

```bash
python3 twins/reference-917-engine/source/run_f42_1_thermal_optimization.py prepare
docker run --rm --platform linux/arm64 -v "$PWD:/repo" \
  -w /repo/work/917-f42-1-thermal-optimization/<cas> \
  --entrypoint bash 3dprinting993-cae-aircooled-f34:dev \
  -lc 'ccx -i head-f42-1-thermal > log.ccx 2>&1'
python3 twins/reference-917-engine/source/run_f42_1_thermal_optimization.py summarize
make 917-f42-1-thermal-optimization-check
```

CalculiX résout ici une conduction séquentielle avec films moyens; il ne reçoit
pas un champ local OpenFOAM. Le cas OpenFOAM exact F41 n'est pas accepté et
aucune CHT tête entière n'est terminée. L'échelle absolue, les interfaces, la
carte matériau à chaud, la carte ventilateur/fuites et la corrélation par
thermocouples restent non validées. Impression métal et démarrage moteur restent
interdits.

