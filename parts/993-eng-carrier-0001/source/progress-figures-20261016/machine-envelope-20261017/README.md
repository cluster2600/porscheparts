# Encombrement nominal de la pose actuelle du carrier

La planche présente les projections XY et XZ de **toutes les 587 404 faces** du
NPZ posé `13fb2ff1…`, sans décimation, changement de coordonnées ou nouveau
placement. La copie `data/part.npz` est byte-identique à l’original conservé.
Les surfaces de support finales ne sont pas représentées.

La pose réellement conservée est une rotation de 45° autour de Z, avec le bas
de pièce à Z10 et son sommet à Z62. Sa boîte mesure
451,134126397 × 451,134126397 × 52 mm. Le décalage de 10 mm est la valeur de
`support_gap_mm` et la cote globale du bas de pièce ; il ne signifie pas que
les sept régions de support ont une hauteur uniforme de 10 mm.

La plaque d’étude mesure 500 × 500 × 20 mm. Le CORE place son dessus à Z0 et son
dessous à Z−20. La chambre 650 × 650 est centrée sur le même axeXY : les marges
géométriques sont 24,432936801 mm entre boîte de pièce et bord de plaque,
75 mm entre plaque et chambre, et99,432936801 mm entre boîte de pièce et chambre.
Ce sont des marges à l’enveloppe nominale, sans déduction inventée pour un
bridage ou des zones interdites.

## Deux fiches constructeur, relues le 17 octobre 2026

| Machine | Volume nominal annoncé | Convention de hauteur | Épaisseur de couche publiée |
| --- | --- | --- | --- |
| [Eplus3D EP-M650](https://www.eplus3d.com/products/ep-m650-metal-3d-printer/) | 650 × 650 × 800 mm| Plaque incluse| 20–120 µm|
| [BLT-S600 révisée](https://www.xa-blt.com/en/product/blt-s600/?category=8) | 650 × 650 × 850 mm| Substrat exclu| Non précisée sur cette fiche|

La [publication officielle de la révision BLT-S600](https://www.xa-blt.com/en/news/enhance-quality-and-efficiency-standing-out-with-strength-join-us-at-airshow-china-2024-to-witness-the-upgraded-blt-s600/)
confirme le volume 650 × 650 × 850 mm. La fiche produit précise l’exclusion de
l’épaisseur du substrat.

Avec la plaque d’étude de 20 mm, l’EP-M650 demande une hauteur occupée de
20 + 62 = 82 mm dans sa convention, soit 718 mm disponibles au-dessus. La BLT
annonce 850 mm au-dessus du substrat : 62 mm sont occupés, soit 788 mm de réserve.
Le panneauZ traduit ces deux origines ; les barres sont un schéma des hauteurs,
pas un dessin de la pièce ni des supports. Les projections XY et XZ ont, elles,
des axes en millimètres d’échelles égales et contrôlées.

Les deux constructeurs annoncent les alliages de titane. La
[fiche matière Eplus3D](https://www.eplus3d.com/products/titanium-additive-manufacturing/)
répertorie les Ti64 Grade 5 et Grade 23. Cela ne relie pas automatiquement le
candidat Grade 5 aux données mécaniques du coupon Grade 23 ELI, et ne fournit
pas ici un jeu de paramètres Grade 23 / 60 µm propre à l’EP-M650. La planche
indique donc **« Ti64 : variante procédé à choisir »**. Elle ne transpose
aucune résistance de fiche ou de coupon au carrier.

Les choix machine sont déjà conservés dans le fichier historique
`parts/993-eng-carrier-0001/source/process-20261016/machine-options.json` ; sa
copie du 16 octobre reste intacte. Les spécifications relues le 17 octobre sont
enregistrées séparément dans `data/figure-data.json`. Aucun fabricant n’a été
contacté. Bridage, surface utile et paramètres de fabrication restent à définir.

## Sources et reproduction

- `data/part.npz` : copie exacte du maillage posé, 293 660 sommets / 587 404 faces.
- `data/inputs-v2.json` : copie exacte du reçu de pose et des paramètres.
- `data/machine-options-20261016.json` : copie exacte du choix historique.
- `data/figure-data.json` : identités de tableaux, bornes et marges calculées.
- `render-plan-v3.json` : sources/données épinglées et ressources.
- `render-003/render-receipt.json` : vrai résultat du rendu, axes, marges,
  nombres de faces et versions/empreintes des bibliothèques chargées.

Le renderer réutilise Python 3.10.11, Matplotlib 3.10.8, NumPy 2.2.6 et
Pillow 11.3.0 déjà installés. Il ne charge aucun module AM et ne lance aucun
solveur. La limite est 60 s, un thread, zéro worker. Les collections des deux
projections sont rastérisées dans les PDF/SVG pour conserver des fichiers
compacts ; tous les triangles restent soumis au renderer.

Depuis n’importe quel répertoire, donner des chemins absolus et un dossier
de sortie neuf :

```sh
/usr/bin/nice -n 10 /Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10 -B \
  /CHEMIN/carrier-machine-envelope-figure-001/render_v3.py \
  /CHEMIN/SORTIE_NEUVE
```

Le reçu vérifie les sources avant/après et contient les empreintes des PNG,
SVG et PDF. Le manifeste lie également les copies et leur origine. Aucune
source historique, géométrie ou recette de fabrication n’est modifiée.

Le premier rendu `render-001` reste conservé. La révision de présentation v2
sépare les titres et les paragraphes, déplace la légende et utilise des traits
de cote pour les deux très petites distances. Le fichier
`presentation-only-v2.patch` conserve le delta ; données, axes et marges ne
changent pas.

La révision v3 déplace seulement la légende dans la zone vide de la plaque,
afin de laisser visible le contour orange de la chambre. Le delta est conservé
dans `presentation-only-v3.patch`. Le rendu final est `render-003/`.
