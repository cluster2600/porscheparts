# F50 — criblage thermo-mécanique comparatif 2V / 4V

## Verdict

La campagne F50 a réellement exécuté **18 jobs CalculiX 2.21** sur six
maillages Gmsh : trois niveaux pour la version 2 soupapes et trois pour la
version 4 soupapes. Les trois indicateurs de convergence du couple
medium/fin passent pour les deux architectures.

Le résultat d'ingénierie reste néanmoins **rouge**. Au maillage fin, les deux
témoins dépassent 300 °C et leur contrainte thermo-élastique p95 dépasse même
la limite d'élasticité CP1 publiée à température ambiante. Une limite ambiante
n'est pas une limite admissible à chaud; elle n'est utilisée ici que comme
alarme optimiste.

Cette campagne n'est pas une FEA de culasse complète. Le maillage volumique de
la peau F43 est privé et n'est pas publié. F50 refuse donc de le remplacer par
une enveloppe inventée. Le domaine calculé est seulement un **témoin local
circulaire du pont de chambre**, à l'intérieur du bore de 90 mm, percé des
sections fonctionnelles circulaires F47. La peau extérieure F43 n'est ni
chargée, ni modifiée, ni approximée. Aucun ovale, aucune ellipse et aucun
redimensionnement anisotrope ne sont utilisés.

## Entrées verrouillées

Le contrat
[`thermomechanical-screen-f50.json`](../twins/reference-917-engine/thermomechanical-screen-f50.json)
verrouille par SHA-256 :

- le rapport de peau externe F43, dont on reprend uniquement l'aire totale
  publique et non la géométrie privée ;
- les architectures et sections circulaires F45/F47 ;
- une trace F46 complète par architecture, `Cd=0,72` et pas de vilebrequin
  `0,25°` ;
- le criblage matériau/process F49.

La F50 ne forme jamais une histoire de charge avec l'enveloppe point par point
F47. Chaque variante conserve l'identité d'une trajectoire F46 complète.

## Modèle mathématique

### Charges d'un cycle

Pour chaque trace complète, la pression mécanique est :

\[
p_g = \max_\theta p_{abs}(\theta)-101\,325\quad [\mathrm{Pa}].
\]

Le flux stationnaire du criblage est la moyenne signée sur les 720 degrés :

\[
\bar q = \frac{1}{720^\circ}\int_0^{720^\circ}q_w(\theta)\,d\theta.
\]

Le temps physique de la trace reste défini par :

\[
t=\frac{\theta}{6N},\qquad N=9\,000\ \mathrm{tr/min}.
\]

| Entrée F46 | 2V | 4V |
|---|---:|---:|
| Pression de pointe absolue | 20,139 MPa | 21,902 MPa |
| Pression de pointe relative | 20,038 MPa | 21,800 MPa |
| Flux moyen signé | 1,085 MW/m² | 1,149 MW/m² |
| Flux instantané maximal | 12,119 MW/m² | 13,028 MW/m² |

### Conduction

CalculiX résout sur le témoin :

\[
\nabla\cdot(k\nabla T)=0,
\]

avec `k = 187 W/(m·K)`, seule valeur CP1 publique de F49. Elle est maintenue
constante alors qu'elle n'est documentée qu'à température ambiante; la porte
« carte chaude » reste donc fermée.

La face chambre reçoit `q̄`. Les faces supérieure et périphérique reçoivent
une condition de Robin. Comme le témoin local omet les ailettes, la conductance
globale hypothétique est conservée par :

\[
h_{eq}=h_{air}\frac{A_{F43}}{A_{témoin}},
\]

avec `h_air = 250 W/(m²·K)`, `T_air = 80 °C` et
`A_F43 = 112 256,35 mm²`. Ce choix est une hypothèse de sensibilité et non une
CHT. Le bilan est contrôlé par :

\[
\varepsilon_Q=\frac{|Q_{entrée}-Q_{film}|}{|Q_{entrée}|}\le 2\%.
\]

### Structure

Le calcul C3D4 linéaire utilise :

\[
\nabla\cdot\boldsymbol\sigma=0,
\qquad
\boldsymbol\sigma=\mathbf C:
(\boldsymbol\varepsilon-\alpha(T-T_0)\mathbf I).
\]

Les hypothèses `E = 70 GPa`, `ν = 0,33` et
`α = 23×10⁻⁶ K⁻¹` ne proviennent pas d'une carte CP1 qualifiée F49. La rive
circulaire est encastrée; cette condition représente la continuité locale avec
la culasse et tend à majorer les contraintes thermiques. Le contact des sièges,
la précharge des goujons, la plasticité, le fluage et la relaxation ne sont pas
modélisés.

La contrainte équivalente publiée est :

\[
\sigma_{vm}=\sqrt{\frac12[(\sigma_1-\sigma_2)^2+
(\sigma_2-\sigma_3)^2+(\sigma_3-\sigma_1)^2]}.
\]

Le p95 principal exclut une bande fixe de 5 mm au voisinage de l'encastrement,
tout en conservant les maxima bruts dans le rapport.

### Proxy de fatigue

Faute de courbes HCF, LCF et TMF à chaud, F50 ne calcule ni durée de vie ni
dommage de Miner. Le seul indicateur est une demi-amplitude élastique
relâché-froid vers chargé-chaud :

\[
\sigma_a=\frac{\Delta\sigma_{vm}}{2},
\qquad
P_{SWT}^{*}=\frac{\sigma_a^2}{E}.
\]

Cet indicateur sert à comparer les architectures; son unité en MPa ne doit pas
être interprétée comme un critère de durée de vie.

## Résultats CalculiX

| Maillage | Variante | Tétraèdres | Tmin qualité | Tmax | p95 thermo-pression | Umax |
|---:|:---:|---:|---:|---:|---:|---:|
| 5,0 mm | 2V | 3 731 | > 0,38 | 382,87 °C | 777,98 MPa | 0,1926 mm |
| 3,5 mm | 2V | 10 164 | > 0,38 | 382,55 °C | 777,20 MPa | 0,1914 mm |
| 2,5 mm | 2V | 26 154 | 0,3895 | 382,48 °C | 769,46 MPa | 0,1973 mm |
| 5,0 mm | 4V | 3 809 | > 0,38 | 397,72 °C | 808,50 MPa | 0,1739 mm |
| 3,5 mm | 4V | 10 389 | > 0,38 | 397,31 °C | 786,76 MPa | 0,1796 mm |
| 2,5 mm | 4V | 25 864 | 0,3820 | 396,65 °C | 775,12 MPa | 0,1812 mm |

À pression seule sur la maille fine, le p95 vaut 53,54 MPa en 2V et
65,99 MPa en 4V. Le saut vers environ 770–775 MPa vient donc surtout de
l'expansion thermique empêchée par l'encastrement du témoin; il ne doit pas
être transposé tel quel à la culasse sans interfaces et contacts réels.

| Convergence medium → fin | Limite | 2V | 4V | Statut |
|---|---:|---:|---:|:---:|
| Tmax | 2 % | 0,0196 % | 0,1668 % | passe numérique |
| contrainte p95 | 10 % | 0,996 % | 1,479 % | passe numérique |
| Umax | 5 % | 2,996 % | 0,887 % | passe numérique |

Sur la maille fine, la 4V est plus chaude de 3,70 %, a un p95 supérieur de
0,74 %, un déplacement maximal inférieur de 8,14 % et un proxy SWT supérieur
de 1,48 %. Les deux variantes échouent néanmoins les écrans 300 °C et limite
d'élasticité ambiante.

## Reproduction

Le solveur ne détruit jamais un résultat existant. Il faut choisir un dossier
`work/` neuf :

```bash
make 917-thermomechanical-f50
make 917-thermomechanical-f50-publish
make 917-thermomechanical-f50-check
```

Le mode `solve` conserve localement les `.msh`, `.inp`, `.dat`, `.frd` et
`.npz`. Ils ne sont pas publiés. Le mode `publish` produit seulement le rapport
agrégé, les images de champs du témoin et leur manifeste :

- [`rapport agrégé`](../twins/reference-917-engine/evidence/f50-thermomechanical/thermomechanical-screen-report.json) ;
- [`champ 2V`](../twins/reference-917-engine/evidence/f50-thermomechanical/f50-local-deck-2v-fields.png) ;
- [`champ 4V`](../twins/reference-917-engine/evidence/f50-thermomechanical/f50-local-deck-4v-fields.png) ;
- [`convergence`](../twins/reference-917-engine/evidence/f50-thermomechanical/f50-local-deck-mesh-convergence.png) ;
- [`manifeste`](../twins/reference-917-engine/evidence/f50-thermomechanical/manifest.json).

## Ce qui bloque une validation de culasse

La convergence numérique du témoin ne ferme aucune des portes suivantes :

1. maillage solide complet lié à la même peau F43 pour 2V et 4V ;
2. surfaces chambre, ailettes, sièges, guides et goujons vérifiées sur la CAO ;
3. carte CP1 dépendante de la température avec plasticité, fluage et
   relaxation, issue des coupons du procédé exact ;
4. contacts, interférences de sièges/guides, précharges et cycle transitoire ;
5. CHT corrélée, thermocouples, pression cylindre et fatigue TMF ;
6. CT/CND, étanchéité, banc de flux et banc moteur.

En conséquence, `manufacturing_authorized`, `metal_print_authorized` et
`engine_start_authorized` restent explicitement `false`.
