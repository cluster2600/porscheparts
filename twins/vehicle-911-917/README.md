# 911–917 — études d’encombrement F0/F1

Cette étude commence le dessin d’une 911 type 993 recevant un flat-12 de
917/30 biturbo. Elle compare l’architecture naturelle de la 911 — boîte devant
le moteur — à l’implantation centrale de la 917.

## Décision F1 — comportement prioritaire

La F1 remplace l’implantation retenue en F0 : le moteur n’est plus suspendu
derrière les roues arrière. Le flat-12 occupe l’ancienne zone de banquette,
devant le nouvel essieu arrière, et le transaxle est réservé derrière lui. Le
plus court essai passant parmi les trois dessinés porte l’empattement de
2 272 à **2 722 mm**, soit **+450 mm**.

Dans ce screening, la réserve moteur commence à X=1 472 mm, donc 107 mm après
la limite arrière hypothétique des occupants et 52 mm après la cloison
provisoire. Le centre géométrique du scan partiel se trouve environ 654 mm
devant l’essieu arrière. Ce point n’est pas le centre de masse du moteur et la
répartition 55–60 % arrière affichée est une cible, pas un résultat calculé.

Les sorties F1 restent dans `work/911-917-packaging-f1/`, hors Git :

- `911-917-mid-engine-layout-f1.png` et `.svg` : élévation cotée, vue de dessus
  et comparaison des empattements +300/+450/+600 mm ;
- `911-917-mid-engine-packaging-f1.step` : volumes de garde Build123d ;
- `911-917-mid-engine-designer-f1.png` : vue de designer générée à partir de la
  planche technique, non cotée et non dimensionnelle ;
- `packaging-report-f1.json` : calculs reproductibles et limites de preuve.

Le mode, le prompt exact et les empreintes de la vue de designer sont conservés
dans `designer-render-f1.json`.

### Variantes F2/F3 — aileron 930 et caisse étirée

F2 remplace le grand aileron de course par une « whale tail » fixe inspirée de
la 930 Turbo. Un échangeur horizontal d’air de suralimentation est montré sous
sa grille, avec une sortie d’air canalisée. F3 corrige ensuite la perspective de
la vue trois-quarts : les 450 mm sont visiblement ajoutés entre la cabine et
l’essieu arrière, pas dans le porte-à-faux.

- `911-917-mid-engine-930-tail-f2.png` : première intégration de l’aileron et de
  l’échangeur ;
- `911-917-mid-engine-930-tail-stretched-f3.png` : vue trois-quarts corrigée ;
- `designer-render-930-tail-f2.json` et
  `designer-render-930-tail-stretched-f3.json` : prompts, empreintes et limites.

F4 reprend la référence visuelle fournie par l’utilisateur : la lèvre supérieure
est plus large, plus reculée et remonte davantage. L’échangeur reste sous la
grille. Le rendu final est `911-917-mid-engine-930-tail-wide-f4.png` et son
contrat de provenance `designer-render-930-tail-wide-f4.json`. La photographie
de référence n’est pas copiée dans le dépôt et reste interdite de publication
tant que ses droits ne sont pas établis.

Ces images ne dimensionnent ni la puissance thermique, ni la perte de charge,
ni l’équilibre aérodynamique. Le dessin coté et le STEP F1 restent l’autorité
géométrique du screening.

### Variante F5 — prises d’air de custode et cloison moteur

F5 supprime les deux vitres latérales arrière. Leurs ouvertures deviennent des
prises d’air symétriques à ailettes, reliées visuellement à des plénums et aux
conduits du refroidissement moteur et des admissions biturbo. Une cloison pleine
hauteur à double peau ferme l’habitacle immédiatement derrière les sièges.

Le rendu est `911-917-mid-engine-intakes-firewall-f5.png` et sa provenance est
conservée dans `designer-render-intakes-firewall-f5.json`. Les sections de
passage, pertes de charge, entrées d’eau, matériaux, joints, traversées et tenue
au feu restent inconnus ; aucune fonction de sécurité n’est validée.

### Variante F6 — habitacle visuellement fermé

F6 corrige la vue trois-quarts : aucun siège, dossier ou volume habitable ne
subsiste derrière le montant B. La lunette arrière montre la face opaque de la
cloison, tandis que la coupe conserve exactement deux sièges devant celle-ci.
Le rendu final est `911-917-mid-engine-cabin-closed-f6.png` et les deux retouches
sont consignées dans `designer-render-cabin-closed-f6.json`.

### Variante F7 — cloison droite dans la coupe

F7 corrige uniquement la géométrie apparente de la cloison moteur dans la coupe
latérale. Ses deux peaux sont représentées par des lignes verticales parallèles,
sans cassure ni inclinaison, et la cloison reste continue du plancher à la
structure supérieure derrière les deux sièges. Le rendu est
`911-917-mid-engine-straight-firewall-f7.png` et sa provenance est conservée
dans `designer-render-straight-firewall-f7.json`.

Cette rectitude est une intention graphique : la position longitudinale,
l'épaisseur, les interfaces de coque et les performances feu/fumées ne sont pas
encore cotées ni validées.

### Variante F8 — profil de toit corrigé et gel artistique

F8 remplace, dans la coupe uniquement, le toit en pente montante par un arc de
coupé peu prononcé : raccord tangent au pare-brise, sommet au-dessus des
occupants avant, puis descente continue vers la cloison verticale. Le rendu est
`911-917-mid-engine-roof-profile-f8.png` et sa provenance est conservée dans
`designer-render-roof-profile-f8.json`.

F8 clôt les rendus artistiques. Son profil sert de brief visuel, pas de surface
CAO : la suite du projet doit partir des datums de coque mesurés, d'enveloppes
3D traçables et de calculs mécaniques reproductibles.

## F9 — démarrage de l'ingénierie mécanique

`mechanical-engineering-basis-f9.json` remplace le raisonnement par image par
un registre calculable et fermé par défaut. Le script
`source/build_mechanical_engineering_basis_f9.py` calcule le couple équivalent
à 1 600 mechanical hp entre 7 000 et 9 000 tr/min, applique un facteur de
screening provisoire de 1,30 et compare ce besoin aux seules valeurs publiées
par D.M.A., Hewland et Xtrac.

Le résultat F9 ne sélectionne aucune boîte. Le facteur 1,30 n'est pas un critère
de réception : il devra être remplacé par la courbe moteur mesurée, les pics
torsionnels et un spectre de charge accepté par le fabricant. Le registre F9
énumère aussi les mesures manquantes pour les datums de coque, l'enveloppe
moteur complète, les masses/centres de gravité, les interfaces de boîte, les
charges dynamiques et les rejets thermiques.

```bash
python3 twins/vehicle-911-917/source/build_mechanical_engineering_basis_f9.py --mode build
python3 twins/vehicle-911-917/source/build_mechanical_engineering_basis_f9.py --mode check
```

```bash
python3 twins/vehicle-911-917/source/build_mid_engine_layout_f1.py --mode render
.venv/bin/python twins/vehicle-911-917/source/build_mid_engine_layout_f1.py --mode cad
python3 twins/vehicle-911-917/source/build_mid_engine_layout_f1.py --mode check
```

L’empattement +300 mm échoue sur les dégagements occupants/cloison. Le +600 mm
offre davantage d’espace, mais allonge inutilement la voiture à ce stade. Le
+450 mm est donc une décision de dessin réversible, à revalider dès réception
du plan général de boîte et des mesures de caisse.

## Décision F0 — historique, non retenue pour la suite

L’essai alors retenu conservait l’empattement documentaire de 2 272 mm, supprimait les
places arrière, réservait la boîte devant le moteur et allongeait provisoirement la
poupe de 450 mm. Cette configuration est la seule des trois à préserver la zone
occupants déjà utilisée par le modèle de screening tout en laissant au moins
75 mm derrière la réserve du moteur complet.

Ce n’est pas encore une validation de montage :

- le scan local du carter et des cylindres est réellement lu par le générateur,
  mais son échelle 1:1 et son orientation restent non étalonnées ;
- le scan ne contient pas les culasses complètes, les collecteurs, les turbos,
  les écrans thermiques ou les volumes de maintenance ;
- aucune boîte candidate ne publie à la fois un plan général coté, les
  interfaces nécessaires et une marge de couple acceptée pour l’objectif de
  1 600 ch ;
- la silhouette de carrosserie est un dessin de présentation autour des
  dimensions documentaires de la 993, pas une surface Porsche reconstruite.

## Sorties locales

Les sorties restent dans `work/911-917-packaging-f0/`, hors Git :

- `911-917-packaging-f0.png` et `.svg` : élévation, vue de dessus et comparaison
  des trois essais ;
- `911-917-packaging-preferred-f0.step` : volumes de garde Build123d de
  l’implantation retenue ;
- `packaging-report-f0.json` : cotes calculées, provenance, décisions et gates.

Le dessin est produit avec Matplotlib et la CAO avec Build123d 0.11.1 déjà
présent dans `.venv` :

```bash
python3 twins/vehicle-911-917/source/build_packaging_concept_f0.py --mode render
.venv/bin/python twins/vehicle-911-917/source/build_packaging_concept_f0.py --mode cad
python3 twins/vehicle-911-917/source/build_packaging_concept_f0.py --mode check
```

## Lecture des couleurs

- orange plein : projection du scan local réorienté pour le screening ;
- orange transparent : réserve hypothétique du moteur complet ;
- bleu : réserve de boîte, non issue d’un plan constructeur ;
- gris : enveloppe de carrosserie et zone des places arrière supprimées ;
- rouge pointillé : cloison pare-feu à définir après mesure de caisse.

La recherche de transmission et les données à demander aux constructeurs sont
détaillées dans [gearbox-shortlist.md](research/gearbox-shortlist.md).

## Porte suivante

Avant de figer le dessin, il faut obtenir un plan général ou un STEP de la
boîte, mesurer la coque et les sièges, étalonner le scan moteur, puis remplacer
la réserve moteur par l’assemblage complet avec admission, échappement,
refroidissement et biturbo. Tous les gates de fabrication, route et circuit
restent fermés.
