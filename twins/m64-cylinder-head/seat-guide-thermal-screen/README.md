# Serrages siège/corps et guide/corps — écran thermique M64 4V V2

**Résultat : aucun serrage de fabrication ne peut encore être retenu.** Les
calculs montrent une sensibilité suffisante à la dilatation différentielle pour
perdre l'interférence dans certaines hypothèses. Ils ne démontrent ni la perte
réelle d'un siège, ni sa rétention moteur. Aucun matériau n'est sélectionné.

Le [rapport reproductible](report.json) comporte 48 lignes de sensibilité aux
extrémités documentées de température, trois cas de températures différentes
insert/corps et 12 cas d'anneaux normalisés. **Aucune CAO n'a été modifiée.**

## Données réelles et hypothèses

Les diamètres viennent des profils du [module V2 indépendant](../source/build_four_valve_distribution.py)
et sont en **mm de conception**, pas en unités du scan. Le STEP fermé est lié
par SHA-256 `fac380b277add2e3d265d7fa8265baeb0ce460b9f69075730d14ece555e76a76`.

| Pièce, deux exemplaires par culasse 4V | Ø extérieur | Référence de serrage diamétral à froid |
|---|---:|---:|
| Siège admission | 43 mm | 0,060–0,100 mm, référence MAHLE générique |
| Siège échappement | 36 mm | 0,050–0,090 mm, référence MAHLE générique |
| Guide admission / échappement | 11 mm | **Inconnue** |

La page PDF 30 / imprimée 28 de [MAHLE, Valve Train Components](https://www.mahle-aftermarket.com/media/homepage/facelift/media-center/product-catalogs/mahle_valve_train_components_catalog_2025_screen_v002.pdf)
a été relue visuellement : les plages concernent le diamètre extérieur du siège
et son logement dans une culasse aluminium. MAHLE avertit du risque de
déformation et de fissuration entre sièges si le serrage est excessif. Ce ne sont
pas des spécifications M64 4V turbo ou LPBF. Le montage est décrit à température
ambiante, sans valeur exacte de température. **Les jeux diamétraux tige/guide
CAO de 0,030/0,040 mm ne sont pas des serrages guide/corps.**

Les [coefficients CP1 déjà sourcés](../cp1-hot-points-supplement-20260907.json)
sont uniquement des coefficients moyens sur des intervalles. Les états de
traitement, l'orientation et les incertitudes associés aux coefficients ne sont
pas précisés. Deux jeux documentaires restent séparés :

- Constellium Formnext 2021 : 25,19 × 10⁻⁶/K sur 20–200 °C.
- EOS : 19, 21 et 22 × 10⁻⁶/K sur 25–100, 25–200 et 25–300 °C.

Aucune interpolation, extrapolation ou fusion n'est faite. Chaque cas suppose
que ses dimensions à froid sont référencées à son propre T₀ (20 ou 25 °C),
sans transformer une même pièce entre ces références. Ni CP1 ni sa fiche
récente ne deviennent un matériau qualifié par cet écran.

**Hypothèses de sensibilité, pas propriétés de matériaux :** coefficient moyen
de l'insert égal à 10, 15 ou 20 × 10⁻⁶/K. Cette grille ne constitue pas une borne
physique sur les aciers ou bronzes. Les températures choisies ne proviennent
pas d'une simulation CHT ni d'une mesure moteur.

## Calcul des diamètres libres

À la même référence T₀, on définit `I₀ = D_insert,0 − D_logement,0`.
Une valeur positive désigne une interférence **diamétrale**. Avec les
déformations thermiques libres d'ingénierie `εi` et `εh` :

```text
I(Ti, Th) = D_insert,0 (1 + εi) − (D_insert,0 − I₀) (1 + εh)
         = I₀ (1 + εh) + D_insert,0 (εi − εh)
I₀,contact_nul = D_insert,0 (εh − εi) / (1 + εh)
```

Pour un coefficient **moyen sur l'intervalle exact**, `ε = α_moyen (T − T₀)`.
Ce n'est pas l'intégration d'un coefficient instantané `α(T)`. `Ti` et `Th`
sont indépendants. `I < 0` signifie un jeu libre dans ce modèle ; `I = 0`
donne une pression de contact nulle dans l'anneau idéal, **pas une marge de
rétention acceptable**. Les tolérances se propagent aux coins des intervalles
indépendants : la fonction est multi-affine. Ce calcul utilise des flottants,
pas une arithmétique d'intervalles à arrondi dirigé.

Exemple à **Ti = Th = 200 °C**, insert hypothétique à 15 × 10⁻⁶/K :

| Référence corps utilisée séparément | Siège Ø43, I₀ = 0,060–0,100 | Siège Ø36, I₀ = 0,050–0,090 |
|---|---:|---:|
| Formnext, T₀ = 20 °C | **−0,01860 à +0,02158 mm** | **−0,01580 à +0,02438 mm** |
| EOS, T₀ = 25 °C | +0,01507 à +0,05522 mm | +0,01238 à +0,05253 mm |

Les différences de résultat ne justifient pas de choisir le jeu documentaire
le plus favorable. Elles justifient d'obtenir les dilatations du **même couple
matériau/processus/traitement** avant de dimensionner le serrage.

Dans le cas Formnext et insert hypothétique ci-dessus, le seuil de contact
nul vaut **0,07851 mm** pour le siège admission, **0,06573 mm** pour celui
d'échappement et **0,02009 mm** pour un guide Ø11. Ces valeurs ne sont **pas
des serrages recommandés**. Avec le corps à 200 °C et l'insert à 150/200/250 °C,
le seuil du siège admission devient respectivement 0,11062 / 0,07851 /
0,04641 mm : il faut les deux températures de contact, pas une température
unique attribuée à toute la culasse.

## Lamé : test local normalisé, pas calcul de résistance de la culasse

Le calcul utilise deux anneaux concentriques élastiques isotropes, de rayons
`a < b < c`, interface nominale `b`, bord externe **libre** `c`, contact sans
frottement, petits déplacements et **contrainte axiale nulle**. Les relations
d'équilibre radial et de Hooke sont contrôlées à partir des
[notes MIT, sections 2 et 4](https://ocw.mit.edu/courses/22-312-engineering-of-nuclear-reactors-fall-2015/eb49bc4f3e701be60ca651c5a109312f_MIT22_312F15_note_L4.pdf).
La compliance ci-dessous est dérivée pour `σz = 0` ; elle ne copie pas la
solution en déformation plane de la section 4.

```text
Ki = (b² + a²)/(b² − a²) − νi
Kh = (c² + b²)/(c² − b²) + νh
p  = max(0, I) / [2b (Ki/Ei + Kh/Eh)]
```

Le test indépendant reconstitue `σr = A − B/r²`, `σθ = A + B/r²`, puis les
déplacements par Hooke et vérifie `2(u_corps − u_insert) = I` : le facteur
radial/diamétral est ainsi contrôlé. Le rapport donne uniquement `p/Eh` et
des contraintes normalisées. Les véritables `E(T)`, `ν(T)` et rayons extérieurs
de logement manquent ; **pression et contrainte de culasse en MPa restent nulles
dans le rapport, au sens « non calculées », pas zéro**.

Pour un anneau inspiré du seul Ø intérieur minimal du siège admission,
`a/b = 35,6/43`, et les hypothèses sans matériau `Ei/Eh = 3`, `νi = νh = 0,3` :

| c/b hypothétique | Gain `(p/Eh)/(I/D)` |
|---|---:|
| 1,1 | 0,07994 |
| 1,5 | 0,21806 |
| 2,0 | 0,27378 |

Les sièges coniques et leur faible longueur ne sont pas des anneaux uniformes.
Pour les guides, ce modèle ne prédit pas encore la réduction du diamètre
intérieur après emmanchement ni son effet sur le jeu tige/guide.

## Deux soupapes contre quatre : limite essentielle du pont de 2 mm

V2 comprend quatre sièges et quatre guides. L'écart minimal de **2 mm entre
enveloppes extérieures de sièges** est contrôlé sur la CAO froide. Le corps
receveur n'existe pas encore dans ce module : ce n'est donc pas la preuve d'un
ligament de matière final de 2 mm. Le futur pont entre logements inclinés
subit les interactions de plusieurs frettages et les gradients thermiques.
**Il n'est pas axisymétrique ; on ne remplace pas ce pont par `c = b + 1 mm`.**

Pour la référence 2V, les diamètres de têtes de soupapes MAHLE ne fournissent
ni les Ø extérieurs des sièges, ni les logements. Aucune supériorité 4V/2V
en résistance ou dissipation n'est calculée avec ces données. Il faudra un
modèle 3D de contact couplé sur chaque architecture, à charges comparables.

## Prochaine décision et reproduction

Il faut maintenant les références/alloys des sièges et guides, les
dilatations et propriétés mécaniques à chaud du même état de fabrication,
les logements/tolérances à T₀ explicite, le serrage guide/corps, puis les
températures CHT de part et d'autre. Ensuite seulement : contact 3D avec
plasticité/relaxation, maintien sous pression/impact soupape et essais de
rétention/thermiques sur coupons. Augmenter simplement le serrage peut
aggraver la fissuration du pont. **Aucune autorisation d'impression ou moteur.**

Depuis la racine du dépôt, sans OCP, GPU, Kali ni service payant :

```sh
python3 twins/m64-cylinder-head/seat-guide-thermal-screen/screen.py
python3 -m unittest discover -s tests -p test_m64_seat_guide_thermal_screen.py -v
```

**11 tests exécutés et réussis** : définition des diamètres libres, température
séparée, seuil de contact, bornes, Hooke/Lamé, limites analytiques, contact
unilatéral, rejets d'entrées et liens SHA-256. Ce sont des vérifications du
calcul analytique et de ses sources, pas une validation physique du produit.
