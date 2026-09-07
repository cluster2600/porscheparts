# M64 — données matière relues sur les PDF fabricants

7 septembre 2026. Le skill PDF a imposé une vérification **visuelle** des
tableaux et notes : ECKART pages PDF 4–5, Constellium pages 1–2. Les quatre
pages ont été rendues localement ; ni PDF ni rendus propriétaires ne sont
ajoutés au dépôt. Empreintes, localisateurs et chiffres :
`twins/m64-cylinder-head/documentary-material-points-20260907.json`.

## Points A20X en fonction de la température

| T d'essai (°C) | Résistance à la traction (MPa) | Limite d'élasticité publiée (MPa) | Allongement (%) |
| ---: | ---: | ---: | ---: |
| 20 | 511 | 445 | 11 |
| 100 | 423 | 375 | 10 |
| 150 | 369 | 354 | 20 |
| 200 | 331 | 311 | 15 |
| 250 | 224 | 215 | 12 |

Source : [ECKART, page PDF 5, tableau inférieur](https://www.eckart.net/en/download/document/view/id/519).
Ce tableau ne précise pas directement traitement, orientation, effectif,
temps de maintien ni méthode d'essai à chaud. **Il n'est pas automatiquement
étiqueté T7.** Le tableau supérieur donne E = 74/77/79 GPa à température
ambiante pour brut/détensionné/traité T7, respectivement. Le détensionnement
est 300 °C, 2 h, sur plateau ; la recette T7 est propriétaire.

Anomalie conservée : 445 MPa à 20 °C dans le tableau inférieur, contre une
plage 390–440 MPa dans la colonne T7 supérieure. Ne pas fusionner ces jeux
ni corriger le chiffre sans clarification du fabricant. Les libellés ne
précisent pas l'offset Rp0,2 ; le relevé conserve « yield strength ».

## CP1 : traitement à 400 °C, mais traction à 25 °C

| Traitement à 400 °C | Traction à 25 °C (MPa) | Limite publiée à 25 °C (MPa) | Allongement (%) | k publié (W/m·K) |
| ---: | ---: | ---: | ---: | ---: |
| 1 h | 340 | 321 | 14,2 | 182 |
| 4 h | 342 | 323 | 12,8 | 187 |
| 7 h | 332 | 313 | 16,8 | 189 |

Source : [Constellium CP1, novembre 2021, page 2](https://assets.foleon.com/eu-central-1/de-uploads-7e3kk3/41170/product_sheet_aheadd_cp1_nov_2021docx.e81a7d073ebf.pdf).
L'orientation verticale et les 25 °C concernent la traction. **La température
de mesure de k n'est pas explicitée dans son en-tête adjacent** : elle reste
nulle dans le relevé. Les trois lignes font varier la durée du traitement,
pas la température de fonctionnement. Aucun point de traction à chaud n'est
fourni. La stabilité annoncée à 250–300 °C durant plusieurs milliers d'heures
ne constitue ni une courbe k(T) ni une résistance admissible à chaud.

## Données encore nécessaires pour simuler la pièce

| Propriété | A20X, pages examinées | CP1, pages examinées |
| --- | --- | --- |
| Limite/rupture en fonction de T | 5 points publiés, conditions incomplètes | Aucun point à chaud |
| Module E(T) | Seulement E ambiant selon état | Non publié |
| Conductivité k(T) | Non publiée | 3 valeurs selon traitement, pas selon T |
| Capacité thermique Cp(T) | Non publiée | Non publiée |
| Dilatation α(T), coefficient de Poisson | Non publiés | Non publiés |
| Plasticité complète, fluage, relaxation, fatigue/TMF | Pas de lois utilisables dans ces pages | Pas de lois utilisables dans ces pages |

Ce relevé améliore les points de départ documentaires mais ne fournit pas
une carte constitutive complète. Il ne choisit pas de matériau gagnant,
n'interpole aucune courbe et n'attribue aucun admissible à la culasse M64.
Les charges, le procédé exact et la plage de température doivent être
définis avant de comparer les marges mécaniques et thermiques.
