# Cotes FIA appliquées au prototype PicoGK

La fiche FIA et ses transcriptions étaient déjà dans le dépôt. Le prototype
précédent n'en exploitait pas la cote axe de piston–calotte : 22 mm au lieu
des 43 mm publiés. Cette étape du 11 octobre 2026 corrige cette omission et
rend explicite la provenance des dimensions utilisées.

## Source relue et réemploi du Git

La [fiche officielle n° 250](https://historicdb.fia.com/sites/default/files/car_attachment/1601078401/homologation_form_number_250_group_4.pdf)
a été téléchargée à nouveau, puis ses pages 8 et 14 inspectées visuellement.
Son SHA-256 correspond au registre existant :
`92a03ecef96a68cd227d0ef9f5f7413a7519a04ef24796330fbee4874b2226cd`.
Le PDF et ses captures restent privés dans `work/`.

Les transcriptions déjà présentes sont réutilisées :
[registre de source](../../../catalog/sources/src-fia-917-homologation-250.json),
[faits F13](../../../twins/reference-917-engine/classical-solver-cases-f13.json),
[dimensions F35](../../../twins/reference-917-engine/rotating-assembly-cad-f35.json)
et [matrice de mesures F29](../../../archive/917/docs/917_GERMAN_SOURCE_AND_MEASUREMENT_MATRIX_F29.md).
Le [relevé de relecture](source-review.json) fixe pages, champs, unités,
variante et empreintes. Aucun de ces anciens contrats n'est modifié.

| Référence FIA du 4,494 L | Page / champ | Application |
|---|---|---|
| Alésage 85 mm, course 66 mm | 8 / 133–134 | paramètres géométriques et cinématique |
| Distance axe de piston–calotte 43 mm | 8 / 146 | calotte du prototype placée à +43 mm de l'axe |
| Diamètre de palier/maneton 52 mm | 8 / 158 | référence de maneton ; logement de bielle à 54 mm avec coussinet radial de 1 mm **supposé** |
| Bielle 0,42 ± 0,02 kg | 8 / 163 | comparaison d'inertie avec les masses calculées du prototype |
| Piston + axe + segments 0,46 ± 0,02 kg | 8 / 164 | groupe complet de référence, jamais traité comme la masse du seul piston |

Le champ 159 à 56 mm reste exclu : son libellé est ambigu dans les contrats
existants. Il ne fournit ni le diamètre extérieur de la tête ni la cote du
logement usiné. L'extension 1/1E, page 14, donne 86 × 70,4 mm au 4,907 L ;
elle est enregistrée séparément et n'est pas appliquée à cette configuration.
Le libellé historique « Boxer » au champ 132 ne définit pas à lui seul
l'appariement des manetons ; la topologie et les phases du prototype restent
des hypothèses à confronter au vilebrequin.

## Géométrie réexécutée

[La configuration](reference-assumptions.json) est contrôlée par
[run.py](run.py), puis envoyée au générateur PicoGK de
[l'expérience précédente](../hypothesis/README.md). Ses sources et leurs
empreintes restent intactes : une nouvelle exécution et un nouveau relevé
sont créés. Les quatre familles et les 48 instances sont recalculées aux
grilles 1 et 0,5 mm ; les STL/VDB et l'assemblage restent privés.

Le générateur conservé représente un piston symétrique autour de son axe.
Pour appliquer +43 mm à la calotte, cette expérience choisit aussi **43 mm
de jupe sous l'axe** : hypothèse supplémentaire, pas cote FIA. La hauteur
totale calculée de 86 mm ne doit donc pas être attribuée à la fiche. Une
définition asymétrique attend la cote de jupe et son profil. Le diamètre
extérieur de tête de bielle 72 mm vient de l'hypothèse F35 ; le logement
54 mm est calculé depuis 52 mm et l'épaisseur de coussinet supposée.

Cette correction expose une incohérence utile : le cylindre provisoire reste
placé de 70 à 192 mm de l'axe de vilebrequin. Avec l'entraxe de bielle supposé
132 mm, la calotte atteint 208 mm au PMH. Le critère conservateur de couverture
axiale complète de la jupe donne −16 mm et **rejette cette implantation**.
Les entraxes 120 et 144 mm donnent −26 et −28 mm sous les mêmes hypothèses.
Cela ne prouve pas un défaut du moteur Porsche : position du cylindre, jupe,
culasse et référence de pont du prototype ne sont pas mesurées. Ces valeurs
ne sont pas artificiellement allongées pour faire passer le contrôle.

Le [relevé d'exécution](execution-20261011.json) conserve les audits, masses,
sondes et portes de qualification. Un écran de maillage ou un dégagement
échantillonné ne valide pas cette implantation ni son volume balayé complet.

## Charges et matière

Les masses FIA donnent une masse réciproque nominale de 0,600 kg sous
l'hypothèse inchangée d'un tiers de bielle en translation. En combinant les
intervalles déclarés par somme des extrêmes, elle varie de 0,5733 à 0,6267 kg.
Neuf scénarios pression/régime sont recalculés pour ce groupe documentaire,
en parallèle des dix-huit scénarios fondés sur les volumes et densités du
prototype. Les masses FIA ne sont pas transférées aux nouvelles pièces
titane/aluminium : leur géométrie et leur matière diffèrent.

À 8 000 tr/min et 80 bar supposés, ce groupe donne 45,40 kN de gaz et
17,37 kN d'inertie nominale. La somme des pics indépendants varie de
61,99 à 63,54 kN avec les intervalles de masse. Il ne s'agit pas d'un cycle
de combustion mesuré ni d'une preuve de résistance de la bielle.

La fiche indique des alliages légers et un revêtement de cylindre chromé dur,
sans qualifier AlSi10Mg ni Ti6Al4V. Les candidats additifs du dossier précédent
restent des choix à étudier ; ils ne sont pas des nuances Porsche confirmées.
Pression de combustion, fraction de masse de bielle, tolérances de montage,
tenue à chaud, fatigue et procédé final restent à établir.

```bash
PYTHON=/chemin/vers/python-avec-dependances-scientifiques
DOTNET=/chemin/vers/dotnet-9
"$PYTHON" models/917-engine-reconstruction/fia/run.py \
  --output work/917-fia/nouvelle-execution --dotnet "$DOTNET"
"$PYTHON" tests/test_917_picogk_fia.py -v
```

Les cotes documentaires sont disponibles et appliquées au modèle. Elles
n'établissent pas à elles seules l'identité ou l'échelle du scan, les intérieurs
non décrits, les tolérances d'usinage ou une qualification de fabrication.

Les 17 tests ciblés des trois étapes passent, dont le contrôle des empreintes
et les rejets de mélange de variantes. La compilation termine sans erreur ni
avertissement. `make check` exécute 3 631 tests, 153 ignorés, puis s'arrête sur
les deux comparaisons exactes de flottants déjà reproduites dans les fichiers
993 impeller/stator inchangés ; les cibles suivantes ne sont pas atteintes
localement. Les liens Markdown sont contrôlés séparément. Le code retour zéro
de cette expérience signifie que le diagnostic a été exécuté, pas que son
implantation rejetée est acceptée. Lire `source-review-status.json` et le
rapport FIA, en plus du statut du sous-programme de géométrie.
