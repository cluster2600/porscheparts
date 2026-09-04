# F42.2 — tranchage géométrique pleine pièce à 50 µm

## Verdict

F42.2 intersecte réellement la peau soudée privée avec les `4 122` plans
médians d'une construction à `50 µm`. Le résultat public contient une ligne
agrégée par couche, une image de synthèse et une vidéo de progression. Les
contours, coordonnées et supports reconstructibles restent privés.

![Audit pleine pile F42.2](../twins/reference-917-engine/evidence/f42-2-full-build/917-head-f42-2-full-build.png)

Cette preuve **n'autorise pas l'impression**. Elle n'est ni un projet du
trancheur BLT, ni un fichier machine, ni un calcul AdditiveFOAM, ni une preuve
de jeu entre une pièce déformée et le recoater.

## Repère, machine et pile de couches

L'orientation verrouillée `scan_y_down` conserve l'enveloppe de la preuve F41 :
environ `119 × 82 × 206 mm`. Elle tient nominalement dans le volume constructeur
`250 × 250 × 400 mm` de la BLT-S310. Cette vérification d'enveloppe ne comprend
pas la plaque, les marges de bord, les supports optimisés, le retrait ni la
déformation.

La hauteur exacte du maillage traité et le calcul
`ceil(hauteur / 0,050) = 4 122` sont consignés dans le rapport. Chaque section
est prise au milieu de la couche (`0,025`, `0,075`, ..., `206,075 mm`) par
intersection triangle-plan. Une couche vide, un index manquant, un pas Z faux
ou une métrique non finie fait échouer la chaîne.

La machine et la fenêtre procédé restent celles documentées en F42. Source
constructeur : [catalogue BLT](https://www.xa-blt.com/en/wp-content/uploads/2023/04/BLT-Engine-Solutions-2023.4.13.pdf).

## Résultats de l'écran

| Mesure | Résultat F42.2 |
| --- | ---: |
| couches réellement sectionnées | 4 122 / 4 122 |
| couches internes vides | 0 |
| couches avec nouvel îlot | 112 |
| nombre total de nouveaux îlots | 179 |
| couches avec région non soutenue | 2 098 |
| aire non soutenue maximale sur une couche | 458,464 mm² |
| volume de l'enveloppe support à pas 0,25 mm | 265,161 cm³ |
| surface latérale support approximative | 216 843,7 mm² |

L'écran cardinal donne `-Y` comme plus faible projection descendante parmi les
six directions testées. L'orientation verrouillée reste `+Y / scan_y_down` :
`-Y` n'est qu'une candidate tant qu'elle n'a pas son propre tranchage exhaustif,
son placement, ses supports et son étude thermique.

## Îlots, overhangs et supports

Le critère géométrique est un angle limite de `45°`. À `50 µm`, une couche est
considérée portée par la couche précédente dilatée de
`0,05 / tan(45°) = 0,05 mm`. Le rapport distingue :

- les composantes entièrement nouvelles, appelées îlots géométriques ;
- les régions partiellement non portées d'une composante existante ;
- les composantes et aires filtrées au-dessus de `0,01 mm²`, seuil numérique
  déclaré et non seuil procédé BLT.

Une enveloppe de supports conservative est ensuite construite de haut en bas :
chaque région non portée est projetée verticalement jusqu'au plateau et la
matière de la pièce est retranchée à chaque couche. Cette seconde étape est
rastérisée à un pas déclaré de `0,25 mm`; les détections d'îlots et d'overhangs
restent issues des contours exacts à `50 µm`. Le volume est la somme des
pixels occupés multipliée par l'aire du pixel et `0,05 mm`; la surface latérale
est estimée par les arêtes de pixels multipliées par `0,05 mm`. Les interfaces horizontales, dents,
struts, perforations, paramètres de détachement et parcours laser ne sont pas
modélisés. Le fichier NPZ binaire couche par couche est conservé exclusivement dans le
répertoire privé du calculateur et son seul SHA-256 est public.

Les six directions cardinales sont aussi comparées par aire de triangles dont
la normale est descendante au-delà de `45°`. C'est un écran surfacique rapide.
Une orientation candidate doit être retranchée intégralement avant décision ;
elle n'est pas automatiquement retenue.

## Recoater et AdditiveFOAM

Le tranchage géométrique répond à « où se trouve la matière nominale à chaque
couche ». AdditiveFOAM répond à un autre problème : dépôt d'énergie, champ de
température et bain fondu pour une piste ou un domaine calculé. F42.2 n'exécute
pas AdditiveFOAM et ne produit aucun champ thermique.

Une collision recoater exige au minimum un champ de déformation LPBF calibré,
le jeu, la raideur et le sens de balayage de la lame, la géométrie finale des
supports et le projet fournisseur. Ces entrées manquent. La pile nominale est
dans l'enveloppe machine, mais la porte `recoater_collision_clearance_verified`
reste donc fausse.

## Reproduction contrôlée

Le STL n'est jamais copié dans Git. Sur le calculateur autorisé :

```sh
python3 twins/reference-917-engine/source/run_f42_2_full_build_slicing.py \
  --head /chemin/prive/culasse-soudee.stl \
  --output /chemin/prive/f42-2-full-build
```

Seuls les deux fichiers publics suivants sont ensuite extraits :

- `917-head-f42-2-full-build-report.json` ;
- `917-head-f42-2-layer-metrics.csv`.

Le rendu public, sans contours, est produit par :

```sh
python3 twins/reference-917-engine/source/render_f42_2_full_build.py \
  --report twins/reference-917-engine/evidence/f42-2-full-build/917-head-f42-2-full-build-report.json \
  --metrics twins/reference-917-engine/evidence/f42-2-full-build/917-head-f42-2-layer-metrics.csv \
  --image twins/reference-917-engine/evidence/f42-2-full-build/917-head-f42-2-full-build.png \
  --video twins/reference-917-engine/evidence/f42-2-full-build/917-head-f42-2-build-progress.mp4 \
  --manifest twins/reference-917-engine/evidence/f42-2-full-build/917-head-f42-2-publication-manifest.json
```

Les tests relisent les `4 122` lignes, les SHA-256 et toutes les portes de
sécurité. L'autorisation restera fermée jusqu'à revue fournisseur du projet de
tranchage, géométrie finale des supports, calcul thermo-mécanique corrélé,
rapport de collision et fichier machine signé.
