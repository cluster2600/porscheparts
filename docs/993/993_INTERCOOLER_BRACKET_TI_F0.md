# Support d'intercooler 993 Ti-6Al-4V — jumeau F0

## Verdict

Le support d'intercooler est un **candidat LPBF conditionnel**, pas une pièce
prête à imprimer. Sa forme F0 consolide un cadre ouvert, deux oeillets et un
plot central dans un seul solide, sans cavité de poudre. Toutefois, la forme
actuelle reste largement plane et accessible à une découpe suivie d'usinage.
La LPBF ne sera retenue que si une géométrie mesurée et des charges réelles
justifient une optimisation topologique ou une consolidation impossible à
obtenir économiquement par tôlerie ou CNC. Pour la forme F0 actuelle, la voie
provisoire inscrite au catalogue est donc la CNC.

PorscheFanatics établit les références `99311011050` et `99311011052` et leur
place dans le circuit de suralimentation. FVD déclare une enveloppe
`255 × 80 × 23 mm` et une masse de `200 g` pour son support renforcé. Ces
sources ne fournissent ni les entraxes, ni les alésages, ni les surfaces de
contact. Tous ces détails restent donc des hypothèses du projet.

## Géométrie et matière

- maître éditable : `build123d` ;
- échange dimensionnel : STEP, solide OCCT unique ;
- enveloppe reproduite : `255 × 80 × 23 mm` ;
- volume CAO : `41 869,513 mm³` ;
- masse calculée avec `ρ = 4,42 g/cm³` : `185,063 g` ;
- matériau candidat : Ti-6Al-4V Grade 5 LPBF ;
- carte élastique de criblage : `E = 110 GPa`, `ν = 0,31` ;
- référence de comparaison : `Rp0,2 = 828 MPa` corroyé, jamais un admissible
  LPBF.

## Modèles mathématiques

Le criblage analytique existant applique une charge centrale synthétique
`F = 400 N` sur une portée `L = 220 mm` :

```text
A = n b t
I = n b t³ / 12
Mmax = F L / 4
sigma = Mmax (t/2) / I
tau_max = 1,5 F / A
sigma_VM = sqrt(sigma² + 3 tau²)
delta = F L³ / (48 E I)
delta_L = alpha L delta_T
```

Il donne `σVM = 229,422 MPa`, `δ = 2,801 mm` et une dilatation libre de
`0,2376 mm` pour `ΔT = 120 K`. Ce modèle de poutre remplace la forme réelle par
deux bandes de 8 mm et ne représente pas les concentrations locales.

## Calcul CalculiX exécuté

Le STEP exact a été maillé par Gmsh 4.12.1 avec des tétraèdres quadratiques
C3D10, puis résolu par CalculiX 2.21. L'oeillet gauche est bloqué en XYZ,
l'oeillet droit est un appui glissant en X et la charge totale de `400 N` est
répartie sur le dessus du plot central. Appuis, charge et direction sont des
conditions de régression non mesurées.

| Taille cible | Noeuds | C3D10 | p95 von Mises | p99 | Maximum local | Flèche max. |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5,0 mm | 8 132 | 3 730 | 69,156 MPa | 90,817 MPa | 232,178 MPa | 1,18565 mm |
| 3,5 mm | 13 352 | 6 311 | 68,056 MPa | 90,153 MPa | 253,708 MPa | 1,19357 mm |
| 2,5 mm | 29 854 | 15 419 | 73,006 MPa | 94,116 MPa | 328,332 MPa | 1,21033 mm |

Entre les deux maillages les plus fins, la variation vaut `6,78 %` sur le p95
et `1,38 %` sur la flèche, sous le seuil de régression de `10 %`. Le maximum
local continue en revanche d'augmenter ; il ne doit pas être présenté comme
convergé. Le p95 fin vaut `31,8 %` du résultat analytique nominal, tandis que
le maximum local vaut `143,1 %` de ce résultat. Cette différence confirme que
le calcul de poutre est utile comme ordre de grandeur, pas comme substitut CAE.

Les maillages, decks et champs restent hors Git. Le rapport public conserve
leurs tailles et SHA-256 dans
[`calculix-screen.json`](../../parts/993-eng-intercooler-bracket-ti-f0-0001/evidence/calculix-screen.json).

## Conversion OpenUSD

La passe `conversion-only` du workflow NVIDIA a utilisé l'image
`simready-workflow` verrouillée, `usd-convert-cad 0.2.0`, SimReady Foundation
`v2026.04.1` et le runtime de validation épinglé. Le USD dérivé :

- conserve l'enveloppe `255 × 80 × 23 mm` ;
- possède un `defaultPrim`, un axe Z et `metersPerUnit = 0,001` ;
- contient un mesh et passe les huit contrôles USD minimum ;
- ne contient aucun corps rigide, collider ou joint ;
- ne porte aucune carte physique Ti-6Al-4V qualifiée.

Le fichier USD reste un artefact reproductible hors Git ; son nom, sa taille et
son SHA-256 sont enregistrés dans
[`simready-conversion-summary.json`](../../parts/993-eng-intercooler-bracket-ti-f0-0001/evidence/simready-conversion-summary.json).
Cette réussite ne constitue pas une conformité SimReady complète.

## Reproduction

```bash
python3 parts/993-eng-intercooler-bracket-ti-f0-0001/source/intercooler_bracket.py \
  --out parts/993-eng-intercooler-bracket-ti-f0-0001/derived/intercooler_bracket_ti_f0.step \
  --report parts/993-eng-intercooler-bracket-ti-f0-0001/evidence/engineering-screen.json

python3 twins/993-intercooler-bracket-ti-f0/source/run_calculix_screen.py \
  --step parts/993-eng-intercooler-bracket-ti-f0-0001/derived/intercooler_bracket_ti_f0.step \
  --work-root /SORTIE_PRIVEE/993-intercooler-bracket \
  --mesh-sizes 5.0,3.5,2.5 \
  --report parts/993-eng-intercooler-bracket-ti-f0-0001/evidence/calculix-screen.json
```

La seconde commande doit s'exécuter dans un environnement contenant Gmsh et
CalculiX. L'image locale employée est identifiée dans le rapport ; aucun digest
de registre portable n'est revendiqué pour cette CAE.

## Portes restant fermées

- géométrie et tolérances des trois interfaces ;
- masse de l'intercooler, efforts des durites, accélérations et précharges ;
- température moteur, contraintes thermiques, vibration et fatigue ;
- carte matière LPBF liée à la machine, l'orientation et au traitement ;
- stratégie de supports, HIP, usinage, CT et isolation galvanique ;
- comparaison chiffrée CNC/tôlerie/LPBF ;
- essais statiques, vibratoires, thermiques et montage véhicule ;
- revue professionnelle et autorisation de fabrication.

PhysicsNeMo reste hors périmètre : trois maillages d'un même cas synthétique ne
forment ni un dataset corrélé ni un domaine d'apprentissage admissible.
