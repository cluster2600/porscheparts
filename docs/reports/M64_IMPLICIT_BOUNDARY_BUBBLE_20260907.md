# Audit d'une déformation à bords conservés — 7 septembre 2026

## Résultat : champ initial rejeté, localisation numérique prometteuse

Le premier champ à exposants tous égaux à 2 est rejeté. Une recherche
numérique distincte, ensuite autorisée et limitée à 60 secondes, trouve un
champ localisé dont le maximum échantillonné vaut **0,850141**, inférieur
à la limite 1. Il reste un **candidat mathématique**, pas une CAO acceptée :
ni le corridor continu ni un solide modifié ne sont encore contrôlés.

**Suite de cet audit :** le champ 12 × 23 a été construit puis rejeté ;
un candidat de moindre degré 10 × 11 a ensuite franchi les contrôles CAO
locaux. Voir le [dossier consolidé de réparation Bernstein](M64_LOCAL_BERNSTEIN_REPAIR_20260907.md).
Le présent document conserve les résultats et limites de l'étape numérique
initiale.

## Premier champ rejeté avant construction CAO

L'audit exploite la **vraie face bilinéaire du STEP privé F53** et sa surface
voisine cylindrique. Il ne crée pas de géométrie de substitution. Le champ
testé peut conserver les cinq limites de manière analytique, mais il atteint
**3,285 unités du scan** à l'intérieur de la face découpée, alors que la
limite imposée pour cet essai est **1 unité**. Il est donc rejeté : aucun
nouveau patch, solide, STEP ou résultat physique n'est produit par cet audit.

La provenance reste une reconstruction de recherche issue du scan 935,
pas une culasse M64 dimensionnellement validée. Les unités du scan ne sont
pas assimilées à des millimètres certifiés.

## Hypothèse mathématique vérifiée sur la source

Quatre limites sont isoparamétriques. La cinquième, non isoparamétrique,
est partagée avec une **surface cylindrique analytique OCCT**, identifiée
par l'arête topologique commune ; il ne s'agit pas d'un cylindre ajusté à
une image. Les coordonnées, indices de faces et paramètres restent privés.

Pour la surface source bilinéaire `S0(u,v)`, avec `u,v` normalisés :

```text
F(X) = distance(X, axe du cylindre)^2 / rayon^2 - 1
E(u,v) = u(1-u)v(1-v)
D(u,v) = C E(u,v)^2 F(S0(u,v))^2
S1(u,v) = S0(u,v) + D(u,v) n
```

`n` est la direction du déplacement précédemment testé vers le passage
d'air. `C` impose `D = 0,85` au même point cible. Le polynôme a un bidegré
au plus `8 × 8` : aucune interpolation `BRepFill` n'est utilisée.

Les facteurs carrés imposent, en arithmétique exacte, une valeur et un
gradient nuls sur les quatre bords iso et sur `F = 0`. Cela conserverait la
surface et ses dérivées **le long de ces limites de la surface source** ;
ce n'est pas une affirmation de continuité G1 initiale de tout l'assemblage.
Les courbes OCCT sont évaluées numériquement, donc les résidus sont mesurés
séparément, sans les déclarer exactement nuls.

## Contrôles effectivement exécutés

- Projection du point cible sur la surface source : erreur `7,11e-15` unité.
- Au point cible : `F = 7,25825`, `E²F² = 0,0845102`, `C = 10,0580`.
  La normalisation n'est donc pas proche du seuil de singularité `1e-20`.
- Sur **121 points de la découpe cylindrique** : `|F|max = 1,63e-9`,
  `|D|max = 1,28e-18` unité ; dérivées normalisées maximales
  `1,66e-11` en U et `4,04e-11` en V.
- Sur **121 points de chacun des quatre bords iso** : `|D|max ≤ 8,42e-13`,
  dérivées normalisées maximales `7,67e-12`.

La sélection du domaine de la face utilise `BRepClass_FaceClassifier` sur
les paramètres de la surface originale, en conservant les états `IN/ON`.
Les points hors de la découpe ne contribuent pas aux maxima ci-dessous.

| Grille du domaine paramétrique | Points retenus dans la face | `max(abs(D))`, unités du scan | `max(abs(∂D/∂u))` | `max(abs(∂D/∂v))` |
|---|---:|---:|---:|---:|
| 41 × 41 | 1 597 | 3,27694 | 13,5117 | 18,6932 |
| 81 × 81 | 6 250 | 3,28468 | 13,5881 | 18,6938 |

Les dérivées sont par unité de paramètre normalisé, pas des pentes
dimensionnelles. Le rapport de projection du produit vectoriel des
dérivées déformées sur celui de la source reste positif aux points testés
(minimum `0,825486`). **Cela n'est pas un contrôle global d'auto-intersection**
et ne compense pas le dépassement d'amplitude.

La conversion des coefficients en base de Bernstein donne `11,9944`
comme maximum absolu de coefficients sur le rectangle paramétrique entier.
Cette borne flottante n'est pas arrondie par intervalles et concerne aussi
la partie non retenue par le rognage : elle n'est pas présentée comme une
borne certifiée du maximum sur la face. Les deux grilles ne constituent
pas non plus une démonstration de convergence ou un maximum global.
**Un seul point intérieur au-delà de 1 suffit néanmoins à rejeter ce champ.**

## Reproductibilité et intégrité

Script : `twins/m64-cylinder-head/audit_transition_implicit_constraint.py`.
Quatre tests unitaires vérifient le produit et la dérivation polynomiale,
l'annulation d'un facteur de bord, l'élévation linéaire vers Bernstein et
la normalisation/recherche bornée sur un champ symétrique synthétique.
Ils ne remplacent pas l'audit natif de la CAO.

Exécution réelle dans OCP sur Kali, limitée à deux CPU, 4 Gio et 300 s.
Rapport privé :

```text
/tmp/917-f50/out/m64-implicit-bubble-audit-20260907.json
SHA-256 55548191758d4bd9279d2057a80f787e1892a0114df01331fa43dbd7f12fecda
```

Le maître reste inchangé :
`700baea66bc72cdb6aee529e21b167270ebde11db94b06f8e1e55ee08bdd9bf2`.
Le rapport est laissé intact ; la protection contre la division par zéro
du script a ensuite été déplacée avant le calcul de `C`, sans changement
de la formule ni du résultat non singulier consigné ici.

## Recherche numérique de localisation, sans construction CAO

L'option `--localized-search` remplace le facteur de bord par
`u^p (1-u)^q v^r (1-v)^s`, toujours multiplié par `F²`, avec chaque exposant
entier entre 2 et 12. Les **14 641 combinaisons** sont comparées sur les
6 250 points retenus de la grille 81 × 81. La normalisation au point cible
reste fixée à 0,85 ; le critère maximal reste 1. Il n'y a ni relaxation du
seuil, ni déplacement du point, ni nouveau cylindre ajusté.

La meilleure combinaison sur cette grille est **(6, 2, 7, 12)**.
Son maximum est ensuite contrôlé sur une grille plus fine de la même face :

| Grille | Points retenus | `max(abs(D))` | Rapport d'orientation minimal |
|---|---:|---:|---:|
| 81 × 81 | 6 250 | 0,849251 | 0,982683 |
| 161 × 161 | 24 732 | 0,850141 | 0,982592 |

Le point cible a exactement la valeur prescrite dans la formule, même
lorsqu'il n'appartient pas à la grille ; le maximum grossier inférieur
à 0,85 n'est donc pas une borne globale. Les maxima des dérivées sur la
grille fine valent 6,81980 en U et 4,99246 en V. Aucun renversement local
d'orientation n'est observé aux points échantillonnés. Ce contrôle n'exclut
ni un maximum entre les points, ni une collision avec une autre face.

Le bidegré polynomial nécessaire est au plus **12 × 23**. Le facteur au
point cible vaut `1,70801e-6`, donc `C = 497 654,8`. Ce grand coefficient est
une mise à l'échelle, pas une mesure suffisante du conditionnement numérique.
La recherche évalue des facteurs positifs normalisés ; elle ne développe
pas ce polynôme de degré 23 en base de puissances. Une éventuelle conversion
vers des pôles Bernstein doit encore être contrôlée numériquement. Les
composantes de `∇log(D)` au point cible valent `(0,0117811 ; 0,262300)` ;
le point n'est pas un maximum stationnaire exactement imposé.

Les exposants tous supérieurs ou égaux à 2 conservent la propriété
analytique de valeur et gradient nuls aux bords. Les résidus de courbes
mesurés plus haut concernent le premier champ ; aucun nouveau contrôle
surfaces/arêtes d'un patch CAO localisé n'est prétendu.

Exécution native bornée à deux CPU et **60 secondes**, terminée avec
`exit 0`, sans STEP généré. Rapport privé distinct, premier rapport conservé :

```text
/tmp/917-f50/out/m64-localized-implicit-bubble-audit-20260907.json
SHA-256 458cac4e13d5f5569c324f5ed98cb65c50c634dc6c386cc407eab60e8cf87977
```

Le SHA du maître a de nouveau été vérifié inchangé après la recherche.
`field_accepted` et `cad_construction_authorized` restent faux dans le
rapport. La localisation passe seulement les critères **échantillonnés**
d'amplitude et d'orientation ; elle doit encore franchir les contrôles de
corridor, de conversion et de noyau CAO, puis les rayons appariés.

Aucune simulation thermique, calcul de résistance ou qualification LPBF
n'est prétendu par cette étape. La fabrication et le montage moteur restent
interdits.
